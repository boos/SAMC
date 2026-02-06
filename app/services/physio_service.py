"""
Physio data service.

Business logic for daily physiological data management.
Handles mapping between nested API schemas and flat database model.
"""

import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session

from app.db.repositories.physio import PhysioRepository
from app.models.physio import PhysioData
from app.schemas.physio import (
    HRVData,
    HeartRateData,
    PhysioEntryCreate,
    PhysioEntryResponse,
    PhysioEntryUpdate,
    SleepData,
)


class PhysioService:
    """Service for physio data business logic."""

    def __init__(self, session: Session):
        self.repository = PhysioRepository(session)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upsert(
        self, user_id: int, date: datetime.date, data: PhysioEntryCreate,
    ) -> tuple[PhysioEntryResponse, bool]:
        """Create or update a physio entry for the given date.

        Returns:
            Tuple of (response, created) where created is True if new entry.
        """
        existing = self.repository.get_by_user_and_date(user_id, date)

        if existing:
            flat = self._schema_to_flat(data)
            for key, value in flat.items():
                if value is not None:
                    setattr(existing, key, value)
            existing.updated_at = datetime.datetime.utcnow()
            entry = self.repository.update(existing)
            return self._to_response(entry), False

        entry = PhysioData(user_id=user_id, date=date, **self._schema_to_flat(data))
        entry = self.repository.create(entry)
        return self._to_response(entry), True

    def get_by_id(self, user_id: int, entry_id: int) -> PhysioEntryResponse:
        entry = self._get_owned_entry(user_id, entry_id)
        return self._to_response(entry)

    def get_by_date(self, user_id: int, date: datetime.date) -> PhysioEntryResponse:
        entry = self.repository.get_by_user_and_date(user_id, date)
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No physio entry for {date}",
            )
        return self._to_response(entry)

    def get_range(
        self, user_id: int, start: datetime.date, end: datetime.date,
    ) -> list[PhysioEntryResponse]:
        entries = self.repository.get_by_user_date_range(user_id, start, end)
        return [self._to_response(e) for e in entries]

    def get_latest(self, user_id: int, limit: int = 7) -> list[PhysioEntryResponse]:
        entries = self.repository.get_latest_by_user(user_id, limit)
        return [self._to_response(e) for e in entries]

    def get_all(
        self, user_id: int, skip: int = 0, limit: int = 100,
    ) -> list[PhysioEntryResponse]:
        entries = self.repository.get_all_by_user(user_id, skip, limit)
        return [self._to_response(e) for e in entries]

    def update(
        self, user_id: int, entry_id: int, data: PhysioEntryUpdate,
    ) -> PhysioEntryResponse:
        entry = self._get_owned_entry(user_id, entry_id)
        flat = self._schema_to_flat(data)
        for key, value in flat.items():
            if value is not None:
                setattr(entry, key, value)
        entry.updated_at = datetime.datetime.utcnow()
        entry = self.repository.update(entry)
        return self._to_response(entry)

    def delete(self, user_id: int, entry_id: int) -> None:
        self._get_owned_entry(user_id, entry_id)
        self.repository.delete(entry_id)

    def delete_by_date(self, user_id: int, date: datetime.date) -> None:
        entry = self.repository.get_by_user_and_date(user_id, date)
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No physio entry for {date}",
            )
        self.repository.delete(entry.id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_owned_entry(self, user_id: int, entry_id: int) -> PhysioData:
        """Get entry by id and verify ownership."""
        entry = self.repository.get_by_id(entry_id)
        if not entry or entry.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physio entry not found",
            )
        return entry

    @staticmethod
    def _schema_to_flat(data: PhysioEntryCreate | PhysioEntryUpdate) -> dict:
        """Convert nested schema to flat dict for the database model."""
        flat: dict = {"date": data.date}

        if data.hrv:
            flat["hrv_rmssd"] = data.hrv.rmssd

        if data.heart_rate:
            flat["rhr_morning"] = data.heart_rate.rhr_morning
            flat["rhr_night_avg"] = data.heart_rate.rhr_night_avg
            flat["rhr_night_nadir"] = data.heart_rate.rhr_night_nadir

        if data.sleep:
            flat["sleep_duration_min"] = data.sleep.sleep_duration_min
            flat["deep_sleep_min"] = data.sleep.deep_sleep_min
            flat["rem_sleep_min"] = data.sleep.rem_sleep_min
            flat["light_sleep_min"] = data.sleep.light_sleep_min
            flat["waso_min"] = data.sleep.waso_min
            flat["sleep_onset_time"] = data.sleep.sleep_onset_time
            flat["wake_time"] = data.sleep.wake_time
            flat["awakenings_count"] = data.sleep.awakenings_count
            flat["sleep_onset_latency_min"] = data.sleep.sleep_onset_latency_min

        return flat

    @staticmethod
    def _to_response(entry: PhysioData) -> PhysioEntryResponse:
        """Convert flat database model to nested response schema."""
        hrv = None
        if entry.hrv_rmssd is not None:
            hrv = HRVData(rmssd=entry.hrv_rmssd)

        heart_rate = None
        if entry.rhr_morning is not None:
            heart_rate = HeartRateData(
                rhr_morning=entry.rhr_morning,
                rhr_night_avg=entry.rhr_night_avg,
                rhr_night_nadir=entry.rhr_night_nadir,
            )

        sleep = None
        if entry.sleep_duration_min is not None:
            sleep = SleepData(
                sleep_duration_min=entry.sleep_duration_min,
                deep_sleep_min=entry.deep_sleep_min,
                rem_sleep_min=entry.rem_sleep_min,
                light_sleep_min=entry.light_sleep_min,
                waso_min=entry.waso_min,
                sleep_onset_time=entry.sleep_onset_time,
                wake_time=entry.wake_time,
                awakenings_count=entry.awakenings_count,
                sleep_onset_latency_min=entry.sleep_onset_latency_min,
            )

        return PhysioEntryResponse(
            id=entry.id,
            user_id=entry.user_id,
            date=entry.date,
            hrv=hrv,
            heart_rate=heart_rate,
            sleep=sleep,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
