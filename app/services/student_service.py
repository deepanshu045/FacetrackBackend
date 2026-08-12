from sqlalchemy.orm import Session

from app.models.student import Student
from app.schemas.student import StudentCreate


def create_student(db: Session, student: StudentCreate, college_id: int):

    existing = db.query(Student).filter(
        Student.college_id == college_id,
        Student.roll_no == student.roll_no
    ).first()

    if existing:
        return None

    new_student = Student(
        college_id=college_id,
        roll_no=student.roll_no,
        name=student.name,
        email=student.email,
        phone_no=student.phone_no,
        department=student.department
    )

    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    return new_student
