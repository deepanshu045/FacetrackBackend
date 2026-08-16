from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

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
        DateTime(timezone=True),
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
            name="uq_attendance_student_lecture"
        ),
    )