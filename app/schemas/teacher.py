from pydantic import BaseModel, ConfigDict, EmailStr


class TeacherCreate(BaseModel):
    username: str
    name: str
    email: EmailStr | None = None
    password: str


class TeacherCredentialsUpdate(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    password: str | None = None


class TeacherResponse(BaseModel):
    id: int
    college_id: int
    username: str
    name: str
    email: EmailStr | None = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class TeacherLogin(BaseModel):
    college_slug: str
    username: str
    password: str


class TeacherAssignmentCreate(BaseModel):
    class_section_id: int


class TeacherAssignmentResponse(BaseModel):
    id: int
    teacher_id: int
    class_section_id: int
    model_config = ConfigDict(from_attributes=True)
