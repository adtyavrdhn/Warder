"""
Script to verify a user for testing purposes.
"""

import asyncio
import sys
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserStatus
from app.utils.database import get_db_session


async def verify_user(user_id: UUID):
    """
    Set a user's status to ACTIVE and verified to True.
    
    Args:
        user_id: The ID of the user to verify
    """
    # Get database session
    async with get_db_session() as db:
        # Update user status
        query = (
            update(User)
            .where(User.id == user_id)
            .values(status=UserStatus.ACTIVE, verified=True)
        )
        await db.execute(query)
        await db.commit()
        print(f"User {user_id} has been verified and activated.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python verify_user.py <user_id>")
        sys.exit(1)
    
    try:
        user_id = UUID(sys.argv[1])
        asyncio.run(verify_user(user_id))
    except ValueError:
        print("Invalid UUID format.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
