"""
API Gateway main application.
"""

import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Create FastAPI app
app = FastAPI(
    title="Warder Agentic System API Gateway",
    description="API Gateway for the Warder Agentic System Infrastructure",
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


# Health check endpoint
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "api_gateway"}


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the Warder Agentic System API Gateway"}


# Include routers
# from app.routers import auth, agents, documents, chat

# app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
# app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
# app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])


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
    port = int(os.getenv("PORT", "8000"))

    # Run the application
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
