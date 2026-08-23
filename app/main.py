import logging
import re
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from sqlalchemy import inspect, text
from app.database.base import Base
from app.database.database import engine, SessionLocal
import app.models
from app.api.student import router as student_router
from app.api.recognition import router as recognition_router
from app.api.report import router as report_router
from app.api.auth import router as auth_router
from app.api.notification import router as notification_router
from app.api.public import router as public_router
from app.api.lecture import router as lecture_router
from app.api.lecture_schedule import router as lecture_schedule_router
from app.api.college_closure import router as college_closure_router
from app.api.attendance_management import router as attendance_management_router
from app.api.class_sections import router as class_section_router
from app.api.teacher import router as teacher_router
from fastapi.middleware.cors import CORSMiddleware
from app.models.admin import Admin
from app.models.college import College
from app.schemas.auth import AdminCreate
from app.services.auth_service import create_admin
from app.config import ABSENCE_CHECK_HOUR, CORS_ORIGINS
from app.services.absence_notification_service import send_attendance_summary_notifications

logger = logging.getLogger(__name__)


def add_column_if_missing(table, column, definition):
    inspector = inspect(engine)
    if table not in inspector.get_table_names(): return
    columns = {c["name"] for c in inspector.get_columns(table)}
    if column not in columns:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def ensure_phone_no_column(): add_column_if_missing("students", "phone_no", "VARCHAR(30) NULL")
def ensure_student_class_column(): add_column_if_missing("students", "class_section_id", "INTEGER NULL")
def ensure_lecture_columns():
    add_column_if_missing("lectures", "status", "VARCHAR(20) NOT NULL DEFAULT 'Scheduled'")
    add_column_if_missing("lectures", "class_section_id", "INTEGER NULL")
    add_column_if_missing("lectures", "teacher_id", "INTEGER NULL")
def ensure_schedule_columns():
    add_column_if_missing("lecture_schedules", "class_section_id", "INTEGER NULL")
    add_column_if_missing("lecture_schedules", "teacher_id", "INTEGER NULL")
    add_column_if_missing("lecture_schedules", "effective_start_date", "DATE NULL")
    add_column_if_missing("lecture_schedules", "effective_end_date", "DATE NULL")
def ensure_attendance_columns(): add_column_if_missing("attendance", "status", "VARCHAR(10) NOT NULL DEFAULT 'Present'")


def ensure_admin_settings_columns():
    inspector = inspect(engine)
    if "admins" not in inspector.get_table_names(): return
    columns = {c["name"] for c in inspector.get_columns("admins")}
    with engine.begin() as connection:
        defaults = {
            "notifications": "BOOLEAN NOT NULL DEFAULT 1", "email_alerts": "BOOLEAN NOT NULL DEFAULT 0", "sound_alerts": "BOOLEAN NOT NULL DEFAULT 1",
            "threshold": "INT NOT NULL DEFAULT 85", "resolution": "VARCHAR(10) NOT NULL DEFAULT '1080p'", "fps": "VARCHAR(10) NOT NULL DEFAULT '30'",
            "language": "VARCHAR(30) NOT NULL DEFAULT 'English'", "name": "VARCHAR(150) NULL",
        }
        for name, definition in defaults.items():
            if name not in columns: connection.exec_driver_sql(f"ALTER TABLE admins ADD COLUMN {name} {definition}")


def ensure_multitenancy_columns():
    inspector = inspect(engine); tables = inspector.get_table_names()
    if "admins" not in tables or "students" not in tables: return
    with engine.begin() as connection:
        admin_columns = {c["name"] for c in inspector.get_columns("admins")}; student_columns = {c["name"] for c in inspector.get_columns("students")}
        if "college_id" not in admin_columns: connection.execute(text("ALTER TABLE admins ADD COLUMN college_id INTEGER NULL"))
        if "college_id" not in student_columns: connection.execute(text("ALTER TABLE students ADD COLUMN college_id INTEGER NULL"))
        legacy_id = connection.execute(text("SELECT id FROM colleges WHERE slug = :slug"), {"slug": "legacy-college"}).scalar()
        if legacy_id is None:
            result = connection.execute(text("INSERT INTO colleges (name, slug, is_active) VALUES (:name, :slug, 1)"), {"name": "Legacy College", "slug": "legacy-college"}); legacy_id = result.lastrowid
        connection.execute(text("UPDATE admins SET college_id = :college_id WHERE college_id IS NULL"), {"college_id": legacy_id})
        connection.execute(text("UPDATE students SET college_id = :college_id WHERE college_id IS NULL"), {"college_id": legacy_id})
    if engine.dialect.name == "mysql":
        inspector = inspect(engine)
        with engine.begin() as connection:
            duplicate_usernames = connection.execute(text("""
                SELECT username FROM admins GROUP BY username HAVING COUNT(*) > 1 LIMIT 1
            """)).scalar()
            if duplicate_usernames is not None:
                raise RuntimeError(f"Duplicate admin username found: {duplicate_usernames!r}. Rename the duplicate admin accounts before starting the application.")
            for table, columns in (("admins", {"username", "email"}), ("students", {"roll_no", "email"})):
                for constraint in inspector.get_unique_constraints(table):
                    constrained = set(constraint.get("column_names") or []); name = constraint.get("name") or ""
                    if constrained in ({column} for column in columns) and re.fullmatch(r"[A-Za-z0-9_]+", name): connection.exec_driver_sql(f"ALTER TABLE {table} DROP INDEX {name}")
            existing_admin_indexes = {i["name"] for i in inspect(engine).get_indexes("admins")}
            if "uq_admin_college_username" in existing_admin_indexes: connection.exec_driver_sql("DROP INDEX uq_admin_college_username ON admins")
            for table, index_name, fields in (("admins", "uq_admin_username", "username"), ("admins", "uq_admin_college_email", "college_id, email"), ("students", "uq_student_college_roll_no", "college_id, roll_no"), ("students", "uq_student_college_email", "college_id, email")):
                if index_name not in {i["name"] for i in inspect(engine).get_indexes(table)}: connection.exec_driver_sql(f"CREATE UNIQUE INDEX {index_name} ON {table} ({fields})")


def ensure_college_access_code_column(): add_column_if_missing("colleges", "access_code_hash", "VARCHAR(255) NULL")
def ensure_pending_college_registration_columns():
    inspector = inspect(engine)
    if "pending_college_registrations" not in inspector.get_table_names(): return
    columns = {c["name"] for c in inspector.get_columns("pending_college_registrations")}
    if "name" not in columns:
        with engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE pending_college_registrations ADD COLUMN name VARCHAR(150) NULL")
            connection.exec_driver_sql("UPDATE pending_college_registrations SET name = username WHERE name IS NULL")
            connection.exec_driver_sql("ALTER TABLE pending_college_registrations MODIFY COLUMN name VARCHAR(150) NOT NULL")


def create_default_admin():
    with SessionLocal() as session:
        college = session.query(College).filter(College.slug == "legacy-college").first()
        if college is None:
            college = College(name="Legacy College", slug="legacy-college"); session.add(college); session.commit(); session.refresh(college)
        exists = session.query(Admin).filter(Admin.username == "admin").first()
        if exists is None: create_admin(session, AdminCreate(username="admin", name="Administrator", email="admin@example.com", password="admin123"), college.id)


def absence_email_scheduler(stop_event: threading.Event):
    last_run_date = None
    while not stop_event.is_set():
        now = datetime.now()
        if now.hour >= ABSENCE_CHECK_HOUR and now.date() != last_run_date:
            try:
                with SessionLocal() as session: send_attendance_summary_notifications(session, now.date())
                last_run_date = now.date()
            except Exception: logger.exception("Unable to send absence notification emails")
        stop_event.wait(30)


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = threading.Event(); scheduler = threading.Thread(target=absence_email_scheduler, args=(stop_event,), daemon=True, name="absence-email-scheduler"); scheduler.start(); yield; stop_event.set(); scheduler.join(timeout=2)


Base.metadata.create_all(bind=engine)
ensure_phone_no_column(); ensure_admin_settings_columns(); ensure_multitenancy_columns(); ensure_college_access_code_column(); ensure_pending_college_registration_columns(); ensure_lecture_columns(); ensure_student_class_column(); ensure_schedule_columns(); ensure_attendance_columns(); create_default_admin()

app = FastAPI(title="FaceTrack API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(student_router); app.include_router(recognition_router); app.include_router(report_router); app.include_router(auth_router); app.include_router(notification_router); app.include_router(public_router); app.include_router(lecture_router); app.include_router(lecture_schedule_router); app.include_router(college_closure_router); app.include_router(attendance_management_router); app.include_router(class_section_router); app.include_router(teacher_router)

@app.get("/")
def home(): return {"message": "Face Attendance API Running"}
