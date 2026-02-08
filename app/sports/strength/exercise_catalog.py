"""
Built-in exercise catalog for the weight-lifting plugin.

Each entry is an :class:`~app.sports.strength.exercise_profile.ExerciseProfile`
with 5 categorical tags that feed into
:func:`~app.sports.strength.exercise_profile.compute_exercise_stress_profile`.

The catalog is intentionally opinionated but **extensible** — users can log
exercises not listed here by providing the 5 tags inline (see the
``exercise_name`` path in
:class:`~app.sports.strength.plugin.WeightLiftingExercise`).

To add a new exercise, call :func:`register_exercise` or simply append to
``EXERCISE_CATALOG`` at import time.
"""

from __future__ import annotations

from app.sports.strength.exercise_profile import (
    Complexity,
    EccentricLoad,
    ExerciseProfile,
    LoadIntensity,
    MovementType,
    MuscleMass,
)

# ======================================================================
# Catalog storage
# ======================================================================

EXERCISE_CATALOG: dict[str, ExerciseProfile] = {}


def register_exercise(profile: ExerciseProfile) -> None:
    """Register an exercise profile in the global catalog."""
    EXERCISE_CATALOG[profile.exercise_id] = profile


def get_exercise(exercise_id: str) -> ExerciseProfile | None:
    """Look up an exercise by its ID.  Returns ``None`` if not found."""
    return EXERCISE_CATALOG.get(exercise_id)


# ======================================================================
# Helpers
# ======================================================================

# Aliases for brevity in the table below
C = MovementType.COMPOUND
I = MovementType.ISOLATION
EH = EccentricLoad.HIGH
EM = EccentricLoad.MEDIUM
EL = EccentricLoad.LOW
ML = MuscleMass.LARGE
MM = MuscleMass.MEDIUM
MS = MuscleMass.SMALL
LH = LoadIntensity.HEAVY
LM = LoadIntensity.MODERATE
LL = LoadIntensity.LIGHT
XH = Complexity.HIGH
XM = Complexity.MEDIUM
XL = Complexity.LOW

# ======================================================================
# Built-in exercises
# ======================================================================

_EXERCISES: list[ExerciseProfile] = [
    # ── Lower Body ────────────────────────────────────────────────
    ExerciseProfile(
        exercise_id="back_squat",
        display_name="Back Squat",
        movement_type=C, eccentric_load=EH, muscle_mass=ML,
        load_intensity_hint=LH, complexity=XM,
        primary_muscles=["quadriceps", "glutes", "hamstrings", "core"],
        category="lower_body",
    ),
    ExerciseProfile(
        exercise_id="front_squat",
        display_name="Front Squat",
        movement_type=C, eccentric_load=EH, muscle_mass=ML,
        load_intensity_hint=LH, complexity=XH,
        primary_muscles=["quadriceps", "glutes", "core", "upper_back"],
        category="lower_body",
    ),
    ExerciseProfile(
        exercise_id="deadlift",
        display_name="Deadlift",
        movement_type=C, eccentric_load=EM, muscle_mass=ML,
        load_intensity_hint=LH, complexity=XM,
        primary_muscles=["hamstrings", "glutes", "erectors", "traps"],
        category="lower_body",
    ),
    ExerciseProfile(
        exercise_id="romanian_deadlift",
        display_name="Romanian Deadlift",
        movement_type=C, eccentric_load=EH, muscle_mass=ML,
        load_intensity_hint=LM, complexity=XM,
        primary_muscles=["hamstrings", "glutes", "erectors"],
        category="lower_body",
    ),
    ExerciseProfile(
        exercise_id="leg_press",
        display_name="Leg Press",
        movement_type=C, eccentric_load=EM, muscle_mass=ML,
        load_intensity_hint=LH, complexity=XL,
        primary_muscles=["quadriceps", "glutes"],
        category="lower_body",
    ),
    ExerciseProfile(
        exercise_id="bulgarian_split_squat",
        display_name="Bulgarian Split Squat",
        movement_type=C, eccentric_load=EH, muscle_mass=MM,
        load_intensity_hint=LM, complexity=XM,
        primary_muscles=["quadriceps", "glutes", "hip_stabilisers"],
        category="lower_body",
    ),
    ExerciseProfile(
        exercise_id="leg_extension",
        display_name="Leg Extension",
        movement_type=I, eccentric_load=EM, muscle_mass=MM,
        load_intensity_hint=LM, complexity=XL,
        primary_muscles=["quadriceps"],
        category="lower_body",
    ),
    ExerciseProfile(
        exercise_id="leg_curl",
        display_name="Leg Curl",
        movement_type=I, eccentric_load=EH, muscle_mass=MM,
        load_intensity_hint=LM, complexity=XL,
        primary_muscles=["hamstrings"],
        category="lower_body",
    ),
    ExerciseProfile(
        exercise_id="hip_thrust",
        display_name="Hip Thrust",
        movement_type=C, eccentric_load=EL, muscle_mass=ML,
        load_intensity_hint=LM, complexity=XL,
        primary_muscles=["glutes", "hamstrings"],
        category="lower_body",
    ),

    # ── Upper Push ────────────────────────────────────────────────
    ExerciseProfile(
        exercise_id="bench_press",
        display_name="Bench Press",
        movement_type=C, eccentric_load=EM, muscle_mass=MM,
        load_intensity_hint=LH, complexity=XL,
        primary_muscles=["pectorals", "anterior_deltoids", "triceps"],
        category="upper_push",
    ),
    ExerciseProfile(
        exercise_id="overhead_press",
        display_name="Overhead Press",
        movement_type=C, eccentric_load=EM, muscle_mass=MM,
        load_intensity_hint=LH, complexity=XM,
        primary_muscles=["deltoids", "triceps", "core"],
        category="upper_push",
    ),
    ExerciseProfile(
        exercise_id="incline_db_press",
        display_name="Incline Dumbbell Press",
        movement_type=C, eccentric_load=EM, muscle_mass=MM,
        load_intensity_hint=LM, complexity=XL,
        primary_muscles=["upper_pectorals", "anterior_deltoids", "triceps"],
        category="upper_push",
    ),
    ExerciseProfile(
        exercise_id="dip",
        display_name="Dip",
        movement_type=C, eccentric_load=EM, muscle_mass=MM,
        load_intensity_hint=LM, complexity=XL,
        primary_muscles=["pectorals", "triceps", "anterior_deltoids"],
        category="upper_push",
    ),
    ExerciseProfile(
        exercise_id="lateral_raise",
        display_name="Lateral Raise",
        movement_type=I, eccentric_load=EL, muscle_mass=MS,
        load_intensity_hint=LL, complexity=XL,
        primary_muscles=["lateral_deltoids"],
        category="upper_push",
    ),
    ExerciseProfile(
        exercise_id="tricep_pushdown",
        display_name="Tricep Pushdown",
        movement_type=I, eccentric_load=EL, muscle_mass=MS,
        load_intensity_hint=LM, complexity=XL,
        primary_muscles=["triceps"],
        category="upper_push",
    ),

    # ── Upper Pull ────────────────────────────────────────────────
    ExerciseProfile(
        exercise_id="barbell_row",
        display_name="Barbell Row",
        movement_type=C, eccentric_load=EM, muscle_mass=MM,
        load_intensity_hint=LH, complexity=XM,
        primary_muscles=["lats", "rhomboids", "rear_deltoids", "biceps"],
        category="upper_pull",
    ),
    ExerciseProfile(
        exercise_id="pull_up",
        display_name="Pull-Up",
        movement_type=C, eccentric_load=EM, muscle_mass=MM,
        load_intensity_hint=LM, complexity=XM,
        primary_muscles=["lats", "biceps", "rear_deltoids"],
        category="upper_pull",
    ),
    ExerciseProfile(
        exercise_id="lat_pulldown",
        display_name="Lat Pulldown",
        movement_type=C, eccentric_load=EL, muscle_mass=MM,
        load_intensity_hint=LM, complexity=XL,
        primary_muscles=["lats", "biceps"],
        category="upper_pull",
    ),
    ExerciseProfile(
        exercise_id="bicep_curl",
        display_name="Bicep Curl",
        movement_type=I, eccentric_load=EM, muscle_mass=MS,
        load_intensity_hint=LM, complexity=XL,
        primary_muscles=["biceps", "brachialis"],
        category="upper_pull",
    ),
    ExerciseProfile(
        exercise_id="face_pull",
        display_name="Face Pull",
        movement_type=I, eccentric_load=EL, muscle_mass=MS,
        load_intensity_hint=LL, complexity=XL,
        primary_muscles=["rear_deltoids", "rotator_cuff"],
        category="upper_pull",
    ),

    # ── Upper Pull (continued) ────────────────────────────────────
    ExerciseProfile(
        exercise_id="weighted_chin_up",
        display_name="Weighted Chin-Up",
        movement_type=C, eccentric_load=EM, muscle_mass=MM,
        load_intensity_hint=LM, complexity=XM,
        primary_muscles=["biceps", "lats", "brachialis"],
        category="upper_pull",
    ),
    ExerciseProfile(
        exercise_id="plate_loaded_row_machine",
        display_name="Plate Loaded Row Machine",
        movement_type=C, eccentric_load=EL, muscle_mass=MM,
        load_intensity_hint=LM, complexity=XL,
        primary_muscles=["lats", "rhomboids", "biceps"],
        category="upper_pull",
    ),

    # ── Core ──────────────────────────────────────────────────────
    ExerciseProfile(
        exercise_id="cable_pallof_press",
        display_name="Cable Pallof Press Hold",
        movement_type=I, eccentric_load=EL, muscle_mass=MS,
        load_intensity_hint=LL, complexity=XL,
        primary_muscles=["obliques", "transverse_abdominis"],
        category="core",
    ),
    ExerciseProfile(
        exercise_id="weighted_dead_bug",
        display_name="Weighted Dead Bug",
        movement_type=I, eccentric_load=EL, muscle_mass=MS,
        load_intensity_hint=LL, complexity=XM,
        primary_muscles=["rectus_abdominis", "transverse_abdominis"],
        category="core",
    ),

    # ── Carry ─────────────────────────────────────────────────────
    ExerciseProfile(
        exercise_id="farmers_carry",
        display_name="Farmer's Carry",
        movement_type=C, eccentric_load=EL, muscle_mass=ML,
        load_intensity_hint=LM, complexity=XL,
        primary_muscles=["forearms", "traps", "core", "glutes"],
        category="carry",
    ),

    # ── Lower Body (continued) ────────────────────────────────────
    ExerciseProfile(
        exercise_id="zercher_squat",
        display_name="Barbell Zercher Squat",
        movement_type=C, eccentric_load=EH, muscle_mass=ML,
        load_intensity_hint=LH, complexity=XH,
        primary_muscles=["quadriceps", "glutes", "core", "biceps"],
        category="lower_body",
    ),

    # ── Olympic ───────────────────────────────────────────────────
    ExerciseProfile(
        exercise_id="power_clean",
        display_name="Power Clean",
        movement_type=C, eccentric_load=EL, muscle_mass=ML,
        load_intensity_hint=LH, complexity=XH,
        primary_muscles=["hamstrings", "glutes", "traps", "quadriceps"],
        category="olympic",
    ),
    ExerciseProfile(
        exercise_id="clean_and_jerk",
        display_name="Clean & Jerk",
        movement_type=C, eccentric_load=EL, muscle_mass=ML,
        load_intensity_hint=LH, complexity=XH,
        primary_muscles=["full_body"],
        category="olympic",
    ),
]

# Auto-register all built-in exercises
for _ex in _EXERCISES:
    register_exercise(_ex)
