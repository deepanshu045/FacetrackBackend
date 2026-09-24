from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.models.admin import Admin
from app.models.college import College
from app.models.teacher import Teacher
from app.security.jwt import verify_token

security = HTTPBearer()


def get_current_ngo_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Authenticate an Admin or Teacher for the NGO attendance APIs."""
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    role = payload.get("role")
    college_id = payload.get("college_id")
    user_id = payload.get("admin_id") if role == "admin" else payload.get("teacher_id") if role == "teacher" else None

    if not college_id or not user_id or role not in {"admin", "teacher"}:
        raise HTTPException(status_code=401, detail="Invalid NGO attendance token")

    if role == "admin":
        user = db.query(Admin).join(College, Admin.college_id == College.id).filter(
            Admin.id == user_id,
            Admin.college_id == college_id,
            College.is_active.is_(True),
        ).first()
    else:
        user = db.query(Teacher).join(College, Teacher.college_id == College.id).filter(
            Teacher.id == user_id,
            Teacher.college_id == college_id,
            Teacher.is_active.is_(True),
            College.is_active.is_(True),
        ).first()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found or college is inactive")

    return {"role": role, "user": user, "college_id": college_id}
