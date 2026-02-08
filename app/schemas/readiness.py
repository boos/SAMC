"""
Domain readiness schemas.

Domain readiness models the recovery state of each physiological domain
as a function of time elapsed since last load and load magnitude.

Recovery is modelled as an exponential decay of fatigue:

    fatigue(t) = load × exp(-t / tau)
    readiness(t) = 1 - fatigue_normalised(t)

Where ``tau`` (hours) is the domain-specific recovery time constant:

    M (metabolic):      tau = 36h   (24-48h literature range)
    C (coordination):   tau = 36h   (24-48h, motor learning)
    A (autonomic):      tau = 60h   (48-72h, ANS recovery)
    N (neuromuscular):  tau = 72h   (48-96h, CNS + motor unit)
    T (tendineo):       tau = 120h  (72-168h, connective tissue)

Readiness values are 0.0-1.0 where:
    0.0 = fully fatigued (just trained)
    1.0 = fully recovered (no residual fatigue)
"""

from pydantic import BaseModel, Field


class DomainReadiness(BaseModel):
    """Readiness state for a single physiological domain."""

    readiness: float = Field(
        ..., ge=0.0, le=1.0,
        description="Recovery level 0.0 (fatigued) to 1.0 (recovered)",
    )
    hours_since_load: float | None = Field(
        None,
        description="Hours since last load on this domain (None if no data)",
    )
    residual_fatigue: float = Field(
        ..., ge=0.0,
        description="Normalised residual fatigue (0 = no fatigue)",
    )
    status: str = Field(
        ...,
        description="One of: recovered, partial, fatigued, no_data",
    )
    tau_hours: float = Field(
        ...,
        description="Recovery time constant for this domain (hours)",
    )


class ReadinessVector(BaseModel):
    """Per-domain readiness state."""

    metabolic: DomainReadiness
    neuromuscular: DomainReadiness
    tendineo: DomainReadiness
    autonomic: DomainReadiness
    coordination: DomainReadiness


class ReadinessResponse(BaseModel):
    """Full readiness assessment returned by the readiness endpoint."""

    readiness: ReadinessVector
    overall_readiness: float = Field(
        ..., ge=0.0, le=1.0,
        description="Weighted overall readiness (structural domains weighted higher)",
    )
    overall_status: str = Field(
        ...,
        description="One of: ready, partial, fatigued, no_data",
    )
    bottleneck_domain: str | None = Field(
        None,
        description="Domain with the lowest readiness (the recovery bottleneck)",
    )
    hours_since_last_session: float | None = Field(
        None,
        description="Hours since the most recent training session",
    )
    context_note: str = Field(
        ...,
        description="Human-readable interpretive note",
    )
