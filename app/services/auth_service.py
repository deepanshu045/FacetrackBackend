import hashlib
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.models.admin import Admin
from app.models.college import College
from app.models.pending_college_registration import PendingCollegeRegistration
from app.schemas.auth import AdminCreate

from app.config import FRONTEND_URL, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_SENDER, SMTP_USERNAME
from app.security.password import hash_password

from app.models.admin import Admin
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
        AdminCreate(username=registration.username, name=registration.name, email=registration.email,
                    password=registration.password),
        college.id,
    )
    return admin


def start_college_registration(db: Session, registration) -> None:
    """Email a verification link without creating a college or admin yet."""
    if not all([SMTP_USERNAME, SMTP_PASSWORD, SMTP_SENDER]):
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
        raise ValueError("A verification email has already been sent for this college registration.")

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

    verification_url = f"{FRONTEND_URL}/verify-college?token={token}"
    message = EmailMessage()
    message["Subject"] = "Verify your FaceTrack college registration"
    message["From"] = SMTP_SENDER
    message["To"] = email
    message.set_content(
        f"Hello {pending.username},\n\n"
        f"Verify your email to create the FaceTrack workspace for {pending.college_name}:\n"
        f"{verification_url}\n\n"
        "This link expires in 24 hours. If you did not request this, you can ignore this email."
    )
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        db.delete(pending)
        db.commit()
        raise RuntimeError("Unable to send the verification email. Please try again later.") from error


def verify_college_registration(db: Session, token: str):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
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

    college = College(name=pending.college_name, slug=pending.college_slug)
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

    if not verify_password(
        password,
        admin.password_hash
    ):
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

    # Recognition and sound settings are used by scanners authenticated with a
    # college access code rather than an individual admin login. Keep these
    # settings aligned for every administrator in the same college.
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
