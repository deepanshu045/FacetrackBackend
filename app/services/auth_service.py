import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.admin import Admin
from app.models.college import College
from app.models.pending_college_registration import PendingCollegeRegistration
from app.models.teacher import Teacher
from app.schemas.auth import AdminCreate

from app.config import BACKEND_URL, COLLEGE_APPROVAL_EMAIL
from app.security.password import hash_password
from app.services.email_service import EmailDeliveryError, is_email_configured, send_email
from app.security.password import verify_password


def create_admin(db: Session, admin: AdminCreate, college_id: int):
    username = admin.username.strip()
    email = str(admin.email).strip().lower()
    existing_admin = db.query(Admin).filter((Admin.username == username) | (Admin.email == email)).first()
    if existing_admin:
        return None
    # Admins and teachers share the same login screen, so usernames must be
    # unique across both roles within a college.
    if db.query(Teacher).filter(Teacher.college_id == college_id, Teacher.username == username).first():
        return None
    new_admin = Admin(
        college_id=college_id,
        username=username,
        name=admin.name.strip(),
        email=email,
        password_hash=hash_password(admin.password),
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return new_admin


def create_college_with_admin(db: Session, registration):
    slug = registration.college_slug.strip().lower()
    if not slug or not slug.replace("-", "").isalnum():
        return None
    if db.query(College).filter(College.slug == slug).first():
        return None
    college = College(name=registration.college_name.strip(), slug=slug)
    db.add(college)
    db.flush()
    return create_admin(db, AdminCreate(
        username=registration.username,
        name=registration.name,
        email=registration.email,
        password=registration.password,
    ), college.id)


def start_college_registration(db: Session, registration) -> None:
    if not is_email_configured():
        raise RuntimeError("Email verification is not configured on the server.")
    slug = registration.college_slug.strip().lower()
    username = registration.username.strip()
    if not slug or not slug.replace("-", "").isalnum():
        raise ValueError("College ID may contain only letters, numbers, and hyphens.")
    if not username:
        raise ValueError("Username cannot be empty.")
    email = str(registration.email).strip().lower()
    if db.query(College).filter(College.slug == slug).first():
        raise ValueError("That college ID is already registered.")
    if db.query(Admin).filter(Admin.username == username).first():
        raise ValueError("That username is already in use.")
    if db.query(PendingCollegeRegistration).filter(
        (PendingCollegeRegistration.college_slug == slug)
        | (PendingCollegeRegistration.email == email)
        | (PendingCollegeRegistration.username == username)
    ).first():
        raise ValueError("A verification request has already been sent for this college registration.")
    token = secrets.token_urlsafe(32)
    pending = PendingCollegeRegistration(
        college_name=registration.college_name.strip(),
        college_slug=slug,
        username=username,
        name=registration.name.strip(),
        email=email,
        password_hash=hash_password(registration.password),
        verification_token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(pending)
    db.commit()
    approval_url = f"{BACKEND_URL}/auth/approve-college?token={token}"
    try:
        send_email(
            recipient=COLLEGE_APPROVAL_EMAIL,
            subject=f"FaceTrack - College registration approval: {pending.college_name}",
            text=(
                "FACETRACK COLLEGE APPROVAL\n\n"
                f"A new college has requested registration.\n\n"
                f"College : {pending.college_name}\n"
                f"College ID : {pending.college_slug}\n"
                f"Applicant name : {pending.name}\n"
                f"Applicant username : {pending.username}\n"
                f"Applicant email : {pending.email}\n\n"
                "Review the details above. If you approve this registration, open the link below:\n\n"
                f"{approval_url}\n\n"
                "The approval link expires in 24 hours and can be used only once.\n"
            ),
        )
    except EmailDeliveryError as error:
        db.delete(pending)
        db.commit()
        raise RuntimeError("Unable to send the college approval email. Please try again later.") from error


def verify_college_registration(db: Session, token: str):
    token_hash = hashlib.sha256(token.strip().encode()).hexdigest()
    pending = db.query(PendingCollegeRegistration).filter(
        PendingCollegeRegistration.verification_token_hash == token_hash
    ).first()
    if pending is None or pending.expires_at < datetime.utcnow():
        if pending is not None:
            db.delete(pending)
            db.commit()
        return None
    if db.query(College).filter(College.slug == pending.college_slug).first():
        return None
    if db.query(Admin).filter(Admin.username == pending.username).first():
        return None
    college = College(name=pending.college_name, slug=pending.college_slug, is_active=True)
    db.add(college)
    db.flush()
    admin = Admin(
        college_id=college.id,
        username=pending.username,
        name=pending.name,
        email=pending.email,
        password_hash=pending.password_hash,
    )
    db.add(admin)
    db.delete(pending)
    db.commit()
    db.refresh(admin)
    return admin


def authenticate_user(db: Session, college_slug: str, username: str, password: str):
    slug = college_slug.strip().lower()
    clean_username = username.strip()
    admin = (
        db.query(Admin)
        .join(College)
        .filter(
            College.slug == slug,
            College.is_active.is_(True),
            Admin.username == clean_username,
        )
        .first()
    )
    if admin is not None and verify_password(password, admin.password_hash):
        return admin, "admin"

    teacher = (
        db.query(Teacher)
        .join(College, Teacher.college_id == College.id)
        .filter(
            College.slug == slug,
            College.is_active.is_(True),
            Teacher.username == clean_username,
            Teacher.is_active.is_(True),
        )
        .first()
    )
    if teacher is not None and verify_password(password, teacher.password_hash):
        return teacher, "teacher"

    return None, None


def authenticate_admin(db, college_slug: str, username: str, password: str):
    user, role = authenticate_user(db, college_slug, username, password)
    return user if role == "admin" else None


def update_admin(db: Session, admin: Admin, updates: dict):
    for key, value in updates.items():
        if value is None:
            continue
        if hasattr(admin, key):
            setattr(admin, key, value)
    shared_settings = {key: value for key, value in updates.items() if key in {"threshold", "sound_alerts"} and value is not None}
    if shared_settings:
        db.query(Admin).filter(Admin.college_id == admin.college_id).update(shared_settings, synchronize_session=False)
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def change_admin_password(db: Session, admin: Admin, current_password: str, new_password: str):
    if not verify_password(current_password, admin.password_hash):
        return None
    admin.password_hash = hash_password(new_password)
    db.add(admin)
    db.commit()
    return admin
