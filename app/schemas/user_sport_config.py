"""
User sport configuration API schemas.
"""

import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.stress_vector import StressVector


class UserSportConfigCreate(BaseModel):
    """Schema for adding a sport to user's micro-cycle."""

    sport_id: str = Field(..., description="Sport plugin identifier")
    sessions_per_cycle: int = Field(
        1, ge=1, le=7, description="Sessions per micro-cycle"
    )
    custom_stress_profile: Optional[StressVector] = Field(
        None,
        description="Optional override of the sport's default stress profile",
    )
    priority: int = Field(
        0, ge=0, le=100, description="Scheduling priority (lower = first)"
    )


class UserSportConfigUpdate(BaseModel):
    """Schema for updating sport configuration."""

    sessions_per_cycle: Optional[int] = Field(None, ge=1, le=7)
    custom_stress_profile: Optional[StressVector] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None


class UserSportConfigResponse(BaseModel):
    """Schema for sport config in API responses."""

    id: int
    sport_id: str
    sport_display_name: str
    is_background: bool
    sessions_per_cycle: int
    default_stress_profile: StressVector
    custom_stress_profile: Optional[StressVector]
    effective_stress_profile: StressVector
    priority: int
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True
