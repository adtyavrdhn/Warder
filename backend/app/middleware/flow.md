# Middleware Flow Documentation

## Overview

The middleware components in Warder handle cross-cutting concerns that apply to all requests, such as logging, error handling, and authentication. These middleware components are executed in the order they are added to the FastAPI application.

## Middleware Components

### 1. Logging Middleware (`logging_middleware.py`)

**Purpose**: Logs incoming requests and outgoing responses for monitoring and debugging.

**Flow**:
1. When a request arrives, the middleware logs the request method, URL, and headers
2. The request is passed to the next middleware or route handler
3. After processing, the middleware logs the response status code and time taken
4. The response is returned to the client

**Key Functions**:
- `__init__`: Initializes the middleware with the next middleware in the chain
- `__call__`: Processes the request, logs it, and passes it to the next middleware
- `dispatch`: Asynchronously handles the request/response cycle and logs timing information

**Integration Points**:
- Added to the FastAPI app in `main.py` via `app.add_middleware(LoggingMiddleware)`
- Uses the logging configuration from `utils/logging_config.py`

### 2. Error Handling Middleware (`error_middleware.py`)

**Purpose**: Provides centralized error handling for all exceptions that occur during request processing.

**Flow**:
1. The middleware wraps the request processing in a try-except block
2. If an exception occurs, it is caught and transformed into an appropriate HTTP response
3. The error is logged with contextual information
4. A standardized error response is returned to the client

**Key Functions**:
- `__init__`: Initializes the middleware with the next middleware in the chain
- `__call__`: Processes the request and catches any exceptions
- `handle_exception`: Transforms exceptions into appropriate HTTP responses

**Integration Points**:
- Added to the FastAPI app in `main.py` via `app.add_middleware(ErrorHandlingMiddleware)`
- Works with the exception handlers defined in `main.py`

### 3. Authentication Middleware (`auth_middleware.py`)

**Purpose**: Verifies user authentication and sets the current user in the request context.

**Flow**:
1. The middleware extracts the JWT token from the Authorization header
2. It validates the token and decodes the user information
3. The user information is added to the request state for use in route handlers
4. If authentication fails, an appropriate error response is returned

**Key Functions**:
- `__init__`: Initializes the middleware with the next middleware in the chain
- `__call__`: Processes the request and handles authentication
- `get_token_from_header`: Extracts the JWT token from the Authorization header
- `verify_token`: Validates the JWT token and extracts user information

**Integration Points**:
- Used by the `get_current_user` dependency in route handlers
- Works with the `auth_service.py` for token verification
- Integrated with the user model for retrieving user information

## Middleware Execution Order

The middleware components are executed in the following order:
1. CORS Middleware (built-in FastAPI middleware)
2. Logging Middleware
3. Error Handling Middleware
4. Authentication Middleware (when required by route handlers)

## Error Handling Flow

1. When an exception occurs in any part of the application:
   - If it's a FastAPI HTTPException, it's caught by the built-in exception handler
   - If it's another type of exception, it's caught by our ErrorHandlingMiddleware
   
2. The exception is logged with context information:
   - Request path
   - HTTP method
   - Client IP
   - Exception type and message
   
3. The exception is transformed into an appropriate HTTP response:
   - HTTPExceptions maintain their status code and detail
   - Other exceptions are converted to 500 Internal Server Error with a generic message
   - In development mode, more detailed error information may be included

## Security Considerations

- The authentication middleware validates JWT tokens but doesn't handle token issuance
- Token issuance is handled by the auth_service and auth_router
- Sensitive information is never logged (passwords, tokens, etc.)
- Failed authentication attempts are logged for security monitoring
