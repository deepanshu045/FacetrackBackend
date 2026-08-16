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
            "attendance_time": (
                row[5].time()
                if row[5] is not None
                else None
            ),
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
            Lecture.lecture_date,
            Attendance.marked_at,
        )
        .join(Student, Attendance.student_id == Student.id)
        .join(Lecture, Attendance.lecture_id == Lecture.id)
        .filter(
            Lecture.lecture_date == today,
            Student.college_id == college_id,
        )
        .all()
    )

    return _attendance_rows_to_dict(rows)


def get_student_attendance(
    db: Session,
    student_id: int,
    college_id: int,
):

    rows = (
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
        .filter(
            Attendance.student_id == student_id,
            Student.college_id == college_id,
        )
        .order_by(Lecture.lecture_date.desc())
        .all()
    )

    return _attendance_rows_to_dict(rows)


def get_attendance_by_date(
    db: Session,
    attendance_date: date,
    college_id: int,
):

    rows = (
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
        .filter(
            Lecture.lecture_date == attendance_date,
            Student.college_id == college_id,
        )
        .all()
    )

    return _attendance_rows_to_dict(rows)


def get_monthly_attendance(
    db: Session,
    year: int,
    month: int,
    college_id: int,
):

    start_date = date(year, month, 1)

    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    rows = (
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
        .filter(
            Student.college_id == college_id,
            Lecture.lecture_date >= start_date,
            Lecture.lecture_date < end_date,
        )
        .order_by(Lecture.lecture_date)
        .all()
    )

    return _attendance_rows_to_dict(rows)