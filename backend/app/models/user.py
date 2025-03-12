"""
User model for the Warder application.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Enum, Table, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from passlib.context import CryptContext

from app.utils.database import Base

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, enum.Enum):
    """Enum for user roles."""

    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class UserStatus(str, enum.Enum):
    """Enum for user status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class User(Base):
    """User model."""

    __tablename__ = "users"
    __table_args__ = {"schema": "warder"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)
    status = Column(
        Enum(UserStatus), nullable=False, default=UserStatus.PENDING_VERIFICATION
    )
    verified = Column(Boolean, nullable=False, default=False)
    preferences = Column(JSON, nullable=False, default={})
    quota = Column(
        JSON,
        nullable=False,
        default={"max_agents": 5, "max_storage_mb": 100, "max_requests_per_day": 1000},
    )
    usage = Column(
        JSON,
        nullable=False,
        default={
            "agents_count": 0,
            "storage_used_mb": 0,
            "requests_today": 0,
            "last_request_date": None,
        },
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    agents = relationship("Agent", back_populates="user", cascade="all, delete-orphan")
    documents = relationship(
        "Document", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        """String representation of the user."""
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password for storing."""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str) -> bool:
        """Verify a stored password against a provided password."""
        return pwd_context.verify(plain_password, self.hashed_password)
