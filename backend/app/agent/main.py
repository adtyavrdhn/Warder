"""
Main module for the Warder agent.
"""

import os
import json
import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("warder-agent")

# Create FastAPI app
app = FastAPI(title="Warder Agent", description="API for Warder agent")


class Message(BaseModel):
    """Message model for agent communication."""

    content: str
    role: str = "user"


class Response(BaseModel):
    """Response model for agent communication."""

    content: str
    role: str = "assistant"


@app.get("/")
async def root():
    """Root endpoint for the agent."""
    return {"status": "ok", "message": "Warder agent is running"}


@app.get("/health")
async def health():
    """Health check endpoint for the agent."""
    return {"status": "healthy"}


@app.post("/chat", response_model=Response)
async def chat(message: Message):
    """Chat endpoint for the agent."""
    logger.info(f"Received message: {message.content}")

    # Simple echo response for testing
    return Response(content=f"Echo: {message.content}")


@app.get("/info")
async def info():
    """Info endpoint for the agent."""
    # Get environment variables
    env_vars = {k: v for k, v in os.environ.items() if not k.startswith("_")}

    return {
        "agent_type": os.environ.get("AGENT_TYPE", "chat"),
        "model": os.environ.get("MODEL", "gpt-3.5-turbo"),
        "env_vars": env_vars,
    }


if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8080))

    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=port)
