import smtplib
from datetime import date
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.config import SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_SENDER, SMTP_USERNAME
from app.models.absence_notification import AbsenceNotification
from app.models.attendance import Attendance
from app.models.student import Student


def send_absence_notifications(db: Session, attendance_date: date) -> int:
    """Email students without attendance after the daily cutoff.

    A database record is written only after an email is sent successfully, which
    prevents duplicate emails when the server restarts.
    """
    if not all([SMTP_USERNAME, SMTP_PASSWORD, SMTP_SENDER]):
        return 0

    absent_students = (
        db.query(Student)
        .outerjoin(
            Attendance,
            (Attendance.student_id == Student.id)
            & (Attendance.attendance_date == attendance_date),
        )
        .filter(Attendance.id.is_(None), Student.email.isnot(None))
        .all()
    )

    sent_count = 0
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
        smtp.login(SMTP_USERNAME, SMTP_PASSWORD)

        for student in absent_students:
            already_sent = (
                db.query(AbsenceNotification)
                .filter(
                    AbsenceNotification.student_id == student.id,
                    AbsenceNotification.attendance_date == attendance_date,
                )
                .first()
            )
            if already_sent:
                continue

            message = EmailMessage()
            message["Subject"] = f"Absence notice - {attendance_date.isoformat()}"
            message["From"] = SMTP_SENDER
            message["To"] = student.email
            message.set_content(
                f"Hello {student.name},\n\n"
                f"Our records show that your attendance was not marked by 11:00 AM on "
                f"{attendance_date.strftime('%d %B %Y')}. You have been marked absent.\n\n"
                "If this is incorrect, please contact your administrator.\n\n"
                "FaceTrack Attendance System"
            )

            try:
                smtp.send_message(message)
            except smtplib.SMTPException:
                continue

            db.add(
                AbsenceNotification(
                    student_id=student.id,
                    attendance_date=attendance_date,
                )
            )
            db.commit()
            sent_count += 1

    return sent_count
