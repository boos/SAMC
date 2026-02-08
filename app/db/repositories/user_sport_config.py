"""
User sport configuration repository.
"""

from typing import Optional

from sqlmodel import Session, select

from app.models.user_sport_config import UserSportConfig


class UserSportConfigRepository:
    """Repository for UserSportConfig database operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, config: UserSportConfig) -> UserSportConfig:
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    def get_by_id(self, config_id: int) -> Optional[UserSportConfig]:
        return self.session.get(UserSportConfig, config_id)

    def get_by_user_and_sport(self, user_id: int, sport_id: str, ) -> Optional[UserSportConfig]:
        statement = select(UserSportConfig).where(UserSportConfig.user_id == user_id,
                                                  UserSportConfig.sport_id == sport_id, )
        return self.session.exec(statement).first()

    def get_active_by_user(self, user_id: int) -> list[UserSportConfig]:
        statement = (
            select(UserSportConfig).where(UserSportConfig.user_id == user_id, UserSportConfig.is_active == True,
                                          # noqa: E712
                                          ).order_by(UserSportConfig.priority))
        return list(self.session.exec(statement).all())

    def get_all_by_user(self, user_id: int) -> list[UserSportConfig]:
        statement = (
            select(UserSportConfig).where(UserSportConfig.user_id == user_id).order_by(UserSportConfig.priority))
        return list(self.session.exec(statement).all())

    def update(self, config: UserSportConfig) -> UserSportConfig:
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    def delete(self, config_id: int) -> bool:
        config = self.get_by_id(config_id)
        if config:
            self.session.delete(config)
            self.session.commit()
            return True
        return False
