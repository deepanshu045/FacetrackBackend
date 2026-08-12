from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.models.student import Student
from app.models.college import College
from app.services.report_service import get_student_attendance

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/{college_slug}/attendance/{roll_no}")
def get_public_attendance_report(
    college_slug: str,
    roll_no: str,
    db: Session = Depends(get_db),
):
    student = (
        db.query(Student)
        .join(College)
        .filter(College.slug == college_slug.strip().lower(), Student.roll_no == roll_no.strip())
        .first()
    )
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    return {
        "student": {
            "roll_no": student.roll_no,
            "name": student.name,
            "department": student.department,
        },
        "records": get_student_attendance(db, student.id, student.college_id),
    }
