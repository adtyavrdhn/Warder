"""
Router for document-related endpoints.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.document import DocumentResponse, DocumentUpdate
from app.services.document_service import DocumentService
from app.utils.database import get_db

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.post(
    "/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    file: UploadFile = File(...),
    agent_id: Optional[UUID] = Form(None),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Upload a document.

    Args:
        file: The document file to upload
        agent_id: The associated agent ID (optional)
        db: Database session

    Returns:
        The uploaded document

    Raises:
        HTTPException: If there's an error uploading the document
    """
    try:
        logger.info(f"Received request to upload document: {file.filename}")

        # Create document service
        service = DocumentService(db)

        # Upload document
        document = await service.upload_document(file, agent_id)

        # Convert to response model
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            file_type=document.file_type,
            file_size=document.file_size,
            status=document.status,
            doc_metadata=document.doc_metadata,
            agent_id=document.agent_id,
            created_at=document.created_at.isoformat(),
            updated_at=document.updated_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}",
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID, db: AsyncSession = Depends(get_db)
) -> DocumentResponse:
    """
    Get a document by ID.

    Args:
        document_id: The document ID
        db: Database session

    Returns:
        The document

    Raises:
        HTTPException: If the document is not found
    """
    try:
        logger.info(f"Received request to get document: {document_id}")

        # Create document service
        service = DocumentService(db)

        # Get document
        document = await service.get_document(document_id)

        # Check if document exists
        if not document:
            logger.warning(f"Document with ID {document_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found",
            )

        # Convert to response model
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            file_type=document.file_type,
            file_size=document.file_size,
            status=document.status,
            doc_metadata=document.doc_metadata,
            agent_id=document.agent_id,
            created_at=document.created_at.isoformat(),
            updated_at=document.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting document: {str(e)}",
        )


@router.get("/", response_model=List[DocumentResponse])
async def get_all_documents(
    agent_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
) -> List[DocumentResponse]:
    """
    Get all documents, optionally filtered by agent ID.

    Args:
        agent_id: The agent ID to filter by (optional)
        db: Database session

    Returns:
        List of documents
    """
    try:
        logger.info(
            f"Received request to get all documents{f' for agent {agent_id}' if agent_id else ''}"
        )

        # Create document service
        service = DocumentService(db)

        # Get all documents
        documents = await service.get_all_documents(agent_id)

        # Convert to response models
        return [
            DocumentResponse(
                id=document.id,
                filename=document.filename,
                file_type=document.file_type,
                file_size=document.file_size,
                status=document.status,
                doc_metadata=document.doc_metadata,
                agent_id=document.agent_id,
                created_at=document.created_at.isoformat(),
                updated_at=document.updated_at.isoformat(),
            )
            for document in documents
        ]

    except Exception as e:
        logger.error(f"Error getting all documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting all documents: {str(e)}",
        )


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    document_data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Update a document.

    Args:
        document_id: The document ID
        document_data: The document data to update
        db: Database session

    Returns:
        The updated document

    Raises:
        HTTPException: If the document is not found
    """
    try:
        logger.info(f"Received request to update document: {document_id}")

        # Create document service
        service = DocumentService(db)

        # Update document
        document = await service.update_document(document_id, document_data)

        # Check if document exists
        if not document:
            logger.warning(f"Document with ID {document_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found",
            )

        # Convert to response model
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            file_type=document.file_type,
            file_size=document.file_size,
            status=document.status,
            doc_metadata=document.doc_metadata,
            agent_id=document.agent_id,
            created_at=document.created_at.isoformat(),
            updated_at=document.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating document: {str(e)}",
        )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a document.

    Args:
        document_id: The document ID
        db: Database session

    Raises:
        HTTPException: If the document is not found
    """
    try:
        logger.info(f"Received request to delete document: {document_id}")

        # Create document service
        service = DocumentService(db)

        # Delete document
        deleted = await service.delete_document(document_id)

        # Check if document was deleted
        if not deleted:
            logger.warning(f"Document with ID {document_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}",
        )


@router.post("/{document_id}/process", response_model=DocumentResponse)
async def process_document(
    document_id: UUID, db: AsyncSession = Depends(get_db)
) -> DocumentResponse:
    """
    Process a document.

    Args:
        document_id: The document ID
        db: Database session

    Returns:
        The processed document

    Raises:
        HTTPException: If the document is not found or there's an error processing it
    """
    try:
        logger.info(f"Received request to process document: {document_id}")

        # Create document service
        service = DocumentService(db)

        # Get document
        document = await service.get_document(document_id)

        # Check if document exists
        if not document:
            logger.warning(f"Document with ID {document_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found",
            )

        # Process document
        await service.process_document(document_id)

        # Get updated document
        document = await service.get_document(document_id)

        # Convert to response model
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            file_type=document.file_type,
            file_size=document.file_size,
            status=document.status,
            doc_metadata=document.doc_metadata,
            agent_id=document.agent_id,
            created_at=document.created_at.isoformat(),
            updated_at=document.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}",
        )
