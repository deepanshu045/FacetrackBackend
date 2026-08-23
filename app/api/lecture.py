from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.dependencies.auth import get_current_admin
from app.models.admin import Admin
from app.models.lecture import Lecture
from app.schemas.lecture import LectureCreate, LectureUpdate, LectureResponse
from app.services.lecture_service import create_lecture, get_lectures, get_lecture, update_lecture, delete_lecture
from app.services.lecture_schedule_service import sync_lectures_for_range

router = APIRouter(prefix="/lectures", tags=["Lectures"])


@router.post("", response_model=LectureResponse, status_code=status.HTTP_201_CREATED)
def create(data: LectureCreate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    try:
        lecture = create_lecture(db, admin.college_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if lecture is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A lecture with the same subject, date, class section and start time already exists.",
        )
    return lecture


@router.get("", response_model=list[LectureResponse])
def list_all(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    today = date.today()
    start = start_date or today
    end = end_date or (today + timedelta(days=30))
    if end < start:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date.")
    if (end - start).days > 366:
        raise HTTPException(status_code=400, detail="Lecture generation range cannot exceed 366 days.")

    sync_lectures_for_range(db, admin.college_id, start, end)
    return get_lectures(db, admin.college_id, start_date=start, end_date=end)


@router.get("/{lecture_id}", response_model=LectureResponse)
def get_one(lecture_id: int, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lecture = get_lecture(db, lecture_id, admin.college_id)
    if lecture is None:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    return lecture


@router.put("/{lecture_id}", response_model=LectureResponse)
def update(lecture_id: int, data: LectureUpdate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lecture = get_lecture(db, lecture_id, admin.college_id)
    if lecture is None:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    try:
        return update_lecture(db, lecture, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{lecture_id}/cancel", response_model=LectureResponse)
def cancel(lecture_id: int, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lecture = get_lecture(db, lecture_id, admin.college_id)
    if lecture is None:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    if lecture.status == "Cancelled":
        return lecture
    lecture.status = "Cancelled"
    db.commit()
    db.refresh(lecture)
    return lecture


@router.delete("/{lecture_id}")
def delete(lecture_id: int, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lecture = get_lecture(db, lecture_id, admin.college_id)
    if lecture is None:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    delete_lecture(db, lecture)
    return {"message": "Lecture deleted successfully."}
