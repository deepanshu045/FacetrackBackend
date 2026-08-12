from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy import LargeBinary
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database.base import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)

    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)

    roll_no = Column(String(30), nullable=False)

    name = Column(String(100), nullable=False)

    email = Column(String(100))

    phone_no = Column(String(30), nullable=True)

    department = Column(String(100))

    image_path = Column(String(255))

    face_encoding = Column(LargeBinary)

    @property
    def has_face(self):
        return self.face_encoding is not None or bool(self.image_path)

    attendance = relationship(
        "Attendance",
        back_populates="student",
        cascade="all, delete"
    )

    college = relationship("College", back_populates="students")

    __table_args__ = (
        UniqueConstraint("college_id", "roll_no", name="uq_student_college_roll_no"),
        UniqueConstraint("college_id", "email", name="uq_student_college_email"),
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
