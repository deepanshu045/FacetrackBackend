from pydantic import BaseModel, ConfigDict, field_validator


class ClassSectionCreate(BaseModel):
    department: str
    class_name: str
    section: str

    @field_validator("department", "class_name", "section")
    @classmethod
    def validate_text(cls, value: str, info):
        value = value.strip()
        if not value:
            raise ValueError("Value is required.")
        if info.field_name == "department" and value.upper() == "BCA":
            return "BSc CS"
        return value


class ClassSectionResponse(ClassSectionCreate):
    id: int
    college_id: int
    model_config = ConfigDict(from_attributes=True)
