"""
Router for agent-related endpoints.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse
from app.services.agent_service import AgentService
from app.utils.database import get_db

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate, db: AsyncSession = Depends(get_db)
) -> AgentResponse:
    """
    Create a new agent.

    This endpoint creates a new agent with the specified configuration.
    If the agent type is RAG, it will also initialize the knowledge base.

    Args:
        agent_data: The agent data to create
        db: Database session

    Returns:
        The created agent

    Raises:
        HTTPException: If there's an error creating the agent
    """
    try:
        logger.info(f"Received request to create agent: {agent_data.name}")

        # Create agent service
        service = AgentService(db)

        # Create agent
        agent = await service.create_agent(agent_data)

        # Convert to response model
        return AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            type=agent.type,
            status=agent.status,
            config=agent.config,
            created_at=agent.created_at.isoformat(),
            updated_at=agent.updated_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating agent: {str(e)}",
        )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID, db: AsyncSession = Depends(get_db)
) -> AgentResponse:
    """
    Get an agent by ID.

    Args:
        agent_id: The agent ID
        db: Database session

    Returns:
        The agent

    Raises:
        HTTPException: If the agent is not found
    """
    try:
        logger.info(f"Received request to get agent: {agent_id}")

        # Create agent service
        service = AgentService(db)

        # Get agent
        agent = await service.get_agent(agent_id)

        # Check if agent exists
        if not agent:
            logger.warning(f"Agent with ID {agent_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found",
            )

        # Convert to response model
        return AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            type=agent.type,
            status=agent.status,
            config=agent.config,
            created_at=agent.created_at.isoformat(),
            updated_at=agent.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent: {str(e)}",
        )


@router.get("/", response_model=List[AgentResponse])
async def get_all_agents(
    db: AsyncSession = Depends(get_db),
) -> List[AgentResponse]:
    """
    Get all agents.

    Returns:
        List of all agents
    """
    try:
        logger.info("Received request to get all agents")

        # Create agent service
        service = AgentService(db)

        # Get all agents
        agents = await service.get_all_agents()

        # Convert to response models
        return [
            AgentResponse(
                id=agent.id,
                name=agent.name,
                description=agent.description,
                type=agent.type,
                status=agent.status,
                config=agent.config,
                created_at=agent.created_at.isoformat(),
                updated_at=agent.updated_at.isoformat(),
            )
            for agent in agents
        ]

    except Exception as e:
        logger.error(f"Error getting all agents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting all agents: {str(e)}",
        )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """
    Update an agent.

    Args:
        agent_id: The agent ID
        agent_data: The agent data to update
        db: Database session

    Returns:
        The updated agent

    Raises:
        HTTPException: If the agent is not found
    """
    try:
        logger.info(f"Received request to update agent: {agent_id}")

        # Create agent service
        service = AgentService(db)

        # Update agent
        agent = await service.update_agent(agent_id, agent_data)

        # Check if agent exists
        if not agent:
            logger.warning(f"Agent with ID {agent_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found",
            )

        # Convert to response model
        return AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            type=agent.type,
            status=agent.status,
            config=agent.config,
            created_at=agent.created_at.isoformat(),
            updated_at=agent.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating agent: {str(e)}",
        )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete an agent.

    Args:
        agent_id: The agent ID
        db: Database session

    Raises:
        HTTPException: If the agent is not found
    """
    try:
        logger.info(f"Received request to delete agent: {agent_id}")

        # Create agent service
        service = AgentService(db)

        # Delete agent
        deleted = await service.delete_agent(agent_id)

        # Check if agent was deleted
        if not deleted:
            logger.warning(f"Agent with ID {agent_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting agent: {str(e)}",
        )
