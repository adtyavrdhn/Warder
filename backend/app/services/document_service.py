"""
Document service for the Warder application.
"""

import logging
import os
import shutil
from typing import List, Optional, BinaryIO
from uuid import UUID
import aiofiles
from fastapi import UploadFile

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.document_fixed import Document, DocumentChunk, DocumentStatus
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentChunkCreate

# Try to import document processing libraries, but handle gracefully if not available
try:
    import fitz  # PyMuPDF
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    PROCESSING_AVAILABLE = True
except ImportError:
    PROCESSING_AVAILABLE = False
    logging.warning(
        "Document processing libraries not available. Processing functionality will be limited."
    )

# Configure logger
logger = logging.getLogger(__name__)

# Document storage directory
DOCUMENT_STORAGE_DIR = os.getenv("DOCUMENT_STORAGE_DIR", "data/documents")


class DocumentService:
    """Service for document-related operations."""

    def __init__(self, db: AsyncSession):
        """Initialize the service with a database session."""
        self.db = db

    async def upload_document(
        self, file: UploadFile, agent_id: Optional[UUID] = None
    ) -> Document:
        """
        Upload a document.

        This method performs the following steps:
        1. Save the uploaded file to the document storage directory
        2. Create a document record in the database
        3. Schedule document processing if appropriate

        Args:
            file: The uploaded file
            agent_id: The associated agent ID (optional)

        Returns:
            The created document

        Raises:
            Exception: If there's an error uploading the document
        """
        try:
            logger.info(f"Uploading document: {file.filename}")

            # Create document storage directory if it doesn't exist
            os.makedirs(DOCUMENT_STORAGE_DIR, exist_ok=True)

            # Generate a unique filename
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{UUID().hex}{file_extension}"
            file_path = os.path.join(DOCUMENT_STORAGE_DIR, unique_filename)

            # Save the file
            async with aiofiles.open(file_path, "wb") as out_file:
                content = await file.read()
                await out_file.write(content)

            # Create document data
            document_data = DocumentCreate(
                filename=file.filename,
                file_type=file_extension.lstrip("."),
                file_size=len(content),
                agent_id=agent_id,
                doc_metadata={
                    "original_filename": file.filename,
                    "content_type": file.content_type,
                },
            )

            # Create document object
            document = Document(
                filename=document_data.filename,
                file_path=file_path,
                file_type=document_data.file_type,
                file_size=document_data.file_size,
                status=DocumentStatus.PENDING,
                doc_metadata=document_data.doc_metadata,
                agent_id=document_data.agent_id,
            )

            # Add to database
            self.db.add(document)
            await self.db.commit()
            await self.db.refresh(document)

            logger.info(f"Document uploaded successfully with ID: {document.id}")

            # Process document if it's a PDF and processing is available
            if document.file_type.lower() == "pdf" and PROCESSING_AVAILABLE:
                # Update status to processing
                document.status = DocumentStatus.PROCESSING
                await self.db.commit()

                # Process document in the background
                try:
                    await self.process_document(document.id)
                except Exception as e:
                    logger.error(f"Error processing document {document.id}: {str(e)}")
                    document.status = DocumentStatus.FAILED
                    document.doc_metadata["processing_error"] = str(e)
                    await self.db.commit()

            return document

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error uploading document: {str(e)}")
            raise

    async def get_document(self, document_id: UUID) -> Optional[Document]:
        """
        Get a document by ID.

        Args:
            document_id: The document ID

        Returns:
            The document if found, None otherwise
        """
        try:
            logger.debug(f"Getting document with ID: {document_id}")
            query = select(Document).where(Document.id == document_id)
            result = await self.db.execute(query)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting document {document_id}: {str(e)}")
            raise

    async def get_all_documents(
        self, agent_id: Optional[UUID] = None
    ) -> List[Document]:
        """
        Get all documents, optionally filtered by agent ID.

        Args:
            agent_id: The agent ID to filter by (optional)

        Returns:
            List of documents
        """
        try:
            logger.debug(
                f"Getting all documents{f' for agent {agent_id}' if agent_id else ''}"
            )

            query = select(Document)
            if agent_id:
                query = query.where(Document.agent_id == agent_id)

            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting documents: {str(e)}")
            raise

    async def update_document(
        self, document_id: UUID, document_data: DocumentUpdate
    ) -> Optional[Document]:
        """
        Update a document.

        Args:
            document_id: The document ID
            document_data: The document data to update

        Returns:
            The updated document if found, None otherwise
        """
        try:
            logger.info(f"Updating document with ID: {document_id}")

            # Get current document
            document = await self.get_document(document_id)
            if not document:
                logger.warning(f"Document with ID {document_id} not found for update")
                return None

            # Update document attributes
            update_data = document_data.model_dump(exclude_unset=True)

            if "doc_metadata" in update_data and update_data["doc_metadata"]:
                # Merge metadata instead of replacing
                document.doc_metadata = {**document.doc_metadata, **update_data["doc_metadata"]}
                del update_data["doc_metadata"]

            # Update other fields
            for key, value in update_data.items():
                setattr(document, key, value)

            # Commit changes
            await self.db.commit()
            await self.db.refresh(document)

            logger.info(f"Document updated successfully with ID: {document_id}")
            return document

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating document with ID {document_id}: {str(e)}")
            raise

    async def delete_document(self, document_id: UUID) -> bool:
        """
        Delete a document.

        This method performs the following steps:
        1. Delete the document file from storage
        2. Delete the document record from the database

        Args:
            document_id: The document ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            logger.info(f"Deleting document with ID: {document_id}")

            # Get document to check if it exists
            document = await self.get_document(document_id)
            if not document:
                logger.warning(f"Document with ID {document_id} not found for deletion")
                return False

            # Delete document file
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
                logger.info(f"Deleted document file: {document.file_path}")

            # Delete document from database (will cascade to chunks)
            await self.db.delete(document)
            await self.db.commit()

            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            raise

    async def process_document(self, document_id: UUID) -> bool:
        """
        Process a document by extracting text and creating chunks.

        Args:
            document_id: The document ID

        Returns:
            True if processed successfully, False otherwise
        """
        if not PROCESSING_AVAILABLE:
            logger.warning(
                "Document processing libraries not available. Skipping document processing."
            )
            return False

        try:
            logger.info(f"Processing document with ID: {document_id}")

            # Get document
            document = await self.get_document(document_id)
            if not document:
                logger.warning(
                    f"Document with ID {document_id} not found for processing"
                )
                return False

            # Update status to processing
            document.status = DocumentStatus.PROCESSING
            await self.db.commit()

            # Process document based on file type
            if document.file_type.lower() == "pdf":
                # Extract text from PDF
                text = self._extract_text_from_pdf(document.file_path)

                # Create chunks
                chunks = self._create_text_chunks(text)

                # Save chunks to database
                for i, chunk_text in enumerate(chunks):
                    chunk = DocumentChunk(
                        document_id=document.id,
                        content=chunk_text,
                        chunk_index=i,
                        doc_metadata={
                            "page": i // 2 + 1,  # Rough estimate
                        },
                    )
                    self.db.add(chunk)

                # Update document status
                document.status = DocumentStatus.PROCESSED
                document.doc_metadata["chunk_count"] = len(chunks)
                await self.db.commit()

                logger.info(
                    f"Document {document_id} processed successfully with {len(chunks)} chunks"
                )
                return True
            else:
                logger.warning(
                    f"Unsupported file type for processing: {document.file_type}"
                )
                document.status = DocumentStatus.FAILED
                document.doc_metadata["processing_error"] = (
                    f"Unsupported file type: {document.file_type}"
                )
                await self.db.commit()
                return False

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error processing document {document_id}: {str(e)}")

            # Update document status to failed
            try:
                document = await self.get_document(document_id)
                if document:
                    document.status = DocumentStatus.FAILED
                    document.doc_metadata["processing_error"] = str(e)
                    await self.db.commit()
            except Exception as update_error:
                logger.error(f"Error updating document status: {str(update_error)}")

            raise

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            Extracted text
        """
        text = ""
        try:
            with fitz.open(file_path) as pdf:
                for page in pdf:
                    text += page.get_text()
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise

    def _create_text_chunks(
        self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200
    ) -> List[str]:
        """
        Create text chunks from a document.

        Args:
            text: The document text
            chunk_size: The chunk size
            chunk_overlap: The chunk overlap

        Returns:
            List of text chunks
        """
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
            )
            return text_splitter.split_text(text)
        except Exception as e:
            logger.error(f"Error creating text chunks: {str(e)}")
            raise
