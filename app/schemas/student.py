from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional


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
        if value is None:
            return None
        class_map = {
            "FY": "FY", "SY": "SY", "TY": "TY",
            "FIRST YEAR": "FY", "SECOND YEAR": "SY", "THIRD YEAR": "TY",
            "1ST YEAR": "FY", "2ND YEAR": "SY", "3RD YEAR": "TY",
        }
        return class_map.get(value.strip().upper(), value.strip())

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
