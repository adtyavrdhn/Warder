"""
Agent service for the Warder application.
"""

import logging
import os
import shutil
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

# from sqlalchemy.exc import SQLAlchemyError

from app.models.agent import Agent, AgentStatus, AgentType
from app.schemas.agent import AgentCreate, AgentUpdate

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
        1. Delete the agent's knowledge base directory
        2. Delete the agent record from the database

        Args:
            agent_id: The agent ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            logger.info(f"Deleting agent with ID: {agent_id}")

            # Get agent to check if it exists
            agent = await self.get_agent(agent_id)
            if not agent:
                logger.warning(f"Agent with ID {agent_id} not found for deletion")
                return False

            # Delete agent's knowledge base directory
            kb_dir = self._get_agent_kb_dir(agent_id)
            if os.path.exists(kb_dir):
                shutil.rmtree(kb_dir)
                logger.info(f"Deleted knowledge base directory: {kb_dir}")

            # Delete agent from database
            await self.db.delete(agent)
            await self.db.commit()

            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting agent {agent_id}: {str(e)}")
            raise

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

            # Initialize vector store
            vector_store = PgVector(
                connection_string=VECTOR_DB_URL,
                collection_name=f"agent_{agent_id}",
                recreate_collection=recreate,
            )

            # Initialize knowledge base
            knowledge_base = PDFKnowledgeBase(
                pdf_reader=PDFReader(),
                vector_store=vector_store,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            # Initialize agent
            agent = AgnoAgent(
                knowledge_base=knowledge_base,
            )

            logger.info(f"RAG agent initialized successfully with ID: {agent_id}")

        except Exception as e:
            logger.error(f"Error initializing RAG agent {agent_id}: {str(e)}")
            raise
