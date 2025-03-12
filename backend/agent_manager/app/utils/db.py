"""Database utilities for the Agent Manager service."""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from config.db import DATABASE_URL

# Create base class for models
Base = declarative_base()

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# Get database session
async def get_db():
    """Get database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


# Initialize database
async def init_db():
    """Initialize database."""
    async with engine.begin() as conn:
        # Create schema if it doesn't exist
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS warder"))

        # Drop all tables first to ensure clean schema
        await conn.run_sync(Base.metadata.drop_all)
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
