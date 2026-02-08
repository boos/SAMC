"""
Sport configuration and micro-cycle endpoints.
"""

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.micro_cycle import (
    MicroCycleConfigResponse,
    MicroCycleConfigUpdate,
)
from app.schemas.user_sport_config import (
    UserSportConfigCreate,
    UserSportConfigResponse,
    UserSportConfigUpdate,
)
from app.services.micro_cycle_service import MicroCycleService

# Ensure plugins are registered before the registry is used.
import app.sports  # noqa: F401
from app.sports.registry import SportRegistry

router = APIRouter()


@router.get(
    "/available",
    summary="List all available sports from the plugin registry.",
)
def list_available_sports():
    """Returns all registered sport plugins with their default profiles."""
    plugins = SportRegistry.all()
    return [
        {
            "sport_id": p.sport_id,
            "display_name": p.display_name,
            "is_background": p.is_background,
            "default_stress_profile": p.default_stress_profile.model_dump(),
            "recovery_days_hint": p.recovery_days_hint,
            "sessions_per_cycle_default": p.sessions_per_cycle_default,
        }
        for p in plugins.values()
    ]


@router.get(
    "/my-sports",
    summary="Get user's configured sports.",
    response_model=list[UserSportConfigResponse],
)
def get_my_sports(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MicroCycleService(db)
    return service.get_user_sports(user.id)


@router.post(
    "/my-sports",
    summary="Add a sport to your micro-cycle.",
    response_model=UserSportConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_sport(
    data: UserSportConfigCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MicroCycleService(db)
    return service.add_sport(user.id, data)


@router.put(
    "/my-sports/{sport_id}",
    summary="Update sport configuration.",
    response_model=UserSportConfigResponse,
)
def update_sport(
    sport_id: str,
    data: UserSportConfigUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MicroCycleService(db)
    return service.update_sport(user.id, sport_id, data)


@router.delete(
    "/my-sports/{sport_id}",
    summary="Remove a sport from your micro-cycle.",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_sport(
    sport_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MicroCycleService(db)
    service.remove_sport(user.id, sport_id)


@router.get(
    "/micro-cycle",
    summary="Get micro-cycle configuration with computed length.",
    response_model=MicroCycleConfigResponse,
)
def get_micro_cycle(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MicroCycleService(db)
    return service.get_micro_cycle(user.id)


@router.put(
    "/micro-cycle",
    summary="Update micro-cycle settings (override length, rest days).",
    response_model=MicroCycleConfigResponse,
)
def update_micro_cycle(
    data: MicroCycleConfigUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = MicroCycleService(db)
    return service.update_micro_cycle(user.id, data)
