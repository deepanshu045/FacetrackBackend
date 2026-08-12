import os
import shutil

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import UploadFile
from fastapi import HTTPException

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.services.recognition_service import recognize_student
from app.services.attendance_service import mark_attendance

from app.dependencies.auth import get_current_admin
from app.models.admin import Admin
from app.models.student import Student


class ManualAttendanceRequest(BaseModel):
    student_id: int

router = APIRouter(
    prefix="/recognition",
    tags=["Recognition"]
)

TEMP_FOLDER = "app/temp"

os.makedirs(TEMP_FOLDER, exist_ok=True)


@router.post("/match")
def match_face(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    ...

    filepath = os.path.join(
        TEMP_FOLDER,
        file.filename
    )

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = recognize_student(db, filepath, admin.college_id)

    os.remove(filepath)

    if result == "INVALID_FACE":
        raise HTTPException(
            status_code=400,
            detail="Image must contain exactly one face."
        )

    if result is None:
        return {
            "matched": False,
            "message": "No matching student found."
        }

    attendance = mark_attendance(db, result.id)

    if attendance == "ALREADY_MARKED":
        return {
            "matched": True,
            "attendance_marked": False,
            "message": "Attendance already marked today.",
            "student_id": result.id,
            "roll_no": result.roll_no,
            "name": result.name,
            "department": result.department
        }
    
    return {
        "matched": True,
        "attendance_marked": True,
        "message": "Attendance marked successfully.",
        "student_id": result.id,
        "roll_no": result.roll_no,
        "name": result.name,
        "department": result.department,
        "attendance_id": attendance.id,
        "date": str(attendance.attendance_date),
        "time": str(attendance.attendance_time)
    }


@router.post("/manual")
def mark_attendance_manual(
    request: ManualAttendanceRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    student = db.query(Student).filter(
        Student.id == request.student_id,
        Student.college_id == admin.college_id,
    ).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")

    attendance = mark_attendance(db, student.id)

    if attendance == "ALREADY_MARKED":
        return {
            "matched": True,
            "attendance_marked": False,
            "message": "Attendance already marked today.",
            "student_id": student.id,
            "roll_no": student.roll_no,
            "name": student.name,
            "department": student.department
        }

    return {
        "matched": True,
        "attendance_marked": True,
        "message": "Attendance marked successfully.",
        "student_id": student.id,
        "roll_no": student.roll_no,
        "name": student.name,
        "department": student.department,
        "attendance_id": attendance.id,
        "date": str(attendance.attendance_date),
        "time": str(attendance.attendance_time)
    }
