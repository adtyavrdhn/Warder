# /Users/adivardh/Warder/backend/app/schemas/agent.py
"""
Agent schemas for the Warder application.
"""

from typing import Dict, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.agent import AgentType, AgentStatus, ContainerStatus


class KnowledgeBaseConfig(BaseModel):
    """Configuration for knowledge base."""

    directory: str = Field(default="data/pdfs")
    recreate: bool = Field(default=False)
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)


class ContainerConfig(BaseModel):
    """Configuration for agent container."""

    image: str = Field(
        default="warder/agent:latest", description="Docker image for the agent"
    )
    memory_limit: str = Field(
        default="512m", description="Memory limit for the container"
    )
    cpu_limit: float = Field(default=0.5, description="CPU limit for the container")
    env_vars: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )
    auto_start: bool = Field(
        default=True, description="Whether to start the container automatically"
    )


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
    container_config: Optional[ContainerConfig] = Field(
        default=None, description="Container configuration"
    )
    user_id: UUID = Field(..., description="ID of the user who owns this agent")


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""

    name: Optional[str] = Field(None, description="Name of the agent")
    description: Optional[str] = Field(None, description="Description of the agent")
    status: Optional[AgentStatus] = Field(None, description="Status of the agent")
    config: Optional[Dict[str, Any]] = Field(
        None, description="Additional configuration"
    )
    container_status: Optional[ContainerStatus] = Field(
        None, description="Container status"
    )
    container_config: Optional[Dict[str, Any]] = Field(
        None, description="Container configuration"
    )


class AgentResponse(BaseModel):
    """Schema for agent response."""

    id: UUID = Field(..., description="Agent ID")
    name: str = Field(..., description="Name of the agent")
    description: Optional[str] = Field(None, description="Description of the agent")
    type: AgentType = Field(..., description="Type of the agent")
    status: AgentStatus = Field(..., description="Status of the agent")
    config: Dict[str, Any] = Field(..., description="Additional configuration")
    user_id: UUID = Field(..., description="ID of the user who owns this agent")

    # Container-related fields
    container_id: Optional[str] = Field(None, description="Container ID")
    container_name: Optional[str] = Field(None, description="Container name")
    container_status: ContainerStatus = Field(..., description="Container status")
    container_config: Dict[str, Any] = Field(..., description="Container configuration")
    host_port: Optional[str] = Field(None, description="Host port for the container")

    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True
