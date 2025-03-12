"""
Container service for the Warder application.
Handles Docker container operations for agent hosting.
"""

import logging
import os
import re
import random
import string
import docker
from typing import Dict, List, Optional, Tuple, Any

from app.models.agent import Agent

# Configure logger
logger = logging.getLogger(__name__)

# Docker client
try:
    docker_client = docker.from_env()
    DOCKER_AVAILABLE = True
except Exception as e:
    logger.warning(f"Docker client initialization failed: {str(e)}")
    DOCKER_AVAILABLE = False

# Default port range for agent containers
DEFAULT_PORT_RANGE_START = int(os.getenv("AGENT_PORT_RANGE_START", "9000"))
DEFAULT_PORT_RANGE_END = int(os.getenv("AGENT_PORT_RANGE_END", "9500"))

# Default container network
DEFAULT_NETWORK = os.getenv("AGENT_NETWORK", "warder_network")

# Default container image
DEFAULT_IMAGE = os.getenv("AGENT_IMAGE", "warder/agent:latest")


class ContainerService:
    """Service for container-related operations."""

    def __init__(self):
        """Initialize the container service."""
        if not DOCKER_AVAILABLE:
            logger.warning(
                "Docker is not available. Container operations will be limited."
            )
            return

        # Ensure the network exists
        self._ensure_network()

    def _ensure_network(self) -> None:
        """Ensure the Docker network exists."""
        if not DOCKER_AVAILABLE:
            return

        try:
            networks = docker_client.networks.list(names=[DEFAULT_NETWORK])
            if not networks:
                logger.info(f"Creating Docker network: {DEFAULT_NETWORK}")
                docker_client.networks.create(
                    name=DEFAULT_NETWORK,
                    driver="bridge",
                    check_duplicate=True,
                )
                logger.info(f"Docker network created: {DEFAULT_NETWORK}")
        except Exception as e:
            logger.error(f"Error ensuring Docker network: {str(e)}")

    def _generate_container_name(self, agent_name: str) -> str:
        """
        Generate a unique container name based on the agent name.

        Args:
            agent_name: The agent name

        Returns:
            A unique container name
        """
        # Sanitize the agent name (remove special characters, convert to lowercase)
        sanitized_name = re.sub(r"[^a-zA-Z0-9_.-]", "", agent_name.lower())

        # Add a random suffix to ensure uniqueness
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))

        return f"warder-agent-{sanitized_name}-{suffix}"

    def _find_available_port(self) -> int:
        """
        Find an available port in the configured range.

        Returns:
            An available port
        """
        if not DOCKER_AVAILABLE:
            # Return a random port in the range if Docker is not available
            return random.randint(DEFAULT_PORT_RANGE_START, DEFAULT_PORT_RANGE_END)

        # Get all running containers
        containers = docker_client.containers.list()

        # Extract all used ports
        used_ports = set()
        for container in containers:
            for port_config in container.ports.values():
                if port_config:
                    for binding in port_config:
                        if "HostPort" in binding:
                            used_ports.add(int(binding["HostPort"]))

        # Find an available port in the range
        for port in range(DEFAULT_PORT_RANGE_START, DEFAULT_PORT_RANGE_END + 1):
            if port not in used_ports:
                return port

        # If all ports are used, return a random port (will fail if actually used)
        logger.warning(
            "All ports in the configured range are used. Returning a random port."
        )
        return random.randint(DEFAULT_PORT_RANGE_START, DEFAULT_PORT_RANGE_END)

    async def create_container(self, agent: Agent) -> Tuple[bool, str]:
        """
        Create a Docker container for the agent.

        Args:
            agent: The agent to create a container for

        Returns:
            A tuple of (success, message)
        """
        if not DOCKER_AVAILABLE:
            return False, "Docker is not available"

        try:
            # Generate a unique container name
            container_name = self._generate_container_name(agent.name)

            # Find an available port
            host_port = self._find_available_port()

            # Get container configuration from agent
            container_config = agent.container_config or {}

            # Set default values if not provided
            image = container_config.get("image", DEFAULT_IMAGE)
            memory_limit = container_config.get("memory_limit", "512m")
            cpu_limit = container_config.get("cpu_limit", 0.5)
            env_vars = container_config.get("env_vars", {})

            # Add agent-specific environment variables
            env_vars.update(
                {
                    "AGENT_ID": str(agent.id),
                    "AGENT_NAME": agent.name,
                    "AGENT_TYPE": agent.type.value,
                }
            )

            # Create the container
            logger.info(
                f"Creating container for agent {agent.id} with name {container_name}"
            )
            container = docker_client.containers.create(
                image=image,
                name=container_name,
                detach=True,
                environment=env_vars,
                network=DEFAULT_NETWORK,
                ports={"8000/tcp": host_port},
                mem_limit=memory_limit,
                cpu_quota=int(cpu_limit * 100000),  # Docker uses microseconds
                restart_policy={"Name": "unless-stopped"},
                labels={
                    "warder.agent.id": str(agent.id),
                    "warder.agent.name": agent.name,
                    "warder.agent.user_id": str(agent.user_id),
                },
            )

            return True, container.id

        except Exception as e:
            logger.error(f"Error creating container for agent {agent.id}: {str(e)}")
            return False, str(e)

    async def start_container(self, container_id: str) -> Tuple[bool, str]:
        """
        Start a Docker container.

        Args:
            container_id: The container ID

        Returns:
            A tuple of (success, message)
        """
        if not DOCKER_AVAILABLE:
            return False, "Docker is not available"

        try:
            container = docker_client.containers.get(container_id)
            container.start()
            logger.info(f"Container {container_id} started")
            return True, "Container started"
        except Exception as e:
            logger.error(f"Error starting container {container_id}: {str(e)}")
            return False, str(e)

    async def stop_container(self, container_id: str) -> Tuple[bool, str]:
        """
        Stop a Docker container.

        Args:
            container_id: The container ID

        Returns:
            A tuple of (success, message)
        """
        if not DOCKER_AVAILABLE:
            return False, "Docker is not available"

        try:
            container = docker_client.containers.get(container_id)
            container.stop(timeout=10)  # Give it 10 seconds to stop gracefully
            logger.info(f"Container {container_id} stopped")
            return True, "Container stopped"
        except Exception as e:
            logger.error(f"Error stopping container {container_id}: {str(e)}")
            return False, str(e)

    async def delete_container(self, container_id: str) -> Tuple[bool, str]:
        """
        Delete a Docker container.

        Args:
            container_id: The container ID

        Returns:
            A tuple of (success, message)
        """
        if not DOCKER_AVAILABLE:
            return False, "Docker is not available"

        try:
            container = docker_client.containers.get(container_id)

            # Stop the container if it's running
            if container.status == "running":
                container.stop(timeout=10)

            # Remove the container
            container.remove(force=True)
            logger.info(f"Container {container_id} deleted")
            return True, "Container deleted"
        except Exception as e:
            logger.error(f"Error deleting container {container_id}: {str(e)}")
            return False, str(e)

    async def get_container_status(self, container_id: str) -> Optional[str]:
        """
        Get the status of a Docker container.

        Args:
            container_id: The container ID

        Returns:
            The container status if found, None otherwise
        """
        if not DOCKER_AVAILABLE:
            return None

        try:
            container = docker_client.containers.get(container_id)
            return container.status
        except Exception as e:
            logger.error(f"Error getting container status for {container_id}: {str(e)}")
            return None

    async def get_container_logs(
        self, container_id: str, lines: int = 100
    ) -> Optional[str]:
        """
        Get the logs of a Docker container.

        Args:
            container_id: The container ID
            lines: Number of lines to retrieve

        Returns:
            The container logs if found, None otherwise
        """
        if not DOCKER_AVAILABLE:
            return None

        try:
            container = docker_client.containers.get(container_id)
            logs = container.logs(tail=lines, timestamps=True).decode("utf-8")
            return logs
        except Exception as e:
            logger.error(f"Error getting container logs for {container_id}: {str(e)}")
            return None

    async def list_agent_containers(self) -> List[Dict[str, Any]]:
        """
        List all agent containers.

        Returns:
            A list of container information dictionaries
        """
        if not DOCKER_AVAILABLE:
            return []

        try:
            containers = docker_client.containers.list(
                all=True, filters={"label": "warder.agent.id"}
            )

            result = []
            for container in containers:
                result.append(
                    {
                        "id": container.id,
                        "name": container.name,
                        "status": container.status,
                        "agent_id": container.labels.get("warder.agent.id"),
                        "agent_name": container.labels.get("warder.agent.name"),
                        "user_id": container.labels.get("warder.agent.user_id"),
                        "created": container.attrs.get("Created"),
                        "ports": container.ports,
                    }
                )

            return result
        except Exception as e:
            logger.error(f"Error listing agent containers: {str(e)}")
            return []

    async def get_container_stats(self, container_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the stats of a Docker container.

        Args:
            container_id: The container ID

        Returns:
            The container stats if found, None otherwise
        """
        if not DOCKER_AVAILABLE:
            return None

        try:
            container = docker_client.containers.get(container_id)
            stats = container.stats(stream=False)

            # Extract relevant stats
            cpu_stats = stats.get("cpu_stats", {})
            memory_stats = stats.get("memory_stats", {})
            network_stats = stats.get("networks", {}).get("eth0", {})

            return {
                "cpu_usage": cpu_stats.get("cpu_usage", {}).get("total_usage", 0),
                "system_cpu_usage": cpu_stats.get("system_cpu_usage", 0),
                "memory_usage": memory_stats.get("usage", 0),
                "memory_limit": memory_stats.get("limit", 0),
                "network_rx_bytes": network_stats.get("rx_bytes", 0),
                "network_tx_bytes": network_stats.get("tx_bytes", 0),
            }
        except Exception as e:
            logger.error(f"Error getting container stats for {container_id}: {str(e)}")
            return None
