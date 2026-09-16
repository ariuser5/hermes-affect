"""Derive a concise response posture without exposing numerical state."""

from __future__ import annotations

from enum import Enum

from .calculations import affect_intensity, effective_expression_drive
from .config import AffectConfig
from .events import AffectiveEvent, EventType
from .models import AffectState
from .parameters import (
    ACTIVE_AFFECT_THRESHOLD,
    COUNTERATTACK_ASSERTIVENESS_THRESHOLD,
    COUNTERATTACK_DRIVE_THRESHOLD,
    EVASIVE_ASSERTIVENESS_THRESHOLD,
    EVASIVE_DRIVE_THRESHOLD,
    GUARDED_AFFECT_THRESHOLD,
    PLAYFUL_VALENCE_THRESHOLD,
    REFUSAL_ASSERTIVENESS_THRESHOLD,
    REFUSAL_OFFENDED_THRESHOLD,
    TERSE_AFFECT_THRESHOLD,
    WARM_VALENCE_THRESHOLD,
)

__all__ = [
    "ResponsePosture",
    "affect_intensity",
    "effective_expression_drive",
    "derive_posture",
]


class ResponsePosture(str, Enum):
    NORMAL_ENGAGEMENT = "normal_engagement"
    WARM = "warm"
    PLAYFUL = "playful_engagement"
    TERSE = "terse_or_cold"
    GUARDED = "guarded_reply"
    EVASIVE = "evasive_answer"
    TOPIC_AVOIDANCE = "deliberate_topic_avoidance"
    REFUSAL = "refusal_to_cooperate"
    COUNTERATTACK = "verbal_counterattack"
    RECONCILIATION = "reconciliation_attempt"
    MEDIATION = "mediation"
    TOPIC_STEERING = "topic_steering"
    PASS = "pass"


def derive_posture(
    state: AffectState,
    config: AffectConfig,
    event: AffectiveEvent | None = None,
) -> ResponsePosture:
    expression_drive = effective_expression_drive(state, config)
    if event is not None:
        if event.event_type == EventType.BOT_MEDIATION:
            return ResponsePosture.MEDIATION
        if event.event_type == EventType.TOPIC_STEERING:
            return ResponsePosture.TOPIC_STEERING
        if event.event_type in {EventType.APOLOGY, EventType.RECONCILIATION}:
            return ResponsePosture.RECONCILIATION
        if event.event_type == EventType.USER_MODERATION and event.action == "calm":
            return ResponsePosture.PASS
    if state.active_sensitivities and (
        state.frustration > ACTIVE_AFFECT_THRESHOLD or state.offended > ACTIVE_AFFECT_THRESHOLD
    ):
        return ResponsePosture.TOPIC_AVOIDANCE
    if state.open_conflicts and (
        state.frustration > ACTIVE_AFFECT_THRESHOLD or state.offended > ACTIVE_AFFECT_THRESHOLD
    ):
        if (
            expression_drive >= COUNTERATTACK_DRIVE_THRESHOLD
            and config.traits["assertiveness"] >= COUNTERATTACK_ASSERTIVENESS_THRESHOLD
        ):
            return ResponsePosture.COUNTERATTACK
        if (
            state.offended > REFUSAL_OFFENDED_THRESHOLD
            and config.traits["assertiveness"] < REFUSAL_ASSERTIVENESS_THRESHOLD
        ):
            return ResponsePosture.REFUSAL
        if (
            expression_drive <= EVASIVE_DRIVE_THRESHOLD
            and config.traits["assertiveness"] < EVASIVE_ASSERTIVENESS_THRESHOLD
        ):
            return ResponsePosture.EVASIVE
        return ResponsePosture.GUARDED
    if state.frustration > TERSE_AFFECT_THRESHOLD or state.offended > TERSE_AFFECT_THRESHOLD:
        return ResponsePosture.TERSE
    if state.frustration > GUARDED_AFFECT_THRESHOLD:
        return ResponsePosture.GUARDED
    if state.valence > WARM_VALENCE_THRESHOLD:
        if config.traits["playfulness"] > PLAYFUL_VALENCE_THRESHOLD:
            return ResponsePosture.PLAYFUL
        return ResponsePosture.WARM
    return ResponsePosture.NORMAL_ENGAGEMENT
