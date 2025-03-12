"""
Chat models for the Agentic System Infrastructure.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Enum for message role."""
    USER = "user"
    AGENT = "agent"


class Citation(BaseModel):
    """Model for citation data."""
    document_id: UUID
    chunk_id: UUID
    text: str
    relevance_score: float


class MessageBase(BaseModel):
    """Base model for message data."""
    role: MessageRole
    content: str


class MessageCreate(MessageBase):
    """Model for message creation."""
    conversation_id: UUID
    citations: Optional[List[Citation]] = None


class MessageResponse(MessageBase):
    """Model for message response."""
    id: UUID
    conversation_id: UUID
    created_at: datetime
    citations: Optional[List[Citation]] = None

    class Config:
        from_attributes = True


class MessageInDB(MessageBase):
    """Model for message in database."""
    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    citations: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    """Base model for conversation data."""
    pass


class ConversationCreate(ConversationBase):
    """Model for conversation creation."""
    agent_id: UUID
    user_id: UUID


class ConversationResponse(ConversationBase):
    """Model for conversation response."""
    id: UUID
    agent_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[MessageResponse]] = None

    class Config:
        from_attributes = True


class ConversationInDB(ConversationBase):
    """Model for conversation in database."""
    id: UUID = Field(default_factory=uuid4)
    agent_id: UUID
    user_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
