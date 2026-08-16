from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.class_section import ClassSection
from app.schemas.student import StudentCreate


def create_student(db: Session, student: StudentCreate, college_id: int):
    existing = db.query(Student).filter(Student.college_id == college_id, Student.roll_no == student.roll_no).first()
    if existing:
        return None

    class_section = None
    if student.class_section_id is not None:
        class_section = db.query(ClassSection).filter(ClassSection.id == student.class_section_id, ClassSection.college_id == college_id).first()
        if class_section is None:
            raise ValueError("Class section not found in this college.")
    elif student.class_name and student.section and student.department:
        class_section = db.query(ClassSection).filter(
            ClassSection.college_id == college_id,
            ClassSection.department == student.department,
            ClassSection.class_name == student.class_name,
            ClassSection.section == student.section,
        ).first()
        if class_section is None:
            raise ValueError("Class section does not exist. Create it first.")

    new_student = Student(
        college_id=college_id,
        class_section_id=class_section.id if class_section else None,
        roll_no=student.roll_no,
        name=student.name,
        email=student.email,
        phone_no=student.phone_no,
        department=class_section.department if class_section else student.department,
        class_name=class_section.class_name if class_section else student.class_name,
        section=class_section.section if class_section else student.section,
    )
    db.add(new_student); db.commit(); db.refresh(new_student)
    return new_student
