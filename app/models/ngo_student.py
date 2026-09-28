from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.base import Base


class NGOStudent(Base):
    __tablename__ = "ngo_students"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False, index=True)
    ngo_class_id = Column(Integer, ForeignKey("ngo_classes.id"), nullable=False, index=True)
    roll_no = Column(String(30), nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    phone_no = Column(String(30), nullable=True)

    admin = relationship("Admin")
    ngo_class = relationship("NGOClass")

    __table_args__ = (
        UniqueConstraint(
            "admin_id", "roll_no",
            name="uq_ngo_admin_student_roll_no",
        ),
    )
