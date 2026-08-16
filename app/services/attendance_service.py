from datetime import datetime

from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.lecture import Lecture
from app.models.student import Student
from app.services.lecture_schedule_service import sync_lectures_for_date


def get_active_lecture(db: Session, student_id: int):
    now = datetime.now()
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        return None

    sync_lectures_for_date(db, student.college_id, now.date())

    return (
        db.query(Lecture)
        .filter(
            Lecture.college_id == student.college_id,
            Lecture.lecture_date == now.date(),
            Lecture.start_time <= now.time(),
            Lecture.end_time >= now.time(),
            Lecture.status == "Scheduled",
        )
        .order_by(Lecture.start_time.asc())
        .first()
    )


def mark_attendance(db: Session, student_id: int, lecture_id: int | None = None):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        return "STUDENT_NOT_FOUND"

    if lecture_id is None:
        lecture = get_active_lecture(db, student_id)
        if lecture is None:
            return "NO_ACTIVE_LECTURE"
    else:
        lecture = (
            db.query(Lecture)
            .filter(Lecture.id == lecture_id, Lecture.college_id == student.college_id)
            .first()
        )
        if lecture is None:
            return "LECTURE_NOT_FOUND"
        if lecture.status == "Cancelled":
            return "LECTURE_CANCELLED"

        now = datetime.now()
        if lecture.lecture_date != now.date() or now.time() < lecture.start_time or now.time() > lecture.end_time:
            return "LECTURE_NOT_ACTIVE"

    if lecture.status == "Cancelled":
        return "LECTURE_CANCELLED"

    existing = (
        db.query(Attendance)
        .filter(Attendance.student_id == student_id, Attendance.lecture_id == lecture.id)
        .first()
    )
    if existing:
        return "ALREADY_MARKED"

    attendance = Attendance(student_id=student_id, lecture_id=lecture.id, marked_at=datetime.now())
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance
