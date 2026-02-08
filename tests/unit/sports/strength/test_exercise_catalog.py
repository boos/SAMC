"""Tests for the exercise catalog."""

from app.sports.strength.exercise_catalog import (
    EXERCISE_CATALOG,
    get_exercise,
)
from app.sports.strength.exercise_profile import (
    Complexity,
    EccentricLoad,
    ExerciseProfile,
    LoadIntensity,
    MovementType,
    MuscleMass,
    compute_exercise_stress_profile,
)


class TestCatalogContents:
    """Verify the built-in exercise catalog is well-formed."""

    def test_catalog_not_empty(self):
        assert len(EXERCISE_CATALOG) >= 20, (
            f"Expected at least 20 exercises, got {len(EXERCISE_CATALOG)}"
        )

    def test_all_entries_are_exercise_profiles(self):
        for eid, profile in EXERCISE_CATALOG.items():
            assert isinstance(profile, ExerciseProfile), (
                f"Catalog entry '{eid}' is {type(profile)}, expected ExerciseProfile"
            )

    def test_all_entries_have_valid_enum_tags(self):
        """Every catalog entry must have valid enum values for all 5 tags."""
        for eid, profile in EXERCISE_CATALOG.items():
            assert isinstance(profile.movement_type, MovementType), (
                f"{eid}: invalid movement_type"
            )
            assert isinstance(profile.eccentric_load, EccentricLoad), (
                f"{eid}: invalid eccentric_load"
            )
            assert isinstance(profile.muscle_mass, MuscleMass), (
                f"{eid}: invalid muscle_mass"
            )
            assert isinstance(profile.load_intensity_hint, LoadIntensity), (
                f"{eid}: invalid load_intensity_hint"
            )
            assert isinstance(profile.complexity, Complexity), (
                f"{eid}: invalid complexity"
            )

    def test_exercise_id_matches_key(self):
        """The exercise_id field must match the catalog dict key."""
        for key, profile in EXERCISE_CATALOG.items():
            assert profile.exercise_id == key, (
                f"Key '{key}' does not match exercise_id '{profile.exercise_id}'"
            )

    def test_no_duplicate_display_names(self):
        """Display names should be unique."""
        names = [p.display_name for p in EXERCISE_CATALOG.values()]
        assert len(names) == len(set(names)), (
            f"Duplicate display names found: "
            f"{[n for n in names if names.count(n) > 1]}"
        )

    def test_all_entries_produce_valid_stress_vectors(self):
        """Every catalog exercise should produce a valid StressVector
        through the mapping function.
        """
        for eid, profile in EXERCISE_CATALOG.items():
            sv = compute_exercise_stress_profile(
                movement_type=profile.movement_type,
                eccentric_load=profile.eccentric_load,
                muscle_mass=profile.muscle_mass,
                load_intensity=profile.load_intensity_hint,
                complexity=profile.complexity,
            )
            for domain in ["metabolic", "neuromuscular", "tendineo", "autonomic", "coordination"]:
                val = getattr(sv, domain)
                assert 0.0 <= val <= 1.0, (
                    f"{eid}: {domain}={val} out of [0, 1]"
                )

    def test_has_lower_body_exercises(self):
        lower = [p for p in EXERCISE_CATALOG.values() if p.category == "lower_body"]
        assert len(lower) >= 5, f"Expected ≥5 lower body exercises, got {len(lower)}"

    def test_has_upper_push_exercises(self):
        push = [p for p in EXERCISE_CATALOG.values() if p.category == "upper_push"]
        assert len(push) >= 3, f"Expected ≥3 upper push exercises, got {len(push)}"

    def test_has_upper_pull_exercises(self):
        pull = [p for p in EXERCISE_CATALOG.values() if p.category == "upper_pull"]
        assert len(pull) >= 3, f"Expected ≥3 upper pull exercises, got {len(pull)}"


class TestCatalogLookup:
    """Test the get_exercise() function."""

    def test_known_exercise_returns_profile(self):
        profile = get_exercise("back_squat")
        assert profile is not None
        assert profile.exercise_id == "back_squat"
        assert profile.display_name == "Back Squat"

    def test_unknown_exercise_returns_none(self):
        assert get_exercise("nonexistent_exercise") is None

    def test_empty_string_returns_none(self):
        assert get_exercise("") is None

    def test_all_catalog_ids_lookup_correctly(self):
        for eid in EXERCISE_CATALOG:
            result = get_exercise(eid)
            assert result is not None, f"get_exercise('{eid}') returned None"
            assert result.exercise_id == eid
