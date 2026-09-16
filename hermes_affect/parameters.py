"""Editable coefficients and thresholds for the affect algorithm.

This module is the tuning surface for the behavior engine.  The surrounding
modules decide *which* rule applies and update state; the values below decide
how strongly each rule changes state and when a posture changes.

These are code-level defaults.  Per-bot personality belongs in ``SOUL.md``
(``traits`` and ``tuning``); edit this file when changing the algorithm for
all bots.  Keep bounded state values in the inclusive ``[0, 1]`` range unless
a constant is explicitly documented as a gain or multiplier.
"""

from __future__ import annotations

from typing import Final

from .events import EventType

# ---------------------------------------------------------------------------
# Event transition coefficients
# ---------------------------------------------------------------------------

REACTIVITY_BASE: Final = 0.25
REACTIVITY_TRAIT_WEIGHT: Final = 0.75
PRIDE_SENSITIVITY_BASE: Final = 0.40
PRIDE_SENSITIVITY_TRAIT_WEIGHT: Final = 0.60

LOW_SEVERITY_MULTIPLIER: Final = 0.5
HIGH_SEVERITY_MULTIPLIER: Final = 1.75
SEVERE_SEVERITY_MULTIPLIER: Final = 2.5
MAX_NUMERIC_SEVERITY: Final = 5.0

SENSITIVITY_BASE: Final = 1.0

PRAISE_VALENCE_GAIN: Final = 0.12
PRAISE_AROUSAL_GAIN: Final = 0.04
TRUST_GAIN: Final = 0.08
AFFINITY_GAIN: Final = 0.10
IRRITATION_RELIEF_FROM_POSITIVE_SIGNAL: Final = 0.04

JOKE_BASE_GAIN: Final = 0.08
JOKE_PLAYFULNESS_BASE: Final = 0.35
JOKE_PLAYFULNESS_WEIGHT: Final = 0.65
JOKE_FRUSTRATION_GAIN: Final = 0.05
JOKE_AFFINITY_GAIN: Final = 0.05
SERIOUS_JOKE_PLAYFULNESS_THRESHOLD: Final = 0.35
SERIOUS_JOKE_IRRITATION_GAIN: Final = 0.04

TEASING_BASE_GAIN: Final = 0.08
TEASING_MISUNDERSTANDING_BASE: Final = 0.35
TEASING_MISUNDERSTANDING_WEIGHT: Final = 0.65
TEASING_IRRITATION_GAIN: Final = 0.10
TEASING_TENSION_GAIN: Final = 0.08

INSULT_VALENCE_GAIN: Final = 0.18
INSULT_AROUSAL_GAIN: Final = 0.18
INSULT_FRUSTRATION_GAIN: Final = 0.20
INSULT_OFFENDED_GAIN: Final = 0.24
INSULT_IRRITATION_GAIN: Final = 0.22
INSULT_TENSION_GAIN: Final = 0.25

DISAGREEMENT_AROUSAL_GAIN: Final = 0.06
DISAGREEMENT_FRUSTRATION_GAIN: Final = 0.08
DISAGREEMENT_TENSION_GAIN: Final = 0.08

REPAIR_VALENCE_GAIN: Final = 0.10
REPAIR_AROUSAL_RELIEF: Final = 0.08
REPAIR_FRUSTRATION_RELIEF: Final = 0.16
REPAIR_OFFENDED_RELIEF: Final = 0.20
REPAIR_IRRITATION_RELIEF: Final = 0.20
REPAIR_TENSION_RELIEF: Final = 0.24
CONFLICT_CLEARED_TENSION_THRESHOLD: Final = 0.15

MODERATION_CALM_AROUSAL_RELIEF: Final = 0.25
MODERATION_CALM_FRUSTRATION_RELIEF: Final = 0.30
MODERATION_CALM_OFFENDED_RELIEF: Final = 0.20
MODERATION_CALM_IRRITATION_RELIEF: Final = 0.18
MODERATION_CALM_TENSION_RELIEF: Final = 0.20
MODERATION_HEAT_AROUSAL_GAIN: Final = 0.18
MODERATION_HEAT_FRUSTRATION_GAIN: Final = 0.10

MEDIATION_AROUSAL_RELIEF: Final = 0.12
MEDIATION_FRUSTRATION_RELIEF: Final = 0.12
MEDIATION_RESPECT_GAIN: Final = 0.05

LEADERSHIP_CHALLENGE_BASE_GAIN: Final = 0.10
LEADERSHIP_CHALLENGE_RESPECT_LOSS: Final = 0.08
LEADERSHIP_CHALLENGE_TENSION_GAIN: Final = 0.10
TOPIC_STEERING_RESPECT_GAIN: Final = 0.02

# Persistence-based decay.  The trait changes the rate between the base and
# base + range: higher persistence means a smaller decay rate.
GLOBAL_DECAY_BASE_RATE: Final = 0.20
GLOBAL_DECAY_PERSISTENCE_RANGE: Final = 0.80
RELATION_DECAY_BASE_RATE: Final = 0.08
RELATION_DECAY_PERSISTENCE_RANGE: Final = 0.42

# ---------------------------------------------------------------------------
# Expression and posture thresholds
# ---------------------------------------------------------------------------

EXPRESSION_REACTIVITY_WEIGHT: Final = 0.30
EXPRESSION_PRIDE_WEIGHT: Final = 0.25
EXPRESSION_ASSERTIVENESS_WEIGHT: Final = 0.20
EXPRESSION_PERSISTENCE_WEIGHT: Final = 0.15
EXPRESSION_PLAYFULNESS_WEIGHT: Final = 0.10
EXPRESSION_CURVE_BASE: Final = 0.5
EXPRESSION_CURVE_TEMPERAMENT_WEIGHT: Final = 1.5

ACTIVE_AFFECT_THRESHOLD: Final = 0.30
COUNTERATTACK_DRIVE_THRESHOLD: Final = 0.65
COUNTERATTACK_ASSERTIVENESS_THRESHOLD: Final = 0.55
REFUSAL_OFFENDED_THRESHOLD: Final = 0.65
REFUSAL_ASSERTIVENESS_THRESHOLD: Final = 0.40
EVASIVE_DRIVE_THRESHOLD: Final = 0.35
EVASIVE_ASSERTIVENESS_THRESHOLD: Final = 0.40
TERSE_AFFECT_THRESHOLD: Final = 0.65
GUARDED_AFFECT_THRESHOLD: Final = 0.45
WARM_VALENCE_THRESHOLD: Final = 0.45
PLAYFUL_VALENCE_THRESHOLD: Final = 0.65

CONTEXT_GENTLE_DRIVE_THRESHOLD: Final = 0.20
CONTEXT_CONTROLLED_DRIVE_THRESHOLD: Final = 0.75
CONTEXT_TENSE_DRIVE_THRESHOLD: Final = 0.80

# ---------------------------------------------------------------------------
# Social-influence coefficients
# ---------------------------------------------------------------------------

STYLE_LEARNING_RATE: Final = 0.20
INFLUENCE_ESTIMATE_LEARNING_RATE: Final = 0.20
OBSERVATION_EFFECT_NORMALIZER: Final = 1.5
MAX_OBSERVATION_COUNT: Final = 1000
TENSION_UNRESOLVED_WEIGHT: Final = 0.55
TENSION_IRRITATION_WEIGHT: Final = 0.45
TRUST_SUPPORT_BASE: Final = 0.5
TRUST_SUPPORT_WEIGHT: Final = 0.5
PERSISTENCE_TENSION_PENALTY: Final = 0.35
CALMING_TENSION_PENALTY: Final = 0.5
PRIDE_PRESSURE_PRIDE_WEIGHT: Final = 0.45
PRIDE_PRESSURE_REACTIVITY_WEIGHT: Final = 0.35
PRIDE_PRESSURE_ASSERTIVENESS_WEIGHT: Final = 0.20
CONFLICT_TENSION_WEIGHT: Final = 0.55
CONFLICT_PRIDE_WEIGHT: Final = 0.25
CONFLICT_PERSISTENCE_WEIGHT: Final = 0.20
CONFLICT_CALMING_RELIEF: Final = 0.30

STYLE_SIGNALS: Final = {
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
