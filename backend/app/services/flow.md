# Services Flow Documentation

## Overview

The services directory contains the business logic layer of the Warder application. These service classes encapsulate complex operations, database interactions, and external integrations, providing a clean separation of concerns from the API routes.

## Key Services

### 1. Agent Service (`agent_service.py`)

**Purpose**: Manages the lifecycle and operations of AI agents in the system.

**Key Functions**:
- `create_agent`: Creates a new agent in the database
- `get_agent`: Retrieves an agent by ID
- `update_agent`: Updates an agent's properties
- `delete_agent`: Removes an agent from the system
- `list_agents`: Lists agents with optional filtering
- `start_agent`: Starts an agent's container
- `stop_agent`: Stops an agent's container
- `restart_agent`: Restarts an agent's container
- `_initialize_rag_agent`: Sets up a RAG (Retrieval-Augmented Generation) agent
- `add_document_to_agent`: Associates a document with an agent
- `remove_document_from_agent`: Removes a document association
- `get_agent_instance`: Retrieves a cached agent instance
- `get_agent_response`: Gets a response from an agent for a query

**Integration Points**:
- Uses ContainerService for container operations
- Interacts with Agent and Document models
- Called by agent_router endpoints
- Stores agent instances in memory for efficient access

**Flow Example (Creating and Starting an Agent)**:
1. `create_agent` is called with agent details
2. A new Agent record is created in the database
3. If auto_start is true, `start_agent` is called
4. `start_agent` calls ContainerService.create_container
5. Container environment variables are configured
6. Knowledge base path is set up and mounted
7. The container is started and its status is updated in the database

### 2. Container Service (`container_service.py`)

**Purpose**: Manages Docker/Podman containers for agent deployment.

**Key Functions**:
- `create_container`: Creates a new container for an agent
- `start_container`: Starts an existing container
- `stop_container`: Stops a running container
- `remove_container`: Removes a container
- `get_container_status`: Checks the status of a container
- `get_available_port`: Finds an available port for a new container
- `wait_for_container_health`: Waits until a container is healthy

**Integration Points**:
- Used by AgentService for agent container lifecycle
- Executes shell commands for container operations
- Manages container networking and port allocation

**Flow Example (Creating a Container)**:
1. `create_container` is called with agent details
2. An available port is found using `get_available_port`
3. Environment variables are prepared for the container
4. The container is created with appropriate volume mounts
5. The container is started and its health is checked
6. Container details are returned for updating the agent record

### 3. Document Service (`document_service.py`)

**Purpose**: Manages document operations including storage and retrieval.

**Key Functions**:
- `create_document`: Uploads and creates a new document
- `get_document`: Retrieves a document by ID
- `update_document`: Updates document properties
- `delete_document`: Removes a document
- `list_documents`: Lists documents with optional filtering
- `process_document`: Processes a document for use in knowledge bases

**Integration Points**:
- Called by document_router endpoints
- Interacts with Document model
- Manages file storage for documents

**Flow Example (Uploading a Document)**:
1. `create_document` is called with document details and file
2. The file is saved to the appropriate storage location
3. A new Document record is created in the database
4. If processing is requested, `process_document` is called
5. The document is processed for use in knowledge bases
6. The document details are returned

### 4. Auth Service (`auth_service.py`)

**Purpose**: Handles authentication and authorization operations.

**Key Functions**:
- `authenticate_user`: Verifies user credentials
- `create_access_token`: Creates a JWT token for authentication
- `verify_token`: Validates a JWT token
- `get_password_hash`: Hashes a password for secure storage
- `verify_password`: Verifies a password against its hash
- `get_current_user`: Gets the current authenticated user

**Integration Points**:
- Used by auth_router for login and token operations
- Integrated with auth_middleware for request authentication
- Works with the User model for user verification

**Flow Example (User Login)**:
1. `authenticate_user` is called with username and password
2. The user is retrieved from the database
3. The password is verified using `verify_password`
4. If authentication succeeds, `create_access_token` is called
5. A JWT token is generated with user claims
6. The token is returned for client authentication

### 5. User Service (`user_service.py`)

**Purpose**: Manages user account operations.

**Key Functions**:
- `create_user`: Creates a new user account
- `get_user`: Retrieves a user by ID
- `update_user`: Updates user properties
- `delete_user`: Removes a user account
- `list_users`: Lists users with optional filtering
- `change_password`: Updates a user's password

**Integration Points**:
- Called by user_router endpoints
- Uses auth_service for password hashing
- Interacts with User model

**Flow Example (User Registration)**:
1. `create_user` is called with user details
2. The password is hashed using auth_service.get_password_hash
3. A new User record is created in the database
4. The user details (excluding password) are returned

## Service Interaction Patterns

### 1. Layered Architecture

The services implement a layered architecture pattern:
- **API Layer** (routers): Handles HTTP requests and responses
- **Service Layer** (services): Implements business logic
- **Data Layer** (models): Manages data persistence

This separation ensures:
- Business logic is isolated from API concerns
- Database operations are encapsulated
- Code is more maintainable and testable

### 2. Dependency Injection

Services are typically instantiated and injected where needed:
- FastAPI dependencies provide services to route handlers
- Services can depend on other services
- This facilitates testing and loose coupling

Example:
```python
def get_agent_service():
    return AgentService()

@router.post("/agents")
async def create_agent(
    agent_data: AgentCreate,
    agent_service: AgentService = Depends(get_agent_service),
    current_user: User = Depends(get_current_user)
):
    return await agent_service.create_agent(agent_data, current_user)
```

### 3. Asynchronous Operations

Services use async/await for non-blocking operations:
- Database queries are asynchronous
- External API calls are asynchronous when possible
- This improves application scalability and responsiveness

Example:
```python
async def get_agent(self, agent_id: UUID, user_id: UUID) -> Agent:
    agent = await self.db.get(Agent, agent_id)
    if not agent or agent.user_id != user_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
```

## Error Handling

Services implement consistent error handling:
1. Domain-specific errors are raised as HTTPExceptions
2. Database errors are caught and transformed into appropriate HTTPExceptions
3. External service errors are handled and logged
4. Detailed error information is logged for debugging

Example:
```python
try:
    # Operation that might fail
    result = await some_operation()
    return result
except SomeSpecificError as e:
    logger.error(f"Specific error occurred: {str(e)}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

## Caching Strategy

Some services implement caching for performance:
- AgentService caches agent instances in memory
- This reduces initialization overhead for frequent agent interactions
- Cache invalidation occurs when agents are modified or restarted

Example:
```python
# Class-level cache for agent instances
_agent_instances = {}

async def get_agent_instance(self, agent_id: UUID) -> Any:
    """Get an agent instance from the cache or initialize it."""
    if agent_id in self._agent_instances:
        return self._agent_instances[agent_id]
    
    # Initialize and cache the agent
    agent = await self._initialize_agent(agent_id)
    self._agent_instances[agent_id] = agent
    return agent
```

## Transaction Management

Services manage database transactions to ensure data consistency:
- Operations that modify multiple records use transactions
- If any part of a transaction fails, all changes are rolled back
- This prevents partial updates and data inconsistencies

Example:
```python
async def complex_operation(self, data):
    async with self.db.begin() as transaction:
        try:
            # Multiple database operations
            result1 = await self.db.execute(...)
            result2 = await self.db.execute(...)
            
            # If all operations succeed, the transaction is committed
            return combined_result
        except Exception as e:
            # If any operation fails, the transaction is rolled back
            await transaction.rollback()
            raise
```
