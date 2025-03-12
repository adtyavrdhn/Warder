"""
Tests for authentication and authorization functionality.
"""

import pytest
import uuid
from httpx import AsyncClient
from fastapi import status

from app.models.user import User, UserRole, UserStatus
from app.utils.auth import create_access_token, get_password_hash


@pytest.fixture
async def test_user(db_session):
    """Create a test user for authentication tests."""
    # Check if user already exists
    from sqlalchemy import select
    existing_user = await db_session.execute(
        select(User).where(User.username == "testuser")
    )
    user_row = existing_user.scalar_one_or_none()
    
    if user_row:
        # If user exists, return it
        return user_row
    
    # Otherwise create a new user
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        username="testuser",
        email="test@example.com",
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
async def test_admin(db_session):
    """Create a test admin for authorization tests."""
    # Check if admin already exists
    from sqlalchemy import select
    existing_admin = await db_session.execute(
        select(User).where(User.username == "testadmin")
    )
    admin_row = existing_admin.scalar_one_or_none()
    
    if admin_row:
        # If admin exists, return it
        return admin_row
    
    # Otherwise create a new admin
    admin_id = uuid.uuid4()
    admin = User(
        id=admin_id,
        username="testadmin",
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPass123!"),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        verified=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
def user_token(test_user):
    """Create a token for the test user."""
    return create_access_token({"sub": str(test_user.id)})


@pytest.fixture
def admin_token(test_admin):
    """Create a token for the test admin."""
    return create_access_token({"sub": str(test_admin.id)})


@pytest.mark.asyncio
async def test_login(client: AsyncClient, test_user):
    """Test user login endpoint."""
    response = await client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "Password123!"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, test_user):
    """Test login with invalid credentials."""
    response = await client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "WrongPassword"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration endpoint."""
    response = await client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "NewPass123!",
            "first_name": "New",
            "last_name": "User",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, test_user):
    """Test registration with duplicate username."""
    response = await client.post(
        "/api/auth/register",
        json={
            "username": "testuser",  # Same as test_user
            "email": "different@example.com",
            "password": "NewPass123!",
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, user_token, test_user):
    """Test getting current user info."""
    response = await client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """Test accessing protected endpoint without token."""
    response = await client.get("/api/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_admin_access(client: AsyncClient, admin_token):
    """Test admin access to all users endpoint."""
    response = await client.get(
        "/api/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_non_admin_restricted_access(client: AsyncClient, user_token):
    """Test non-admin access to admin-only endpoint."""
    response = await client.get(
        "/api/users/",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user):
    """Test refresh token endpoint."""
    # First login to get tokens
    login_response = await client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "Password123!"},
    )
    tokens = login_response.json()

    # Use refresh token to get new access token
    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient, user_token, test_user):
    """Test updating user information."""
    response = await client.put(
        "/api/users/me",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "first_name": "Updated",
            "last_name": "User",
            "preferences": {"theme": "dark"},
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "User"
    assert data["preferences"]["theme"] == "dark"
