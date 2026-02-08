"""
ACWR (Acute:Chronic Workload Ratio) — vectorial computation.

The ACWR is a **monitoring and context** tool in SAMC.  It:

- does **not** close the micro-cycle,
- does **not** substitute domain-level evaluation,
- does **not** causally predict injury risk.

It is used as:

- an indicator of spike or under-exposure,
- an attention signal on load context,
- decision support for modulating stimulus density and timing.

Thresholds are *operational categories*, not absolute truths.

Key design choices
------------------

1. **Per-domain** (not scalar) — avoids masking sport-specific spikes.
2. **Non-universalist labelling** — underexposed / in_range / spike / high_spike / insufficient_history.
3. **Chronic-load minimum threshold** per domain — prevents numerical instability when a sport is new or the athlete
is returning.
4. **Weighted aggregation** (not pure worst-domain) — structural domains (N, T) have priority; A is a modulator; M and C are
   high-tolerance.
5. **Encapsulated time windows** — ready for EWMA migration.
"""

from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db.repositories.training_session import TrainingSessionRepository
from app.schemas.acwr import (ACWRVector, DomainACWR, TrainingStateResponse, )
from app.schemas.stress_vector import DOMAIN_NAMES, LoadVector

# ======================================================================
# Configuration — encapsulated, not hard-coded
# ======================================================================

# Default minimum chronic-load thresholds (per domain).
# Below these values ACWR is marked ``insufficient_history``.
#
# Calibration reference (tonnage-based loads):
#   Typical 3-session week ≈ M:9500  N:12300  T:9500  A:10400  C:2900
#   A single deload session ≈ M:525   N:746    T:607   A:604    C:172
#
# Thresholds set at ~5% of a typical weekly average — low enough to
# activate after 1-2 weeks of even light training, high enough to
# prevent division-by-near-zero instability.
_DEFAULT_MIN_CHRONIC: dict[str, float] = {
    "metabolic": 500.0,
    "neuromuscular": 600.0,
    "tendineo": 500.0,
    "autonomic": 500.0,
    "coordination": 150.0,
}

# Domain weights for global aggregation.
_DEFAULT_DOMAIN_WEIGHTS: dict[str, float] = { "neuromuscular": 1.0,  # structural — max priority
                                              "tendineo": 1.0,  # structural — max priority
                                              "autonomic": 0.6,  # modulator
                                              "metabolic": 0.3,  # high tolerance
                                              "coordination": 0.2,  # high tolerance
                                              }


class ACWRConfig(BaseModel):
    """Configuration for the ACWR computation.

    All parameters are encapsulated here so that:
    - nothing is hard-coded in the computation function,
    - different configs can be injected for testing,
    - future EWMA migration only requires adding a branch on ``method``.
    """

    acute_days: int = Field(7, ge=3, le=14)
    chronic_days: int = Field(28, ge=14, le=56)
    method: str = Field("rolling_average", description="'rolling_average' (MVP) or 'ewma' (future)", )

    min_chronic_thresholds: dict[str, float] = Field(default_factory=lambda: dict(_DEFAULT_MIN_CHRONIC))
    domain_weights: dict[str, float] = Field(default_factory=lambda: dict(_DEFAULT_DOMAIN_WEIGHTS))

    @property
    def chronic_weeks(self) -> float:
        return self.chronic_days / 7.0


# Singleton default config
DEFAULT_CONFIG = ACWRConfig()

# ======================================================================
# Status labelling
# ======================================================================

_THRESHOLDS: list[tuple[str, float, float]] = [("underexposed", 0.0, 0.8), ("in_range", 0.8, 1.3), ("spike", 1.3, 1.5),
                                               ("high_spike", 1.5, float("inf")), ]


def _label_acwr(value: float) -> str:
    """Map an ACWR float to its operational status label."""
    for label, low, high in _THRESHOLDS:
        if low <= value < high:
            return label
    return "high_spike"


# ======================================================================
# Per-domain computation
# ======================================================================


def _compute_domain_acwr(domain: str, acute_sum: float, chronic_sum: float, chronic_weeks: float,
                         min_threshold: float, ) -> DomainACWR:
    """Compute :class:`DomainACWR` for a single domain."""
    chronic_weekly = chronic_sum / chronic_weeks if chronic_weeks > 0 else 0.0

    if chronic_weekly < min_threshold:
        return DomainACWR(value=None, status="insufficient_history", acute_load=round(acute_sum, 4),
                          chronic_load=round(chronic_weekly, 4), has_sufficient_history=False, )

    acwr_value = round(acute_sum / chronic_weekly, 3)
    return DomainACWR(value=acwr_value, status=_label_acwr(acwr_value), acute_load=round(acute_sum, 4),
                      chronic_load=round(chronic_weekly, 4), has_sufficient_history=True, )


# ======================================================================
# Structural status (N + T)
# ======================================================================


def _compute_structural_status(neu: DomainACWR, ten: DomainACWR, ) -> str:
    """Evaluate the combined state of the structural domains."""
    statuses = []
    for d in (neu, ten):
        if d.has_sufficient_history:
            statuses.append(d.status)

    if not statuses:
        return "structural_insufficient_data"

    if any(s == "high_spike" for s in statuses):
        return "structural_alert"
    if any(s == "spike" for s in statuses):
        return "structural_caution"
    return "structural_ok"


# ======================================================================
# Global status — weighted aggregation with structural veto
# ======================================================================


def _compute_global_status(acwr_vector: ACWRVector, structural_status: str, weights: dict[str, float], ) -> str:
    """Compute a weighted global status.

    Only domains with sufficient history participate.
    The structural status can **veto** an otherwise-good global score.
    """
    total_weight = 0.0
    weighted_sum = 0.0

    for domain in DOMAIN_NAMES:
        dacwr: DomainACWR = getattr(acwr_vector, domain)
        if not dacwr.has_sufficient_history or dacwr.value is None:
            continue
        w = weights.get(domain, 0.3)
        weighted_sum += dacwr.value * w
        total_weight += w

    if total_weight == 0:
        return "insufficient_data"

    global_acwr = weighted_sum / total_weight
    base_status = _label_acwr(global_acwr)

    # Structural veto: if structural is alert/caution, global cannot be
    # better than the structural level.
    if structural_status == "structural_alert":
        if base_status in ("underexposed", "in_range", "spike"):
            return "spike"  # promote to at least spike
    elif structural_status == "structural_caution":
        if base_status in ("underexposed", "in_range"):
            return "in_range"  # keep at least in_range (acknowledges attention)

    return base_status


# ======================================================================
# Context note generation
# ======================================================================


def _generate_context_note(acwr_vector: ACWRVector, structural_status: str, global_status: str, ) -> str:
    """Generate a human-readable interpretive note."""
    parts: list[str] = []

    # Check for insufficient data
    insufficient = [d for d in DOMAIN_NAMES if not getattr(acwr_vector, d).has_sufficient_history]
    if len(insufficient) == len(DOMAIN_NAMES):
        return "Dati insufficienti su tutti i domini — continuare ad accumulare sessioni."

    if insufficient:
        names = ", ".join(insufficient)
        parts.append(f"Dati insufficienti su: {names}")

    # Structural commentary
    if structural_status == "structural_alert":
        spiked = []
        for d in ("neuromuscular", "tendineo"):
            dacwr = getattr(acwr_vector, d)
            if dacwr.has_sufficient_history and dacwr.status in ("spike", "high_spike",):
                spiked.append(d)
        names = " e ".join(spiked)
        parts.append(f"Spike sui domini strutturali ({names}) — "
                     "considerare riduzione volume o aumento recovery")
    elif structural_status == "structural_caution":
        parts.append("Attenzione sui domini strutturali — monitorare il prossimo ciclo")

    # Per-domain spikes (non-structural)
    for d in ("metabolic", "autonomic", "coordination"):
        dacwr = getattr(acwr_vector, d)
        if dacwr.has_sufficient_history and dacwr.status in ("spike", "high_spike",):
            parts.append(f"Spike su {d} (ACWR {dacwr.value})")

    # Under-exposure
    underexposed = [d for d in DOMAIN_NAMES if
                    getattr(acwr_vector, d).has_sufficient_history and getattr(acwr_vector, d).status == "underexposed"]
    if underexposed:
        names = ", ".join(underexposed)
        parts.append(f"Sotto-esposizione su: {names}")

    if not parts:
        return "Carico stabile, tutti i domini in range operativo."

    return ". ".join(parts) + "."


# ======================================================================
# Main entry point
# ======================================================================


def compute_acwr(session: Session, user_id: int, as_of_date: datetime.date,
                 config: Optional[ACWRConfig] = None, ) -> TrainingStateResponse:
    """Compute the full vectorial ACWR and training state.

    Args:
        session: Database session.
        user_id: User ID.
        as_of_date: Reference date (typically today).
        config: Optional :class:`ACWRConfig` override (uses
            ``DEFAULT_CONFIG`` if ``None``).

    Returns:
        :class:`TrainingStateResponse` with per-domain ACWR,
        structural status, global status, and context note.
    """
    cfg = config or DEFAULT_CONFIG
    repo = TrainingSessionRepository(session)

    # --- Acute window ---
    acute_start = as_of_date - datetime.timedelta(days=cfg.acute_days - 1)
    acute_sums = repo.sum_load_by_date_range(user_id, acute_start, as_of_date)

    # --- Chronic window ---
    chronic_start = as_of_date - datetime.timedelta(days=cfg.chronic_days - 1)
    chronic_sums = repo.sum_load_by_date_range(user_id, chronic_start, as_of_date)

    # --- Data sufficiency ---
    days_of_data = repo.count_by_user_date_range(user_id, chronic_start, as_of_date)

    # --- Per-domain ACWR ---
    domain_results: dict[str, DomainACWR] = { }
    for domain in DOMAIN_NAMES:
        min_thr = cfg.min_chronic_thresholds.get(domain, 0.1)
        domain_results[domain] = _compute_domain_acwr(domain=domain, acute_sum=acute_sums[domain],
                                                      chronic_sum=chronic_sums[domain], chronic_weeks=cfg.chronic_weeks,
                                                      min_threshold=min_thr, )

    acwr_vector = ACWRVector(**domain_results)

    # --- Structural status (N + T) ---
    structural_status = _compute_structural_status(neu=domain_results["neuromuscular"],
                                                   ten=domain_results["tendineo"], )

    # --- Global status (weighted aggregation + structural veto) ---
    global_status = _compute_global_status(acwr_vector=acwr_vector, structural_status=structural_status,
                                           weights=cfg.domain_weights, )

    # --- Context note ---
    context_note = _generate_context_note(acwr_vector=acwr_vector, structural_status=structural_status,
                                          global_status=global_status, )

    # --- Build response ---
    acute_load = LoadVector.from_dict(acute_sums)
    chronic_load = LoadVector(metabolic=chronic_sums["metabolic"] / cfg.chronic_weeks,
                              neuromuscular=chronic_sums["neuromuscular"] / cfg.chronic_weeks,
                              tendineo=chronic_sums["tendineo"] / cfg.chronic_weeks,
                              autonomic=chronic_sums["autonomic"] / cfg.chronic_weeks,
                              coordination=chronic_sums["coordination"] / cfg.chronic_weeks, )

    return TrainingStateResponse(acute_load=acute_load, chronic_load=chronic_load, acwr=acwr_vector,
                                 global_status=global_status, structural_status=structural_status,
                                 context_note=context_note, days_of_data=days_of_data, )
