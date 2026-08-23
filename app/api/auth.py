from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.auth import (
    LoginRequest,
    Token,
    AdminResponse,
    AdminUpdate,
    ChangePasswordRequest,
    CollegeAccessCodeRequest,
    CollegeRegistration,
    RegistrationMessage,
)
from app.services.auth_service import (
    authenticate_user,
    update_admin,
    change_admin_password,
    start_college_registration,
    verify_college_registration,
    create_admin,
)
from app.security.jwt import create_access_token
from app.database.dependency import get_db
from app.dependencies.auth import get_current_admin
from app.models.admin import Admin
from app.models.college import College
from app.security.password import hash_password
from app.schemas.auth import AdminCreate

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register-admin", response_model=AdminResponse)
def register_admin(admin: AdminCreate, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    new_admin = create_admin(db, admin, current_admin.college_id)
    if new_admin is None:
        raise HTTPException(status_code=400, detail="Username or email already exists.")
    return new_admin


@router.get("/admins", response_model=list[AdminResponse])
def list_admins(db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    return db.query(Admin).filter(Admin.college_id == current_admin.college_id).order_by(Admin.created_at, Admin.id).all()


@router.delete("/admins/{admin_id}")
def delete_admin(admin_id: int, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    if admin_id == current_admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own administrator account.")
    target = db.query(Admin).filter(Admin.id == admin_id, Admin.college_id == current_admin.college_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Administrator not found.")
    if db.query(Admin).filter(Admin.college_id == current_admin.college_id).count() <= 1:
        raise HTTPException(status_code=400, detail="A college must keep at least one administrator.")
    db.delete(target)
    db.commit()
    return {"success": True}


@router.post("/register-college", response_model=RegistrationMessage, status_code=202)
def register_college(payload: CollegeRegistration, db: Session = Depends(get_db)):
    try:
        start_college_registration(db, payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"message": "Registration submitted. The college will be created after administrator approval."}


@router.get("/approve-college", response_model=AdminResponse, status_code=201)
def approve_college(token: str, db: Session = Depends(get_db)):
    admin = verify_college_registration(db, token)
    if admin is None:
        raise HTTPException(status_code=400, detail="This approval link is invalid, expired, or has already been used.")
    return admin


@router.post("/verify-college-email", response_model=AdminResponse, status_code=201)
def verify_college_email(token: str, db: Session = Depends(get_db)):
    return approve_college(token, db)


@router.post("/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user, role = authenticate_user(db, credentials.college_slug, credentials.username, credentials.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    claims = {
        "sub": user.username,
        "college_id": user.college_id,
        "role": role,
    }
    claims["admin_id" if role == "admin" else "teacher_id"] = user.id
    access_token = create_access_token(claims)
    return {"access_token": access_token, "token_type": "bearer", "role": role}


@router.get("/me", response_model=AdminResponse)
def get_me(admin: Admin = Depends(get_current_admin)):
    return admin


@router.put("/me", response_model=AdminResponse)
def update_me(updates: AdminUpdate, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    return update_admin(db, admin, updates.dict())


@router.post("/change-password", response_model=AdminResponse)
def change_password(payload: ChangePasswordRequest, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    updated_admin = change_admin_password(db, admin, payload.current_password, payload.new_password)
    if updated_admin is None:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    return updated_admin


@router.put("/college/access-code")
def set_college_access_code(payload: CollegeAccessCodeRequest, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    code = payload.access_code.strip()
    if len(code) < 8:
        raise HTTPException(status_code=400, detail="Access code must be at least 8 characters.")
    college = db.query(College).filter(College.id == admin.college_id).first()
    if college is None:
        raise HTTPException(status_code=404, detail="College not found")
    college.access_code_hash = hash_password(code)
    db.commit()
    return {"success": True}
