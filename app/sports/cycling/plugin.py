"""
Bicycle Commuting sport plugin.

Stress profile: high metabolic, low-moderate across other domains.
Commuting is relatively steady-state, low-skill, moderate on tendons.

This is a **background** sport: it does not occupy micro-cycle slots
but its load contributes to the ACWR computation.

Load calculation uses duration, RPE, and elevation gain::

    base_load = (duration / 30) * (RPE / 5)
    elevation_bonus = 1 + (elevation_gain_m / 1000)
    factor = base_load * elevation_bonus * intensity_modifier
"""

from typing import Optional, Type

from pydantic import BaseModel, Field

from app.schemas.stress_vector import LoadVector, StressVector
from app.sports.base import SportPlugin

# Reference session: 30 min at RPE 5 = factor 1.0
REFERENCE_DURATION_MIN = 30.0
REFERENCE_RPE = 5.0


class BicycleCommutingSessionData(BaseModel):
    """Sport-specific session data for bicycle commuting."""

    distance_km: float = Field(..., ge=0.1, le=300.0, description="Distance in kilometres")
    duration_min: int = Field(..., ge=1, le=600, description="Duration in minutes")
    avg_heart_rate: Optional[int] = Field(None, ge=40, le=220, description="Average heart rate (bpm)")
    elevation_gain_m: float = Field(0.0, ge=0.0, le=5000.0, description="Total elevation gain (metres)")
    rpe: float = Field(5.0, ge=1.0, le=10.0, description="Rate of perceived exertion (1-10)", )


class BicycleCommutingPlugin(SportPlugin):
    """Bicycle Commuting sport plugin implementation."""

    @property
    def sport_id(self) -> str:
        return "bicycle_commuting"

    @property
    def display_name(self) -> str:
        return "Bicycle Commuting"

    @property
    def default_stress_profile(self) -> StressVector:
        return StressVector(metabolic=0.7, neuromuscular=0.2, tendineo=0.3, autonomic=0.4, coordination=0.1, )

    @property
    def session_schema(self) -> Type[BaseModel]:
        return BicycleCommutingSessionData

    def compute_load(self, session_data: dict, intensity_modifier: float, ) -> LoadVector:
        """Compute load from duration / RPE / elevation.

        Reference session: 30 min commute at RPE 5 = factor 1.0.
        """
        validated = BicycleCommutingSessionData(**session_data)

        base_load = ((validated.duration_min / REFERENCE_DURATION_MIN) * (validated.rpe / REFERENCE_RPE))

        # +10% per 100 m of climbing
        elevation_bonus = 1.0 + (validated.elevation_gain_m / 1000.0)

        combined_factor = base_load * elevation_bonus * intensity_modifier

        return self.default_stress_profile.scaled_unclamped(combined_factor)

    # ------------------------------------------------------------------
    # Background sport overrides
    # ------------------------------------------------------------------

    @property
    def is_background(self) -> bool:
        return True

    @property
    def recovery_days_hint(self) -> int:
        return 0

    @property
    def sessions_per_cycle_default(self) -> int:
        return 0
