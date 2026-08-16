from sqlalchemy import Column, Integer, String, Date, Time, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)
    class_section_id = Column(Integer, ForeignKey("class_sections.id"), nullable=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True, index=True)
    subject = Column(String(150), nullable=False)
    department = Column(String(100), nullable=True, index=True)
    class_name = Column(String(100), nullable=True, index=True)
    section = Column(String(50), nullable=True, index=True)
    lecture_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    status = Column(String(20), nullable=False, default="Scheduled", server_default="Scheduled")
    created_at = Column(DateTime, server_default=func.now())

    college = relationship("College", back_populates="lectures")
    class_section = relationship("ClassSection")
    teacher = relationship("Teacher")
    attendance = relationship("Attendance", back_populates="lecture", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("college_id", "lecture_date", "subject", "start_time", name="uq_college_lecture"),
    )
