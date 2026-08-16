from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship

from sqlalchemy.sql import func

from app.database.base import Base


class Admin(Base):
    __tablename__ = "admins"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)

    username = Column(String(100), nullable=False, unique=True, index=True)

    name = Column(String(150), nullable=True)

    email = Column(
        String(100),
        nullable=False
    )

    password_hash = Column(
        String(255),
        nullable=False
    )

    notifications = Column(
        Boolean,
        nullable=False,
        server_default="1"
    )

    email_alerts = Column(
        Boolean,
        nullable=False,
        server_default="0"
    )

    sound_alerts = Column(
        Boolean,
        nullable=False,
        server_default="1"
    )

    threshold = Column(
        Integer,
        nullable=False,
        server_default="85"
    )

    resolution = Column(
        String(10),
        nullable=False,
        server_default="1080p"
    )

    fps = Column(
        String(10),
        nullable=False,
        server_default="30"
    )

    language = Column(
        String(30),
        nullable=False,
        server_default="English"
    )

    college = relationship("College", back_populates="admins")

    __table_args__ = (
        UniqueConstraint("college_id", "email", name="uq_admin_college_email"),
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )
