"""
Training session repository.

Handles database operations for :class:`TrainingSession`.
Includes aggregation queries used by the ACWR computation.
"""

import datetime
from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.training_session import TrainingSession


class TrainingSessionRepository:
    """Repository for TrainingSession database operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, entry: TrainingSession) -> TrainingSession:
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def get_by_id(self, entry_id: int) -> Optional[TrainingSession]:
        return self.session.get(TrainingSession, entry_id)

    def get_by_user_and_date(self, user_id: int, date: datetime.date, ) -> list[TrainingSession]:
        statement = (
            select(TrainingSession).where(TrainingSession.user_id == user_id, TrainingSession.date == date, ).order_by(
                TrainingSession.sport_id, TrainingSession.session_order))
        return list(self.session.exec(statement).all())

    def get_by_user_date_range(self, user_id: int, start: datetime.date, end: datetime.date, ) -> list[TrainingSession]:
        statement = (select(TrainingSession).where(TrainingSession.user_id == user_id, TrainingSession.date >= start,
                                                   TrainingSession.date <= end, ).order_by(TrainingSession.date,
                                                                                           TrainingSession.sport_id))
        return list(self.session.exec(statement).all())

    # ------------------------------------------------------------------
    # Aggregation queries for ACWR
    # ------------------------------------------------------------------

    def sum_load_by_date_range(self, user_id: int, start: datetime.date, end: datetime.date, ) -> dict[str, float]:
        """Sum load vectors across all sessions in the date range.

        Returns a dict with 5 domain sums.  Critical for ACWR.
        """
        statement = select(func.coalesce(func.sum(TrainingSession.metabolic_load), 0.0),
                           func.coalesce(func.sum(TrainingSession.neuromuscular_load), 0.0),
                           func.coalesce(func.sum(TrainingSession.tendons_load), 0.0),
                           func.coalesce(func.sum(TrainingSession.autonomic_load), 0.0),
                           func.coalesce(func.sum(TrainingSession.coordination_load), 0.0), ).where(
            TrainingSession.user_id == user_id, TrainingSession.date >= start, TrainingSession.date <= end, )
        row = self.session.exec(statement).first()
        if row is None:
            return { "metabolic": 0.0, "neuromuscular": 0.0, "tendineo": 0.0, "autonomic": 0.0, "coordination": 0.0, }
        return { "metabolic": float(row[0]), "neuromuscular": float(row[1]), "tendineo": float(row[2]),
                 "autonomic": float(row[3]), "coordination": float(row[4]), }

    def count_by_user_date_range(self, user_id: int, start: datetime.date, end: datetime.date, ) -> int:
        """Count sessions in date range (for data-sufficiency checks)."""
        statement = (select(func.count()).select_from(TrainingSession).where(TrainingSession.user_id == user_id,
                                                                             TrainingSession.date >= start,
                                                                             TrainingSession.date <= end, ))
        return self.session.exec(statement).first() or 0

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def update(self, entry: TrainingSession) -> TrainingSession:
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def delete(self, entry_id: int) -> bool:
        entry = self.get_by_id(entry_id)
        if entry:
            self.session.delete(entry)
            self.session.commit()
            return True
        return False
