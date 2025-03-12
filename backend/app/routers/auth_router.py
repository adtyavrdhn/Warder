# /Users/adivardh/Warder/backend/app/routers/auth_router.py
"""
Router for authentication-related endpoints.
"""

import logging
from datetime import timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserStatus
from app.schemas.user import UserCreate, UserResponse
from app.utils.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_user_by_username,
    get_user_by_email,
    get_user_by_id,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.utils.database import get_db

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_data: UserCreate, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Register a new user.

    Args:
        user_data: The user data to create
        db: Database session

    Returns:
        The created user

    Raises:
        HTTPException: If there's an error creating the user
    """
    try:
        logger.info(f"Received request to register user: {user_data.username}")

        # Check if username already exists
        existing_user = await get_user_by_username(db, user_data.username)
        if existing_user:
            logger.warning(f"Username {user_data.username} already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username {user_data.username} already exists",
            )

        # Check if email already exists
        existing_user = await get_user_by_email(db, user_data.email)
        if existing_user:
            logger.warning(f"Email {user_data.email} already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email {user_data.email} already exists",
            )

        # Create user object
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=User.hash_password(user_data.password),
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role,
            status=UserStatus.PENDING_VERIFICATION,
            verified=False,
        )

        # Add to database
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # TODO: Send verification email

        logger.info(f"User {user_data.username} registered successfully")

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
        logger.error(f"Error registering user: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering user: {str(e)}",
        )


@router.post("/login")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get an access token.

    Args:
        form_data: The form data with username and password
        db: Database session

    Returns:
        The access token and token type

    Raises:
        HTTPException: If authentication fails
    """
    try:
        logger.info(f"Received login request for user: {form_data.username}")

        user = await authenticate_user(db, form_data.username, form_data.password)
        if not user:
            logger.warning(f"Invalid credentials for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if user.status != UserStatus.ACTIVE:
            logger.warning(f"User {form_data.username} is {user.status}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User account is {user.status}",
            )

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )

        # Create refresh token
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        logger.info(f"User {form_data.username} logged in successfully")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": str(user.id),
            "username": user.username,
            "role": user.role,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during login: {str(e)}",
        )


from pydantic import BaseModel


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Refresh an access token.

    Args:
        refresh_token: The refresh token
        db: Database session

    Returns:
        The new access token and token type

    Raises:
        HTTPException: If the refresh token is invalid
    """
    try:
        from jose import jwt, JWTError
        from app.utils.auth import SECRET_KEY, ALGORITHM

        try:
            payload = jwt.decode(
                token_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM]
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user
        from uuid import UUID

        user = await get_user_by_id(db, UUID(user_id))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User account is {user.status}",
            )

        # Create new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )

        logger.info(f"Access token refreshed for user: {user.username}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing token: {str(e)}",
        )
