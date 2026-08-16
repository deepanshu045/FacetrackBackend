from datetime import date

from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.attendance import Attendance
from app.models.lecture import Lecture


def _attendance_rows_to_dict(rows):
    return [
        {
            "student_id": row[0],
            "roll_no": row[1],
            "name": row[2],
            "department": row[3],
            "attendance_date": row[4],
            "attendance_time": row[5],
        }
        for row in rows
    ]


def _query_rows(db: Session, college_id: int):
    return (
        db.query(
            Attendance.student_id,
            Student.roll_no,
            Student.name,
            Student.department,
            Lecture.lecture_date,
            Attendance.marked_at,
        )
        .join(Student, Attendance.student_id == Student.id)
        .join(Lecture, Attendance.lecture_id == Lecture.id)
        .filter(Student.college_id == college_id, Lecture.college_id == college_id)
    )


def _to_report_rows(rows):
    return _attendance_rows_to_dict(
        [
            (
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                row[5].time(),
            )
            for row in rows
        ]
    )


def get_today_attendance(db: Session, college_id: int):
    rows = _query_rows(db, college_id).filter(Lecture.lecture_date == date.today()).all()
    return _to_report_rows(rows)


def get_student_attendance(db: Session, student_id: int, college_id: int):
    rows = (
        _query_rows(db, college_id)
        .filter(Attendance.student_id == student_id)
        .order_by(Lecture.lecture_date.desc(), Attendance.marked_at.desc())
        .all()
    )
    return _to_report_rows(rows)


def get_attendance_by_date(db: Session, attendance_date: date, college_id: int):
    rows = (
        _query_rows(db, college_id)
        .filter(Lecture.lecture_date == attendance_date)
        .order_by(Attendance.marked_at)
        .all()
    )
    return _to_report_rows(rows)


def get_monthly_attendance(db: Session, year: int, month: int, college_id: int):
    start_date = date(year, month, 1)
    next_month = date(year + (month == 12), (month % 12) + 1, 1)
    rows = (
        _query_rows(db, college_id)
        .filter(
            Lecture.lecture_date >= start_date,
            Lecture.lecture_date < next_month,
        )
        .order_by(Lecture.lecture_date, Attendance.marked_at)
        .all()
    )
    return _to_report_rows(rows)
