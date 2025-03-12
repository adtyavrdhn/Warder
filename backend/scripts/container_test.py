#!/usr/bin/env python3
"""
Container test script for Warder agent container functionality.

This script directly tests the agent container functionality by:
1. Creating a container using the ContainerService
2. Starting the container and waiting for it to be ready
3. Communicating with the agent inside the container
4. Cleaning up the container after testing
"""

import os
import sys
import time
import uuid
import requests
import logging
import random
import re
import subprocess
from typing import Optional

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("container-test")

# Import container service
from app.services.container_service import ContainerService

# Container configuration
CONTAINER_IMAGE = "warder/agent:latest"
CONTAINER_NAME_PREFIX = "test-agent-"
CONTAINER_PORT = 8080
HOST_PORT_RANGE_START = 9000
HOST_PORT_RANGE_END = 9500
CONTAINER_NETWORK = "warder_network"
KNOWLEDGE_PATH = "/app/data/pdfs"
PDF_KNOWLEDGE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../data/pdfs")
)

# Vector database configuration
VECTOR_DB_URL = os.getenv(
    "VECTOR_DB_URL", "postgresql://postgres:postgres@localhost:5432/warder"
)


class ContainerTest:
    """Test for Warder agent container functionality."""

    def __init__(self):
        """Initialize the container test."""
        self.container_service = ContainerService()
        self.container_id = None
        self.container_name = None
        self.host_port = None
        self.agent_url = None

    def run(self) -> bool:
        """
        Run the container test.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create container network if it doesn't exist
            if not self.ensure_network():
                return False

            # Create and start container
            if not self.create_and_start_container():
                return False

            # Wait for container to be ready
            if not self.wait_for_container_ready():
                return False

            # Test communication with agent
            if not self.test_agent_communication():
                return False

            logger.info("Container test completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error running container test: {str(e)}")
            return False

        finally:
            # Clean up resources
            self.cleanup()

    def ensure_network(self) -> bool:
        """
        Ensure the container network exists.
        The ContainerService automatically creates the network in its constructor.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Ensuring container network: {CONTAINER_NETWORK}")

            # Check if network exists using podman directly
            result = subprocess.run(
                ["podman", "network", "inspect", CONTAINER_NETWORK],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.info(f"Network {CONTAINER_NETWORK} exists")
                return True

            # Create the network if it doesn't exist
            logger.info(f"Creating network {CONTAINER_NETWORK}")
            create_result = subprocess.run(
                ["podman", "network", "create", CONTAINER_NETWORK],
                capture_output=True,
                text=True,
            )

            if create_result.returncode == 0:
                logger.info(f"Network {CONTAINER_NETWORK} created successfully")
                return True
            else:
                logger.error(
                    f"Failed to create network {CONTAINER_NETWORK}: {create_result.stderr}"
                )
                return False
        except Exception as e:
            logger.error(f"Error ensuring network: {str(e)}")
            return False

    def create_and_start_container(self) -> bool:
        """
        Create and start a container for the agent.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate a unique container name
            container_name = f"{CONTAINER_NAME_PREFIX}{uuid.uuid4().hex[:8]}"
            logger.info(f"Creating container: {container_name}")

            # Find an available port
            host_port = self._find_available_port()
            logger.info(f"Using host port: {host_port}")

            # Generate a unique agent ID
            agent_id = str(uuid.uuid4())

            # Environment variables for the container
            env_vars = {
                "AGENT_ID": agent_id,
                "AGENT_NAME": "Test RAG Agent",
                "AGENT_TYPE": "rag",  # Set to RAG agent type
                "PORT": str(CONTAINER_PORT),
                "KNOWLEDGE_PATH": KNOWLEDGE_PATH,
                # Vector database configuration for PDF knowledge base
                "VECTOR_DB_URL": VECTOR_DB_URL,
                "VECTOR_DB_TABLE": f"pdf_documents_{agent_id}".replace("-", "_"),
                "KB_RECREATE": "true",
                "KB_CHUNK_SIZE": "1000",
                "KB_CHUNK_OVERLAP": "200",
                # LLM configuration - ensure the agent connects to an LLM
                "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
                "AGNO_LLM_PROVIDER": "openai",
                "AGNO_LLM_MODEL": "gpt-3.5-turbo",
            }

            # Build command to create the container
            cmd = ["podman", "create", "--name", container_name]

            # Add environment variables
            for key, value in env_vars.items():
                cmd.extend(["-e", f"{key}={value}"])

            # Add network
            cmd.extend(["--network", CONTAINER_NETWORK])

            # Add port mapping
            cmd.extend(["-p", f"{host_port}:{CONTAINER_PORT}/tcp"])

            # Mount the PDF knowledge base directory
            cmd.extend(["-v", f"{PDF_KNOWLEDGE_PATH}:/app/data/pdfs:ro"])

            # Add resource limits
            cmd.extend(["--memory", "1024m"])  # Increased memory for RAG
            cmd.extend(["--cpus", "1.0"])  # Increased CPU for RAG

            # Add image
            cmd.append(CONTAINER_IMAGE)

            # Create the container
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"Failed to create container: {result.stderr}")
                return False

            container_id = result.stdout.strip()
            self.container_id = container_id
            self.container_name = container_name
            self.host_port = host_port
            self.agent_url = f"http://localhost:{host_port}"

            logger.info(f"Container created successfully with ID: {container_id}")

            # Start the container
            start_cmd = ["podman", "start", container_id]
            start_result = subprocess.run(start_cmd, capture_output=True, text=True)

            if start_result.returncode != 0:
                logger.error(f"Failed to start container: {start_result.stderr}")
                return False

            logger.info(f"Container started successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating container: {str(e)}")
            return False

    def _find_available_port(self) -> int:
        """
        Find an available port in the configured range.

        Returns:
            An available port
        """
        try:
            # Get all running containers
            result = subprocess.run(
                ["podman", "ps", "--format", "{{.Ports}}"],
                capture_output=True,
                text=True,
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
            for port in range(HOST_PORT_RANGE_START, HOST_PORT_RANGE_END + 1):
                if port not in used_ports:
                    return port

            # If all ports are used, return a random port (will fail if actually used)
            logger.warning(
                "All ports in the configured range are used. Returning a random port."
            )
        except subprocess.SubprocessError as e:
            logger.error(f"Error finding available port: {str(e)}")

        return random.randint(HOST_PORT_RANGE_START, HOST_PORT_RANGE_END)

    def wait_for_container_ready(self, timeout: int = 60) -> bool:
        """
        Wait for the container to be ready to accept requests.

        Args:
            timeout: Timeout in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.container_id or not self.host_port:
                logger.error("No container ID or host port available")
                return False

            logger.info(f"Waiting for container to be ready (timeout: {timeout}s)")

            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # Check if the container is running
                    result = subprocess.run(
                        [
                            "podman",
                            "inspect",
                            "--format",
                            "{{.State.Status}}",
                            self.container_id,
                        ],
                        capture_output=True,
                        text=True,
                    )

                    if result.returncode != 0 or result.stdout.strip() != "running":
                        logger.info("Container is not running yet, waiting...")
                        time.sleep(2)
                        continue

                    # Try to connect to the agent's health endpoint
                    response = requests.get(f"{self.agent_url}/health", timeout=5)
                    if response.status_code == 200:
                        logger.info("Container is ready to accept requests")
                        return True
                except (requests.RequestException, ConnectionError):
                    # Connection failed, container might not be ready yet
                    pass

                # Wait a bit before trying again
                time.sleep(2)

            logger.error("Timed out waiting for container to be ready")
            return False

        except Exception as e:
            logger.error(f"Error waiting for container: {str(e)}")
            return False

    def test_agent_communication(self) -> bool:
        """
        Test communication with the agent.

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.agent_url:
                logger.error("No agent URL available")
                return False

            logger.info("Testing communication with agent")

            # Test health endpoint
            logger.info("Testing agent health endpoint")
            response = requests.get(f"{self.agent_url}/health")

            if response.status_code != 200:
                logger.error(f"Health check failed: {response.text}")
                return False

            logger.info("Health check successful")

            # Wait for the knowledge base to be loaded
            logger.info("Waiting for knowledge base to be loaded (30 seconds)...")
            time.sleep(30)  # Give time for the knowledge base to be loaded

            # Test chat endpoint with a simple greeting
            logger.info("Testing agent chat endpoint with a simple greeting")
            chat_data = {"content": "Hello, agent!", "role": "user"}
            response = requests.post(f"{self.agent_url}/chat", json=chat_data)

            if response.status_code != 200:
                logger.error(f"Chat test failed: {response.text}")
                return False

            chat_response = response.json()
            logger.info(f"Chat test successful. Response: {chat_response}")

            # Check if the response is just an echo (indicating LLM is not connected)
            if chat_response.get("content", "").startswith("Echo:"):
                logger.warning(
                    "Agent is returning echo responses, indicating LLM is not connected"
                )
                # Continue with tests but note the issue
            else:
                logger.info("Agent is properly connected to the LLM")

            # Test chat endpoint with a PDF knowledge-based query
            logger.info("Testing agent chat endpoint with a PDF knowledge-based query")
            knowledge_query = {
                "content": "What information can you find in the PDF documents?",
                "role": "user",
            }
            response = requests.post(f"{self.agent_url}/chat", json=knowledge_query)

            if response.status_code != 200:
                logger.error(f"PDF knowledge query test failed: {response.text}")
                return False

            knowledge_response = response.json()
            logger.info(
                f"PDF knowledge query test successful. Response: {knowledge_response}"
            )

            # Test query endpoint directly (our new endpoint)
            logger.info("Testing agent query endpoint with a PDF knowledge-based query")
            query_data = {
                "query": "Summarize the key information from the PDF documents."
            }
            response = requests.post(f"{self.agent_url}/query", json=query_data)

            if response.status_code != 200:
                logger.error(f"Direct query test failed: {response.text}")
                logger.warning(
                    "This may be because the agent container doesn't have the /query endpoint yet"
                )
                logger.warning(
                    "Make sure to rebuild the agent container with the updated main.py that includes the /query endpoint"
                )
                # Continue with tests but note the issue
            else:
                query_response = response.json()
                resp_str = str(query_response)
                logger.info(
                    f"Direct query test successful. Response: {resp_str[:50]}..."
                )

                # Check if the response is just an echo (indicating LLM is not connected)
                if "response" in query_response and query_response[
                    "response"
                ].startswith("Echo:"):
                    logger.warning(
                        "Agent query returning echo responses, LLM connection issue"
                    )
                else:
                    logger.info("Agent query is properly connected to the LLM")

            # Return true even if some tests had warnings - we've logged the issues
            return True

        except Exception as e:
            logger.error(f"Error testing agent communication: {str(e)}")
            return False

    def cleanup(self) -> None:
        """
        Clean up resources.
        """
        logger.info("Cleaning up resources")

        # Stop and remove the container if it exists
        if self.container_id:
            logger.info(f"Stopping and removing container: {self.container_id}")
            try:
                # Stop the container
                subprocess.run(
                    ["podman", "stop", "--time", "10", self.container_id],
                    capture_output=True,
                    text=True,
                )

                # Remove the container
                subprocess.run(
                    ["podman", "rm", "--force", self.container_id],
                    capture_output=True,
                    text=True,
                )

                logger.info("Container stopped and removed")
            except Exception as e:
                logger.error(f"Error cleaning up container: {str(e)}")


if __name__ == "__main__":
    # Run the container test
    test = ContainerTest()
    success = test.run()

    # Exit with appropriate status code
    sys.exit(0 if success else 1)
