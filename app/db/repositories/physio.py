"""
Physio data repository.

Handles database operations for PhysioData model.
"""

import datetime
from typing import Optional

from sqlmodel import Session, select

from app.models.physio import PhysioData


class PhysioRepository:
    """Repository for PhysioData database operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, entry: PhysioData) -> PhysioData:
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def get_by_id(self, entry_id: int) -> Optional[PhysioData]:
        return self.session.get(PhysioData, entry_id)

    def get_by_user_and_date(
        self, user_id: int, date: datetime.date,
    ) -> Optional[PhysioData]:
        """Get a single entry for a user on a specific date."""
        statement = select(PhysioData).where(
            PhysioData.user_id == user_id,
            PhysioData.date == date,
        )
        return self.session.exec(statement).first()

    def get_by_user_date_range(
        self, user_id: int, start: datetime.date, end: datetime.date,
    ) -> list[PhysioData]:
        """Get entries for a user within a date range (inclusive)."""
        statement = (
            select(PhysioData)
            .where(
                PhysioData.user_id == user_id,
                PhysioData.date >= start,
                PhysioData.date <= end,
            )
            .order_by(PhysioData.date)
        )
        return list(self.session.exec(statement).all())

    def get_latest_by_user(
        self, user_id: int, limit: int = 7,
    ) -> list[PhysioData]:
        """Get the most recent entries for a user, ordered by date descending."""
        statement = (
            select(PhysioData)
            .where(PhysioData.user_id == user_id)
            .order_by(PhysioData.date.desc())
            .limit(limit)
        )
        return list(self.session.exec(statement).all())

    def get_all_by_user(
        self, user_id: int, skip: int = 0, limit: int = 100,
    ) -> list[PhysioData]:
        """Get all entries for a user with pagination."""
        statement = (
            select(PhysioData)
            .where(PhysioData.user_id == user_id)
            .order_by(PhysioData.date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.exec(statement).all())

    def update(self, entry: PhysioData) -> PhysioData:
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
