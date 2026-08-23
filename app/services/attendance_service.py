from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.lecture import Lecture
from app.models.student import Student
from app.services.lecture_schedule_service import sync_lectures_for_date
from app.utils.timezone import now_local


ACTIVE_LECTURE_STATUS = "Scheduled"


def get_active_lecture(db: Session, student_id: int):
    now = now_local()
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        return None

    sync_lectures_for_date(db, student.college_id, now.date())

    query = db.query(Lecture).filter(
        Lecture.college_id == student.college_id,
        Lecture.lecture_date == now.date(),
        Lecture.start_time <= now.time(),
        Lecture.end_time >= now.time(),
        Lecture.status == ACTIVE_LECTURE_STATUS,
    )

    if student.class_section_id is not None:
        query = query.filter(Lecture.class_section_id == student.class_section_id)
    else:
        query = query.filter(
            Lecture.department == student.department,
            Lecture.class_name == student.class_name,
            Lecture.section == student.section,
        )

    return query.order_by(Lecture.start_time.asc()).first()


def _validate_status(status: str) -> str | None:
    normalized_status = status.strip().title()
    return normalized_status if normalized_status in {"Present", "Absent"} else None


def _get_lecture_for_student(db: Session, student: Student, lecture_id: int):
    lecture = (
        db.query(Lecture)
        .filter(Lecture.id == lecture_id, Lecture.college_id == student.college_id)
        .first()
    )
    if lecture is None:
        return "LECTURE_NOT_FOUND"
    if lecture.status == "Cancelled":
        return "LECTURE_CANCELLED"

    if student.class_section_id is not None and lecture.class_section_id is not None:
        if lecture.class_section_id != student.class_section_id:
            return "STUDENT_NOT_IN_LECTURE_CLASS"
    elif (
        lecture.department != student.department
        or lecture.class_name != student.class_name
        or lecture.section != student.section
    ):
        return "STUDENT_NOT_IN_LECTURE_CLASS"

    return lecture


def set_attendance_status(db: Session, student_id: int, lecture_id: int, status: str):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        return "STUDENT_NOT_FOUND"

    normalized_status = _validate_status(status)
    if normalized_status is None:
        return "INVALID_STATUS"

    lecture = _get_lecture_for_student(db, student, lecture_id)
    if isinstance(lecture, str):
        return lecture

    attendance = (
        db.query(Attendance)
        .filter(
            Attendance.student_id == student_id,
            Attendance.lecture_id == lecture_id,
        )
        .first()
    )
    if attendance is None:
        attendance = Attendance(
            student_id=student_id,
            lecture_id=lecture_id,
            status=normalized_status,
            marked_at=now_local(),
        )
        db.add(attendance)
    else:
        attendance.status = normalized_status
        attendance.marked_at = now_local()

    db.commit()
    db.refresh(attendance)
    return attendance


def mark_attendance(db: Session, student_id: int, lecture_id: int | None = None):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        return "STUDENT_NOT_FOUND"

    if lecture_id is None:
        lecture = get_active_lecture(db, student_id)
        if lecture is None:
            return "NO_ACTIVE_LECTURE"
    else:
        lecture = _get_lecture_for_student(db, student, lecture_id)
        if isinstance(lecture, str):
            return lecture

        now = now_local()
        if (
            lecture.lecture_date != now.date()
            or now.time() < lecture.start_time
            or now.time() > lecture.end_time
        ):
            return "LECTURE_NOT_ACTIVE"

    existing = (
        db.query(Attendance)
        .filter(
            Attendance.student_id == student_id,
            Attendance.lecture_id == lecture.id,
        )
        .first()
    )
    if existing is not None:
        return "ALREADY_MARKED"

    attendance = Attendance(
        student_id=student_id,
        lecture_id=lecture.id,
        status="Present",
        marked_at=now_local(),
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance
