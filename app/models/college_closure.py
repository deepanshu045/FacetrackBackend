from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class CollegeClosure(Base):
    __tablename__ = "college_closures"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False, index=True)
    closure_date = Column(Date, nullable=False)
    reason = Column(String(50), nullable=False, default="Other")
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    college = relationship("College", back_populates="closures")

    __table_args__ = (
        UniqueConstraint("college_id", "closure_date", name="uq_college_closure_date"),
    )
