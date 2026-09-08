"""Derive a concise response posture without exposing numerical state."""

from __future__ import annotations

from enum import Enum

from .config import AffectConfig
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


def derive_posture(state: AffectState, config: AffectConfig) -> ResponsePosture:
    if state.response_posture == ResponsePosture.MEDIATION:
        return ResponsePosture.MEDIATION
    if state.open_conflicts and (state.frustration > 0.30 or state.offended > 0.30):
        if config.dynamics["expression_gain"] >= 1.75:
            return ResponsePosture.COUNTERATTACK
        return ResponsePosture.GUARDED
    if state.frustration > 0.65 or state.offended > 0.65:
        return ResponsePosture.TERSE
    if state.frustration > 0.45:
        return ResponsePosture.GUARDED
    if state.valence > 0.45:
        if config.traits["playfulness"] > 0.65 and config.traits["humor_tolerance"] > 0.55:
            return ResponsePosture.PLAYFUL
        return ResponsePosture.WARM
    return ResponsePosture.NORMAL_ENGAGEMENT
