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
        if value not in {"Present", "Absent"}: raise ValueError("Status must be Present or Absent.")
        return value


class BulkAttendanceRequest(BaseModel):
    status: str
    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str):
        value = value.strip().title()
        if value not in {"Present", "Absent"}: raise ValueError("Status must be Present or Absent.")
        return value


def get_college_lecture(db: Session, lecture_id: int, college_id: int):
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.college_id == college_id).first()
    if lecture is None: raise HTTPException(404, "Lecture not found.")
    if lecture.status == "Cancelled": raise HTTPException(400, "This lecture has been cancelled. Attendance cannot be marked.")
    if lecture.class_section_id is None and not (lecture.department and lecture.class_name and lecture.section): raise HTTPException(400, "Lecture class information is incomplete.")
    return lecture


def get_lecture_students(db: Session, lecture: Lecture, college_id: int):
    query = db.query(Student).filter(Student.college_id == college_id)
    if lecture.class_section_id is not None:
        query = query.filter(Student.class_section_id == lecture.class_section_id)
    else:
        query = query.filter(Student.department == lecture.department, Student.class_name == lecture.class_name, Student.section == lecture.section)
    return query.order_by(Student.roll_no.asc(), Student.id.asc()).all()


def attendance_result(result):
    if isinstance(result, str):
        messages = {
            "STUDENT_NOT_FOUND": (404, "Student not found."),
            "LECTURE_NOT_FOUND": (404, "Lecture not found."),
            "LECTURE_CANCELLED": (400, "This lecture has been cancelled."),
            "STUDENT_NOT_IN_LECTURE_CLASS": (400, "Student does not belong to this lecture's class/section."),
            "INVALID_STATUS": (400, "Status must be Present or Absent."),
        }
        code, message = messages.get(result, (400, result)); raise HTTPException(code, message)


@router.get("/lecture/{lecture_id}")
def get_lecture_attendance(lecture_id: int, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lecture = get_college_lecture(db, lecture_id, admin.college_id); students = get_lecture_students(db, lecture, admin.college_id)
    attendance_rows = {row.student_id: row for row in db.query(Attendance).filter(Attendance.lecture_id == lecture.id).all()}
    rows = []; present = absent = 0
    for student in students:
        record = attendance_rows.get(student.id); row_status = record.status if record else "Absent"
        if row_status == "Present": present += 1
        else: absent += 1
        rows.append({"student_id": student.id, "roll_no": student.roll_no, "name": student.name, "department": student.department, "class_name": student.class_name, "section": student.section, "status": row_status, "attendance_id": record.id if record else None})
    return {"lecture": {"id": lecture.id, "subject": lecture.subject, "class_section_id": lecture.class_section_id, "department": lecture.department, "class_name": lecture.class_name, "section": lecture.section, "lecture_date": str(lecture.lecture_date), "start_time": str(lecture.start_time), "end_time": str(lecture.end_time), "status": lecture.status}, "summary": {"total_students": len(students), "present": present, "absent": absent}, "students": rows}


@router.post("/lecture/{lecture_id}/student")
def mark_student_attendance(lecture_id: int, request: AttendanceStatusRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lecture = get_college_lecture(db, lecture_id, admin.college_id)
    student = next((s for s in get_lecture_students(db, lecture, admin.college_id) if s.id == request.student_id), None)
    if student is None: raise HTTPException(404, "Student does not belong to this lecture's class/section.")
    result = set_attendance_status(db, student.id, lecture_id, request.status); attendance_result(result)
    return {"success": True, "message": f"{student.name} marked {result.status}.", "student_id": student.id, "lecture_id": lecture_id, "status": result.status, "attendance_id": result.id}


@router.post("/lecture/{lecture_id}/mark-all")
def mark_all_attendance(lecture_id: int, request: BulkAttendanceRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lecture = get_college_lecture(db, lecture_id, admin.college_id); students = get_lecture_students(db, lecture, admin.college_id)
    for student in students:
        result = set_attendance_status(db, student.id, lecture.id, request.status); attendance_result(result)
    return {"success": True, "message": f"{len(students)} students from the lecture class marked {request.status}.", "lecture_id": lecture.id, "status": request.status, "updated": len(students)}
