"""
Agent models for the Agentic System Infrastructure.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Enum for agent status."""

    DEPLOYING = "deploying"
    ACTIVE = "active"
    STOPPED = "stopped"
    ERROR = "error"


class AgentBase(BaseModel):
    """Base model for agent data."""

    name: str


class AgentCreate(AgentBase):
    """Model for agent creation."""

    pass


class AgentUpdate(BaseModel):
    """Model for agent update."""

    name: Optional[str] = None
    status: Optional[AgentStatus] = None


class AgentResponse(AgentBase):
    """Model for agent response."""

    id: UUID
    user_id: UUID
    status: AgentStatus
    container_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentInDB(AgentBase):
    """Model for agent in database."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    status: AgentStatus = AgentStatus.DEPLOYING
    container_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True
