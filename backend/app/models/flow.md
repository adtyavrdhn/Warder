# Models Flow Documentation

## Overview

The models directory contains the SQLAlchemy ORM (Object-Relational Mapping) models that define the database schema for the Warder application. These models represent the core entities in the system and their relationships.

## Key Models

### 1. User Model (`user.py`)

**Purpose**: Represents user accounts in the system.

**Key Fields**:
- `id`: UUID primary key
- `username`: Unique username
- `email`: Unique email address
- `hashed_password`: Securely stored password hash
- `full_name`: User's full name
- `is_active`: Whether the user account is active
- `is_superuser`: Whether the user has superuser privileges
- `created_at`: Timestamp of account creation
- `updated_at`: Timestamp of last update

**Relationships**:
- `agents`: One-to-many relationship with Agent model
- `documents`: One-to-many relationship with Document model

**Integration Points**:
- Used by the auth_service for authentication
- Referenced by the user_router for user management
- Associated with agents and documents for ownership

### 2. Agent Model (`agent.py`)

**Purpose**: Represents an AI agent in the system, which can be deployed as a container.

**Key Fields**:
- `id`: UUID primary key
- `name`: Name of the agent
- `description`: Description of the agent's purpose
- `type`: Type of agent (e.g., "rag", "chat")
- `user_id`: Foreign key to the User model
- `created_at`: Timestamp of agent creation
- `updated_at`: Timestamp of last update
- `container_id`: ID of the associated container
- `container_status`: Status of the container (e.g., "running", "stopped")
- `container_port`: Port the container is running on
- `knowledge_base_path`: Path to the agent's knowledge base

**Relationships**:
- `user`: Many-to-one relationship with User model
- `documents`: Many-to-many relationship with Document model through AgentDocument

**Integration Points**:
- Managed by the agent_service
- Referenced by the agent_router for API endpoints
- Used by the container_service for container management

### 3. Document Model (`document.py`)

**Purpose**: Represents a document in the system that can be used as knowledge for agents.

**Key Fields**:
- `id`: UUID primary key
- `name`: Name of the document
- `description`: Description of the document
- `file_path`: Path to the document file
- `file_type`: Type of the document (e.g., "pdf", "txt")
- `user_id`: Foreign key to the User model
- `created_at`: Timestamp of document creation
- `updated_at`: Timestamp of last update

**Relationships**:
- `user`: Many-to-one relationship with User model
- `agents`: Many-to-many relationship with Agent model through AgentDocument

**Integration Points**:
- Managed by the document_service
- Referenced by the document_router for API endpoints
- Used by agents as knowledge sources

### 4. AgentDocument Model (`agent_document.py`)

**Purpose**: Represents the many-to-many relationship between agents and documents.

**Key Fields**:
- `agent_id`: Foreign key to the Agent model
- `document_id`: Foreign key to the Document model
- `created_at`: Timestamp of association creation

**Relationships**:
- `agent`: Many-to-one relationship with Agent model
- `document`: Many-to-one relationship with Document model

**Integration Points**:
- Used by the agent_service to manage document associations
- Referenced when building agent knowledge bases

## Database Operations Flow

### 1. Model Creation

When a new entity is created:
1. A new instance of the model is created with the provided data
2. The instance is added to the database session
3. The session is committed to persist the changes
4. The created entity is returned, typically with its generated ID

Example (User creation):
```python
new_user = User(
    username=username,
    email=email,
    hashed_password=hashed_password,
    full_name=full_name,
    is_active=True
)
db.add(new_user)
await db.commit()
await db.refresh(new_user)
return new_user
```

### 2. Model Retrieval

When retrieving entities:
1. A query is constructed using SQLAlchemy's query builder
2. Filters are applied as needed
3. The query is executed to retrieve the results
4. The results are returned, either as a single entity or a list

Example (Get user by ID):
```python
user = await db.get(User, user_id)
if not user:
    raise HTTPException(status_code=404, detail="User not found")
return user
```

### 3. Model Update

When updating an entity:
1. The entity is retrieved from the database
2. The entity's attributes are updated with new values
3. The session is committed to persist the changes
4. The updated entity is returned

Example (Update agent):
```python
agent = await db.get(Agent, agent_id)
if not agent:
    raise HTTPException(status_code=404, detail="Agent not found")
    
for key, value in update_data.dict(exclude_unset=True).items():
    setattr(agent, key, value)
    
await db.commit()
await db.refresh(agent)
return agent
```

### 4. Model Deletion

When deleting an entity:
1. The entity is retrieved from the database
2. The entity is removed from the session
3. The session is committed to persist the changes

Example (Delete document):
```python
document = await db.get(Document, document_id)
if not document:
    raise HTTPException(status_code=404, detail="Document not found")
    
await db.delete(document)
await db.commit()
return {"message": "Document deleted successfully"}
```

## Relationships and Cascade Behavior

The models define relationships with appropriate cascade behavior:

1. **User-Agent Relationship**:
   - When a user is deleted, all their agents are deleted (cascade="all, delete-orphan")
   - This ensures no orphaned agents exist in the system

2. **User-Document Relationship**:
   - When a user is deleted, all their documents are deleted (cascade="all, delete-orphan")
   - This ensures no orphaned documents exist in the system

3. **Agent-Document Relationship**:
   - When an agent is deleted, the association with documents is removed, but documents remain
   - When a document is deleted, the association with agents is removed, but agents remain

## Database Schema Evolution

The models define the current state of the database schema. When changes to the schema are needed:

1. Models are updated to reflect the new schema
2. Alembic migrations are generated to apply the changes to the database
3. Migrations are applied during deployment or application startup

This ensures that the database schema stays in sync with the application models.
