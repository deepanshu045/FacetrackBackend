from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.schemas.report import AttendanceReport, StudentAttendanceSummary
from app.services.report_service import (
    get_today_attendance,
    get_student_attendance,
    get_student_attendance_summary,
    get_attendance_by_date,
    get_monthly_attendance,
)

from app.dependencies.auth import get_current_admin
from app.models.admin import Admin

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
    dependencies=[Depends(get_current_admin)]
)


@router.get(
    "/today",
    response_model=list[AttendanceReport]
)
def today_report(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return get_today_attendance(db, admin.college_id)


@router.get(
    "/student/{student_id}",
    response_model=list[AttendanceReport]
)
def student_report(
    student_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return get_student_attendance(db, student_id, admin.college_id)


@router.get(
    "/student/{student_id}/summary",
    response_model=StudentAttendanceSummary,
)
def student_attendance_summary(
    student_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    summary = get_student_attendance_summary(db, student_id, admin.college_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return summary


@router.get(
    "/date/{attendance_date}",
    response_model=list[AttendanceReport]
)
def date_report(
    attendance_date: date,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return get_attendance_by_date(db, attendance_date, admin.college_id)


@router.get(
    "/monthly/{year}/{month}",
    response_model=list[AttendanceReport]
)
def monthly_report(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return get_monthly_attendance(db, year, month, admin.college_id)
