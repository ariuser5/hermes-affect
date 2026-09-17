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

# Impact floor when reactivity is 0. Formula: base + weight * reactivity.
REACTIVITY_BASE: Final = 0.25
# Additional event impact available when reactivity is 1.
REACTIVITY_TRAIT_WEIGHT: Final = 0.75
# Offense sensitivity floor when pride is 0.
PRIDE_SENSITIVITY_BASE: Final = 0.40
# Additional offense sensitivity available when pride is 1.
PRIDE_SENSITIVITY_TRAIT_WEIGHT: Final = 0.60

# Multiplier for low/mild classifier severity.
LOW_SEVERITY_MULTIPLIER: Final = 0.5
# Multiplier for high classifier severity.
HIGH_SEVERITY_MULTIPLIER: Final = 1.75
# Multiplier for severe deterministic severity.
SEVERE_SEVERITY_MULTIPLIER: Final = 2.5
# Safety ceiling for numeric severity values supplied by deterministic events.
MAX_NUMERIC_SEVERITY: Final = 5.0

# Starting point for a topic-sensitivity multiplier; a matching sensitivity
# then adds its configured intensity. Example: intensity 0.5 -> multiplier 1.5.
SENSITIVITY_BASE: Final = 1.0

# Global valence increase from praise/support.
PRAISE_VALENCE_GAIN: Final = 0.12
# Global arousal increase from praise/support.
PRAISE_AROUSAL_GAIN: Final = 0.04
# Relationship trust increase from praise/support.
TRUST_GAIN: Final = 0.08
# Relationship affinity increase from praise/support.
AFFINITY_GAIN: Final = 0.10
# Relationship irritation relief from praise/support.
IRRITATION_RELIEF_FROM_POSITIVE_SIGNAL: Final = 0.04

# Base global valence/arousal change from a joke before playfulness weighting.
JOKE_BASE_GAIN: Final = 0.08
# Minimum joke interpretation factor at playfulness 0.
JOKE_PLAYFULNESS_BASE: Final = 0.35
# Additional joke interpretation factor available at playfulness 1.
JOKE_PLAYFULNESS_WEIGHT: Final = 0.65
# Frustration added by a joke, reduced by playfulness.
JOKE_FRUSTRATION_GAIN: Final = 0.05
# Relationship affinity gain from a joke before playfulness weighting.
JOKE_AFFINITY_GAIN: Final = 0.05
# Below this playfulness, a joke also creates irritation.
SERIOUS_JOKE_PLAYFULNESS_THRESHOLD: Final = 0.35
# Irritation added when a joke is interpreted seriously.
SERIOUS_JOKE_IRRITATION_GAIN: Final = 0.04

# Base arousal/frustration change from teasing before trait and escalation gains.
TEASING_BASE_GAIN: Final = 0.08
# Minimum teasing misunderstanding factor at playfulness 1.
TEASING_MISUNDERSTANDING_BASE: Final = 0.35
# Additional teasing misunderstanding at playfulness 0.
TEASING_MISUNDERSTANDING_WEIGHT: Final = 0.65
# Relationship irritation gain from teasing.
TEASING_IRRITATION_GAIN: Final = 0.10
# Relationship unresolved-tension gain from teasing.
TEASING_TENSION_GAIN: Final = 0.08

# Valence loss caused by insult impact.
INSULT_VALENCE_GAIN: Final = 0.18
# Arousal gain caused by insult impact.
INSULT_AROUSAL_GAIN: Final = 0.18
# Frustration gain caused by insult impact.
INSULT_FRUSTRATION_GAIN: Final = 0.20
# Offense gain caused by insult impact.
INSULT_OFFENDED_GAIN: Final = 0.24
# Relationship irritation gain caused by insult impact.
INSULT_IRRITATION_GAIN: Final = 0.22
# Relationship unresolved-tension gain caused by insult impact.
INSULT_TENSION_GAIN: Final = 0.25

# Arousal gain from disagreement before escalation and reactivity gains.
DISAGREEMENT_AROUSAL_GAIN: Final = 0.06
# Frustration gain from disagreement before escalation and reactivity gains.
DISAGREEMENT_FRUSTRATION_GAIN: Final = 0.08
# Relationship tension gain from disagreement before escalation and reactivity gains.
DISAGREEMENT_TENSION_GAIN: Final = 0.08

# Global valence recovery from apology/reconciliation.
REPAIR_VALENCE_GAIN: Final = 0.10
# Arousal relief from apology/reconciliation.
REPAIR_AROUSAL_RELIEF: Final = 0.08
# Frustration relief from apology/reconciliation.
REPAIR_FRUSTRATION_RELIEF: Final = 0.16
# Offense relief from apology/reconciliation.
REPAIR_OFFENDED_RELIEF: Final = 0.20
# Relationship irritation relief from apology/reconciliation.
REPAIR_IRRITATION_RELIEF: Final = 0.20
# Relationship tension relief from apology/reconciliation.
REPAIR_TENSION_RELIEF: Final = 0.24
# An open conflict is removed below this remaining tension.
CONFLICT_CLEARED_TENSION_THRESHOLD: Final = 0.15

# Global arousal relief from calm moderation.
MODERATION_CALM_AROUSAL_RELIEF: Final = 0.25
# Global frustration relief from calm moderation.
MODERATION_CALM_FRUSTRATION_RELIEF: Final = 0.30
# Global offense relief from calm moderation.
MODERATION_CALM_OFFENDED_RELIEF: Final = 0.20
# Irritation relief applied to every relationship during calm moderation.
MODERATION_CALM_IRRITATION_RELIEF: Final = 0.18
# Tension relief applied to every relationship during calm moderation.
MODERATION_CALM_TENSION_RELIEF: Final = 0.20
# Arousal gain from heat moderation.
MODERATION_HEAT_AROUSAL_GAIN: Final = 0.18
# Frustration gain from heat moderation.
MODERATION_HEAT_FRUSTRATION_GAIN: Final = 0.10

# Arousal relief from bot mediation.
MEDIATION_AROUSAL_RELIEF: Final = 0.12
# Frustration relief from bot mediation.
MEDIATION_FRUSTRATION_RELIEF: Final = 0.12
# Respect gain toward the mediating participant.
MEDIATION_RESPECT_GAIN: Final = 0.05

# Arousal/frustration gain from a leadership challenge before trait gains.
LEADERSHIP_CHALLENGE_BASE_GAIN: Final = 0.10
# Respect loss toward the challenged participant.
LEADERSHIP_CHALLENGE_RESPECT_LOSS: Final = 0.08
# Relationship tension gain from a leadership challenge.
LEADERSHIP_CHALLENGE_TENSION_GAIN: Final = 0.10
# Respect gain when a participant successfully steers away from a topic.
TOPIC_STEERING_RESPECT_GAIN: Final = 0.02

# Persistence-based decay.  The trait changes the rate between the base and
# base + range: higher persistence means a smaller decay rate.
# Global decay rate when persistence is 1.
GLOBAL_DECAY_BASE_RATE: Final = 0.20
# Extra global decay rate contributed when persistence moves from 1 to 0.
GLOBAL_DECAY_PERSISTENCE_RANGE: Final = 0.80
# Relationship decay rate when persistence is 1.
RELATION_DECAY_BASE_RATE: Final = 0.08
# Extra relationship decay rate contributed when persistence moves from 1 to 0.
RELATION_DECAY_PERSISTENCE_RANGE: Final = 0.42

# ---------------------------------------------------------------------------
# Expression and posture thresholds
# ---------------------------------------------------------------------------

# Weight of reactivity in the temperament part of expression drive.
EXPRESSION_REACTIVITY_WEIGHT: Final = 0.30
# Weight of pride in the temperament part of expression drive.
EXPRESSION_PRIDE_WEIGHT: Final = 0.25
# Weight of assertiveness in the temperament part of expression drive.
EXPRESSION_ASSERTIVENESS_WEIGHT: Final = 0.20
# Weight of persistence in the temperament part of expression drive.
EXPRESSION_PERSISTENCE_WEIGHT: Final = 0.15
# Weight of playfulness in the temperament part of expression drive.
EXPRESSION_PLAYFULNESS_WEIGHT: Final = 0.10
# Baseline curvature factor in k = gain * (base + temperament_weight * temperament).
EXPRESSION_CURVE_BASE: Final = 0.5
# Scales the temperament contribution to the exponential curve.
EXPRESSION_CURVE_TEMPERAMENT_WEIGHT: Final = 1.5

# Affect level above which a sensitivity/conflict becomes behaviorally active.
ACTIVE_AFFECT_THRESHOLD: Final = 0.30
# Expression drive required before an assertive bot may counterattack.
COUNTERATTACK_DRIVE_THRESHOLD: Final = 0.65
# Minimum assertiveness required for counterattack posture.
COUNTERATTACK_ASSERTIVENESS_THRESHOLD: Final = 0.55
# Offense level that permits refusal for a low-assertiveness bot.
REFUSAL_OFFENDED_THRESHOLD: Final = 0.65
# Assertiveness ceiling for refusal posture.
REFUSAL_ASSERTIVENESS_THRESHOLD: Final = 0.40
# Expression-drive ceiling for evasive behavior.
EVASIVE_DRIVE_THRESHOLD: Final = 0.35
# Assertiveness ceiling for evasive behavior.
EVASIVE_ASSERTIVENESS_THRESHOLD: Final = 0.40
# Affect level above which a non-conflict response becomes terse/cold.
TERSE_AFFECT_THRESHOLD: Final = 0.65
# Frustration level above which a non-conflict response becomes guarded.
GUARDED_AFFECT_THRESHOLD: Final = 0.45
# Positive valence level required for warm posture.
WARM_VALENCE_THRESHOLD: Final = 0.45
# Playfulness level required for playful posture instead of warm posture.
PLAYFUL_VALENCE_THRESHOLD: Final = 0.65

# First expression tier: measured guidance below this drive.
CONTEXT_GENTLE_DRIVE_THRESHOLD: Final = 0.20
# Second expression tier: controlled and firmer guidance below this drive.
CONTEXT_CONTROLLED_DRIVE_THRESHOLD: Final = 0.75
# Third expression tier: skeptical/terse guidance below this drive; above it is intense.
CONTEXT_TENSE_DRIVE_THRESHOLD: Final = 0.80

# ---------------------------------------------------------------------------
# Social-influence coefficients
# ---------------------------------------------------------------------------

# Smoothing rate for observed style; 0 freezes history and 1 replaces it at once.
STYLE_LEARNING_RATE: Final = 0.20
# Smoothing rate for the participant influence estimate.
INFLUENCE_ESTIMATE_LEARNING_RATE: Final = 0.20
# Total state-change scale treated as a full-strength observation.
# Example: changes summing to 0.75 -> effect strength 0.5.
OBSERVATION_EFFECT_NORMALIZER: Final = 1.5
# Safety bound on stored observations for one participant.
MAX_OBSERVATION_COUNT: Final = 1000
# Share of unresolved tension in tension pressure.
TENSION_UNRESOLVED_WEIGHT: Final = 0.55
# Share of irritation in tension pressure.
TENSION_IRRITATION_WEIGHT: Final = 0.45
# Baseline relationship support before trust is considered.
TRUST_SUPPORT_BASE: Final = 0.5
# Extra relationship support contributed by positive trust.
TRUST_SUPPORT_WEIGHT: Final = 0.5
# How much tension reduces a persistent participant's buffer.
PERSISTENCE_TENSION_PENALTY: Final = 0.35
# How much tension reduces the calming effect of influence.
CALMING_TENSION_PENALTY: Final = 0.5
# Share of pride in a listener's conflict pressure.
PRIDE_PRESSURE_PRIDE_WEIGHT: Final = 0.45
# Share of reactivity in a listener's conflict pressure.
PRIDE_PRESSURE_REACTIVITY_WEIGHT: Final = 0.35
# Share of assertiveness in a listener's conflict pressure.
PRIDE_PRESSURE_ASSERTIVENESS_WEIGHT: Final = 0.20
# Share of tension pressure in conflict risk.
CONFLICT_TENSION_WEIGHT: Final = 0.55
# Share of pride pressure in conflict risk.
CONFLICT_PRIDE_WEIGHT: Final = 0.25
# Share of low persistence buffer in conflict risk.
CONFLICT_PERSISTENCE_WEIGHT: Final = 0.20
# Reduction in conflict risk from successful calming influence.
CONFLICT_CALMING_RELIEF: Final = 0.30

# Each tuple is (supportive, playful, confrontational, cooperative) and is
# the target style estimate for one classified event type.
STYLE_SIGNALS: Final = {
    # Praise is strongly supportive and cooperative.
    EventType.PRAISE: (0.9, 0.1, 0.0, 0.9),
    # Support is maximally supportive and cooperative.
    EventType.SUPPORT: (1.0, 0.1, 0.0, 1.0),
    # Jokes are primarily playful with mild social cooperation.
    EventType.JOKE: (0.1, 1.0, 0.1, 0.4),
    # Teasing is playful but carries some confrontation.
    EventType.TEASING: (0.0, 0.8, 0.4, 0.2),
    # Insults are maximally confrontational.
    EventType.INSULT: (0.0, 0.0, 1.0, 0.0),
    # Disagreement is moderately confrontational and cooperative.
    EventType.DISAGREEMENT: (0.1, 0.1, 0.7, 0.4),
    # Apology is supportive and cooperative.
    EventType.APOLOGY: (0.7, 0.1, 0.0, 0.8),
    # Reconciliation is strongly supportive and cooperative.
    EventType.RECONCILIATION: (0.8, 0.1, 0.0, 1.0),
    # Moderation is mildly confrontational but cooperative.
    EventType.USER_MODERATION: (0.2, 0.0, 0.4, 0.6),
    # Bot mediation is supportive and cooperative.
    EventType.BOT_MEDIATION: (0.7, 0.1, 0.0, 1.0),
    # Bot provocation is confrontational.
    EventType.BOT_PROVOCATION: (0.0, 0.1, 1.0, 0.0),
    # Topic steering is mostly cooperative.
    EventType.TOPIC_STEERING: (0.2, 0.1, 0.1, 0.7),
    # Leadership challenges are strongly confrontational.
    EventType.LEADERSHIP_CHALLENGE: (0.0, 0.0, 0.9, 0.1),
}
