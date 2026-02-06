"""
Physiological data database model.

Defines the physio_data table for daily physiological data tracking.
"""

import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class PhysioData(SQLModel, table=True):
    """
    Daily physiological data entry.

    Stores HRV, resting heart rate, and sleep metrics.
    One entry per user per day (enforced by unique constraint).
    """
    __tablename__ = "physio_data"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_physio_user_date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    date: datetime.date = Field(nullable=False, index=True)

    # HRV
    hrv_rmssd: Optional[float] = Field(default=None)

    # Heart Rate
    rhr_morning: Optional[int] = Field(default=None)
    rhr_night_avg: Optional[int] = Field(default=None)
    rhr_night_nadir: Optional[int] = Field(default=None)

    # Sleep
    sleep_duration_min: Optional[int] = Field(default=None)
    deep_sleep_min: Optional[int] = Field(default=None)
    rem_sleep_min: Optional[int] = Field(default=None)
    light_sleep_min: Optional[int] = Field(default=None)
    waso_min: Optional[int] = Field(default=None)
    sleep_onset_time: Optional[datetime.time] = Field(default=None)
    wake_time: Optional[datetime.time] = Field(default=None)
    awakenings_count: Optional[int] = Field(default=None)
    sleep_onset_latency_min: Optional[int] = Field(default=None)

    # Timestamps
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
