# NGO Attendance API

The NGO attendance feature is added to the existing FaceTrack FastAPI backend without changing the existing lecture/face-attendance records.

## Authentication

Use the existing `/auth/login` endpoint for admin users or `/teachers/login` for teacher users. Send the returned JWT as `Authorization: Bearer <token>`.

## Endpoints

- `GET /ngo/classes` — list all classes for an admin, or assigned classes for a teacher.
- `GET /ngo/classes/{class_section_id}/students` — list students in a class.
- `POST /ngo/attendance` — create or update daily attendance for multiple students.
- `GET /ngo/attendance` — filter attendance by class, student and date range.
- `GET /ngo/students/{student_id}/attendance-summary` — present, absent, total and percentage.
- `GET /ngo/classes/{class_section_id}/attendance-summary` — class attendance summary.

## Save attendance example

```json
{
  "class_section_id": 1,
  "attendance_date": "2026-09-24",
  "records": [
    {"student_id": 10, "status": "Present"},
    {"student_id": 11, "status": "Absent"}
  ]
}
```

Saving the same student/class/date again updates the existing record instead of creating a duplicate. The database also enforces a unique constraint for this combination.

## Important design choice

The new table is `ngo_attendance`. It is intentionally separate from the existing `attendance` table because FaceTrack's current attendance is tied to lectures. This keeps the existing application behavior unchanged while providing the simpler date-based attendance model needed by the NGO website.

The feature reuses the existing `Student`, `ClassSection`, `Teacher`, `TeacherAssignment`, `Admin`, JWT and database infrastructure.
