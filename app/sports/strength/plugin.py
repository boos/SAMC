"""
Weight Lifting sport plugin.

Load calculation uses **per-exercise stress profiling** based on 5
categorical tags (movement type, eccentric load, muscle mass, load
intensity, complexity).  Each exercise produces its own
:class:`~app.schemas.stress_vector.StressVector` via
:func:`~app.sports.strength.exercise_profile.compute_exercise_stress_profile`.

The session load is the **sum** of per-exercise load contributions::

    For each exercise:
        tonnage      = sets × reps × weight_kg
        rpe_factor   = rpe / 10
        stress       = compute_exercise_stress_profile(5 tags)
        exercise_load = stress.scaled_unclamped(tonnage × rpe_factor)

    session_load = Σ exercise_loads × intensity_modifier

There is no arbitrary reference constant.  The ACWR (a ratio) self-
calibrates against the athlete's own training history.
"""

from __future__ import annotations

from typing import Self, Type

from pydantic import BaseModel, Field, model_validator

from app.schemas.stress_vector import LoadVector, StressVector
from app.sports.base import SportPlugin
from app.sports.strength.exercise_catalog import get_exercise
from app.sports.strength.exercise_profile import (
    Complexity,
    EccentricLoad,
    LoadIntensity,
    MovementType,
    MuscleMass,
    compute_exercise_stress_profile,
)


# ======================================================================
# Session schemas
# ======================================================================


class WeightLiftingExercise(BaseModel):
    """A single exercise within a weight-lifting session.

    Provide ``exercise_id`` for a catalog lookup **or** ``exercise_name``
    together with all 5 categorical tags for a custom exercise.
    """

    # ── Catalog lookup ────────────────────────────────────────────
    exercise_id: str | None = Field(
        default=None,
        description="Catalog exercise ID, e.g. 'back_squat'.  Mutually "
                    "exclusive with exercise_name.",
    )

    # ── Custom exercise fields ────────────────────────────────────
    exercise_name: str | None = Field(
        default=None,
        description="Custom exercise name (requires all 5 category tags).",
    )
    movement_type: MovementType | None = None
    eccentric_load: EccentricLoad | None = None
    muscle_mass: MuscleMass | None = None
    load_intensity: LoadIntensity | None = None
    complexity: Complexity | None = None

    # ── Common fields ─────────────────────────────────────────────
    sets: int = Field(..., ge=1, le=20, description="Number of sets performed")
    reps: int = Field(..., ge=1, le=100, description="Repetitions per set")
    weight_kg: float = Field(
        ..., ge=0.0, le=1000.0, description="Weight in kilograms",
    )
    rpe: float = Field(
        ..., ge=1.0, le=10.0,
        description="Rate of perceived exertion for this exercise (1-10)",
    )

    @model_validator(mode="after")
    def validate_exercise_identity(self) -> Self:
        """Ensure exactly one identification path is provided.

        * ``exercise_id`` → catalog lookup (all 5 tags come from the
          catalog; inline tags are ignored).
        * ``exercise_name`` + all 5 tags → custom exercise.

        When ``exercise_id`` is given, the catalog is also validated
        here so that errors surface during schema validation (caught
        by the service layer's ``try/except``).
        """
        if self.exercise_id and self.exercise_name:
            raise ValueError(
                "Provide either exercise_id (catalog) or exercise_name "
                "(custom), not both."
            )
        if not self.exercise_id and not self.exercise_name:
            raise ValueError(
                "Provide exercise_id (catalog lookup) or exercise_name "
                "(custom exercise with 5 category tags)."
            )

        # Validate catalog existence
        if self.exercise_id:
            profile = get_exercise(self.exercise_id)
            if profile is None:
                from app.sports.strength.exercise_catalog import EXERCISE_CATALOG
                available = sorted(EXERCISE_CATALOG.keys())
                raise ValueError(
                    f"Unknown exercise_id: '{self.exercise_id}'.  "
                    f"Available: {available}"
                )

        # Validate custom exercise has all 5 tags
        if self.exercise_name:
            _TAG_FIELDS = [
                "movement_type", "eccentric_load", "muscle_mass",
                "load_intensity", "complexity",
            ]
            missing = [f for f in _TAG_FIELDS if getattr(self, f) is None]
            if missing:
                raise ValueError(
                    f"Custom exercise requires all 5 category tags.  "
                    f"Missing: {missing}"
                )

        return self


class WeightLiftingSessionData(BaseModel):
    """Sport-specific session data for weight lifting."""

    exercises: list[WeightLiftingExercise] = Field(
        ..., min_length=1,
        description="List of exercises performed (each with per-exercise RPE)",
    )
    session_rpe: float | None = Field(
        default=None, ge=1.0, le=10.0,
        description="Optional overall session RPE (informational only, "
                    "not used in load calculation)",
    )


# ======================================================================
# Plugin
# ======================================================================


class WeightLiftingPlugin(SportPlugin):
    """Weight Lifting sport plugin with exercise-categorisation-based
    load computation.
    """

    @property
    def sport_id(self) -> str:
        return "weight_lifting"

    @property
    def display_name(self) -> str:
        return "Weight Lifting"

    @property
    def default_stress_profile(self) -> StressVector:
        """Average stress profile for the sport (informational).

        Not used in ``compute_load`` — each exercise derives its own
        profile from its categorical tags.
        """
        return StressVector(
            metabolic=0.3,
            neuromuscular=0.9,
            tendineo=0.8,
            autonomic=0.5,
            coordination=0.3,
        )

    @property
    def session_schema(self) -> Type[BaseModel]:
        return WeightLiftingSessionData

    def compute_load(
        self,
        session_data: dict,
        intensity_modifier: float,
    ) -> LoadVector:
        """Compute the session load vector from per-exercise contributions.

        Algorithm
        ---------
        For each exercise:

        1. Resolve 5 categorical tags (catalog or inline).
        2. ``stress = compute_exercise_stress_profile(tags)``
        3. ``tonnage = sets × reps × weight_kg``
        4. ``rpe_factor = rpe / 10``
        5. ``exercise_load = stress.scaled_unclamped(tonnage × rpe_factor)``
        6. Accumulate into ``session_load``.

        Finally, apply ``intensity_modifier`` to the aggregate.
        """
        validated = WeightLiftingSessionData(**session_data)
        session_load = LoadVector.zero()

        for ex in validated.exercises:
            # 1. Resolve tags
            if ex.exercise_id:
                profile = get_exercise(ex.exercise_id)
                # profile is guaranteed non-None because the model_validator
                # already checked the catalog.
                assert profile is not None
                mv_type = profile.movement_type
                ecc = profile.eccentric_load
                mm = profile.muscle_mass
                li = profile.load_intensity_hint
                cpx = profile.complexity
            else:
                # Custom exercise — all tags guaranteed present by validator
                assert ex.movement_type is not None
                assert ex.eccentric_load is not None
                assert ex.muscle_mass is not None
                assert ex.load_intensity is not None
                assert ex.complexity is not None
                mv_type = ex.movement_type
                ecc = ex.eccentric_load
                mm = ex.muscle_mass
                li = ex.load_intensity
                cpx = ex.complexity

            # 2. Map categories → per-exercise StressVector
            exercise_stress = compute_exercise_stress_profile(
                movement_type=mv_type,
                eccentric_load=ecc,
                muscle_mass=mm,
                load_intensity=li,
                complexity=cpx,
            )

            # 3. Tonnage
            tonnage = ex.sets * ex.reps * ex.weight_kg

            # 4. RPE modulation
            rpe_factor = ex.rpe / 10.0

            # 5. Per-exercise LoadVector
            exercise_load = exercise_stress.scaled_unclamped(
                tonnage * rpe_factor,
            )

            # 6. Accumulate
            session_load = session_load.add(exercise_load)

        # Apply intensity_modifier
        if intensity_modifier != 1.0:
            session_load = LoadVector(
                metabolic=session_load.metabolic * intensity_modifier,
                neuromuscular=session_load.neuromuscular * intensity_modifier,
                tendineo=session_load.tendineo * intensity_modifier,
                autonomic=session_load.autonomic * intensity_modifier,
                coordination=session_load.coordination * intensity_modifier,
            )

        return session_load

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    @property
    def is_background(self) -> bool:
        return False

    @property
    def recovery_days_hint(self) -> int:
        return 2

    @property
    def sessions_per_cycle_default(self) -> int:
        return 2
