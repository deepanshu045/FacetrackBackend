from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.dependencies.ngo_auth import get_current_ngo_user
from app.models.class_section import ClassSection
from app.models.ngo_attendance import NGOAttendance
from app.models.student import Student
from app.models.teacher import TeacherAssignment
from app.schemas.ngo_attendance import NGOAttendanceSaveRequest

router = APIRouter(prefix="/ngo", tags=["NGO Attendance"])


def get_allowed_class(db: Session, user_context: dict, class_section_id: int) -> ClassSection:
    college_id = user_context["college_id"]
    class_section = db.query(ClassSection).filter(
        ClassSection.id == class_section_id,
        ClassSection.college_id == college_id,
    ).first()
    if class_section is None:
        raise HTTPException(404, "Class section not found.")

    if user_context["role"] == "teacher":
        teacher_id = user_context["user"].id
        assigned = db.query(TeacherAssignment).filter(
            TeacherAssignment.teacher_id == teacher_id,
            TeacherAssignment.class_section_id == class_section_id,
        ).first()
        if assigned is None:
            raise HTTPException(403, "You are not assigned to this class.")

    return class_section


@router.get("/classes")
def list_ngo_classes(
    db: Session = Depends(get_db),
    user_context: dict = Depends(get_current_ngo_user),
):
    query = db.query(ClassSection).filter(ClassSection.college_id == user_context["college_id"])

    if user_context["role"] == "teacher":
        assigned_ids = db.query(TeacherAssignment.class_section_id).filter(
            TeacherAssignment.teacher_id == user_context["user"].id
        ).subquery()
        query = query.filter(ClassSection.id.in_(assigned_ids))

    classes = query.order_by(ClassSection.department, ClassSection.class_name, ClassSection.section).all()
    return [
        {
            "id": item.id,
            "department": item.department,
            "class_name": item.class_name,
            "section": item.section,
        }
        for item in classes
    ]


@router.get("/classes/{class_section_id}/students")
def list_ngo_class_students(
    class_section_id: int,
    db: Session = Depends(get_db),
    user_context: dict = Depends(get_current_ngo_user),
):
    class_section = get_allowed_class(db, user_context, class_section_id)
    students = db.query(Student).filter(
        Student.college_id == user_context["college_id"],
        Student.class_section_id == class_section.id,
    ).order_by(Student.name, Student.id).all()

    return [
        {
            "id": student.id,
            "student_id": student.roll_no,
            "name": student.name,
            "email": student.email,
            "phone_no": student.phone_no,
            "active": True,
        }
        for student in students
    ]


@router.post("/attendance")
def save_ngo_attendance(
    payload: NGOAttendanceSaveRequest,
    db: Session = Depends(get_db),
    user_context: dict = Depends(get_current_ngo_user),
):
    class_section = get_allowed_class(db, user_context, payload.class_section_id)
    college_id = user_context["college_id"]

    students = db.query(Student).filter(
        Student.college_id == college_id,
        Student.class_section_id == class_section.id,
        Student.id.in_([record.student_id for record in payload.records]),
    ).all()
    student_ids = {student.id for student in students}
    invalid_ids = sorted({record.student_id for record in payload.records} - student_ids)
    if invalid_ids:
        raise HTTPException(400, f"Students not found in this class: {invalid_ids}")

    saved = 0
    for record in payload.records:
        attendance = db.query(NGOAttendance).filter(
            NGOAttendance.college_id == college_id,
            NGOAttendance.student_id == record.student_id,
            NGOAttendance.class_section_id == class_section.id,
            NGOAttendance.attendance_date == payload.attendance_date,
        ).first()

        if attendance is None:
            attendance = NGOAttendance(
                college_id=college_id,
                student_id=record.student_id,
                class_section_id=class_section.id,
                attendance_date=payload.attendance_date,
            )
            db.add(attendance)

        attendance.status = record.status
        attendance.marked_by_admin_id = user_context["user"].id if user_context["role"] == "admin" else None
        attendance.marked_by_teacher_id = user_context["user"].id if user_context["role"] == "teacher" else None
        saved += 1

    db.commit()
    return {
        "success": True,
        "message": "Attendance saved successfully.",
        "class_section_id": class_section.id,
        "attendance_date": payload.attendance_date,
        "records_saved": saved,
    }


@router.get("/attendance")
def get_ngo_attendance(
    class_section_id: int | None = Query(default=None),
    student_id: int | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    user_context: dict = Depends(get_current_ngo_user),
):
    if from_date and to_date and from_date > to_date:
        raise HTTPException(400, "from_date cannot be after to_date.")

    query = db.query(NGOAttendance, Student).join(Student, Student.id == NGOAttendance.student_id).filter(
        NGOAttendance.college_id == user_context["college_id"]
    )

    if class_section_id is not None:
        get_allowed_class(db, user_context, class_section_id)
        query = query.filter(NGOAttendance.class_section_id == class_section_id)
    elif user_context["role"] == "teacher":
        assigned_ids = db.query(TeacherAssignment.class_section_id).filter(
            TeacherAssignment.teacher_id == user_context["user"].id
        ).subquery()
        query = query.filter(NGOAttendance.class_section_id.in_(assigned_ids))

    if student_id is not None:
        query = query.filter(NGOAttendance.student_id == student_id)
    if from_date:
        query = query.filter(NGOAttendance.attendance_date >= from_date)
    if to_date:
        query = query.filter(NGOAttendance.attendance_date <= to_date)

    rows = query.order_by(NGOAttendance.attendance_date.desc(), Student.name).all()
    return [
        {
            "id": attendance.id,
            "student_id": student.id,
            "student_name": student.name,
            "class_section_id": attendance.class_section_id,
            "attendance_date": attendance.attendance_date,
            "status": attendance.status,
        }
        for attendance, student in rows
    ]


@router.get("/students/{student_id}/attendance-summary")
def get_student_attendance_summary(
    student_id: int,
    db: Session = Depends(get_db),
    user_context: dict = Depends(get_current_ngo_user),
):
    student = db.query(Student).filter(
        Student.id == student_id,
        Student.college_id == user_context["college_id"],
    ).first()
    if student is None:
        raise HTTPException(404, "Student not found.")

    if student.class_section_id is None:
        return {"student_id": student.id, "student_name": student.name, "total_classes": 0, "present": 0, "absent": 0, "percentage": 0}

    get_allowed_class(db, user_context, student.class_section_id)
    total = db.query(func.count(NGOAttendance.id)).filter(
        NGOAttendance.student_id == student.id,
        NGOAttendance.college_id == user_context["college_id"],
    ).scalar() or 0
    present = db.query(func.count(NGOAttendance.id)).filter(
        NGOAttendance.student_id == student.id,
        NGOAttendance.college_id == user_context["college_id"],
        NGOAttendance.status == "Present",
    ).scalar() or 0
    absent = total - present
    percentage = round((present / total) * 100, 2) if total else 0

    return {
        "student_id": student.id,
        "student_name": student.name,
        "total_classes": total,
        "present": present,
        "absent": absent,
        "percentage": percentage,
    }


@router.get("/classes/{class_section_id}/attendance-summary")
def get_class_attendance_summary(
    class_section_id: int,
    db: Session = Depends(get_db),
    user_context: dict = Depends(get_current_ngo_user),
):
    class_section = get_allowed_class(db, user_context, class_section_id)
    total = db.query(func.count(NGOAttendance.id)).filter(
        NGOAttendance.college_id == user_context["college_id"],
        NGOAttendance.class_section_id == class_section.id,
    ).scalar() or 0
    present = db.query(func.count(NGOAttendance.id)).filter(
        NGOAttendance.college_id == user_context["college_id"],
        NGOAttendance.class_section_id == class_section.id,
        NGOAttendance.status == "Present",
    ).scalar() or 0
    absent = total - present
    percentage = round((present / total) * 100, 2) if total else 0

    return {
        "class_section_id": class_section.id,
        "class_name": f"{class_section.class_name} - {class_section.section}",
        "total_attendance_records": total,
        "present": present,
        "absent": absent,
        "percentage": percentage,
    }
