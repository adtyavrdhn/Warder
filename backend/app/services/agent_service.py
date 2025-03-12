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

# from sqlalchemy.exc import SQLAlchemyError

from app.models.agent import Agent, AgentStatus, AgentType, ContainerStatus
from app.schemas.agent import AgentCreate, AgentUpdate
from app.services.container_service import ContainerService

# Try to import Agno for RAG functionality, but handle gracefully if not available
try:
    from agno.knowledge.pdf import PDFKnowledgeBase, PDFReader
    from agno.vectordb.pgvector import PgVector
    from agno.agent import Agent as AgnoAgent

    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    logging.warning("Agno library not available. RAG functionality will be limited.")

# Configure logger
logger = logging.getLogger(__name__)

# Knowledge base directory
KNOWLEDGE_BASE_DIR = os.getenv("KNOWLEDGE_BASE_DIR", "data/knowledge_base")
VECTOR_DB_URL = os.getenv(
    "VECTOR_DB_URL", "postgresql://postgres:postgres@localhost:5432/warder"
)


class AgentService:
    """Service for agent-related operations."""

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
        4. Update the agent status

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
                    if AGNO_AVAILABLE:
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
        if not AGNO_AVAILABLE:
            logger.warning(
                "Agno library not available. Skipping RAG agent initialization."
            )
            return

        try:
            logger.info(f"Initializing RAG agent with ID: {agent_id}")

            # Initialize vector store with proper table name for the agent
            table_name = f"pdf_documents_{agent_id}".replace("-", "_")

            # Initialize PDF knowledge base using the correct pattern
            knowledge_base = PDFKnowledgeBase(
                path=kb_dir,  # Use the agent's knowledge base directory
                vector_db=PgVector(
                    table_name=table_name,
                    db_url=VECTOR_DB_URL,
                ),
                reader=PDFReader(
                    chunk=True, chunk_size=chunk_size, chunk_overlap=chunk_overlap
                ),
            )

            # Load the knowledge base
            knowledge_base.load(recreate=recreate)

            # Initialize agent with the knowledge base
            agent = AgnoAgent(
                knowledge=knowledge_base,
                search_knowledge=True,
            )

            logger.info(f"RAG agent initialized successfully with ID: {agent_id}")

        except Exception as e:
            logger.error(f"Error initializing RAG agent {agent_id}: {str(e)}")
            raise

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
