from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.models.admin import Admin
from app.models.college import College
from app.security.jwt import verify_token

security = HTTPBearer()


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Return the authenticated admin and enforce tenant/college isolation.

    The college_id comes only from the signed JWT and the database record.
    Client-supplied college IDs must never be trusted for authorization.
    """
    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    admin_id = payload.get("admin_id")
    token_college_id = payload.get("college_id")

    if admin_id is None or token_college_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    # Verify BOTH the admin and its college from the database. This prevents
    # an admin from using a token after being moved/deleted and prevents access
    # to another college's tenant data.
    admin = (
        db.query(Admin)
        .join(College, Admin.college_id == College.id)
        .filter(
            Admin.id == admin_id,
            Admin.college_id == token_college_id,
            College.is_active.is_(True),
        )
        .first()
    )

    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found or college is inactive"
        )

    return admin
