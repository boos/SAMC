"""
5-domain stress vector schema.

The StressVector is the fundamental unit of load measurement in SAMC.
Every sport and every training session is characterized by stress across
five physiological domains:

- Metabolic: cardiovascular / energy system stress
- Neuromuscular: CNS / motor unit recruitment stress
- Tendineo: tendon / connective tissue stress
- Autonomic: autonomic nervous system stress / recovery cost
- Coordination: motor learning / skill coordination stress
"""

from __future__ import annotations

from pydantic import BaseModel, Field

DOMAIN_NAMES = ["metabolic", "neuromuscular", "tendineo", "autonomic", "coordination", ]


class StressVector(BaseModel):
    """5-domain stress vector. Profile values normalised 0.0–1.0."""

    metabolic: float = Field(0.0, ge=0.0, le=1.0, description="Metabolic / cardiovascular / energy system stress", )
    neuromuscular: float = Field(0.0, ge=0.0, le=1.0, description="Neuromuscular / CNS / motor unit recruitment "
                                                                  "stress", )
    tendineo: float = Field(0.0, ge=0.0, le=1.0, description="Tendinous / connective tissue stress", )
    autonomic: float = Field(0.0, ge=0.0, le=1.0, description="Autonomic nervous system stress / recovery cost", )
    coordination: float = Field(0.0, ge=0.0, le=1.0, description="Motor learning / skill coordination stress", )

    # ------------------------------------------------------------------
    # Arithmetic helpers
    # ------------------------------------------------------------------

    def scaled(self, factor: float) -> StressVector:
        """Return a new vector with all components multiplied by *factor*.

        Components are clamped to [0.0, 1.0] — this is intended for
        producing *profile-level* vectors.  For accumulated loads that
        may exceed 1.0 per domain, use :meth:`scaled_unclamped`.
        """
        return StressVector(metabolic=min(max(self.metabolic * factor, 0.0), 1.0),
                            neuromuscular=min(max(self.neuromuscular * factor, 0.0), 1.0),
                            tendineo=min(max(self.tendineo * factor, 0.0), 1.0),
                            autonomic=min(max(self.autonomic * factor, 0.0), 1.0),
                            coordination=min(max(self.coordination * factor, 0.0), 1.0), )

    def scaled_unclamped(self, factor: float) -> LoadVector:
        """Return a :class:`LoadVector` (unclamped) by multiplying each
        component by *factor*.  Used for session load computation where
        accumulated values may exceed 1.0.
        """
        return LoadVector(metabolic=self.metabolic * factor, neuromuscular=self.neuromuscular * factor,
                          tendineo=self.tendineo * factor, autonomic=self.autonomic * factor,
                          coordination=self.coordination * factor, )

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def max_component(self) -> tuple[str, float]:
        """Return ``(domain_name, value)`` of the highest component."""
        components = { name: getattr(self, name) for name in DOMAIN_NAMES }
        name = max(components, key=components.get)  # type: ignore[arg-type]
        return name, components[name]

    def as_list(self) -> list[float]:
        """Return as ordered list ``[met, neu, ten, aut, coo]``."""
        return [getattr(self, name) for name in DOMAIN_NAMES]

    @classmethod
    def zero(cls) -> StressVector:
        """Return a zero vector."""
        return cls()


class LoadVector(BaseModel):
    """Unclamped version of :class:`StressVector` used for accumulated
    session loads.  Individual domain values **can** exceed 1.0.
    """

    metabolic: float = Field(0.0, ge=0.0)
    neuromuscular: float = Field(0.0, ge=0.0)
    tendineo: float = Field(0.0, ge=0.0)
    autonomic: float = Field(0.0, ge=0.0)
    coordination: float = Field(0.0, ge=0.0)

    def add(self, other: LoadVector) -> LoadVector:
        """Element-wise addition (for daily/window accumulation)."""
        return LoadVector(metabolic=self.metabolic + other.metabolic,
                          neuromuscular=self.neuromuscular + other.neuromuscular,
                          tendineo=self.tendineo + other.tendineo, autonomic=self.autonomic + other.autonomic,
                          coordination=self.coordination + other.coordination, )

    def max_component(self) -> tuple[str, float]:
        """Return ``(domain_name, value)`` of the highest component."""
        components = { name: getattr(self, name) for name in DOMAIN_NAMES }
        name = max(components, key=components.get)  # type: ignore[arg-type]
        return name, components[name]

    def as_list(self) -> list[float]:
        """Return as ordered list ``[met, neu, ten, aut, coo]``."""
        return [getattr(self, name) for name in DOMAIN_NAMES]

    @classmethod
    def zero(cls) -> LoadVector:
        """Return a zero vector."""
        return cls()

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> LoadVector:
        """Create from a dict (e.g. from SQL aggregation results)."""
        return cls(**{ name: data.get(name, 0.0) for name in DOMAIN_NAMES })
