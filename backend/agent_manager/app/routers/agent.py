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
from app.repositories.agent_repository import AgentRepository
from app.utils.db import get_db

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# Dependency to get agent service
async def get_agent_service(db: AsyncSession = Depends(get_db)) -> AgentService:
    """
    Get agent service dependency.

    Args:
        db: Database session

    Returns:
        Agent service instance
    """
    repository = AgentRepository(db)
    return AgentService(repository)


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate, service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """
    Create a new agent.

    This endpoint creates a new agent with the specified configuration.
    If the agent type is RAG, it will also initialize the knowledge base.

    Args:
        agent_data: The agent data to create
        service: Agent service dependency

    Returns:
        The created agent

    Raises:
        HTTPException: If there's an error creating the agent
    """
    try:
        logger.info(f"Received request to create agent: {agent_data.name}")

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
    agent_id: UUID, service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """
    Get an agent by ID.

    Args:
        agent_id: The agent ID
        service: Agent service dependency

    Returns:
        The agent

    Raises:
        HTTPException: If the agent is not found
    """
    try:
        logger.info(f"Received request to get agent: {agent_id}")

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
    service: AgentService = Depends(get_agent_service),
) -> List[AgentResponse]:
    """
    Get all agents.

    Returns:
        List of all agents
    """
    try:
        logger.info("Received request to get all agents")

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
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """
    Update an agent.

    Args:
        agent_id: The agent ID
        agent_data: The agent data to update
        service: Agent service dependency

    Returns:
        The updated agent

    Raises:
        HTTPException: If the agent is not found
    """
    try:
        logger.info(f"Received request to update agent: {agent_id}")

        # Update agent
        agent = await service.update_agent(agent_id, agent_data)

        # Check if agent exists
        if not agent:
            logger.warning(f"Agent with ID {agent_id} not found for update")
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
async def delete_agent(
    agent_id: UUID, service: AgentService = Depends(get_agent_service)
) -> None:
    """
    Delete an agent.

    Args:
        agent_id: The agent ID
        service: Agent service dependency

    Raises:
        HTTPException: If the agent is not found
    """
    try:
        logger.info(f"Received request to delete agent: {agent_id}")

        # Delete agent
        deleted = await service.delete_agent(agent_id)

        # Check if agent exists
        if not deleted:
            logger.warning(f"Agent with ID {agent_id} not found for deletion")
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
