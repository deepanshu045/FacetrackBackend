from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    student_id = Column(
        Integer,
        ForeignKey("students.id"),
        nullable=False,
        index=True
    )

    lecture_id = Column(
        Integer,
        ForeignKey("lectures.id"),
        nullable=False,
        index=True
    )

    marked_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    student = relationship(
        "Student",
        back_populates="attendance"
    )

    lecture = relationship(
        "Lecture",
        back_populates="attendance"
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "lecture_id",
            name="unique_student_lecture_attendance"
        ),
    )