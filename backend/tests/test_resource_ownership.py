"""
Tests for resource ownership and multi-tenancy functionality.
"""

import pytest
import uuid
from httpx import AsyncClient
from fastapi import status

from app.models.user import User, UserRole, UserStatus
from app.models.agent import Agent, AgentType, AgentStatus
from app.models.document import Document, DocumentStatus
from app.utils.auth import create_access_token, get_password_hash


@pytest.fixture
async def user1(db_session):
    """Create first test user."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        username="user1",
        email="user1@example.com",
        hashed_password=get_password_hash("Password123!"),
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def user2(db_session):
    """Create second test user."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        username="user2",
        email="user2@example.com",
        hashed_password=get_password_hash("Password123!"),
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session):
    """Create admin test user."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPass123!"),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def user1_token(user1):
    """Create a token for user1."""
    return create_access_token({"sub": str(user1.id)})


@pytest.fixture
def user2_token(user2):
    """Create a token for user2."""
    return create_access_token({"sub": str(user2.id)})


@pytest.fixture
def admin_token(admin_user):
    """Create a token for admin user."""
    return create_access_token({"sub": str(admin_user.id)})


@pytest.fixture
async def user1_agent(db_session, user1):
    """Create an agent owned by user1."""
    agent_id = uuid.uuid4()
    agent = Agent(
        id=agent_id,
        name="User1 Agent",
        description="Test agent for user1",
        type=AgentType.RAG,
        status=AgentStatus.ACTIVE,
        user_id=user1.id,
        config={"model": "gpt-4"},
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


@pytest.fixture
async def user2_agent(db_session, user2):
    """Create an agent owned by user2."""
    agent_id = uuid.uuid4()
    agent = Agent(
        id=agent_id,
        name="User2 Agent",
        description="Test agent for user2",
        type=AgentType.CHAT,
        status=AgentStatus.ACTIVE,
        user_id=user2.id,
        config={"model": "gpt-3.5-turbo"},
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


@pytest.fixture
async def user1_document(db_session, user1):
    """Create a document owned by user1."""
    doc_id = uuid.uuid4()
    document = Document(
        id=doc_id,
        filename="user1_doc.pdf",
        file_path="/path/to/user1_doc.pdf",
        file_type="application/pdf",
        file_size=1024,
        status=DocumentStatus.PROCESSED,
        user_id=user1.id,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document


@pytest.mark.asyncio
async def test_user_can_access_own_agent(client, user1_token, user1_agent):
    """Test that a user can access their own agent."""
    response = await client.get(
        f"/api/agents/{user1_agent.id}",
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(user1_agent.id)
    assert data["name"] == user1_agent.name


@pytest.mark.asyncio
async def test_user_cannot_access_others_agent(client, user1_token, user2_agent):
    """Test that a user cannot access another user's agent."""
    response = await client.get(
        f"/api/agents/{user2_agent.id}",
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_admin_can_access_any_agent(client, admin_token, user1_agent):
    """Test that an admin can access any user's agent."""
    response = await client.get(
        f"/api/agents/{user1_agent.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(user1_agent.id)


@pytest.mark.asyncio
async def test_user_can_list_only_own_agents(
    client, user1_token, user1_agent, user2_agent
):
    """Test that a user can only list their own agents."""
    response = await client.get(
        "/api/agents/",
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Check that only user1's agents are returned
    agent_ids = [agent["id"] for agent in data]
    assert str(user1_agent.id) in agent_ids
    assert str(user2_agent.id) not in agent_ids


@pytest.mark.asyncio
async def test_admin_can_list_all_agents(client, admin_token, user1_agent, user2_agent):
    """Test that an admin can list all agents."""
    response = await client.get(
        "/api/agents/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Check that both agents are returned
    agent_ids = [agent["id"] for agent in data]
    assert str(user1_agent.id) in agent_ids
    assert str(user2_agent.id) in agent_ids


@pytest.mark.asyncio
async def test_user_can_update_own_agent(client, user1_token, user1_agent):
    """Test that a user can update their own agent."""
    response = await client.put(
        f"/api/agents/{user1_agent.id}",
        headers={"Authorization": f"Bearer {user1_token}"},
        json={
            "name": "Updated Agent Name",
            "description": "Updated description",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated Agent Name"
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_user_cannot_update_others_agent(client, user1_token, user2_agent):
    """Test that a user cannot update another user's agent."""
    response = await client.put(
        f"/api/agents/{user2_agent.id}",
        headers={"Authorization": f"Bearer {user1_token}"},
        json={
            "name": "Attempted Update",
            "description": "This should fail",
        },
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_user_can_delete_own_agent(client, user1_token, user1_agent):
    """Test that a user can delete their own agent."""
    response = await client.delete(
        f"/api/agents/{user1_agent.id}",
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify agent is deleted or marked as deleted
    response = await client.get(
        f"/api/agents/{user1_agent.id}",
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_200_OK]
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert data["status"] == "deleted"
