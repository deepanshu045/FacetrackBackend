from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional


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


def normalize_class_year(value: Optional[str]):
    if value is None:
        return None
    value = value.strip()
    normalized = CLASS_YEAR_MAP.get(value.upper())
    if normalized:
        return normalized
    if value.upper().endswith("Y") and value[:-1].isdigit() and 1 <= int(value[:-1]) <= 99:
        return value[:-1] + "Y"
    return value


class StudentCreate(BaseModel):
    roll_no: str
    name: str
    email: Optional[EmailStr] = None
    phone_no: Optional[str] = None
    department: str
    class_section_id: Optional[int] = None
    class_name: Optional[str] = None
    section: Optional[str] = None

    @field_validator("department")
    @classmethod
    def normalize_department(cls, value: str):
        return "BSc CS" if value.strip().upper() == "BCA" else value.strip()

    @field_validator("class_name")
    @classmethod
    def normalize_class_name(cls, value: Optional[str]):
        return normalize_class_year(value)

    @model_validator(mode="after")
    def require_email_or_phone(self):
        if self.email is None and self.phone_no is None:
            raise ValueError("Email or phone number is required")
        return self


class StudentUpdate(BaseModel):
    roll_no: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_no: Optional[str] = None
    department: Optional[str] = None
    class_section_id: Optional[int] = None
    class_name: Optional[str] = None
    section: Optional[str] = None

    @field_validator("department")
    @classmethod
    def normalize_department(cls, value: Optional[str]):
        if value is None:
            return None
        return "BSc CS" if value.strip().upper() == "BCA" else value.strip()

    @field_validator("class_name")
    @classmethod
    def normalize_class_name(cls, value: Optional[str]):
        return normalize_class_year(value)


class StudentResponse(BaseModel):
    id: int
    roll_no: str
    name: str
    email: Optional[EmailStr] = None
    phone_no: Optional[str] = None
    department: str
    class_section_id: Optional[int] = None
    class_name: Optional[str] = None
    section: Optional[str] = None
    image_path: Optional[str] = None
    has_face: bool = False

    class Config:
        from_attributes = True
