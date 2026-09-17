"""Response strategy derived from emotion, relationships and local atmosphere."""

from __future__ import annotations

from enum import Enum

from .calculations import affect_intensity, effective_expression_drive, temperament_drives
from .configuration import AffectConfig
from .events import AffectiveEvent, EventType
from .parameters import ACTIVE_THRESHOLD, SECONDARY_SHARE, STRATEGY_THRESHOLD, STRONG_THRESHOLD
from .state import AffectState

__all__ = ["ResponsePosture", "affect_intensity", "effective_expression_drive", "derive_posture"]


class ResponsePosture(str, Enum):
    NORMAL_ENGAGEMENT = "normal_engagement"
    WARM = "warm"
    PLAYFUL = "playful_engagement"
    MISCHIEVOUS = "mischievous_teasing"
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
    drives = temperament_drives(config)
    personal = event is None or event.target != "participant"
    if event is not None:
        if event.event_type == EventType.USER_MODERATION and event.action == "calm":
            return ResponsePosture.PASS
        if personal and event.event_type in {EventType.APOLOGY, EventType.RECONCILIATION}:
            return ResponsePosture.RECONCILIATION
        if personal and event.event_type == EventType.BOT_MEDIATION:
            return ResponsePosture.MEDIATION
        if personal and event.event_type == EventType.TOPIC_STEERING:
            return ResponsePosture.TOPIC_STEERING

    # Group tension can motivate intervention or avoidance without becoming personal offense.
    if state.atmosphere_tension > ACTIVE_THRESHOLD:
        if drives["mediation"] > STRATEGY_THRESHOLD and not personal:
            return ResponsePosture.MEDIATION
        if drives["conflict_avoidance"] > STRATEGY_THRESHOLD:
            return ResponsePosture.TOPIC_AVOIDANCE

    if (
        personal
        and state.active_sensitivities
        and max(state.frustration, state.offended) > ACTIVE_THRESHOLD
    ):
        return ResponsePosture.TOPIC_AVOIDANCE

    participant = event.speaker_id if event else state.current_participant
    # With no conversational target this also supports standalone state inspection.
    conflict = participant in state.open_conflicts if participant else bool(state.open_conflicts)
    if personal and conflict and max(state.frustration, state.offended) > ACTIVE_THRESHOLD:
        assertiveness = config.traits["assertiveness"]
        drive = effective_expression_drive(state, config)
        if assertiveness >= SECONDARY_SHARE and drive >= STRONG_THRESHOLD:
            return ResponsePosture.COUNTERATTACK
        if assertiveness < SECONDARY_SHARE and state.offended > STRONG_THRESHOLD:
            return ResponsePosture.REFUSAL
        if assertiveness < SECONDARY_SHARE and drive < STRATEGY_THRESHOLD:
            return ResponsePosture.EVASIVE
        return ResponsePosture.GUARDED

    # A temperament can invite/continue teasing without a separate "trolling" trait.
    if (
        personal
        and event is not None
        and event.event_type in {EventType.JOKE, EventType.TEASING, EventType.DISAGREEMENT}
        and drives["mischief"] > STRATEGY_THRESHOLD
    ):
        return ResponsePosture.MISCHIEVOUS
    if max(state.frustration, state.offended) > STRONG_THRESHOLD:
        return ResponsePosture.TERSE
    if state.frustration > ACTIVE_THRESHOLD:
        return ResponsePosture.GUARDED
    if state.valence > ACTIVE_THRESHOLD:
        return (
            ResponsePosture.PLAYFUL
            if config.traits["playfulness"] > SECONDARY_SHARE
            else ResponsePosture.WARM
        )
    return ResponsePosture.NORMAL_ENGAGEMENT
