from sqlalchemy import Column, Integer, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database.base import Base


class AttendanceSummaryNotification(Base):
    __tablename__ = "attendance_summary_notifications"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(
        Integer,
        ForeignKey("students.id"),
        nullable=False,
        index=True
    )

    summary_date = Column(
        Date,
        nullable=False,
        index=True
    )

    sent_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    student = relationship(
        "Student",
        back_populates="attendance_summary_notifications"
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "summary_date",
            name="uq_attendance_summary_student_date"
        ),
    )