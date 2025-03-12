"""
Logging middleware for the Warder application.

This middleware provides comprehensive logging for all requests and responses.
"""

import time
import uuid
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import json
from typing import Callable, Dict, Any

# Configure logging
logger = logging.getLogger("warder.api")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging requests and responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and log details.

        Args:
            request: FastAPI request
            call_next: Next middleware or endpoint handler

        Returns:
            Response: FastAPI response
        """
        # Generate a unique request ID
        request_id = str(uuid.uuid4())

        # Add request ID to request state for use in endpoint handlers
        request.state.request_id = request_id

        # Log request details
        await self._log_request(request, request_id)

        # Process the request and measure execution time
        start_time = time.time()

        try:
            response = await call_next(request)

            # Log response details
            process_time = time.time() - start_time
            self._log_response(request, response, request_id, process_time)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response
        except Exception as e:
            # Log exception details
            process_time = time.time() - start_time
            self._log_exception(request, e, request_id, process_time)
            raise

    async def _log_request(self, request: Request, request_id: str) -> None:
        """
        Log request details.

        Args:
            request: FastAPI request
            request_id: Unique request ID
        """
        # Get client IP
        client_host = request.client.host if request.client else "unknown"

        # Get request path and method
        path = request.url.path
        method = request.method

        # Get request headers (excluding sensitive information)
        headers = dict(request.headers)
        if "authorization" in headers:
            headers["authorization"] = "REDACTED"

        # Get request query parameters
        query_params = dict(request.query_params)

        # Log request body for non-GET requests if not multipart form
        body = {}
        if method != "GET" and not request.headers.get("content-type", "").startswith(
            "multipart/form-data"
        ):
            try:
                body_bytes = await request.body()
                if body_bytes:
                    try:
                        body = json.loads(body_bytes)
                        # Redact sensitive information
                        if "password" in body:
                            body["password"] = "REDACTED"
                    except json.JSONDecodeError:
                        body = {"raw": "non-JSON body"}
            except Exception:
                body = {"error": "Could not read request body"}

        # Create log entry
        log_entry = {
            "request_id": request_id,
            "client_ip": client_host,
            "method": method,
            "path": path,
            "headers": headers,
            "query_params": query_params,
            "body": body,
        }

        logger.info(f"Request: {json.dumps(log_entry)}")

    def _log_response(
        self, request: Request, response: Response, request_id: str, process_time: float
    ) -> None:
        """
        Log response details.

        Args:
            request: FastAPI request
            response: FastAPI response
            request_id: Unique request ID
            process_time: Request processing time in seconds
        """
        # Create log entry
        log_entry = {
            "request_id": request_id,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
            "path": request.url.path,
            "method": request.method,
        }

        logger.info(f"Response: {json.dumps(log_entry)}")

    def _log_exception(
        self,
        request: Request,
        exception: Exception,
        request_id: str,
        process_time: float,
    ) -> None:
        """
        Log exception details.

        Args:
            request: FastAPI request
            exception: Exception that occurred
            request_id: Unique request ID
            process_time: Request processing time in seconds
        """
        # Create log entry
        log_entry = {
            "request_id": request_id,
            "exception": str(exception),
            "exception_type": type(exception).__name__,
            "process_time_ms": round(process_time * 1000, 2),
            "path": request.url.path,
            "method": request.method,
        }

        logger.error(f"Exception: {json.dumps(log_entry)}")
