from datetime import date

from sqlalchemy.orm import Session

from app.models.college_closure import CollegeClosure
from app.models.lecture import Lecture


def create_closure(db: Session, college_id: int, closure_date: date, reason: str, description: str | None):
    existing = (
        db.query(CollegeClosure)
        .filter(
            CollegeClosure.college_id == college_id,
            CollegeClosure.closure_date == closure_date,
        )
        .first()
    )
    if existing:
        return None

    closure = CollegeClosure(
        college_id=college_id,
        closure_date=closure_date,
        reason=reason,
        description=description,
    )
    db.add(closure)
    db.commit()
    db.refresh(closure)
    return closure


def is_college_closed(db: Session, college_id: int, closure_date: date) -> bool:
    return (
        db.query(CollegeClosure.id)
        .filter(
            CollegeClosure.college_id == college_id,
            CollegeClosure.closure_date == closure_date,
        )
        .first()
        is not None
    )


def get_closures(db: Session, college_id: int):
    return (
        db.query(CollegeClosure)
        .filter(CollegeClosure.college_id == college_id)
        .order_by(CollegeClosure.closure_date.desc())
        .all()
    )


def delete_closure(db: Session, closure: CollegeClosure):
    db.delete(closure)
    db.commit()


def remove_future_lecture_occurrences(db: Session, college_id: int, closure_date: date):
    """Remove only un-attended scheduled occurrences for a newly closed date.

    Existing attendance and cancelled lectures are preserved. If a lecture already
    has attendance, it is left intact rather than silently deleting attendance data.
    """
    lectures = (
        db.query(Lecture)
        .filter(
            Lecture.college_id == college_id,
            Lecture.lecture_date == closure_date,
            Lecture.status == "Scheduled",
        )
        .all()
    )
    removed = 0
    for lecture in lectures:
        if lecture.attendance:
            lecture.status = "Cancelled"
        else:
            db.delete(lecture)
        removed += 1
    if removed:
        db.commit()
    return removed
