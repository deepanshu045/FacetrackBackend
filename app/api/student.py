from fastapi import APIRouter
from fastapi import Query
from fastapi import Depends
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import File
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.dependencies.auth import get_current_admin
from app.models.admin import Admin
from app.models.absence_notification import AbsenceNotification
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse
from app.services.student_service import create_student
from app.services.upload_service import upload_student_image

router = APIRouter(
    prefix="/students",
    tags=["Students"]
)


@router.get("/", response_model=list[StudentResponse])
def list_students(
    query: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    students_query = db.query(Student).filter(Student.college_id == admin.college_id)
    normalized_query = query.strip() if query else ""

    if normalized_query:
        pattern = f"%{normalized_query}%"
        students_query = students_query.filter(
            or_(
                Student.name.ilike(pattern),
                Student.roll_no.ilike(pattern),
                Student.email.ilike(pattern),
                Student.phone_no.ilike(pattern),
                Student.department.ilike(pattern),
            )
        )
        return students_query.order_by(Student.name).limit(20).all()

    return students_query.all()


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    student = db.query(Student).filter(Student.id == student_id, Student.college_id == admin.college_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.post(
    "/register",
    response_model=StudentResponse
)
def register_student(
    student: StudentCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    new_student = create_student(db, student, admin.college_id)

    if new_student is None:
        raise HTTPException(
            status_code=400,
            detail="Roll number already exists."
        )

    return new_student


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    student = db.query(Student).filter(Student.id == student_id, Student.college_id == admin.college_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(student, field, value)

    db.add(student)
    db.commit()
    db.refresh(student)

    return student


@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    student = db.query(Student).filter(Student.id == student_id, Student.college_id == admin.college_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    # Attendance is deleted by Student.attendance's ORM cascade. Absence
    # notifications also reference the student, but are not an ORM relationship,
    # so remove them explicitly before deleting the student.
    db.query(AbsenceNotification).filter(
        AbsenceNotification.student_id == student.id
    ).delete(synchronize_session=False)
    db.delete(student)
    db.commit()

    return {"success": True}


@router.post("/upload-face/{student_id}")
def upload_face(
    student_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    result = upload_student_image(
        db,
        student_id,
        file,
        admin.college_id,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found."
        )

    if result == "INVALID_FACE":
        raise HTTPException(
            status_code=400,
            detail="Image must contain exactly one face."
        )

    if result == "INVALID_IMAGE":
        raise HTTPException(
            status_code=400,
            detail="Upload a valid image file."
        )

    if result == "STORAGE_NOT_CONFIGURED":
        raise HTTPException(
            status_code=503,
            detail="Student photo storage is not configured on the server."
        )

    if result == "DUPLICATE_FACE":
        raise HTTPException(
            status_code=400,
            detail="This face is already registered to another student."
        )

    return {
        "message": "Face registered successfully."
    }

