from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
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


def _approval_page(title: str, message: str, success: bool) -> HTMLResponse:
    status_color = "#166534" if success else "#b91c1c"
    status_background = "#f0fdf4" if success else "#fef2f2"
    icon = "✓" if success else "!"
    html = f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} - FaceTrack</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            padding: 24px;
            background: #f8fafc;
            color: #0f172a;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}
        .card {{
            width: min(520px, 100%);
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 20px;
            padding: 40px 32px;
            text-align: center;
            box-shadow: 0 20px 50px rgba(15, 23, 42, .08);
        }}
        .icon {{
            width: 64px;
            height: 64px;
            margin: 0 auto 22px;
            display: grid;
            place-items: center;
            border-radius: 50%;
            background: {status_background};
            color: {status_color};
            font-size: 32px;
            font-weight: 800;
        }}
        h1 {{ margin: 0 0 12px; font-size: 28px; letter-spacing: -.02em; }}
        p {{ margin: 0; color: #475569; line-height: 1.7; font-size: 16px; }}
        .brand {{ margin-top: 28px; color: #64748b; font-size: 13px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; }}
    </style>
</head>
<body>
    <main class="card">
        <div class="icon">{icon}</div>
        <h1>{title}</h1>
        <p>{message}</p>
        <div class="brand">FaceTrack</div>
    </main>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200 if success else 400)


@router.get("/approve-college", response_class=HTMLResponse)
def approve_college(token: str, db: Session = Depends(get_db)):
    admin = verify_college_registration(db, token)
    if admin is None:
        return _approval_page(
            "Approval link is invalid",
            "This college approval link is invalid, expired, or has already been used.",
            False,
        )

    return _approval_page(
        "College approved successfully",
        "The college account has been created successfully. A confirmation email has been sent to the registered college email address.",
        True,
    )


@router.post("/verify-college-email", response_model=AdminResponse, status_code=201)
def verify_college_email(token: str, db: Session = Depends(get_db)):
    admin = verify_college_registration(db, token)
    if admin is None:
        raise HTTPException(status_code=400, detail="This approval link is invalid, expired, or has already been used.")
    return admin


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
