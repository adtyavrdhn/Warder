"""
Agent schemas for the Warder application.
"""

from typing import Dict, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.agent import AgentType, AgentStatus


class KnowledgeBaseConfig(BaseModel):
    """Configuration for knowledge base."""

    directory: str = Field(default="data/pdfs")
    recreate: bool = Field(default=False)
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)


class AgentCreate(BaseModel):
    """Schema for creating an agent."""

    name: str = Field(..., description="Name of the agent")
    description: Optional[str] = Field(None, description="Description of the agent")
    type: AgentType = Field(default=AgentType.RAG, description="Type of the agent")
    knowledge_base: Optional[KnowledgeBaseConfig] = Field(
        default=None, description="Knowledge base configuration"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Additional configuration"
    )


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""

    name: Optional[str] = Field(None, description="Name of the agent")
    description: Optional[str] = Field(None, description="Description of the agent")
    status: Optional[AgentStatus] = Field(None, description="Status of the agent")
    config: Optional[Dict[str, Any]] = Field(
        None, description="Additional configuration"
    )


class AgentResponse(BaseModel):
    """Schema for agent response."""

    id: UUID = Field(..., description="Agent ID")
    name: str = Field(..., description="Name of the agent")
    description: Optional[str] = Field(None, description="Description of the agent")
    type: AgentType = Field(..., description="Type of the agent")
    status: AgentStatus = Field(..., description="Status of the agent")
    config: Dict[str, Any] = Field(..., description="Additional configuration")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True
