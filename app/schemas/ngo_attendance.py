from datetime import date
from pydantic import BaseModel, Field, field_validator


class NGOClassCreate(BaseModel):
    department: str
    class_name: str
    section: str

    @field_validator("department", "class_name", "section")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value is required.")
        if value.upper() == "BCA":
            return "BSc CS"
        return value


class NGOStudentCreate(BaseModel):
    ngo_class_id: int
    roll_no: str
    name: str
    email: str | None = None
    phone_no: str | None = None

    @field_validator("roll_no", "name")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value is required.")
        return value


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
    ngo_class_id: int
    attendance_date: date
    records: list[AttendanceRecordInput] = Field(min_length=1)


class AttendanceFilter(BaseModel):
    ngo_class_id: int | None = None
    student_id: int | None = None
    from_date: date | None = None
    to_date: date | None = None
