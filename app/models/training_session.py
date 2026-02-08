"""
Training session database model.

Stores training sessions with sport-specific data as JSON
and the computed 5-domain stress load vector as individual
float columns (for efficient SQL aggregation in ACWR queries).
"""

import datetime
from typing import Optional

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field, SQLModel


class TrainingSession(SQLModel, table=True):
    """A single training session.

    Each session belongs to a user, references a sport by ``sport_id``
    string, stores sport-specific data as JSON, and stores the computed
    5-domain load vector as individual float columns.
    """

    __tablename__ = "training_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "date", "sport_id", "session_order", name="uq_training_user_date_sport_order", ),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    date: datetime.date = Field(nullable=False, index=True)
    sport_id: str = Field(nullable=False, max_length=50, index=True)

    # Order within the day for same sport (allows multiple sessions)
    session_order: int = Field(default=1, nullable=False)

    # Session metadata
    intensity_modifier: float = Field(default=1.0, nullable=False)
    notes: Optional[str] = Field(default=None, max_length=1000)

    # Sport-specific data (validated by plugin schema at service layer)
    sport_data: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False), )

    # Computed 5-domain load vector
    metabolic_load: float = Field(default=0.0, nullable=False)
    neuromuscular_load: float = Field(default=0.0, nullable=False)
    tendons_load: float = Field(default=0.0, nullable=False)
    autonomic_load: float = Field(default=0.0, nullable=False)
    coordination_load: float = Field(default=0.0, nullable=False)

    # Timestamps
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
