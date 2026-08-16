from datetime import date
from sqlalchemy.orm import Session
from app.models.lecture import Lecture
from app.models.lecture_schedule import LectureSchedule
from app.models.class_section import ClassSection
from app.schemas.lecture_schedule import LectureScheduleCreate
from app.services.college_closure_service import is_college_closed


def _resolve_class(db: Session, college_id: int, data):
    if data.class_section_id is not None:
        item = db.query(ClassSection).filter(ClassSection.id == data.class_section_id, ClassSection.college_id == college_id).first()
    else:
        item = db.query(ClassSection).filter(ClassSection.college_id == college_id, ClassSection.department == data.department, ClassSection.class_name == data.class_name, ClassSection.section == data.section).first()
    if item is None: raise ValueError("Class section does not exist. Create it first.")
    return item


def create_schedule(db: Session, college_id: int, data: LectureScheduleCreate):
    class_section = _resolve_class(db, college_id, data)
    existing = db.query(LectureSchedule).filter(LectureSchedule.college_id == college_id, LectureSchedule.day_of_week == data.day_of_week, LectureSchedule.subject == data.subject, LectureSchedule.start_time == data.start_time, LectureSchedule.class_section_id == class_section.id).first()
    if existing: return None
    schedule = LectureSchedule(college_id=college_id, class_section_id=class_section.id, subject=data.subject, department=class_section.department, class_name=class_section.class_name, section=class_section.section, day_of_week=data.day_of_week, start_time=data.start_time, end_time=data.end_time)
    db.add(schedule); db.commit(); db.refresh(schedule)
    return schedule


def get_schedules(db: Session, college_id: int):
    return db.query(LectureSchedule).filter(LectureSchedule.college_id == college_id).order_by(LectureSchedule.day_of_week, LectureSchedule.start_time).all()


def delete_schedule(db: Session, schedule: LectureSchedule):
    db.delete(schedule); db.commit()


def sync_lectures_for_date(db: Session, college_id: int, lecture_date: date):
    if is_college_closed(db, college_id, lecture_date): return []
    schedules = db.query(LectureSchedule).filter(LectureSchedule.college_id == college_id, LectureSchedule.day_of_week == lecture_date.weekday()).all()
    created = []
    for schedule in schedules:
        existing = db.query(Lecture).filter(Lecture.college_id == college_id, Lecture.lecture_date == lecture_date, Lecture.subject == schedule.subject, Lecture.start_time == schedule.start_time, Lecture.class_section_id == schedule.class_section_id).first()
        if existing: continue
        lecture = Lecture(college_id=college_id, class_section_id=schedule.class_section_id, subject=schedule.subject, department=schedule.department, class_name=schedule.class_name, section=schedule.section, lecture_date=lecture_date, start_time=schedule.start_time, end_time=schedule.end_time, status="Scheduled")
        db.add(lecture); created.append(lecture)
    if created:
        db.commit()
        for lecture in created: db.refresh(lecture)
    return created
