import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.admin import Admin
from app.models.college import College
from app.models.pending_college_registration import PendingCollegeRegistration
from app.schemas.auth import AdminCreate

from app.config import BACKEND_URL, COLLEGE_APPROVAL_EMAIL
from app.security.password import hash_password
from app.services.email_service import EmailDeliveryError, is_email_configured, send_email

from app.security.password import verify_password


def create_admin(
    db: Session,
    admin: AdminCreate,
    college_id: int,
):
    existing = (
        db.query(Admin)
        .filter(
            Admin.college_id == college_id,
            ((Admin.username == admin.username) |
             (Admin.email == admin.email))
        )
        .first()
    )

    if existing:
        return None

    new_admin = Admin(
        college_id=college_id,
        username=admin.username,
        name=admin.name.strip(),
        email=admin.email,
        password_hash=hash_password(admin.password)
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
    admin = create_admin(
        db,
        AdminCreate(
            username=registration.username,
            name=registration.name,
            email=registration.email,
            password=registration.password,
        ),
        college.id,
    )
    return admin


def start_college_registration(db: Session, registration) -> None:
    """Create a pending registration and send an approval link to the owner/admin."""
    if not is_email_configured():
        raise RuntimeError("Email verification is not configured on the server.")

    slug = registration.college_slug.strip().lower()
    if not slug or not slug.replace("-", "").isalnum():
        raise ValueError("College ID may contain only letters, numbers, and hyphens.")

    email = str(registration.email).strip().lower()

    if db.query(College).filter(College.slug == slug).first():
        raise ValueError("That college ID is already registered.")

    if db.query(PendingCollegeRegistration).filter(
        (PendingCollegeRegistration.college_slug == slug)
        | (PendingCollegeRegistration.email == email)
    ).first():
        raise ValueError("A verification request has already been sent for this college registration.")

    token = secrets.token_urlsafe(32)
    pending = PendingCollegeRegistration(
        college_name=registration.college_name.strip(),
        college_slug=slug,
        username=registration.username.strip(),
        name=registration.name.strip(),
        email=email,
        password_hash=hash_password(registration.password),
        verification_token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(pending)
    db.commit()

    # IMPORTANT: the applicant does not get the approval link.
    # In Resend testing mode the approval email goes to the Resend account owner.
    approval_url = f"{BACKEND_URL}/auth/approve-college?token={token}"

    try:
        send_email(
            recipient=COLLEGE_APPROVAL_EMAIL,
            subject=f"FaceTrack - College registration approval: {pending.college_name}",
            text=(
                "FACETRACK COLLEGE APPROVAL\n"
                "=" * 60 + "\n\n"
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
    """Approve a pending college registration using the one-time approval token."""
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


def authenticate_admin(
    db,
    college_slug: str,
    username: str,
    password: str
):
    admin = (
        db.query(Admin)
        .join(College)
        .filter(
            College.slug == college_slug.strip().lower(),
            College.is_active.is_(True),
            Admin.username == username,
        )
        .first()
    )

    if admin is None:
        return None

    if not verify_password(password, admin.password_hash):
        return None

    return admin


def update_admin(
    db: Session,
    admin: Admin,
    updates: dict
):
    for key, value in updates.items():
        if value is None:
            continue
        if hasattr(admin, key):
            setattr(admin, key, value)

    shared_settings = {
        key: value
        for key, value in updates.items()
        if key in {"threshold", "sound_alerts"} and value is not None
    }
    if shared_settings:
        db.query(Admin).filter(Admin.college_id == admin.college_id).update(
            shared_settings,
            synchronize_session=False,
        )

    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def change_admin_password(
    db: Session,
    admin: Admin,
    current_password: str,
    new_password: str
):
    if not verify_password(current_password, admin.password_hash):
        return None

    admin.password_hash = hash_password(new_password)
    db.add(admin)
    db.commit()
    return admin
