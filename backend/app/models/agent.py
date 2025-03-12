# /Users/adivardh/Warder/backend/app/models/agent.py
"""
Agent model for the Warder application.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
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
    user_id = Column(UUID(as_uuid=True), ForeignKey("warder.users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="agents")

    def __repr__(self):
        """String representation of the agent."""
        return f"<Agent(id={self.id}, name={self.name}, type={self.type}, status={self.status})>"
