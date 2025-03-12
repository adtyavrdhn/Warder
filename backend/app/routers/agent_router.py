"""
Router for agent-related endpoints.
"""

import logging
from typing import List, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse
from app.services.agent_service import AgentService
from app.utils.database import get_db

# Configure logger
logger = logging.getLogger(__name__)


# Create router
router = APIRouter()


# Define query model
class AgentQuery(BaseModel):
    """Model for agent query."""

    query: str


async def get_agent_response(self, agent_id: UUID, message: dict) -> Dict[str, str]:
    """Get a response from an agent."""
    agent = await self.db.get(Agent, agent_id)

    if settings.USE_CONTAINERS:
        # Container mode - HTTP request to container
        if not agent.container_id or agent.container_status != "running":
            # Start container if needed
            await self.start_agent(agent_id)

        # Forward request to container
        response = await self._forward_to_container(agent, "/chat", message)
        return response
    else:
        # In-process mode - direct call
        agent_instance = await self.get_agent_instance(agent_id)
        response = agent_instance.get_response(message["content"])
        return {"content": response, "role": "assistant"}


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


@router.post("/{agent_id}/chat", status_code=status.HTTP_200_OK)
async def chat_with_agent(
    agent_id: UUID,
    message: dict,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Chat with an agent."""
    # Get agent from database
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get response from agent (either container or in-process)
    return await agent_service.get_agent_response(agent_id, message)


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


@router.post("/{agent_id}/start", status_code=status.HTTP_200_OK)
async def start_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Start an agent's container.

    Args:
        agent_id: The agent ID
        db: Database session

    Returns:
        A success message

    Raises:
        HTTPException: If the agent is not found or if there's an error starting the container
    """
    try:
        logger.info(f"Received request to start agent: {agent_id}")

        # Create agent service
        service = AgentService(db)

        # Start agent container
        success = await service.start_agent_container(agent_id)

        # Check if operation was successful
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to start agent container for agent {agent_id}",
            )

        return {"message": f"Agent {agent_id} started successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting agent: {str(e)}",
        )


@router.post("/{agent_id}/stop", status_code=status.HTTP_200_OK)
async def stop_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Stop an agent's container.

    Args:
        agent_id: The agent ID
        db: Database session

    Returns:
        A success message

    Raises:
        HTTPException: If the agent is not found or if there's an error stopping the container
    """
    try:
        logger.info(f"Received request to stop agent: {agent_id}")

        # Create agent service
        service = AgentService(db)

        # Stop agent container
        success = await service.stop_agent_container(agent_id)

        # Check if operation was successful
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to stop agent container for agent {agent_id}",
            )

        return {"message": f"Agent {agent_id} stopped successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error stopping agent: {str(e)}",
        )


@router.get("/{agent_id}/logs", status_code=status.HTTP_200_OK)
async def get_agent_logs(
    agent_id: UUID,
    lines: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get logs from an agent's container.

    Args:
        agent_id: The agent ID
        lines: Number of log lines to retrieve (default: 100, max: 1000)
        db: Database session

    Returns:
        The container logs

    Raises:
        HTTPException: If the agent is not found or if there's an error getting the logs
    """
    try:
        logger.info(f"Received request to get logs for agent: {agent_id}")

        # Create agent service
        service = AgentService(db)

        # Get agent logs
        logs = await service.get_agent_container_logs(agent_id, lines)

        # Check if logs were retrieved
        if logs is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get logs for agent {agent_id}",
            )

        return {"logs": logs}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting logs for agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting logs: {str(e)}",
        )


@router.get("/{agent_id}/stats", status_code=status.HTTP_200_OK)
async def get_agent_stats(agent_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Get stats from an agent's container.

    Args:
        agent_id: The agent ID
        db: Database session

    Returns:
        The container stats

    Raises:
        HTTPException: If the agent is not found or if there's an error getting the stats
    """
    try:
        logger.info(f"Received request to get stats for agent: {agent_id}")

        # Create agent service
        service = AgentService(db)

        # Check if agent exists
        agent = await service.get_agent(agent_id)
        if not agent:
            logger.warning(f"Agent with ID {agent_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found",
            )

        # Get container ID
        container_id = agent.container_id
        if not container_id:
            logger.warning(f"Agent {agent_id} has no container")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent has no container",
            )

        # Get container stats
        success, stats = await service.container_service.get_container_stats(
            container_id
        )
        if not success:
            logger.warning(f"Failed to get stats for container {container_id}: {stats}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get stats: {stats}",
            )

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats for agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting stats: {str(e)}",
        )


@router.post("/{agent_id}/query", status_code=status.HTTP_200_OK)
async def query_agent(
    agent_id: UUID,
    query_data: AgentQuery,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Query an agent and get a response.

    Args:
        agent_id: The agent ID
        query_data: The query data
        db: Database session

    Returns:
        The agent's response

    Raises:
        HTTPException: If the agent is not found or if there's an error querying the agent
    """
    try:
        logger.info(f"Received request to query agent: {agent_id}")

        # Create agent service
        service = AgentService(db)

        # Check if agent exists
        agent = await service.get_agent(agent_id)
        if not agent:
            logger.warning(f"Agent with ID {agent_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found",
            )

        # Get response from agent
        response = await service.get_agent_response(agent_id, query_data.query)

        # Check if response was generated
        if response is None:
            logger.warning(f"Failed to get response from agent {agent_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get response from agent",
            )

        return {"response": response}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying agent: {str(e)}",
        )
