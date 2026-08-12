from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.dependencies.auth import get_current_admin
from app.models.admin import Admin
from app.models.attendance import Attendance
from app.models.student import Student

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
def list_notifications(
    limit: int = Query(default=8, ge=1, le=50),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    records = (
        db.query(Attendance, Student)
        .join(Student, Attendance.student_id == Student.id)
        .filter(Student.college_id == admin.college_id)
        .order_by(Attendance.attendance_date.desc(), Attendance.attendance_time.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": attendance.id,
            "type": "attendance",
            "message": f"Attendance marked for {student.name}",
            "created_at": datetime.combine(
                attendance.attendance_date, attendance.attendance_time
            ).isoformat(),
        }
        for attendance, student in records
    ]
