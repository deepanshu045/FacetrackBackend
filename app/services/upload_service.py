import os
import tempfile

import face_recognition
import numpy as np
from fastapi import UploadFile
from imagekitio import ImageKit
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.config import (
    IMAGE_JPEG_QUALITY,
    IMAGE_MAX_DIMENSION,
    IMAGEKIT_PRIVATE_KEY,
    IMAGEKIT_URL_ENDPOINT,
)
from app.models.student import Student
from app.services.face_service import generate_face_encoding


def _compress_to_jpeg(file: UploadFile) -> str:
    """Create an optimized JPEG for recognition and cloud storage."""
    try:
        with Image.open(file.file) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode not in ("RGB", "L"):
                background = Image.new("RGB", image.size, "white")
                if image.mode == "RGBA":
                    background.paste(image, mask=image.getchannel("A"))
                else:
                    background.paste(image.convert("RGB"))
                image = background
            else:
                image = image.convert("RGB")

            image.thumbnail((IMAGE_MAX_DIMENSION, IMAGE_MAX_DIMENSION))
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as output:
                image.save(
                    output,
                    format="JPEG",
                    quality=IMAGE_JPEG_QUALITY,
                    optimize=True,
                )
                return output.name
    except (UnidentifiedImageError, OSError, ValueError):
        return ""


def _upload_to_imagekit(local_path: str, student_id: int, college_id: int):
    if not IMAGEKIT_PRIVATE_KEY:
        return None

    client = ImageKit(private_key=IMAGEKIT_PRIVATE_KEY)
    with open(local_path, "rb") as image_file:
        response = client.files.upload(
            file=image_file,
            file_name=f"student-{student_id}.jpg",
            folder=f"/colleges/{college_id}/students",
            is_private_file=True,
            use_unique_file_name=True,
            tags=["student-face", f"college-{college_id}"],
        )
    return response


def _build_imagekit_url(upload_result):
    if upload_result.url:
        return upload_result.url

    if upload_result.file_path and IMAGEKIT_URL_ENDPOINT:
        endpoint = IMAGEKIT_URL_ENDPOINT.rstrip("/")
        path = upload_result.file_path
        if not path.startswith("/"):
            path = "/" + path
        return endpoint + path

    if upload_result.file_id:
        return upload_result.file_id

    return None


def upload_student_image(
    db: Session,
    student_id: int,
    file: UploadFile,
    college_id: int,
):
    student = db.query(Student).filter(
        Student.id == student_id,
        Student.college_id == college_id,
    ).first()

    if student is None:
        return None

    filepath = _compress_to_jpeg(file)
    if not filepath:
        return "INVALID_IMAGE"

    try:
        encoding = generate_face_encoding(filepath)
        if encoding is None:
            return "INVALID_FACE"

        existing_students = db.query(Student).filter(
            Student.college_id == college_id,
            Student.face_encoding.isnot(None),
        ).all()

        threshold = 0.50
        for existing in existing_students:
            if existing.id == student_id:
                continue

            known_encoding = np.frombuffer(existing.face_encoding, dtype=np.float64)
            distance = face_recognition.face_distance([known_encoding], encoding)[0]
            if distance <= threshold:
                return "DUPLICATE_FACE"

        upload_result = _upload_to_imagekit(filepath, student_id, college_id)
        if upload_result is None:
            return "STORAGE_NOT_CONFIGURED"

        student.image_path = _build_imagekit_url(upload_result)
        student.face_encoding = encoding.tobytes()
        db.commit()
        db.refresh(student)
        return student
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
