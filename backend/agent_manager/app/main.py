"""
Agent Manager main application.
"""

import os
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import agent
from config.logging import configure_logging
from common.utils.db import init_db
from config.db import KNOWLEDGE_BASE_DIR

# Configure logging
logger = configure_logging("agent_manager")

# Create FastAPI app
app = FastAPI(
    title="Warder Agent Manager",
    description="Agent Manager for the Warder Agentic System Infrastructure",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        logger.info("Initializing database connection")
        await init_db()
        logger.info("Database connection initialized successfully")

        # Create data directories if they don't exist
        os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)
        logger.info(f"Knowledge base directory created: {KNOWLEDGE_BASE_DIR}")

    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "agent_manager"}


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the Warder Agent Manager"}


# Include routers
app.include_router(agent.router, prefix="/agents", tags=["Agents"])


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
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    # Get port from environment variable or use default
    port = int(os.getenv("PORT", "8001"))

    # Run the application
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
