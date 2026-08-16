from sqlalchemy.orm import Session

from app.models.lecture import Lecture
from app.models.class_section import ClassSection
from app.models.teacher import Teacher
from app.schemas.lecture import LectureCreate, LectureUpdate


def _validate_time_range(start_time, end_time):
    if end_time <= start_time:
        raise ValueError("End time must be after start time.")


def _resolve_class(db: Session, college_id: int, data):
    if data.class_section_id is not None:
        class_section = db.query(ClassSection).filter(ClassSection.id == data.class_section_id, ClassSection.college_id == college_id).first()
        if class_section is None:
            raise ValueError("Class section not found in this college.")
        return class_section
    if not all([data.department, data.class_name, data.section]):
        raise ValueError("Provide class_section_id or department, class_name and section.")
    class_section = db.query(ClassSection).filter(
        ClassSection.college_id == college_id,
        ClassSection.department == data.department,
        ClassSection.class_name == data.class_name,
        ClassSection.section == data.section,
    ).first()
    if class_section is None:
        raise ValueError("Class section does not exist. Create it first.")
    return class_section


def _has_overlap(db: Session, college_id: int, class_section_id: int, lecture_date, start_time, end_time, exclude_lecture_id=None):
    query = db.query(Lecture).filter(
        Lecture.college_id == college_id,
        Lecture.class_section_id == class_section_id,
        Lecture.lecture_date == lecture_date,
        Lecture.status != "Cancelled",
        Lecture.start_time < end_time,
        Lecture.end_time > start_time,
    )
    if exclude_lecture_id is not None:
        query = query.filter(Lecture.id != exclude_lecture_id)
    return query.first() is not None


def _resolve_teacher(db: Session, college_id: int, teacher_id):
    if teacher_id is None:
        return None
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id, Teacher.college_id == college_id, Teacher.is_active.is_(True)).first()
    if teacher is None:
        raise ValueError("Teacher not found in this college.")
    return teacher


def create_lecture(db: Session, college_id: int, data: LectureCreate):
    _validate_time_range(data.start_time, data.end_time)
    class_section = _resolve_class(db, college_id, data)
    teacher = _resolve_teacher(db, college_id, data.teacher_id)
    if _has_overlap(db, college_id, class_section.id, data.lecture_date, data.start_time, data.end_time):
        raise ValueError("Lecture overlaps with another scheduled lecture for the same class and section.")
    existing = db.query(Lecture).filter(
        Lecture.college_id == college_id,
        Lecture.lecture_date == data.lecture_date,
        Lecture.subject == data.subject,
        Lecture.start_time == data.start_time,
        Lecture.class_section_id == class_section.id,
    ).first()
    if existing:
        return None
    lecture = Lecture(
        college_id=college_id,
        class_section_id=class_section.id,
        teacher_id=teacher.id if teacher else None,
        subject=data.subject,
        department=class_section.department,
        class_name=class_section.class_name,
        section=class_section.section,
        lecture_date=data.lecture_date,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    db.add(lecture); db.commit(); db.refresh(lecture)
    return lecture


def get_lectures(db: Session, college_id: int):
    return db.query(Lecture).filter(Lecture.college_id == college_id).order_by(Lecture.lecture_date.desc(), Lecture.start_time.asc()).all()


def get_lecture(db: Session, lecture_id: int, college_id: int):
    return db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.college_id == college_id).first()


def update_lecture(db: Session, lecture: Lecture, data: LectureUpdate):
    class_section_id = data.class_section_id if data.class_section_id is not None else lecture.class_section_id
    if data.class_section_id is not None or any(v is not None for v in (data.department, data.class_name, data.section)):
        class_section = _resolve_class(db, lecture.college_id, data)
        class_section_id = class_section.id
    else:
        class_section = db.query(ClassSection).filter(ClassSection.id == class_section_id, ClassSection.college_id == lecture.college_id).first()
    if class_section is None:
        raise ValueError("Class section not found.")
    teacher_id = data.teacher_id if data.teacher_id is not None else lecture.teacher_id
    teacher = _resolve_teacher(db, lecture.college_id, teacher_id)
    subject = data.subject.strip() if data.subject is not None else lecture.subject
    lecture_date = data.lecture_date or lecture.lecture_date
    start_time = data.start_time or lecture.start_time
    end_time = data.end_time or lecture.end_time
    _validate_time_range(start_time, end_time)
    if _has_overlap(db, lecture.college_id, class_section_id, lecture_date, start_time, end_time, lecture.id):
        raise ValueError("Lecture overlaps with another scheduled lecture for the same class and section.")
    lecture.subject = subject
    lecture.class_section_id = class_section_id
    lecture.teacher_id = teacher.id if teacher else None
    lecture.department = class_section.department
    lecture.class_name = class_section.class_name
    lecture.section = class_section.section
    lecture.lecture_date = lecture_date
    lecture.start_time = start_time
    lecture.end_time = end_time
    db.commit(); db.refresh(lecture)
    return lecture


def delete_lecture(db: Session, lecture: Lecture):
    db.delete(lecture); db.commit()
