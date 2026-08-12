from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.attendance import Attendance


def mark_attendance(db: Session, student_id: int):

    today = date.today()

    existing = db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.attendance_date == today
    ).first()

    if existing:
        return "ALREADY_MARKED"

    attendance = Attendance(
        student_id=student_id,
        attendance_date=today,
        attendance_time=datetime.now().time()
    )

    db.add(attendance)
    db.commit()
    db.refresh(attendance)

    return attendance