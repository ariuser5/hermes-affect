"""Pure v2 derivations. No hidden per-profile tuning or mutable state."""

from __future__ import annotations

import math

from .configuration import AffectConfig
from .events import AffectiveEvent
from .parameters import (
    EXPRESSION_CURVATURE,
    MIN_DECAY_RATE,
    RELATION_TIME_MULTIPLIER,
    SECONDARY_SHARE,
    TRAIT_FLOOR,
)
from .state import AffectState, ParticipantRelation, clamp


def trait_factor(value: float) -> float:
    return TRAIT_FLOOR + (1.0 - TRAIT_FLOOR) * value


def event_severity(event: AffectiveEvent) -> float:
    """Severity is strength, not confidence. Invalid values use normal strength."""
    value = str(event.attributes.get("severity", "normal")).lower()
    labels = {"low": 0.5, "mild": 0.5, "normal": 1.0, "high": 1.75, "severe": 2.5}
    if value in labels:
        return labels[value]
    try:
        number = float(value)
    except ValueError:
        return 1.0
    return clamp(number, 0.0, 5.0) if math.isfinite(number) else 1.0


def sensitivity_multiplier(config: AffectConfig, event: AffectiveEvent) -> float:
    topic = event.attributes.get("topic", "").casefold()
    return 1.0 + max(
        (s.intensity for s in config.sensitivities if s.topic.casefold() == topic),
        default=0.0,
    )


def reactivity_factor(config: AffectConfig) -> float:
    return trait_factor(config.traits["reactivity"])


def pride_sensitivity(config: AffectConfig) -> float:
    return trait_factor(config.traits["pride"])


def playful_signal_factor(playfulness: float) -> float:
    return trait_factor(playfulness)


def teasing_misunderstanding(playfulness: float) -> float:
    return trait_factor(1.0 - playfulness)


def affect_intensity(state: AffectState) -> float:
    # Magnitude only. Rendering selects emotional direction separately.
    return max(abs(state.valence), state.arousal, state.frustration, state.offended)


def effective_expression_drive(state: AffectState, config: AffectConfig) -> float:
    intensity = max(affect_intensity(state), state.atmosphere_tension)
    return -math.expm1(-EXPRESSION_CURVATURE * config.tuning["expression_gain"] * intensity)


def global_decay_factor(config: AffectConfig, elapsed_hours: float) -> float:
    rate = MIN_DECAY_RATE + (1.0 - MIN_DECAY_RATE) * (1.0 - config.traits["persistence"])
    return math.exp(-rate * max(0.0, elapsed_hours))


def relation_decay_factor(config: AffectConfig, elapsed_hours: float) -> float:
    return global_decay_factor(config, elapsed_hours / RELATION_TIME_MULTIPLIER)


def credibility(relation: ParticipantRelation) -> float:
    """Map signed trust/respect to [0,1], with a neutral stranger at 0.5."""
    return (2.0 + relation.trust + relation.respect) / 4.0


def social_receptivity(config: AffectConfig, relation: ParticipantRelation) -> float:
    return (
        config.traits["receptiveness"]
        * credibility(relation)
        * (1.0 - SECONDARY_SHARE * relation.unresolved_tension)
    )


def repair_factor(config: AffectConfig, relation: ParticipantRelation) -> float:
    return trait_factor(social_receptivity(config, relation))


def temperament_drives(config: AffectConfig) -> dict[str, float]:
    t = config.traits
    return {
        "mischief": t["playfulness"] * t["assertiveness"] * (1.0 - t["receptiveness"]),
        "conflict_avoidance": t["reactivity"] * (1.0 - t["assertiveness"]),
        "mediation": t["receptiveness"] * t["assertiveness"],
        "teasing_sensitivity": t["reactivity"] * (t["pride"] + 1.0 - t["playfulness"]) / 2,
        "atmosphere_sensitivity": trait_factor(
            (t["reactivity"] + t["pride"] + 1.0 - t["assertiveness"]) / 3
        ),
    }


def humor_compatibility(config: AffectConfig, relation: ParticipantRelation) -> float:
    """A local estimate from observed style, not knowledge of private traits."""
    return 1.0 - abs(config.traits["playfulness"] - relation.observed_style.get("playful", 0.5))
