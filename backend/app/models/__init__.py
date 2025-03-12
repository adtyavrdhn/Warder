"""
Models package for the Warder application.
"""

# Import models to register them with SQLAlchemy
from app.models.agent import Agent, AgentType, AgentStatus
from app.models.document_fixed import Document, DocumentChunk, DocumentStatus
