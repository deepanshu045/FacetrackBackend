from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator


class CollegeClosureCreate(BaseModel):
    closure_date: date
    reason: str = "Other"
    description: str | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str):
        value = value.strip()
        allowed = {"Holiday", "Event", "Emergency", "Other"}
        if value not in allowed:
            raise ValueError("reason must be Holiday, Event, Emergency, or Other.")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None):
        if value is None:
            return value
        value = value.strip()
        return value or None


class CollegeClosureResponse(BaseModel):
    id: int
    college_id: int
    closure_date: date
    reason: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)
