from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(DateTime, server_default=func.now())

    college = relationship("College")
    assignments = relationship("TeacherAssignment", back_populates="teacher", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("college_id", "username", name="uq_teacher_college_username"),
        UniqueConstraint("college_id", "email", name="uq_teacher_college_email"),
    )


class TeacherAssignment(Base):
    __tablename__ = "teacher_assignments"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    class_section_id = Column(Integer, ForeignKey("class_sections.id", ondelete="CASCADE"), nullable=False, index=True)

    teacher = relationship("Teacher", back_populates="assignments")
    class_section = relationship("ClassSection")

    __table_args__ = (
        UniqueConstraint("teacher_id", "class_section_id", name="uq_teacher_class_section"),
    )
