"""Micro-cycle configuration repository."""

from typing import Optional

from sqlmodel import Session, select

from app.models.micro_cycle import MicroCycleConfig


class MicroCycleConfigRepository:
    """Repository for MicroCycleConfig database operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_user(self, user_id: int) -> Optional[MicroCycleConfig]:
        statement = select(MicroCycleConfig).where(
            MicroCycleConfig.user_id == user_id
        )
        return self.session.exec(statement).first()

    def create(self, config: MicroCycleConfig) -> MicroCycleConfig:
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    def update(self, config: MicroCycleConfig) -> MicroCycleConfig:
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    def get_or_create(self, user_id: int) -> MicroCycleConfig:
        """Get the user's config, or create a default one."""
        existing = self.get_by_user(user_id)
        if existing:
            return existing
        config = MicroCycleConfig(user_id=user_id)
        return self.create(config)
