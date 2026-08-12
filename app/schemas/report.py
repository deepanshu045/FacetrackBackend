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