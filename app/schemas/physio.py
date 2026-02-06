"""
Physiological data API schemas.

Pydantic models for daily physiology entry request/response validation.
Supports HRV, resting heart rate, and sleep metrics.
"""

import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Nested value-object schemas (embedded data groups)
# ---------------------------------------------------------------------------

class HRVData(BaseModel):
    """HRV (Heart Rate Variability) metrics."""

    rmssd: float = Field(
        ..., ge=1.0, le=300.0,
        description="Root mean square of successive RR interval differences (ms)",
    )


class HeartRateData(BaseModel):
    """Resting heart rate metrics."""

    rhr_morning: int = Field(
        ..., ge=25, le=120,
        description="Morning resting heart rate at waking (bpm)",
    )
    rhr_night_avg: Optional[int] = Field(
        None, ge=25, le=120,
        description="Average resting heart rate during night (bpm)",
    )
    rhr_night_nadir: Optional[int] = Field(
        None, ge=20, le=100,
        description="Lowest resting heart rate during night (bpm)",
    )


class SleepData(BaseModel):
    """Sleep metrics."""

    sleep_duration_min: int = Field(
        ..., ge=0, le=1440,
        description="Total effective sleep duration (minutes)",
    )
    deep_sleep_min: Optional[int] = Field(
        None, ge=0, le=600,
        description="Time in deep sleep (minutes)",
    )
    rem_sleep_min: Optional[int] = Field(
        None, ge=0, le=600,
        description="Time in REM sleep (minutes)",
    )
    light_sleep_min: Optional[int] = Field(
        None, ge=0, le=600,
        description="Time in light sleep (minutes)",
    )
    waso_min: Optional[int] = Field(
        None, ge=0, le=480,
        description="Wake after sleep onset (minutes awake during the night)",
    )
    sleep_onset_time: Optional[datetime.time] = Field(
        None,
        description="Time of falling asleep (HH:MM)",
    )
    wake_time: Optional[datetime.time] = Field(
        None,
        description="Time of waking up (HH:MM)",
    )
    awakenings_count: Optional[int] = Field(
        None, ge=0, le=50,
        description="Number of awakenings during the night",
    )
    sleep_onset_latency_min: Optional[int] = Field(
        None, ge=0, le=300,
        description="Time to fall asleep after lights out (minutes)",
    )


# ---------------------------------------------------------------------------
# Entity schemas (Base / Create / Update / Response)
# ---------------------------------------------------------------------------

# Shared properties
class PhysioEntryBase(BaseModel):
    """Base physiological entry schema with common fields."""

    date: datetime.date = Field(
        ...,
        description="Calendar date this entry belongs to (YYYY-MM-DD)",
    )
    hrv: Optional[HRVData] = Field(
        None,
        description="Heart rate variability data",
    )
    heart_rate: Optional[HeartRateData] = Field(
        None,
        description="Resting heart rate data",
    )
    sleep: Optional[SleepData] = Field(
        None,
        description="Sleep metrics data",
    )


# Request schemas
class PhysioEntryCreate(PhysioEntryBase):
    """Schema for creating a daily physiological entry."""
    pass


class PhysioEntryUpdate(BaseModel):
    """Schema for updating a physiological entry (all fields optional)."""

    date: Optional[datetime.date] = Field(
        None,
        description="Calendar date this entry belongs to (YYYY-MM-DD)",
    )
    hrv: Optional[HRVData] = Field(
        None,
        description="Heart rate variability data",
    )
    heart_rate: Optional[HeartRateData] = Field(
        None,
        description="Resting heart rate data",
    )
    sleep: Optional[SleepData] = Field(
        None,
        description="Sleep metrics data",
    )


# Response schemas
class PhysioEntryResponse(PhysioEntryBase):
    """Schema for physiological entry data in API responses."""

    id: int
    user_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True
