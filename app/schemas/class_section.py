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
        if info.field_name == "class_name":
            class_map = {
                "FY": "FY",
                "SY": "SY",
                "TY": "TY",
                "FIRST YEAR": "FY",
                "SECOND YEAR": "SY",
                "THIRD YEAR": "TY",
                "1ST YEAR": "FY",
                "2ND YEAR": "SY",
                "3RD YEAR": "TY",
            }
            return class_map.get(value.upper(), value)
        return value


class ClassSectionResponse(ClassSectionCreate):
    id: int
    college_id: int
    model_config = ConfigDict(from_attributes=True)
