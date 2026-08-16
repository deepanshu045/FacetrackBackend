from datetime import date

from sqlalchemy.orm import Session

from app.models.class_section import ClassSection
from app.models.lecture import Lecture
from app.models.lecture_schedule import LectureSchedule
from app.schemas.lecture_schedule import LectureScheduleCreate
from app.services.college_closure_service import is_college_closed


def _resolve_class_section(
    db: Session,
    college_id: int,
    schedule_data: LectureScheduleCreate,
) -> ClassSection:
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


def create_schedule(
    db: Session,
    college_id: int,
    schedule_data: LectureScheduleCreate,
):
    class_section = _resolve_class_section(db, college_id, schedule_data)
    existing_schedule = (
        db.query(LectureSchedule)
        .filter(
            LectureSchedule.college_id == college_id,
            LectureSchedule.day_of_week == schedule_data.day_of_week,
            LectureSchedule.subject == schedule_data.subject,
            LectureSchedule.start_time == schedule_data.start_time,
            LectureSchedule.class_section_id == class_section.id,
        )
        .first()
    )
    if existing_schedule is not None:
        return None

    schedule = LectureSchedule(
        college_id=college_id,
        class_section_id=class_section.id,
        subject=schedule_data.subject,
        department=class_section.department,
        class_name=class_section.class_name,
        section=class_section.section,
        day_of_week=schedule_data.day_of_week,
        start_time=schedule_data.start_time,
        end_time=schedule_data.end_time,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def get_schedules(db: Session, college_id: int):
    return (
        db.query(LectureSchedule)
        .filter(LectureSchedule.college_id == college_id)
        .order_by(LectureSchedule.day_of_week, LectureSchedule.start_time)
        .all()
    )


def delete_schedule(db: Session, schedule: LectureSchedule) -> None:
    db.delete(schedule)
    db.commit()


def sync_lectures_for_date(db: Session, college_id: int, lecture_date: date):
    if is_college_closed(db, college_id, lecture_date):
        return []

    schedules = (
        db.query(LectureSchedule)
        .filter(
            LectureSchedule.college_id == college_id,
            LectureSchedule.day_of_week == lecture_date.weekday(),
        )
        .all()
    )

    created_lectures = []
    for schedule in schedules:
        existing_lecture = (
            db.query(Lecture)
            .filter(
                Lecture.college_id == college_id,
                Lecture.lecture_date == lecture_date,
                Lecture.subject == schedule.subject,
                Lecture.start_time == schedule.start_time,
                Lecture.class_section_id == schedule.class_section_id,
            )
            .first()
        )
        if existing_lecture is not None:
            continue

        lecture = Lecture(
            college_id=college_id,
            class_section_id=schedule.class_section_id,
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
