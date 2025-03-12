# Agent Flow Documentation

## Overview

The agent directory contains the implementation of the Warder agent system, which runs in a containerized environment. The agent is responsible for handling natural language queries, interacting with knowledge bases, and providing responses using LLM (Large Language Model) technology.

## Key Components

### 1. Main Agent Application (`main.py`)

**Purpose**: Serves as the entry point for the agent container, initializing the agent and exposing API endpoints.

**Flow**:
1. On startup, the agent is initialized with configuration from environment variables
2. FastAPI routes are defined for interacting with the agent
3. The agent listens for incoming requests and processes them

**Key Functions**:
- `initialize_agent()`: Sets up the agent with the appropriate configuration
- `chat(message)`: Endpoint for chat interactions with the agent
- `query(query_data)`: Endpoint for direct queries to the agent
- `health()`: Health check endpoint for container monitoring
- `info()`: Endpoint for retrieving agent information

**Integration Points**:
- Communicates with the main application through HTTP requests
- Managed by the ContainerService for lifecycle operations
- Configured through environment variables passed by the AgentService

### 2. Knowledge Base Integration

**Purpose**: Connects the agent to various knowledge sources for context-aware responses.

**Flow**:
1. On initialization, the agent loads knowledge from specified sources (e.g., PDF documents)
2. The knowledge is processed and stored in a vector database for efficient retrieval
3. When a query is received, relevant knowledge is retrieved and used to inform the agent's response

**Key Components**:
- `PDFKnowledgeBase`: Handles loading and processing PDF documents
- `PDFReader`: Extracts and chunks text from PDF files
- `PgVector`: Stores and retrieves vector embeddings in PostgreSQL

**Integration Points**:
- Uses the vector database configured through environment variables
- Accesses PDF documents mounted to the container
- Integrated with the LLM for knowledge-enhanced responses

### 3. LLM Integration

**Purpose**: Provides natural language understanding and generation capabilities.

**Flow**:
1. The agent forwards user queries to the LLM
2. Relevant knowledge is included in the context
3. The LLM generates a response based on the query and context
4. The response is returned to the user

**Key Components**:
- `Agent` class: Manages interaction with the LLM
- Environment variables for LLM configuration (provider, model, API keys)

**Integration Points**:
- Configured through environment variables
- Integrated with knowledge base for context-aware responses
- Accessed by the chat and query endpoints

## Container Lifecycle

1. **Creation**:
   - The ContainerService creates a container with the agent image
   - Environment variables are set for configuration
   - Knowledge directories are mounted to the container
   - Network and resource limits are configured

2. **Initialization**:
   - On startup, the agent initializes with the provided configuration
   - The knowledge base is loaded and indexed
   - The agent connects to the LLM provider

3. **Operation**:
   - The agent listens for incoming requests on the configured port
   - Requests are processed and responses are generated
   - Health checks ensure the agent is functioning properly

4. **Termination**:
   - When the container is stopped, resources are cleaned up
   - The agent process is terminated

## API Endpoints

1. **Health Check** (`GET /health`):
   - Returns the health status of the agent
   - Used by the container orchestration system for monitoring

2. **Chat** (`POST /chat`):
   - Accepts a message with content and role
   - Returns a response from the agent
   - Maintains conversation context

3. **Query** (`POST /query`):
   - Accepts a direct query string
   - Returns a response based on the query and available knowledge
   - Optimized for single-turn interactions

4. **Info** (`GET /info`):
   - Returns information about the agent configuration
   - Includes agent type, name, and capabilities

## Environment Variables

The agent container is configured through the following environment variables:

- `AGENT_ID`: Unique identifier for the agent
- `AGENT_NAME`: Display name for the agent
- `AGENT_TYPE`: Type of agent (e.g., "rag" for Retrieval-Augmented Generation)
- `PORT`: Port for the agent to listen on
- `KNOWLEDGE_PATH`: Path to the knowledge directory in the container
- `VECTOR_DB_URL`: Connection string for the vector database
- `VECTOR_DB_TABLE`: Table name for storing vector embeddings
- `KB_RECREATE`: Whether to recreate the knowledge base on startup
- `KB_CHUNK_SIZE`: Size of text chunks for knowledge base processing
- `KB_CHUNK_OVERLAP`: Overlap between text chunks
- `OPENAI_API_KEY`: API key for OpenAI (if using OpenAI as the LLM provider)
- `AGNO_LLM_PROVIDER`: LLM provider to use (e.g., "openai")
- `AGNO_LLM_MODEL`: LLM model to use (e.g., "gpt-3.5-turbo")

## Testing

The agent container can be tested using the `container_test.py` script, which:

1. Creates and starts a container with the agent
2. Waits for the container to be ready
3. Tests communication with the agent through its API endpoints
4. Cleans up the container after testing

This provides a way to validate the agent's functionality in isolation before integrating it with the main application.
