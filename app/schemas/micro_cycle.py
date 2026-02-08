"""
Micro-cycle configuration API schemas.
"""

import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.user_sport_config import UserSportConfigResponse


class MicroCycleConfigUpdate(BaseModel):
    """Schema for updating micro-cycle settings."""

    override_length_days: Optional[int] = Field(None, ge=3, le=21)
    min_rest_days: Optional[int] = Field(None, ge=0, le=3)


class MicroCycleConfigResponse(BaseModel):
    """Schema for micro-cycle config in API responses."""

    computed_length_days: int
    override_length_days: Optional[int]
    effective_length_days: int
    min_rest_days: int
    current_cycle_start: Optional[datetime.date]
    sports: list[UserSportConfigResponse]

    class Config:
        from_attributes = True
