from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.base import Base


class ClassSection(Base):
    __tablename__ = "class_sections"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)
    department = Column(String(100), nullable=False)
    class_name = Column(String(100), nullable=False)
    section = Column(String(50), nullable=False)

    college = relationship("College")

    __table_args__ = (
        UniqueConstraint(
            "college_id", "department", "class_name", "section",
            name="uq_college_class_section",
        ),
    )
