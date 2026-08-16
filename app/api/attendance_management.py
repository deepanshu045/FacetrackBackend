from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.dependencies.auth import get_current_admin
from app.models.admin import Admin
from app.models.attendance import Attendance
from app.models.lecture import Lecture
from app.models.student import Student
from app.services.attendance_service import set_attendance_status

router = APIRouter(prefix="/attendance", tags=["Attendance Management"])


class AttendanceStatusRequest(BaseModel):
    student_id: int
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str):
        value = value.strip().title()
        if value not in {"Present", "Absent"}:
            raise ValueError("Status must be Present or Absent.")
        return value


class BulkAttendanceRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str):
        value = value.strip().title()
        if value not in {"Present", "Absent"}:
            raise ValueError("Status must be Present or Absent.")
        return value


def get_college_lecture(db: Session, lecture_id: int, college_id: int):
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.college_id == college_id).first()
    if lecture is None:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    if lecture.status == "Cancelled":
        raise HTTPException(status_code=400, detail="This lecture has been cancelled. Attendance cannot be marked.")
    if not lecture.department or not lecture.class_name or not lecture.section:
        raise HTTPException(status_code=400, detail="Lecture class information is incomplete. Set department, class and section before marking attendance.")
    return lecture


def get_lecture_students(db: Session, lecture: Lecture, college_id: int):
    return db.query(Student).filter(
        Student.college_id == college_id,
        Student.department == lecture.department,
        Student.class_name == lecture.class_name,
        Student.section == lecture.section,
    ).order_by(Student.roll_no.asc(), Student.id.asc()).all()


def attendance_result(result):
    if result == "STUDENT_NOT_FOUND":
        raise HTTPException(status_code=404, detail="Student not found.")
    if result == "LECTURE_NOT_FOUND":
        raise HTTPException(status_code=404, detail="Lecture not found.")
    if result == "LECTURE_CANCELLED":
        raise HTTPException(status_code=400, detail="This lecture has been cancelled.")
    if result == "STUDENT_NOT_IN_LECTURE_CLASS":
        raise HTTPException(status_code=400, detail="Student does not belong to this lecture's department, class or section.")
    if result == "INVALID_STATUS":
        raise HTTPException(status_code=400, detail="Status must be Present or Absent.")


@router.get("/lecture/{lecture_id}")
def get_lecture_attendance(lecture_id: int, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lecture = get_college_lecture(db, lecture_id, admin.college_id)
    students = get_lecture_students(db, lecture, admin.college_id)
    attendance_rows = {row.student_id: row for row in db.query(Attendance).filter(Attendance.lecture_id == lecture.id).all()}

    rows = []
    present = 0
    absent = 0
    for student in students:
        record = attendance_rows.get(student.id)
        status = record.status if record else "Absent"
        if status == "Present":
            present += 1
        else:
            absent += 1
        rows.append({
            "student_id": student.id,
            "roll_no": student.roll_no,
            "name": student.name,
            "department": student.department,
            "class_name": student.class_name,
            "section": student.section,
            "status": status,
            "attendance_id": record.id if record else None,
        })

    return {
        "lecture": {
            "id": lecture.id,
            "subject": lecture.subject,
            "department": lecture.department,
            "class_name": lecture.class_name,
            "section": lecture.section,
            "lecture_date": str(lecture.lecture_date),
            "start_time": str(lecture.start_time),
            "end_time": str(lecture.end_time),
            "status": lecture.status,
        },
        "summary": {"total_students": len(students), "present": present, "absent": absent},
        "students": rows,
    }


@router.post("/lecture/{lecture_id}/student")
def mark_student_attendance(lecture_id: int, request: AttendanceStatusRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lecture = get_college_lecture(db, lecture_id, admin.college_id)
    student = db.query(Student).filter(
        Student.id == request.student_id,
        Student.college_id == admin.college_id,
        Student.department == lecture.department,
        Student.class_name == lecture.class_name,
        Student.section == lecture.section,
    ).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student does not belong to this lecture's class/section.")

    result = set_attendance_status(db, student.id, lecture_id, request.status)
    attendance_result(result)
    return {"success": True, "message": f"{student.name} marked {result.status}.", "student_id": student.id, "lecture_id": lecture_id, "status": result.status, "attendance_id": result.id}


@router.post("/lecture/{lecture_id}/mark-all")
def mark_all_attendance(lecture_id: int, request: BulkAttendanceRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lecture = get_college_lecture(db, lecture_id, admin.college_id)
    students = get_lecture_students(db, lecture, admin.college_id)
    updated = 0
    for student in students:
        result = set_attendance_status(db, student.id, lecture.id, request.status)
        attendance_result(result)
        updated += 1

    return {
        "success": True,
        "message": f"{updated} students from {lecture.department} {lecture.class_name} Section {lecture.section} marked {request.status}.",
        "lecture_id": lecture.id,
        "status": request.status,
        "updated": updated,
    }
