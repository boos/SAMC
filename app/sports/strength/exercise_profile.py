"""
Exercise stress profiling based on physiological categorisation.

Each exercise is characterised by **5 categorical tags** that describe its
physiological impact.  A deterministic mapping function converts these tags
into a :class:`~app.schemas.stress_vector.StressVector` using transparent,
auditable contribution tables (base + additive model, clamped to [0, 1]).

The tags and their primary physiological rationale:

* **MovementType** (compound / isolation) — drives neuromuscular recruitment
  (N) and systemic recovery cost (A).
* **EccentricLoad** (high / medium / low) — drives tendon stress (T) and
  eccentric muscle damage component of N.
* **MuscleMass** (large / medium / small) — drives metabolic demand (M) and
  contributes to recovery cost (A).
* **LoadIntensity** (heavy / moderate / light) — drives CNS intensity (N)
  and systemic depletion (A).  This is the *default hint* stored in the
  exercise catalog; the per-exercise RPE modulates magnitude at computation
  time, not the shape of the stress profile.
* **Complexity** (high / medium / low) — drives motor learning /
  coordination demand (C).

.. note::

   The contribution tables are **heuristics informed by exercise science**,
   not empirically measured constants.  They are declared as module-level
   dictionaries so they can be inspected, tested and — in future — tuned
   against population data.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.stress_vector import StressVector


# ======================================================================
# Enums
# ======================================================================

class MovementType(str, Enum):
    """Whether the exercise is multi-joint (compound) or single-joint."""
    COMPOUND = "compound"
    ISOLATION = "isolation"


class EccentricLoad(str, Enum):
    """Magnitude of the eccentric (lengthening) component."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MuscleMass(str, Enum):
    """Approximate fraction of total body musculature involved.

    * ``large``  — >40 % (squat, deadlift)
    * ``medium`` — 15–40 % (bench press, rows)
    * ``small``  — <15 % (curls, lateral raises)
    """
    LARGE = "large"
    MEDIUM = "medium"
    SMALL = "small"


class LoadIntensity(str, Enum):
    """Typical loading intensity for this exercise (catalog default)."""
    HEAVY = "heavy"
    MODERATE = "moderate"
    LIGHT = "light"


class Complexity(str, Enum):
    """Motor-learning / coordination complexity."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ======================================================================
# ExerciseProfile data model
# ======================================================================

class ExerciseProfile(BaseModel):
    """Catalog entry describing a single exercise and its 5 tags."""

    exercise_id: str = Field(..., description="Unique slug, e.g. 'back_squat'")
    display_name: str = Field(..., description="Human-readable name")
    movement_type: MovementType
    eccentric_load: EccentricLoad
    muscle_mass: MuscleMass
    load_intensity_hint: LoadIntensity = Field(
        ...,
        description=(
            "Default loading intensity for this exercise.  "
            "Not used directly in load calculation — RPE modulates magnitude."
        ),
    )
    complexity: Complexity
    primary_muscles: list[str] = Field(
        default_factory=list,
        description="Informational list of primary muscles targeted",
    )
    category: str = Field(
        default="",
        description="Movement category, e.g. 'lower_body', 'upper_push'",
    )


# ======================================================================
# Contribution tables — base + additive per domain
# ======================================================================
#
# Each domain has a *base* value plus additive contributions from the
# categories that influence it.  The final value is clamped to [0, 1].
#
# Legend:
#   N = neuromuscular, T = tendineo, M = metabolic,
#   A = autonomic, C = coordination

_N_CONTRIBUTIONS: dict[str, dict[str, float] | float] = {
    "base": 0.20,
    "movement_type": {"compound": 0.25, "isolation": 0.05},
    "load_intensity": {"heavy": 0.35, "moderate": 0.15, "light": 0.05},
    "eccentric_load": {"high": 0.15, "medium": 0.05, "low": 0.0},
}

_T_CONTRIBUTIONS: dict[str, dict[str, float] | float] = {
    "base": 0.15,
    "eccentric_load": {"high": 0.40, "medium": 0.15, "low": 0.05},
    "load_intensity": {"heavy": 0.25, "moderate": 0.10, "light": 0.0},
    "movement_type": {"compound": 0.05, "isolation": 0.0},
}

_M_CONTRIBUTIONS: dict[str, dict[str, float] | float] = {
    "base": 0.10,
    "muscle_mass": {"large": 0.50, "medium": 0.25, "small": 0.05},
    "movement_type": {"compound": 0.10, "isolation": 0.0},
    "load_intensity": {"heavy": 0.05, "moderate": 0.10, "light": 0.05},
}

_A_CONTRIBUTIONS: dict[str, dict[str, float] | float] = {
    "base": 0.10,
    "movement_type": {"compound": 0.20, "isolation": 0.05},
    "muscle_mass": {"large": 0.30, "medium": 0.15, "small": 0.05},
    "load_intensity": {"heavy": 0.20, "moderate": 0.10, "light": 0.05},
}

_C_CONTRIBUTIONS: dict[str, dict[str, float] | float] = {
    "base": 0.05,
    "complexity": {"high": 0.70, "medium": 0.25, "low": 0.05},
}


def _resolve_domain(
    table: dict[str, dict[str, float] | float],
    *,
    movement_type: MovementType,
    eccentric_load: EccentricLoad,
    muscle_mass: MuscleMass,
    load_intensity: LoadIntensity,
    complexity: Complexity,
) -> float:
    """Sum base + additive contributions from a single domain table."""
    tag_values = {
        "movement_type": movement_type.value,
        "eccentric_load": eccentric_load.value,
        "muscle_mass": muscle_mass.value,
        "load_intensity": load_intensity.value,
        "complexity": complexity.value,
    }
    base = table["base"]
    assert isinstance(base, (int, float))
    total = float(base)
    for key, mapping in table.items():
        if key == "base":
            continue
        assert isinstance(mapping, dict)
        tag_val = tag_values.get(key)
        if tag_val is not None:
            total += mapping.get(tag_val, 0.0)
    return min(max(total, 0.0), 1.0)


# ======================================================================
# Public API
# ======================================================================

def compute_exercise_stress_profile(
    movement_type: MovementType,
    eccentric_load: EccentricLoad,
    muscle_mass: MuscleMass,
    load_intensity: LoadIntensity,
    complexity: Complexity,
) -> StressVector:
    """Map 5 categorical exercise tags to a clamped ``StressVector``.

    The mapping uses transparent additive contribution tables defined at
    module level (``_N_CONTRIBUTIONS``, ``_T_CONTRIBUTIONS``, etc.).
    Each domain value is the sum of a base constant plus contributions
    from the relevant categories, clamped to [0.0, 1.0].

    Parameters
    ----------
    movement_type:
        Compound (multi-joint) or isolation (single-joint).
    eccentric_load:
        Magnitude of the eccentric component (high / medium / low).
    muscle_mass:
        Fraction of body musculature involved (large / medium / small).
    load_intensity:
        Typical loading intensity (heavy / moderate / light).
    complexity:
        Motor-learning / coordination complexity (high / medium / low).

    Returns
    -------
    StressVector
        Per-exercise stress profile with values in [0.0, 1.0].
    """
    kwargs = dict(
        movement_type=movement_type,
        eccentric_load=eccentric_load,
        muscle_mass=muscle_mass,
        load_intensity=load_intensity,
        complexity=complexity,
    )
    return StressVector(
        metabolic=_resolve_domain(_M_CONTRIBUTIONS, **kwargs),
        neuromuscular=_resolve_domain(_N_CONTRIBUTIONS, **kwargs),
        tendineo=_resolve_domain(_T_CONTRIBUTIONS, **kwargs),
        autonomic=_resolve_domain(_A_CONTRIBUTIONS, **kwargs),
        coordination=_resolve_domain(_C_CONTRIBUTIONS, **kwargs),
    )
