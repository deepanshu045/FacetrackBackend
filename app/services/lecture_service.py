from sqlalchemy.orm import Session

from app.models.lecture import Lecture
from app.schemas.lecture import LectureCreate, LectureUpdate


def _validate_time_range(start_time, end_time):
    if end_time <= start_time:
        raise ValueError("End time must be after start time.")


def _has_overlap(db: Session, college_id: int, department: str, class_name: str, section: str, lecture_date, start_time, end_time, exclude_lecture_id: int | None = None):
    query = db.query(Lecture).filter(
        Lecture.college_id == college_id,
        Lecture.department == department,
        Lecture.class_name == class_name,
        Lecture.section == section,
        Lecture.lecture_date == lecture_date,
        Lecture.status != "Cancelled",
        Lecture.start_time < end_time,
        Lecture.end_time > start_time,
    )
    if exclude_lecture_id is not None:
        query = query.filter(Lecture.id != exclude_lecture_id)
    return query.first() is not None


def create_lecture(db: Session, college_id: int, data: LectureCreate):
    _validate_time_range(data.start_time, data.end_time)
    existing = db.query(Lecture).filter(
        Lecture.college_id == college_id,
        Lecture.lecture_date == data.lecture_date,
        Lecture.subject == data.subject,
        Lecture.start_time == data.start_time,
        Lecture.department == data.department,
        Lecture.class_name == data.class_name,
        Lecture.section == data.section,
    ).first()
    if existing:
        return None
    if _has_overlap(db, college_id, data.department, data.class_name, data.section, data.lecture_date, data.start_time, data.end_time):
        raise ValueError("Lecture overlaps with another scheduled lecture for the same class and section.")
    lecture = Lecture(
        college_id=college_id,
        subject=data.subject,
        department=data.department,
        class_name=data.class_name,
        section=data.section,
        lecture_date=data.lecture_date,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    db.add(lecture)
    db.commit()
    db.refresh(lecture)
    return lecture


def get_lectures(db: Session, college_id: int):
    return db.query(Lecture).filter(Lecture.college_id == college_id).order_by(Lecture.lecture_date.desc(), Lecture.start_time.asc()).all()


def get_lecture(db: Session, lecture_id: int, college_id: int):
    return db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.college_id == college_id).first()


def update_lecture(db: Session, lecture: Lecture, data: LectureUpdate):
    subject = data.subject.strip() if data.subject is not None else lecture.subject
    department = data.department.strip() if data.department is not None else lecture.department
    class_name = data.class_name.strip() if data.class_name is not None else lecture.class_name
    section = data.section.strip() if data.section is not None else lecture.section
    lecture_date = data.lecture_date or lecture.lecture_date
    start_time = data.start_time or lecture.start_time
    end_time = data.end_time or lecture.end_time
    if not subject or not department or not class_name or not section:
        raise ValueError("Subject, department, class and section are required.")
    _validate_time_range(start_time, end_time)
    duplicate = db.query(Lecture).filter(
        Lecture.college_id == lecture.college_id,
        Lecture.lecture_date == lecture_date,
        Lecture.subject == subject,
        Lecture.start_time == start_time,
        Lecture.department == department,
        Lecture.class_name == class_name,
        Lecture.section == section,
        Lecture.id != lecture.id,
    ).first()
    if duplicate:
        raise ValueError("Lecture already exists.")
    if _has_overlap(db, lecture.college_id, department, class_name, section, lecture_date, start_time, end_time, lecture.id):
        raise ValueError("Lecture overlaps with another scheduled lecture for the same class and section.")
    lecture.subject = subject
    lecture.department = department
    lecture.class_name = class_name
    lecture.section = section
    lecture.lecture_date = lecture_date
    lecture.start_time = start_time
    lecture.end_time = end_time
    db.commit()
    db.refresh(lecture)
    return lecture


def delete_lecture(db: Session, lecture: Lecture):
    db.delete(lecture)
    db.commit()
