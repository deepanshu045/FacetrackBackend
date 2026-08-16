# FaceTrack Backend Guide

> A practical reference for the FaceTrack backend so you do not need to open the source code every time.
>
> Repository: `deepanshu045/FacetrackBackend`
>
> This document describes the current implementation on the `main` branch. Keep it updated whenever a backend feature or API contract changes.

## 1. Technology

- FastAPI
- SQLAlchemy ORM
- MySQL
- Pydantic schemas
- JWT authentication
- Password hashing
- Face recognition for attendance
- Resend for attendance email notifications
- Background scheduler for daily attendance summaries
- CORS for frontend integration

The FastAPI application is created in `app/main.py` and includes routers for students, recognition, reports, authentication, notifications, public college registration, lectures, weekly schedules, college closures, attendance management, class sections, and teachers.

## 2. Main business structure

```text
College
├── Admins
├── Teachers
│   └── TeacherAssignments → ClassSection
├── ClassSections
│   ├── Students
│   └── Lectures
│       └── Attendance
├── LectureSchedules (weekly recurring pattern)
└── CollegeClosures (holidays / urgent college closure)
```

The important rule is that data is tenant-isolated by `college_id`. Admins and teachers should only operate on records belonging to their college.

## 3. Authentication

### Admin

Admin authentication uses:

`POST /auth/login`

Request fields:

- `college_slug`
- `username`
- `password`

The JWT contains the admin username, admin ID, and college ID.

Useful endpoints:

- `POST /auth/register-admin` — create another admin in the current college
- `GET /auth/admins` — list admins in the current college
- `DELETE /auth/admins/{admin_id}` — delete another admin; the current admin cannot delete itself and a college must keep at least one admin
- `GET /auth/me` — current admin
- `PUT /auth/me` — update current admin
- `POST /auth/change-password` — change password
- `PUT /auth/college/access-code` — set college access code

### College registration / approval

- `POST /auth/register-college` — submit a pending college registration
- `GET /auth/approve-college?token=...` — approve a pending college using the approval link
- `POST /auth/verify-college-email?token=...` — compatibility endpoint for the old frontend

The approval email is sent through the existing email service. Resend testing mode only delivers to the Resend account's testing recipient until a sending domain is verified.

### Teacher

Teacher authentication uses:

`POST /teachers/login`

Request fields:

- `college_slug`
- `username`
- `password`

Teacher JWT includes `teacher_id`, `college_id`, and `role=teacher`.

Useful endpoints:

- `POST /teachers` — admin creates a teacher
- `GET /teachers` — list teachers in the admin's college
- `POST /teachers/login` — teacher login
- `GET /teachers/me` — current teacher
- `POST /teachers/admin/{teacher_id}/classes` — assign teacher to a class section
- `GET /teachers/me/classes` — teacher's assigned classes
- `GET /teachers/me/lectures` — lectures assigned to the teacher or to one of the teacher's assigned classes

Teacher usernames are unique per college using `(college_id, username)`.

## 4. Class sections

Class sections provide the correct boundary for attendance. Instead of relying only on text fields such as department/class/section, students and lectures can use `class_section_id`.

Endpoints:

- `POST /class-sections`
- `GET /class-sections`
- `DELETE /class-sections/{class_section_id}`

Create example:

```json
{
  "department": "CSE",
  "class_name": "1st Year",
  "section": "A"
}
```

A class section is unique inside a college by department + class name + section.

## 5. Students

Endpoints:

- `GET /students/` — list students; supports `query` and optional `class_section_id`
- `GET /students/{student_id}`
- `POST /students/register`
- `PUT /students/{student_id}`
- `DELETE /students/{student_id}`
- `POST /students/upload-face/{student_id}`

Important behavior:

- Student records are filtered by the current admin's `college_id`.
- `class_section_id` can be assigned or changed.
- When a class section is assigned, department/class/section are synchronized from the class section.
- Face upload validates that the image contains exactly one face and rejects duplicate registered faces.

## 6. Lectures

Endpoints:

- `POST /lectures`
- `GET /lectures`
- `GET /lectures/{lecture_id}`
- `PUT /lectures/{lecture_id}`
- `POST /lectures/{lecture_id}/cancel`
- `DELETE /lectures/{lecture_id}`

A lecture can contain:

- college
- subject
- lecture date
- start time
- end time
- status (`Scheduled` / `Cancelled`)
- `class_section_id`
- `teacher_id`

Multiple lectures can exist on the same date as long as their time rules allow them.

Cancelled lectures cannot receive attendance through the teacher attendance flow or recognition flow.

## 7. Weekly lecture schedules

Endpoints:

- `POST /lecture-schedules`
- `GET /lecture-schedules`
- `DELETE /lecture-schedules/{schedule_id}`

A weekly schedule is the recurring pattern used to generate lectures for actual dates. It can be connected to a `class_section_id` so a class gets only its own scheduled lectures.

The lecture list endpoint synchronizes today's scheduled occurrences before returning lectures.

## 8. College closures / holidays

Endpoints:

- `POST /college-closures`
- `GET /college-closures`
- `DELETE /college-closures/{closure_id}`

A closure belongs to a college and a date and can have a reason/description.

When a closure is created, future lecture occurrences for that college/date are removed by the closure service. This is intended for:

- official holidays
- college events
- urgent college shutdowns
- unexpected days off

## 9. Attendance

### Face recognition

`POST /recognition/match`

Upload an image. The backend:

1. Saves the temporary image.
2. Finds a matching registered student within the current college.
3. Checks the active lecture.
4. Marks attendance.
5. Prevents duplicate attendance for the same student/lecture.
6. Removes the temporary image.

### Manual attendance

`POST /recognition/manual`

Request:

```json
{
  "student_id": 5
}
```

The backend uses the active lecture and the selected student.

### Teacher attendance

Teacher endpoints:

- `GET /teachers/me/lectures/{lecture_id}/attendance`
- `POST /teachers/me/lectures/{lecture_id}/attendance`
- `POST /teachers/me/lectures/{lecture_id}/mark-all`

Teacher attendance is restricted to students whose `class_section_id` matches the lecture's class section and whose `college_id` matches the teacher's college.

Allowed status values:

- `Present`
- `Absent`

Cancelled lectures reject attendance marking.

## 10. Reports

All report endpoints require admin authentication.

- `GET /reports/today`
- `GET /reports/student/{student_id}`
- `GET /reports/date/{attendance_date}`
- `GET /reports/monthly/{year}/{month}`

These are the main endpoints for the admin dashboard's attendance reports.

## 11. Attendance notification emails

The backend has a background scheduler that checks the configured absence-summary hour. It calls the attendance summary notification service once per day.

For each student, the service:

1. Finds lectures for the date.
2. Limits them to the student's college.
3. Checks whether a daily notification record already exists.
4. Checks each lecture for attendance.
5. Calculates present, absent, total, and percentage.
6. Sends one collective daily email.
7. Creates `attendance_summary_notifications` only after successful delivery.

If Resend rejects the email, the notification record is not created so a later scheduler run can retry.

## 12. Important database entities

Current important models include:

- `College`
- `Admin`
- `Teacher`
- `TeacherAssignment`
- `ClassSection`
- `Student`
- `Lecture`
- `LectureSchedule`
- `Attendance`
- `AttendanceSummaryNotification`
- `AbsenceNotification`
- `CollegeClosure`
- pending college registration model

Important relationships/fields added for the class-based architecture:

- `students.class_section_id`
- `lectures.class_section_id`
- `lectures.teacher_id`
- `lecture_schedules.class_section_id`
- `attendance.status`

## 13. Admin username rule

Admin usernames are globally unique.

The `Admin` SQLAlchemy model currently uses:

```python
username = Column(String(100), nullable=False, unique=True, index=True)
```

The startup migration checks for duplicate existing admin usernames before creating the global unique index. If duplicates are found, startup raises an error and the duplicate accounts must be renamed first.

Teacher usernames use a different rule:

```text
(college_id, username)
```

Therefore the same teacher username can exist in two different colleges.

## 14. Multi-college security rule

Every protected operation should follow this pattern:

```python
.filter(Model.id == requested_id,
        Model.college_id == current_user.college_id)
```

For class-based attendance, also verify:

```text
student.college_id == lecture.college_id
student.class_section_id == lecture.class_section_id
```

This prevents a teacher/admin from changing an ID in the URL/request and accessing another college's records.

## 15. Startup and database migration

`app/main.py` runs `Base.metadata.create_all(bind=engine)` and several compatibility migrations at startup.

The startup logic currently ensures columns such as:

- `students.phone_no`
- `students.class_section_id`
- `lectures.status`
- `lectures.class_section_id`
- `lectures.teacher_id`
- `lecture_schedules.class_section_id`
- `attendance.status`
- admin settings columns
- college access-code column

It also handles legacy records by assigning missing college IDs to the `legacy-college` record.

Before production, consider replacing startup `ALTER TABLE` migrations with Alembic migrations.

## 16. Frontend integration checklist

The frontend should store the JWT after login and send:

```http
Authorization: Bearer <access_token>
```

Admin pages should call admin-protected endpoints.

Teacher pages should use the teacher JWT and teacher-protected endpoints.

Recommended frontend route structure:

```text
/login
/admin/dashboard
/admin/classes
/admin/students
/admin/teachers
/admin/lectures
/admin/schedules
/admin/closures
/admin/attendance
/admin/reports

/teacher/login
/teacher/dashboard
/teacher/classes
/teacher/lectures
/teacher/attendance
```

## 17. Typical workflows

### Admin creates a class

```text
POST /class-sections
        ↓
class_section_id
```

### Admin registers a student

```text
POST /students/register
        ↓
PUT /students/{id} with class_section_id
```

### Admin creates a teacher

```text
POST /teachers
        ↓
POST /teachers/admin/{teacher_id}/classes
```

### Admin creates a lecture

```text
POST /lectures
        ↓
class_section_id + teacher_id
```

### Teacher marks attendance

```text
POST /teachers/login
        ↓
GET /teachers/me/lectures
        ↓
GET /teachers/me/lectures/{id}/attendance
        ↓
POST /teachers/me/lectures/{id}/attendance
```

### Face recognition attendance

```text
POST /recognition/match
        ↓
face match
        ↓
active lecture check
        ↓
attendance record
```

## 18. Testing priorities

When changing the backend, always test these cases:

1. Admin from College A cannot access College B students.
2. Teacher from College A cannot access College B lectures.
3. Teacher assigned to CSE 1-A cannot mark attendance for CSE 1-B.
4. Cancelled lecture cannot receive attendance.
5. Duplicate attendance is not created.
6. Multiple lectures on one day work correctly.
7. Weekly schedule creates the expected lecture occurrences.
8. College closure prevents future occurrences.
9. Student moved to another class no longer appears in the old class's attendance list.
10. Daily email is recorded only after successful delivery.
11. Duplicate admin usernames are rejected.
12. Teacher usernames are unique inside their college.

## 19. Useful development commands

Start locally:

```bash
uvicorn app.main:app --reload
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

OpenAPI JSON:

```text
http://127.0.0.1:8000/openapi.json
```

## 20. When adding a new feature

Before changing code, answer:

- Which role can use it? Admin / Teacher / Student / public?
- Which college owns the data?
- Does the operation require `college_id` filtering?
- Does it need `class_section_id` filtering?
- Does it affect attendance?
- Does it affect weekly schedules?
- Does it need a new database column/table?
- Does the frontend need a new endpoint?
- Does the Swagger request/response schema need updating?
- Does the feature need a migration?

## 21. Current architecture summary

FaceTrack is now organized around this flow:

```text
College registration
        ↓
Admin approval
        ↓
College Admin
        ├── Class Sections
        │      └── Students
        ├── Teachers
        │      └── Assigned Class Sections
        ├── Weekly Schedules
        │      └── Lectures
        ├── College Closures
        └── Attendance / Reports
                 ↑
        Face Recognition
                 ↑
             Students
```

The key architectural rule is: **attendance belongs to a lecture, a lecture belongs to a class section, and a class section belongs to a college.** This is the basis for preventing students from other classes or colleges from being marked accidentally.
