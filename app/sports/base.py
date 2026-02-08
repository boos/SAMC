"""
Abstract base class for sport plugins.

Every sport in SAMC must implement this interface.  The plugin defines:

- A unique sport identifier (slug)
- A display name
- A default 5-domain stress profile
- Whether the sport is a *background* activity
- A session data schema (sport-specific fields)
- A load calculation method (session data -> LoadVector)
"""

from abc import ABC, abstractmethod
from typing import Type

from pydantic import BaseModel

from app.schemas.stress_vector import LoadVector, StressVector


class SportPlugin(ABC):
    """Abstract base class that every sport plugin must implement."""

    @property
    @abstractmethod
    def sport_id(self) -> str:
        """Unique slug identifier, e.g. ``'weight_lifting'``."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name, e.g. ``'Weight Lifting'``."""
        ...

    @property
    @abstractmethod
    def default_stress_profile(self) -> StressVector:
        """Default stress signature for this sport (values 0.0–1.0)."""
        ...

    @property
    @abstractmethod
    def session_schema(self) -> Type[BaseModel]:
        """Pydantic schema for sport-specific session data."""
        ...

    @abstractmethod
    def compute_load(self, session_data: dict, intensity_modifier: float, ) -> LoadVector:
        """Compute the 5-domain load vector for a session.

        Args:
            session_data: Validated sport-specific data dict.
            intensity_modifier: Overall session intensity factor
                (1.0 = normal).

        Returns:
            :class:`LoadVector` — unclamped, may exceed 1.0 per domain.
        """
        ...

    # ------------------------------------------------------------------
    # Optional overrides with sensible defaults
    # ------------------------------------------------------------------

    @property
    def is_background(self) -> bool:
        """If ``True`` the sport does not occupy micro-cycle slots and
        does not influence cycle length, but its load still contributes
        to the ACWR computation.  Default ``False``."""
        return False

    @property
    def recovery_days_hint(self) -> int:
        """Suggested minimum days between sessions.  Default ``1``."""
        return 1

    @property
    def sessions_per_cycle_default(self) -> int:
        """Default number of sessions per micro-cycle.  Background
        sports should return ``0``.  Default ``1``."""
        return 1
