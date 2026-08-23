from typing import Optional
from pydantic import BaseModel
from pydantic import EmailStr


class AdminCreate(BaseModel):
    username: str
    name: str
    email: EmailStr
    password: str


class CollegeRegistration(BaseModel):
    college_name: str
    college_slug: str
    username: str
    name: str
    email: EmailStr
    password: str


class AdminResponse(BaseModel):
    id: int
    username: str
    name: Optional[str] = None
    email: EmailStr
    notifications: bool
    email_alerts: bool
    sound_alerts: bool
    threshold: int
    resolution: str
    fps: str
    language: str
    college_id: int

    class Config:
        from_attributes = True


class AdminUpdate(BaseModel):
    email: Optional[EmailStr] = None
    notifications: Optional[bool] = None
    email_alerts: Optional[bool] = None
    sound_alerts: Optional[bool] = None
    threshold: Optional[int] = None
    resolution: Optional[str] = None
    fps: Optional[str] = None
    language: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CollegeAccessCodeRequest(BaseModel):
    access_code: str


class LoginRequest(BaseModel):
    college_slug: str
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str


class RegistrationMessage(BaseModel):
    message: str
