from datetime import date

from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.lecture import Lecture
from app.models.attendance import Attendance
from app.models.attendance_summary_notification import (
    AttendanceSummaryNotification,
)
from app.services.email_service import send_email, EmailDeliveryError


def send_attendance_summary_notifications(
    db: Session,
    attendance_date: date,
):
    """
    Send one collective attendance summary per student
    for all lectures on the specified date.
    """

 
    #  Get all lectures for the date

    lectures = (
        db.query(Lecture)
        .filter(
            Lecture.lecture_date == attendance_date
        )
        .order_by(
            Lecture.start_time.asc()
        )
        .all()
    )

    if not lectures:
        return

    # ---------------------------------------------------------
    # 2. Get colleges having lectures today
    # ---------------------------------------------------------

    college_ids = {
        lecture.college_id
        for lecture in lectures
    }

    students = (
        db.query(Student)
        .filter(
            Student.college_id.in_(college_ids),
            Student.email.isnot(None),
        )
        .all()
    )

    # 3. Process each student
    

    for student in students:

        student_lectures = [
            lecture
            for lecture in lectures
            if lecture.college_id == student.college_id
        ]

        if not student_lectures:
            continue

        
        # 4. Check whether today's summary was already sent
        

        already_sent = (
            db.query(AttendanceSummaryNotification)
            .filter(
                AttendanceSummaryNotification.student_id == student.id,
                AttendanceSummaryNotification.summary_date
                == attendance_date,
            )
            .first()
        )

        if already_sent:
            continue

        # 5. Calculate attendance lecture by lecture

        report_rows = []

        present_count = 0
        absent_count = 0

        for lecture in student_lectures:

            attendance = (
                db.query(Attendance)
                .filter(
                    Attendance.student_id == student.id,
                    Attendance.lecture_id == lecture.id,
                )
                .first()
            )

            if attendance:
                status = "Present"
                present_count += 1
            else:
                status = "Absent"
                absent_count += 1

            report_rows.append(
                {
                    "subject": lecture.subject,
                    "start_time": lecture.start_time.strftime(
                        "%I:%M %p"
                    ),
                    "end_time": lecture.end_time.strftime(
                        "%I:%M %p"
                    ),
                    "status": status,
                }
            )

        total_lectures = len(report_rows)

        if total_lectures == 0:
            continue

        percentage = round(
            (present_count / total_lectures) * 100,
            2,
        )

        # 6. Build email
        

        subject = (
            "FaceTrack - Daily Attendance Report - "
            f"{attendance_date.strftime('%d %B %Y')}"
        )

        text = build_attendance_email(
            student=student,
            attendance_date=attendance_date,
            report_rows=report_rows,
            present_count=present_count,
            absent_count=absent_count,
            total_lectures=total_lectures,
            percentage=percentage,
        )

        # -----------------------------------------------------
        # 7. Send email through Resend
        # -----------------------------------------------------

        try:
            send_email(
                recipient=student.email,
                subject=subject,
                text=text,
            )

        except EmailDeliveryError:
            # Do NOT create the notification record.
            # The scheduler can retry later.
            continue

        # -----------------------------------------------------
        # 8. Record successful delivery
        # -----------------------------------------------------

        notification = AttendanceSummaryNotification(
            student_id=student.id,
            summary_date=attendance_date,
        )

        db.add(notification)
        db.commit()


def build_attendance_email(
    student,
    attendance_date,
    report_rows,
    present_count,
    absent_count,
    total_lectures,
    percentage,
):
    """
    Build the plain-text daily attendance email.
    """

    lines = []

    lines.append("FACETRACK")
    lines.append("=" * 60)
    lines.append("")

    lines.append("Daily Attendance Report")
    lines.append("=" * 60)
    lines.append("")

    lines.append(
        f"Student : {student.name}"
    )

    lines.append(
        f"Roll No : {student.roll_no}"
    )

    lines.append(
        f"Date    : {attendance_date.strftime('%d %B %Y')}"
    )

    lines.append("")

    lines.append("-" * 70)

    lines.append(
        f"{'Subject':<25}"
        f"{'Time':<27}"
        f"Status"
    )

    lines.append("-" * 70)

    for row in report_rows:

        time = (
            f"{row['start_time']} - "
            f"{row['end_time']}"
        )

        lines.append(
            f"{row['subject']:<25}"
            f"{time:<27}"
            f"{row['status']}"
        )

    lines.append("-" * 70)

    lines.append("")

    lines.append("Today's Summary")
    lines.append("-" * 30)

    lines.append(
        f"Total Lectures : {total_lectures}"
    )

    lines.append(
        f"Present        : {present_count}"
    )

    lines.append(
        f"Absent         : {absent_count}"
    )

    lines.append(
        f"Attendance     : {percentage}%"
    )

    lines.append("")

    lines.append("=" * 60)
    lines.append("")

    lines.append(
        "This is an automatically generated email from FaceTrack."
    )

    return "\n".join(lines)