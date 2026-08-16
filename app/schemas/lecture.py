from datetime import date, time, datetime

from pydantic import BaseModel, ConfigDict, field_validator


class LectureCreate(BaseModel):
    subject: str
    department: str
    class_name: str
    section: str
    lecture_date: date
    start_time: time
    end_time: time

    @field_validator("subject", "department", "class_name", "section")
    @classmethod
    def validate_text(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError("This field is required.")
        return value

    @field_validator("end_time")
    @classmethod
    def validate_time(cls, value: time, info):
        start_time = info.data.get("start_time")
        if start_time and value <= start_time:
            raise ValueError("End time must be after start time.")
        return value


class LectureUpdate(BaseModel):
    subject: str | None = None
    department: str | None = None
    class_name: str | None = None
    section: str | None = None
    lecture_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None


class LectureResponse(BaseModel):
    id: int
    college_id: int
    subject: str
    department: str | None = None
    class_name: str | None = None
    section: str | None = None
    lecture_date: date
    start_time: time
    end_time: time
    status: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
