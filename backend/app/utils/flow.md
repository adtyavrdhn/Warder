# Utils Flow Documentation

## Overview

The utils directory contains utility functions and classes that provide common functionality used throughout the Warder application. These utilities handle cross-cutting concerns such as database connections, logging configuration, and helper functions.

## Key Utility Modules

### 1. Database Utilities (`database.py`)

**Purpose**: Manages database connections and operations.

**Key Functions**:
- `init_db()`: Initializes the database connection
- `get_db()`: Provides a database session for dependency injection
- `create_tables()`: Creates database tables based on SQLAlchemy models
- `get_engine()`: Gets the SQLAlchemy engine instance

**Usage Flow**:
1. `init_db()` is called during application startup
2. Database connection pool is established
3. `get_db()` is used as a FastAPI dependency in route handlers
4. Route handlers receive a database session for operations
5. When the request is complete, the session is closed automatically

**Example**:
```python
# In main.py
@app.on_event("startup")
async def startup_event():
    await init_db()
    await create_tables()

# In a router
@router.get("/items")
async def get_items(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item))
    items = result.scalars().all()
    return items
```

### 2. Logging Configuration (`logging_config.py`)

**Purpose**: Configures logging for the application.

**Key Functions**:
- `configure_logging()`: Sets up logging with appropriate handlers and formatters
- `get_logger()`: Gets a logger instance for a specific module

**Usage Flow**:
1. `configure_logging()` is called during application startup
2. Logging is configured with console and file handlers
3. `get_logger()` is used in modules to get a logger instance
4. Log messages are formatted and directed to appropriate outputs

**Example**:
```python
# In main.py
logger = configure_logging("warder_app")

# In a service module
logger = get_logger("agent_service")
logger.info("Initializing agent service")
```

### 3. File Utilities (`file_utils.py`)

**Purpose**: Handles file operations for documents and knowledge bases.

**Key Functions**:
- `save_uploaded_file()`: Saves an uploaded file to the appropriate location
- `ensure_directory_exists()`: Creates directories if they don't exist
- `get_file_extension()`: Extracts the extension from a filename
- `generate_unique_filename()`: Generates a unique filename to prevent collisions

**Usage Flow**:
1. When a file is uploaded, `save_uploaded_file()` is called
2. The function ensures the target directory exists
3. A unique filename is generated if needed
4. The file is saved to the appropriate location
5. The file path is returned for storage in the database

**Example**:
```python
async def create_document(self, document_data, file, user_id):
    # Generate a unique filename
    filename = generate_unique_filename(file.filename)
    
    # Save the file
    file_path = await save_uploaded_file(
        file, 
        os.path.join(DOCUMENT_STORAGE_PATH, str(user_id))
    )
    
    # Create the document record
    document = Document(
        name=document_data.name,
        description=document_data.description,
        file_path=file_path,
        file_type=get_file_extension(file.filename),
        user_id=user_id
    )
    
    self.db.add(document)
    await self.db.commit()
    await self.db.refresh(document)
    return document
```

### 4. Security Utilities (`security.py`)

**Purpose**: Provides security-related functions.

**Key Functions**:
- `generate_password_hash()`: Hashes passwords for secure storage
- `verify_password()`: Verifies a password against its hash
- `create_jwt_token()`: Creates a JWT token for authentication
- `decode_jwt_token()`: Decodes and validates a JWT token

**Usage Flow**:
1. When a user registers, `generate_password_hash()` is used to hash their password
2. When a user logs in, `verify_password()` is used to verify their credentials
3. After successful authentication, `create_jwt_token()` generates a token
4. When a protected endpoint is accessed, `decode_jwt_token()` validates the token

**Example**:
```python
async def authenticate_user(self, username: str, password: str) -> Optional[User]:
    user = await self.get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

async def login(self, username: str, password: str) -> Dict[str, str]:
    user = await self.authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_jwt_token(
        data={"sub": str(user.id), "username": user.username}
    )
    return {"access_token": access_token, "token_type": "bearer"}
```

### 5. Validation Utilities (`validation.py`)

**Purpose**: Provides custom validation functions for data validation.

**Key Functions**:
- `validate_email()`: Validates email addresses
- `validate_password_strength()`: Checks password strength
- `sanitize_input()`: Sanitizes user input to prevent injection attacks

**Usage Flow**:
1. These functions are used in Pydantic model validators
2. They provide more complex validation than built-in Pydantic validators
3. They help ensure data integrity and security

**Example**:
```python
class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        result = validate_password_strength(v)
        if not result['valid']:
            raise ValueError(result['message'])
        return v
    
    @validator('email')
    def validate_email_format(cls, v):
        if not validate_email(v):
            raise ValueError("Invalid email format")
        return v
```

## Utility Design Patterns

### 1. Dependency Injection

Utilities are designed to be used with FastAPI's dependency injection system:
- Functions like `get_db()` are used as dependencies
- This allows for easy testing and loose coupling
- Dependencies can be overridden in tests

Example:
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/items")
async def get_items(db: AsyncSession = Depends(get_db)):
    # Use the injected db session
    pass
```

### 2. Singleton Pattern

Some utilities implement the singleton pattern to ensure only one instance exists:
- Database connection pool
- Logging configuration
- This prevents resource duplication and ensures consistent behavior

Example:
```python
# Singleton database engine
_engine = None

async def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            DATABASE_URL,
            echo=DEBUG_MODE,
            future=True
        )
    return _engine
```

### 3. Factory Pattern

Factory functions create and configure objects:
- `configure_logging()` creates and configures loggers
- `create_async_engine()` creates the database engine
- This centralizes configuration and simplifies usage

Example:
```python
def configure_logging(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Configure handlers and formatters
    
    return logger
```

## Error Handling

Utilities implement consistent error handling:
1. Expected errors are raised with descriptive messages
2. Unexpected errors are caught, logged, and re-raised if appropriate
3. Resource cleanup is ensured with try-finally blocks

Example:
```python
async def save_uploaded_file(file, directory):
    try:
        ensure_directory_exists(directory)
        file_path = os.path.join(directory, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return file_path
    except OSError as e:
        logger.error(f"File save error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save file")
    finally:
        file.file.close()
```

## Asynchronous Design

Many utilities are designed for asynchronous operation:
- Database functions use SQLAlchemy's async API
- File operations are wrapped in async functions
- This improves application scalability and responsiveness

Example:
```python
async def init_db():
    global _engine
    try:
        _engine = create_async_engine(
            DATABASE_URL,
            echo=DEBUG_MODE,
            future=True
        )
        
        # Test the connection
        async with _engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise
```

## Configuration Management

Utilities handle application configuration:
- Environment variables are loaded and validated
- Default values are provided where appropriate
- Configuration is centralized for consistency

Example:
```python
# Load configuration from environment variables
DEBUG_MODE = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/warder")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Validate required configuration
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set")
```
