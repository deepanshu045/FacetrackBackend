from datetime import date, time

from pydantic import BaseModel


class AttendanceReport(BaseModel):
    student_id: int
    roll_no: str
    name: str
    department: str
    attendance_date: date
    attendance_time: time
    lecture_id: int | None = None
    subject: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    status: str = "Present"

    class Config:
        from_attributes = True


class StudentAttendanceSummary(BaseModel):
    student_id: int
    roll_no: str
    name: str
    department: str
    class_section_id: int | None = None
    present: int
    total_lectures: int
    percentage: int
