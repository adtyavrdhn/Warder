# Agentic System Infrastructure Backend

This directory contains the backend services for the Agentic System Infrastructure that enables users to deploy and interact with AI agents without writing code.

## Architecture

The system follows a microservices architecture with the following core components:

- **API Gateway Service**: Handles external requests, authentication, and request routing
- **Agent Manager Service**: Orchestrates the agent lifecycle using the Agno framework
- **Document Processor Service**: Ingests, analyzes, and processes documents
- **Database Service**: Utilizes PostgreSQL with PgVector for metadata and embeddings
- **Agent Containers**: Each agent is deployed within its own Docker container managed by Kubernetes

## Directory Structure

```
backend/
├── api_gateway/        # API Gateway service
├── agent_manager/      # Agent Manager service
├── document_processor/ # Document Processor service
├── database/           # Database migrations and scripts
├── kubernetes/         # Kubernetes configuration files
├── docker/             # Docker configuration files
├── common/             # Shared code and utilities
├── config/             # Configuration files
├── scripts/            # Utility scripts
└── tests/              # Integration tests
```

## Getting Started

1. Install dependencies:
   ```
   make install
   ```

2. Set up the database:
   ```
   make setup-db
   ```

3. Start the services:
   ```
   make run
   ```

4. Run tests:
   ```
   make test
   ```

## Development

- Use `make dev` to start the services in development mode
- Use `make lint` to run linters
- Use `make format` to format code

## Deployment

- Use `make build` to build Docker images
- Use `make deploy` to deploy to Kubernetes

## Documentation

API documentation is available at `/docs` when the API Gateway is running.
