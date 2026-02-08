"""
Daily advisor — combines ACWR + readiness into actionable guidance.

Architecture (three layers):
    1. **ACWR** (guardrail) — detects load spikes / under-exposure
    2. **Readiness** (decisor) — evaluates per-domain recovery state
    3. **Advisor** (consequence) — combines both into a recommendation

The advisor does NOT prescribe specific exercises.  It answers:
    - Should I train today?  (recommendation)
    - At what volume?        (volume modifier)
    - Which domains can handle load?  (domain guidance)

The session selection (which exercises, which weights) remains the
athlete's decision, informed by the advisor's domain guidance.
"""

from __future__ import annotations

import datetime
from typing import Optional

from sqlmodel import Session

from app.samc.acwr import ACWRConfig, compute_acwr
from app.samc.readiness import ReadinessConfig, compute_readiness
from app.schemas.acwr import TrainingStateResponse
from app.schemas.advisor import (
    AdvisorResponse,
    DomainGuidance,
    VolumeModifier,
)
from app.schemas.readiness import DomainReadiness, ReadinessResponse
from app.schemas.stress_vector import DOMAIN_NAMES


# ======================================================================
# Per-domain guidance
# ======================================================================


def _domain_can_load(
    readiness: DomainReadiness,
    acwr_status: str | None,
    domain: str,
) -> tuple[bool, str]:
    """Decide if a domain can receive load today.

    Returns:
        ``(can_load, note)``
    """
    # Structural domains (N, T) are more conservative.
    is_structural = domain in ("neuromuscular", "tendineo")

    # ACWR guardrail: high_spike blocks training on that domain.
    if acwr_status == "high_spike":
        return False, "ACWR in high spike — evitare carico su questo dominio."

    # Readiness-based decision.
    if readiness.status == "fatigued":
        if is_structural:
            return False, "Dominio strutturale ancora affaticato — riposo necessario."
        return False, "Dominio affaticato — evitare carico diretto."

    if readiness.status == "partial":
        if is_structural and acwr_status == "spike":
            return False, "Recovery parziale + spike ACWR strutturale — prudenza."
        return True, "Recovery parziale — carico moderato possibile."

    if readiness.status == "recovered":
        return True, "Dominio recuperato — pronto per carico pieno."

    # no_data
    return True, "Nessun dato recente — procedi normalmente."


def _compute_domain_guidance(
    readiness: ReadinessResponse,
    acwr: TrainingStateResponse,
) -> list[DomainGuidance]:
    """Build per-domain guidance by combining readiness + ACWR."""
    guidance = []

    for domain in DOMAIN_NAMES:
        dr: DomainReadiness = getattr(readiness.readiness, domain)
        acwr_domain = getattr(acwr.acwr, domain)
        acwr_status = acwr_domain.status if acwr_domain.has_sufficient_history else None

        can_load, note = _domain_can_load(dr, acwr_status, domain)

        guidance.append(DomainGuidance(
            domain=domain,
            readiness=dr.readiness,
            readiness_status=dr.status,
            acwr_status=acwr_status,
            can_load=can_load,
            note=note,
        ))

    return guidance


# ======================================================================
# Volume recommendation
# ======================================================================


def _compute_volume(
    readiness: ReadinessResponse,
    acwr: TrainingStateResponse,
    guidance: list[DomainGuidance],
) -> VolumeModifier:
    """Determine volume modifier from overall state."""
    # Count blocked structural domains.
    structural_blocked = sum(
        1 for g in guidance
        if g.domain in ("neuromuscular", "tendineo") and not g.can_load
    )

    # If both structural domains are blocked → rest.
    if structural_blocked == 2:
        return VolumeModifier(
            factor=0.0, label="rest",
            reason="Entrambi i domini strutturali (N+T) necessitano riposo.",
        )

    # If one structural domain blocked → minimal.
    if structural_blocked == 1:
        return VolumeModifier(
            factor=0.3, label="minimal",
            reason="Un dominio strutturale affaticato — sessione leggera.",
        )

    # ACWR-based adjustment.
    gs = acwr.global_status
    if gs == "high_spike":
        return VolumeModifier(
            factor=0.3, label="minimal",
            reason="ACWR in high spike — sessione molto leggera.",
        )
    if gs == "spike":
        return VolumeModifier(
            factor=0.7, label="reduced",
            reason="ACWR in zona spike — ridurre volume del 30%.",
        )

    # Readiness-based adjustment.
    overall = readiness.overall_readiness
    if overall < 0.5:
        return VolumeModifier(
            factor=0.5, label="reduced",
            reason="Readiness bassa — ridurre volume.",
        )
    if overall < 0.85:
        return VolumeModifier(
            factor=0.8, label="moderate",
            reason="Recovery parziale — volume moderato.",
        )

    return VolumeModifier(
        factor=1.0, label="full",
        reason="Recuperato — volume pieno.",
    )


# ======================================================================
# Recommendation
# ======================================================================


def _compute_recommendation(
    volume: VolumeModifier,
    guidance: list[DomainGuidance],
) -> tuple[str, str]:
    """Determine recommendation label and summary.

    Returns:
        ``(recommendation, summary)``
    """
    trainable = [g for g in guidance if g.can_load]
    blocked = [g for g in guidance if not g.can_load]

    if volume.label == "rest":
        return (
            "rest",
            "Riposo consigliato — i domini strutturali necessitano recovery.",
        )

    if volume.label == "minimal":
        blocked_names = ", ".join(g.domain for g in blocked)
        return (
            "light_session",
            f"Sessione leggera consigliata — evitare carico su {blocked_names}.",
        )

    if volume.label == "reduced":
        return (
            "train_reduced",
            "Allenamento possibile con volume ridotto.",
        )

    if volume.label == "moderate":
        return (
            "train_reduced",
            "Allenamento possibile con volume moderato — recovery parziale.",
        )

    # Full
    if not blocked:
        return (
            "train",
            "Tutti i domini recuperati — allenamento pieno possibile.",
        )

    blocked_names = ", ".join(g.domain for g in blocked)
    return (
        "train",
        f"Allenamento pieno possibile — attenzione a {blocked_names}.",
    )


# ======================================================================
# Main entry point
# ======================================================================


def compute_daily_advice(
    session: Session,
    user_id: int,
    as_of: datetime.datetime,
    acwr_config: Optional[ACWRConfig] = None,
    readiness_config: Optional[ReadinessConfig] = None,
) -> AdvisorResponse:
    """Compute the daily training advice.

    Combines ACWR (guardrail) + domain readiness (decisor) into
    an actionable recommendation with per-domain guidance.

    Args:
        session: Database session.
        user_id: User ID.
        as_of: Reference datetime (typically now).
        acwr_config: Optional ACWR config override.
        readiness_config: Optional readiness config override.

    Returns:
        :class:`AdvisorResponse` with recommendation, volume,
        domain guidance, and underlying ACWR + readiness data.
    """
    # Layer 1: ACWR (guardrail).
    acwr_state = compute_acwr(session, user_id, as_of.date(), acwr_config)

    # Layer 2: Readiness (decisor).
    readiness_state = compute_readiness(
        session, user_id, as_of, readiness_config,
    )

    # Layer 3: Advisor (consequence).
    guidance = _compute_domain_guidance(readiness_state, acwr_state)
    volume = _compute_volume(readiness_state, acwr_state, guidance)
    recommendation, summary = _compute_recommendation(volume, guidance)

    trainable = [g.domain for g in guidance if g.can_load]
    blocked = [g.domain for g in guidance if not g.can_load]

    return AdvisorResponse(
        recommendation=recommendation,
        summary=summary,
        volume=volume,
        domain_guidance=guidance,
        trainable_domains=trainable,
        blocked_domains=blocked,
        readiness=readiness_state,
        acwr=acwr_state,
    )
