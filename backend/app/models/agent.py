"""
Agent model for the Warder application.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from app.utils.database import Base


class AgentType(str, enum.Enum):
    """Enum for agent types."""

    RAG = "rag"
    CHAT = "chat"
    FUNCTION = "function"
    CUSTOM = "custom"


class AgentStatus(str, enum.Enum):
    """Enum for agent status."""

    CREATING = "creating"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    STOPPED = "stopped"
    FAILED = "failed"
    DELETED = "deleted"


class Agent(Base):
    """Agent model."""

    __tablename__ = "agents"
    __table_args__ = {"schema": "warder"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    type = Column(Enum(AgentType), nullable=False, default=AgentType.RAG)
    status = Column(Enum(AgentStatus), nullable=False, default=AgentStatus.CREATING)
    config = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    def __repr__(self):
        """String representation of the agent."""
        return f"<Agent(id={self.id}, name={self.name}, type={self.type}, status={self.status})>"
