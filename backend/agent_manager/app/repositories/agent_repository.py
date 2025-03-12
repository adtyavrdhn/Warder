"""
Repository for agent-related database operations.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate, AgentStatus

# Configure logger
logger = logging.getLogger(__name__)


class AgentRepository:
    """Repository for agent-related database operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the repository with a database session."""
        self.db = db_session

    async def create(self, agent_data: AgentCreate) -> Agent:
        """
        Create a new agent in the database.

        Args:
            agent_data: The agent data to create

        Returns:
            The created agent

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            logger.info(f"Creating agent with name: {agent_data.name}")

            # Create agent object
            agent = Agent(
                id=uuid4(),
                name=agent_data.name,
                description=agent_data.description,
                type=agent_data.type,
                status=AgentStatus.CREATING,
                config={
                    "knowledge_base": (
                        agent_data.knowledge_base.dict()
                        if agent_data.knowledge_base
                        else None
                    ),
                    **agent_data.config,
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            # Add to database
            self.db.add(agent)
            await self.db.commit()
            await self.db.refresh(agent)

            logger.info(f"Agent created successfully with ID: {agent.id}")
            return agent

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating agent: {str(e)}")
            raise

    async def get_by_id(self, agent_id: UUID) -> Optional[Agent]:
        """
        Get an agent by ID.

        Args:
            agent_id: The agent ID

        Returns:
            The agent if found, None otherwise

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            logger.debug(f"Getting agent with ID: {agent_id}")

            query = select(Agent).where(Agent.id == agent_id)
            result = await self.db.execute(query)
            agent = result.scalars().first()

            if agent:
                logger.debug(f"Found agent with ID: {agent_id}")
            else:
                logger.debug(f"Agent with ID {agent_id} not found")

            return agent

        except SQLAlchemyError as e:
            logger.error(f"Error getting agent by ID {agent_id}: {str(e)}")
            raise

    async def get_all(self) -> List[Agent]:
        """
        Get all agents.

        Returns:
            List of all agents

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            logger.debug("Getting all agents")

            query = select(Agent)
            result = await self.db.execute(query)
            agents = result.scalars().all()

            logger.debug(f"Found {len(agents)} agents")
            return agents

        except SQLAlchemyError as e:
            logger.error(f"Error getting all agents: {str(e)}")
            raise

    async def update(self, agent_id: UUID, agent_data: AgentUpdate) -> Optional[Agent]:
        """
        Update an agent.

        Args:
            agent_id: The agent ID
            agent_data: The agent data to update

        Returns:
            The updated agent if found, None otherwise

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            logger.info(f"Updating agent with ID: {agent_id}")

            # Get current agent
            agent = await self.get_by_id(agent_id)
            if not agent:
                logger.warning(f"Agent with ID {agent_id} not found for update")
                return None

            # Prepare update data
            update_data = agent_data.dict(exclude_unset=True)
            if "config" in update_data and update_data["config"]:
                # Merge configs instead of replacing
                update_data["config"] = {**agent.config, **update_data["config"]}

            update_data["updated_at"] = datetime.utcnow()

            # Update agent
            query = (
                update(Agent)
                .where(Agent.id == agent_id)
                .values(**update_data)
                .returning(Agent)
            )
            result = await self.db.execute(query)
            updated_agent = result.scalars().first()

            await self.db.commit()

            logger.info(f"Agent updated successfully with ID: {agent_id}")
            return updated_agent

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating agent with ID {agent_id}: {str(e)}")
            raise

    async def delete(self, agent_id: UUID) -> bool:
        """
        Delete an agent.

        Args:
            agent_id: The agent ID

        Returns:
            True if deleted, False otherwise

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            logger.info(f"Deleting agent with ID: {agent_id}")

            # Check if agent exists
            agent = await self.get_by_id(agent_id)
            if not agent:
                logger.warning(f"Agent with ID {agent_id} not found for deletion")
                return False

            # Delete agent
            query = delete(Agent).where(Agent.id == agent_id)
            await self.db.execute(query)
            await self.db.commit()

            logger.info(f"Agent deleted successfully with ID: {agent_id}")
            return True

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error deleting agent with ID {agent_id}: {str(e)}")
            raise

    async def update_status(
        self, agent_id: UUID, status: AgentStatus
    ) -> Optional[Agent]:
        """
        Update an agent's status.

        Args:
            agent_id: The agent ID
            status: The new status

        Returns:
            The updated agent if found, None otherwise

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            logger.info(f"Updating status of agent with ID {agent_id} to {status}")

            # Update agent status
            query = (
                update(Agent)
                .where(Agent.id == agent_id)
                .values(status=status, updated_at=datetime.utcnow())
                .returning(Agent)
            )
            result = await self.db.execute(query)
            updated_agent = result.scalars().first()

            if not updated_agent:
                logger.warning(f"Agent with ID {agent_id} not found for status update")
                return None

            await self.db.commit()

            logger.info(
                f"Agent status updated successfully to {status} for ID: {agent_id}"
            )
            return updated_agent

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(
                f"Error updating status for agent with ID {agent_id}: {str(e)}"
            )
            raise
