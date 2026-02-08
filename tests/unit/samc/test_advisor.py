"""
Unit tests for the daily advisor module.

Tests the combination of ACWR (guardrail) + readiness (decisor)
into actionable training recommendations.
"""

import pytest

from app.samc.advisor import (
    _compute_domain_guidance,
    _compute_recommendation,
    _compute_volume,
    _domain_can_load,
)
from app.schemas.acwr import ACWRVector, DomainACWR, TrainingStateResponse
from app.schemas.advisor import DomainGuidance, VolumeModifier
from app.schemas.readiness import (
    DomainReadiness,
    ReadinessResponse,
    ReadinessVector,
)
from app.schemas.stress_vector import DOMAIN_NAMES, LoadVector


# ======================================================================
# Helpers
# ======================================================================


def _make_domain_readiness(
    readiness: float = 1.0,
    status: str = "recovered",
    hours: float | None = None,
) -> DomainReadiness:
    return DomainReadiness(
        readiness=readiness,
        hours_since_load=hours,
        residual_fatigue=max(0, 1.0 - readiness),
        status=status,
        tau_hours=72.0,
    )


def _make_readiness_response(
    overrides: dict[str, DomainReadiness] | None = None,
    overall: float = 1.0,
    overall_status: str = "recovered",
    bottleneck: str | None = None,
) -> ReadinessResponse:
    defaults = {d: _make_domain_readiness() for d in DOMAIN_NAMES}
    if overrides:
        defaults.update(overrides)
    return ReadinessResponse(
        readiness=ReadinessVector(**defaults),
        overall_readiness=overall,
        overall_status=overall_status,
        bottleneck_domain=bottleneck,
        hours_since_last_session=48.0,
        context_note="Test",
    )


def _make_domain_acwr(
    value: float | None = 1.0,
    status: str = "in_range",
    sufficient: bool = True,
) -> DomainACWR:
    return DomainACWR(
        value=value,
        status=status,
        acute_load=1000.0,
        chronic_load=1000.0,
        has_sufficient_history=sufficient,
    )


def _make_acwr_response(
    overrides: dict[str, DomainACWR] | None = None,
    global_status: str = "in_range",
    structural_status: str = "structural_ok",
) -> TrainingStateResponse:
    defaults = {d: _make_domain_acwr() for d in DOMAIN_NAMES}
    if overrides:
        defaults.update(overrides)
    return TrainingStateResponse(
        acute_load=LoadVector.zero(),
        chronic_load=LoadVector.zero(),
        acwr=ACWRVector(**defaults),
        global_status=global_status,
        structural_status=structural_status,
        context_note="Test",
        days_of_data=10,
    )


# ======================================================================
# _domain_can_load
# ======================================================================


class TestDomainCanLoad:
    """Test per-domain load permission logic."""

    def test_recovered_no_acwr_issue(self):
        dr = _make_domain_readiness(readiness=0.9, status="recovered")
        can, note = _domain_can_load(dr, "in_range", "metabolic")
        assert can is True
        assert "recuperato" in note

    def test_fatigued_blocks(self):
        dr = _make_domain_readiness(readiness=0.3, status="fatigued")
        can, note = _domain_can_load(dr, "in_range", "metabolic")
        assert can is False
        assert "affaticato" in note.lower() or "fatigue" in note.lower()

    def test_fatigued_structural_blocks_with_structural_note(self):
        dr = _make_domain_readiness(readiness=0.3, status="fatigued")
        can, note = _domain_can_load(dr, "in_range", "neuromuscular")
        assert can is False
        assert "strutturale" in note.lower()

    def test_acwr_high_spike_blocks(self):
        dr = _make_domain_readiness(readiness=0.9, status="recovered")
        can, note = _domain_can_load(dr, "high_spike", "metabolic")
        assert can is False
        assert "ACWR" in note

    def test_partial_allows_loading(self):
        dr = _make_domain_readiness(readiness=0.6, status="partial")
        can, note = _domain_can_load(dr, "in_range", "metabolic")
        assert can is True
        assert "moderato" in note

    def test_partial_structural_with_spike_blocks(self):
        """Partial N/T + ACWR spike → blocked (conservative)."""
        dr = _make_domain_readiness(readiness=0.6, status="partial")
        can, note = _domain_can_load(dr, "spike", "neuromuscular")
        assert can is False
        assert "prudenza" in note.lower()

    def test_no_data_allows(self):
        dr = _make_domain_readiness(readiness=1.0, status="no_data")
        can, note = _domain_can_load(dr, None, "coordination")
        assert can is True


# ======================================================================
# _compute_domain_guidance
# ======================================================================


class TestComputeDomainGuidance:
    """Test domain guidance assembly."""

    def test_all_recovered_all_trainable(self):
        readiness = _make_readiness_response()
        acwr = _make_acwr_response()
        guidance = _compute_domain_guidance(readiness, acwr)
        assert len(guidance) == 5
        assert all(g.can_load for g in guidance)

    def test_fatigued_domain_blocked(self):
        readiness = _make_readiness_response(
            overrides={"neuromuscular": _make_domain_readiness(0.3, "fatigued", 12.0)},
            overall=0.7, overall_status="partial",
            bottleneck="neuromuscular",
        )
        acwr = _make_acwr_response()
        guidance = _compute_domain_guidance(readiness, acwr)
        neu_g = next(g for g in guidance if g.domain == "neuromuscular")
        assert neu_g.can_load is False
        # Others should still be trainable.
        others = [g for g in guidance if g.domain != "neuromuscular"]
        assert all(g.can_load for g in others)


# ======================================================================
# _compute_volume
# ======================================================================


class TestComputeVolume:
    """Test volume modifier computation."""

    def test_all_good_full_volume(self):
        readiness = _make_readiness_response()
        acwr = _make_acwr_response()
        guidance = _compute_domain_guidance(readiness, acwr)
        vol = _compute_volume(readiness, acwr, guidance)
        assert vol.label == "full"
        assert vol.factor == 1.0

    def test_both_structural_blocked_rest(self):
        readiness = _make_readiness_response(
            overrides={
                "neuromuscular": _make_domain_readiness(0.3, "fatigued", 6.0),
                "tendineo": _make_domain_readiness(0.3, "fatigued", 6.0),
            },
            overall=0.5, overall_status="fatigued",
        )
        acwr = _make_acwr_response()
        guidance = _compute_domain_guidance(readiness, acwr)
        vol = _compute_volume(readiness, acwr, guidance)
        assert vol.label == "rest"
        assert vol.factor == 0.0

    def test_one_structural_blocked_minimal(self):
        readiness = _make_readiness_response(
            overrides={
                "neuromuscular": _make_domain_readiness(0.3, "fatigued", 12.0),
            },
            overall=0.7, overall_status="partial",
        )
        acwr = _make_acwr_response()
        guidance = _compute_domain_guidance(readiness, acwr)
        vol = _compute_volume(readiness, acwr, guidance)
        assert vol.label == "minimal"
        assert vol.factor == 0.3

    def test_acwr_high_spike_minimal(self):
        readiness = _make_readiness_response()
        acwr = _make_acwr_response(global_status="high_spike")
        guidance = _compute_domain_guidance(readiness, acwr)
        vol = _compute_volume(readiness, acwr, guidance)
        assert vol.label == "minimal"

    def test_acwr_spike_reduced(self):
        readiness = _make_readiness_response()
        acwr = _make_acwr_response(global_status="spike")
        guidance = _compute_domain_guidance(readiness, acwr)
        vol = _compute_volume(readiness, acwr, guidance)
        assert vol.label == "reduced"
        assert vol.factor == 0.7

    def test_low_readiness_reduced(self):
        readiness = _make_readiness_response(
            overall=0.45, overall_status="fatigued",
        )
        acwr = _make_acwr_response()
        guidance = _compute_domain_guidance(readiness, acwr)
        vol = _compute_volume(readiness, acwr, guidance)
        assert vol.label == "reduced"

    def test_moderate_readiness_moderate_volume(self):
        readiness = _make_readiness_response(
            overall=0.7, overall_status="partial",
        )
        acwr = _make_acwr_response()
        guidance = _compute_domain_guidance(readiness, acwr)
        vol = _compute_volume(readiness, acwr, guidance)
        assert vol.label == "moderate"
        assert vol.factor == 0.8


# ======================================================================
# _compute_recommendation
# ======================================================================


class TestComputeRecommendation:
    """Test recommendation generation."""

    def test_rest_recommendation(self):
        vol = VolumeModifier(factor=0.0, label="rest", reason="test")
        guidance = [
            DomainGuidance(
                domain=d, readiness=0.3, readiness_status="fatigued",
                acwr_status="in_range", can_load=False, note="test",
            )
            for d in DOMAIN_NAMES
        ]
        rec, summary = _compute_recommendation(vol, guidance)
        assert rec == "rest"
        assert "Riposo" in summary

    def test_light_session_recommendation(self):
        vol = VolumeModifier(factor=0.3, label="minimal", reason="test")
        guidance = [
            DomainGuidance(
                domain=d, readiness=0.9, readiness_status="recovered",
                acwr_status="in_range", can_load=(d != "neuromuscular"),
                note="test",
            )
            for d in DOMAIN_NAMES
        ]
        rec, summary = _compute_recommendation(vol, guidance)
        assert rec == "light_session"
        assert "neuromuscular" in summary

    def test_train_reduced_recommendation(self):
        vol = VolumeModifier(factor=0.7, label="reduced", reason="test")
        guidance = [
            DomainGuidance(
                domain=d, readiness=0.7, readiness_status="partial",
                acwr_status="in_range", can_load=True, note="test",
            )
            for d in DOMAIN_NAMES
        ]
        rec, summary = _compute_recommendation(vol, guidance)
        assert rec == "train_reduced"

    def test_full_train_recommendation(self):
        vol = VolumeModifier(factor=1.0, label="full", reason="test")
        guidance = [
            DomainGuidance(
                domain=d, readiness=0.95, readiness_status="recovered",
                acwr_status="in_range", can_load=True, note="test",
            )
            for d in DOMAIN_NAMES
        ]
        rec, summary = _compute_recommendation(vol, guidance)
        assert rec == "train"
        assert "pieno" in summary.lower()

    def test_full_volume_with_blocked_domain_mentioned(self):
        vol = VolumeModifier(factor=1.0, label="full", reason="test")
        guidance = [
            DomainGuidance(
                domain=d, readiness=0.95 if d != "coordination" else 0.3,
                readiness_status="recovered" if d != "coordination" else "fatigued",
                acwr_status="in_range",
                can_load=(d != "coordination"),
                note="test",
            )
            for d in DOMAIN_NAMES
        ]
        rec, summary = _compute_recommendation(vol, guidance)
        assert rec == "train"
        assert "coordination" in summary


# ======================================================================
# Integration: combined logic
# ======================================================================


class TestAdvisorCombinedLogic:
    """Test how ACWR and readiness interact."""

    def test_acwr_spike_overrides_good_readiness(self):
        """Even with full readiness, ACWR high_spike on a domain blocks it."""
        readiness = _make_readiness_response()
        acwr = _make_acwr_response(
            overrides={"neuromuscular": _make_domain_acwr(1.6, "high_spike")},
        )
        guidance = _compute_domain_guidance(readiness, acwr)
        neu_g = next(g for g in guidance if g.domain == "neuromuscular")
        assert neu_g.can_load is False

    def test_good_acwr_doesnt_override_bad_readiness(self):
        """Good ACWR doesn't override fatigued readiness."""
        readiness = _make_readiness_response(
            overrides={"tendineo": _make_domain_readiness(0.3, "fatigued", 12.0)},
        )
        acwr = _make_acwr_response()
        guidance = _compute_domain_guidance(readiness, acwr)
        ten_g = next(g for g in guidance if g.domain == "tendineo")
        assert ten_g.can_load is False

    def test_insufficient_acwr_data_with_good_readiness_allows(self):
        """No ACWR data but good readiness → allow training."""
        readiness = _make_readiness_response()
        acwr = _make_acwr_response(
            overrides={
                d: _make_domain_acwr(None, "insufficient_history", False)
                for d in DOMAIN_NAMES
            },
            global_status="insufficient_data",
        )
        guidance = _compute_domain_guidance(readiness, acwr)
        assert all(g.can_load for g in guidance)

    def test_both_structural_fatigued_rest(self):
        """Both N and T fatigued → rest regardless of ACWR."""
        readiness = _make_readiness_response(
            overrides={
                "neuromuscular": _make_domain_readiness(0.2, "fatigued", 6.0),
                "tendineo": _make_domain_readiness(0.3, "fatigued", 6.0),
            },
            overall=0.5,
        )
        acwr = _make_acwr_response()
        guidance = _compute_domain_guidance(readiness, acwr)
        vol = _compute_volume(readiness, acwr, guidance)
        rec, _ = _compute_recommendation(vol, guidance)
        assert rec == "rest"

    def test_typical_48h_post_training(self):
        """48h after a heavy session: M+C recovered, A partial, N+T partial."""
        readiness = _make_readiness_response(
            overrides={
                "metabolic": _make_domain_readiness(0.9, "recovered", 48.0),
                "coordination": _make_domain_readiness(0.9, "recovered", 48.0),
                "autonomic": _make_domain_readiness(0.7, "partial", 48.0),
                "neuromuscular": _make_domain_readiness(0.6, "partial", 48.0),
                "tendineo": _make_domain_readiness(0.55, "partial", 48.0),
            },
            overall=0.72, overall_status="partial",
            bottleneck="tendineo",
        )
        acwr = _make_acwr_response()
        guidance = _compute_domain_guidance(readiness, acwr)
        vol = _compute_volume(readiness, acwr, guidance)

        # Should allow training but with moderate volume.
        assert all(g.can_load for g in guidance)
        assert vol.label == "moderate"
