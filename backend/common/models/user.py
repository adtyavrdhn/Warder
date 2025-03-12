"""
User models for authentication and authorization.
"""
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base model for user data."""
    username: str
    email: EmailStr


class UserCreate(UserBase):
    """Model for user creation."""
    password: str


class UserResponse(UserBase):
    """Model for user response."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserInDB(UserBase):
    """Model for user in database."""
    id: UUID = Field(default_factory=uuid4)
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Model for authentication token."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Model for token data."""
    user_id: UUID
    username: str
