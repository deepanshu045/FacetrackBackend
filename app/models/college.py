from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class College(Base):
    __tablename__ = "colleges"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    slug = Column(String(80), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, server_default="1")
    access_code_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    admins = relationship("Admin", back_populates="college")
    students = relationship("Student", back_populates="college")
    lectures = relationship("Lecture", back_populates="college", cascade="all, delete-orphan")
    lecture_schedules = relationship("LectureSchedule", back_populates="college", cascade="all, delete-orphan")
    closures = relationship("CollegeClosure", back_populates="college", cascade="all, delete-orphan")
