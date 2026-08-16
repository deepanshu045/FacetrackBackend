from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import numpy as np

from app.database.dependency import get_db
from app.models.student import Student
from app.models.college import College
from app.models.admin import Admin
from app.security.password import verify_password
from app.services.attendance_service import mark_attendance
from app.services.report_service import get_student_attendance

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/colleges")
def list_active_colleges(db: Session = Depends(get_db)):
    colleges = (
        db.query(College)
        .filter(College.is_active.is_(True))
        .order_by(College.name)
        .all()
    )
    return {"colleges": [{"id": row.id, "name": row.name, "slug": row.slug} for row in colleges]}


@router.get("/college/access-code/{access_code}")
def resolve_college_by_access_code(
    access_code: str,
    db: Session = Depends(get_db),
):
    code = access_code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="Access code is required.")

    colleges = (
        db.query(College)
        .filter(College.is_active.is_(True), College.access_code_hash.is_not(None))
        .all()
    )
    matches = [college for college in colleges if verify_password(code, college.access_code_hash)]
    if len(matches) != 1:
        raise HTTPException(status_code=404, detail="Invalid college access code.")

    college = matches[0]
    admin = (
        db.query(Admin)
        .filter(Admin.college_id == college.id)
        .order_by(Admin.id)
        .first()
    )
    confidence_threshold = int(admin.threshold) if admin is not None else 85
    sound_alerts = bool(admin.sound_alerts) if admin is not None else True

    students = (
        db.query(Student)
        .filter(Student.college_id == college.id, Student.face_encoding.is_not(None))
        .order_by(Student.name)
        .all()
    )

    return {
        "college_id": college.id,
        "college_slug": college.slug,
        "college_name": college.name,
        "recognition_settings": {
            "confidence_threshold": confidence_threshold,
            "distance_threshold": 0.70 - ((confidence_threshold - 60.0) / 39.0) * 0.20,
            "sound_alerts": sound_alerts,
        },
        "students": [
            {
                "id": student.id,
                "roll_no": student.roll_no,
                "name": student.name,
                "department": student.department or "Not set",
                "face_encoding": np.frombuffer(student.face_encoding, dtype=np.float64).tolist(),
            }
            for student in students
        ],
    }


def _lecture_payload(lecture):
    return {
        "id": lecture.id,
        "subject": lecture.subject,
        "date": lecture.lecture_date.isoformat(),
        "start_time": lecture.start_time.isoformat(),
        "end_time": lecture.end_time.isoformat(),
    }


@router.post("/college/{college_slug}/mark-attendance")
def mark_attendance_public(
    college_slug: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    college = db.query(College).filter(College.slug == college_slug.strip().lower()).first()
    if college is None:
        raise HTTPException(status_code=404, detail="College not found.")

    try:
        student_id = int(payload.get("student_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="A valid student_id is required.")

    student = (
        db.query(Student)
        .filter(Student.id == student_id, Student.college_id == college.id)
        .first()
    )
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found in this college.")

    lecture_id = payload.get("lecture_id")
    if lecture_id is not None:
        try:
            lecture_id = int(lecture_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="lecture_id must be an integer.")

    result = mark_attendance(db, student.id, lecture_id=lecture_id)
    if isinstance(result, str):
        if result == "ALREADY_MARKED":
            # This branch is kept for compatibility if the service returns the
            # duplicate marker directly in a future implementation.
            raise HTTPException(status_code=409, detail="Attendance already marked for this lecture.")

        messages = {
            "NO_ACTIVE_LECTURE": "No active lecture for this student right now.",
            "LECTURE_NOT_FOUND": "Lecture not found.",
            "LECTURE_CANCELLED": "This lecture is cancelled.",
            "LECTURE_NOT_ACTIVE": "This lecture is not currently active.",
            "STUDENT_NOT_IN_LECTURE_CLASS": "Student is not enrolled in this lecture's class.",
            "STUDENT_NOT_FOUND": "Student not found.",
        }
        raise HTTPException(
            status_code=409 if result in {"NO_ACTIVE_LECTURE", "LECTURE_NOT_ACTIVE", "LECTURE_CANCELLED", "STUDENT_NOT_IN_LECTURE_CLASS"} else 404,
            detail=messages.get(result, result),
        )

    # A second scan in the same lecture is a normal duplicate, not a failure.
    if result is None:
        raise HTTPException(status_code=409, detail="Attendance could not be recorded.")

    return {
        "attendance_marked": True,
        "already_marked": False,
        "message": "Attendance marked successfully for this lecture.",
        "student_id": student.id,
        "roll_no": student.roll_no,
        "name": student.name,
        "lecture": _lecture_payload(result.lecture),
    }


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
