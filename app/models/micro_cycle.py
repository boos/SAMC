"""
Micro-cycle configuration model.

Stores the user's micro-cycle settings.  The ``computed_length_days``
is recalculated whenever sports are added or removed.  The user may
optionally override the computed length.
"""

import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class MicroCycleConfig(SQLModel, table=True):
    """User's micro-cycle configuration.

    One row per user.  ``computed_length_days`` is recalculated by the
    :class:`MicroCycleService` whenever the user's sport selection
    changes.
    """

    __tablename__ = "micro_cycle_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, unique=True, index=True)

    # Computed from active sports
    computed_length_days: int = Field(default=7)

    # User override — takes precedence over computed if set
    override_length_days: Optional[int] = Field(default=None)

    # Minimum rest days within the cycle
    min_rest_days: int = Field(default=1, ge=0, le=3)

    # Current cycle start date (rolling window, not calendar-fixed)
    current_cycle_start: Optional[datetime.date] = Field(default=None)

    # Timestamps
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    @property
    def effective_length_days(self) -> int:
        """Return override if set, otherwise computed length."""
        return self.override_length_days or self.computed_length_days
