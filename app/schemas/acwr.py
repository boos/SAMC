"""
ACWR (Acute:Chronic Workload Ratio) vector schemas.

The ACWR is a **monitoring and context** tool, not a deterministic decision mechanism.  It does not close the
micro-cycle, does not predict injuries, and does not automatically block training.

Status labels are *operational categories*, not absolute truths:

- ``underexposed``       — ACWR < 0.8
- ``in_range``           — 0.8 <= ACWR <= 1.3
- ``spike``              — 1.3 < ACWR <= 1.5
- ``high_spike``         — ACWR > 1.5
- ``insufficient_history`` — chronic load below minimum threshold
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.stress_vector import LoadVector


class DomainACWR(BaseModel):
    """ACWR state for a single physiological domain."""

    value: Optional[float] = Field(None, description="ACWR ratio (None if insufficient history)")
    status: str = Field(..., description=("One of: underexposed, in_range, spike, "
                                          "high_spike, insufficient_history"), )
    acute_load: float = Field(..., description="Acute window load for this domain")
    chronic_load: float = Field(..., description="Chronic weekly average load for this domain")
    has_sufficient_history: bool = Field(..., description="Whether chronic load exceeds the minimum threshold", )


class ACWRVector(BaseModel):
    """Per-domain ACWR with individual state."""

    metabolic: DomainACWR
    neuromuscular: DomainACWR
    tendineo: DomainACWR
    autonomic: DomainACWR
    coordination: DomainACWR


class TrainingStateResponse(BaseModel):
    """Complete training state returned by the analytics endpoint.

    ``global_status`` uses weighted aggregation (not pure worst-domain).
    ``structural_status`` reflects the state of the structural domains
    (Neuromuscolare + Tendineo) which drive micro-cycle progression.
    ``context_note`` is a human-readable interpretive note.
    """

    acute_load: LoadVector
    chronic_load: LoadVector
    acwr: ACWRVector
    global_status: str = Field(..., description="Weighted aggregation across all domains")
    structural_status: str = Field(..., description="State of structural domains (N + T): "
                                                    "structural_ok, structural_caution, structural_alert", )
    context_note: str = Field(..., description="Human-readable interpretive note")
    days_of_data: int = Field(..., description="Number of session-days in the chronic window")
