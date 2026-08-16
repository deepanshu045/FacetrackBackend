from sqlalchemy import Column, Integer, String, DateTime, LargeBinary, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database.base import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)
    class_section_id = Column(Integer, ForeignKey("class_sections.id"), nullable=True, index=True)
    roll_no = Column(String(30), nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100))
    phone_no = Column(String(30), nullable=True)
    department = Column(String(100))
    class_name = Column(String(100), nullable=True, index=True)
    section = Column(String(50), nullable=True, index=True)
    image_path = Column(String(255))
    face_encoding = Column(LargeBinary)

    @property
    def has_face(self):
        return self.face_encoding is not None or bool(self.image_path)

    attendance = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    absence_notifications = relationship("AbsenceNotification", back_populates="student", cascade="all, delete-orphan")
    attendance_summary_notifications = relationship("AttendanceSummaryNotification", back_populates="student", cascade="all, delete-orphan")
    college = relationship("College", back_populates="students")
    class_section = relationship("ClassSection")

    __table_args__ = (
        UniqueConstraint("college_id", "roll_no", name="uq_student_college_roll_no"),
        UniqueConstraint("college_id", "email", name="uq_student_college_email"),
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
