from pydantic import BaseModel, ConfigDict, field_validator


CLASS_YEAR_MAP = {
    "FY": "FY", "SY": "SY", "TY": "TY",
    "4Y": "4Y", "5Y": "5Y", "6Y": "6Y", "7Y": "7Y", "8Y": "8Y", "9Y": "9Y", "10Y": "10Y",
    "FIRST YEAR": "FY", "SECOND YEAR": "SY", "THIRD YEAR": "TY", "FOURTH YEAR": "4Y",
    "FIFTH YEAR": "5Y", "SIXTH YEAR": "6Y", "SEVENTH YEAR": "7Y", "EIGHTH YEAR": "8Y",
    "NINTH YEAR": "9Y", "TENTH YEAR": "10Y",
    "1ST YEAR": "FY", "2ND YEAR": "SY", "3RD YEAR": "TY", "4TH YEAR": "4Y",
    "1": "FY", "2": "SY", "3": "TY",
    "5TH YEAR": "5Y", "6TH YEAR": "6Y", "7TH YEAR": "7Y", "8TH YEAR": "8Y",
    "9TH YEAR": "9Y", "10TH YEAR": "10Y",
}


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
            normalized = CLASS_YEAR_MAP.get(value.upper())
            if normalized:
                return normalized
            if value.upper().endswith("Y") and value[:-1].isdigit() and 1 <= int(value[:-1]) <= 99:
                return value[:-1] + "Y"
        return value


class ClassSectionResponse(ClassSectionCreate):
    id: int
    college_id: int
    model_config = ConfigDict(from_attributes=True)
