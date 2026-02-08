"""Tests for the vectorial ACWR computation.

These are *pure unit tests* — they test the ACWR functions directly
without hitting the database.  The repository layer is replaced by
pre-computed load dicts.
"""

import pytest

from app.samc.acwr import (
    ACWRConfig,
    DEFAULT_CONFIG,
    _compute_domain_acwr,
    _compute_global_status,
    _compute_structural_status,
    _generate_context_note,
    _label_acwr,
)
from app.schemas.acwr import ACWRVector, DomainACWR


# ======================================================================
# Helpers
# ======================================================================


def _make_domain(
    value: float | None,
    status: str,
    acute: float = 0.0,
    chronic: float = 0.0,
    sufficient: bool = True,
) -> DomainACWR:
    return DomainACWR(
        value=value,
        status=status,
        acute_load=acute,
        chronic_load=chronic,
        has_sufficient_history=sufficient,
    )


def _make_vector(**overrides) -> ACWRVector:
    """Build an ACWRVector with all domains in_range by default."""
    defaults = {
        "metabolic": _make_domain(1.0, "in_range", 9500, 9500),
        "neuromuscular": _make_domain(1.0, "in_range", 12000, 12000),
        "tendineo": _make_domain(1.0, "in_range", 9500, 9500),
        "autonomic": _make_domain(1.0, "in_range", 10000, 10000),
        "coordination": _make_domain(1.0, "in_range", 2900, 2900),
    }
    defaults.update(overrides)
    return ACWRVector(**defaults)


# ======================================================================
# ACWRConfig
# ======================================================================


class TestACWRConfig:
    def test_default_values(self):
        cfg = ACWRConfig()
        assert cfg.acute_days == 7
        assert cfg.chronic_days == 28
        assert cfg.chronic_weeks == 4.0

    def test_chronic_weeks_property(self):
        cfg = ACWRConfig(chronic_days=21)
        assert cfg.chronic_weeks == 3.0

    def test_min_chronic_thresholds_tonnage_scale(self):
        """Thresholds should be in the hundreds (tonnage-based), not < 1."""
        cfg = ACWRConfig()
        for domain, threshold in cfg.min_chronic_thresholds.items():
            assert threshold >= 100.0, (
                f"{domain} threshold {threshold} is too low for tonnage-based loads"
            )

    def test_default_config_singleton(self):
        assert DEFAULT_CONFIG.acute_days == 7
        assert DEFAULT_CONFIG.chronic_days == 28


# ======================================================================
# _label_acwr
# ======================================================================


class TestLabelACWR:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (0.0, "underexposed"),
            (0.5, "underexposed"),
            (0.79, "underexposed"),
            (0.8, "in_range"),
            (1.0, "in_range"),
            (1.29, "in_range"),
            (1.3, "spike"),
            (1.49, "spike"),
            (1.5, "high_spike"),
            (2.0, "high_spike"),
            (5.0, "high_spike"),
        ],
    )
    def test_label_boundaries(self, value, expected):
        assert _label_acwr(value) == expected


# ======================================================================
# _compute_domain_acwr
# ======================================================================


class TestComputeDomainACWR:
    """Test the per-domain ACWR computation with tonnage-scale loads."""

    def test_stable_training_in_range(self):
        """4 weeks of consistent training → ACWR ≈ 1.0."""
        # Acute = 1 week at 12000, chronic = 4 weeks at 12000/week = 48000 total
        d = _compute_domain_acwr(
            domain="neuromuscular",
            acute_sum=12000.0,
            chronic_sum=48000.0,
            chronic_weeks=4.0,
            min_threshold=600.0,
        )
        assert d.has_sufficient_history is True
        assert d.value == 1.0
        assert d.status == "in_range"

    def test_spike_detection(self):
        """Doubling acute load → ACWR = 2.0 → high_spike."""
        d = _compute_domain_acwr(
            domain="neuromuscular",
            acute_sum=24000.0,
            chronic_sum=48000.0,
            chronic_weeks=4.0,
            min_threshold=600.0,
        )
        assert d.has_sufficient_history is True
        assert d.value == 2.0
        assert d.status == "high_spike"

    def test_underexposure(self):
        """Half the acute load → ACWR = 0.5 → underexposed."""
        d = _compute_domain_acwr(
            domain="neuromuscular",
            acute_sum=6000.0,
            chronic_sum=48000.0,
            chronic_weeks=4.0,
            min_threshold=600.0,
        )
        assert d.has_sufficient_history is True
        assert d.value == 0.5
        assert d.status == "underexposed"

    def test_insufficient_history(self):
        """Chronic weekly below threshold → insufficient_history."""
        d = _compute_domain_acwr(
            domain="neuromuscular",
            acute_sum=500.0,
            chronic_sum=1000.0,  # weekly = 250, below 600 threshold
            chronic_weeks=4.0,
            min_threshold=600.0,
        )
        assert d.has_sufficient_history is False
        assert d.value is None
        assert d.status == "insufficient_history"

    def test_zero_chronic_weeks(self):
        """Zero chronic weeks → 0 chronic weekly → insufficient."""
        d = _compute_domain_acwr(
            domain="metabolic",
            acute_sum=1000.0,
            chronic_sum=0.0,
            chronic_weeks=0.0,
            min_threshold=500.0,
        )
        assert d.has_sufficient_history is False
        assert d.status == "insufficient_history"

    def test_zero_loads(self):
        """All zero loads → insufficient history."""
        d = _compute_domain_acwr(
            domain="metabolic",
            acute_sum=0.0,
            chronic_sum=0.0,
            chronic_weeks=4.0,
            min_threshold=500.0,
        )
        assert d.has_sufficient_history is False
        assert d.status == "insufficient_history"

    def test_rounding(self):
        """ACWR value should be rounded to 3 decimal places."""
        d = _compute_domain_acwr(
            domain="tendineo",
            acute_sum=10000.0,
            chronic_sum=36000.0,  # weekly = 9000
            chronic_weeks=4.0,
            min_threshold=500.0,
        )
        assert d.value == 1.111  # 10000/9000 = 1.1111...

    def test_acute_chronic_loads_stored(self):
        """Acute and chronic loads should be available in the result."""
        d = _compute_domain_acwr(
            domain="metabolic",
            acute_sum=9580.0,
            chronic_sum=38320.0,
            chronic_weeks=4.0,
            min_threshold=500.0,
        )
        assert d.acute_load == 9580.0
        assert d.chronic_load == 9580.0  # 38320/4

    def test_typical_session_loads_not_insufficient(self):
        """Realistic training data should NOT be marked insufficient.

        Reference: a typical 3-session week produces N ≈ 12300.
        After 2 weeks, chronic weekly ≈ 12300 which is well above
        the 600 threshold.
        """
        d = _compute_domain_acwr(
            domain="neuromuscular",
            acute_sum=12300.0,
            chronic_sum=24600.0,  # 2 weeks worth
            chronic_weeks=4.0,    # but window is 4 weeks
            min_threshold=600.0,
        )
        # chronic_weekly = 24600/4 = 6150 > 600 → sufficient
        assert d.has_sufficient_history is True


# ======================================================================
# _compute_structural_status
# ======================================================================


class TestStructuralStatus:
    def test_both_in_range(self):
        neu = _make_domain(1.0, "in_range")
        ten = _make_domain(1.0, "in_range")
        assert _compute_structural_status(neu, ten) == "structural_ok"

    def test_one_spike(self):
        neu = _make_domain(1.4, "spike")
        ten = _make_domain(1.0, "in_range")
        assert _compute_structural_status(neu, ten) == "structural_caution"

    def test_one_high_spike(self):
        neu = _make_domain(1.0, "in_range")
        ten = _make_domain(1.8, "high_spike")
        assert _compute_structural_status(neu, ten) == "structural_alert"

    def test_both_high_spike(self):
        neu = _make_domain(2.0, "high_spike")
        ten = _make_domain(1.6, "high_spike")
        assert _compute_structural_status(neu, ten) == "structural_alert"

    def test_both_insufficient(self):
        neu = _make_domain(None, "insufficient_history", sufficient=False)
        ten = _make_domain(None, "insufficient_history", sufficient=False)
        assert _compute_structural_status(neu, ten) == "structural_insufficient_data"

    def test_one_insufficient_one_ok(self):
        """If only one structural domain has data, use that."""
        neu = _make_domain(None, "insufficient_history", sufficient=False)
        ten = _make_domain(1.0, "in_range")
        assert _compute_structural_status(neu, ten) == "structural_ok"

    def test_one_insufficient_one_spike(self):
        neu = _make_domain(1.4, "spike")
        ten = _make_domain(None, "insufficient_history", sufficient=False)
        assert _compute_structural_status(neu, ten) == "structural_caution"

    def test_underexposed_is_ok(self):
        """Underexposure is not caution/alert at structural level."""
        neu = _make_domain(0.5, "underexposed")
        ten = _make_domain(0.6, "underexposed")
        assert _compute_structural_status(neu, ten) == "structural_ok"


# ======================================================================
# _compute_global_status
# ======================================================================


class TestGlobalStatus:
    def test_all_in_range(self):
        v = _make_vector()
        status = _compute_global_status(v, "structural_ok", DEFAULT_CONFIG.domain_weights)
        assert status == "in_range"

    def test_all_insufficient(self):
        insuf = _make_domain(None, "insufficient_history", sufficient=False)
        v = _make_vector(
            metabolic=insuf,
            neuromuscular=insuf,
            tendineo=insuf,
            autonomic=insuf,
            coordination=insuf,
        )
        status = _compute_global_status(v, "structural_insufficient_data", DEFAULT_CONFIG.domain_weights)
        assert status == "insufficient_data"

    def test_structural_alert_veto(self):
        """Structural alert should promote global to at least spike."""
        v = _make_vector(
            neuromuscular=_make_domain(1.8, "high_spike", 20000, 11000),
        )
        status = _compute_global_status(v, "structural_alert", DEFAULT_CONFIG.domain_weights)
        # Even if weighted avg might be in_range, structural veto promotes
        assert status in ("spike", "high_spike")

    def test_structural_caution_veto(self):
        """Structural caution should keep global at least in_range."""
        # All domains underexposed except N which spikes
        v = _make_vector(
            metabolic=_make_domain(0.5, "underexposed", 4000, 8000),
            neuromuscular=_make_domain(1.4, "spike", 16000, 11000),
            tendineo=_make_domain(0.5, "underexposed", 4000, 8000),
            autonomic=_make_domain(0.5, "underexposed", 4000, 8000),
            coordination=_make_domain(0.5, "underexposed", 1500, 3000),
        )
        status = _compute_global_status(v, "structural_caution", DEFAULT_CONFIG.domain_weights)
        # Weighted avg is low (pulled by underexposed), but caution veto
        assert status != "underexposed"

    def test_weighted_average_respects_domain_weights(self):
        """N and T (weight=1.0) should dominate over M and C (weight=0.3/0.2)."""
        v = _make_vector(
            metabolic=_make_domain(2.0, "high_spike", 19000, 9500),
            neuromuscular=_make_domain(1.0, "in_range", 12000, 12000),
            tendineo=_make_domain(1.0, "in_range", 9500, 9500),
            autonomic=_make_domain(1.0, "in_range", 10000, 10000),
            coordination=_make_domain(1.0, "in_range", 2900, 2900),
        )
        # M spikes but has low weight (0.3), N+T dominate
        status = _compute_global_status(v, "structural_ok", DEFAULT_CONFIG.domain_weights)
        assert status == "in_range"


# ======================================================================
# _generate_context_note
# ======================================================================


class TestContextNote:
    def test_all_in_range(self):
        v = _make_vector()
        note = _generate_context_note(v, "structural_ok", "in_range")
        assert "stabile" in note.lower() or "range" in note.lower()

    def test_all_insufficient(self):
        insuf = _make_domain(None, "insufficient_history", sufficient=False)
        v = _make_vector(
            metabolic=insuf,
            neuromuscular=insuf,
            tendineo=insuf,
            autonomic=insuf,
            coordination=insuf,
        )
        note = _generate_context_note(v, "structural_insufficient_data", "insufficient_data")
        assert "insufficienti" in note.lower()

    def test_structural_alert_mentioned(self):
        v = _make_vector(
            neuromuscular=_make_domain(1.8, "high_spike", 20000, 11000),
        )
        note = _generate_context_note(v, "structural_alert", "spike")
        assert "strutturali" in note.lower()

    def test_structural_caution_mentioned(self):
        v = _make_vector(
            tendineo=_make_domain(1.4, "spike", 13000, 9500),
        )
        note = _generate_context_note(v, "structural_caution", "in_range")
        assert "strutturali" in note.lower()

    def test_underexposure_mentioned(self):
        v = _make_vector(
            metabolic=_make_domain(0.3, "underexposed", 3000, 9500),
        )
        note = _generate_context_note(v, "structural_ok", "in_range")
        assert "sotto-esposizione" in note.lower() or "metabolic" in note.lower()

    def test_non_structural_spike_mentioned(self):
        v = _make_vector(
            metabolic=_make_domain(1.6, "high_spike", 15000, 9500),
        )
        note = _generate_context_note(v, "structural_ok", "in_range")
        assert "metabolic" in note.lower()


# ======================================================================
# Integration: threshold calibration sanity checks
# ======================================================================


class TestThresholdCalibration:
    """Verify that the new tonnage-based thresholds work correctly
    with realistic training data.
    """

    def test_one_light_week_is_sufficient(self):
        """A single deload session per week should be enough to cross
        the min_chronic threshold for most domains.
        """
        cfg = ACWRConfig()
        # Deload session: M≈525, N≈746, T≈607, A≈604, C≈172
        # After 4 weeks: chronic_sum = 4 * session, weekly = session
        for domain, deload_load in [
            ("neuromuscular", 746.0),
            ("tendineo", 607.0),
            ("metabolic", 525.0),
            ("autonomic", 604.0),
            ("coordination", 172.0),
        ]:
            chronic_sum = deload_load * 4  # 4 weeks
            d = _compute_domain_acwr(
                domain=domain,
                acute_sum=deload_load,
                chronic_sum=chronic_sum,
                chronic_weeks=4.0,
                min_threshold=cfg.min_chronic_thresholds[domain],
            )
            assert d.has_sufficient_history is True, (
                f"{domain}: deload weekly={deload_load} < threshold="
                f"{cfg.min_chronic_thresholds[domain]}"
            )

    def test_first_week_only_is_insufficient(self):
        """With only 1 session ever (chronic sum spread over 4 weeks),
        chronic weekly should be below threshold for structural domains.
        """
        cfg = ACWRConfig()
        # Single deload session in 28 days → weekly = session / 4
        d = _compute_domain_acwr(
            domain="neuromuscular",
            acute_sum=746.0,
            chronic_sum=746.0,  # only 1 session in 28 days
            chronic_weeks=4.0,
            min_threshold=cfg.min_chronic_thresholds["neuromuscular"],
        )
        # weekly = 746/4 = 186.5, threshold = 600 → insufficient
        assert d.has_sufficient_history is False

    def test_typical_training_produces_valid_acwr(self):
        """4 weeks of typical training → all domains in_range."""
        cfg = ACWRConfig()
        # Typical weekly loads: M≈9500, N≈12300, T≈9500, A≈10400, C≈2900
        weekly_loads = {
            "metabolic": 9500.0,
            "neuromuscular": 12300.0,
            "tendineo": 9500.0,
            "autonomic": 10400.0,
            "coordination": 2900.0,
        }
        for domain, weekly in weekly_loads.items():
            d = _compute_domain_acwr(
                domain=domain,
                acute_sum=weekly,         # 1 week = weekly
                chronic_sum=weekly * 4,   # 4 weeks
                chronic_weeks=4.0,
                min_threshold=cfg.min_chronic_thresholds[domain],
            )
            assert d.has_sufficient_history is True
            assert d.value == 1.0
            assert d.status == "in_range"

    def test_progressive_overload_spike(self):
        """50% volume increase in acute week → spike on structural domains."""
        cfg = ACWRConfig()
        d = _compute_domain_acwr(
            domain="neuromuscular",
            acute_sum=18450.0,          # 12300 * 1.5
            chronic_sum=12300.0 * 4,
            chronic_weeks=4.0,
            min_threshold=cfg.min_chronic_thresholds["neuromuscular"],
        )
        assert d.value == 1.5
        assert d.status == "high_spike"
