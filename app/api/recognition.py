import os
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.services.recognition_service import recognize_student
from app.services.attendance_service import mark_attendance
from app.dependencies.auth import get_current_admin
from app.models.admin import Admin
from app.models.student import Student
from app.models.college import College
from app.security.password import verify_password
from app.services.desktop_presence_service import mark_desktop_seen, desktop_status


class ManualAttendanceRequest(BaseModel):
    student_id: int


class DesktopHeartbeatRequest(BaseModel):
    access_code: str


router = APIRouter(prefix="/recognition", tags=["Recognition"])
TEMP_FOLDER = "app/temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)


def handle_attendance_result(result):
    messages = {
        "NO_ACTIVE_LECTURE": "No active lecture is running right now.",
        "LECTURE_NOT_FOUND": "Lecture not found.",
        "LECTURE_NOT_ACTIVE": "This lecture is not currently active.",
        "LECTURE_CANCELLED": "This lecture has been cancelled. Attendance cannot be marked.",
        "STUDENT_NOT_FOUND": "Student not found.",
    }
    if result in messages:
        raise HTTPException(status_code=400, detail=messages[result])


@router.post("/desktop-heartbeat")
def desktop_heartbeat(request: DesktopHeartbeatRequest, db: Session = Depends(get_db)):
    code = request.access_code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="Access code is required.")

    colleges = (
        db.query(College)
        .filter(College.is_active.is_(True), College.access_code_hash.is_not(None))
        .all()
    )
    matches = [college for college in colleges if verify_password(code, college.access_code_hash)]
    if len(matches) != 1:
        raise HTTPException(status_code=401, detail="Invalid camera access code.")

    mark_desktop_seen(matches[0].id)
    return {"online": True, "college_id": matches[0].id}


@router.get("/desktop-status")
def get_desktop_status(admin: Admin = Depends(get_current_admin)):
    status = desktop_status(admin.college_id)
    return {"college_id": admin.college_id, **status}


@router.post("/match")
def match_face(file: UploadFile = File(...), db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    filepath = os.path.join(TEMP_FOLDER, file.filename)
    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        result = recognize_student(db, filepath, admin.college_id)
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    if result == "INVALID_FACE":
        raise HTTPException(status_code=400, detail="Image must contain exactly one face.")
    if result is None:
        return {"matched": False, "message": "No matching student found."}

    attendance = mark_attendance(db, result.id)
    if attendance == "ALREADY_MARKED":
        return {"matched": True, "attendance_marked": False, "message": "Attendance already marked for this lecture.", "student_id": result.id, "roll_no": result.roll_no, "name": result.name, "department": result.department}
    handle_attendance_result(attendance)
    return {"matched": True, "attendance_marked": True, "message": "Attendance marked successfully.", "student_id": result.id, "roll_no": result.roll_no, "name": result.name, "department": result.department, "attendance_id": attendance.id, "date": str(attendance.marked_at.date()), "time": str(attendance.marked_at.time())}


@router.post("/manual")
def mark_attendance_manual(request: ManualAttendanceRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    student = db.query(Student).filter(Student.id == request.student_id, Student.college_id == admin.college_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")

    attendance = mark_attendance(db, student.id)
    if attendance == "ALREADY_MARKED":
        return {"matched": True, "attendance_marked": False, "message": "Attendance already marked for this lecture.", "student_id": student.id, "roll_no": student.roll_no, "name": student.name, "department": student.department}
    handle_attendance_result(attendance)
    return {"matched": True, "attendance_marked": True, "message": "Attendance marked successfully.", "student_id": student.id, "roll_no": student.roll_no, "name": student.name, "department": student.department, "attendance_id": attendance.id, "date": str(attendance.marked_at.date()), "time": str(attendance.marked_at.time())}
