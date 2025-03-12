"""
Test fixtures for the Warder application.
"""

import asyncio
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from app.utils.database import Base
from app.main import app
from app.utils.database import get_db


# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/warder_test"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

# Create test session factory
test_async_session = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# Override the get_db dependency for testing
async def override_get_db():
    """Get a test database session."""
    async with test_async_session() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Set up the test database."""
    # Create schema
    async with test_engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS warder"))

    # Create tables
    async with test_engine.begin() as conn:
        # Import all models to ensure they're registered with Base metadata
        from app.models.user import User
        from app.models.agent import Agent
        from app.models.document import Document, DocumentChunk

        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Drop tables after tests
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(setup_database):
    """Get a test database session."""
    async with test_async_session() as session:
        yield session
        # Roll back all changes after each test
        await session.rollback()


@pytest_asyncio.fixture
async def client(setup_database):
    """Get a test client for the FastAPI application."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
