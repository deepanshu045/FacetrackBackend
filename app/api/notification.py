from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.dependencies.auth import get_current_admin
from app.models.admin import Admin
from app.models.attendance import Attendance
from app.models.lecture import Lecture
from app.models.student import Student

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
def list_notifications(
    limit: int = Query(default=8, ge=1, le=50),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    records = (
        db.query(Attendance, Student, Lecture)
        .join(Student, Attendance.student_id == Student.id)
        .join(Lecture, Attendance.lecture_id == Lecture.id)
        .filter(
            Student.college_id == admin.college_id,
            Lecture.college_id == admin.college_id,
        )
        .order_by(Lecture.lecture_date.desc(), Attendance.marked_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": attendance.id,
            "type": "attendance",
            "message": f"Attendance marked for {student.name}",
            "created_at": attendance.marked_at.isoformat(),
            "lecture_id": lecture.id,
            "subject": lecture.subject,
            "attendance_date": lecture.lecture_date.isoformat(),
            "status": attendance.status,
        }
        for attendance, student, lecture in records
    ]
