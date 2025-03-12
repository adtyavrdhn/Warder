"""
Main module for the Warder agent.
"""

import os
import json
import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("warder-agent")

# Add the parent directory to the path so we can import agno
sys.path.append("/app")

# Try to import agno
try:
    from agno import Agent, KnowledgeBase

    AGNO_AVAILABLE = True
    logger.info("Agno is available")
except ImportError:
    AGNO_AVAILABLE = False
    logger.warning("Agno is not available. Using fallback mode.")

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


# Initialize agent
agent = None


def initialize_agent():
    """Initialize the agent with the configuration from environment variables."""
    global agent

    if not AGNO_AVAILABLE:
        logger.warning("Cannot initialize Agno agent: Agno is not available")
        return

    try:
        # Get agent configuration from environment variables
        agent_type = os.environ.get("AGENT_TYPE", "chat")
        agent_id = os.environ.get("AGENT_ID", "default")
        agent_name = os.environ.get("AGENT_NAME", "Warder Agent")

        # Get knowledge base configuration if available
        knowledge_path = os.environ.get("KNOWLEDGE_PATH")

        # Initialize knowledge base if path is provided
        knowledge_base = None
        if knowledge_path:
            logger.info(f"Initializing knowledge base from {knowledge_path}")
            knowledge_base = KnowledgeBase(path=knowledge_path)
            knowledge_base.load(recreate=False)

        # Initialize agent
        logger.info(
            f"Initializing agent: {agent_name} (ID: {agent_id}, Type: {agent_type})"
        )
        agent = Agent(
            knowledge=knowledge_base,
            search_knowledge=True if knowledge_base else False,
        )

        logger.info("Agent initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing agent: {str(e)}")
        agent = None


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

    # Use the agent to generate a response if available
    if agent and AGNO_AVAILABLE:
        try:
            # Get response from the agent
            agent_response = agent.get_response(message.content)
            logger.info(f"Agent response: {agent_response}")
            return Response(content=agent_response)
        except Exception as e:
            logger.error(f"Error getting response from agent: {str(e)}")
            # Fall back to echo response if there's an error
            return Response(content=f"Error: {str(e)}")
    else:
        # Simple echo response for testing when agent is not available
        logger.warning("Agent not available. Using echo response.")
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
    # Initialize the agent
    initialize_agent()

    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8080))

    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=port)
