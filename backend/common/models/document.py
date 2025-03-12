"""
Document models for the Agentic System Infrastructure.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    """Enum for document status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class DocumentBase(BaseModel):
    """Base model for document data."""
    original_name: str
    mime_type: str
    size_bytes: int


class DocumentCreate(DocumentBase):
    """Model for document creation."""
    agent_id: UUID
    storage_path: str


class DocumentUpdate(BaseModel):
    """Model for document update."""
    status: Optional[DocumentStatus] = None


class DocumentResponse(DocumentBase):
    """Model for document response."""
    id: UUID
    agent_id: UUID
    storage_path: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentInDB(DocumentBase):
    """Model for document in database."""
    id: UUID = Field(default_factory=uuid4)
    agent_id: UUID
    storage_path: str
    status: DocumentStatus = DocumentStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class ChunkStrategy(str, Enum):
    """Enum for chunk strategy."""
    FIXED_SIZE = "fixed_size"
    PARAGRAPH = "paragraph"
    SECTION = "section"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class ChunkBase(BaseModel):
    """Base model for chunk data."""
    chunk_text: str
    chunk_strategy: ChunkStrategy


class ChunkCreate(ChunkBase):
    """Model for chunk creation."""
    document_id: UUID
    chunk_index: int
    embedding: Optional[list[float]] = None


class ChunkResponse(ChunkBase):
    """Model for chunk response."""
    id: UUID
    document_id: UUID
    chunk_index: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChunkInDB(ChunkBase):
    """Model for chunk in database."""
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    chunk_index: int
    embedding: Optional[list[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
