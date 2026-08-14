# FaceTrack Backend - Agent Guide

## What this project is

FaceTrack is a FastAPI backend for multi-college face-attendance tracking. It
provides administrator authentication, student management, face registration
and recognition, attendance/report APIs, public scanner APIs, ImageKit image
storage, and Resend transactional email.

The companion frontend is deployed separately. The current production frontend
origin is `https://facetrackfrontend.pages.dev`; the backend is deployed on
Render.

## Start here: application boot sequence

The production container starts here:

```text
Dockerfile CMD
  -> gunicorn -k uvicorn.workers.UvicornWorker app.main:app
  -> import app/main.py
  -> import models and routers
  -> Base.metadata.create_all(bind=engine)
  -> schema compatibility functions + legacy default-admin setup
  -> create FastAPI app and CORS middleware
  -> include routers
  -> lifespan starts the daily absence-email scheduler thread
```

For local development, activate `myenv` and run:

```powershell
myenv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API root (`GET /`) returns a small health message. OpenAPI is normally at
`/docs`.

## Repository map

```text
app/main.py                    Application entry point, startup schema work, CORS, routers, scheduler
app/config.py                  Environment-variable loading and global settings
app/database/                  SQLAlchemy engine, Base, session dependency
app/models/                    SQLAlchemy persistence models
app/schemas/                   Pydantic request/response models
app/api/                       FastAPI endpoint routers
app/services/                  Business logic: auth, mail, face, attendance, reports, uploads
app/dependencies/auth.py       JWT bearer-token authentication dependency
app/security/                  Password hashing and JWT helpers
Dockerfile                     Render/container entry point
requirements.txt               Python dependencies
```

## Configuration

Copy `.env.example` to `.env` for local work. Do not commit `.env` or any
secrets. Production values must be configured in Render's Environment panel.

Required/important variables:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Preferred MySQL-compatible SQLAlchemy URL. The `DB_*` variables are the fallback. |
| `JWT_SECRET_KEY` | Replace the development default in every deployed environment. |
| `FRONTEND_URL` | Used in college-verification links and the default CORS list. |
| `CORS_ORIGINS` | Comma-separated exact origins; no trailing slash. Include the deployed frontend. |
| `RESEND_API_KEY` | Resend API key for verification and absence emails. |
| `RESEND_SENDER` | Sender on a Resend-verified domain. `onboarding@resend.dev` is test-only. |
| `IMAGEKIT_PRIVATE_KEY`, `IMAGEKIT_URL_ENDPOINT` | Private student-face image storage. |
| `ABSENCE_CHECK_HOUR` | Local-server-hour cutoff for the absence scheduler (default `11`). |

## API areas

| Router | Main responsibilities |
| --- | --- |
| `/auth` | College registration/verification, login, current-admin settings, admin management, scanner access-code setup. |
| `/students` | Authenticated student CRUD and face-image upload. |
| `/recognition` | Authenticated face matching and manual attendance. |
| `/reports` | Authenticated today/student/date/month attendance reports. |
| `/notifications` | Authenticated recent attendance notifications. |
| `/public` | College discovery, scanner access-code resolution, scanner attendance marking, public attendance lookup. |

With the exception of `/public` and registration/login endpoints, routes use
`get_current_admin`. New data-access paths must scope students, attendance, and
related records to `admin.college_id`; this is a multi-tenant application.

## Data model and important relationships

`College` owns `Admin` and `Student` records. A `Student` has `Attendance`
records, an optional image URL, and a binary NumPy face encoding. Attendance is
unique per student/date. `AbsenceNotification` records emails sent for an
absent student/date so the scheduler does not resend them. Pending college
registrations store a hash of the one-time verification token and a hashed
password until verification succeeds.

When deleting a student, delete dependent absence notifications first; the
student-to-attendance ORM relationship handles attendance deletion. See
`app/api/student.py`.

## Email behavior

All transactional email goes through `app/services/email_service.py` and the
Resend Python SDK. Call `send_email(...)`; do not add SMTP code. Resend errors
are intentionally converted into `EmailDeliveryError`; college registration
returns this as an HTTP 503 and removes the unsent pending registration.

For arbitrary recipient delivery, `RESEND_SENDER` must use an exact domain (or
subdomain) verified in Resend. Never log API keys.

## Startup and schema caution

There is no Alembic migration system. `app/main.py` executes `create_all` and
several compatibility `ALTER TABLE`/index migration routines at import/startup.
Treat edits there as production database changes: inspect the active MySQL
schema and keep operations idempotent. Do not move them into request handlers.

`create_default_admin()` exists for legacy data compatibility. Do not depend on
the default credentials in a deployment; replace/secure them operationally.

## Validation

Use the project virtual environment when it exists:

```powershell
myenv\Scripts\python.exe -m compileall -q app
myenv\Scripts\python.exe -m pytest tests -q
```

`tmp_imagekit_test.py` is a malformed scratch file, so running bare `pytest`
from the repository root currently fails during collection. The `tests/`
directory currently has no meaningful automated coverage; add focused tests for
behavioral changes, especially tenant isolation and database deletes.

## Change checklist

1. Begin with `app/main.py`, then follow the relevant router into its service.
2. Preserve college scoping on every authenticated query.
3. Keep secrets in environment variables only; update `.env.example` when a
   new non-secret configuration value is needed.
4. For browser issues, check both the actual backend error and Render's
   `CORS_ORIGINS`; a server-side 500 can appear as a CORS failure in browsers.
5. Compile/test before handoff and state any test limitation plainly.
