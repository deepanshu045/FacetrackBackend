from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database.base import Base


class PendingCollegeRegistration(Base):
    """A college registration that is waiting for email verification."""

    __tablename__ = "pending_college_registrations"

    id = Column(Integer, primary_key=True)
    college_name = Column(String(150), nullable=False)
    college_slug = Column(String(80), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=False)
    name = Column(String(150), nullable=False)
    email = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    verification_token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
