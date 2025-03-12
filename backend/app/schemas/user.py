# /Users/adivardh/Warder/backend/app/schemas/user.py
"""
User schemas for the Warder application.
"""

from typing import Dict, Optional, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, validator
import re

from app.models.user import UserRole, UserStatus


class UserBase(BaseModel):
    """Base schema for user data."""

    username: str = Field(..., description="Username")
    email: EmailStr = Field(..., description="Email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")

    @validator("username")
    def username_alphanumeric(cls, v):
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Username must be alphanumeric with optional underscores and hyphens"
            )
        return v


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(..., description="Password", min_length=8)
    role: UserRole = Field(default=UserRole.USER, description="User role")

    @validator("password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        return v


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: Optional[EmailStr] = Field(None, description="Email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    password: Optional[str] = Field(None, description="Password", min_length=8)
    role: Optional[UserRole] = Field(None, description="User role")
    status: Optional[UserStatus] = Field(None, description="User status")
    verified: Optional[bool] = Field(None, description="Verification status")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    quota: Optional[Dict[str, Any]] = Field(None, description="User quota")

    @validator("password")
    def password_strength(cls, v):
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        return v


class UserResponse(UserBase):
    """Schema for user response."""

    id: UUID = Field(..., description="User ID")
    role: UserRole = Field(..., description="User role")
    status: UserStatus = Field(..., description="User status")
    verified: bool = Field(..., description="Verification status")
    preferences: Dict[str, Any] = Field(..., description="User preferences")
    quota: Dict[str, Any] = Field(..., description="User quota")
    usage: Dict[str, Any] = Field(..., description="User usage")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True


class UserInDB(UserResponse):
    """Schema for user in database (includes hashed password)."""

    hashed_password: str = Field(..., description="Hashed password")
