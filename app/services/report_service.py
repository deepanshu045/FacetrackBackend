from datetime import date

from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.attendance import Attendance


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


def get_today_attendance(db: Session, college_id: int):

    today = date.today()

    rows = (
        db.query(
            Attendance.student_id,
            Student.roll_no,
            Student.name,
            Student.department,
            Attendance.attendance_date,
            Attendance.attendance_time,
        )
        .join(Student)
        .filter(Attendance.attendance_date == today, Student.college_id == college_id)
        .all()
    )

    return _attendance_rows_to_dict(rows)


def get_student_attendance(db: Session, student_id: int, college_id: int):

    rows = (
        db.query(
            Attendance.student_id,
            Student.roll_no,
            Student.name,
            Student.department,
            Attendance.attendance_date,
            Attendance.attendance_time,
        )
        .join(Student)
        .filter(Attendance.student_id == student_id, Student.college_id == college_id)
        .order_by(Attendance.attendance_date.desc())
        .all()
    )

    return _attendance_rows_to_dict(rows)


def get_attendance_by_date(db: Session, attendance_date: date, college_id: int):

    rows = (
        db.query(
            Attendance.student_id,
            Student.roll_no,
            Student.name,
            Student.department,
            Attendance.attendance_date,
            Attendance.attendance_time,
        )
        .join(Student)
        .filter(Attendance.attendance_date == attendance_date, Student.college_id == college_id)
        .all()
    )

    return _attendance_rows_to_dict(rows)


def get_monthly_attendance(db: Session, year: int, month: int, college_id: int):

    rows = (
        db.query(
            Attendance.student_id,
            Student.roll_no,
            Student.name,
            Student.department,
            Attendance.attendance_date,
            Attendance.attendance_time
        )
        .join(Student)
        .filter(
            Student.college_id == college_id,
            Attendance.attendance_date >= date(year, month, 1),
            Attendance.attendance_date < (
                date(year + (month == 12), (month % 12) + 1, 1)
            )
        )
        .order_by(Attendance.attendance_date)
        .all()
    )

    return _attendance_rows_to_dict(rows)
