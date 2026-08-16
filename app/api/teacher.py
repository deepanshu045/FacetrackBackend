from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database.dependency import get_db
from app.dependencies.auth import get_current_admin
from app.dependencies.teacher_auth import get_current_teacher
from app.models.admin import Admin
from app.models.college import College
from app.models.class_section import ClassSection
from app.models.teacher import Teacher, TeacherAssignment
from app.models.lecture import Lecture
from app.schemas.teacher import (
    TeacherCreate, TeacherResponse, TeacherLogin,
    TeacherAssignmentCreate, TeacherAssignmentResponse,
)
from app.security.password import hash_password, verify_password
from app.security.jwt import create_access_token

router = APIRouter(prefix="/teachers", tags=["Teachers"])


@router.post("", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED)
def create_teacher(data: TeacherCreate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    if len(data.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")
    exists = db.query(Teacher).filter(Teacher.college_id == admin.college_id, Teacher.username == data.username.strip()).first()
    if exists:
        raise HTTPException(409, "Teacher username already exists in this college.")
    if data.email:
        email_exists = db.query(Teacher).filter(Teacher.college_id == admin.college_id, Teacher.email == str(data.email)).first()
        if email_exists:
            raise HTTPException(409, "Teacher email already exists in this college.")
    teacher = Teacher(
        college_id=admin.college_id,
        username=data.username.strip(),
        name=data.name.strip(),
        email=str(data.email) if data.email else None,
        password_hash=hash_password(data.password),
    )
    db.add(teacher); db.commit(); db.refresh(teacher)
    return teacher


@router.get("", response_model=list[TeacherResponse])
def list_teachers(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    return db.query(Teacher).filter(Teacher.college_id == admin.college_id).order_by(Teacher.name).all()


@router.post("/login")
def login(data: TeacherLogin, db: Session = Depends(get_db)):
    teacher = db.query(Teacher).join(College, Teacher.college_id == College.id).filter(
        Teacher.username == data.username,
        College.slug == data.college_slug,
        Teacher.is_active.is_(True),
        College.is_active.is_(True),
    ).first()
    if teacher is None or not verify_password(data.password, teacher.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({
        "sub": teacher.username,
        "teacher_id": teacher.id,
        "college_id": teacher.college_id,
        "role": "teacher",
    })
    return {"access_token": token, "token_type": "bearer"}


@router.post("/{teacher_id}/classes", response_model=TeacherAssignmentResponse, status_code=201)
def assign_class(teacher_id: int, data: TeacherAssignmentCreate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id, Teacher.college_id == admin.college_id).first()
    class_section = db.query(ClassSection).filter(ClassSection.id == data.class_section_id, ClassSection.college_id == admin.college_id).first()
    if teacher is None or class_section is None:
        raise HTTPException(404, "Teacher or class section not found.")
    existing = db.query(TeacherAssignment).filter(TeacherAssignment.teacher_id == teacher_id, TeacherAssignment.class_section_id == data.class_section_id).first()
    if existing:
        return existing
    assignment = TeacherAssignment(teacher_id=teacher_id, class_section_id=data.class_section_id)
    db.add(assignment); db.commit(); db.refresh(assignment)
    return assignment


@router.get("/me/classes", response_model=list[TeacherAssignmentResponse])
def my_classes(teacher: Teacher = Depends(get_current_teacher), db: Session = Depends(get_db)):
    return db.query(TeacherAssignment).filter(TeacherAssignment.teacher_id == teacher.id).all()


@router.get("/me/lectures")
def my_lectures(teacher: Teacher = Depends(get_current_teacher), db: Session = Depends(get_db)):
    class_ids = db.query(TeacherAssignment.class_section_id).filter(TeacherAssignment.teacher_id == teacher.id).subquery()
    return db.query(Lecture).filter(
        Lecture.college_id == teacher.college_id,
        (Lecture.teacher_id == teacher.id) | Lecture.class_section_id.in_(class_ids),
    ).order_by(Lecture.lecture_date.desc(), Lecture.start_time).all()
