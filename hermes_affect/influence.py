"""Inspectable participant-to-participant social influence policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .config import AffectConfig
from .events import EventType
from .models import ParticipantRelation, clamp, utc_now

OBSERVED_STYLE_FIELDS = (
    "supportive",
    "playful",
    "confrontational",
    "cooperative",
)

_STYLE_SIGNALS = {
    EventType.PRAISE: (0.9, 0.1, 0.0, 0.9),
    EventType.SUPPORT: (1.0, 0.1, 0.0, 1.0),
    EventType.JOKE: (0.1, 1.0, 0.1, 0.4),
    EventType.TEASING: (0.0, 0.8, 0.4, 0.2),
    EventType.INSULT: (0.0, 0.0, 1.0, 0.0),
    EventType.DISAGREEMENT: (0.1, 0.1, 0.7, 0.4),
    EventType.APOLOGY: (0.7, 0.1, 0.0, 0.8),
    EventType.RECONCILIATION: (0.8, 0.1, 0.0, 1.0),
    EventType.USER_MODERATION: (0.2, 0.0, 0.4, 0.6),
    EventType.BOT_MEDIATION: (0.7, 0.1, 0.0, 1.0),
    EventType.BOT_PROVOCATION: (0.0, 0.1, 1.0, 0.0),
    EventType.TOPIC_STEERING: (0.2, 0.1, 0.1, 0.7),
    EventType.LEADERSHIP_CHALLENGE: (0.0, 0.0, 0.9, 0.1),
}


def observe_style(
    relation: ParticipantRelation,
    event_type: EventType,
    *,
    learning_rate: float = 0.2,
) -> None:
    """Update bounded style estimates without retaining message content."""

    rate = clamp(learning_rate, 0.0, 1.0)
    signals = _STYLE_SIGNALS.get(event_type, (0.5, 0.5, 0.5, 0.5))
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
    trust_support = 0.5 + max(relation.trust, 0.0) * 0.5
    tension_pressure = relation.unresolved_tension * 0.55 + relation.irritation * 0.45
    pride_pressure = (
        listener.pride * 0.45
        + listener.reactivity * 0.35
        + listener.assertiveness * 0.20
    )
    persistence_buffer = listener.persistence * (1.0 - tension_pressure * 0.35)

    persuasion = clamp(leadership_tendency * effective_receptiveness * trust_support)
    calming = clamp(persuasion * persistence_buffer * (1.0 - tension_pressure * 0.5))
    conflict_risk = clamp(
        tension_pressure * 0.55
        + pride_pressure * 0.25
        + (1.0 - persistence_buffer) * 0.20
        - calming * 0.30,
        0.0,
        1.0,
    )
    return InfluenceDecision(
        persuasion=persuasion,
        calming=calming,
        conflict_risk=conflict_risk,
        factors={
            "leadership_tendency": leadership_tendency,
            "effective_receptiveness": effective_receptiveness,
            "trust_support": trust_support,
            "tension_pressure": tension_pressure,
            "pride_pressure": pride_pressure,
            "persistence_buffer": persistence_buffer,
        },
    )
