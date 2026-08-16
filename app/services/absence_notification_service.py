from datetime import date

from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.lecture import Lecture
from app.models.attendance import Attendance
from app.models.attendance_summary_notification import AttendanceSummaryNotification
from app.services.email_service import send_email, EmailDeliveryError
from app.services.lecture_schedule_service import sync_lectures_for_date


def send_attendance_summary_notifications(db: Session, attendance_date: date):
    lectures = db.query(Lecture).filter(Lecture.lecture_date == attendance_date).order_by(Lecture.start_time.asc()).all()
    if not lectures:
        return

    college_ids = {lecture.college_id for lecture in lectures}
    for college_id in college_ids:
        sync_lectures_for_date(db, college_id, attendance_date)

    lectures = db.query(Lecture).filter(Lecture.lecture_date == attendance_date).order_by(Lecture.start_time.asc()).all()
    students = db.query(Student).filter(Student.college_id.in_([l.college_id for l in lectures]), Student.email.isnot(None)).all()

    for student in students:
        student_lectures = [l for l in lectures if l.college_id == student.college_id]
        if not student_lectures:
            continue

        already_sent = db.query(AttendanceSummaryNotification).filter(
            AttendanceSummaryNotification.student_id == student.id,
            AttendanceSummaryNotification.summary_date == attendance_date,
        ).first()
        if already_sent:
            continue

        report_rows = []
        present_count = 0
        absent_count = 0
        counted_lectures = 0

        for lecture in student_lectures:
            attendance = db.query(Attendance).filter(
                Attendance.student_id == student.id,
                Attendance.lecture_id == lecture.id,
            ).first()

            if lecture.status == "Cancelled":
                status = "Cancelled"
            elif attendance:
                status = "Present"
                present_count += 1
                counted_lectures += 1
            else:
                status = "Absent"
                absent_count += 1
                counted_lectures += 1

            report_rows.append({
                "subject": lecture.subject,
                "start_time": lecture.start_time.strftime("%I:%M %p"),
                "end_time": lecture.end_time.strftime("%I:%M %p"),
                "status": status,
            })

        if counted_lectures == 0:
            percentage = 0
        else:
            percentage = round((present_count / counted_lectures) * 100, 2)

        subject = f"FaceTrack - Daily Attendance Report - {attendance_date.strftime('%d %B %Y')}"
        text = build_attendance_email(
            student, attendance_date, report_rows,
            present_count, absent_count, counted_lectures, percentage,
        )

        try:
            send_email(recipient=student.email, subject=subject, text=text)
        except EmailDeliveryError:
            continue

        db.add(AttendanceSummaryNotification(student_id=student.id, summary_date=attendance_date))
        db.commit()


def build_attendance_email(student, attendance_date, report_rows, present_count, absent_count, total_lectures, percentage):
    lines = [
        "FACETRACK", "=" * 60, "", "Daily Attendance Report", "=" * 60, "",
        f"Student : {student.name}", f"Roll No : {student.roll_no}",
        f"Date    : {attendance_date.strftime('%d %B %Y')}", "", "-" * 70,
        f"{'Subject':<25}{'Time':<27}Status", "-" * 70,
    ]
    for row in report_rows:
        time = f"{row['start_time']} - {row['end_time']}"
        lines.append(f"{row['subject']:<25}{time:<27}{row['status']}")
    lines += [
        "-" * 70, "", "Today's Summary", "-" * 30,
        f"Total Lectures : {total_lectures}",
        f"Present        : {present_count}",
        f"Absent         : {absent_count}",
        f"Attendance     : {percentage}%", "", "=" * 60, "",
        "This is an automatically generated email from FaceTrack.",
    ]
    return "\n".join(lines)
