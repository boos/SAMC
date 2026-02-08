"""Tests for the WeightLiftingPlugin with exercise-categorisation-based
load computation.
"""

import pytest
from pydantic import ValidationError

from app.schemas.stress_vector import LoadVector
from app.sports.base import SportPlugin
from app.sports.strength.exercise_profile import (
    Complexity,
    EccentricLoad,
    LoadIntensity,
    MovementType,
    MuscleMass,
)
from app.sports.strength.plugin import (
    WeightLiftingExercise,
    WeightLiftingPlugin,
    WeightLiftingSessionData,
)


@pytest.fixture
def plugin():
    return WeightLiftingPlugin()


# ======================================================================
# Plugin interface compliance
# ======================================================================


class TestPluginInterface:
    """Verify the plugin satisfies the SportPlugin ABC."""

    def test_is_sport_plugin(self, plugin):
        assert isinstance(plugin, SportPlugin)

    def test_sport_id(self, plugin):
        assert plugin.sport_id == "weight_lifting"

    def test_display_name(self, plugin):
        assert plugin.display_name == "Weight Lifting"

    def test_default_stress_profile_valid(self, plugin):
        sv = plugin.default_stress_profile
        for domain in ["metabolic", "neuromuscular", "tendineo", "autonomic", "coordination"]:
            val = getattr(sv, domain)
            assert 0.0 <= val <= 1.0

    def test_session_schema(self, plugin):
        assert plugin.session_schema is WeightLiftingSessionData

    def test_is_not_background(self, plugin):
        assert plugin.is_background is False

    def test_recovery_days_hint(self, plugin):
        assert plugin.recovery_days_hint == 2

    def test_sessions_per_cycle_default(self, plugin):
        assert plugin.sessions_per_cycle_default == 2


# ======================================================================
# Schema validation
# ======================================================================


class TestSchemaValidation:
    """Test WeightLiftingExercise and WeightLiftingSessionData validation."""

    def test_catalog_exercise_valid(self):
        ex = WeightLiftingExercise(
            exercise_id="back_squat", sets=4, reps=6, weight_kg=100, rpe=8.0,
        )
        assert ex.exercise_id == "back_squat"
        assert ex.exercise_name is None

    def test_custom_exercise_valid(self):
        ex = WeightLiftingExercise(
            exercise_name="My Exercise",
            movement_type="compound",
            eccentric_load="high",
            muscle_mass="large",
            load_intensity="heavy",
            complexity="medium",
            sets=3, reps=8, weight_kg=60, rpe=7.0,
        )
        assert ex.exercise_name == "My Exercise"
        assert ex.exercise_id is None

    def test_both_id_and_name_raises(self):
        with pytest.raises(ValidationError, match="exercise_id.*exercise_name"):
            WeightLiftingExercise(
                exercise_id="back_squat",
                exercise_name="Also Named",
                sets=3, reps=8, weight_kg=60, rpe=7.0,
            )

    def test_neither_id_nor_name_raises(self):
        with pytest.raises(ValidationError, match="exercise_id.*exercise_name"):
            WeightLiftingExercise(
                sets=3, reps=8, weight_kg=60, rpe=7.0,
            )

    def test_unknown_exercise_id_raises(self):
        with pytest.raises(ValidationError, match="Unknown exercise_id"):
            WeightLiftingExercise(
                exercise_id="nonexistent_exercise",
                sets=3, reps=8, weight_kg=60, rpe=7.0,
            )

    def test_custom_missing_tags_raises(self):
        with pytest.raises(ValidationError, match="Missing"):
            WeightLiftingExercise(
                exercise_name="My Exercise",
                movement_type="compound",
                # Missing eccentric_load, muscle_mass, load_intensity, complexity
                sets=3, reps=8, weight_kg=60, rpe=7.0,
            )

    def test_session_data_valid(self):
        data = WeightLiftingSessionData(
            exercises=[
                WeightLiftingExercise(
                    exercise_id="back_squat",
                    sets=4, reps=6, weight_kg=100, rpe=8.0,
                ),
            ],
            session_rpe=7.5,
        )
        assert len(data.exercises) == 1
        assert data.session_rpe == 7.5

    def test_session_data_empty_exercises_raises(self):
        with pytest.raises(ValidationError):
            WeightLiftingSessionData(exercises=[])

    def test_session_rpe_optional(self):
        data = WeightLiftingSessionData(
            exercises=[
                WeightLiftingExercise(
                    exercise_id="bench_press",
                    sets=3, reps=10, weight_kg=70, rpe=7.0,
                ),
            ],
        )
        assert data.session_rpe is None


# ======================================================================
# compute_load tests
# ======================================================================


class TestComputeLoad:
    """Test the full compute_load pipeline."""

    def test_single_catalog_exercise(self, plugin):
        """A single catalog exercise should produce a non-zero LoadVector."""
        load = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "back_squat", "sets": 4, "reps": 6,
                 "weight_kg": 100, "rpe": 8.0},
            ]},
            intensity_modifier=1.0,
        )
        assert isinstance(load, LoadVector)
        assert load.neuromuscular > 0
        assert load.tendineo > 0
        assert load.metabolic > 0
        assert load.autonomic > 0
        assert load.coordination > 0

    def test_squat_dominates_neuromuscular(self, plugin):
        """Back squat should produce much higher N than lateral raise."""
        squat_load = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "back_squat", "sets": 4, "reps": 6,
                 "weight_kg": 100, "rpe": 8.0},
            ]},
            intensity_modifier=1.0,
        )
        raise_load = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "lateral_raise", "sets": 3, "reps": 15,
                 "weight_kg": 10, "rpe": 8.0},
            ]},
            intensity_modifier=1.0,
        )
        assert squat_load.neuromuscular > raise_load.neuromuscular * 5

    def test_mixed_session_accumulates(self, plugin):
        """A mixed session should be the sum of individual exercise loads."""
        squat_only = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "back_squat", "sets": 4, "reps": 6,
                 "weight_kg": 100, "rpe": 8.0},
            ]},
            intensity_modifier=1.0,
        )
        bench_only = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "bench_press", "sets": 4, "reps": 8,
                 "weight_kg": 80, "rpe": 7.0},
            ]},
            intensity_modifier=1.0,
        )
        combined = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "back_squat", "sets": 4, "reps": 6,
                 "weight_kg": 100, "rpe": 8.0},
                {"exercise_id": "bench_press", "sets": 4, "reps": 8,
                 "weight_kg": 80, "rpe": 7.0},
            ]},
            intensity_modifier=1.0,
        )
        # Combined should equal sum of individual loads
        assert abs(combined.neuromuscular - (squat_only.neuromuscular + bench_only.neuromuscular)) < 0.01
        assert abs(combined.tendineo - (squat_only.tendineo + bench_only.tendineo)) < 0.01
        assert abs(combined.metabolic - (squat_only.metabolic + bench_only.metabolic)) < 0.01

    def test_custom_exercise(self, plugin):
        """Custom exercise with inline tags should work."""
        load = plugin.compute_load(
            {"exercises": [
                {
                    "exercise_name": "My Custom Press",
                    "movement_type": "compound",
                    "eccentric_load": "medium",
                    "muscle_mass": "medium",
                    "load_intensity": "moderate",
                    "complexity": "low",
                    "sets": 3, "reps": 10, "weight_kg": 40, "rpe": 7.0,
                },
            ]},
            intensity_modifier=1.0,
        )
        assert isinstance(load, LoadVector)
        assert load.neuromuscular > 0

    def test_unknown_exercise_id_raises(self, plugin):
        """Unknown exercise_id should raise during validation."""
        with pytest.raises(Exception, match="Unknown exercise_id"):
            plugin.compute_load(
                {"exercises": [
                    {"exercise_id": "invented_exercise", "sets": 3,
                     "reps": 8, "weight_kg": 60, "rpe": 7.0},
                ]},
                intensity_modifier=1.0,
            )

    def test_rpe_scaling(self, plugin):
        """RPE 10 should produce exactly double the load of RPE 5."""
        load_rpe5 = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "bench_press", "sets": 3, "reps": 10,
                 "weight_kg": 80, "rpe": 5.0},
            ]},
            intensity_modifier=1.0,
        )
        load_rpe10 = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "bench_press", "sets": 3, "reps": 10,
                 "weight_kg": 80, "rpe": 10.0},
            ]},
            intensity_modifier=1.0,
        )
        ratio = load_rpe10.neuromuscular / load_rpe5.neuromuscular
        assert abs(ratio - 2.0) < 0.01, f"Expected ratio 2.0, got {ratio}"

    def test_intensity_modifier_scales(self, plugin):
        """intensity_modifier=2.0 should double all load domains."""
        load_1x = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "deadlift", "sets": 3, "reps": 5,
                 "weight_kg": 120, "rpe": 8.0},
            ]},
            intensity_modifier=1.0,
        )
        load_2x = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "deadlift", "sets": 3, "reps": 5,
                 "weight_kg": 120, "rpe": 8.0},
            ]},
            intensity_modifier=2.0,
        )
        assert abs(load_2x.neuromuscular - load_1x.neuromuscular * 2) < 0.01
        assert abs(load_2x.tendineo - load_1x.tendineo * 2) < 0.01
        assert abs(load_2x.metabolic - load_1x.metabolic * 2) < 0.01

    def test_session_rpe_informational_only(self, plugin):
        """session_rpe should not affect the load calculation."""
        load_no_srpe = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "pull_up", "sets": 4, "reps": 8,
                 "weight_kg": 0, "rpe": 7.0},
            ]},
            intensity_modifier=1.0,
        )
        load_with_srpe = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "pull_up", "sets": 4, "reps": 8,
                 "weight_kg": 0, "rpe": 7.0},
            ],
             "session_rpe": 9.0},
            intensity_modifier=1.0,
        )
        assert load_no_srpe.neuromuscular == load_with_srpe.neuromuscular
        assert load_no_srpe.tendineo == load_with_srpe.tendineo

    def test_zero_weight_produces_zero_load(self, plugin):
        """Weight=0 (bodyweight marker) should produce zero load."""
        load = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "pull_up", "sets": 4, "reps": 8,
                 "weight_kg": 0, "rpe": 7.0},
            ]},
            intensity_modifier=1.0,
        )
        assert load.neuromuscular == 0.0
        assert load.tendineo == 0.0


# ======================================================================
# Comparative / regression tests
# ======================================================================


class TestComparativeLoad:
    """Compare exercise loads to ensure physiological coherence."""

    def test_high_eccentric_exercise_more_T(self, plugin):
        """Romanian deadlift (high ecc) should produce more T than
        hip thrust (low ecc) for comparable tonnage.
        """
        rdl_load = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "romanian_deadlift", "sets": 3, "reps": 10,
                 "weight_kg": 80, "rpe": 7.0},
            ]},
            intensity_modifier=1.0,
        )
        ht_load = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "hip_thrust", "sets": 3, "reps": 10,
                 "weight_kg": 80, "rpe": 7.0},
            ]},
            intensity_modifier=1.0,
        )
        assert rdl_load.tendineo > ht_load.tendineo

    def test_compound_more_N_than_isolation(self, plugin):
        """Barbell row should produce more N per kg than bicep curl."""
        row_load = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "barbell_row", "sets": 3, "reps": 10,
                 "weight_kg": 60, "rpe": 7.0},
            ]},
            intensity_modifier=1.0,
        )
        curl_load = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "bicep_curl", "sets": 3, "reps": 10,
                 "weight_kg": 60, "rpe": 7.0},
            ]},
            intensity_modifier=1.0,
        )
        # Same tonnage, but row is compound → higher N
        assert row_load.neuromuscular > curl_load.neuromuscular

    def test_olympic_lift_high_coordination(self, plugin):
        """Power clean should have significantly higher coordination load
        than bench press for comparable tonnage.
        """
        clean_load = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "power_clean", "sets": 5, "reps": 3,
                 "weight_kg": 80, "rpe": 8.0},
            ]},
            intensity_modifier=1.0,
        )
        bench_load = plugin.compute_load(
            {"exercises": [
                {"exercise_id": "bench_press", "sets": 5, "reps": 3,
                 "weight_kg": 80, "rpe": 8.0},
            ]},
            intensity_modifier=1.0,
        )
        assert clean_load.coordination > bench_load.coordination * 3
