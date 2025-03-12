"""
Tests for the agent API endpoints.
"""

import os
import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.agent import Agent
from app.schemas.agent import AgentType, AgentStatus, AgentCreate
from app.repositories.agent_repository import AgentRepository
from app.services.agent_service import AgentService


# Create test client
client = TestClient(app)


# Mock database session
@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


# Mock agent repository
@pytest.fixture
def mock_agent_repository(mock_db_session):
    """Mock agent repository."""
    repository = AgentRepository(mock_db_session)
    return repository


# Mock agent service
@pytest.fixture
def mock_agent_service(mock_agent_repository):
    """Mock agent service."""
    with patch("app.routers.agent.get_agent_service") as mock_get_service:
        service = AgentService(mock_agent_repository)
        mock_get_service.return_value = service
        yield service


# Test agent creation
def test_create_agent(mock_agent_service, mock_agent_repository):
    """Test agent creation endpoint."""
    # Mock repository create method
    agent_id = uuid.uuid4()
    mock_agent = MagicMock(spec=Agent)
    mock_agent.id = agent_id
    mock_agent.name = "Test Agent"
    mock_agent.description = "Test Description"
    mock_agent.type = AgentType.RAG
    mock_agent.status = AgentStatus.ACTIVE
    mock_agent.config = {"test": "config"}
    mock_agent.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    mock_agent.updated_at.isoformat.return_value = "2023-01-01T00:00:00"

    # Set up the mock
    mock_agent_service.create_agent = AsyncMock(return_value=mock_agent)

    # Test data
    test_data = {
        "name": "Test Agent",
        "description": "Test Description",
        "type": "rag",
        "knowledge_base": {
            "directory": "data/pdfs/test",
            "recreate": False,
            "chunk_size": 1000,
            "chunk_overlap": 200,
        },
        "config": {"test": "config"},
    }

    # Make request
    response = client.post("/agents/", json=test_data)

    # Check response
    assert response.status_code == 201
    assert response.json()["name"] == "Test Agent"
    assert response.json()["description"] == "Test Description"
    assert response.json()["type"] == "rag"
    assert response.json()["status"] == "active"
    assert response.json()["config"] == {"test": "config"}

    # Check that service was called correctly
    mock_agent_service.create_agent.assert_called_once()
    call_args = mock_agent_service.create_agent.call_args[0][0]
    assert isinstance(call_args, AgentCreate)
    assert call_args.name == "Test Agent"
    assert call_args.description == "Test Description"
    assert call_args.type == AgentType.RAG
    assert call_args.knowledge_base.directory == "data/pdfs/test"
    assert call_args.knowledge_base.recreate is False
    assert call_args.knowledge_base.chunk_size == 1000
    assert call_args.knowledge_base.chunk_overlap == 200
    assert call_args.config == {"test": "config"}


# Test get agent by ID
def test_get_agent_by_id(mock_agent_service):
    """Test get agent by ID endpoint."""
    # Mock service get_agent method
    agent_id = uuid.uuid4()
    mock_agent = MagicMock(spec=Agent)
    mock_agent.id = agent_id
    mock_agent.name = "Test Agent"
    mock_agent.description = "Test Description"
    mock_agent.type = AgentType.RAG
    mock_agent.status = AgentStatus.ACTIVE
    mock_agent.config = {"test": "config"}
    mock_agent.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    mock_agent.updated_at.isoformat.return_value = "2023-01-01T00:00:00"

    # Set up the mock
    mock_agent_service.get_agent = AsyncMock(return_value=mock_agent)

    # Make request
    response = client.get(f"/agents/{agent_id}")

    # Check response
    assert response.status_code == 200
    assert response.json()["id"] == str(agent_id)
    assert response.json()["name"] == "Test Agent"
    assert response.json()["description"] == "Test Description"
    assert response.json()["type"] == "rag"
    assert response.json()["status"] == "active"
    assert response.json()["config"] == {"test": "config"}

    # Check that service was called correctly
    mock_agent_service.get_agent.assert_called_once_with(agent_id)


# Test get agent by ID not found
def test_get_agent_by_id_not_found(mock_agent_service):
    """Test get agent by ID endpoint when agent not found."""
    # Mock service get_agent method
    agent_id = uuid.uuid4()

    # Set up the mock
    mock_agent_service.get_agent = AsyncMock(return_value=None)

    # Make request
    response = client.get(f"/agents/{agent_id}")

    # Check response
    assert response.status_code == 404
    assert response.json()["detail"] == f"Agent with ID {agent_id} not found"

    # Check that service was called correctly
    mock_agent_service.get_agent.assert_called_once_with(agent_id)


# Test get all agents
def test_get_all_agents(mock_agent_service):
    """Test get all agents endpoint."""
    # Mock service get_all_agents method
    agent_id1 = uuid.uuid4()
    agent_id2 = uuid.uuid4()

    mock_agent1 = MagicMock(spec=Agent)
    mock_agent1.id = agent_id1
    mock_agent1.name = "Test Agent 1"
    mock_agent1.description = "Test Description 1"
    mock_agent1.type = AgentType.RAG
    mock_agent1.status = AgentStatus.ACTIVE
    mock_agent1.config = {"test": "config1"}
    mock_agent1.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    mock_agent1.updated_at.isoformat.return_value = "2023-01-01T00:00:00"

    mock_agent2 = MagicMock(spec=Agent)
    mock_agent2.id = agent_id2
    mock_agent2.name = "Test Agent 2"
    mock_agent2.description = "Test Description 2"
    mock_agent2.type = AgentType.CHAT
    mock_agent2.status = AgentStatus.ACTIVE
    mock_agent2.config = {"test": "config2"}
    mock_agent2.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    mock_agent2.updated_at.isoformat.return_value = "2023-01-01T00:00:00"

    # Set up the mock
    mock_agent_service.get_all_agents = AsyncMock(
        return_value=[mock_agent1, mock_agent2]
    )

    # Make request
    response = client.get("/agents/")

    # Check response
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["id"] == str(agent_id1)
    assert response.json()[0]["name"] == "Test Agent 1"
    assert response.json()[1]["id"] == str(agent_id2)
    assert response.json()[1]["name"] == "Test Agent 2"

    # Check that service was called correctly
    mock_agent_service.get_all_agents.assert_called_once()


# Test update agent
def test_update_agent(mock_agent_service):
    """Test update agent endpoint."""
    # Mock service update_agent method
    agent_id = uuid.uuid4()
    mock_agent = MagicMock(spec=Agent)
    mock_agent.id = agent_id
    mock_agent.name = "Updated Agent"
    mock_agent.description = "Updated Description"
    mock_agent.type = AgentType.RAG
    mock_agent.status = AgentStatus.ACTIVE
    mock_agent.config = {"test": "updated_config"}
    mock_agent.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    mock_agent.updated_at.isoformat.return_value = "2023-01-01T00:00:00"

    # Set up the mock
    mock_agent_service.update_agent = AsyncMock(return_value=mock_agent)

    # Test data
    test_data = {
        "name": "Updated Agent",
        "description": "Updated Description",
        "status": "active",
        "config": {"test": "updated_config"},
    }

    # Make request
    response = client.put(f"/agents/{agent_id}", json=test_data)

    # Check response
    assert response.status_code == 200
    assert response.json()["id"] == str(agent_id)
    assert response.json()["name"] == "Updated Agent"
    assert response.json()["description"] == "Updated Description"
    assert response.json()["status"] == "active"
    assert response.json()["config"] == {"test": "updated_config"}

    # Check that service was called correctly
    mock_agent_service.update_agent.assert_called_once()


# Test update agent not found
def test_update_agent_not_found(mock_agent_service):
    """Test update agent endpoint when agent not found."""
    # Mock service update_agent method
    agent_id = uuid.uuid4()

    # Set up the mock
    mock_agent_service.update_agent = AsyncMock(return_value=None)

    # Test data
    test_data = {"name": "Updated Agent", "description": "Updated Description"}

    # Make request
    response = client.put(f"/agents/{agent_id}", json=test_data)

    # Check response
    assert response.status_code == 404
    assert response.json()["detail"] == f"Agent with ID {agent_id} not found"

    # Check that service was called correctly
    mock_agent_service.update_agent.assert_called_once()


# Test delete agent
def test_delete_agent(mock_agent_service):
    """Test delete agent endpoint."""
    # Mock service delete_agent method
    agent_id = uuid.uuid4()

    # Set up the mock
    mock_agent_service.delete_agent = AsyncMock(return_value=True)

    # Make request
    response = client.delete(f"/agents/{agent_id}")

    # Check response
    assert response.status_code == 204

    # Check that service was called correctly
    mock_agent_service.delete_agent.assert_called_once_with(agent_id)


# Test delete agent not found
def test_delete_agent_not_found(mock_agent_service):
    """Test delete agent endpoint when agent not found."""
    # Mock service delete_agent method
    agent_id = uuid.uuid4()

    # Set up the mock
    mock_agent_service.delete_agent = AsyncMock(return_value=False)

    # Make request
    response = client.delete(f"/agents/{agent_id}")

    # Check response
    assert response.status_code == 404
    assert response.json()["detail"] == f"Agent with ID {agent_id} not found"

    # Check that service was called correctly
    mock_agent_service.delete_agent.assert_called_once_with(agent_id)


# Test agent creation with error
def test_create_agent_error(mock_agent_service):
    """Test agent creation endpoint with error."""
    # Mock service create_agent method to raise an exception
    mock_agent_service.create_agent = AsyncMock(side_effect=Exception("Test error"))

    # Test data
    test_data = {"name": "Test Agent", "description": "Test Description", "type": "rag"}

    # Make request
    response = client.post("/agents/", json=test_data)

    # Check response
    assert response.status_code == 500
    assert response.json()["detail"] == "Error creating agent: Test error"

    # Check that service was called correctly
    mock_agent_service.create_agent.assert_called_once()
