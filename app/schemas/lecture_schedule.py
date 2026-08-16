from datetime import time

from pydantic import BaseModel, ConfigDict, field_validator


class LectureScheduleCreate(BaseModel):
    subject: str
    class_section_id: int | None = None
    department: str | None = None
    class_name: str | None = None
    section: str | None = None
    day_of_week: int
    start_time: time
    end_time: time

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, subject: str) -> str:
        normalized_subject = subject.strip()
        if not normalized_subject:
            raise ValueError("Subject is required.")
        return normalized_subject

    @field_validator("day_of_week")
    @classmethod
    def validate_day_of_week(cls, day_of_week: int) -> int:
        if not 0 <= day_of_week <= 6:
            raise ValueError("day_of_week must be between 0 (Monday) and 6 (Sunday).")
        return day_of_week

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, end_time: time, info) -> time:
        start_time = info.data.get("start_time")
        if start_time is not None and end_time <= start_time:
            raise ValueError("End time must be after start time.")
        return end_time


class LectureScheduleResponse(BaseModel):
    id: int
    college_id: int
    class_section_id: int | None = None
    subject: str
    department: str | None = None
    class_name: str | None = None
    section: str | None = None
    day_of_week: int
    start_time: time
    end_time: time

    model_config = ConfigDict(from_attributes=True)
