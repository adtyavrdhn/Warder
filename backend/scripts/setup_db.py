#!/usr/bin/env python
"""
Database setup script for the Warder application.

This script initializes the database, creates necessary tables,
and runs migrations to set up the initial database state.
"""

import asyncio
import logging
import sys
import os

# Add the parent directory to sys.path to allow imports from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.database import init_db, create_tables
from app.utils.logging_config import configure_logging

# Configure logging
logger = configure_logging("warder_setup")


async def setup_database():
    """Initialize database, create tables, and run migrations."""
    try:
        logger.info("Initializing database connection")
        await init_db()
        
        logger.info("Creating database tables")
        await create_tables()
        
        logger.info("Database setup completed successfully")
    except Exception as e:
        logger.error(f"Error during database setup: {str(e)}")
        raise


if __name__ == "__main__":
    logger.info("Starting database setup")
    asyncio.run(setup_database())
    logger.info("Database setup completed")
