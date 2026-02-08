"""
Domain readiness — per-domain recovery model.

This module computes how recovered each physiological domain is based on
recent training history.  Unlike the ACWR (which tracks load ratios over
weeks), readiness models the **short-term recovery state** — hours to
days after training.

Model
-----
Each training session deposits a load on each domain.  The residual
fatigue from that load decays exponentially:

    fatigue_from_session(t) = load × exp(-t / tau)

where ``t`` is hours elapsed and ``tau`` is the domain-specific recovery
time constant.  Fatigue from multiple sessions is summed (superposition).

Total residual fatigue is normalised against a reference load to produce
a 0-1 readiness score:

    readiness = max(0, 1 - total_fatigue / reference_load)

Recovery time constants (tau, in hours) are based on physiological
literature:

    M (metabolic):      36h  — glycogen resynthesis, cardiovascular
    C (coordination):   36h  — motor pattern consolidation
    A (autonomic):      60h  — ANS balance, HRV recovery
    N (neuromuscular):  72h  — CNS fatigue, motor unit recovery
    T (tendineo):      120h  — collagen turnover, tendon adaptation

These are heuristic starting points, not empirically validated constants.
The relative ordering (M,C < A < N < T) is well established in the
literature (Hiscock et al. 2019; Damas et al. 2015).

Design choices
--------------
1. **Superposition** — fatigue from multiple sessions sums.  A session
   2 days ago AND another 4 days ago both contribute residual fatigue.
2. **Exponential decay** — simple, one-parameter model per domain.
   Captures the essential dynamics without overfitting.
3. **Reference load normalisation** — readiness is relative to the
   athlete's own chronic load (the "expected" session).  This makes
   the 0-1 scale meaningful regardless of training level.
4. **Lookback window** — only sessions within 5×tau contribute
   meaningfully (exp(-5) ≈ 0.007, negligible).
"""

from __future__ import annotations

import datetime
import math
from typing import Optional

from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db.repositories.training_session import TrainingSessionRepository
from app.schemas.readiness import (
    DomainReadiness,
    ReadinessResponse,
    ReadinessVector,
)
from app.schemas.stress_vector import DOMAIN_NAMES

# ======================================================================
# Configuration
# ======================================================================

# Domain recovery time constants (hours).
_DEFAULT_TAU: dict[str, float] = {
    "metabolic": 36.0,
    "neuromuscular": 72.0,
    "tendineo": 120.0,
    "autonomic": 60.0,
    "coordination": 36.0,
}

# Readiness thresholds for status labels.
_READINESS_THRESHOLDS: list[tuple[str, float, float]] = [
    ("fatigued", 0.0, 0.5),
    ("partial", 0.5, 0.85),
    ("recovered", 0.85, float("inf")),
]

# Domain weights for overall readiness (same philosophy as ACWR).
_READINESS_WEIGHTS: dict[str, float] = {
    "neuromuscular": 1.0,
    "tendineo": 1.0,
    "autonomic": 0.6,
    "metabolic": 0.3,
    "coordination": 0.2,
}

# How many tau multiples to look back (exp(-5) ≈ 0.007).
_LOOKBACK_TAUS = 5.0


class ReadinessConfig(BaseModel):
    """Configuration for the readiness computation."""

    tau: dict[str, float] = Field(
        default_factory=lambda: dict(_DEFAULT_TAU),
    )
    readiness_weights: dict[str, float] = Field(
        default_factory=lambda: dict(_READINESS_WEIGHTS),
    )
    lookback_taus: float = Field(default=_LOOKBACK_TAUS)


DEFAULT_READINESS_CONFIG = ReadinessConfig()


# ======================================================================
# Status labelling
# ======================================================================


def _label_readiness(value: float) -> str:
    """Map a readiness float to its status label."""
    for label, low, high in _READINESS_THRESHOLDS:
        if low <= value < high:
            return label
    return "recovered"


# ======================================================================
# Core computation
# ======================================================================


def _compute_domain_readiness(
    domain: str,
    session_loads: list[tuple[float, float]],
    tau: float,
    reference_load: float,
) -> DomainReadiness:
    """Compute readiness for a single domain.

    Args:
        domain: Domain name.
        session_loads: List of ``(hours_ago, load_value)`` tuples.
            ``hours_ago`` is positive (e.g. 48.0 means 2 days ago).
            ``load_value`` is the domain-specific load from that session.
        tau: Recovery time constant for this domain (hours).
        reference_load: Chronic average load per session for this domain.
            Used to normalise fatigue into a 0-1 readiness scale.

    Returns:
        :class:`DomainReadiness` for this domain.
    """
    if not session_loads:
        return DomainReadiness(
            readiness=1.0,
            hours_since_load=None,
            residual_fatigue=0.0,
            status="no_data",
            tau_hours=tau,
        )

    # Sum residual fatigue from all recent sessions.
    total_fatigue = 0.0
    min_hours = None

    for hours_ago, load in session_loads:
        if hours_ago < 0:
            hours_ago = 0.0
        decay = math.exp(-hours_ago / tau)
        total_fatigue += load * decay
        if min_hours is None or hours_ago < min_hours:
            min_hours = hours_ago

    # Normalise against reference load.
    if reference_load > 0:
        normalised_fatigue = total_fatigue / reference_load
    else:
        # No chronic reference — use raw fatigue vs single session.
        # Fall back to a simple heuristic: if total_fatigue > 0,
        # readiness depends purely on decay.
        normalised_fatigue = total_fatigue / max(total_fatigue, 1.0)

    readiness = max(0.0, min(1.0, 1.0 - normalised_fatigue))

    return DomainReadiness(
        readiness=round(readiness, 3),
        hours_since_load=round(min_hours, 1) if min_hours is not None else None,
        residual_fatigue=round(normalised_fatigue, 3),
        status=_label_readiness(readiness),
        tau_hours=tau,
    )


def _compute_overall_readiness(
    readiness_vector: ReadinessVector,
    weights: dict[str, float],
) -> tuple[float, str, str | None]:
    """Compute weighted overall readiness and find bottleneck.

    Returns:
        ``(overall_readiness, overall_status, bottleneck_domain)``
    """
    total_weight = 0.0
    weighted_sum = 0.0
    min_readiness = 1.0
    bottleneck = None
    has_data = False

    for domain in DOMAIN_NAMES:
        dr: DomainReadiness = getattr(readiness_vector, domain)
        if dr.status == "no_data":
            continue
        has_data = True
        w = weights.get(domain, 0.3)
        weighted_sum += dr.readiness * w
        total_weight += w

        if dr.readiness < min_readiness:
            min_readiness = dr.readiness
            bottleneck = domain

    if not has_data or total_weight == 0:
        return 1.0, "no_data", None

    overall = weighted_sum / total_weight
    return round(overall, 3), _label_readiness(overall), bottleneck


def _generate_readiness_note(
    readiness_vector: ReadinessVector,
    overall_status: str,
    bottleneck: str | None,
    hours_since_last: float | None,
) -> str:
    """Generate a human-readable readiness note."""
    parts: list[str] = []

    # No data
    no_data_domains = [
        d for d in DOMAIN_NAMES
        if getattr(readiness_vector, d).status == "no_data"
    ]
    if len(no_data_domains) == len(DOMAIN_NAMES):
        return "Nessun dato di allenamento recente — pronto per allenarsi."

    # Fatigued domains
    fatigued = [
        d for d in DOMAIN_NAMES
        if getattr(readiness_vector, d).status == "fatigued"
    ]
    if fatigued:
        names = ", ".join(fatigued)
        parts.append(f"Domini ancora affaticati: {names}")

    # Partially recovered
    partial = [
        d for d in DOMAIN_NAMES
        if getattr(readiness_vector, d).status == "partial"
    ]
    if partial:
        names = ", ".join(partial)
        parts.append(f"Recovery parziale su: {names}")

    # Structural bottleneck
    structural = {"neuromuscular", "tendineo"}
    if bottleneck and bottleneck in structural:
        dr = getattr(readiness_vector, bottleneck)
        parts.append(
            f"Bottleneck strutturale: {bottleneck} "
            f"(readiness {dr.readiness:.0%})"
        )

    if not parts:
        return "Tutti i domini recuperati — pronto per allenarsi."

    return ". ".join(parts) + "."


# ======================================================================
# Main entry point
# ======================================================================


def compute_readiness(
    session: Session,
    user_id: int,
    as_of: datetime.datetime,
    config: Optional[ReadinessConfig] = None,
) -> ReadinessResponse:
    """Compute per-domain readiness for a user.

    Args:
        session: Database session.
        user_id: User ID.
        as_of: Reference datetime (typically now, with time of day).
        config: Optional config override.

    Returns:
        :class:`ReadinessResponse` with per-domain readiness.
    """
    cfg = config or DEFAULT_READINESS_CONFIG
    repo = TrainingSessionRepository(session)

    # Determine lookback window — max tau × lookback_taus.
    max_tau = max(cfg.tau.values())
    lookback_hours = max_tau * cfg.lookback_taus
    lookback_start = as_of - datetime.timedelta(hours=lookback_hours)

    # Get all sessions in the lookback window.
    sessions = repo.get_by_user_date_range(
        user_id, lookback_start.date(), as_of.date(),
    )

    # Build per-domain session loads with hours_ago.
    domain_loads: dict[str, list[tuple[float, float]]] = {
        d: [] for d in DOMAIN_NAMES
    }
    _LOAD_COLUMNS = {
        "metabolic": "metabolic_load",
        "neuromuscular": "neuromuscular_load",
        "tendineo": "tendons_load",
        "autonomic": "autonomic_load",
        "coordination": "coordination_load",
    }

    hours_since_last: float | None = None

    for ts in sessions:
        # Approximate session time as noon of the session date.
        session_dt = datetime.datetime.combine(
            ts.date, datetime.time(12, 0),
        )
        hours_ago = (as_of - session_dt).total_seconds() / 3600.0
        if hours_ago < 0:
            continue  # Future session, skip.

        if hours_since_last is None or hours_ago < hours_since_last:
            hours_since_last = hours_ago

        for domain in DOMAIN_NAMES:
            load_val = getattr(ts, _LOAD_COLUMNS[domain])
            if load_val > 0:
                domain_loads[domain].append((hours_ago, load_val))

    # Compute reference load per domain (chronic average per session).
    # Use 28-day window for chronic reference.
    chronic_start = as_of.date() - datetime.timedelta(days=27)
    chronic_sums = repo.sum_load_by_date_range(
        user_id, chronic_start, as_of.date(),
    )
    chronic_session_count = repo.count_by_user_date_range(
        user_id, chronic_start, as_of.date(),
    )
    avg_sessions = max(chronic_session_count, 1)

    reference_loads: dict[str, float] = {
        d: chronic_sums[d] / avg_sessions for d in DOMAIN_NAMES
    }

    # Compute per-domain readiness.
    domain_results: dict[str, DomainReadiness] = {}
    for domain in DOMAIN_NAMES:
        domain_results[domain] = _compute_domain_readiness(
            domain=domain,
            session_loads=domain_loads[domain],
            tau=cfg.tau.get(domain, 48.0),
            reference_load=reference_loads[domain],
        )

    readiness_vector = ReadinessVector(**domain_results)

    # Overall readiness.
    overall, overall_status, bottleneck = _compute_overall_readiness(
        readiness_vector, cfg.readiness_weights,
    )

    # Context note.
    context_note = _generate_readiness_note(
        readiness_vector, overall_status, bottleneck,
        hours_since_last,
    )

    return ReadinessResponse(
        readiness=readiness_vector,
        overall_readiness=overall,
        overall_status=overall_status,
        bottleneck_domain=bottleneck,
        hours_since_last_session=round(hours_since_last, 1) if hours_since_last is not None else None,
        context_note=context_note,
    )
