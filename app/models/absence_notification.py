from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.sql import func

from app.database.base import Base


class AbsenceNotification(Base):
    __tablename__ = "absence_notifications"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    attendance_date = Column(Date, nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "attendance_date", name="unique_absence_email"),
    )
