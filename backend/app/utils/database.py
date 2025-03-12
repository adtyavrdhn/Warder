"""
Database utility functions for the Warder application.
"""

import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from contextlib import asynccontextmanager

# Configure logger
logger = logging.getLogger(__name__)

# Database URL from environment or default
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/warder"
)

# Create engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

# Create session factory
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Create base class for models
Base = declarative_base()


async def init_db():
    """Initialize database connection."""
    try:
        # Test the connection
        async with AsyncSession(engine) as session:
            result = await session.execute(text("SELECT 1 AS test"))
            await session.commit()
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise


async def drop_tables():
    """Drop all tables in the database."""
    try:
        # Import all models to ensure they're registered with the Base metadata
        # These imports must be here to avoid circular imports
        from app.models.agent import Agent
        from app.models.document_fixed import Document, DocumentChunk
        
        # Drop all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("All tables dropped successfully")
    except Exception as e:
        logger.error(f"Error dropping tables: {str(e)}")
        raise


async def create_tables():
    """Create all tables defined in models."""
    try:
        # Create schema if it doesn't exist
        async with AsyncSession(engine) as session:
            await session.execute(text("CREATE SCHEMA IF NOT EXISTS warder"))
            await session.commit()
        
        # Import all models to ensure they're registered with the Base metadata
        # These imports must be here to avoid circular imports
        from app.models.agent import Agent
        from app.models.document_fixed import Document, DocumentChunk
        
        # First drop any existing tables to ensure clean state
        await drop_tables()
        
        # Create tables with explicit ordering
        async with engine.begin() as conn:
            # Create tables in the correct order to respect foreign key constraints
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise


@asynccontextmanager
async def get_db_session():
    """Get a database session."""
    session = async_session()
    try:
        yield session
    finally:
        await session.close()


async def get_db():
    """Dependency for FastAPI to get a database session."""
    async with get_db_session() as session:
        yield session
