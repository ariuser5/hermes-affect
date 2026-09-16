"""Inspectable participant-to-participant social influence policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .calculations import (
    calming_factor,
    persistence_buffer,
    pride_pressure,
    tension_pressure,
    trust_support,
)
from .calculations import (
    conflict_risk as calculate_conflict_risk,
)
from .config import AffectConfig
from .events import EventType
from .models import ParticipantRelation, clamp, utc_now
from .parameters import STYLE_LEARNING_RATE, STYLE_SIGNALS

OBSERVED_STYLE_FIELDS = (
    "supportive",
    "playful",
    "confrontational",
    "cooperative",
)

def observe_style(
    relation: ParticipantRelation,
    event_type: EventType,
    *,
    learning_rate: float = STYLE_LEARNING_RATE,
) -> None:
    """Update bounded style estimates without retaining message content."""

    rate = clamp(learning_rate, 0.0, 1.0)
    signals = STYLE_SIGNALS.get(event_type, (0.5, 0.5, 0.5, 0.5))
    for field_name, signal in zip(OBSERVED_STYLE_FIELDS, signals):
        previous = relation.observed_style.get(field_name, 0.5)
        relation.observed_style[field_name] = clamp(previous + rate * (signal - previous), 0.0, 1.0)
    relation.updated_at = utc_now()


@dataclass(frozen=True)
class ParticipantTraits:
    """Public or locally resolved temperament, with no mutable group state."""

    reactivity: float = 0.5
    persistence: float = 0.5
    pride: float = 0.5
    playfulness: float = 0.5
    assertiveness: float = 0.5
    social_influence: float = 0.5
    receptiveness: float = 0.5

    @classmethod
    def from_config(cls, config: AffectConfig) -> ParticipantTraits:
        return cls(**{name: config.traits[name] for name in cls.__dataclass_fields__})


class ParticipantTraitResolver(Protocol):
    def resolve(self, participant_id: str) -> ParticipantTraits: ...


@dataclass
class NeutralTraitResolver:
    traits: dict[str, ParticipantTraits] = field(default_factory=dict)
    neutral: ParticipantTraits = field(default_factory=ParticipantTraits)

    def resolve(self, participant_id: str) -> ParticipantTraits:
        return self.traits.get(participant_id, self.neutral)


@dataclass
class LayeredTraitResolver:
    """Resolve public temperament, then observed behavior, then neutral values."""

    public_signatures: dict[str, ParticipantTraits] = field(default_factory=dict)
    observed_traits: dict[str, ParticipantTraits] = field(default_factory=dict)
    neutral: ParticipantTraits = field(default_factory=ParticipantTraits)

    def resolve(self, participant_id: str) -> ParticipantTraits:
        return (
            self.public_signatures.get(participant_id)
            or self.observed_traits.get(participant_id)
            or self.neutral
        )


@dataclass(frozen=True)
class InfluenceDecision:
    persuasion: float
    calming: float
    conflict_risk: float
    factors: dict[str, float]


def evaluate_influence(
    speaker: ParticipantTraits,
    listener: ParticipantTraits,
    relation: ParticipantRelation,
) -> InfluenceDecision:
    """Return separate, inspectable social policy factors.

    Administrative identity is intentionally absent. A speaker's effect comes
    from assertiveness and social influence; a listener's effective receptivity
    also depends on relationship respect. This keeps influence distinct from
    permission to administer the plugin.
    """

    leadership_tendency = speaker.assertiveness * speaker.social_influence
    effective_receptiveness = (
        listener.receptiveness * max(relation.respect, 0.0) * speaker.social_influence
    )
    trust_support_factor = trust_support(relation.trust)
    tension_pressure_factor = tension_pressure(relation)
    pride_pressure_factor = pride_pressure(
        listener.pride,
        listener.reactivity,
        listener.assertiveness,
    )
    persistence_buffer_factor = persistence_buffer(
        listener.persistence,
        tension_pressure_factor,
    )

    persuasion = clamp(
        leadership_tendency * effective_receptiveness * trust_support_factor
    )
    calming = clamp(
        calming_factor(
            persuasion,
            persistence_buffer_factor,
            tension_pressure_factor,
        )
    )
    conflict_risk_value = clamp(
        calculate_conflict_risk(
            tension_pressure_factor,
            pride_pressure_factor,
            persistence_buffer_factor,
            calming,
        ),
        0.0,
        1.0,
    )
    return InfluenceDecision(
        persuasion=persuasion,
        calming=calming,
        conflict_risk=conflict_risk_value,
        factors={
            "leadership_tendency": leadership_tendency,
            "effective_receptiveness": effective_receptiveness,
            "trust_support": trust_support_factor,
            "tension_pressure": tension_pressure_factor,
            "pride_pressure": pride_pressure_factor,
            "persistence_buffer": persistence_buffer_factor,
        },
    )
