"""Derive a concise response posture without exposing numerical state."""

from __future__ import annotations

from enum import Enum

from .config import AffectConfig
from .events import AffectiveEvent, EventType
from .models import AffectState


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
    if event is not None:
        if event.event_type == EventType.BOT_MEDIATION:
            return ResponsePosture.MEDIATION
        if event.event_type == EventType.TOPIC_STEERING:
            return ResponsePosture.TOPIC_STEERING
        if event.event_type in {EventType.APOLOGY, EventType.RECONCILIATION}:
            return ResponsePosture.RECONCILIATION
        if event.event_type == EventType.USER_MODERATION and event.action == "calm":
            return ResponsePosture.PASS
    if state.active_sensitivities and (state.frustration > 0.30 or state.offended > 0.30):
        return ResponsePosture.TOPIC_AVOIDANCE
    if state.open_conflicts and (state.frustration > 0.30 or state.offended > 0.30):
        if (
            config.tuning["expression_gain"] >= 1.75
            and config.traits["assertiveness"] >= 0.55
        ):
            return ResponsePosture.COUNTERATTACK
        if state.offended > 0.65 and config.traits["assertiveness"] < 0.40:
            return ResponsePosture.REFUSAL
        if (
            config.tuning["expression_gain"] <= 0.65
            and config.traits["assertiveness"] < 0.40
        ):
            return ResponsePosture.EVASIVE
        return ResponsePosture.GUARDED
    if state.frustration > 0.65 or state.offended > 0.65:
        return ResponsePosture.TERSE
    if state.frustration > 0.45:
        return ResponsePosture.GUARDED
    if state.valence > 0.45:
        if config.traits["playfulness"] > 0.65:
            return ResponsePosture.PLAYFUL
        return ResponsePosture.WARM
    return ResponsePosture.NORMAL_ENGAGEMENT
