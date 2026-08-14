from datetime import date, time, datetime

from pydantic import BaseModel, ConfigDict, field_validator


class LectureCreate(BaseModel):
    subject: str
    lecture_date: date
    start_time: time
    end_time: time

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str):
        value = value.strip()

        if not value:
            raise ValueError("Subject is required.")

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
    lecture_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None


class LectureResponse(BaseModel):
    id: int
    college_id: int
    subject: str
    lecture_date: date
    start_time: time
    end_time: time
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)