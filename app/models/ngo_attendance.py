from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.base import Base

class NGOAttendance(Base):
    __tablename__ = "ngo_attendance"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("ngo_students.id"), nullable=False, index=True)
    ngo_class_id = Column(Integer, ForeignKey("ngo_classes.id"), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False)
    status = Column(String(10), nullable=False, default="Present")
    marked_by_admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    admin = relationship("Admin", foreign_keys=[admin_id])
    marked_by_admin = relationship("Admin", foreign_keys=[marked_by_admin_id])
    student = relationship("NGOStudent")
    ngo_class = relationship("NGOClass")

    __table_args__ = (
        UniqueConstraint("admin_id", "student_id", "ngo_class_id", "attendance_date",
                         name="uq_ngo_attendance_student_class_date"),
    )
