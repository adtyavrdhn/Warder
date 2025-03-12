"""
Error handling middleware for the Warder application.

This middleware provides consistent error handling and response formatting
for all exceptions that occur during request processing.
"""

import logging
import traceback
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from typing import Callable, Dict, Any

# Configure logging
logger = logging.getLogger("warder.api")


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling errors and exceptions.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and handle any errors.

        Args:
            request: FastAPI request
            call_next: Next middleware or endpoint handler

        Returns:
            Response: FastAPI response
        """
        try:
            return await call_next(request)
        except Exception as e:
            # Get request ID from request state if available
            request_id = getattr(request.state, "request_id", "unknown")

            # Log the exception with stack trace
            logger.error(
                f"Unhandled exception for request {request_id}: {str(e)}\n"
                f"Stack trace: {traceback.format_exc()}"
            )

            # Handle specific exception types
            if isinstance(e, SQLAlchemyError):
                return self._handle_database_error(e, request_id)
            elif isinstance(e, ValidationError):
                return self._handle_validation_error(e, request_id)
            else:
                return self._handle_generic_error(e, request_id)

    def _handle_database_error(
        self, error: SQLAlchemyError, request_id: str
    ) -> JSONResponse:
        """
        Handle database-related errors.

        Args:
            error: SQLAlchemy error
            request_id: Unique request ID

        Returns:
            JSONResponse: JSON response with error details
        """
        return JSONResponse(
            status_code=500,
            content={
                "error": "Database error",
                "detail": str(error),
                "request_id": request_id,
                "type": "database_error",
            },
        )

    def _handle_validation_error(
        self, error: ValidationError, request_id: str
    ) -> JSONResponse:
        """
        Handle validation errors.

        Args:
            error: Pydantic validation error
            request_id: Unique request ID

        Returns:
            JSONResponse: JSON response with error details
        """
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation error",
                "detail": error.errors(),
                "request_id": request_id,
                "type": "validation_error",
            },
        )

    def _handle_generic_error(self, error: Exception, request_id: str) -> JSONResponse:
        """
        Handle generic errors.

        Args:
            error: Generic exception
            request_id: Unique request ID

        Returns:
            JSONResponse: JSON response with error details
        """
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(error),
                "request_id": request_id,
                "type": "internal_error",
            },
        )
