from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.dependencies.auth import get_current_admin
from app.models.admin import Admin
from app.models.lecture_schedule import LectureSchedule
from app.schemas.lecture_schedule import LectureScheduleCreate, LectureScheduleResponse
from app.services.lecture_schedule_service import create_schedule, get_schedules, delete_schedule

router = APIRouter(prefix="/lecture-schedules", tags=["Lecture Schedules"])


@router.post("", response_model=LectureScheduleResponse, status_code=status.HTTP_201_CREATED)
def create(data: LectureScheduleCreate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    try:
        schedule = create_schedule(db, admin.college_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if schedule is None:
        raise HTTPException(status_code=400, detail="Weekly lecture schedule already exists.")
    return schedule


@router.get("", response_model=list[LectureScheduleResponse])
def list_all(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    return get_schedules(db, admin.college_id)


@router.delete("/{schedule_id}")
def delete(schedule_id: int, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    schedule = db.query(LectureSchedule).filter(
        LectureSchedule.id == schedule_id,
        LectureSchedule.college_id == admin.college_id,
    ).first()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Weekly schedule not found.")
    delete_schedule(db, schedule)
    return {"message": "Weekly lecture schedule deleted successfully."}
