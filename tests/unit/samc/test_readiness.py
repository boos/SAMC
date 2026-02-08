"""
Unit tests for domain readiness model.

Tests the exponential decay recovery model, per-domain readiness
computation, overall readiness aggregation, and status labelling.
"""

import math

import pytest

from app.samc.readiness import (
    DEFAULT_READINESS_CONFIG,
    ReadinessConfig,
    _compute_domain_readiness,
    _compute_overall_readiness,
    _generate_readiness_note,
    _label_readiness,
)
from app.schemas.readiness import DomainReadiness, ReadinessVector


# ======================================================================
# Helpers
# ======================================================================


def _make_readiness(
    readiness: float = 1.0,
    status: str = "recovered",
    hours: float | None = None,
    fatigue: float = 0.0,
    tau: float = 72.0,
) -> DomainReadiness:
    return DomainReadiness(
        readiness=readiness,
        hours_since_load=hours,
        residual_fatigue=fatigue,
        status=status,
        tau_hours=tau,
    )


def _make_vector(**overrides) -> ReadinessVector:
    """Build a ReadinessVector with defaults (all recovered)."""
    defaults = {d: _make_readiness() for d in [
        "metabolic", "neuromuscular", "tendineo",
        "autonomic", "coordination",
    ]}
    defaults.update(overrides)
    return ReadinessVector(**defaults)


# ======================================================================
# _label_readiness
# ======================================================================


class TestLabelReadiness:
    """Test readiness status labelling."""

    @pytest.mark.parametrize("value,expected", [
        (0.0, "fatigued"),
        (0.25, "fatigued"),
        (0.49, "fatigued"),
        (0.5, "partial"),
        (0.6, "partial"),
        (0.84, "partial"),
        (0.85, "recovered"),
        (0.9, "recovered"),
        (1.0, "recovered"),
    ])
    def test_thresholds(self, value, expected):
        assert _label_readiness(value) == expected


# ======================================================================
# _compute_domain_readiness
# ======================================================================


class TestComputeDomainReadiness:
    """Test per-domain readiness computation."""

    def test_no_sessions_returns_no_data(self):
        """No sessions → readiness 1.0, status no_data."""
        dr = _compute_domain_readiness(
            "neuromuscular", session_loads=[], tau=72.0,
            reference_load=1000.0,
        )
        assert dr.readiness == 1.0
        assert dr.status == "no_data"
        assert dr.hours_since_load is None
        assert dr.residual_fatigue == 0.0

    def test_just_trained_high_fatigue(self):
        """Session 0 hours ago → very low readiness."""
        dr = _compute_domain_readiness(
            "neuromuscular",
            session_loads=[(0.0, 1000.0)],
            tau=72.0,
            reference_load=1000.0,
        )
        # fatigue = 1000 * exp(0) / 1000 = 1.0 → readiness ≈ 0.0
        assert dr.readiness == 0.0
        assert dr.status == "fatigued"
        assert dr.hours_since_load == 0.0

    def test_one_tau_elapsed(self):
        """After 1 tau, fatigue ≈ 37% of initial → readiness ≈ 0.63."""
        tau = 72.0
        dr = _compute_domain_readiness(
            "neuromuscular",
            session_loads=[(tau, 1000.0)],
            tau=tau,
            reference_load=1000.0,
        )
        expected_fatigue = math.exp(-1)  # ≈ 0.368
        expected_readiness = 1.0 - expected_fatigue
        assert abs(dr.readiness - expected_readiness) < 0.01
        assert dr.status == "partial"

    def test_two_tau_elapsed(self):
        """After 2 tau, fatigue ≈ 13.5% → readiness ≈ 0.865."""
        tau = 72.0
        dr = _compute_domain_readiness(
            "neuromuscular",
            session_loads=[(tau * 2, 1000.0)],
            tau=tau,
            reference_load=1000.0,
        )
        expected_fatigue = math.exp(-2)  # ≈ 0.135
        expected_readiness = 1.0 - expected_fatigue
        assert abs(dr.readiness - expected_readiness) < 0.01
        assert dr.status == "recovered"

    def test_five_tau_fully_recovered(self):
        """After 5 tau, fatigue ≈ 0.7% → essentially recovered."""
        tau = 72.0
        dr = _compute_domain_readiness(
            "neuromuscular",
            session_loads=[(tau * 5, 1000.0)],
            tau=tau,
            reference_load=1000.0,
        )
        assert dr.readiness >= 0.99
        assert dr.status == "recovered"

    def test_superposition_two_sessions(self):
        """Two sessions accumulate fatigue."""
        tau = 72.0
        # Session 1: 24h ago, load 1000
        # Session 2: 48h ago, load 1000
        dr = _compute_domain_readiness(
            "neuromuscular",
            session_loads=[(24.0, 1000.0), (48.0, 1000.0)],
            tau=tau,
            reference_load=1000.0,
        )
        f1 = 1000 * math.exp(-24 / tau) / 1000
        f2 = 1000 * math.exp(-48 / tau) / 1000
        expected_readiness = max(0, 1 - (f1 + f2))
        assert abs(dr.readiness - expected_readiness) < 0.01
        assert dr.hours_since_load == 24.0  # Most recent

    def test_heavier_session_more_fatigue(self):
        """Heavier load produces more fatigue at same time."""
        tau = 72.0
        dr_light = _compute_domain_readiness(
            "neuromuscular",
            session_loads=[(24.0, 500.0)],
            tau=tau,
            reference_load=1000.0,
        )
        dr_heavy = _compute_domain_readiness(
            "neuromuscular",
            session_loads=[(24.0, 2000.0)],
            tau=tau,
            reference_load=1000.0,
        )
        assert dr_heavy.readiness < dr_light.readiness

    def test_metabolic_recovers_faster_than_tendon(self):
        """Same load and time → metabolic (tau=36) recovers faster than tendon (tau=120)."""
        dr_met = _compute_domain_readiness(
            "metabolic",
            session_loads=[(48.0, 1000.0)],
            tau=36.0,
            reference_load=1000.0,
        )
        dr_ten = _compute_domain_readiness(
            "tendineo",
            session_loads=[(48.0, 1000.0)],
            tau=120.0,
            reference_load=1000.0,
        )
        assert dr_met.readiness > dr_ten.readiness

    def test_zero_reference_load_fallback(self):
        """With zero reference load, uses self-normalisation."""
        dr = _compute_domain_readiness(
            "coordination",
            session_loads=[(24.0, 100.0)],
            tau=36.0,
            reference_load=0.0,
        )
        # Should produce some readiness value without division by zero.
        assert 0.0 <= dr.readiness <= 1.0

    def test_negative_hours_clamped_to_zero(self):
        """Negative hours_ago (shouldn't happen) are clamped to 0."""
        dr = _compute_domain_readiness(
            "metabolic",
            session_loads=[(-5.0, 1000.0)],
            tau=36.0,
            reference_load=1000.0,
        )
        # Treated as 0 hours ago → full fatigue.
        assert dr.readiness == 0.0

    def test_readiness_clamped_at_zero(self):
        """With extreme fatigue, readiness doesn't go below 0."""
        dr = _compute_domain_readiness(
            "neuromuscular",
            session_loads=[(0.0, 5000.0)],
            tau=72.0,
            reference_load=1000.0,
        )
        assert dr.readiness == 0.0


# ======================================================================
# Domain-specific tau values
# ======================================================================


class TestDomainTauValues:
    """Verify default tau values match physiology."""

    def test_tau_ordering(self):
        """M, C < A < N < T."""
        cfg = DEFAULT_READINESS_CONFIG
        assert cfg.tau["metabolic"] < cfg.tau["autonomic"]
        assert cfg.tau["coordination"] < cfg.tau["autonomic"]
        assert cfg.tau["autonomic"] < cfg.tau["neuromuscular"]
        assert cfg.tau["neuromuscular"] < cfg.tau["tendineo"]

    def test_metabolic_and_coordination_equal(self):
        cfg = DEFAULT_READINESS_CONFIG
        assert cfg.tau["metabolic"] == cfg.tau["coordination"]

    def test_tendon_slowest(self):
        cfg = DEFAULT_READINESS_CONFIG
        assert cfg.tau["tendineo"] == max(cfg.tau.values())


# ======================================================================
# Overall readiness
# ======================================================================


class TestOverallReadiness:
    """Test weighted overall readiness aggregation."""

    def test_all_recovered(self):
        vector = _make_vector()
        overall, status, bottleneck = _compute_overall_readiness(
            vector, DEFAULT_READINESS_CONFIG.readiness_weights,
        )
        assert overall == 1.0
        assert status == "recovered"

    def test_all_no_data(self):
        vector = _make_vector(**{
            d: _make_readiness(status="no_data")
            for d in ["metabolic", "neuromuscular", "tendineo",
                       "autonomic", "coordination"]
        })
        overall, status, bottleneck = _compute_overall_readiness(
            vector, DEFAULT_READINESS_CONFIG.readiness_weights,
        )
        assert status == "no_data"
        assert bottleneck is None

    def test_structural_bottleneck_weighted_heavily(self):
        """If N is fatigued, overall should be significantly pulled down."""
        vector = _make_vector(
            neuromuscular=_make_readiness(readiness=0.3, status="fatigued", hours=12.0, fatigue=0.7),
        )
        overall, status, bottleneck = _compute_overall_readiness(
            vector, DEFAULT_READINESS_CONFIG.readiness_weights,
        )
        assert overall < 0.85  # Not "recovered"
        assert bottleneck == "neuromuscular"

    def test_coordination_bottleneck_low_impact(self):
        """If C is fatigued but all others recovered, overall barely affected."""
        vector = _make_vector(
            coordination=_make_readiness(readiness=0.3, status="fatigued", hours=6.0, fatigue=0.7),
        )
        overall, status, bottleneck = _compute_overall_readiness(
            vector, DEFAULT_READINESS_CONFIG.readiness_weights,
        )
        # Coordination weight is 0.2, others are 1.0+0.6+0.3+1.0 = 2.9
        # Overall ≈ (1*1 + 1*1 + 0.6*1 + 0.3*1 + 0.2*0.3) / (1+1+0.6+0.3+0.2) ≈ 0.955
        assert overall > 0.9
        assert bottleneck == "coordination"

    def test_bottleneck_is_lowest_domain(self):
        vector = _make_vector(
            tendineo=_make_readiness(readiness=0.4, status="fatigued", hours=24.0, fatigue=0.6),
            autonomic=_make_readiness(readiness=0.6, status="partial", hours=24.0, fatigue=0.4),
        )
        _, _, bottleneck = _compute_overall_readiness(
            vector, DEFAULT_READINESS_CONFIG.readiness_weights,
        )
        assert bottleneck == "tendineo"


# ======================================================================
# Context note generation
# ======================================================================


class TestReadinessNote:
    """Test human-readable note generation."""

    def test_all_no_data(self):
        vector = _make_vector(**{
            d: _make_readiness(status="no_data")
            for d in ["metabolic", "neuromuscular", "tendineo",
                       "autonomic", "coordination"]
        })
        note = _generate_readiness_note(vector, "no_data", None, None)
        assert "Nessun dato" in note

    def test_all_recovered(self):
        vector = _make_vector()
        note = _generate_readiness_note(vector, "recovered", None, 96.0)
        assert "recuperati" in note or "pronto" in note

    def test_fatigued_domains_mentioned(self):
        vector = _make_vector(
            neuromuscular=_make_readiness(readiness=0.3, status="fatigued", hours=12.0, fatigue=0.7),
        )
        note = _generate_readiness_note(
            vector, "fatigued", "neuromuscular", 12.0,
        )
        assert "neuromuscular" in note
        assert "affaticati" in note or "Bottleneck" in note

    def test_structural_bottleneck_highlighted(self):
        vector = _make_vector(
            tendineo=_make_readiness(readiness=0.4, status="fatigued", hours=24.0, fatigue=0.6),
        )
        note = _generate_readiness_note(
            vector, "partial", "tendineo", 24.0,
        )
        assert "Bottleneck strutturale" in note
        assert "tendineo" in note


# ======================================================================
# Recovery timeline comparisons
# ======================================================================


class TestRecoveryTimelines:
    """Verify that domain recovery ordering matches physiology."""

    def test_at_48h_metabolic_much_more_recovered_than_tendon(self):
        """At 48h post-session: metabolic much more recovered than tendon."""
        dr_met = _compute_domain_readiness(
            "metabolic",
            session_loads=[(48.0, 1000.0)],
            tau=36.0,
            reference_load=1000.0,
        )
        dr_ten = _compute_domain_readiness(
            "tendineo",
            session_loads=[(48.0, 1000.0)],
            tau=120.0,
            reference_load=1000.0,
        )
        # At 48h: metabolic (tau=36) ≈ 0.74, tendon (tau=120) ≈ 0.33
        assert dr_met.readiness > 0.7
        assert dr_ten.readiness < 0.4
        assert dr_met.readiness > dr_ten.readiness + 0.3

    def test_at_72h_neuromuscular_partial_tendon_still_behind(self):
        """At 72h: neuromuscular ≈ 1 tau → partial. Tendon < 1 tau → more fatigued."""
        dr_neu = _compute_domain_readiness(
            "neuromuscular",
            session_loads=[(72.0, 1000.0)],
            tau=72.0,
            reference_load=1000.0,
        )
        dr_ten = _compute_domain_readiness(
            "tendineo",
            session_loads=[(72.0, 1000.0)],
            tau=120.0,
            reference_load=1000.0,
        )
        assert dr_neu.readiness > dr_ten.readiness

    def test_recovery_ordering_at_48h(self):
        """At 48h, recovery order should be: M=C > A > N > T."""
        loads = [(48.0, 1000.0)]
        ref = 1000.0
        cfg = DEFAULT_READINESS_CONFIG
        results = {}
        for d in ["metabolic", "coordination", "autonomic",
                   "neuromuscular", "tendineo"]:
            results[d] = _compute_domain_readiness(
                d, loads, cfg.tau[d], ref,
            ).readiness

        assert results["metabolic"] == results["coordination"]
        assert results["metabolic"] > results["autonomic"]
        assert results["autonomic"] > results["neuromuscular"]
        assert results["neuromuscular"] > results["tendineo"]


# ======================================================================
# ReadinessConfig
# ======================================================================


class TestReadinessConfig:
    """Test config object."""

    def test_default_config_valid(self):
        cfg = DEFAULT_READINESS_CONFIG
        assert len(cfg.tau) == 5
        assert all(v > 0 for v in cfg.tau.values())
        assert all(v > 0 for v in cfg.readiness_weights.values())

    def test_custom_config(self):
        cfg = ReadinessConfig(
            tau={"metabolic": 24, "neuromuscular": 48, "tendineo": 96,
                 "autonomic": 36, "coordination": 24},
        )
        assert cfg.tau["neuromuscular"] == 48
