"""
Micro-cycle configuration service.

Manages user sport selections and micro-cycle sizing.

**Sizing algorithm**::

    total_slots   = SUM(sessions_per_cycle) for NON-background active sports
    max_recovery  = MAX(recovery_days_hint) for NON-background active sports
    computed_length = total_slots + max_recovery + min_rest_days

Background sports (e.g. bicycle commuting) do **not** contribute to
``total_slots`` or ``max_recovery`` — they affect load/ACWR only.
"""

import datetime

from fastapi import HTTPException, status
from sqlmodel import Session

from app.db.repositories.micro_cycle import MicroCycleConfigRepository
from app.db.repositories.user_sport_config import UserSportConfigRepository
from app.models.user_sport_config import UserSportConfig
from app.schemas.micro_cycle import (MicroCycleConfigResponse, MicroCycleConfigUpdate, )
from app.schemas.stress_vector import StressVector
from app.schemas.user_sport_config import (UserSportConfigCreate, UserSportConfigResponse, UserSportConfigUpdate, )
from app.sports.registry import SportRegistry


class MicroCycleService:
    """Service for micro-cycle and sport configuration."""

    def __init__(self, session: Session):
        self.sport_config_repo = UserSportConfigRepository(session)
        self.micro_cycle_repo = MicroCycleConfigRepository(session)

    # ------------------------------------------------------------------
    # Sport Configuration
    # ------------------------------------------------------------------

    def add_sport(self, user_id: int, data: UserSportConfigCreate, ) -> UserSportConfigResponse:
        plugin = SportRegistry.get(data.sport_id)
        if not plugin:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown sport: '{data.sport_id}'", )

        existing = self.sport_config_repo.get_by_user_and_sport(user_id, data.sport_id)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Sport '{data.sport_id}' already configured", )

        config = UserSportConfig(user_id=user_id, sport_id=data.sport_id, sessions_per_cycle=data.sessions_per_cycle,
                                 custom_stress_profile=(
                                     data.custom_stress_profile.model_dump() if data.custom_stress_profile else None),
                                 priority=data.priority, )
        config = self.sport_config_repo.create(config)

        self._recalculate_cycle_length(user_id)

        return self._sport_config_to_response(config)

    def update_sport(self, user_id: int, sport_id: str, data: UserSportConfigUpdate, ) -> UserSportConfigResponse:
        config = self.sport_config_repo.get_by_user_and_sport(user_id, sport_id)
        if not config:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sport '{sport_id}' not configured", )

        if data.sessions_per_cycle is not None:
            config.sessions_per_cycle = data.sessions_per_cycle
        if data.custom_stress_profile is not None:
            config.custom_stress_profile = (data.custom_stress_profile.model_dump())
        if data.priority is not None:
            config.priority = data.priority
        if data.is_active is not None:
            config.is_active = data.is_active

        config.updated_at = datetime.datetime.utcnow()
        config = self.sport_config_repo.update(config)

        self._recalculate_cycle_length(user_id)

        return self._sport_config_to_response(config)

    def remove_sport(self, user_id: int, sport_id: str) -> None:
        config = self.sport_config_repo.get_by_user_and_sport(user_id, sport_id)
        if not config:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sport '{sport_id}' not configured", )
        self.sport_config_repo.delete(config.id)
        self._recalculate_cycle_length(user_id)

    def get_user_sports(self, user_id: int) -> list[UserSportConfigResponse]:
        configs = self.sport_config_repo.get_all_by_user(user_id)
        return [self._sport_config_to_response(c) for c in configs]

    # ------------------------------------------------------------------
    # Micro-Cycle Config
    # ------------------------------------------------------------------

    def get_micro_cycle(self, user_id: int) -> MicroCycleConfigResponse:
        mc = self.micro_cycle_repo.get_or_create(user_id)
        sports = self.get_user_sports(user_id)
        return MicroCycleConfigResponse(computed_length_days=mc.computed_length_days,
                                        override_length_days=mc.override_length_days,
                                        effective_length_days=mc.effective_length_days, min_rest_days=mc.min_rest_days,
                                        current_cycle_start=mc.current_cycle_start, sports=sports, )

    def update_micro_cycle(self, user_id: int, data: MicroCycleConfigUpdate, ) -> MicroCycleConfigResponse:
        mc = self.micro_cycle_repo.get_or_create(user_id)
        if data.override_length_days is not None:
            mc.override_length_days = data.override_length_days
        if data.min_rest_days is not None:
            mc.min_rest_days = data.min_rest_days
        mc.updated_at = datetime.datetime.utcnow()
        mc = self.micro_cycle_repo.update(mc)

        # Recalculate in case min_rest_days changed
        self._recalculate_cycle_length(user_id)
        return self.get_micro_cycle(user_id)

    # ------------------------------------------------------------------
    # Sizing Algorithm
    # ------------------------------------------------------------------

    def _recalculate_cycle_length(self, user_id: int) -> None:
        """Recompute ``computed_length_days`` from active sports.

        Background sports are **excluded** from the calculation.
        """
        mc = self.micro_cycle_repo.get_or_create(user_id)
        active_configs = self.sport_config_repo.get_active_by_user(user_id)

        if not active_configs:
            mc.computed_length_days = 7  # default when no sports
        else:
            total_slots = 0
            max_recovery = 0

            for config in active_configs:
                plugin = SportRegistry.get(config.sport_id)
                if plugin and plugin.is_background:
                    continue  # background sports don't affect sizing

                total_slots += config.sessions_per_cycle
                if plugin:
                    max_recovery = max(max_recovery, plugin.recovery_days_hint)

            if total_slots == 0:
                # Only background sports active
                mc.computed_length_days = 7
            else:
                mc.computed_length_days = (total_slots + max_recovery + mc.min_rest_days)

        mc.updated_at = datetime.datetime.utcnow()
        self.micro_cycle_repo.update(mc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sport_config_to_response(config: UserSportConfig, ) -> UserSportConfigResponse:
        plugin = SportRegistry.get(config.sport_id)
        default_profile = (plugin.default_stress_profile if plugin else StressVector.zero())
        display_name = plugin.display_name if plugin else config.sport_id
        is_background = plugin.is_background if plugin else False

        custom_profile = None
        if config.custom_stress_profile:
            custom_profile = StressVector(**config.custom_stress_profile)

        effective_profile = (custom_profile if custom_profile else default_profile)

        return UserSportConfigResponse(id=config.id, sport_id=config.sport_id, sport_display_name=display_name,
                                       is_background=is_background, sessions_per_cycle=config.sessions_per_cycle,
                                       default_stress_profile=default_profile, custom_stress_profile=custom_profile,
                                       effective_stress_profile=effective_profile, priority=config.priority,
                                       is_active=config.is_active, created_at=config.created_at,
                                       updated_at=config.updated_at, )
