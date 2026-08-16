from datetime import time

from pydantic import BaseModel, ConfigDict, field_validator


class LectureScheduleCreate(BaseModel):
    subject: str
    day_of_week: int
    start_time: time
    end_time: time

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError("Subject is required.")
        return value

    @field_validator("day_of_week")
    @classmethod
    def validate_day(cls, value: int):
        if value < 0 or value > 6:
            raise ValueError("day_of_week must be between 0 (Monday) and 6 (Sunday).")
        return value

    @field_validator("end_time")
    @classmethod
    def validate_time(cls, value: time, info):
        start = info.data.get("start_time")
        if start and value <= start:
            raise ValueError("End time must be after start time.")
        return value


class LectureScheduleResponse(BaseModel):
    id: int
    college_id: int
    subject: str
    day_of_week: int
    start_time: time
    end_time: time

    model_config = ConfigDict(from_attributes=True)
