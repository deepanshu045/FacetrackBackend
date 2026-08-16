from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.dependencies.auth import get_current_admin
from app.models.admin import Admin
from app.models.absence_notification import AbsenceNotification
from app.models.student import Student
from app.models.class_section import ClassSection
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse
from app.services.student_service import create_student
from app.services.upload_service import upload_student_image

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/", response_model=list[StudentResponse])
def list_students(query: str | None = Query(default=None, max_length=100), class_section_id: int | None = None, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    students_query = db.query(Student).filter(Student.college_id == admin.college_id)
    if class_section_id is not None:
        allowed = db.query(ClassSection.id).filter(ClassSection.id == class_section_id, ClassSection.college_id == admin.college_id).first()
        if allowed is None:
            raise HTTPException(404, "Class section not found.")
        students_query = students_query.filter(Student.class_section_id == class_section_id)
    normalized_query = query.strip() if query else ""
    if normalized_query:
        pattern = f"%{normalized_query}%"
        students_query = students_query.filter(or_(Student.name.ilike(pattern), Student.roll_no.ilike(pattern), Student.email.ilike(pattern), Student.phone_no.ilike(pattern), Student.department.ilike(pattern)))
        return students_query.order_by(Student.name).limit(20).all()
    return students_query.all()


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    student = db.query(Student).filter(Student.id == student_id, Student.college_id == admin.college_id).first()
    if student is None: raise HTTPException(404, "Student not found")
    return student


@router.post("/register", response_model=StudentResponse)
def register_student(student: StudentCreate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    try:
        new_student = create_student(db, student, admin.college_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if new_student is None:
        raise HTTPException(400, "Roll number already exists.")
    return new_student


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(student_id: int, payload: StudentUpdate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    student = db.query(Student).filter(Student.id == student_id, Student.college_id == admin.college_id).first()
    if student is None: raise HTTPException(404, "Student not found")
    updates = payload.model_dump(exclude_unset=True)
    if "class_section_id" in updates:
        class_section = db.query(ClassSection).filter(ClassSection.id == updates["class_section_id"], ClassSection.college_id == admin.college_id).first() if updates["class_section_id"] is not None else None
        if updates["class_section_id"] is not None and class_section is None:
            raise HTTPException(400, "Class section not found.")
        if class_section:
            student.department, student.class_name, student.section = class_section.department, class_section.class_name, class_section.section
        student.class_section_id = updates.pop("class_section_id")
    for field, value in updates.items(): setattr(student, field, value)
    db.add(student); db.commit(); db.refresh(student)
    return student


@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    student = db.query(Student).filter(Student.id == student_id, Student.college_id == admin.college_id).first()
    if student is None: raise HTTPException(404, "Student not found")
    db.query(AbsenceNotification).filter(AbsenceNotification.student_id == student.id).delete(synchronize_session=False)
    db.delete(student); db.commit()
    return {"success": True}


@router.post("/upload-face/{student_id}")
def upload_face(student_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    result = upload_student_image(db, student_id, file, admin.college_id)
    if result is None: raise HTTPException(404, "Student not found.")
    if result == "INVALID_FACE": raise HTTPException(400, "Image must contain exactly one face.")
    if result == "INVALID_IMAGE": raise HTTPException(400, "Upload a valid image file.")
    if result == "STORAGE_NOT_CONFIGURED": raise HTTPException(503, "Student photo storage is not configured on the server.")
    if result == "DUPLICATE_FACE": raise HTTPException(400, "This face is already registered to another student.")
    return {"message": "Face registered successfully."}
