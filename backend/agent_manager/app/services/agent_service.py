"""
Service for agent-related operations.
"""

import logging
import os
import shutil
from typing import List, Optional, Dict, Any
from uuid import UUID

from agno.knowledge.pdf import PDFKnowledgeBase, PDFReader
from agno.vectordb.pgvector import PgVector
from agno.agent import Agent as AgnoAgent

from app.models.agent import Agent
from app.repositories.agent_repository import AgentRepository
from app.schemas.agent import AgentCreate, AgentUpdate, AgentStatus, AgentType
from config.db import VECTOR_DB_URL, KNOWLEDGE_BASE_DIR

# Configure logger
logger = logging.getLogger(__name__)


class AgentService:
    """Service for agent-related operations."""

    def __init__(self, repository: AgentRepository):
        """Initialize the service with a repository."""
        self.repository = repository

    async def create_agent(self, agent_data: AgentCreate) -> Agent:
        """
        Create a new agent.

        This method performs the following steps:
        1. Create the agent record in the database
        2. Create the agent's knowledge base directory if needed
        3. Initialize the agent with Agno
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

            # Step 1: Create agent record in database
            agent = await self.repository.create(agent_data)

            # Step 2: Create agent's knowledge base directory if needed
            kb_dir = self._get_agent_kb_dir(agent.id)
            os.makedirs(kb_dir, exist_ok=True)
            logger.info(f"Created knowledge base directory: {kb_dir}")

            # Step 3: Initialize agent with Agno
            if agent_data.type == AgentType.RAG:
                try:
                    # Update agent status to deploying
                    await self.repository.update_status(agent.id, AgentStatus.DEPLOYING)

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
                    await self.repository.update_status(agent.id, AgentStatus.ACTIVE)
                    logger.info(f"Agent {agent.id} initialized successfully")

                except Exception as e:
                    # Update agent status to failed
                    await self.repository.update_status(agent.id, AgentStatus.FAILED)
                    logger.error(f"Error initializing agent {agent.id}: {str(e)}")
                    raise
            else:
                # For non-RAG agents, just mark as active
                await self.repository.update_status(agent.id, AgentStatus.ACTIVE)

            # Refresh agent data
            agent = await self.repository.get_by_id(agent.id)
            return agent

        except Exception as e:
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
            return await self.repository.get_by_id(agent_id)
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
            return await self.repository.get_all()
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
            return await self.repository.update(agent_id, agent_data)
        except Exception as e:
            logger.error(f"Error updating agent {agent_id}: {str(e)}")
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
            agent = await self.repository.get_by_id(agent_id)
            if not agent:
                logger.warning(f"Agent with ID {agent_id} not found for deletion")
                return False

            # Delete agent's knowledge base directory
            kb_dir = self._get_agent_kb_dir(agent_id)
            if os.path.exists(kb_dir):
                shutil.rmtree(kb_dir)
                logger.info(f"Deleted knowledge base directory: {kb_dir}")

            # Delete agent from database
            return await self.repository.delete(agent_id)

        except Exception as e:
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
    ) -> None:
        """
        Initialize a RAG agent with Agno.

        Args:
            agent_id: The agent ID
            kb_dir: The knowledge base directory
            recreate: Whether to recreate the knowledge base
            chunk_size: The chunk size for document splitting
            chunk_overlap: The chunk overlap for document splitting

        Raises:
            Exception: If there's an error initializing the agent
        """
        try:
            logger.info(
                f"Initializing RAG agent {agent_id} with knowledge base directory: {kb_dir}"
            )

            # Create table name based on agent ID to ensure uniqueness
            table_name = f"agent_{str(agent_id).replace('-', '_')}"

            # Initialize knowledge base
            knowledge_base = PDFKnowledgeBase(
                path=kb_dir,
                vector_db=PgVector(
                    table_name=table_name,
                    db_url=VECTOR_DB_URL,
                ),
                reader=PDFReader(
                    chunk=True, chunk_size=chunk_size, chunk_overlap=chunk_overlap
                ),
            )

            # Load knowledge base
            knowledge_base.load(recreate=recreate)

            # Initialize agent
            agent = AgnoAgent(
                knowledge=knowledge_base,
                search_knowledge=True,
            )

            logger.info(f"RAG agent {agent_id} initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing RAG agent {agent_id}: {str(e)}")
            raise
