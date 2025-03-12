"""
Document schemas for the Warder application.
"""

from typing import Dict, Optional, Any, List
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.document_fixed import DocumentStatus


class DocumentCreate(BaseModel):
    """Schema for document metadata after upload."""

    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File type/extension")
    file_size: int = Field(..., description="File size in bytes")
    agent_id: Optional[UUID] = Field(None, description="Associated agent ID")
    doc_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""

    status: Optional[DocumentStatus] = Field(None, description="Document status")
    doc_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DocumentResponse(BaseModel):
    """Schema for document response."""

    id: UUID = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File type/extension")
    file_size: int = Field(..., description="File size in bytes")
    status: DocumentStatus = Field(..., description="Document status")
    doc_metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    agent_id: Optional[UUID] = Field(None, description="Associated agent ID")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True


class DocumentChunkCreate(BaseModel):
    """Schema for creating a document chunk."""

    document_id: UUID = Field(..., description="Document ID")
    content: str = Field(..., description="Chunk content")
    chunk_index: int = Field(..., description="Index of the chunk in the document")
    doc_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class DocumentChunkResponse(BaseModel):
    """Schema for document chunk response."""

    id: UUID = Field(..., description="Chunk ID")
    document_id: UUID = Field(..., description="Document ID")
    content: str = Field(..., description="Chunk content")
    chunk_index: int = Field(..., description="Index of the chunk in the document")
    doc_metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    embedding_id: Optional[str] = Field(None, description="Vector store embedding ID")
    created_at: str = Field(..., description="Creation timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True
