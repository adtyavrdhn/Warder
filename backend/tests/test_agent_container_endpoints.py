"""
Integration tests for agent container management endpoints.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch
from uuid import uuid4

from app.models.user import User
from app.models.agent import Agent, AgentType, AgentStatus, ContainerStatus
from app.services.container_service import ContainerService


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        first_name="Test",
        last_name="User"
    )
    user.set_password("Password123!")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_agent(db_session, test_user):
    """Create a test agent."""
    agent = Agent(
        name="Test Container Agent",
        description="Test agent for container management",
        type=AgentType.CHAT,
        status=AgentStatus.ACTIVE,
        user_id=test_user.id,
        config={"model": "gpt-3.5-turbo"},
        container_status=ContainerStatus.NONE,
        container_config={
            "image": "warder/agent:latest",
            "memory_limit": "512m",
            "cpu_limit": 0.5,
            "env_vars": {"TEST_VAR": "test_value"},
        },
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


@pytest_asyncio.fixture
async def auth_headers(client, test_user):
    """Get authentication headers for the test user."""
    response = await client.post(
        "/api/auth/token",
        data={
            "username": test_user.username,
            "password": "Password123!",
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAgentContainerEndpoints:
    """Tests for agent container management endpoints."""

    @pytest.mark.asyncio
    @patch.object(ContainerService, "create_container")
    @patch.object(ContainerService, "start_container")
    async def test_start_agent_container(
        self, mock_start, mock_create, client, test_agent, auth_headers
    ):
        """Test starting an agent container."""
        # Set up
        mock_create.return_value = (True, "test-container-id")
        mock_start.return_value = (True, "Container started")
        
        # Execute
        response = await client.post(
            f"/api/agents/{test_agent.id}/start",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert "started successfully" in response.json()["message"]

    @pytest.mark.asyncio
    @patch.object(ContainerService, "stop_container")
    async def test_stop_agent_container(
        self, mock_stop, client, test_agent, auth_headers
    ):
        """Test stopping an agent container."""
        # Set up
        test_agent.container_id = "test-container-id"
        test_agent.container_status = ContainerStatus.RUNNING
        mock_stop.return_value = (True, "Container stopped")
        
        # Execute
        response = await client.post(
            f"/api/agents/{test_agent.id}/stop",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert "stopped successfully" in response.json()["message"]

    @pytest.mark.asyncio
    @patch.object(ContainerService, "get_container_logs")
    async def test_get_agent_logs(
        self, mock_logs, client, test_agent, auth_headers
    ):
        """Test getting agent container logs."""
        # Set up
        test_agent.container_id = "test-container-id"
        test_agent.container_status = ContainerStatus.RUNNING
        mock_logs.return_value = "Test container logs"
        
        # Execute
        response = await client.get(
            f"/api/agents/{test_agent.id}/logs",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["logs"] == "Test container logs"

    @pytest.mark.asyncio
    @patch.object(ContainerService, "get_container_stats")
    async def test_get_agent_stats(
        self, mock_stats, client, test_agent, auth_headers
    ):
        """Test getting agent container stats."""
        # Set up
        test_agent.container_id = "test-container-id"
        test_agent.container_status = ContainerStatus.RUNNING
        mock_stats.return_value = {"cpu": "10%", "memory": "100MB"}
        
        # Execute
        response = await client.get(
            f"/api/agents/{test_agent.id}/stats",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["stats"] == {"cpu": "10%", "memory": "100MB"}

    @pytest.mark.asyncio
    @patch.object(ContainerService, "get_container_logs")
    async def test_get_agent_logs_with_lines_param(
        self, mock_logs, client, test_agent, auth_headers
    ):
        """Test getting agent container logs with lines parameter."""
        # Set up
        test_agent.container_id = "test-container-id"
        test_agent.container_status = ContainerStatus.RUNNING
        mock_logs.return_value = "Test container logs"
        
        # Execute
        response = await client.get(
            f"/api/agents/{test_agent.id}/logs?lines=50",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["logs"] == "Test container logs"
        mock_logs.assert_called_once_with(test_agent.container_id, 50)

    @pytest.mark.asyncio
    async def test_start_nonexistent_agent(self, client, auth_headers):
        """Test starting a nonexistent agent."""
        # Execute
        response = await client.post(
            f"/api/agents/{uuid4()}/start",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch.object(ContainerService, "start_container")
    async def test_start_agent_container_failure(
        self, mock_start, client, test_agent, auth_headers
    ):
        """Test failure when starting an agent container."""
        # Set up
        test_agent.container_id = "test-container-id"
        mock_start.return_value = (False, "Failed to start container")
        
        # Execute
        response = await client.post(
            f"/api/agents/{test_agent.id}/start",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 400
        assert "Failed to start" in response.json()["detail"]
