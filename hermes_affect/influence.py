"""Inspectable participant-to-participant social influence policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .config import AffectConfig
from .models import ParticipantRelation, clamp


@dataclass(frozen=True)
class ParticipantTraits:
    social_influence: float = 0.5
    leadership_drive: float = 0.5
    deference: float = 0.5
    pride: float = 0.5
    reactivity: float = 0.5
    patience: float = 0.5
    conflict_avoidance: float = 0.5
    playfulness: float = 0.5
    seriousness: float = 0.5

    @classmethod
    def from_config(cls, config: AffectConfig) -> "ParticipantTraits":
        return cls(
            social_influence=config.traits["social_influence"],
            leadership_drive=config.traits["leadership_drive"],
            deference=config.traits["deference"],
            pride=config.traits["pride"],
            reactivity=config.traits["reactivity"],
            patience=config.traits["patience"],
            conflict_avoidance=config.traits["conflict_avoidance"],
            playfulness=config.traits["playfulness"],
            seriousness=config.traits["seriousness"],
        )


class ParticipantTraitResolver(Protocol):
    def resolve(self, participant_id: str) -> ParticipantTraits: ...


@dataclass
class NeutralTraitResolver:
    traits: dict[str, ParticipantTraits] = field(default_factory=dict)
    neutral: ParticipantTraits = field(default_factory=ParticipantTraits)

    def resolve(self, participant_id: str) -> ParticipantTraits:
        return self.traits.get(participant_id, self.neutral)


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
    """Return separate policy factors rather than one unconditional multiplier."""

    leadership_signal = speaker.social_influence * 0.45 + speaker.leadership_drive * 0.55
    receptivity = listener.deference * (0.55 + relation.respect * 0.45)
    trust_support = 0.5 + max(relation.trust, 0.0) * 0.5
    tension_pressure = relation.unresolved_tension * 0.55 + relation.irritation * 0.45
    pride_pressure = listener.pride * 0.4 + listener.reactivity * 0.35
    patience_buffer = listener.patience * 0.35 + listener.conflict_avoidance * 0.25

    persuasion = clamp(leadership_signal * receptivity * trust_support, 0.0, 1.0)
    calming = clamp(persuasion * patience_buffer * (1.0 - tension_pressure * 0.5), 0.0, 1.0)
    conflict_risk = clamp(
        tension_pressure * 0.55
        + pride_pressure * 0.25
        + (1.0 - patience_buffer) * 0.20
        - calming * 0.30,
        0.0,
        1.0,
    )
    return InfluenceDecision(
        persuasion=persuasion,
        calming=calming,
        conflict_risk=conflict_risk,
        factors={
            "leadership_signal": leadership_signal,
            "receptivity": receptivity,
            "trust_support": trust_support,
            "tension_pressure": tension_pressure,
            "pride_pressure": pride_pressure,
            "patience_buffer": patience_buffer,
        },
    )
