"""
User sport configuration model.

Stores which sports a user has selected for their micro-cycle
and optional per-sport configuration overrides.
"""

import datetime
from typing import Optional

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field, SQLModel


class UserSportConfig(SQLModel, table=True):
    """A user's selected sport within their micro-cycle.

    One row per user per sport.  The existence of an active row means
    the user has this sport in their micro-cycle.
    """

    __tablename__ = "user_sport_configs"
    __table_args__ = (UniqueConstraint("user_id", "sport_id", name="uq_user_sport"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    sport_id: str = Field(nullable=False, max_length=50)

    # How many sessions per micro-cycle for this sport
    sessions_per_cycle: int = Field(default=1, ge=1, le=7)

    # User can override the default stress profile per sport (optional)
    custom_stress_profile: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True), )

    # Position / priority in the micro-cycle (lower = scheduled first)
    priority: int = Field(default=0)

    # Is this sport currently active?
    is_active: bool = Field(default=True)

    # Timestamps
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
