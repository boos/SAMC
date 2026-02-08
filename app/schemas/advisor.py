"""
Daily advisor schemas.

The advisor combines ACWR (guardrail) + domain readiness (decisor) to
produce an actionable daily recommendation.
"""

from pydantic import BaseModel, Field

from app.schemas.acwr import TrainingStateResponse
from app.schemas.readiness import ReadinessResponse


class DomainGuidance(BaseModel):
    """Per-domain training guidance."""

    domain: str
    readiness: float = Field(
        ..., ge=0.0, le=1.0,
        description="Current readiness level",
    )
    readiness_status: str
    acwr_status: str | None = Field(
        None,
        description="ACWR status for context (None if insufficient data)",
    )
    can_load: bool = Field(
        ...,
        description="Whether this domain can safely receive load today",
    )
    note: str = Field(
        ...,
        description="Brief guidance for this domain",
    )


class VolumeModifier(BaseModel):
    """Volume recommendation relative to normal training."""

    factor: float = Field(
        ..., ge=0.0, le=1.5,
        description="Multiplier: 1.0 = normal, 0.7 = reduce 30%, etc.",
    )
    label: str = Field(
        ...,
        description="One of: full, moderate, reduced, minimal, rest",
    )
    reason: str


class AdvisorResponse(BaseModel):
    """Complete daily advisor output."""

    recommendation: str = Field(
        ...,
        description="One of: train, train_reduced, light_session, rest",
    )
    summary: str = Field(
        ...,
        description="Human-readable 1-2 sentence recommendation",
    )
    volume: VolumeModifier
    domain_guidance: list[DomainGuidance]
    trainable_domains: list[str] = Field(
        ...,
        description="Domains that can receive load today",
    )
    blocked_domains: list[str] = Field(
        ...,
        description="Domains that should be avoided today",
    )
    readiness: ReadinessResponse
    acwr: TrainingStateResponse
