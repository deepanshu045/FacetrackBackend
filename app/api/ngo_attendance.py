from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.dependencies.auth import get_current_admin
from app.models.admin import Admin
from app.models.ngo_class import NGOClass
from app.models.ngo_student import NGOStudent
from app.models.ngo_attendance import NGOAttendance
from app.schemas.ngo_attendance import (
    NGOClassCreate,
    NGOStudentCreate,
    NGOAttendanceSaveRequest,
)

router = APIRouter(prefix="/ngo", tags=["NGO"])


def get_ngo_class(db: Session, admin: Admin, ngo_class_id: int) -> NGOClass:
    item = db.query(NGOClass).filter(
        NGOClass.id == ngo_class_id,
        NGOClass.admin_id == admin.id,
    ).first()
    if item is None:
        raise HTTPException(404, "NGO class not found.")
    return item


@router.post("/classes")
def create_ngo_class(
    payload: NGOClassCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    existing = db.query(NGOClass).filter(
        NGOClass.admin_id == admin.id,
        NGOClass.department == payload.department,
        NGOClass.class_name == payload.class_name,
        NGOClass.section == payload.section,
    ).first()
    if existing:
        raise HTTPException(409, "This NGO class and section already exists.")

    item = NGOClass(
        admin_id=admin.id,
        department=payload.department,
        class_name=payload.class_name,
        section=payload.section,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "success": True,
        "message": "NGO class created successfully.",
        "class": {
            "id": item.id,
            "department": item.department,
            "class_name": item.class_name,
            "section": item.section,
        },
    }


@router.get("/classes")
def list_ngo_classes(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    classes = db.query(NGOClass).filter(
        NGOClass.admin_id == admin.id
    ).order_by(
        NGOClass.department,
        NGOClass.class_name,
        NGOClass.section,
    ).all()

    return [
        {
            "id": item.id,
            "department": item.department,
            "class_name": item.class_name,
            "section": item.section,
        }
        for item in classes
    ]


@router.post("/students")
def create_ngo_student(
    payload: NGOStudentCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    ngo_class = get_ngo_class(db, admin, payload.ngo_class_id)

    existing = db.query(NGOStudent).filter(
        NGOStudent.admin_id == admin.id,
        NGOStudent.roll_no == payload.roll_no,
    ).first()
    if existing:
        raise HTTPException(409, "A student with this roll number already exists.")

    student = NGOStudent(
        admin_id=admin.id,
        ngo_class_id=ngo_class.id,
        roll_no=payload.roll_no,
        name=payload.name,
        email=payload.email,
        phone_no=payload.phone_no,
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    return {
        "success": True,
        "message": "NGO student created successfully.",
        "student": {
            "id": student.id,
            "roll_no": student.roll_no,
            "name": student.name,
            "email": student.email,
            "phone_no": student.phone_no,
            "ngo_class_id": student.ngo_class_id,
            "class_name": ngo_class.class_name,
            "section": ngo_class.section,
            "department": ngo_class.department,
        },
    }


@router.get("/classes/{ngo_class_id}/students")
def list_ngo_class_students(
    ngo_class_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    get_ngo_class(db, admin, ngo_class_id)

    students = db.query(NGOStudent).filter(
        NGOStudent.admin_id == admin.id,
        NGOStudent.ngo_class_id == ngo_class_id,
    ).order_by(NGOStudent.name, NGOStudent.id).all()

    return [
        {
            "id": student.id,
            "roll_no": student.roll_no,
            "name": student.name,
            "email": student.email,
            "phone_no": student.phone_no,
            "ngo_class_id": student.ngo_class_id,
        }
        for student in students
    ]


@router.post("/attendance")
def save_ngo_attendance(
    payload: NGOAttendanceSaveRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    get_ngo_class(db, admin, payload.ngo_class_id)

    student_ids = [record.student_id for record in payload.records]
    students = db.query(NGOStudent).filter(
        NGOStudent.admin_id == admin.id,
        NGOStudent.ngo_class_id == payload.ngo_class_id,
        NGOStudent.id.in_(student_ids),
    ).all()
    valid_ids = {student.id for student in students}
    invalid_ids = sorted(set(student_ids) - valid_ids)

    if invalid_ids:
        raise HTTPException(400, f"Students not found in this NGO class: {invalid_ids}")

    saved = 0
    for record in payload.records:
        attendance = db.query(NGOAttendance).filter(
            NGOAttendance.admin_id == admin.id,
            NGOAttendance.student_id == record.student_id,
            NGOAttendance.ngo_class_id == payload.ngo_class_id,
            NGOAttendance.attendance_date == payload.attendance_date,
        ).first()

        if attendance is None:
            attendance = NGOAttendance(
                admin_id=admin.id,
                student_id=record.student_id,
                ngo_class_id=payload.ngo_class_id,
                attendance_date=payload.attendance_date,
                marked_by_admin_id=admin.id,
            )
            db.add(attendance)

        attendance.status = record.status
        attendance.marked_by_admin_id = admin.id
        saved += 1

    db.commit()

    return {
        "success": True,
        "message": "NGO attendance saved successfully.",
        "ngo_class_id": payload.ngo_class_id,
        "attendance_date": payload.attendance_date,
        "records_saved": saved,
    }


@router.get("/attendance")
def get_ngo_attendance(
    ngo_class_id: int | None = Query(default=None),
    student_id: int | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    if from_date and to_date and from_date > to_date:
        raise HTTPException(400, "from_date cannot be after to_date.")

    query = db.query(NGOAttendance, NGOStudent).join(
        NGOStudent, NGOStudent.id == NGOAttendance.student_id
    ).filter(
        NGOAttendance.admin_id == admin.id
    )

    if ngo_class_id is not None:
        get_ngo_class(db, admin, ngo_class_id)
        query = query.filter(NGOAttendance.ngo_class_id == ngo_class_id)

    if student_id is not None:
        query = query.filter(
            NGOAttendance.student_id == student_id,
            NGOStudent.admin_id == admin.id,
        )

    if from_date:
        query = query.filter(NGOAttendance.attendance_date >= from_date)
    if to_date:
        query = query.filter(NGOAttendance.attendance_date <= to_date)

    rows = query.order_by(
        NGOAttendance.attendance_date.desc(),
        NGOStudent.name,
    ).all()

    return [
        {
            "id": attendance.id,
            "student_id": student.id,
            "student_name": student.name,
            "ngo_class_id": attendance.ngo_class_id,
            "attendance_date": attendance.attendance_date,
            "status": attendance.status,
        }
        for attendance, student in rows
    ]


@router.get("/students/{student_id}/attendance-summary")
def get_student_attendance_summary(
    student_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    student = db.query(NGOStudent).filter(
        NGOStudent.id == student_id,
        NGOStudent.admin_id == admin.id,
    ).first()
    if student is None:
        raise HTTPException(404, "NGO student not found.")

    total = db.query(func.count(NGOAttendance.id)).filter(
        NGOAttendance.admin_id == admin.id,
        NGOAttendance.student_id == student.id,
    ).scalar() or 0

    present = db.query(func.count(NGOAttendance.id)).filter(
        NGOAttendance.admin_id == admin.id,
        NGOAttendance.student_id == student.id,
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


@router.get("/classes/{ngo_class_id}/attendance-summary")
def get_class_attendance_summary(
    ngo_class_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    ngo_class = get_ngo_class(db, admin, ngo_class_id)

    total = db.query(func.count(NGOAttendance.id)).filter(
        NGOAttendance.admin_id == admin.id,
        NGOAttendance.ngo_class_id == ngo_class.id,
    ).scalar() or 0

    present = db.query(func.count(NGOAttendance.id)).filter(
        NGOAttendance.admin_id == admin.id,
        NGOAttendance.ngo_class_id == ngo_class.id,
        NGOAttendance.status == "Present",
    ).scalar() or 0

    absent = total - present
    percentage = round((present / total) * 100, 2) if total else 0

    return {
        "ngo_class_id": ngo_class.id,
        "class_name": f"{ngo_class.class_name} - {ngo_class.section}",
        "total_attendance_records": total,
        "present": present,
        "absent": absent,
        "percentage": percentage,
    }
