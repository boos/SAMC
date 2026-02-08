"""
Training session endpoints.

CRUD for training sessions with date-based organisation.
"""

import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.training_session import (TrainingSessionCreate, TrainingSessionResponse, TrainingSessionUpdate, )
from app.services.training_session_service import TrainingSessionService

router = APIRouter()


@router.post("/{date}", summary="Log a training session for a date.", response_model=TrainingSessionResponse,
             status_code=status.HTTP_201_CREATED, )
def create_session(date: datetime.date, data: TrainingSessionCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user), ):
    service = TrainingSessionService(db)
    return service.create(user.id, date, data)


@router.get("/{date}", summary="Get all training sessions for a date.", response_model=list[TrainingSessionResponse], )
def get_sessions_by_date(date: datetime.date, db: Session = Depends(get_db), user: User = Depends(get_current_user), ):
    service = TrainingSessionService(db)
    return service.get_by_date(user.id, date)


@router.get("", summary="List training sessions with optional date range.",
            response_model=list[TrainingSessionResponse], )
def list_sessions(start: Optional[datetime.date] = Query(None, description="Range start (inclusive)"),
                  end: Optional[datetime.date] = Query(None, description="Range end (inclusive)"),
                  db: Session = Depends(get_db), user: User = Depends(get_current_user), ):
    service = TrainingSessionService(db)
    if start and end:
        return service.get_range(user.id, start, end)
    # Default: last 30 days
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=30)
    return service.get_range(user.id, start_date, end_date)


@router.put("/id/{session_id}", summary="Update a training session.", response_model=TrainingSessionResponse, )
def update_session(session_id: int, data: TrainingSessionUpdate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user), ):
    service = TrainingSessionService(db)
    return service.update(user.id, session_id, data)


@router.delete("/id/{session_id}", summary="Delete a training session.", status_code=status.HTTP_204_NO_CONTENT, )
def delete_session(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user), ):
    service = TrainingSessionService(db)
    service.delete(user.id, session_id)
