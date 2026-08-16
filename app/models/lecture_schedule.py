from sqlalchemy import Column, Integer, String, Time, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class LectureSchedule(Base):
    __tablename__ = "lecture_schedules"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)
    subject = Column(String(150), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # Monday=0 ... Sunday=6
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    college = relationship("College", back_populates="lecture_schedules")

    __table_args__ = (
        UniqueConstraint(
            "college_id", "day_of_week", "subject", "start_time",
            name="uq_college_weekly_schedule"
        ),
    )
