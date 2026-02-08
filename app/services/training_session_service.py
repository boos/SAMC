"""
Training session service.

Validates sport-specific data through the plugin schema, computes
the load vector using the plugin's ``compute_load`` method, and
stores both the raw data and the computed vector.
"""

import datetime

from fastapi import HTTPException, status
from sqlmodel import Session

from app.db.repositories.training_session import TrainingSessionRepository
from app.models.training_session import TrainingSession
from app.schemas.stress_vector import LoadVector
from app.schemas.training_session import (TrainingSessionCreate, TrainingSessionResponse, TrainingSessionUpdate, )
from app.sports.registry import SportRegistry


class TrainingSessionService:
    """Service for training session business logic."""

    def __init__(self, session: Session):
        self.repository = TrainingSessionRepository(session)

    def create(self, user_id: int, date: datetime.date, data: TrainingSessionCreate, ) -> TrainingSessionResponse:
        # 1. Validate sport exists in registry
        plugin = SportRegistry.get(data.sport_id)
        if not plugin:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=(f"Unknown sport: '{data.sport_id}'. "
                                                                                 f"Available: {SportRegistry.available_sport_ids()}"), )

        # 2. Validate sport-specific data against plugin schema
        try:
            plugin.session_schema(**data.sport_data)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"Invalid sport data for '{data.sport_id}': {e}", )

        # 3. Compute load vector
        load_vector = plugin.compute_load(data.sport_data, data.intensity_modifier)

        # 4. Create DB entry
        entry = TrainingSession(user_id=user_id, date=date, sport_id=data.sport_id, session_order=data.session_order,
                                intensity_modifier=data.intensity_modifier, sport_data=data.sport_data,
                                notes=data.notes, metabolic_load=load_vector.metabolic,
                                neuromuscular_load=load_vector.neuromuscular, tendons_load=load_vector.tendineo,
                                autonomic_load=load_vector.autonomic, coordination_load=load_vector.coordination, )
        entry = self.repository.create(entry)
        return self._to_response(entry)

    def get_by_id(self, user_id: int, entry_id: int) -> TrainingSessionResponse:
        entry = self._get_owned_entry(user_id, entry_id)
        return self._to_response(entry)

    def get_by_date(self, user_id: int, date: datetime.date) -> list[TrainingSessionResponse]:
        entries = self.repository.get_by_user_and_date(user_id, date)
        return [self._to_response(e) for e in entries]

    def get_range(self, user_id: int, start: datetime.date, end: datetime.date, ) -> list[TrainingSessionResponse]:
        entries = self.repository.get_by_user_date_range(user_id, start, end)
        return [self._to_response(e) for e in entries]

    def update(self, user_id: int, entry_id: int, data: TrainingSessionUpdate, ) -> TrainingSessionResponse:
        entry = self._get_owned_entry(user_id, entry_id)
        plugin = SportRegistry.get_or_raise(entry.sport_id)

        if data.sport_data is not None:
            try:
                plugin.session_schema(**data.sport_data)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Invalid sport data: {e}", )
            entry.sport_data = data.sport_data

        if data.intensity_modifier is not None:
            entry.intensity_modifier = data.intensity_modifier

        if data.notes is not None:
            entry.notes = data.notes

        # Recompute load vector with (potentially) updated data
        load_vector = plugin.compute_load(entry.sport_data, entry.intensity_modifier)
        entry.metabolic_load = load_vector.metabolic
        entry.neuromuscular_load = load_vector.neuromuscular
        entry.tendons_load = load_vector.tendineo
        entry.autonomic_load = load_vector.autonomic
        entry.coordination_load = load_vector.coordination
        entry.updated_at = datetime.datetime.utcnow()

        entry = self.repository.update(entry)
        return self._to_response(entry)

    def delete(self, user_id: int, entry_id: int) -> None:
        self._get_owned_entry(user_id, entry_id)
        self.repository.delete(entry_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_owned_entry(self, user_id: int, entry_id: int) -> TrainingSession:
        entry = self.repository.get_by_id(entry_id)
        if not entry or entry.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training session not found", )
        return entry

    @staticmethod
    def _to_response(entry: TrainingSession) -> TrainingSessionResponse:
        plugin = SportRegistry.get(entry.sport_id)
        display_name = plugin.display_name if plugin else entry.sport_id

        load_vector = LoadVector(metabolic=entry.metabolic_load, neuromuscular=entry.neuromuscular_load,
                                 tendineo=entry.tendons_load, autonomic=entry.autonomic_load,
                                 coordination=entry.coordination_load, )

        return TrainingSessionResponse(id=entry.id, user_id=entry.user_id, date=entry.date, sport_id=entry.sport_id,
                                       sport_display_name=display_name, session_order=entry.session_order,
                                       intensity_modifier=entry.intensity_modifier, sport_data=entry.sport_data,
                                       load_vector=load_vector, notes=entry.notes, created_at=entry.created_at,
                                       updated_at=entry.updated_at, )
