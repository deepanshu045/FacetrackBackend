from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.class_section import ClassSection
from app.models.lecture import Lecture
from app.models.lecture_schedule import LectureSchedule
from app.models.teacher import Teacher
from app.schemas.lecture_schedule import LectureScheduleCreate
from app.services.college_closure_service import is_college_closed


def _resolve_class_section(db: Session, college_id: int, schedule_data: LectureScheduleCreate) -> ClassSection:
    query = db.query(ClassSection).filter(ClassSection.college_id == college_id)
    if schedule_data.class_section_id is not None:
        query = query.filter(ClassSection.id == schedule_data.class_section_id)
    else:
        query = query.filter(
            ClassSection.department == schedule_data.department,
            ClassSection.class_name == schedule_data.class_name,
            ClassSection.section == schedule_data.section,
        )
    class_section = query.first()
    if class_section is None:
        raise ValueError("Class section does not exist. Create it first.")
    return class_section


def _resolve_teacher(db: Session, college_id: int, teacher_id: int | None) -> Teacher | None:
    if teacher_id is None:
        return None
    teacher = db.query(Teacher).filter(
        Teacher.id == teacher_id,
        Teacher.college_id == college_id,
        Teacher.is_active.is_(True),
    ).first()
    if teacher is None:
        raise ValueError("Teacher not found in this college.")
    return teacher


def create_schedule(db: Session, college_id: int, schedule_data: LectureScheduleCreate):
    class_section = _resolve_class_section(db, college_id, schedule_data)
    _resolve_teacher(db, college_id, schedule_data.teacher_id)
    existing_schedule = db.query(LectureSchedule).filter(
        LectureSchedule.college_id == college_id,
        LectureSchedule.day_of_week == schedule_data.day_of_week,
        LectureSchedule.subject == schedule_data.subject,
        LectureSchedule.start_time == schedule_data.start_time,
        LectureSchedule.class_section_id == class_section.id,
    ).first()
    if existing_schedule is not None:
        return None

    schedule = LectureSchedule(
        college_id=college_id,
        class_section_id=class_section.id,
        teacher_id=schedule_data.teacher_id,
        subject=schedule_data.subject,
        department=class_section.department,
        class_name=class_section.class_name,
        section=class_section.section,
        day_of_week=schedule_data.day_of_week,
        start_time=schedule_data.start_time,
        end_time=schedule_data.end_time,
        effective_start_date=schedule_data.effective_start_date,
        effective_end_date=schedule_data.effective_end_date,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def get_schedules(db: Session, college_id: int):
    return db.query(LectureSchedule).filter(
        LectureSchedule.college_id == college_id
    ).order_by(LectureSchedule.day_of_week, LectureSchedule.start_time).all()


def delete_schedule(db: Session, schedule: LectureSchedule) -> None:
    db.delete(schedule)
    db.commit()


def sync_lectures_for_date(db: Session, college_id: int, lecture_date: date):
    if is_college_closed(db, college_id, lecture_date):
        return []

    schedules = db.query(LectureSchedule).filter(
        LectureSchedule.college_id == college_id,
        LectureSchedule.day_of_week == lecture_date.weekday(),
        (LectureSchedule.effective_start_date.is_(None) | (LectureSchedule.effective_start_date <= lecture_date)),
        (LectureSchedule.effective_end_date.is_(None) | (LectureSchedule.effective_end_date >= lecture_date)),
    ).all()

    created_lectures = []
    for schedule in schedules:
        existing_lecture = db.query(Lecture).filter(
            Lecture.college_id == college_id,
            Lecture.lecture_date == lecture_date,
            Lecture.subject == schedule.subject,
            Lecture.start_time == schedule.start_time,
            Lecture.class_section_id == schedule.class_section_id,
        ).first()
        if existing_lecture is not None:
            continue

        lecture = Lecture(
            college_id=college_id,
            class_section_id=schedule.class_section_id,
            teacher_id=schedule.teacher_id,
            subject=schedule.subject,
            department=schedule.department,
            class_name=schedule.class_name,
            section=schedule.section,
            lecture_date=lecture_date,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            status="Scheduled",
        )
        db.add(lecture)
        created_lectures.append(lecture)

    if created_lectures:
        db.commit()
        for lecture in created_lectures:
            db.refresh(lecture)
    return created_lectures


def sync_lectures_for_range(db: Session, college_id: int, start_date: date, end_date: date):
    if end_date < start_date:
        return []
    created = []
    current = start_date
    while current <= end_date:
        created.extend(sync_lectures_for_date(db, college_id, current))
        current += timedelta(days=1)
    return created
