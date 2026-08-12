from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import ForeignKey
from sqlalchemy import Date
from sqlalchemy import Time
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship


from app.database.base import Base


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True)

    student_id = Column(
        Integer,
        ForeignKey("students.id"),
        nullable=False
    )

    attendance_date = Column(
        Date,
        nullable=False
    )

    attendance_time = Column(
        Time,
        nullable=False
    )

    student = relationship(
    "Student",
    back_populates="attendance"
)

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "attendance_date",
            name="unique_daily_attendance"
        ),
    )