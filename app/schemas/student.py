from pydantic import BaseModel, EmailStr, model_validator
from typing import Optional


class StudentCreate(BaseModel):
    roll_no: str
    name: str
    email: Optional[EmailStr] = None
    phone_no: Optional[str] = None
    department: str
    class_name: Optional[str] = None
    section: Optional[str] = None

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
    class_name: Optional[str] = None
    section: Optional[str] = None


class StudentResponse(BaseModel):
    id: int
    roll_no: str
    name: str
    email: Optional[EmailStr] = None
    phone_no: Optional[str] = None
    department: str
    class_name: Optional[str] = None
    section: Optional[str] = None
    image_path: Optional[str] = None
    has_face: bool = False

    class Config:
        from_attributes = True
