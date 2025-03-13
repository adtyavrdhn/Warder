"""
Main module for the Warder agent.
"""

import os
import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from agno.agent import Agent
from pydantic import BaseModel
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("warder-agent")

sys.path.append("/app")

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


class Query(BaseModel):
    """Query model for direct agent queries."""

    query: str


# Initialize agent
agent = None


def initialize_agent():
    """Initialize the agent with the configuration from environment variables."""
    global agent

    try:
        agent_type = os.environ.get("AGENT_TYPE", "rag")
        agent_id = os.environ.get("AGENT_ID", "default")
        agent_name = os.environ.get("AGENT_NAME", "Warder Agent")

        # Get knowledge base configuration if available
        knowledge_path = os.environ.get("KNOWLEDGE_PATH")

        # Initialize knowledge base if path is provided
        knowledge_base = None
        if knowledge_path:
            logger.info(f"Initializing knowledge base from {knowledge_path}")

            # Get database configuration from environment variables
            db_url = os.environ.get(
                "VECTOR_DB_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai"
            )
            table_name = os.environ.get("VECTOR_DB_TABLE", "pdf_documents")
            recreate = os.environ.get("KB_RECREATE", "False").lower() == "true"
            chunk_size = int(os.environ.get("KB_CHUNK_SIZE", "1000"))

            # Initialize PDF knowledge base using the correct pattern
            from agno.knowledge.pdf import PDFKnowledgeBase, PDFReader
            from agno.vectordb.pgvector import PgVector

            logger.info(
                f"Initializing PDF knowledge base with vector DB: {db_url}, table: {table_name}"
            )
            knowledge_base = PDFKnowledgeBase(
                path=knowledge_path,
                vector_db=PgVector(
                    table_name=table_name,
                    db_url=db_url,
                ),
                reader=PDFReader(chunk=True, chunk_size=chunk_size),
            )
            knowledge_base.load(recreate=recreate)

        # Initialize agent
        logger.info(
            f"Initializing agent: {agent_name} (ID: {agent_id}, Type: {agent_type})"
        )

        # Initialize agent with LLM configuration
        agent = Agent(
            name=agent_name,
            knowledge=knowledge_base,
            search_knowledge=True if knowledge_base else False,
            model="gpt-4o",
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

    try:
        if agent is None:
            raise HTTPException(status_code=503, detail="Agent not initialized")

        # Get response from the agent - handle response as plain string
        response_text = agent.print_response(message.content)
        if response_text is None:
            raise HTTPException(status_code=500, detail="No response from agent")

        logger.info(f"Agent response: {response_text}")
        return Response(content=str(response_text))
    except Exception as e:
        logger.error(f"Error getting response from agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Initialize the agent
    initialize_agent()

    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8080))

    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=port)
