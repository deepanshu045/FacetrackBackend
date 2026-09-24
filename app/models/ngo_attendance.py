from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class NGOAttendance(Base):
    """Simple daily attendance record for the NGO web application.

    This table is intentionally separate from FaceTrack's lecture-based
    attendance table so the existing application behavior is not changed.
    """

    __tablename__ = "ngo_attendance"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    class_section_id = Column(Integer, ForeignKey("class_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    status = Column(String(10), nullable=False, server_default="Present")
    marked_by_admin_id = Column(Integer, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    marked_by_teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    student = relationship("Student")
    class_section = relationship("ClassSection")

    __table_args__ = (
        UniqueConstraint(
            "college_id", "student_id", "class_section_id", "attendance_date",
            name="uq_ngo_attendance_student_class_date",
        ),
        CheckConstraint("status IN ('Present', 'Absent')", name="ck_ngo_attendance_status"),
    )
