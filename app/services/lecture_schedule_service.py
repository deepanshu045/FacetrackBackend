from datetime import date

from sqlalchemy.orm import Session

from app.models.lecture import Lecture
from app.models.lecture_schedule import LectureSchedule
from app.schemas.lecture_schedule import LectureScheduleCreate


def create_schedule(db: Session, college_id: int, data: LectureScheduleCreate):
    existing = (
        db.query(LectureSchedule)
        .filter(
            LectureSchedule.college_id == college_id,
            LectureSchedule.day_of_week == data.day_of_week,
            LectureSchedule.subject == data.subject,
            LectureSchedule.start_time == data.start_time,
        )
        .first()
    )
    if existing:
        return None

    schedule = LectureSchedule(
        college_id=college_id,
        subject=data.subject,
        day_of_week=data.day_of_week,
        start_time=data.start_time,
        end_time=data.end_time,
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


def delete_schedule(db: Session, schedule: LectureSchedule):
    db.delete(schedule)
    db.commit()


def sync_lectures_for_date(db: Session, college_id: int, lecture_date: date):
    """Create actual lecture occurrences from the weekly timetable.

    Existing lecture rows are never changed, so cancelled occurrences stay cancelled.
    """
    schedules = (
        db.query(LectureSchedule)
        .filter(
            LectureSchedule.college_id == college_id,
            LectureSchedule.day_of_week == lecture_date.weekday(),
        )
        .all()
    )

    created = []
    for schedule in schedules:
        existing = (
            db.query(Lecture)
            .filter(
                Lecture.college_id == college_id,
                Lecture.lecture_date == lecture_date,
                Lecture.subject == schedule.subject,
                Lecture.start_time == schedule.start_time,
            )
            .first()
        )
        if existing:
            continue

        lecture = Lecture(
            college_id=college_id,
            subject=schedule.subject,
            lecture_date=lecture_date,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            status="Scheduled",
        )
        db.add(lecture)
        created.append(lecture)

    if created:
        db.commit()
        for lecture in created:
            db.refresh(lecture)

    return created
