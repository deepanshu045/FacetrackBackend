from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.dependencies.auth import get_current_admin

from app.models.admin import Admin

from app.schemas.lecture import (
    LectureCreate,
    LectureUpdate,
    LectureResponse,
)

from app.services.lecture_service import (
    create_lecture,
    get_lectures,
    get_lecture,
    update_lecture,
    delete_lecture,
)


router = APIRouter(
    prefix="/lectures",
    tags=["Lectures"]
)


@router.post(
    "",
    response_model=LectureResponse,
    status_code=status.HTTP_201_CREATED
)
def create(
    data: LectureCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    lecture = create_lecture(
        db,
        admin.college_id,
        data
    )

    if lecture is None:
        raise HTTPException(
            status_code=400,
            detail="Lecture already exists."
        )

    return lecture


@router.get(
    "",
    response_model=list[LectureResponse]
)
def list_all(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    return get_lectures(
        db,
        admin.college_id
    )


@router.get(
    "/{lecture_id}",
    response_model=LectureResponse
)
def get_one(
    lecture_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    lecture = get_lecture(
        db,
        lecture_id,
        admin.college_id
    )

    if lecture is None:
        raise HTTPException(
            status_code=404,
            detail="Lecture not found."
        )

    return lecture


@router.put(
    "/{lecture_id}",
    response_model=LectureResponse
)
def update(
    lecture_id: int,
    data: LectureUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    lecture = get_lecture(
        db,
        lecture_id,
        admin.college_id
    )

    if lecture is None:
        raise HTTPException(
            status_code=404,
            detail="Lecture not found."
        )

    try:
        return update_lecture(
            db,
            lecture,
            data
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )


@router.delete(
    "/{lecture_id}"
)
def delete(
    lecture_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    lecture = get_lecture(
        db,
        lecture_id,
        admin.college_id
    )

    if lecture is None:
        raise HTTPException(
            status_code=404,
            detail="Lecture not found."
        )

    delete_lecture(db, lecture)

    return {
        "message": "Lecture deleted successfully."
    }