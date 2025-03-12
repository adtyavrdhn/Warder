# Routers Flow Documentation

## Overview

The routers directory contains FastAPI router modules that define the API endpoints for the Warder application. Each router is responsible for a specific domain of functionality, encapsulating related endpoints and their dependencies.

## Key Routers

### 1. Agent Router (`agent_router.py`)

**Purpose**: Handles all API endpoints related to agent management and interaction.

**Key Endpoints**:
- `POST /agents`: Creates a new agent
- `GET /agents/{agent_id}`: Retrieves an agent by ID
- `PUT /agents/{agent_id}`: Updates an agent
- `DELETE /agents/{agent_id}`: Deletes an agent
- `GET /agents`: Lists agents with filtering options
- `POST /agents/{agent_id}/start`: Starts an agent's container
- `POST /agents/{agent_id}/stop`: Stops an agent's container
- `POST /agents/{agent_id}/restart`: Restarts an agent's container
- `POST /agents/{agent_id}/documents`: Associates a document with an agent
- `DELETE /agents/{agent_id}/documents/{document_id}`: Removes a document association
- `POST /agents/{agent_id}/chat`: Sends a chat message to an agent
- `POST /agents/{agent_id}/query`: Sends a direct query to an agent

**Dependencies**:
- `get_db`: Database session
- `get_current_user`: Authenticated user
- `get_agent_service`: Agent service instance
- `get_document_service`: Document service instance

**Flow Example (Creating an Agent)**:
1. Client sends a POST request to `/agents` with agent details
2. The `create_agent` endpoint handler is invoked
3. The current user is authenticated using the `get_current_user` dependency
4. The agent service is obtained using the `get_agent_service` dependency
5. The agent service's `create_agent` method is called with the agent details and user
6. The created agent is returned in the response

### 2. Document Router (`document_router.py`)

**Purpose**: Manages document-related API endpoints.

**Key Endpoints**:
- `POST /documents`: Uploads a new document
- `GET /documents/{document_id}`: Retrieves a document by ID
- `PUT /documents/{document_id}`: Updates a document
- `DELETE /documents/{document_id}`: Deletes a document
- `GET /documents`: Lists documents with filtering options
- `GET /documents/{document_id}/download`: Downloads a document file

**Dependencies**:
- `get_db`: Database session
- `get_current_user`: Authenticated user
- `get_document_service`: Document service instance

**Flow Example (Uploading a Document)**:
1. Client sends a POST request to `/documents` with document details and file
2. The `create_document` endpoint handler is invoked
3. The current user is authenticated using the `get_current_user` dependency
4. The document service is obtained using the `get_document_service` dependency
5. The document service's `create_document` method is called with the document details, file, and user
6. The created document is returned in the response

### 3. Auth Router (`auth_router.py`)

**Purpose**: Handles authentication-related API endpoints.

**Key Endpoints**:
- `POST /token`: Authenticates a user and issues a JWT token
- `POST /register`: Registers a new user
- `GET /me`: Retrieves the current authenticated user's details
- `POST /refresh`: Refreshes an existing JWT token

**Dependencies**:
- `get_db`: Database session
- `get_auth_service`: Auth service instance
- `get_user_service`: User service instance
- `get_current_user`: Authenticated user (for protected endpoints)

**Flow Example (User Login)**:
1. Client sends a POST request to `/token` with username and password
2. The `login_for_access_token` endpoint handler is invoked
3. The auth service is obtained using the `get_auth_service` dependency
4. The auth service's `authenticate_user` method is called with the credentials
5. If authentication succeeds, a JWT token is generated and returned
6. If authentication fails, a 401 Unauthorized response is returned

### 4. User Router (`user_router.py`)

**Purpose**: Manages user-related API endpoints.

**Key Endpoints**:
- `GET /users/{user_id}`: Retrieves a user by ID
- `PUT /users/{user_id}`: Updates a user
- `DELETE /users/{user_id}`: Deletes a user
- `GET /users`: Lists users with filtering options
- `POST /users/{user_id}/password`: Changes a user's password

**Dependencies**:
- `get_db`: Database session
- `get_current_user`: Authenticated user
- `get_user_service`: User service instance

**Flow Example (Updating a User)**:
1. Client sends a PUT request to `/users/{user_id}` with updated user details
2. The `update_user` endpoint handler is invoked
3. The current user is authenticated using the `get_current_user` dependency
4. Authorization is checked (user can only update their own profile unless they're a superuser)
5. The user service is obtained using the `get_user_service` dependency
6. The user service's `update_user` method is called with the user ID and updated details
7. The updated user is returned in the response

## Router Registration

All routers are registered in the main FastAPI application (`main.py`) with appropriate prefixes and tags:

```python
app.include_router(auth_router.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(user_router.router, prefix="/api/users", tags=["Users"])
app.include_router(agent_router.router, prefix="/api/agents", tags=["Agents"])
app.include_router(document_router.router, prefix="/api/documents", tags=["Documents"])
```

This creates a structured API with logical grouping of endpoints.

## Authentication and Authorization Flow

### 1. Authentication

Most endpoints require authentication, which follows this flow:
1. The client includes a JWT token in the Authorization header
2. The `get_current_user` dependency extracts and validates the token
3. If the token is valid, the user is retrieved and made available to the endpoint
4. If the token is invalid or missing, a 401 Unauthorized response is returned

```python
async def get_current_user(
    auth_service: AuthService = Depends(get_auth_service),
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    user = await auth_service.verify_token(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
```

### 2. Authorization

Authorization is handled at the endpoint level:
- Users can only access their own resources unless they're superusers
- Superusers can access all resources
- Some endpoints have specific authorization rules

Example:
```python
@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_db)
):
    # Authorization check
    if not current_user.is_superuser and agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this agent")
    
    return await agent_service.get_agent(agent_id, current_user.id)
```

## Request Validation

FastAPI automatically validates requests based on the Pydantic models defined in the schemas directory:
1. Request data is parsed and validated against the schema
2. If validation fails, a 422 Unprocessable Entity response is returned with details
3. If validation succeeds, the validated data is passed to the endpoint handler

Example:
```python
@router.post("/", response_model=AgentResponse)
async def create_agent(
    agent_data: AgentCreate,  # Validated against AgentCreate schema
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_db)
):
    return await agent_service.create_agent(agent_data, current_user)
```

## Response Formatting

Responses are formatted based on the response_model specified for each endpoint:
1. The endpoint handler returns a data structure (typically a model instance or dictionary)
2. FastAPI serializes the data according to the response_model
3. Fields not included in the response_model are excluded from the output
4. Additional validation ensures the response matches the expected schema

Example:
```python
@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_db)
):
    agent = await agent_service.get_agent(agent_id, current_user.id)
    # The response will only include fields defined in AgentResponse
    return agent
```

## Error Handling

Routers handle errors in a consistent way:
1. Expected errors are raised as HTTPExceptions with appropriate status codes
2. Unexpected errors are caught by the error middleware and converted to 500 Internal Server Error responses
3. Validation errors are automatically handled by FastAPI

Example:
```python
@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_db)
):
    try:
        await agent_service.delete_agent(agent_id, current_user.id)
        return {"message": "Agent deleted successfully"}
    except HTTPException:
        # Re-raise HTTP exceptions from the service
        raise
    except Exception as e:
        # Log unexpected errors and raise a generic HTTP exception
        logger.error(f"Error deleting agent: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete agent")
```

## Pagination and Filtering

List endpoints support pagination and filtering:
1. Query parameters define page size, page number, and filter criteria
2. The service layer applies these parameters to the database query
3. The response includes the results and pagination metadata

Example:
```python
@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_db)
):
    filters = {}
    if name:
        filters["name"] = name
    if type:
        filters["type"] = type
        
    agents = await agent_service.list_agents(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        filters=filters
    )
    return agents
```
