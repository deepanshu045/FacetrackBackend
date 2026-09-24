from datetime import date

from pydantic import BaseModel, Field, field_validator


class AttendanceRecordInput(BaseModel):
    student_id: int
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        value = value.strip().title()
        if value not in {"Present", "Absent"}:
            raise ValueError("Status must be Present or Absent.")
        return value


class NGOAttendanceSaveRequest(BaseModel):
    class_section_id: int
    attendance_date: date
    records: list[AttendanceRecordInput] = Field(min_length=1)


class AttendanceFilter(BaseModel):
    class_section_id: int | None = None
    student_id: int | None = None
    from_date: date | None = None
    to_date: date | None = None
