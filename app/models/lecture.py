from sqlalchemy import (
    Column, Integer, String, Date, Time, DateTime, ForeignKey,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)
    subject = Column(String(150), nullable=False)
    lecture_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    status = Column(String(20), nullable=False, default="Scheduled", server_default="Scheduled")
    created_at = Column(DateTime, server_default=func.now())

    college = relationship("College", back_populates="lectures")
    attendance = relationship("Attendance", back_populates="lecture", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint(
            "college_id", "lecture_date", "subject", "start_time",
            name="uq_college_lecture"
        ),
    )
