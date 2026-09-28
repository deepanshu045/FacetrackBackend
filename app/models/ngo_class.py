from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.base import Base

class NGOClass(Base):
    __tablename__ = "ngo_classes"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False, index=True)
    department = Column(String(100), nullable=False)
    class_name = Column(String(100), nullable=False)
    section = Column(String(50), nullable=False)

    admin = relationship("Admin")

    __table_args__ = (
        UniqueConstraint("admin_id", "department", "class_name", "section",
                         name="uq_ngo_admin_class_section"),
    )
