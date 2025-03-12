"""
Unit tests for the agent service container management methods.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentType, AgentStatus, ContainerStatus
from app.services.agent_service import AgentService
from app.services.container_service import ContainerService


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    session = AsyncMock(spec=AsyncSession)
    # Mock the execute method to return a result proxy that can be awaited
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_container_service():
    """Mock container service for testing."""
    with patch("app.services.agent_service.ContainerService") as mock_service:
        mock_instance = MagicMock(spec=ContainerService)
        mock_service.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    agent = MagicMock(spec=Agent)
    agent.id = uuid4()
    agent.name = "Test Agent"
    agent.description = "Test agent for container service"
    agent.type = AgentType.CHAT
    agent.status = AgentStatus.ACTIVE
    agent.user_id = uuid4()
    agent.container_id = None
    agent.container_name = None
    agent.container_status = ContainerStatus.NONE
    agent.container_config = {
        "image": "warder/agent:latest",
        "memory_limit": "512m",
        "cpu_limit": 0.5,
        "env_vars": {"TEST_VAR": "test_value"},
    }
    agent.host_port = None
    return agent


class TestAgentServiceContainer:
    """Tests for the AgentService container management methods."""

    @pytest.mark.asyncio
    async def test_create_agent_container(
        self, mock_db_session, mock_container_service, mock_agent
    ):
        """Test creating an agent container."""
        # Set up
        service = AgentService(mock_db_session)
        
        # Mock the get_agent method
        service.get_agent = AsyncMock(return_value=mock_agent)
        
        # Mock the container service create_container method
        mock_container_service.create_container = AsyncMock(return_value=(True, "test-container-id"))
        
        # Execute
        success = await service.create_agent_container(mock_agent.id)
        
        # Assert
        assert success is True
        mock_container_service.create_container.assert_called_once_with(mock_agent)
        assert mock_agent.container_id == "test-container-id"
        assert mock_agent.container_status == ContainerStatus.STOPPED
        assert mock_db_session.commit.called

    @pytest.mark.asyncio
    async def test_create_agent_container_failure(
        self, mock_db_session, mock_container_service, mock_agent
    ):
        """Test failure when creating an agent container."""
        # Set up
        service = AgentService(mock_db_session)
        
        # Mock the get_agent method
        service.get_agent = AsyncMock(return_value=mock_agent)
        
        # Mock the container service create_container method
        mock_container_service.create_container = AsyncMock(return_value=(False, "Test error"))
        
        # Execute
        success = await service.create_agent_container(mock_agent.id)
        
        # Assert
        assert success is False
        mock_container_service.create_container.assert_called_once_with(mock_agent)
        assert mock_agent.container_status == ContainerStatus.FAILED
        assert mock_db_session.commit.called

    @pytest.mark.asyncio
    async def test_start_agent_container(
        self, mock_db_session, mock_container_service, mock_agent
    ):
        """Test starting an agent container."""
        # Set up
        service = AgentService(mock_db_session)
        mock_agent.container_id = "test-container-id"
        mock_agent.container_status = ContainerStatus.STOPPED
        
        # Mock the container service
        mock_container_service.start_container = AsyncMock(return_value=(True, "Container started"))
        
        # Mock the get_agent method
        mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=mock_agent)
        
        # Execute
        success = await service.start_agent_container(mock_agent.id)
        
        # Assert
        assert success is True
        mock_container_service.start_container.assert_called_once_with("test-container-id")
        assert mock_agent.container_status == ContainerStatus.RUNNING
        mock_db_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_agent_container_no_container(
        self, mock_db_session, mock_container_service, mock_agent
    ):
        """Test starting an agent with no container."""
        # Set up
        service = AgentService(mock_db_session)
        mock_agent.container_id = None
        mock_agent.container_status = ContainerStatus.NONE
        
        # Mock the get_agent method
        mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=mock_agent)
        
        # Execute
        success = await service.start_agent_container(mock_agent.id)
        
        # Assert
        # Current implementation returns False when no container exists
        assert success is False
        mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_agent_container(
        self, mock_db_session, mock_container_service, mock_agent
    ):
        """Test stopping an agent container."""
        # Set up
        service = AgentService(mock_db_session)
        mock_agent.container_id = "test-container-id"
        mock_agent.container_status = ContainerStatus.RUNNING
        
        # Mock the container service
        mock_container_service.stop_container = AsyncMock(return_value=(True, "Container stopped"))
        
        # Mock the get_agent method
        mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=mock_agent)
        
        # Execute
        success = await service.stop_agent_container(mock_agent.id)
        
        # Assert
        assert success is True
        mock_container_service.stop_container.assert_called_once_with("test-container-id")
        assert mock_agent.container_status == ContainerStatus.STOPPED
        mock_db_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stop_agent_container_no_container(
        self, mock_db_session, mock_container_service, mock_agent
    ):
        """Test stopping an agent with no container."""
        # Set up
        service = AgentService(mock_db_session)
        mock_agent.container_id = None
        mock_agent.container_status = ContainerStatus.NONE
        
        # Mock the get_agent method
        mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=mock_agent)
        
        # Execute
        success = await service.stop_agent_container(mock_agent.id)
        
        # Assert
        assert success is False
        mock_container_service.stop_container.assert_not_called()
        assert mock_agent.container_status == ContainerStatus.NONE
        mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_agent_container_logs(
        self, mock_db_session, mock_container_service, mock_agent
    ):
        """Test getting agent container logs."""
        # Set up
        service = AgentService(mock_db_session)
        mock_agent.container_id = "test-container-id"
        mock_agent.container_status = ContainerStatus.RUNNING
        
        # Mock the container service
        mock_container_service.get_container_logs = AsyncMock(return_value="Test container logs")
        
        # Mock the get_agent method
        mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=mock_agent)
        
        # Execute
        logs = await service.get_agent_container_logs(mock_agent.id, 100)
        
        # Assert
        assert logs == "Test container logs"
        mock_container_service.get_container_logs.assert_called_once_with(
            "test-container-id", 100
        )

    @pytest.mark.asyncio
    async def test_get_agent_container_stats(
        self, mock_db_session, mock_container_service, mock_agent
    ):
        """Test getting agent container stats."""
        # Set up
        service = AgentService(mock_db_session)
        mock_agent.container_id = "test-container-id"
        mock_agent.container_status = ContainerStatus.RUNNING
        
        # Mock the container service
        mock_container_service.get_container_stats = AsyncMock(return_value={
            "cpu": "10%",
            "memory": "100MB",
        })
        
        # Mock the get_agent method
        mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=mock_agent)
        
        # Execute
        stats = await service.get_agent_container_stats(mock_agent.id)
        
        # Assert
        assert stats == {"cpu": "10%", "memory": "100MB"}
        mock_container_service.get_container_stats.assert_called_once_with(
            "test-container-id"
        )

    @pytest.mark.asyncio
    async def test_delete_agent_with_container(
        self, mock_db_session, mock_container_service, mock_agent
    ):
        """Test deleting an agent with a container."""
        # Set up
        service = AgentService(mock_db_session)
        mock_agent.container_id = "test-container-id"
        mock_agent.container_status = ContainerStatus.RUNNING
        
        # Mock the container service
        mock_container_service.delete_container = AsyncMock(return_value=(True, "Container deleted"))
        
        # Mock the get_agent method
        mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=mock_agent)
        
        # Execute
        success = await service.delete_agent(mock_agent.id)
        
        # Assert
        assert success is True
        mock_container_service.delete_container.assert_called_once_with("test-container-id")
        mock_db_session.delete.assert_called_once_with(mock_agent)
        mock_db_session.commit.assert_awaited_once()
