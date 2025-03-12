# Schemas Flow Documentation

## Overview

The schemas directory contains Pydantic models that define the structure of data for request validation, response serialization, and internal data transfer. These schemas ensure type safety and data validation throughout the application.

## Key Schema Categories

### 1. Agent Schemas (`agent.py`)

**Purpose**: Define the data structures for agent-related operations.

**Key Schemas**:
- `AgentBase`: Base schema with common agent fields
- `AgentCreate`: Schema for creating a new agent
- `AgentUpdate`: Schema for updating an existing agent
- `AgentResponse`: Schema for agent responses in API endpoints
- `AgentQuery`: Schema for agent query requests
- `AgentChat`: Schema for agent chat requests
- `AgentContainerConfig`: Schema for agent container configuration

**Usage Flow**:
1. `AgentCreate` validates incoming data when creating an agent
2. The validated data is passed to the agent_service
3. The agent_service creates an Agent model instance
4. The Agent model is converted to an `AgentResponse` for the API response

**Example**:
```python
class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: str

class AgentCreate(AgentBase):
    auto_start: bool = False
    container_config: Optional[AgentContainerConfig] = None

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None

class AgentResponse(AgentBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    container_id: Optional[str] = None
    container_status: Optional[str] = None
    container_port: Optional[int] = None
    knowledge_base_path: Optional[str] = None

    class Config:
        orm_mode = True
```

### 2. Document Schemas (`document.py`)

**Purpose**: Define the data structures for document-related operations.

**Key Schemas**:
- `DocumentBase`: Base schema with common document fields
- `DocumentCreate`: Schema for creating a new document
- `DocumentUpdate`: Schema for updating an existing document
- `DocumentResponse`: Schema for document responses in API endpoints

**Usage Flow**:
1. `DocumentCreate` validates incoming data when uploading a document
2. The validated data is passed to the document_service
3. The document_service creates a Document model instance
4. The Document model is converted to a `DocumentResponse` for the API response

### 3. User Schemas (`user.py`)

**Purpose**: Define the data structures for user-related operations.

**Key Schemas**:
- `UserBase`: Base schema with common user fields
- `UserCreate`: Schema for creating a new user
- `UserUpdate`: Schema for updating an existing user
- `UserResponse`: Schema for user responses in API endpoints
- `PasswordChange`: Schema for password change requests

**Usage Flow**:
1. `UserCreate` validates incoming data when registering a user
2. The validated data is passed to the user_service
3. The user_service creates a User model instance
4. The User model is converted to a `UserResponse` for the API response

### 4. Auth Schemas (`auth.py`)

**Purpose**: Define the data structures for authentication operations.

**Key Schemas**:
- `Token`: Schema for authentication token responses
- `TokenData`: Schema for token payload data
- `Login`: Schema for login requests

**Usage Flow**:
1. `Login` validates incoming credentials
2. The auth_service authenticates the user
3. A JWT token is generated
4. The token is returned in a `Token` response

## Schema Inheritance and Composition

Schemas use inheritance and composition to maintain DRY (Don't Repeat Yourself) principles:

1. **Inheritance**:
   - Base schemas define common fields
   - Create, update, and response schemas inherit from base schemas
   - This ensures consistency across related schemas

2. **Composition**:
   - Complex schemas include nested schemas
   - This allows for structured validation of complex data

Example:
```python
class AgentContainerConfig(BaseModel):
    memory_limit: Optional[str] = "512m"
    cpu_limit: Optional[float] = 0.5
    environment_variables: Optional[Dict[str, str]] = {}

class AgentCreate(AgentBase):
    auto_start: bool = False
    container_config: Optional[AgentContainerConfig] = None
```

## Validation Rules

Schemas define validation rules to ensure data integrity:

1. **Field Constraints**:
   - Type validation (str, int, UUID, etc.)
   - Length constraints (min_length, max_length)
   - Range constraints (ge, le, gt, lt)
   - Regex patterns

2. **Custom Validators**:
   - Functions decorated with `@validator` or `@root_validator`
   - Perform complex validation logic
   - Can transform data during validation

Example:
```python
class UserCreate(UserBase):
    password: str
    confirm_password: str

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        # More password strength checks
        return v
```

## ORM Integration

Response schemas are configured to work with SQLAlchemy ORM models:

1. **ORM Mode**:
   - `orm_mode = True` in Config class
   - Allows direct conversion from ORM models to Pydantic models
   - Handles relationships and lazy-loaded attributes

2. **Field Aliases**:
   - Maps between ORM attribute names and API field names
   - Allows for different naming conventions in the database and API

Example:
```python
class AgentResponse(AgentBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True
        alias_generator = to_camel
        allow_population_by_field_name = True
```

## Optional vs. Required Fields

Schemas distinguish between required and optional fields:

1. **Create Schemas**:
   - Required fields for entity creation
   - Optional fields with defaults where appropriate

2. **Update Schemas**:
   - All fields are optional
   - Only provided fields are updated

Example:
```python
class AgentCreate(AgentBase):
    name: str  # Required
    description: Optional[str] = None  # Optional with default
    
class AgentUpdate(BaseModel):
    name: Optional[str] = None  # Optional for updates
    description: Optional[str] = None  # Optional for updates
```

## Response Filtering

Response schemas control what data is exposed in API responses:

1. **Field Inclusion/Exclusion**:
   - Only fields defined in the response schema are included
   - Sensitive fields (like passwords) are excluded

2. **Computed Fields**:
   - Additional fields can be computed during serialization
   - Useful for derived properties not stored in the database

Example:
```python
class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    is_active: bool
    
    # Password is deliberately excluded
    
    @property
    def is_new_user(self) -> bool:
        """Computed property to check if user is new (less than 7 days old)."""
        return (datetime.now() - self.created_at).days < 7
```

## Schema Usage in API Endpoints

Schemas are used in FastAPI endpoints for request validation and response serialization:

1. **Request Validation**:
   - `request_model` parameter type annotations
   - FastAPI automatically validates incoming data

2. **Response Serialization**:
   - `response_model` parameter in endpoint decorators
   - FastAPI automatically serializes responses

Example:
```python
@router.post("/", response_model=AgentResponse)
async def create_agent(
    agent_data: AgentCreate,  # Request validation
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_db)
):
    # The response is automatically serialized to AgentResponse
    return await agent_service.create_agent(agent_data, current_user)
```
