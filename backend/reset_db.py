"""
Script to reset the database for the Warder application.
This will drop and recreate the database from scratch.
"""

import asyncio
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("db_reset")

# Add the parent directory to the path so we can import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the database functions
from app.utils.database import init_db, drop_tables, create_tables

# Import models to ensure they're registered with SQLAlchemy
from app.models.agent import Agent, AgentType, AgentStatus
from app.models.document import Document, DocumentChunk, DocumentStatus


async def reset_database():
    """Reset the database by dropping and recreating all tables."""
    try:
        logger.info("Initializing database connection")
        await init_db()

        logger.info("Dropping all existing tables")
        await drop_tables()

        logger.info("Creating tables from scratch")
        await create_tables()

        logger.info("Database reset completed successfully")
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(reset_database())
