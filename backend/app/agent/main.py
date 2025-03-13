"""
Main module for the Warder agent.
"""

import os
import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from agno.agent import Agent
from pydantic import BaseModel
from agno.agent import Agent
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
        # Get agent configuration from environment variables
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
            chunk_overlap = int(os.environ.get("KB_CHUNK_OVERLAP", "200"))

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
                reader=PDFReader(
                    chunk=True, chunk_size=chunk_size, chunk_overlap=chunk_overlap
                ),
            )
            knowledge_base.load(recreate=recreate)

        # Get LLM configuration from environment variables
        llm_provider = os.environ.get("LLM_PROVIDER", "")
        llm_model = os.environ.get("LLM_MODEL", "")
        llm_api_key = os.environ.get("LLM_API_KEY", "")

        # Initialize agent
        logger.info(
            f"Initializing agent: {agent_name} (ID: {agent_id}, Type: {agent_type})"
        )

        # Check if we have LLM configuration
        if llm_provider and llm_model and llm_api_key:
            logger.info(f"Using LLM provider: {llm_provider}, model: {llm_model}")

            # Initialize agent with LLM configuration
            agent = Agent(
                knowledge=knowledge_base,
                search_knowledge=True if knowledge_base else False,
                llm_provider=llm_provider,
                llm_model=llm_model,
                llm_api_key=llm_api_key,
            )
        else:
            logger.warning("No LLM configuration found, agent will use echo responses")
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
            agent_response = agent.print_response(message.content)
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


@app.post("/query")
async def query(query_data: Query):
    """Direct query endpoint for the agent."""
    logger.info(f"Received query: {query_data.query}")

    # Use the agent to generate a response if available
    if agent and AGNO_AVAILABLE:
        try:
            # Get response from the agent
            agent_response = agent.print_response(query_data.query)
            logger.info(f"Agent response to query: {agent_response}")
            return {"response": agent_response}
        except Exception as e:
            logger.error(f"Error getting response from agent for query: {str(e)}")
            # Return error message
            return {"error": str(e)}
    else:
        # Simple echo response for testing when agent is not available
        logger.warning("Agent not available for query. Using echo response.")
        return {"response": f"Echo: {query_data.query}"}


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
