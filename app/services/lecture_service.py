from sqlalchemy.orm import Session

from app.models.lecture import Lecture
from app.schemas.lecture import LectureCreate, LectureUpdate


def create_lecture(
    db: Session,
    college_id: int,
    data: LectureCreate
):
    existing = (
        db.query(Lecture)
        .filter(
            Lecture.college_id == college_id,
            Lecture.lecture_date == data.lecture_date,
            Lecture.subject == data.subject,
            Lecture.start_time == data.start_time
        )
        .first()
    )

    if existing:
        return None

    lecture = Lecture(
        college_id=college_id,
        subject=data.subject,
        lecture_date=data.lecture_date,
        start_time=data.start_time,
        end_time=data.end_time,
    )

    db.add(lecture)
    db.commit()
    db.refresh(lecture)

    return lecture


def get_lectures(
    db: Session,
    college_id: int
):
    return (
        db.query(Lecture)
        .filter(Lecture.college_id == college_id)
        .order_by(
            Lecture.lecture_date.desc(),
            Lecture.start_time.asc()
        )
        .all()
    )


def get_lecture(
    db: Session,
    lecture_id: int,
    college_id: int
):
    return (
        db.query(Lecture)
        .filter(
            Lecture.id == lecture_id,
            Lecture.college_id == college_id
        )
        .first()
    )


def update_lecture(
    db: Session,
    lecture: Lecture,
    data: LectureUpdate
):
    if data.subject is not None:
        lecture.subject = data.subject.strip()

    if data.lecture_date is not None:
        lecture.lecture_date = data.lecture_date

    if data.start_time is not None:
        lecture.start_time = data.start_time

    if data.end_time is not None:
        lecture.end_time = data.end_time

    if lecture.end_time <= lecture.start_time:
        raise ValueError("End time must be after start time.")

    db.commit()
    db.refresh(lecture)

    return lecture


def delete_lecture(
    db: Session,
    lecture: Lecture
):
    db.delete(lecture)
    db.commit()