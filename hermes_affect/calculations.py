"""Pure formulas used by the affect engine.

State mutation and rule selection stay in the domain modules.  Keeping the
math here makes the algorithm inspectable and lets tuning changes remain
separate from the Hermes adapter and persistence code.
"""

from __future__ import annotations

import math

from .config import AffectConfig
from .events import AffectiveEvent
from .models import AffectState, ParticipantRelation
from .parameters import (
    CALMING_TENSION_PENALTY,
    CONFLICT_CALMING_RELIEF,
    CONFLICT_PERSISTENCE_WEIGHT,
    CONFLICT_PRIDE_WEIGHT,
    CONFLICT_TENSION_WEIGHT,
    EXPRESSION_ASSERTIVENESS_WEIGHT,
    EXPRESSION_CURVE_BASE,
    EXPRESSION_CURVE_TEMPERAMENT_WEIGHT,
    EXPRESSION_PERSISTENCE_WEIGHT,
    EXPRESSION_PLAYFULNESS_WEIGHT,
    EXPRESSION_PRIDE_WEIGHT,
    EXPRESSION_REACTIVITY_WEIGHT,
    GLOBAL_DECAY_BASE_RATE,
    GLOBAL_DECAY_PERSISTENCE_RANGE,
    HIGH_SEVERITY_MULTIPLIER,
    JOKE_PLAYFULNESS_BASE,
    JOKE_PLAYFULNESS_WEIGHT,
    LOW_SEVERITY_MULTIPLIER,
    MAX_NUMERIC_SEVERITY,
    PERSISTENCE_TENSION_PENALTY,
    PRIDE_PRESSURE_ASSERTIVENESS_WEIGHT,
    PRIDE_PRESSURE_PRIDE_WEIGHT,
    PRIDE_PRESSURE_REACTIVITY_WEIGHT,
    PRIDE_SENSITIVITY_BASE,
    PRIDE_SENSITIVITY_TRAIT_WEIGHT,
    REACTIVITY_BASE,
    REACTIVITY_TRAIT_WEIGHT,
    RELATION_DECAY_BASE_RATE,
    RELATION_DECAY_PERSISTENCE_RANGE,
    SENSITIVITY_BASE,
    SEVERE_SEVERITY_MULTIPLIER,
    TEASING_MISUNDERSTANDING_BASE,
    TEASING_MISUNDERSTANDING_WEIGHT,
    TENSION_IRRITATION_WEIGHT,
    TENSION_UNRESOLVED_WEIGHT,
    TRUST_SUPPORT_BASE,
    TRUST_SUPPORT_WEIGHT,
)


def event_severity(event: AffectiveEvent) -> float:
    """Convert a classifier severity label into a bounded multiplier."""

    value = event.attributes.get("severity", "normal").lower()
    if value in {"low", "mild"}:
        return LOW_SEVERITY_MULTIPLIER
    if value in {"high", "severe"}:
        return HIGH_SEVERITY_MULTIPLIER if value == "high" else SEVERE_SEVERITY_MULTIPLIER
    try:
        return max(0.0, min(float(value), MAX_NUMERIC_SEVERITY))
    except ValueError:
        return 1.0


def sensitivity_multiplier(config: AffectConfig, event: AffectiveEvent) -> float:
    """Return the topic sensitivity multiplier for an event."""

    topic = event.attributes.get("topic", "").strip().lower()
    if not topic:
        return SENSITIVITY_BASE
    matching = [item.intensity for item in config.sensitivities if item.topic.lower() in topic]
    return SENSITIVITY_BASE + max(matching, default=0.0)


def reactivity_factor(config: AffectConfig) -> float:
    return REACTIVITY_BASE + REACTIVITY_TRAIT_WEIGHT * config.traits["reactivity"]


def pride_sensitivity(config: AffectConfig) -> float:
    return PRIDE_SENSITIVITY_BASE + PRIDE_SENSITIVITY_TRAIT_WEIGHT * config.traits["pride"]


def playful_signal_factor(playfulness: float) -> float:
    return JOKE_PLAYFULNESS_BASE + JOKE_PLAYFULNESS_WEIGHT * playfulness


def teasing_misunderstanding(playfulness: float) -> float:
    return TEASING_MISUNDERSTANDING_BASE + TEASING_MISUNDERSTANDING_WEIGHT * (1.0 - playfulness)


def affect_intensity(state: AffectState) -> float:
    """Return the current normalized intensity available for expression."""

    components = (
        abs(state.valence),
        state.arousal,
        state.frustration,
        state.offended,
    )
    return sum(components) / len(components)


def effective_expression_drive(state: AffectState, config: AffectConfig) -> float:
    """Map current affect to a smooth, normalized expression drive."""

    expression_gain = config.tuning["expression_gain"]
    temperament = (
        EXPRESSION_REACTIVITY_WEIGHT * config.traits["reactivity"]
        + EXPRESSION_PRIDE_WEIGHT * config.traits["pride"]
        + EXPRESSION_ASSERTIVENESS_WEIGHT * config.traits["assertiveness"]
        + EXPRESSION_PERSISTENCE_WEIGHT * config.traits["persistence"]
        + EXPRESSION_PLAYFULNESS_WEIGHT * config.traits["playfulness"]
    )
    k = expression_gain * (
        EXPRESSION_CURVE_BASE + EXPRESSION_CURVE_TEMPERAMENT_WEIGHT * temperament
    )
    return -math.expm1(-k * affect_intensity(state))


def global_decay_factor(config: AffectConfig, elapsed_hours: float) -> float:
    persistence = config.traits["persistence"]
    rate = GLOBAL_DECAY_BASE_RATE + GLOBAL_DECAY_PERSISTENCE_RANGE * (1.0 - persistence)
    return math.exp(-rate * elapsed_hours)


def relation_decay_factor(config: AffectConfig, elapsed_hours: float) -> float:
    persistence = config.traits["persistence"]
    rate = RELATION_DECAY_BASE_RATE + RELATION_DECAY_PERSISTENCE_RANGE * (1.0 - persistence)
    return math.exp(-rate * elapsed_hours)


def tension_pressure(relation: ParticipantRelation) -> float:
    return (
        relation.unresolved_tension * TENSION_UNRESOLVED_WEIGHT
        + relation.irritation * TENSION_IRRITATION_WEIGHT
    )


def pride_pressure(configured_pride: float, reactivity: float, assertiveness: float) -> float:
    return (
        configured_pride * PRIDE_PRESSURE_PRIDE_WEIGHT
        + reactivity * PRIDE_PRESSURE_REACTIVITY_WEIGHT
        + assertiveness * PRIDE_PRESSURE_ASSERTIVENESS_WEIGHT
    )


def persistence_buffer(persistence: float, pressure: float) -> float:
    return persistence * (1.0 - pressure * PERSISTENCE_TENSION_PENALTY)


def trust_support(trust: float) -> float:
    return TRUST_SUPPORT_BASE + max(trust, 0.0) * TRUST_SUPPORT_WEIGHT


def calming_factor(persuasion: float, buffer: float, pressure: float) -> float:
    return persuasion * buffer * (1.0 - pressure * CALMING_TENSION_PENALTY)


def conflict_risk(
    pressure: float,
    pride: float,
    buffer: float,
    calming: float,
) -> float:
    return (
        pressure * CONFLICT_TENSION_WEIGHT
        + pride * CONFLICT_PRIDE_WEIGHT
        + (1.0 - buffer) * CONFLICT_PERSISTENCE_WEIGHT
        - calming * CONFLICT_CALMING_RELIEF
    )
