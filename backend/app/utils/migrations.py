"""
Database migration utilities for the Warder application.

This module provides functions for creating and running database migrations
to update the database schema as the application evolves.
"""

import logging
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.database import get_db

logger = logging.getLogger("warder.migrations")


async def run_migrations(db: AsyncSession) -> None:
    """
    Run all database migrations in order.

    Args:
        db: Database session
    """
    logger.info("Running database migrations")

    try:
        # Run migrations in order
        await create_schema(db)
        await create_user_tables(db)
        await add_user_id_to_agents(db)
        await add_user_id_to_documents(db)

        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Error running migrations: {str(e)}")
        raise


async def create_schema(db: AsyncSession) -> None:
    """
    Create the warder schema if it doesn't exist.

    Args:
        db: Database session
    """
    logger.info("Creating warder schema if it doesn't exist")

    query = text("CREATE SCHEMA IF NOT EXISTS warder")
    await db.execute(query)
    await db.commit()


async def create_user_tables(db: AsyncSession) -> None:
    """
    Create the users table if it doesn't exist.

    Args:
        db: Database session
    """
    logger.info("Creating users table if it doesn't exist")

    query = text(
        """
    CREATE TABLE IF NOT EXISTS warder.users (
        id UUID PRIMARY KEY,
        username VARCHAR NOT NULL UNIQUE,
        email VARCHAR NOT NULL UNIQUE,
        hashed_password VARCHAR NOT NULL,
        first_name VARCHAR,
        last_name VARCHAR,
        role VARCHAR NOT NULL,
        status VARCHAR NOT NULL,
        verified BOOLEAN NOT NULL DEFAULT FALSE,
        preferences JSONB NOT NULL DEFAULT '{}',
        quota JSONB NOT NULL DEFAULT '{"max_agents": 5, "max_storage_mb": 100, "max_requests_per_day": 1000}',
        usage JSONB NOT NULL DEFAULT '{"agents_count": 0, "storage_used_mb": 0, "requests_today": 0, "last_request_date": null}',
        created_at TIMESTAMP WITH TIME ZONE NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL
    )
    """
    )

    await db.execute(query)

    # Create indexes
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_username ON warder.users (username)",
        "CREATE INDEX IF NOT EXISTS idx_users_email ON warder.users (email)",
        "CREATE INDEX IF NOT EXISTS idx_users_role ON warder.users (role)",
        "CREATE INDEX IF NOT EXISTS idx_users_status ON warder.users (status)",
    ]

    for index_query in indexes:
        await db.execute(text(index_query))

    await db.commit()


async def add_user_id_to_agents(db: AsyncSession) -> None:
    """
    Add user_id column to agents table if it doesn't exist.

    Args:
        db: Database session
    """
    logger.info("Adding user_id to agents table if it doesn't exist")

    # Check if column exists
    check_query = text(
        """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = 'warder'
    AND table_name = 'agents'
    AND column_name = 'user_id'
    """
    )

    result = await db.execute(check_query)
    column_exists = result.scalar() is not None

    if not column_exists:
        # Add column
        alter_query = text(
            """
        ALTER TABLE warder.agents
        ADD COLUMN user_id UUID REFERENCES warder.users(id)
        """
        )

        await db.execute(alter_query)

        # Create default admin user if not exists
        create_admin_query = text(
            """
        INSERT INTO warder.users (
            id, username, email, hashed_password, role, status, verified,
            preferences, quota, usage, created_at, updated_at
        )
        VALUES (
            '00000000-0000-0000-0000-000000000000',
            'admin',
            'admin@example.com',
            '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', -- 'password'
            'admin',
            'active',
            TRUE,
            '{}',
            '{"max_agents": 999, "max_storage_mb": 999999, "max_requests_per_day": 999999}',
            '{"agents_count": 0, "storage_used_mb": 0, "requests_today": 0, "last_request_date": null}',
            NOW(),
            NOW()
        )
        ON CONFLICT (username) DO NOTHING
        """
        )

        await db.execute(create_admin_query)

        # Set all existing agents to belong to admin user
        update_query = text(
            """
        UPDATE warder.agents
        SET user_id = '00000000-0000-0000-0000-000000000000'
        WHERE user_id IS NULL
        """
        )

        await db.execute(update_query)

        # Make column not nullable
        not_null_query = text(
            """
        ALTER TABLE warder.agents
        ALTER COLUMN user_id SET NOT NULL
        """
        )

        await db.execute(not_null_query)

        # Create index
        index_query = text(
            """
        CREATE INDEX IF NOT EXISTS idx_agents_user_id ON warder.agents (user_id)
        """
        )

        await db.execute(index_query)

        await db.commit()


async def add_user_id_to_documents(db: AsyncSession) -> None:
    """
    Add user_id column to documents table if it doesn't exist.

    Args:
        db: Database session
    """
    logger.info("Adding user_id to documents table if it doesn't exist")

    # Check if column exists
    check_query = text(
        """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = 'warder'
    AND table_name = 'documents'
    AND column_name = 'user_id'
    """
    )

    result = await db.execute(check_query)
    column_exists = result.scalar() is not None

    if not column_exists:
        # Add column
        alter_query = text(
            """
        ALTER TABLE warder.documents
        ADD COLUMN user_id UUID REFERENCES warder.users(id)
        """
        )

        await db.execute(alter_query)

        # Set all existing documents to belong to admin user
        update_query = text(
            """
        UPDATE warder.documents
        SET user_id = '00000000-0000-0000-0000-000000000000'
        WHERE user_id IS NULL
        """
        )

        await db.execute(update_query)

        # Make column not nullable
        not_null_query = text(
            """
        ALTER TABLE warder.documents
        ALTER COLUMN user_id SET NOT NULL
        """
        )

        await db.execute(not_null_query)

        # Create index
        index_query = text(
            """
        CREATE INDEX IF NOT EXISTS idx_documents_user_id ON warder.documents (user_id)
        """
        )

        await db.execute(index_query)

        await db.commit()


async def run_migrations_standalone():
    """Run migrations as a standalone script."""
    try:
        db_generator = get_db()
        db = await anext(db_generator)
        await run_migrations(db)
    except Exception as e:
        logger.error(f"Error running migrations: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(run_migrations_standalone())
