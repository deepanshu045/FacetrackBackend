"""Seed a reusable, idempotent demo dataset for local FaceTrack testing.

Run from the repository root:
    python -m scripts.seed_demo

The script creates/updates one demo college and its demo users, classes,
students, teacher assignments, weekly schedules, demo lectures, and attendance.
Demo lectures are rebuilt on every run so their timing windows are relative to
the time at which the seed is executed.
"""

from __future__ import annotations

from datetime import time, timedelta

from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.models.admin import Admin
from app.models.attendance import Attendance
from app.models.class_section import ClassSection
from app.models.college import College
from app.models.lecture import Lecture
from app.models.lecture_schedule import LectureSchedule
from app.models.student import Student
from app.models.teacher import Teacher, TeacherAssignment
from app.security.password import hash_password
from app.utils.timezone import now_local


COLLEGE_NAME = "Jnan Vikas Mandal"
COLLEGE_SLUG = "jnan-vikas-mandal-demo"
DEMO_PASSWORD = "Demo@123"

ADMIN_USERNAME = "demo_admin"
TEACHER_DEFINITIONS = (
    ("demo_teacher1", "Demo Teacher 1", "teacher1@demo.jvm.edu"),
    ("demo_teacher2", "Demo Teacher 2", "teacher2@demo.jvm.edu"),
    ("demo_teacher3", "Demo Teacher 3", "teacher3@demo.jvm.edu"),
)

CLASS_DEFINITIONS = (
    ("BCA", "1", "A"),
    ("BCA", "1", "B"),
    ("BCA", "2", "A"),
)

LECTURE_SUBJECTS = {
    "completed": "Demo - Completed Lecture",
    "active": "Demo - Active Lecture",
    "upcoming": "Demo - Upcoming Lecture",
    "cancelled": "Demo - Cancelled Lecture",
}

# Python weekday: Monday=0 ... Sunday=6.
# These are the recurring demo classes visible in the weekly timetable.
WEEKLY_SCHEDULE_DEFINITIONS = (
    # teacher index, class index, subject, weekday, start, end
    (0, 0, "Data Structures", 0, time(9, 0), time(10, 0)),
    (1, 0, "Database Management", 0, time(11, 0), time(12, 0)),
    (2, 0, "Python Programming", 1, time(9, 0), time(10, 0)),
    (0, 1, "Computer Networks", 1, time(11, 0), time(12, 0)),
    (1, 1, "Web Development", 2, time(9, 0), time(10, 0)),
    (2, 1, "Operating Systems", 2, time(11, 0), time(12, 0)),
    (0, 2, "Software Engineering", 3, time(9, 0), time(10, 0)),
    (1, 2, "Computer Architecture", 4, time(11, 0), time(12, 0)),
    (2, 2, "Mathematics", 4, time(14, 0), time(15, 0)),
    (0, 0, "Python Lab", 5, time(10, 0), time(12, 0)),
)


def get_or_create_college(db: Session) -> College:
    college = db.query(College).filter(College.slug == COLLEGE_SLUG).first()
    if college is None:
        college = College(name=COLLEGE_NAME, slug=COLLEGE_SLUG, is_active=True)
        db.add(college)
        db.flush()
    else:
        college.name = COLLEGE_NAME
        college.is_active = True
    return college


def get_or_create_admin(db: Session, college: College) -> Admin:
    admin = db.query(Admin).filter(
        Admin.college_id == college.id,
        Admin.username == ADMIN_USERNAME,
    ).first()
    if admin is None:
        admin = Admin(
            college_id=college.id,
            username=ADMIN_USERNAME,
            name="Demo Administrator",
            email="demo_admin@demo.jvm.edu",
            password_hash=hash_password(DEMO_PASSWORD),
        )
        db.add(admin)
    else:
        admin.name = "Demo Administrator"
        admin.email = "demo_admin@demo.jvm.edu"
        admin.password_hash = hash_password(DEMO_PASSWORD)
    return admin


def get_or_create_teachers(db: Session, college: College) -> list[Teacher]:
    teachers: list[Teacher] = []
    for username, name, email in TEACHER_DEFINITIONS:
        teacher = db.query(Teacher).filter(
            Teacher.college_id == college.id,
            Teacher.username == username,
        ).first()
        if teacher is None:
            teacher = Teacher(
                college_id=college.id,
                username=username,
                name=name,
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                is_active=True,
            )
            db.add(teacher)
        else:
            teacher.name = name
            teacher.email = email
            teacher.password_hash = hash_password(DEMO_PASSWORD)
            teacher.is_active = True
        teachers.append(teacher)
    db.flush()
    return teachers


def get_or_create_classes(db: Session, college: College) -> list[ClassSection]:
    classes: list[ClassSection] = []
    for department, class_name, section in CLASS_DEFINITIONS:
        class_section = db.query(ClassSection).filter(
            ClassSection.college_id == college.id,
            ClassSection.department == department,
            ClassSection.class_name == class_name,
            ClassSection.section == section,
        ).first()
        if class_section is None:
            class_section = ClassSection(
                college_id=college.id,
                department=department,
                class_name=class_name,
                section=section,
            )
            db.add(class_section)
        classes.append(class_section)
    db.flush()
    return classes


def upsert_assignments(db: Session, teachers: list[Teacher], classes: list[ClassSection]) -> None:
    for teacher, class_section in zip(teachers, classes):
        assignment = db.query(TeacherAssignment).filter(
            TeacherAssignment.teacher_id == teacher.id,
            TeacherAssignment.class_section_id == class_section.id,
        ).first()
        if assignment is None:
            db.add(TeacherAssignment(
                teacher_id=teacher.id,
                class_section_id=class_section.id,
            ))
    db.flush()


def upsert_weekly_schedules(
    db: Session,
    college: College,
    teachers: list[Teacher],
    classes: list[ClassSection],
) -> list[LectureSchedule]:
    schedules: list[LectureSchedule] = []
    for teacher_index, class_index, subject, weekday, start_time, end_time in WEEKLY_SCHEDULE_DEFINITIONS:
        teacher = teachers[teacher_index]
        class_section = classes[class_index]
        schedule = db.query(LectureSchedule).filter(
            LectureSchedule.college_id == college.id,
            LectureSchedule.class_section_id == class_section.id,
            LectureSchedule.day_of_week == weekday,
            LectureSchedule.subject == subject,
            LectureSchedule.start_time == start_time,
        ).first()
        if schedule is None:
            schedule = LectureSchedule(
                college_id=college.id,
                class_section_id=class_section.id,
                teacher_id=teacher.id,
                subject=subject,
                department=class_section.department,
                class_name=class_section.class_name,
                section=class_section.section,
                day_of_week=weekday,
                start_time=start_time,
                end_time=end_time,
            )
            db.add(schedule)
        else:
            schedule.teacher_id = teacher.id
            schedule.end_time = end_time
            schedule.department = class_section.department
            schedule.class_name = class_section.class_name
            schedule.section = class_section.section
            schedule.effective_start_date = None
            schedule.effective_end_date = None
        schedules.append(schedule)
    db.flush()
    return schedules


def upsert_students(db: Session, college: College, classes: list[ClassSection]) -> list[Student]:
    students: list[Student] = []
    names = (
        "Aarav Sharma", "Aditi Patil", "Arjun Mehta", "Bhavna Joshi", "Chetan Shah",
        "Diya Kulkarni", "Eshan Deshmukh", "Fatima Khan", "Gaurav More", "Harsh Verma",
        "Isha Nair", "Jai Singh", "Kavya Pawar", "Lakshya Jain", "Manav Gupta",
        "Nisha Yadav", "Omkar Jadhav", "Pranav Rao", "Riya Mishra", "Rohan Thakur",
        "Sakshi Kale", "Tanmay Sane", "Uday Shinde", "Vaishnavi Gawde", "Vedant Joshi",
        "Yash Tiwari", "Zoya Sheikh", "Aditya Bhosale", "Neha Salunkhe", "Rahul Chavan",
    )
    for index, name in enumerate(names, start=1):
        class_section = classes[(index - 1) // 10]
        roll_no = f"DEMO{index:03d}"
        email = f"student{index:02d}@demo.jvm.edu"
        student = db.query(Student).filter(
            Student.college_id == college.id,
            Student.roll_no == roll_no,
        ).first()
        if student is None:
            student = Student(
                college_id=college.id,
                class_section_id=class_section.id,
                roll_no=roll_no,
                name=name,
                email=email,
                phone_no=f"900000{index:04d}",
                department=class_section.department,
                class_name=class_section.class_name,
                section=class_section.section,
            )
            db.add(student)
        else:
            student.class_section_id = class_section.id
            student.name = name
            student.email = email
            student.phone_no = f"900000{index:04d}"
            student.department = class_section.department
            student.class_name = class_section.class_name
            student.section = class_section.section
        students.append(student)
    db.flush()
    return students


def rebuild_demo_lectures(
    db: Session,
    college: College,
    teachers: list[Teacher],
    classes: list[ClassSection],
) -> dict[str, Lecture]:
    old_lectures = db.query(Lecture).filter(
        Lecture.college_id == college.id,
        Lecture.subject.in_(list(LECTURE_SUBJECTS.values())),
    ).all()
    for lecture in old_lectures:
        db.query(Attendance).filter(
            Attendance.lecture_id == lecture.id
        ).delete(synchronize_session=False)
        db.delete(lecture)
    db.flush()

    now = now_local()
    yesterday = now.date() - timedelta(days=1)
    tomorrow = now.date() + timedelta(days=1)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    active_start = max(now - timedelta(minutes=15), day_start)
    active_end = min(now + timedelta(minutes=30), day_end)

    definitions = (
        ("completed", teachers[0], classes[0], yesterday, time(10, 0), time(11, 0), "Completed"),
        ("active", teachers[0], classes[0], now.date(), active_start.time(), active_end.time(), "Scheduled"),
        ("upcoming", teachers[1], classes[1], tomorrow, time(9, 0), time(10, 0), "Scheduled"),
        ("cancelled", teachers[2], classes[2], tomorrow, time(11, 0), time(12, 0), "Cancelled"),
    )

    lectures: dict[str, Lecture] = {}
    for key, teacher, class_section, lecture_date, start_time, end_time, status in definitions:
        lecture = Lecture(
            college_id=college.id,
            class_section_id=class_section.id,
            teacher_id=teacher.id,
            subject=LECTURE_SUBJECTS[key],
            department=class_section.department,
            class_name=class_section.class_name,
            section=class_section.section,
            lecture_date=lecture_date,
            start_time=start_time,
            end_time=end_time,
            status=status,
        )
        db.add(lecture)
        lectures[key] = lecture
    db.flush()
    return lectures


def seed_attendance(db: Session, students: list[Student], lectures: dict[str, Lecture]) -> int:
    created = 0
    completed = lectures["completed"]
    for index, student in enumerate(students, start=1):
        db.add(Attendance(
            student_id=student.id,
            lecture_id=completed.id,
            status="Present" if index % 3 != 0 else "Absent",
            marked_at=now_local() - timedelta(days=1),
        ))
        created += 1

    active = lectures["active"]
    for index, student in enumerate(students[:10], start=1):
        db.add(Attendance(
            student_id=student.id,
            lecture_id=active.id,
            status="Present" if index % 2 else "Absent",
            marked_at=now_local(),
        ))
        created += 1
    db.flush()
    return created


def seed_demo() -> None:
    db = SessionLocal()
    try:
        college = get_or_create_college(db)
        admin = get_or_create_admin(db, college)
        teachers = get_or_create_teachers(db, college)
        classes = get_or_create_classes(db, college)
        db.flush()
        upsert_assignments(db, teachers, classes)
        schedules = upsert_weekly_schedules(db, college, teachers, classes)
        students = upsert_students(db, college, classes)
        lectures = rebuild_demo_lectures(db, college, teachers, classes)
        attendance_count = seed_attendance(db, students, lectures)
        db.commit()

        print("Demo seed complete.")
        print(f"College : {college.name} ({college.slug})")
        print(f"Admin   : {admin.username} / {DEMO_PASSWORD}")
        print("Teachers:")
        for teacher in teachers:
            print(f"  - {teacher.username} / {DEMO_PASSWORD}")
        print(f"Classes : {len(classes)}")
        print(f"Students: {len(students)}")
        print(f"Weekly schedules: {len(schedules)}")
        print(f"Demo lectures: {len(lectures)}")
        print(f"Attendance rows: {attendance_count}")
        print("\nTiming checks:")
        print("  - active    : now is inside the lecture window")
        print("  - completed : lecture has already ended")
        print("  - upcoming  : lecture has not started")
        print("  - cancelled : attendance is blocked by status")
        print("  - weekly schedule: recurring Monday-Saturday timetable is populated")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()
