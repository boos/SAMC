"""
Physiological data endpoints.

Daily physio entry CRUD with date-based upsert.
"""

import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlmodel import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.physio import PhysioEntryCreate, PhysioEntryResponse
from app.services.physio_service import PhysioService

router = APIRouter()


@router.put("/{date}", summary="Create or update physio entry for a date.", response_model=PhysioEntryResponse, )
def upsert_physio(date: datetime.date, data: PhysioEntryCreate, response: Response, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user), ):
    """Upsert: creates the entry if it doesn't exist, merges data if it does."""
    service = PhysioService(db)
    entry, created = service.upsert(user.id, date, data)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return entry


@router.get("", summary="List physio entries with optional filters.", response_model=list[PhysioEntryResponse], )
def list_physio(date: Optional[datetime.date] = Query(None, description="Exact date filter"),
                start: Optional[datetime.date] = Query(None, description="Range start (inclusive)"),
                end: Optional[datetime.date] = Query(None, description="Range end (inclusive)"),
                skip: int = Query(0, ge=0, description="Records to skip"),
                limit: int = Query(100, ge=1, le=500, description="Max records to return"),
                db: Session = Depends(get_db), user: User = Depends(get_current_user), ):
    """
    Query physio entries. Filter precedence:
    - date: returns single entry for that date (as a list)
    - start + end: returns entries in range
    - no filters: returns paginated list (most recent first)
    """
    service = PhysioService(db)

    if date:
        entry = service.get_by_date(user.id, date)
        return [entry]

    if start and end:
        return service.get_range(user.id, start, end)

    return service.get_all(user.id, skip, limit)


@router.get("/{date}", summary="Get physio entry for a specific date.", response_model=PhysioEntryResponse, )
def get_physio(date: datetime.date, db: Session = Depends(get_db), user: User = Depends(get_current_user), ):
    service = PhysioService(db)
    return service.get_by_date(user.id, date)


@router.delete("/{date}", summary="Delete physio entry for a specific date.", status_code=status.HTTP_204_NO_CONTENT, )
def delete_physio(date: datetime.date, db: Session = Depends(get_db), user: User = Depends(get_current_user), ):
    service = PhysioService(db)
    service.delete_by_date(user.id, date)
