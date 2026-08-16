from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.dependencies.auth import get_current_admin
from app.models.admin import Admin
from app.models.college_closure import CollegeClosure
from app.schemas.college_closure import CollegeClosureCreate, CollegeClosureResponse
from app.services.college_closure_service import (
    create_closure,
    delete_closure,
    get_closures,
    remove_future_lecture_occurrences,
)

router = APIRouter(prefix="/college-closures", tags=["College Closures"])


@router.post("", response_model=CollegeClosureResponse, status_code=status.HTTP_201_CREATED)
def create(
    data: CollegeClosureCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    closure = create_closure(
        db, admin.college_id, data.closure_date, data.reason, data.description
    )
    if closure is None:
        raise HTTPException(status_code=400, detail="A closure already exists for this date.")

    remove_future_lecture_occurrences(db, admin.college_id, data.closure_date)
    return closure


@router.get("", response_model=list[CollegeClosureResponse])
def list_all(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return get_closures(db, admin.college_id)


@router.delete("/{closure_id}")
def delete(
    closure_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    closure = (
        db.query(CollegeClosure)
        .filter(
            CollegeClosure.id == closure_id,
            CollegeClosure.college_id == admin.college_id,
        )
        .first()
    )
    if closure is None:
        raise HTTPException(status_code=404, detail="College closure not found.")

    delete_closure(db, closure)
    return {"message": "College closure deleted successfully."}
