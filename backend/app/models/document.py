"""
Document model for the Warder application.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Integer, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from app.utils.database import Base


class DocumentStatus(str, enum.Enum):
    """Enum for document status."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Document(Base):
    """Document model."""

    __tablename__ = "documents"
    __table_args__ = {"schema": "warder"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    status = Column(
        Enum(DocumentStatus), nullable=False, default=DocumentStatus.PENDING
    )
    doc_metadata = Column(JSON, nullable=False, default={})
    agent_id = Column(UUID(as_uuid=True), ForeignKey("warder.agents.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    # Relationship with chunks
    chunks = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self):
        """String representation of the document."""
        return (
            f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"
        )


class DocumentChunk(Base):
    """Document chunk model for storing text chunks of documents."""

    __tablename__ = "document_chunks"
    __table_args__ = {"schema": "warder"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("warder.documents.id"), nullable=False
    )
    content = Column(Text, nullable=False)
    doc_metadata = Column(JSON, nullable=False, default={})
    chunk_index = Column(Integer, nullable=False)
    embedding_id = Column(
        String, nullable=True
    )  # Reference to vector store embedding if applicable
    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))

    # Relationship with document
    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        """String representation of the document chunk."""
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"
