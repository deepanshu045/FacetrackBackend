import numpy as np
import face_recognition

from sqlalchemy.orm import Session

from app.models.student import Student
from app.services.face_service import generate_face_encoding


def face_distance_threshold(confidence_threshold: int | float | None) -> float:
    """Convert the dashboard's 60–99% confidence setting to face distance.

    ``face_recognition`` considers smaller distances to be better matches. The
    dashboard uses the opposite convention, so 60% maps to the lenient 0.70
    distance and 99% maps to the strict 0.50 distance.
    """
    try:
        confidence = float(confidence_threshold)
    except (TypeError, ValueError):
        confidence = 85.0
    confidence = min(99.0, max(60.0, confidence))
    return 0.70 - ((confidence - 60.0) / 39.0) * 0.20


def recognize_student(db: Session, image_path: str, college_id: int):

    unknown_encoding = generate_face_encoding(image_path)

    if unknown_encoding is None:
        return "INVALID_FACE"

    students = db.query(Student).filter(Student.college_id == college_id).all()

    if not students:
        return None

    known_encodings = []
    known_students = []

    for student in students:

        if student.face_encoding is None:
            continue

        encoding = np.frombuffer(
            student.face_encoding,
            dtype=np.float64
        )

        known_encodings.append(encoding)
        known_students.append(student)

    if not known_encodings:
        return None

    distances = face_recognition.face_distance(
        known_encodings,
        unknown_encoding
    )

    best_index = np.argmin(distances)

    best_distance = distances[best_index]

    # Settings belong to the college administrator profile. A scanner only
    # identifies a college, so use that college's original administrator.
    from app.models.admin import Admin
    admin = (
        db.query(Admin)
        .filter(Admin.college_id == college_id)
        .order_by(Admin.id)
        .first()
    )
    threshold = face_distance_threshold(admin.threshold if admin else None)

    if best_distance > threshold:
        return None

    return known_students[best_index]
