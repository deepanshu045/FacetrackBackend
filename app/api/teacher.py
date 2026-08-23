from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.dependency import get_db
from app.dependencies.auth import get_current_admin
from app.dependencies.teacher_auth import get_current_teacher
from app.models.admin import Admin
from app.models.college import College
from app.models.class_section import ClassSection
from app.models.teacher import Teacher, TeacherAssignment
from app.models.lecture import Lecture
from app.models.student import Student
from app.models.attendance import Attendance
from app.schemas.teacher import TeacherCreate, TeacherResponse, TeacherLogin, TeacherAssignmentCreate, TeacherAssignmentResponse
from app.security.password import hash_password, verify_password
from app.security.jwt import create_access_token
from app.services.attendance_service import set_attendance_status
from app.services.auth_service import authenticate_user

router = APIRouter(prefix="/teachers", tags=["Teachers"])


def teacher_can_access_lecture(db: Session, teacher: Teacher, lecture_id: int):
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.college_id == teacher.college_id).first()
    if lecture is None: raise HTTPException(404, "Lecture not found.")
    assigned = db.query(TeacherAssignment).filter(TeacherAssignment.teacher_id == teacher.id, TeacherAssignment.class_section_id == lecture.class_section_id).first()
    if lecture.teacher_id != teacher.id and assigned is None: raise HTTPException(403, "You are not assigned to this lecture or class.")
    if lecture.status == "Cancelled": raise HTTPException(400, "This lecture has been cancelled. Attendance cannot be marked.")
    return lecture


@router.post("", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED)
def create_teacher(data: TeacherCreate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    if len(data.password) < 8: raise HTTPException(400, "Password must be at least 8 characters.")
    username = data.username.strip()
    if db.query(Teacher).filter(Teacher.college_id == admin.college_id, Teacher.username == username).first(): raise HTTPException(409, "Teacher username already exists in this college.")
    if db.query(Admin).filter(Admin.college_id == admin.college_id, Admin.username == username).first(): raise HTTPException(409, "That username is already used by an administrator in this college.")
    if data.email and db.query(Teacher).filter(Teacher.college_id == admin.college_id, Teacher.email == str(data.email)).first(): raise HTTPException(409, "Teacher email already exists in this college.")
    teacher = Teacher(college_id=admin.college_id, username=username, name=data.name.strip(), email=str(data.email) if data.email else None, password_hash=hash_password(data.password))
    db.add(teacher); db.commit(); db.refresh(teacher); return teacher


@router.get("", response_model=list[TeacherResponse])
def list_teachers(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    return db.query(Teacher).filter(Teacher.college_id == admin.college_id).order_by(Teacher.name).all()


@router.post("/login")
def login(data: TeacherLogin, db: Session = Depends(get_db)):
    # Keep this endpoint compatible with the unified /auth/login flow. The
    # frontend uses /auth/login so admins and teachers share one login screen.
    user, role = authenticate_user(db, data.college_slug, data.username, data.password)
    if user is None or role != "teacher":
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"access_token": create_access_token({"sub": user.username, "teacher_id": user.id, "college_id": user.college_id, "role": "teacher"}), "token_type": "bearer"}


@router.get("/me")
def me(teacher: Teacher = Depends(get_current_teacher)):
    return {"id": teacher.id, "college_id": teacher.college_id, "username": teacher.username, "name": teacher.name, "email": teacher.email}


@router.post("/admin/{teacher_id}/classes", response_model=TeacherAssignmentResponse, status_code=201)
def assign_class(teacher_id: int, data: TeacherAssignmentCreate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id, Teacher.college_id == admin.college_id).first()
    class_section = db.query(ClassSection).filter(ClassSection.id == data.class_section_id, ClassSection.college_id == admin.college_id).first()
    if teacher is None or class_section is None: raise HTTPException(404, "Teacher or class section not found.")
    existing = db.query(TeacherAssignment).filter(TeacherAssignment.teacher_id == teacher_id, TeacherAssignment.class_section_id == data.class_section_id).first()
    if existing: return existing
    assignment = TeacherAssignment(teacher_id=teacher_id, class_section_id=data.class_section_id)
    db.add(assignment); db.commit(); db.refresh(assignment); return assignment


@router.get("/me/classes", response_model=list[TeacherAssignmentResponse])
def my_classes(teacher: Teacher = Depends(get_current_teacher), db: Session = Depends(get_db)):
    return db.query(TeacherAssignment).filter(TeacherAssignment.teacher_id == teacher.id).all()


@router.get("/me/lectures")
def my_lectures(teacher: Teacher = Depends(get_current_teacher), db: Session = Depends(get_db)):
    class_ids = db.query(TeacherAssignment.class_section_id).filter(TeacherAssignment.teacher_id == teacher.id).subquery()
    return db.query(Lecture).filter(Lecture.college_id == teacher.college_id, (Lecture.teacher_id == teacher.id) | Lecture.class_section_id.in_(class_ids)).order_by(Lecture.lecture_date.desc(), Lecture.start_time).all()


@router.get("/me/lectures/{lecture_id}/attendance")
def lecture_attendance(lecture_id: int, teacher: Teacher = Depends(get_current_teacher), db: Session = Depends(get_db)):
    lecture = teacher_can_access_lecture(db, teacher, lecture_id)
    students = db.query(Student).filter(Student.college_id == teacher.college_id, Student.class_section_id == lecture.class_section_id).order_by(Student.roll_no, Student.id).all()
    records = {r.student_id: r for r in db.query(Attendance).filter(Attendance.lecture_id == lecture.id).all()}
    return [{"student_id": s.id, "roll_no": s.roll_no, "name": s.name, "status": records[s.id].status if s.id in records else "Absent", "attendance_id": records[s.id].id if s.id in records else None} for s in students]


@router.post("/me/lectures/{lecture_id}/attendance")
def mark_attendance(lecture_id: int, student_id: int, status_value: str, teacher: Teacher = Depends(get_current_teacher), db: Session = Depends(get_db)):
    lecture = teacher_can_access_lecture(db, teacher, lecture_id)
    student = db.query(Student).filter(Student.id == student_id, Student.college_id == teacher.college_id, Student.class_section_id == lecture.class_section_id).first()
    if student is None: raise HTTPException(400, "Student does not belong to this lecture's class.")
    normalized = status_value.strip().title()
    if normalized not in {"Present", "Absent"}: raise HTTPException(400, "Status must be Present or Absent.")
    result = set_attendance_status(db, student.id, lecture.id, normalized)
    if isinstance(result, str): raise HTTPException(400, result)
    return {"success": True, "student_id": student.id, "lecture_id": lecture.id, "status": result.status, "attendance_id": result.id}


@router.post("/me/lectures/{lecture_id}/mark-all")
def mark_all(lecture_id: int, status_value: str, teacher: Teacher = Depends(get_current_teacher), db: Session = Depends(get_db)):
    lecture = teacher_can_access_lecture(db, teacher, lecture_id)
    normalized = status_value.strip().title()
    if normalized not in {"Present", "Absent"}: raise HTTPException(400, "Status must be Present or Absent.")
    students = db.query(Student).filter(Student.college_id == teacher.college_id, Student.class_section_id == lecture.class_section_id).all()
    for student in students:
        result = set_attendance_status(db, student.id, lecture.id, normalized)
        if isinstance(result, str): raise HTTPException(400, result)
    return {"success": True, "updated": len(students), "status": normalized}
