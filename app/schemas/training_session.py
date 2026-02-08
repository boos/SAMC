"""
Training session API schemas.

Sport-specific data is validated dynamically by the plugin's
``session_schema`` at the service layer.
"""

import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.stress_vector import LoadVector


class TrainingSessionCreate(BaseModel):
    """Schema for creating a training session."""

    sport_id: str = Field(
        ..., description="Sport plugin identifier, e.g. 'weight_lifting'"
    )
    intensity_modifier: float = Field(
        1.0,
        ge=0.1,
        le=3.0,
        description="Intensity modifier applied to base stress profile (1.0 = normal)",
    )
    sport_data: dict[str, Any] = Field(
        ...,
        description="Sport-specific session data (validated against plugin schema)",
    )
    notes: Optional[str] = Field(
        None, max_length=1000, description="Optional session notes"
    )
    session_order: int = Field(
        1,
        ge=1,
        le=5,
        description="Session order within the day for same sport",
    )


class TrainingSessionUpdate(BaseModel):
    """Schema for updating a training session."""

    intensity_modifier: Optional[float] = Field(None, ge=0.1, le=3.0)
    sport_data: Optional[dict[str, Any]] = None
    notes: Optional[str] = Field(None, max_length=1000)


class TrainingSessionResponse(BaseModel):
    """Schema for training session in API responses."""

    id: int
    user_id: int
    date: datetime.date
    sport_id: str
    sport_display_name: str
    session_order: int
    intensity_modifier: float
    sport_data: dict[str, Any]
    load_vector: LoadVector
    notes: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True
