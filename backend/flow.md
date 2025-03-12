# Warder Backend Flow Documentation

## Overview

This document provides a comprehensive overview of the Warder backend architecture, explaining how all components interact to form a complete system. It serves as a reference for developers working with this codebase and as a guide for troubleshooting issues.

## System Architecture

Warder follows a layered architecture pattern with clear separation of concerns:

1. **API Layer** (Routers)
   - Handles HTTP requests and responses
   - Defines API endpoints and their parameters
   - Manages request validation and response formatting

2. **Service Layer** (Services)
   - Implements business logic
   - Orchestrates operations across multiple components
   - Manages transactions and error handling

3. **Data Layer** (Models)
   - Defines the database schema
   - Handles data persistence
   - Manages relationships between entities

4. **Agent Layer** (Agent Container)
   - Runs in isolated containers
   - Processes natural language queries
   - Interacts with knowledge bases and LLMs

## Request Flow

### 1. Authentication Flow

```
Client → FastAPI → Auth Middleware → Auth Router → Auth Service → Database
   ↑                                                    ↓
   └────────────────────────────────────────────────────
                        JWT Token
```

1. Client sends credentials to `/api/auth/token`
2. Auth router validates the request format
3. Auth service authenticates the user against the database
4. If successful, a JWT token is generated and returned
5. Client includes this token in subsequent requests
6. Auth middleware validates the token on protected endpoints

### 2. Agent Creation Flow

```
Client → FastAPI → Agent Router → Agent Service → Database
                        ↓
                Container Service
                        ↓
                 Docker/Podman
                        ↓
                Agent Container
```

1. Client sends agent creation request to `/api/agents`
2. Agent router validates the request format
3. Agent service creates an agent record in the database
4. If auto_start is true, the container service is called
5. Container service creates and starts a container
6. Agent container initializes with the provided configuration
7. Container status is updated in the database

### 3. Document Upload Flow

```
Client → FastAPI → Document Router → Document Service → File System
                           ↓                 ↓
                        Database         Processing
```

1. Client uploads a document to `/api/documents`
2. Document router validates the request format
3. Document service saves the file to the file system
4. Document record is created in the database
5. If processing is requested, the document is processed for use in knowledge bases

### 4. Agent Query Flow

```
Client → FastAPI → Agent Router → Agent Service → Agent Container → LLM
                                        ↓                ↓
                                    Database      Knowledge Base
```

1. Client sends a query to `/api/agents/{agent_id}/query`
2. Agent router validates the request format
3. Agent service retrieves the agent from the database
4. Agent service forwards the query to the agent container
5. Agent container processes the query using its knowledge base and LLM
6. Response is returned through the same path in reverse

## Component Interactions

### 1. FastAPI and Middleware

FastAPI serves as the web framework, handling HTTP requests and responses. Middleware components process requests in a specific order:

1. CORS Middleware: Handles Cross-Origin Resource Sharing
2. Logging Middleware: Logs request and response details
3. Error Handling Middleware: Catches and processes exceptions
4. Authentication Middleware: Verifies user authentication (when required)

### 2. Routers and Services

Routers define API endpoints and delegate business logic to services:

1. Agent Router → Agent Service
2. Document Router → Document Service
3. Auth Router → Auth Service
4. User Router → User Service

Services implement business logic and interact with the database and external systems.

### 3. Services and Models

Services use SQLAlchemy models to interact with the database:

1. Agent Service → Agent Model
2. Document Service → Document Model
3. Auth Service → User Model
4. User Service → User Model

Models define the database schema and relationships between entities.

### 4. Agent Service and Container Service

The Agent Service uses the Container Service to manage agent containers:

1. Agent Service calls Container Service to create, start, stop, and remove containers
2. Container Service executes Docker/Podman commands
3. Container Service manages container networking and port allocation
4. Agent Service updates the agent record with container status

### 5. Agent Container and LLM

The Agent Container interacts with the LLM provider:

1. Agent Container receives queries through its API
2. Agent Container retrieves relevant knowledge from its knowledge base
3. Agent Container forwards the query and context to the LLM
4. LLM generates a response
5. Agent Container returns the response through its API

## Data Flow

### 1. Database Flow

```
Application → SQLAlchemy → AsyncPG → PostgreSQL
```

1. Application code calls SQLAlchemy ORM functions
2. SQLAlchemy generates SQL queries
3. AsyncPG executes the queries asynchronously
4. PostgreSQL processes the queries and returns results

### 2. File Storage Flow

```
Client → FastAPI → Document Service → File System
```

1. Client uploads files through the API
2. FastAPI processes the multipart form data
3. Document Service saves the files to the appropriate location
4. File paths are stored in the database

### 3. Container Management Flow

```
Agent Service → Container Service → Docker/Podman API → Container Runtime
```

1. Agent Service requests container operations
2. Container Service executes Docker/Podman commands
3. Docker/Podman API creates, starts, stops, or removes containers
4. Container Runtime manages the actual containers

## Key Processes

### 1. Application Startup

1. FastAPI application is created
2. Middleware components are added
3. Routers are registered
4. Database connection is initialized
5. Database tables are created if needed
6. Application starts listening for requests

### 2. Agent Initialization

1. Agent record is created in the database
2. Container is created with appropriate configuration
3. Knowledge base path is mounted to the container
4. Environment variables are set for configuration
5. Container is started
6. Agent initializes its knowledge base
7. Agent connects to the LLM provider
8. Agent starts listening for requests

### 3. Knowledge Base Processing

1. Document is uploaded and stored
2. Document is associated with an agent
3. When the agent container starts, it loads the document
4. Document is processed into chunks
5. Chunks are embedded and stored in the vector database
6. When a query is received, relevant chunks are retrieved
7. Retrieved chunks are used as context for the LLM

## Error Handling and Recovery

### 1. API Error Handling

1. Validation errors are caught by FastAPI and returned as 422 responses
2. HTTPExceptions are caught and returned with their status code and detail
3. Unexpected errors are caught by the error middleware and returned as 500 responses
4. All errors are logged for debugging

### 2. Database Error Handling

1. Connection errors trigger application startup failure
2. Transaction errors cause rollback and are propagated to the API layer
3. Constraint violations are caught and returned as appropriate HTTP errors

### 3. Container Error Handling

1. Container creation failures are logged and returned as errors
2. Container health check failures trigger restart attempts
3. Persistent container issues are reported to the user

## Testing

### 1. Unit Testing

Unit tests focus on individual components:
- Service functions
- Utility functions
- Model validations

### 2. Integration Testing

Integration tests verify component interactions:
- API endpoints
- Database operations
- Service coordination

### 3. Container Testing

Container tests validate agent functionality:
1. Container is created and started
2. Health endpoint is checked
3. Chat endpoint is tested with simple queries
4. Knowledge-based queries are tested
5. Container is cleaned up after testing

## Deployment

### 1. Development Environment

1. PostgreSQL database
2. Docker/Podman for container management
3. Local file storage

### 2. Production Environment

1. Managed PostgreSQL database
2. Container orchestration (Kubernetes, Docker Swarm)
3. Persistent storage for files
4. Load balancing and scaling

## Troubleshooting Guide

### 1. API Issues

- Check the logs for error messages
- Verify the request format against the API schema
- Ensure authentication tokens are valid
- Check for rate limiting or permission issues

### 2. Database Issues

- Verify database connection settings
- Check for schema migration issues
- Look for constraint violations
- Ensure the database server is running

### 3. Container Issues

- Check container logs for errors
- Verify container network connectivity
- Ensure required environment variables are set
- Check for resource constraints (memory, CPU)

### 4. Agent Issues

- Verify LLM provider connectivity
- Check knowledge base accessibility
- Ensure vector database is properly configured
- Look for errors in agent initialization

## Directory Structure

```
backend/
├── app/
│   ├── agent/              # Agent container code
│   ├── middleware/         # FastAPI middleware components
│   ├── models/             # SQLAlchemy ORM models
│   ├── routers/            # FastAPI route definitions
│   ├── schemas/            # Pydantic validation schemas
│   ├── services/           # Business logic services
│   └── utils/              # Utility functions and helpers
├── data/                   # Data storage
│   ├── knowledge_base/     # Knowledge base files
│   └── uploads/            # Uploaded files
├── scripts/                # Utility scripts
│   └── container_test.py   # Agent container test script
├── tests/                  # Test suite
└── main.py                 # Application entry point
```

## Component-Specific Documentation

For detailed information about each component, refer to the flow.md files in their respective directories:

- [Agent Flow](./app/agent/flow.md)
- [Middleware Flow](./app/middleware/flow.md)
- [Models Flow](./app/models/flow.md)
- [Routers Flow](./app/routers/flow.md)
- [Schemas Flow](./app/schemas/flow.md)
- [Services Flow](./app/services/flow.md)
- [Utils Flow](./app/utils/flow.md)

## Agent Container Architecture

The agent container is a key component of the Warder system, providing isolated execution of agent code. Each agent runs in its own container with the following architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                      Agent Container                         │
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │             │    │              │    │               │  │
│  │  FastAPI    │◄───┤  Agent Core  │◄───┤  Knowledge    │  │
│  │  Endpoints  │    │              │    │  Base         │  │
│  │             │    │              │    │               │  │
│  └─────┬───────┘    └──────┬───────┘    └───────────────┘  │
│        │                   │                               │
│        │                   ▼                               │
│        │            ┌──────────────┐                       │
│        │            │              │                       │
│        └───────────►│  LLM Client  │                       │
│                     │              │                       │
│                     └──────┬───────┘                       │
│                            │                               │
└────────────────────────────┼───────────────────────────────┘
                             │
                             ▼
                     ┌───────────────┐
                     │               │
                     │  LLM Provider │
                     │  (OpenAI)     │
                     │               │
                     └───────────────┘
```

1. **FastAPI Endpoints**: Handle HTTP requests to the agent
2. **Agent Core**: Manages agent logic and state
3. **Knowledge Base**: Stores and retrieves relevant knowledge
4. **LLM Client**: Communicates with the LLM provider

## Container Service Implementation

The Container Service manages the lifecycle of agent containers:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│  Agent Service  │◄───┤ Container       │◄───┤  Docker/Podman  │
│                 │    │ Service         │    │  Commands       │
│                 │    │                 │    │                 │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│  Agent Model    │    │  Container      │    │  Container      │
│  (Database)     │    │  Configuration  │    │  Runtime        │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

1. **Agent Service**: Requests container operations
2. **Container Service**: Executes container commands
3. **Docker/Podman Commands**: Interact with the container runtime
4. **Agent Model**: Stores container status and configuration
5. **Container Configuration**: Defines container parameters
6. **Container Runtime**: Manages the actual containers

## Knowledge Base Integration

The knowledge base integration allows agents to access and use document knowledge:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│  Document       │◄───┤  Agent Service  │◄───┤  Agent          │
│  Service        │    │                 │    │  Container      │
│                 │    │                 │    │                 │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│  Document       │    │  Knowledge      │    │  Vector         │
│  Storage        │    │  Base Path      │    │  Database       │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

1. **Document Service**: Manages document storage and processing
2. **Agent Service**: Associates documents with agents
3. **Agent Container**: Loads and uses document knowledge
4. **Document Storage**: Stores the actual document files
5. **Knowledge Base Path**: Mounted to the agent container
6. **Vector Database**: Stores document embeddings for retrieval

## Conclusion

The Warder backend is a complex system with multiple interacting components. This documentation provides a comprehensive overview of how these components work together, serving as a reference for developers and a guide for troubleshooting.

When working with this codebase, remember these key points:

1. **Layered Architecture**: Understand which layer you're working with and its responsibilities
2. **Asynchronous Design**: Most operations are asynchronous for better scalability
3. **Container Isolation**: Agent code runs in isolated containers for security and resource management
4. **Error Handling**: Check the logs for detailed error information
5. **Testing**: Use the container_test.py script to validate agent functionality

By following these guidelines and referring to the component-specific documentation, you'll be able to effectively work with and troubleshoot the Warder backend.
