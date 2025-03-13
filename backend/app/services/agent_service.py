"""
Agent service for the Warder application.
"""

import logging
import os
import shutil
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
import httpx

# from sqlalchemy.exc import SQLAlchemyError

from app.models.agent import Agent, AgentStatus, AgentType, ContainerStatus
from app.schemas.agent import AgentCreate, AgentUpdate
from app.services.container_service import ContainerService

# Try to import Agno for RAG functionality, but handle gracefully if not available
from agno.knowledge.pdf import PDFKnowledgeBase, PDFReader
from agno.vectordb.pgvector import PgVector
from agno.agent import Agent as AgnoAgent


# Configure logger
logger = logging.getLogger(__name__)

# Knowledge base directory
KNOWLEDGE_BASE_DIR = os.getenv("KNOWLEDGE_BASE_DIR", "data/knowledge_base")
VECTOR_DB_URL = os.getenv(
    "VECTOR_DB_URL", "postgresql://postgres:postgres@localhost:5432/warder"
)


class AgentService:
    """Service for agent-related operations."""

    # Class-level dictionary to store agent instances
    _agent_instances = {}

    def __init__(self, db: AsyncSession):
        """Initialize the service with a database session."""
        self.db = db
        self.container_service = ContainerService()

    async def create_agent(self, agent_data: AgentCreate) -> Agent:
        """
        Create a new agent.

        This method performs the following steps:
        1. Create the agent record in the database
        2. Create the agent's knowledge base directory if needed
        3. Initialize the agent with Agno if it's a RAG agent
        4. Create a container for the agent
        5. Update the agent status

        Args:
            agent_data: The agent data to create

        Returns:
            The created agent

        Raises:
            Exception: If there's an error creating the agent
        """
        try:
            logger.info(f"Creating agent with name: {agent_data.name}")

            # Create agent object
            agent = Agent(
                name=agent_data.name,
                description=agent_data.description,
                type=agent_data.type,
                status=AgentStatus.CREATING,
                config={
                    "knowledge_base": (
                        agent_data.knowledge_base.model_dump()
                        if agent_data.knowledge_base
                        else None
                    ),
                    **agent_data.config,
                },
                container_status=ContainerStatus.NONE,
                container_config=(
                    agent_data.container_config.model_dump()
                    if agent_data.container_config
                    else {}
                ),
                user_id=agent_data.user_id,
            )

            # Add to database
            self.db.add(agent)
            await self.db.commit()
            await self.db.refresh(agent)

            # Create agent's knowledge base directory if needed
            kb_dir = self._get_agent_kb_dir(agent.id)
            os.makedirs(kb_dir, exist_ok=True)
            logger.info(f"Created knowledge base directory: {kb_dir}")

            # Initialize agent with Agno if it's a RAG agent
            if agent_data.type == AgentType.RAG:
                try:
                    # Update agent status to deploying
                    agent.status = AgentStatus.DEPLOYING
                    await self.db.commit()

                    # Initialize knowledge base if Agno is available
                    # Get knowledge base config
                    kb_config = agent_data.knowledge_base or {}

                    # Initialize knowledge base
                    await self._initialize_rag_agent(
                        agent_id=agent.id,
                        kb_dir=kb_dir,
                        recreate=kb_config.recreate if kb_config else False,
                        chunk_size=kb_config.chunk_size if kb_config else 1000,
                        chunk_overlap=kb_config.chunk_overlap if kb_config else 200,
                    )

                    # Update agent status to active
                    agent.status = AgentStatus.ACTIVE
                    await self.db.commit()
                    logger.info(f"Agent {agent.id} initialized successfully")

                except Exception as e:
                    # Update agent status to failed
                    agent.status = AgentStatus.FAILED
                    await self.db.commit()
                    logger.error(f"Error initializing agent {agent.id}: {str(e)}")
                    raise
            else:
                # For non-RAG agents, just mark as active
                agent.status = AgentStatus.ACTIVE
                await self.db.commit()

            # Create container for the agent
            logger.info(f"Creating container for agent {agent.id}")
            container_created = await self.create_agent_container(agent.id)
            if not container_created:
                logger.warning(f"Failed to create container for agent {agent.id}")
                # We don't raise an exception here as the agent itself was created successfully
                # The container can be created later if needed

            # Refresh agent data
            await self.db.refresh(agent)
            return agent

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating agent: {str(e)}")
            raise

    async def get_agent(self, agent_id: UUID) -> Optional[Agent]:
        """
        Get an agent by ID.

        Args:
            agent_id: The agent ID

        Returns:
            The agent if found, None otherwise
        """
        try:
            logger.debug(f"Getting agent with ID: {agent_id}")
            query = select(Agent).where(Agent.id == agent_id)
            result = await self.db.execute(query)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting agent {agent_id}: {str(e)}")
            raise

    async def get_all_agents(self) -> List[Agent]:
        """
        Get all agents.

        Returns:
            List of all agents
        """
        try:
            logger.debug("Getting all agents")
            query = select(Agent)
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting all agents: {str(e)}")
            raise

    async def update_agent(
        self, agent_id: UUID, agent_data: AgentUpdate
    ) -> Optional[Agent]:
        """
        Update an agent.

        Args:
            agent_id: The agent ID
            agent_data: The agent data to update

        Returns:
            The updated agent if found, None otherwise
        """
        try:
            logger.info(f"Updating agent with ID: {agent_id}")

            # Get current agent
            agent = await self.get_agent(agent_id)
            if not agent:
                logger.warning(f"Agent with ID {agent_id} not found for update")
                return None

            # Update agent attributes
            update_data = agent_data.model_dump(exclude_unset=True)

            if "config" in update_data and update_data["config"]:
                # Merge configs instead of replacing
                agent.config = {**agent.config, **update_data["config"]}
                del update_data["config"]

            # Update other fields
            for key, value in update_data.items():
                setattr(agent, key, value)

            agent.updated_at = None  # Will trigger the onupdate default

            # Commit changes
            await self.db.commit()
            await self.db.refresh(agent)

            logger.info(f"Agent updated successfully with ID: {agent_id}")
            return agent

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating agent with ID {agent_id}: {str(e)}")
            raise

    async def delete_agent(self, agent_id: UUID) -> bool:
        """
        Delete an agent.

        This method performs the following steps:
        1. Delete the agent's container if it exists
        2. Delete the agent's knowledge base directory
        3. Delete the agent record from the database

        Args:
            agent_id: The agent ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            logger.info(f"Deleting agent with ID: {agent_id}")

            # Get agent to check if it exists
            query = select(Agent).where(Agent.id == agent_id)
            result = await self.db.execute(query)
            agent = result.scalar_one_or_none()

            if not agent:
                logger.warning(f"Agent with ID {agent_id} not found for deletion")
                return False

            # Delete agent's container if it exists
            if agent.container_id:
                success, message = await self.container_service.delete_container(
                    agent.container_id
                )
                if success:
                    logger.info(
                        f"Deleted container for agent {agent_id}: {agent.container_id}"
                    )
                else:
                    logger.warning(
                        f"Failed to delete container for agent {agent_id}: {message}"
                    )

            # Delete agent's knowledge base directory
            kb_dir = self._get_agent_kb_dir(agent_id)
            if os.path.exists(kb_dir):
                shutil.rmtree(kb_dir)
                logger.info(f"Deleted knowledge base directory: {kb_dir}")

            # Delete agent from database
            self.db.delete(agent)
            await self.db.commit()

            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting agent {agent_id}: {str(e)}")
            return False

    def _get_agent_kb_dir(self, agent_id: UUID) -> str:
        """
        Get the agent's knowledge base directory.

        Args:
            agent_id: The agent ID

        Returns:
            The path to the agent's knowledge base directory
        """
        return os.path.join(KNOWLEDGE_BASE_DIR, str(agent_id))

    async def _initialize_rag_agent(
        self,
        agent_id: UUID,
        kb_dir: str,
        recreate: bool = False,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """
        Initialize a RAG agent with Agno.

        Args:
            agent_id: The agent ID
            kb_dir: The knowledge base directory
            recreate: Whether to recreate the knowledge base
            chunk_size: The chunk size for text splitting
            chunk_overlap: The chunk overlap for text splitting

        Raises:
            Exception: If there's an error initializing the agent
        """
        try:
            logger.info(f"Initializing RAG agent with ID: {agent_id}")

            # Initialize vector store with proper table name for the agent
            # Use only the first 8 characters of the UUID to avoid exceeding PostgreSQL's 63-character limit
            short_id = str(agent_id).replace("-", "")[:8]
            table_name = f"pdf_docs_{short_id}"

            # Initialize PDF knowledge base using the correct pattern
            knowledge_base = PDFKnowledgeBase(
                path=kb_dir,  # Use the agent's knowledge base directory
                vector_db=PgVector(
                    table_name=table_name,
                    db_url=VECTOR_DB_URL,
                ),
                reader=PDFReader(chunk=True, chunk_size=chunk_size),
            )

            # Load the knowledge base
            knowledge_base.load(recreate=recreate)

            # Initialize agent with the knowledge base
            agent = AgnoAgent(
                knowledge=knowledge_base,
                search_knowledge=True,
            )

            # Store the agent instance in the class dictionary
            AgentService._agent_instances[str(agent_id)] = agent

            logger.info(f"RAG agent initialized successfully with ID: {agent_id}")

        except Exception as e:
            logger.error(f"Error initializing RAG agent {agent_id}: {str(e)}")
            raise

    async def get_agent_instance(self, agent_id: UUID) -> Optional[AgnoAgent]:
        """
        Get the agent instance for the given agent ID.

        Args:
            agent_id: The agent ID

        Returns:
            The agent instance if found, None otherwise
        """
        agent_id_str = str(agent_id)

        # Check if agent instance exists in memory
        if agent_id_str in AgentService._agent_instances:
            logger.info(f"Found agent instance in memory for agent {agent_id}")
            return AgentService._agent_instances[agent_id_str]

        # If not in memory, try to initialize it
        agent_db = await self.get_agent(agent_id)
        if not agent_db:
            logger.warning(f"Agent with ID {agent_id} not found")
            return None

        # Only initialize if it's a RAG agent
        if agent_db.type.value == "rag":
            # Get the agent's knowledge base directory
            kb_dir = self._get_agent_kb_dir(agent_id)

            # Get knowledge base config from agent config
            kb_config = agent_db.config.get("knowledge_base", {})

            # Initialize the agent
            try:
                await self._initialize_rag_agent(
                    agent_id=agent_id,
                    kb_dir=kb_dir,
                    recreate=kb_config.get("recreate", False),
                    chunk_size=kb_config.get("chunk_size", 1000),
                    chunk_overlap=kb_config.get("chunk_overlap", 200),
                )

                # Return the initialized agent
                return AgentService._agent_instances.get(agent_id_str)
            except Exception as e:
                logger.error(
                    f"Error initializing agent instance for {agent_id}: {str(e)}"
                )
                return None
        else:
            logger.warning(f"Agent {agent_id} is not a RAG agent")
            return None

    async def get_agent_response(self, agent_id: UUID, query: str) -> Optional[str]:
        """
        Get a response from the agent for the given query by communicating with its container.

        Args:
            agent_id: The agent ID
            query: The query to send to the agent

        Returns:
            The agent's response if successful, None otherwise
        """
        try:
            # Get agent from database
            agent = await self.get_agent(agent_id)
            if not agent:
                logger.warning(f"Agent with ID {agent_id} not found")
                return None

            # Check if agent has a container
            if not agent.container_id:
                logger.warning(f"Agent {agent_id} does not have a container")
                return None

            # Check if container is running and start it if needed
            logger.info(f"Agent container status: {agent.container_status}")
            if agent.container_status != ContainerStatus.RUNNING:
                logger.info(f"Starting container for agent {agent_id}")
                success = await self.start_agent_container(agent_id)
                if not success:
                    logger.error(f"Failed to start container for agent {agent_id}")
                    return None

                # Refresh agent data
                agent = await self.get_agent(agent_id)
                logger.info(f"Updated agent container status: {agent.container_status}")

            # Get container port mapping
            container_status = await self.container_service.get_container_status(
                agent.container_id
            )
            if not container_status or container_status != "running":
                logger.error(f"Container for agent {agent_id} is not running")
                return None

            # Get container port mapping
            port_mapping = await self._get_container_port(agent.container_id)
            if not port_mapping:
                logger.error(
                    f"Failed to get port mapping for container {agent.container_id}"
                )
                return None

            # Prepare request to container
            # Try /chat endpoint first
            url = f"http://localhost:{port_mapping}/chat"
            payload = {"content": query}

            logger.info(f"Sending request to agent container at URL: {url}")
            logger.info(f"Request payload: {payload}")

            # Send request to container
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    logger.info(f"Sending POST request to {url}")
                    try:
                        response = await client.post(url, json=payload)
                        logger.info(f"Response status code: {response.status_code}")
                        response.raise_for_status()
                        data = response.json()
                        logger.info(f"Response data: {data}")

                        # Check if the response contains an error
                        if "error" in data:
                            logger.error(f"Agent returned an error: {data['error']}")
                            return None

                        # The /chat endpoint returns a Response object with 'content' field
                        if "content" in data:
                            return data.get("content")

                        # Fallback to the old response format if content is not found
                        return data.get("response")
                    except (httpx.HTTPStatusError, httpx.RequestError) as e:
                        # If /chat endpoint fails, try /query endpoint
                        logger.warning(
                            f"Error with /chat endpoint: {str(e)}. Trying /query endpoint..."
                        )
                        query_url = f"http://localhost:{port_mapping}/query"
                        query_payload = {"query": query}

                        logger.info(
                            f"Sending request to agent container at URL: {query_url}"
                        )
                        logger.info(f"Request payload: {query_payload}")

                        query_response = await client.post(
                            query_url, json=query_payload
                        )
                        logger.info(
                            f"Query response status code: {query_response.status_code}"
                        )
                        query_response.raise_for_status()
                        query_data = query_response.json()
                        logger.info(f"Query response data: {query_data}")

                        # Check if the response contains an error
                        if "error" in query_data:
                            logger.error(
                                f"Agent returned an error: {query_data['error']}"
                            )
                            return None

                        # The /query endpoint returns a response field
                        return query_data.get("response")
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
                )
                return None
            except httpx.RequestError as e:
                logger.error(f"Request error occurred: {str(e)}")
                return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error communicating with agent {agent_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error getting response from agent {agent_id}: {str(e)}")
            return None

    async def create_agent_container(self, agent_id: UUID) -> bool:
        """
        Create a container for the agent.

        Args:
            agent_id: The ID of the agent to create a container for

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Creating container for agent: {agent_id}")

            # Get agent
            agent = await self.get_agent(agent_id)
            if not agent:
                logger.warning(
                    f"Agent with ID {agent_id} not found for creating container"
                )
                return False

            # Check if agent already has a container
            if agent.container_id:
                logger.warning(f"Agent {agent_id} already has a container")
                return True

            # Create the container
            return await self._create_agent_container(agent)

        except Exception as e:
            logger.error(f"Error creating container for agent {agent_id}: {str(e)}")
            return False

    async def _create_agent_container(self, agent: Agent) -> bool:
        """
        Create a container for the agent.

        Args:
            agent: The agent to create a container for

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Creating container for agent: {agent.id}")

            # Create container
            success, result = await self.container_service.create_container(agent)

            if not success:
                logger.error(
                    f"Failed to create container for agent {agent.id}: {result}"
                )
                agent.container_status = ContainerStatus.FAILED
                await self.db.commit()
                return False

            # Update agent with container info
            agent.container_id = result
            agent.container_status = ContainerStatus.STOPPED
            await self.db.commit()

            # Start container if auto_start is enabled
            container_config = agent.container_config or {}
            if container_config.get("auto_start", True):
                await self.start_agent_container(agent.id)

            return True

        except Exception as e:
            logger.error(f"Error creating container for agent {agent.id}: {str(e)}")
            agent.container_status = ContainerStatus.FAILED
            await self.db.commit()
            return False

    async def start_agent_container(self, agent_id: UUID) -> bool:
        """
        Start the agent's container.

        Args:
            agent_id: The agent ID

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting container for agent: {agent_id}")

            # Get agent
            query = select(Agent).where(Agent.id == agent_id)
            result = await self.db.execute(query)
            agent = result.scalar_one_or_none()

            if not agent:
                logger.warning(
                    f"Agent with ID {agent_id} not found for starting container"
                )
                return False

            # Check if agent has a container
            if not agent.container_id:
                logger.warning(f"Agent {agent_id} does not have a container")
                return False

            # Start container
            success, message = await self.container_service.start_container(
                agent.container_id
            )

            if not success:
                logger.error(
                    f"Failed to start container for agent {agent_id}: {message}"
                )
                agent.container_status = ContainerStatus.FAILED
                await self.db.commit()
                return False

            # Update agent container status
            agent.container_status = ContainerStatus.RUNNING
            await self.db.commit()

            return True

        except Exception as e:
            logger.error(f"Error starting container for agent {agent_id}: {str(e)}")
            return False

    async def stop_agent_container(self, agent_id: UUID) -> bool:
        """
        Stop the agent's container.

        Args:
            agent_id: The agent ID

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Stopping container for agent: {agent_id}")

            # Get agent
            query = select(Agent).where(Agent.id == agent_id)
            result = await self.db.execute(query)
            agent = result.scalar_one_or_none()

            if not agent:
                logger.warning(
                    f"Agent with ID {agent_id} not found for stopping container"
                )
                return False

            # Check if agent has a container
            if not agent.container_id:
                logger.warning(f"Agent {agent_id} does not have a container")
                return False

            # Stop container
            success, message = await self.container_service.stop_container(
                agent.container_id
            )

            if not success:
                logger.error(
                    f"Failed to stop container for agent {agent_id}: {message}"
                )
                return False

            # Update agent container status
            agent.container_status = ContainerStatus.STOPPED
            await self.db.commit()

            return True

        except Exception as e:
            logger.error(f"Error stopping container for agent {agent_id}: {str(e)}")
            return False

    async def get_agent_container_logs(
        self, agent_id: UUID, lines: int = 100
    ) -> Optional[str]:
        """
        Get the logs of the agent's container.

        Args:
            agent_id: The agent ID
            lines: Number of lines to retrieve

        Returns:
            The container logs if found, None otherwise
        """
        try:
            logger.info(f"Getting logs for agent container: {agent_id}")

            # Get agent
            query = select(Agent).where(Agent.id == agent_id)
            result = await self.db.execute(query)
            agent = result.scalar_one_or_none()

            if not agent:
                logger.warning(f"Agent with ID {agent_id} not found for getting logs")
                return None

            # Check if agent has a container
            if not agent.container_id:
                logger.warning(f"Agent {agent_id} does not have a container")
                return None

            # Get container logs
            logs = await self.container_service.get_container_logs(
                agent.container_id, lines
            )

            return logs

        except Exception as e:
            logger.error(f"Error getting logs for agent {agent_id}: {str(e)}")
            return None

    async def _get_container_port(self, container_id: str) -> Optional[int]:
        """
        Get the port mapping for a container.

        Args:
            container_id: The container ID

        Returns:
            The host port mapped to the container's port 8000 if found, None otherwise
        """
        try:
            # Get container information using the container service
            success, info = await self.container_service.inspect_container(container_id)
            if not success or not info:
                logger.warning(f"Failed to inspect container {container_id}")
                return None

            # Parse port mappings from container info
            # The format is typically: {'8080/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '9123'}]}
            ports = info.get("NetworkSettings", {}).get("Ports", {})
            container_port = "8080/tcp"  # The port exposed by the agent container

            if container_port in ports and ports[container_port]:
                mapping = ports[container_port][0]
                if "HostPort" in mapping:
                    return int(mapping["HostPort"])

            logger.warning(f"No port mapping found for container {container_id}")
            return None

        except Exception as e:
            logger.error(
                f"Error getting port mapping for container {container_id}: {str(e)}"
            )
            return None

    async def get_agent_container_stats(
        self, agent_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get the stats of the agent's container.

        Args:
            agent_id: The agent ID

        Returns:
            The container stats if found, None otherwise
        """
        try:
            logger.info(f"Getting stats for agent container: {agent_id}")

            # Get agent
            query = select(Agent).where(Agent.id == agent_id)
            result = await self.db.execute(query)
            agent = result.scalar_one_or_none()

            if not agent:
                logger.warning(f"Agent with ID {agent_id} not found for getting stats")
                return None

            # Check if agent has a container
            if not agent.container_id:
                logger.warning(f"Agent {agent_id} does not have a container")
                return None

            # Get container stats
            stats = await self.container_service.get_container_stats(agent.container_id)

            return stats

        except Exception as e:
            logger.error(f"Error getting stats for agent {agent_id}: {str(e)}")
            return None
