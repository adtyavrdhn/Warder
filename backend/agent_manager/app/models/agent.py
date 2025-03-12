"""
Agent database model for the Agent Manager service.
"""

from datetime import datetime
from typing import Dict, Any
from uuid import UUID

from sqlalchemy import Column, String, DateTime, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from common.utils.db import Base
from app.schemas.agent import AgentType, AgentStatus


class Agent(Base):
    """Agent database model."""

    __tablename__ = "agents"
    __table_args__ = {"schema": "warder"}

    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    type = Column(Enum(AgentType), nullable=False, default=AgentType.RAG)
    status = Column(Enum(AgentStatus), nullable=False, default=AgentStatus.CREATING)
    config = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"<Agent(id={self.id}, name={self.name}, type={self.type}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert the agent to a dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "type": self.type.value if self.type else None,
            "status": self.status.value if self.status else None,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
