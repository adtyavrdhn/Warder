"""
Warder Agentic System - Main Application
A simplified monolithic backend for the Warder system
"""

import os
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import agent_router, document_router, auth_router, user_router
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.error_middleware import ErrorHandlingMiddleware
from app.utils.database import init_db, create_tables
from app.utils.logging_config import configure_logging

# Configure logging
logger = configure_logging("warder_app")

# Create FastAPI app
app = FastAPI(
    title="Warder Agentic System",
    description="Unified API for the Warder Agentic System",
    version="0.1.0",
)

# Configure middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Add error handling middleware
app.add_middleware(ErrorHandlingMiddleware)


# Initialize database and create necessary directories on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and create necessary directories on startup."""
    try:
        logger.info("Initializing database connection")
        await init_db()
        await create_tables()
        logger.info("Database connection initialized successfully")

        # Create data directories if they don't exist
        os.makedirs("data/knowledge_base", exist_ok=True)
        logger.info("Knowledge base directory created")

    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "warder_app"}


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the Warder Agentic System"}


# Include routers
app.include_router(auth_router.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(user_router.router, prefix="/api/users", tags=["Users"])
app.include_router(agent_router.router, prefix="/api/agents", tags=["Agents"])
app.include_router(document_router.router, prefix="/api/documents", tags=["Documents"])


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    # Get port from environment variable or use default
    port = int(os.getenv("PORT", "8000"))

    # Run the application
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
