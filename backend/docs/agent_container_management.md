# Agent Container Management

This document provides information about the agent container management functionality in the Warder system, including setup, testing, and usage instructions.

## Overview

The agent container management feature allows the Warder system to create, start, stop, and manage Docker containers for AI agents. Each agent can be deployed in its own container, providing isolation and resource control.

## Prerequisites

- Docker installed and running
- PostgreSQL database for the Warder backend
- Python 3.10 or higher

## Environment Variables

The agent container management functionality uses the following environment variables:

- `AGENT_PORT_RANGE_START`: Default starting port for agent containers (default: 9000)
- `AGENT_PORT_RANGE_END`: Default ending port for agent containers (default: 9500)
- `AGENT_NETWORK`: Docker network name for agent containers (default: `warder_network`)
- `AGENT_IMAGE`: Default Docker image for agents (default: `warder/agent:latest`)

## Setup

### 1. Set up the Docker Environment

Run the setup script to create the Docker network and build the agent image:

```bash
./backend/scripts/setup_docker_env.sh
```

This script will:
- Create the `warder_network` Docker network if it doesn't exist
- Build the agent Docker image (`warder/agent:latest`)

### 2. Run the Warder Backend

Start the Warder backend server:

```bash
cd backend
uvicorn app.main:app --reload
```

## API Endpoints

The following API endpoints are available for agent container management:

### Start Agent Container

```
POST /api/agents/{agent_id}/start
```

Starts the container for the specified agent. If the container doesn't exist, it will be created first.

**Response:**
```json
{
  "message": "Agent container started successfully"
}
```

### Stop Agent Container

```
POST /api/agents/{agent_id}/stop
```

Stops the container for the specified agent.

**Response:**
```json
{
  "message": "Agent container stopped successfully"
}
```

### Get Agent Container Logs

```
GET /api/agents/{agent_id}/logs
```

Retrieves logs from the agent's container.

**Query Parameters:**
- `lines` (optional): Number of log lines to retrieve (default: 100)

**Response:**
```json
{
  "logs": "Container log content..."
}
```

### Get Agent Container Stats

```
GET /api/agents/{agent_id}/stats
```

Retrieves stats from the agent's container, including CPU and memory usage.

**Response:**
```json
{
  "stats": {
    "cpu_usage": "10%",
    "memory_usage": "100MB",
    ...
  }
}
```

## Testing

### Unit Tests

Run the unit tests for the container service and agent service:

```bash
cd backend
pytest tests/test_container_service.py tests/test_agent_service_container.py -v
```

### Integration Tests

Run the integration tests for the agent container management endpoints:

```bash
cd backend
pytest tests/test_agent_container_endpoints.py -v
```

### Manual Testing

1. Create an agent with container configuration:

```bash
curl -X POST "http://localhost:8000/api/agents/" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer YOUR_TOKEN" \
-d '{
  "name": "Test Container Agent",
  "description": "Agent for testing container management",
  "type": "chat",
  "user_id": "YOUR_USER_ID",
  "config": {
    "model": "gpt-3.5-turbo"
  },
  "container_config": {
    "image": "warder/agent:latest",
    "memory_limit": "512m",
    "cpu_limit": 0.5,
    "env_vars": {
      "TEST_VAR": "test_value"
    }
  }
}'
```

2. Start the agent container:

```bash
curl -X POST "http://localhost:8000/api/agents/AGENT_ID/start" \
-H "Authorization: Bearer YOUR_TOKEN"
```

3. Get the agent container logs:

```bash
curl -X GET "http://localhost:8000/api/agents/AGENT_ID/logs" \
-H "Authorization: Bearer YOUR_TOKEN"
```

4. Get the agent container stats:

```bash
curl -X GET "http://localhost:8000/api/agents/AGENT_ID/stats" \
-H "Authorization: Bearer YOUR_TOKEN"
```

5. Stop the agent container:

```bash
curl -X POST "http://localhost:8000/api/agents/AGENT_ID/stop" \
-H "Authorization: Bearer YOUR_TOKEN"
```

## Troubleshooting

### Common Issues

1. **Docker Network Issues**
   - Ensure the Docker network exists: `docker network ls`
   - Recreate the network if needed: `docker network create warder_network`

2. **Container Image Issues**
   - Rebuild the agent image: `docker build -t warder/agent:latest -f backend/Dockerfile.agent backend/`
   - Check if the image exists: `docker images | grep warder/agent`

3. **Port Conflicts**
   - If you encounter port conflicts, adjust the `AGENT_PORT_RANGE_START` and `AGENT_PORT_RANGE_END` environment variables

4. **Container Management Errors**
   - Check the Docker logs: `docker logs CONTAINER_ID`
   - Verify Docker permissions: Ensure the user running the Warder backend has permissions to manage Docker containers
