from datetime import date, time

from pydantic import BaseModel


class AttendanceReport(BaseModel):
    student_id: int
    roll_no: str
    name: str
    department: str
    attendance_date: date
    attendance_time: time

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
