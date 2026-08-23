from sqlalchemy import Column, Integer, String, Time, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class LectureSchedule(Base):
    __tablename__ = "lecture_schedules"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)
    class_section_id = Column(Integer, ForeignKey("class_sections.id"), nullable=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True, index=True)
    subject = Column(String(150), nullable=False)
    department = Column(String(100), nullable=True, index=True)
    class_name = Column(String(100), nullable=True, index=True)
    section = Column(String(50), nullable=True, index=True)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    effective_start_date = Column(Date, nullable=True, index=True)
    effective_end_date = Column(Date, nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now())

    college = relationship("College", back_populates="lecture_schedules")
    class_section = relationship("ClassSection")
    teacher = relationship("Teacher")

    __table_args__ = (UniqueConstraint("college_id", "class_section_id", "day_of_week", "subject", "start_time", name="uq_college_weekly_schedule"),)
