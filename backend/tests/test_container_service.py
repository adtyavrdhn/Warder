"""
Unit tests for the container service.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.agent import Agent, AgentType, AgentStatus, ContainerStatus
from app.services.container_service import ContainerService


@pytest.fixture
def mock_docker_client():
    """Mock Docker client for testing."""
    with patch("app.services.container_service.docker_client") as mock_client:
        yield mock_client


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    agent = Agent(
        id=uuid4(),
        name="Test Agent",
        description="Test agent for container service",
        type=AgentType.CHAT,
        status=AgentStatus.ACTIVE,
        user_id=uuid4(),
        container_status=ContainerStatus.NONE,
        container_config={
            "image": "warder/agent:latest",
            "memory_limit": "512m",
            "cpu_limit": 0.5,
            "env_vars": {"TEST_VAR": "test_value"},
        },
    )
    return agent


class TestContainerService:
    """Tests for the ContainerService class."""

    def test_init(self, mock_docker_client):
        """Test ContainerService initialization."""
        # Set up
        mock_docker_client.networks.list.return_value = []

        # Execute
        service = ContainerService()

        # Assert
        mock_docker_client.networks.list.assert_called_once()
        mock_docker_client.networks.create.assert_called_once()

    def test_generate_container_name(self):
        """Test container name generation."""
        # Set up
        service = ContainerService()
        agent_name = "Test Agent 123"

        # Execute
        container_name = service._generate_container_name(agent_name)

        # Assert
        assert "warder-agent-testagent123-" in container_name
        assert len(container_name) > len("warder-agent-testagent123-")

    @pytest.mark.asyncio
    async def test_create_container_success(self, mock_docker_client, mock_agent):
        """Test successful container creation."""
        # Set up
        service = ContainerService()
        mock_container = MagicMock()
        mock_container.id = "test-container-id"
        mock_docker_client.containers.create.return_value = mock_container

        # Execute
        success, container_id = await service.create_container(mock_agent)

        # Assert
        assert success is True
        assert container_id == "test-container-id"
        mock_docker_client.containers.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_container_failure(self, mock_docker_client, mock_agent):
        """Test container creation failure."""
        # Set up
        service = ContainerService()
        mock_docker_client.containers.create.side_effect = Exception("Test error")

        # Execute
        success, error_message = await service.create_container(mock_agent)

        # Assert
        assert success is False
        assert "Test error" in error_message
        mock_docker_client.containers.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_container_success(self, mock_docker_client):
        """Test successful container start."""
        # Set up
        service = ContainerService()
        container_id = "test-container-id"
        mock_container = MagicMock()
        mock_docker_client.containers.get.return_value = mock_container

        # Execute
        success, message = await service.start_container(container_id)

        # Assert
        assert success is True
        mock_docker_client.containers.get.assert_called_once_with(container_id)
        mock_container.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_container_failure(self, mock_docker_client):
        """Test container start failure."""
        # Set up
        service = ContainerService()
        container_id = "test-container-id"
        mock_docker_client.containers.get.side_effect = Exception("Test error")

        # Execute
        success, error_message = await service.start_container(container_id)

        # Assert
        assert success is False
        assert "Test error" in error_message
        mock_docker_client.containers.get.assert_called_once_with(container_id)

    @pytest.mark.asyncio
    async def test_stop_container_success(self, mock_docker_client):
        """Test successful container stop."""
        # Set up
        service = ContainerService()
        container_id = "test-container-id"
        mock_container = MagicMock()
        mock_docker_client.containers.get.return_value = mock_container

        # Execute
        success, message = await service.stop_container(container_id)

        # Assert
        assert success is True
        mock_docker_client.containers.get.assert_called_once_with(container_id)
        mock_container.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_container_success(self, mock_docker_client):
        """Test successful container deletion."""
        # Set up
        service = ContainerService()
        container_id = "test-container-id"
        mock_container = MagicMock()
        mock_docker_client.containers.get.return_value = mock_container

        # Execute
        success, message = await service.delete_container(container_id)

        # Assert
        assert success is True
        mock_docker_client.containers.get.assert_called_once_with(container_id)
        mock_container.remove.assert_called_once_with(force=True)

    @pytest.mark.asyncio
    async def test_get_container_logs(self, mock_docker_client):
        """Test getting container logs."""
        # Set up
        service = ContainerService()
        container_id = "test-container-id"
        mock_container = MagicMock()
        mock_container.logs.return_value = b"Test logs"
        mock_docker_client.containers.get.return_value = mock_container

        # Execute
        logs = await service.get_container_logs(container_id, 100)

        # Assert
        assert logs == "Test logs"
        mock_docker_client.containers.get.assert_called_once_with(container_id)
        mock_container.logs.assert_called_once_with(tail=100, timestamps=True)

    @pytest.mark.asyncio
    async def test_get_container_stats(self, mock_docker_client):
        """Test getting container stats."""
        # Set up
        service = ContainerService()
        container_id = "test-container-id"
        mock_container = MagicMock()
        mock_stats = {
            "cpu_stats": {"cpu_usage": {"total_usage": 1000}, "system_cpu_usage": 10000},
            "memory_stats": {"usage": 1024 * 1024 * 100, "limit": 1024 * 1024 * 1024},
            "networks": {"eth0": {"rx_bytes": 1024, "tx_bytes": 2048}}
        }
        mock_container.stats.return_value = mock_stats
        mock_docker_client.containers.get.return_value = mock_container
        
        # Expected processed stats
        expected_stats = {
            "cpu_usage": 1000,
            "system_cpu_usage": 10000,
            "memory_usage": 1024 * 1024 * 100,
            "memory_limit": 1024 * 1024 * 1024,
            "network_rx_bytes": 1024,
            "network_tx_bytes": 2048
        }
        
        # Execute
        stats = await service.get_container_stats(container_id)
        
        # Assert
        assert stats == expected_stats
        mock_docker_client.containers.get.assert_called_once_with(container_id)
        mock_container.stats.assert_called_once_with(stream=False)
