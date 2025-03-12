# /Users/adivardh/Warder/backend/app/routers/user_router.py
"""
Router for user-related endpoints.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.user import User, UserStatus, UserRole
from app.schemas.user import UserResponse, UserUpdate
from app.utils.auth import get_current_user, get_current_admin_user, get_user_by_id
from app.utils.database import get_db

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current user information.

    Args:
        current_user: The current user

    Returns:
        The current user information
    """
    logger.info(f"Getting information for user: {current_user.username}")

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role,
        status=current_user.status,
        verified=current_user.verified,
        preferences=current_user.preferences,
        quota=current_user.quota,
        usage=current_user.usage,
        created_at=current_user.created_at.isoformat(),
        updated_at=current_user.updated_at.isoformat(),
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update current user information.

    Args:
        user_data: The user data to update
        current_user: The current user
        db: Database session

    Returns:
        The updated user information

    Raises:
        HTTPException: If there's an error updating the user
    """
    try:
        logger.info(f"Updating user: {current_user.username}")

        # Update user attributes
        update_data = user_data.model_dump(exclude_unset=True)

        # Don't allow users to update their own role or status
        if "role" in update_data:
            del update_data["role"]
        if "status" in update_data:
            del update_data["status"]

        # Hash password if provided
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = User.hash_password(
                update_data.pop("password")
            )

        # Update user
        for key, value in update_data.items():
            setattr(current_user, key, value)

        await db.commit()
        await db.refresh(current_user)

        logger.info(f"User {current_user.username} updated successfully")

        return UserResponse(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            role=current_user.role,
            status=current_user.status,
            verified=current_user.verified,
            preferences=current_user.preferences,
            quota=current_user.quota,
            usage=current_user.usage,
            created_at=current_user.created_at.isoformat(),
            updated_at=current_user.updated_at.isoformat(),
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating user {current_user.username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}",
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Get a user by ID (admin only).

    Args:
        user_id: The user ID
        current_user: The current admin user
        db: Database session

    Returns:
        The user information

    Raises:
        HTTPException: If the user is not found
    """
    try:
        logger.info(f"Admin {current_user.username} getting user with ID: {user_id}")

        # Get user
        user = await get_user_by_id(db, user_id)

        # Check if user exists
        if not user:
            logger.warning(f"User with ID {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            status=user.status,
            verified=user.verified,
            preferences=user.preferences,
            quota=user.quota,
            usage=user.usage,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user: {str(e)}",
        )


@router.get("/", response_model=List[UserResponse])
async def get_all_users(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> List[UserResponse]:
    """
    Get all users (admin only).

    Args:
        current_user: The current admin user
        db: Database session

    Returns:
        List of all users
    """
    try:
        logger.info(f"Admin {current_user.username} getting all users")

        # Get all users
        query = select(User)
        result = await db.execute(query)
        users = result.scalars().all()

        return [
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                status=user.status,
                verified=user.verified,
                preferences=user.preferences,
                quota=user.quota,
                usage=user.usage,
                created_at=user.created_at.isoformat(),
                updated_at=user.updated_at.isoformat(),
            )
            for user in users
        ]

    except Exception as e:
        logger.error(f"Error getting all users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting all users: {str(e)}",
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update a user (admin only).

    Args:
        user_id: The user ID
        user_data: The user data to update
        current_user: The current admin user
        db: Database session

    Returns:
        The updated user information

    Raises:
        HTTPException: If the user is not found or there's an error updating the user
    """
    try:
        logger.info(f"Admin {current_user.username} updating user with ID: {user_id}")

        # Get user
        user = await get_user_by_id(db, user_id)

        # Check if user exists
        if not user:
            logger.warning(f"User with ID {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )

        # Update user attributes
        update_data = user_data.model_dump(exclude_unset=True)

        # Hash password if provided
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = User.hash_password(
                update_data.pop("password")
            )

        # Update user
        for key, value in update_data.items():
            setattr(user, key, value)

        await db.commit()
        await db.refresh(user)

        logger.info(
            f"User {user.username} updated successfully by admin {current_user.username}"
        )

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            status=user.status,
            verified=user.verified,
            preferences=user.preferences,
            quota=user.quota,
            usage=user.usage,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}",
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a user (admin only).

    Args:
        user_id: The user ID
        current_user: The current admin user
        db: Database session

    Raises:
        HTTPException: If the user is not found or there's an error deleting the user
    """
    try:
        logger.info(f"Admin {current_user.username} deleting user with ID: {user_id}")

        # Get user
        user = await get_user_by_id(db, user_id)

        # Check if user exists
        if not user:
            logger.warning(f"User with ID {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )

        # Don't allow deleting the last admin
        if user.role == UserRole.ADMIN:
            # Check if there are other admins
            query = select(User).where(User.role == UserRole.ADMIN, User.id != user_id)
            result = await db.execute(query)
            other_admins = result.scalars().all()

            if not other_admins:
                logger.warning(f"Cannot delete the last admin user: {user.username}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the last admin user",
                )

        # Delete user
        await db.delete(user)
        await db.commit()

        logger.info(
            f"User {user.username} deleted successfully by admin {current_user.username}"
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}",
        )


@router.post("/{user_id}/verify", response_model=UserResponse)
async def verify_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Verify a user (admin only).

    Args:
        user_id: The user ID
        current_user: The current admin user
        db: Database session

    Returns:
        The verified user information

    Raises:
        HTTPException: If the user is not found or there's an error verifying the user
    """
    try:
        logger.info(f"Admin {current_user.username} verifying user with ID: {user_id}")

        # Get user
        user = await get_user_by_id(db, user_id)

        # Check if user exists
        if not user:
            logger.warning(f"User with ID {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )

        # Verify user
        user.verified = True
        user.status = UserStatus.ACTIVE

        await db.commit()
        await db.refresh(user)

        logger.info(
            f"User {user.username} verified successfully by admin {current_user.username}"
        )

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            status=user.status,
            verified=user.verified,
            preferences=user.preferences,
            quota=user.quota,
            usage=user.usage,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error verifying user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying user: {str(e)}",
        )
