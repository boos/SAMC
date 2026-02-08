"""
Analytics endpoints — training state, ACWR, readiness, and advisor.
"""

import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.samc.acwr import compute_acwr
from app.samc.advisor import compute_daily_advice
from app.samc.readiness import compute_readiness
from app.schemas.acwr import TrainingStateResponse
from app.schemas.advisor import AdvisorResponse
from app.schemas.readiness import ReadinessResponse

router = APIRouter()


@router.get(
    "/state",
    summary="Get current training state (vectorial ACWR, risk context).",
    response_model=TrainingStateResponse,
)
def get_training_state(
    as_of: Optional[datetime.date] = Query(
        None, description="Reference date (defaults to today)"
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ref_date = as_of or datetime.date.today()
    return compute_acwr(db, user.id, ref_date)


@router.get(
    "/readiness",
    summary="Get per-domain recovery readiness.",
    response_model=ReadinessResponse,
)
def get_readiness(
    as_of: Optional[datetime.datetime] = Query(
        None, description="Reference datetime (defaults to now)"
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ref_dt = as_of or datetime.datetime.utcnow()
    return compute_readiness(db, user.id, ref_dt)


@router.get(
    "/advisor",
    summary="Get daily training advice (ACWR + readiness combined).",
    response_model=AdvisorResponse,
)
def get_daily_advice(
    as_of: Optional[datetime.datetime] = Query(
        None, description="Reference datetime (defaults to now)"
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ref_dt = as_of or datetime.datetime.utcnow()
    return compute_daily_advice(db, user.id, ref_dt)
