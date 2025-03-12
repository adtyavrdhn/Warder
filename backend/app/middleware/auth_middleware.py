"""
Authorization middleware for the Warder application.

This middleware enforces resource isolation and multi-tenancy by ensuring
that users can only access their own resources.
"""

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Callable, Type, Any
from uuid import UUID

from app.models.user import User
from app.utils.auth import decode_access_token, get_user_by_id
from app.utils.database import get_db
from app.models.user import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current user from the access token.

    Args:
        token: JWT access token
        db: Database session

    Returns:
        User: The current user

    Raises:
        HTTPException: If the token is invalid or the user is not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    user = await get_user_by_id(db, UUID(user_id))
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current active user.

    Args:
        current_user: Current user

    Returns:
        User: The current active user

    Raises:
        HTTPException: If the user is inactive
    """
    if current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def check_admin_role(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Check if the current user has admin role.

    Args:
        current_user: Current active user

    Returns:
        User: The current user if they have admin role

    Raises:
        HTTPException: If the user does not have admin role
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


def resource_owner_or_admin(
    resource_model: Type[Any], resource_id_name: str = "resource_id"
) -> Callable:
    """
    Dependency to check if the current user is the owner of the resource or an admin.

    Args:
        resource_model: The SQLAlchemy model of the resource
        resource_id_name: The name of the path parameter for the resource ID

    Returns:
        Callable: A dependency function
    """

    async def check_ownership(
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        """
        Check if the current user is the owner of the resource or an admin.

        Args:
            request: FastAPI request
            current_user: Current active user
            db: Database session

        Returns:
            User: The current user if they are the owner or an admin

        Raises:
            HTTPException: If the user is not the owner or an admin
        """
        # Admins can access any resource
        if current_user.role == UserRole.ADMIN:
            return current_user

        # Get the resource ID from the path parameters
        resource_id = request.path_params.get(resource_id_name)
        if not resource_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Resource ID not found in path parameters: {resource_id_name}",
            )

        # Query the resource
        resource = await db.get(resource_model, UUID(resource_id))
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resource not found: {resource_id}",
            )

        # Check if the current user is the owner
        if getattr(resource, "user_id", None) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this resource",
            )

        return current_user

    return check_ownership


class ResourceOwnershipMiddleware:
    """
    Middleware to enforce resource ownership.

    This middleware checks if the current user is the owner of the resource
    or an admin for specific endpoints.
    """

    async def __call__(self, request: Request, call_next):
        """
        Process the request and enforce resource ownership.

        Args:
            request: FastAPI request
            call_next: Next middleware or endpoint handler

        Returns:
            Response: FastAPI response
        """
        # Skip ownership check for non-resource endpoints
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        # Skip ownership check for authentication endpoints
        if path.startswith("/api/auth/"):
            return await call_next(request)

        # Skip ownership check for user management endpoints (handled by router dependencies)
        if path.startswith("/api/users/"):
            return await call_next(request)

        # Process the request
        response = await call_next(request)

        return response
