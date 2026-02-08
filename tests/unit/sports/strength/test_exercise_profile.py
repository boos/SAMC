"""Tests for the exercise stress profile mapping function."""

import pytest

from app.sports.strength.exercise_profile import (
    Complexity,
    EccentricLoad,
    LoadIntensity,
    MovementType,
    MuscleMass,
    compute_exercise_stress_profile,
)


# ======================================================================
# Helpers
# ======================================================================


def _profile(**kwargs):
    """Short-hand to call compute_exercise_stress_profile with defaults."""
    defaults = dict(
        movement_type=MovementType.COMPOUND,
        eccentric_load=EccentricLoad.MEDIUM,
        muscle_mass=MuscleMass.MEDIUM,
        load_intensity=LoadIntensity.MODERATE,
        complexity=Complexity.LOW,
    )
    defaults.update(kwargs)
    return compute_exercise_stress_profile(**defaults)


# ======================================================================
# Archetype smoke tests
# ======================================================================


class TestArchetypes:
    """Verify that well-known exercise archetypes produce expected
    relative domain magnitudes.
    """

    def test_back_squat_archetype(self):
        """Heavy compound, high eccentric, large muscle mass → high N, T, A."""
        sv = compute_exercise_stress_profile(
            movement_type=MovementType.COMPOUND,
            eccentric_load=EccentricLoad.HIGH,
            muscle_mass=MuscleMass.LARGE,
            load_intensity=LoadIntensity.HEAVY,
            complexity=Complexity.MEDIUM,
        )
        assert sv.neuromuscular >= 0.90, f"N={sv.neuromuscular}"
        assert sv.tendineo >= 0.80, f"T={sv.tendineo}"
        assert sv.metabolic >= 0.70, f"M={sv.metabolic}"
        assert sv.autonomic >= 0.70, f"A={sv.autonomic}"
        assert sv.coordination >= 0.20, f"C={sv.coordination}"

    def test_lateral_raise_archetype(self):
        """Light isolation, low eccentric, small muscle → all low."""
        sv = compute_exercise_stress_profile(
            movement_type=MovementType.ISOLATION,
            eccentric_load=EccentricLoad.LOW,
            muscle_mass=MuscleMass.SMALL,
            load_intensity=LoadIntensity.LIGHT,
            complexity=Complexity.LOW,
        )
        assert sv.neuromuscular <= 0.35, f"N={sv.neuromuscular}"
        assert sv.tendineo <= 0.25, f"T={sv.tendineo}"
        assert sv.metabolic <= 0.25, f"M={sv.metabolic}"
        assert sv.autonomic <= 0.30, f"A={sv.autonomic}"
        assert sv.coordination <= 0.15, f"C={sv.coordination}"

    def test_olympic_lift_archetype(self):
        """Heavy compound, low eccentric, large muscle, high complexity."""
        sv = compute_exercise_stress_profile(
            movement_type=MovementType.COMPOUND,
            eccentric_load=EccentricLoad.LOW,
            muscle_mass=MuscleMass.LARGE,
            load_intensity=LoadIntensity.HEAVY,
            complexity=Complexity.HIGH,
        )
        # High N and A (heavy compound), high C (olympic), low T (low ecc)
        assert sv.neuromuscular >= 0.70, f"N={sv.neuromuscular}"
        assert sv.tendineo <= 0.50, f"T={sv.tendineo}"
        assert sv.coordination >= 0.70, f"C={sv.coordination}"

    def test_nordic_curl_archetype(self):
        """Isolation, HIGH eccentric, medium muscle → very high T."""
        sv = compute_exercise_stress_profile(
            movement_type=MovementType.ISOLATION,
            eccentric_load=EccentricLoad.HIGH,
            muscle_mass=MuscleMass.MEDIUM,
            load_intensity=LoadIntensity.MODERATE,
            complexity=Complexity.LOW,
        )
        # T should be high due to eccentric despite being isolation
        assert sv.tendineo >= 0.60, f"T={sv.tendineo}"
        # N should be moderate (isolation but high eccentric adds some)
        assert sv.neuromuscular >= 0.30, f"N={sv.neuromuscular}"


# ======================================================================
# Clamping and boundary tests
# ======================================================================


class TestBoundaries:
    """Verify that all outputs are properly clamped to [0, 1]."""

    def test_all_maximal_inputs_clamped(self):
        """Even the most extreme combination should not exceed 1.0."""
        sv = compute_exercise_stress_profile(
            movement_type=MovementType.COMPOUND,
            eccentric_load=EccentricLoad.HIGH,
            muscle_mass=MuscleMass.LARGE,
            load_intensity=LoadIntensity.HEAVY,
            complexity=Complexity.HIGH,
        )
        for domain in ["metabolic", "neuromuscular", "tendineo", "autonomic", "coordination"]:
            val = getattr(sv, domain)
            assert 0.0 <= val <= 1.0, f"{domain}={val} out of [0, 1]"

    def test_all_minimal_inputs_non_negative(self):
        """The weakest combination should still produce non-negative values."""
        sv = compute_exercise_stress_profile(
            movement_type=MovementType.ISOLATION,
            eccentric_load=EccentricLoad.LOW,
            muscle_mass=MuscleMass.SMALL,
            load_intensity=LoadIntensity.LIGHT,
            complexity=Complexity.LOW,
        )
        for domain in ["metabolic", "neuromuscular", "tendineo", "autonomic", "coordination"]:
            val = getattr(sv, domain)
            assert val >= 0.0, f"{domain}={val} is negative"
            # Should also be > 0 because of base values
            assert val > 0.0, f"{domain}={val} is zero (base missing?)"

    @pytest.mark.parametrize("mt", list(MovementType))
    @pytest.mark.parametrize("el", list(EccentricLoad))
    @pytest.mark.parametrize("mm", list(MuscleMass))
    @pytest.mark.parametrize("li", list(LoadIntensity))
    @pytest.mark.parametrize("cx", list(Complexity))
    def test_all_combinations_in_range(self, mt, el, mm, li, cx):
        """Exhaustively check that every possible tag combination stays
        within [0, 1] for all domains.
        """
        sv = compute_exercise_stress_profile(mt, el, mm, li, cx)
        for domain in ["metabolic", "neuromuscular", "tendineo", "autonomic", "coordination"]:
            val = getattr(sv, domain)
            assert 0.0 <= val <= 1.0, (
                f"{domain}={val} for ({mt}, {el}, {mm}, {li}, {cx})"
            )


# ======================================================================
# Comparative / isolation tests
# ======================================================================


class TestComparisons:
    """Verify that changing a single tag moves the expected domain."""

    def test_compound_higher_N_than_isolation(self):
        """Compound should produce higher N than isolation, all else equal."""
        compound = _profile(movement_type=MovementType.COMPOUND)
        isolation = _profile(movement_type=MovementType.ISOLATION)
        assert compound.neuromuscular > isolation.neuromuscular

    def test_compound_higher_A_than_isolation(self):
        """Compound should produce higher A than isolation, all else equal."""
        compound = _profile(movement_type=MovementType.COMPOUND)
        isolation = _profile(movement_type=MovementType.ISOLATION)
        assert compound.autonomic > isolation.autonomic

    def test_high_eccentric_higher_T_than_low(self):
        """High eccentric should produce higher T than low, all else equal."""
        high = _profile(eccentric_load=EccentricLoad.HIGH)
        low = _profile(eccentric_load=EccentricLoad.LOW)
        assert high.tendineo > low.tendineo

    def test_high_eccentric_higher_T_than_medium(self):
        medium = _profile(eccentric_load=EccentricLoad.MEDIUM)
        high = _profile(eccentric_load=EccentricLoad.HIGH)
        assert high.tendineo > medium.tendineo

    def test_large_muscle_higher_M_than_small(self):
        """Large muscle mass should produce higher M than small."""
        large = _profile(muscle_mass=MuscleMass.LARGE)
        small = _profile(muscle_mass=MuscleMass.SMALL)
        assert large.metabolic > small.metabolic

    def test_large_muscle_higher_A_than_small(self):
        """Large muscle mass should produce higher A (recovery cost)."""
        large = _profile(muscle_mass=MuscleMass.LARGE)
        small = _profile(muscle_mass=MuscleMass.SMALL)
        assert large.autonomic > small.autonomic

    def test_heavy_higher_N_than_light(self):
        """Heavy load intensity should produce higher N."""
        heavy = _profile(load_intensity=LoadIntensity.HEAVY)
        light = _profile(load_intensity=LoadIntensity.LIGHT)
        assert heavy.neuromuscular > light.neuromuscular

    def test_heavy_higher_T_than_light(self):
        """Heavy load intensity should produce higher T."""
        heavy = _profile(load_intensity=LoadIntensity.HEAVY)
        light = _profile(load_intensity=LoadIntensity.LIGHT)
        assert heavy.tendineo > light.tendineo

    def test_high_complexity_higher_C_than_low(self):
        """High complexity should produce much higher C."""
        high = _profile(complexity=Complexity.HIGH)
        low = _profile(complexity=Complexity.LOW)
        assert high.coordination > low.coordination
        # The difference should be substantial
        assert high.coordination - low.coordination >= 0.5

    def test_complexity_does_not_affect_N(self):
        """Changing complexity alone should not change N."""
        high = _profile(complexity=Complexity.HIGH)
        low = _profile(complexity=Complexity.LOW)
        assert high.neuromuscular == low.neuromuscular

    def test_muscle_mass_does_not_affect_T(self):
        """Changing muscle mass alone should not change T."""
        large = _profile(muscle_mass=MuscleMass.LARGE)
        small = _profile(muscle_mass=MuscleMass.SMALL)
        assert large.tendineo == small.tendineo
