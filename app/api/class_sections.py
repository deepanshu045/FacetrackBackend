from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.dependencies.auth import get_current_admin
from app.models.admin import Admin
from app.models.class_section import ClassSection
from app.schemas.class_section import ClassSectionCreate, ClassSectionResponse

router = APIRouter(prefix="/class-sections", tags=["Class Sections"])


@router.post("", response_model=ClassSectionResponse)
def create_class_section(
    data: ClassSectionCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    existing = db.query(ClassSection).filter(
        ClassSection.college_id == admin.college_id,
        ClassSection.department == data.department,
        ClassSection.class_name == data.class_name,
        ClassSection.section == data.section,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="This class and section already exists.")

    item = ClassSection(
        college_id=admin.college_id,
        department=data.department,
        class_name=data.class_name,
        section=data.section,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[ClassSectionResponse])
def list_class_sections(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return db.query(ClassSection).filter(
        ClassSection.college_id == admin.college_id
    ).order_by(
        ClassSection.department,
        ClassSection.class_name,
        ClassSection.section,
    ).all()


@router.delete("/{class_section_id}")
def delete_class_section(
    class_section_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    item = db.query(ClassSection).filter(
        ClassSection.id == class_section_id,
        ClassSection.college_id == admin.college_id,
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Class section not found.")

    db.delete(item)
    db.commit()
    return {"success": True, "message": "Class section deleted."}
