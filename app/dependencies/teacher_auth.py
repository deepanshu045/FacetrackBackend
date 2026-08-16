from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.models.teacher import Teacher
from app.models.college import College
from app.security.jwt import verify_token

security = HTTPBearer()


def get_current_teacher(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    payload = verify_token(credentials.credentials)
    if not payload or payload.get("role") != "teacher":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid teacher token")

    teacher_id = payload.get("teacher_id")
    college_id = payload.get("college_id")
    teacher = db.query(Teacher).join(College, Teacher.college_id == College.id).filter(
        Teacher.id == teacher_id,
        Teacher.college_id == college_id,
        Teacher.is_active.is_(True),
        College.is_active.is_(True),
    ).first()
    if teacher is None:
        raise HTTPException(status_code=401, detail="Teacher not found or college is inactive")
    return teacher
