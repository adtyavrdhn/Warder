"""
Container service for the Warder application.
Handles Podman container operations for agent hosting.
"""

import logging
import os
import re
import random
import string
import subprocess
import json
from typing import Dict, List, Optional, Tuple, Any

from app.models.agent import Agent

# Configure logger
logger = logging.getLogger(__name__)

# Check if Podman is available
try:
    result = subprocess.run(
        ["podman", "--version"], capture_output=True, text=True, check=True
    )
    PODMAN_AVAILABLE = True
    logger.info(f"Podman version: {result.stdout.strip()}")
except (subprocess.SubprocessError, FileNotFoundError) as e:
    logger.warning(f"Podman client initialization failed: {str(e)}")
    PODMAN_AVAILABLE = False

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
        if not PODMAN_AVAILABLE:
            logger.warning(
                "Podman is not available. Container operations will be limited."
            )
            return

        # Ensure the network exists
        self._ensure_network()

    def _ensure_network(self) -> None:
        """Ensure the Podman network exists."""
        if not PODMAN_AVAILABLE:
            return

        try:
            # Check if network exists
            result = subprocess.run(
                ["podman", "network", "inspect", DEFAULT_NETWORK],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.info(f"Creating Podman network: {DEFAULT_NETWORK}")
                subprocess.run(
                    ["podman", "network", "create", DEFAULT_NETWORK],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logger.info(f"Podman network created: {DEFAULT_NETWORK}")
        except subprocess.SubprocessError as e:
            logger.error(f"Error ensuring Podman network: {str(e)}")

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
        if not PODMAN_AVAILABLE:
            # Return a random port in the range if Podman is not available
            return random.randint(DEFAULT_PORT_RANGE_START, DEFAULT_PORT_RANGE_END)

        # Get all running containers
        try:
            result = subprocess.run(
                ["podman", "ps", "--format", "{{.Ports}}"],
                capture_output=True,
                text=True,
                check=True,
            )

            # Extract all used ports
            used_ports = set()
            for line in result.stdout.splitlines():
                if line:
                    # Parse port mappings like "0.0.0.0:9000->8000/tcp"
                    port_mappings = line.split(",")
                    for mapping in port_mappings:
                        match = re.search(r":(\d+)->", mapping)
                        if match:
                            used_ports.add(int(match.group(1)))

            # Find an available port in the range
            for port in range(DEFAULT_PORT_RANGE_START, DEFAULT_PORT_RANGE_END + 1):
                if port not in used_ports:
                    return port

            # If all ports are used, return a random port (will fail if actually used)
            logger.warning(
                "All ports in the configured range are used. Returning a random port."
            )
        except subprocess.SubprocessError as e:
            logger.error(f"Error finding available port: {str(e)}")

        return random.randint(DEFAULT_PORT_RANGE_START, DEFAULT_PORT_RANGE_END)

    async def create_container(self, agent: Agent) -> Tuple[bool, str]:
        """
        Create a Podman container for the agent.

        Args:
            agent: The agent to create a container for

        Returns:
            A tuple of (success, message)
        """
        if not PODMAN_AVAILABLE:
            return False, "Podman is not available"

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

            # Add LLM model configuration
            model_config = agent.config.get("model", {})
            if model_config:
                env_vars["LLM_PROVIDER"] = model_config.get("provider", "openai")
                env_vars["LLM_MODEL"] = model_config.get("name", "gpt-4o")
                # Add API key if available
                if "api_key" in model_config:
                    env_vars["LLM_API_KEY"] = model_config["api_key"]

            # Add knowledge base configuration for RAG agents
            if agent.type.value == "rag":
                # Get knowledge base config from agent config
                kb_config = agent.config.get("knowledge_base", {})

                # Set knowledge path to the mounted directory in the container
                env_vars["KNOWLEDGE_PATH"] = "data/pdfs/docs"

                # Set vector database configuration
                # Get the vector database URL from environment or use a default
                vector_db_url = os.getenv(
                    "VECTOR_DB_URL",
                    "postgresql://postgres:postgres@localhost:5432/warder",
                )

                # For Podman on macOS, we need to use the special hostname
                if "localhost" in vector_db_url or "127.0.0.1" in vector_db_url:
                    # Replace localhost with host.containers.internal for Podman
                    vector_db_url = vector_db_url.replace(
                        "localhost", "host.containers.internal"
                    )
                    vector_db_url = vector_db_url.replace(
                        "127.0.0.1", "host.containers.internal"
                    )

                env_vars["VECTOR_DB_URL"] = vector_db_url
                # Create a table name for this agent
                table_name = f"pdf_documents_{agent.id}".replace("-", "_")
                env_vars["VECTOR_DB_TABLE"] = table_name

                # Set knowledge base parameters
                env_vars["KB_RECREATE"] = str(kb_config.get("recreate", False)).lower()
                env_vars["KB_CHUNK_SIZE"] = str(kb_config.get("chunk_size", 1000))
                env_vars["KB_CHUNK_OVERLAP"] = str(kb_config.get("chunk_overlap", 200))

            # Create the container
            logger.info(
                f"Creating container for agent {agent.id} with name {container_name}"
            )

            # Build command with environment variables
            cmd = ["podman", "create", "--name", container_name]

            # Add environment variables
            for key, value in env_vars.items():
                cmd.extend(["-e", f"{key}={value}"])

            # Use the default network for better connectivity
            cmd.extend(["--network", DEFAULT_NETWORK])

            # Add port mapping for the container
            # Find an available port
            host_port = self._find_available_port()
            # Map to port 8080 which is what the agent is using
            cmd.extend(["-p", f"{host_port}:8080/tcp"])

            # Debug output for troubleshooting
            logger.info(f"Container create command: {' '.join(cmd)}")

            # Add memory limit
            cmd.extend(["--memory", memory_limit])

            # Add CPU limit (Podman uses --cpus instead of Docker's cpu-quota)
            cmd.extend(["--cpus", str(cpu_limit)])

            # Add restart policy
            cmd.extend(["--restart", "unless-stopped"])

            # Mount knowledge base directory for RAG agents
            if agent.type.value == "rag":
                # Get the agent's knowledge base directory with absolute path
                kb_base = os.getenv("KNOWLEDGE_BASE_DIR", "data/knowledge_base")
                kb_dir = os.path.join(os.getcwd(), kb_base, str(agent.id))
                # Ensure the directory exists
                os.makedirs(kb_dir, exist_ok=True)
                # Mount the directory to the container with absolute path
                cmd.extend(["-v", f"{kb_dir}:/app/data/pdfs:ro"])

            # Add labels
            cmd.extend(
                [
                    "--label",
                    f"warder.agent.id={str(agent.id)}",
                    "--label",
                    f"warder.agent.name={agent.name}",
                    "--label",
                    f"warder.agent.user_id={str(agent.user_id)}",
                ]
            )

            # Add image with localhost prefix for podman
            cmd.append(f"localhost/{image}")

            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Return the container ID
            container_id = result.stdout.strip()
            return True, container_id

        except subprocess.SubprocessError as e:
            logger.error(f"Error creating container for agent {agent.id}: {str(e)}")
            return False, str(e)

    async def start_container(self, container_id: str) -> Tuple[bool, str]:
        """
        Start a Podman container.

        Args:
            container_id: The container ID

        Returns:
            A tuple of (success, message)
        """
        if not PODMAN_AVAILABLE:
            return False, "Podman is not available"

        try:
            subprocess.run(
                ["podman", "start", container_id],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"Container {container_id} started")
            return True, "Container started"
        except subprocess.SubprocessError as e:
            logger.error(f"Error starting container {container_id}: {str(e)}")
            return False, str(e)

    async def stop_container(self, container_id: str) -> Tuple[bool, str]:
        """
        Stop a Podman container.

        Args:
            container_id: The container ID

        Returns:
            A tuple of (success, message)
        """
        if not PODMAN_AVAILABLE:
            return False, "Podman is not available"

        try:
            subprocess.run(
                ["podman", "stop", "--time", "10", container_id],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"Container {container_id} stopped")
            return True, "Container stopped"
        except subprocess.SubprocessError as e:
            logger.error(f"Error stopping container {container_id}: {str(e)}")
            return False, str(e)

    async def delete_container(self, container_id: str) -> Tuple[bool, str]:
        """
        Delete a Podman container.

        Args:
            container_id: The container ID

        Returns:
            A tuple of (success, message)
        """
        if not PODMAN_AVAILABLE:
            return False, "Podman is not available"

        try:
            # Check if container is running
            result = subprocess.run(
                ["podman", "inspect", "--format", "{{.State.Running}}", container_id],
                capture_output=True,
                text=True,
            )

            # Stop the container if it's running
            if result.stdout.strip() == "true":
                subprocess.run(
                    ["podman", "stop", "--time", "10", container_id],
                    capture_output=True,
                    text=True,
                    check=True,
                )

            # Remove the container
            subprocess.run(
                ["podman", "rm", "--force", container_id],
                capture_output=True,
                text=True,
                check=True,
            )

            logger.info(f"Container {container_id} deleted")
            return True, "Container deleted"
        except subprocess.SubprocessError as e:
            logger.error(f"Error deleting container {container_id}: {str(e)}")
            return False, str(e)

    async def get_container_status(self, container_id: str) -> Optional[str]:
        """
        Get the status of a Podman container.

        Args:
            container_id: The container ID

        Returns:
            The container status if found, None otherwise
        """
        if not PODMAN_AVAILABLE:
            return None

        try:
            result = subprocess.run(
                ["podman", "inspect", "--format", "{{.State.Status}}", container_id],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except subprocess.SubprocessError as e:
            logger.error(f"Error getting container status for {container_id}: {str(e)}")
            return None

    async def get_container_logs(
        self, container_id: str, lines: int = 100
    ) -> Optional[str]:
        """
        Get the logs of a Podman container.

        Args:
            container_id: The container ID
            lines: Number of lines to retrieve

        Returns:
            The container logs if found, None otherwise
        """
        if not PODMAN_AVAILABLE:
            return None

        try:
            result = subprocess.run(
                ["podman", "logs", "--tail", str(lines), "--timestamps", container_id],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return result.stdout
            return None
        except subprocess.SubprocessError as e:
            logger.error(f"Error getting container logs for {container_id}: {str(e)}")
            return None

    async def list_agent_containers(self) -> List[Dict[str, Any]]:
        """
        List all agent containers.

        Returns:
            A list of container information dictionaries
        """
        if not PODMAN_AVAILABLE:
            return []

        try:
            # Get all containers with the warder.agent.id label
            result = subprocess.run(
                [
                    "podman",
                    "ps",
                    "--all",
                    "--filter",
                    "label=warder.agent.id",
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return []

            containers = json.loads(result.stdout)

            result = []
            for container in containers:
                # Extract port mappings
                ports = {}
                if "Ports" in container:
                    for port_mapping in container["Ports"]:
                        parts = port_mapping.split("->")
                        if len(parts) == 2:
                            host_part = parts[0].strip()
                            container_part = parts[1].strip()
                            ports[container_part] = [
                                {"HostPort": host_part.split(":")[-1]}
                            ]

                # Extract labels
                labels = container.get("Labels", {})

                result.append(
                    {
                        "id": container["Id"],
                        "name": container["Names"][0],
                        "status": container["State"],
                        "agent_id": labels.get("warder.agent.id"),
                        "agent_name": labels.get("warder.agent.name"),
                        "user_id": labels.get("warder.agent.user_id"),
                        "created": container["Created"],
                        "ports": ports,
                    }
                )

            return result
        except (subprocess.SubprocessError, json.JSONDecodeError) as e:
            logger.error(f"Error listing agent containers: {str(e)}")
            return []

    async def inspect_container(
        self, container_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Inspect a Podman container to get detailed information.

        Args:
            container_id: The container ID

        Returns:
            A tuple of (success, container_info)
        """
        if not PODMAN_AVAILABLE:
            return False, None

        try:
            result = subprocess.run(
                ["podman", "inspect", container_id],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error(
                    f"Error inspecting container {container_id}: {result.stderr}"
                )
                return False, None

            # Parse the JSON output
            container_info = json.loads(result.stdout)
            if (
                not container_info
                or not isinstance(container_info, list)
                or len(container_info) == 0
            ):
                logger.error(f"Invalid container info format for {container_id}")
                return False, None

            return True, container_info[0]
        except (subprocess.SubprocessError, json.JSONDecodeError) as e:
            logger.error(f"Error inspecting container {container_id}: {str(e)}")
            return False, None

    async def get_container_stats(self, container_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the stats of a Podman container.

        Args:
            container_id: The container ID

        Returns:
            The container stats if found, None otherwise
        """
        if not PODMAN_AVAILABLE:
            return None

        try:
            result = subprocess.run(
                ["podman", "stats", "--no-stream", "--format", "json", container_id],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                stats = json.loads(result.stdout)
                if stats and len(stats) > 0:
                    return stats[0]
            return None
        except (subprocess.SubprocessError, json.JSONDecodeError) as e:
            logger.error(f"Error getting container stats for {container_id}: {str(e)}")
            return None
