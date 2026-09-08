"""Bounded affect transitions and configurable decay."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from .config import AffectConfig
from .events import AffectiveEvent, EventType
from .models import AffectState, ParticipantRelation, clamp, utc_now


def _relation(state: AffectState, participant_id: str) -> ParticipantRelation:
    return state.relationships.setdefault(participant_id, ParticipantRelation())


def _change(state: AffectState, *, valence=0.0, arousal=0.0, frustration=0.0, offended=0.0) -> None:
    state.valence = clamp(state.valence + valence)
    state.arousal = clamp(state.arousal + arousal, 0.0, 1.0)
    state.frustration = clamp(state.frustration + frustration, 0.0, 1.0)
    state.offended = clamp(state.offended + offended, 0.0, 1.0)


def apply_event(state: AffectState, event: AffectiveEvent, config: AffectConfig) -> str:
    """Apply one event and return the inspectable rule name that fired."""

    gain = config.dynamics["escalation_gain"]
    relation = _relation(state, event.speaker_id)

    if event.event_type in {EventType.PRAISE, EventType.SUPPORT}:
        _change(state, valence=0.12, arousal=0.04)
        relation.trust = clamp(relation.trust + 0.08)
        relation.affinity = clamp(relation.affinity + 0.10)
        relation.irritation = clamp(relation.irritation - 0.04, 0.0, 1.0)
        return "positive_social_signal"
    if event.event_type == EventType.JOKE:
        _change(state, valence=0.08, arousal=0.08)
        relation.affinity = clamp(relation.affinity + 0.05)
        return "playful_signal"
    if event.event_type == EventType.TEASING:
        _change(state, arousal=0.08 * gain, frustration=0.08 * gain)
        relation.irritation = clamp(relation.irritation + 0.10 * gain, 0.0, 1.0)
        relation.unresolved_tension = clamp(relation.unresolved_tension + 0.08 * gain, 0.0, 1.0)
        return "teasing_tension"
    if event.event_type in {EventType.INSULT, EventType.BOT_PROVOCATION}:
        _change(
            state,
            valence=-0.18 * gain,
            arousal=0.18 * gain,
            frustration=0.20 * gain,
            offended=0.24 * gain,
        )
        relation.irritation = clamp(relation.irritation + 0.22 * gain, 0.0, 1.0)
        relation.unresolved_tension = clamp(relation.unresolved_tension + 0.25 * gain, 0.0, 1.0)
        state.open_conflicts[event.speaker_id] = {
            "heat": relation.unresolved_tension,
            "status": "open",
            "updated_at": utc_now(),
        }
        return "direct_offense"
    if event.event_type == EventType.DISAGREEMENT:
        _change(state, arousal=0.06 * gain, frustration=0.08 * gain)
        relation.unresolved_tension = clamp(relation.unresolved_tension + 0.08 * gain, 0.0, 1.0)
        return "disagreement_pressure"
    if event.event_type in {EventType.APOLOGY, EventType.RECONCILIATION}:
        _change(state, valence=0.10, arousal=-0.08, frustration=-0.16, offended=-0.20)
        relation.irritation = clamp(relation.irritation - 0.20, 0.0, 1.0)
        relation.unresolved_tension = clamp(relation.unresolved_tension - 0.24, 0.0, 1.0)
        if relation.unresolved_tension < 0.15:
            state.open_conflicts.pop(event.speaker_id, None)
        return "repair_signal"
    if event.event_type == EventType.USER_MODERATION:
        if event.action == "calm":
            _change(state, arousal=-0.25, frustration=-0.30, offended=-0.20)
            for item in state.relationships.values():
                item.irritation = clamp(item.irritation - 0.18, 0.0, 1.0)
                item.unresolved_tension = clamp(item.unresolved_tension - 0.20, 0.0, 1.0)
            return "verified_user_calm"
        _change(state, arousal=0.18, frustration=0.10)
        return "verified_user_heat"
    if event.event_type == EventType.BOT_MEDIATION:
        _change(state, arousal=-0.12, frustration=-0.12)
        relation.respect = clamp(relation.respect + 0.05)
        return "social_mediation"
    if event.event_type == EventType.LEADERSHIP_CHALLENGE:
        _change(state, arousal=0.10 * gain, frustration=0.10 * gain)
        relation.respect = clamp(relation.respect - 0.08)
        relation.unresolved_tension = clamp(relation.unresolved_tension + 0.10 * gain, 0.0, 1.0)
        return "leadership_challenge"
    if event.event_type == EventType.TOPIC_STEERING:
        relation.respect = clamp(relation.respect + 0.02)
        return "topic_steering"
    return "unhandled_event"


def decay_state(state: AffectState, config: AffectConfig, elapsed_hours: float) -> None:
    """Decay global emotion and relational heat without erasing history."""

    if elapsed_hours <= 0:
        return
    rate = config.dynamics["emotional_decay"]
    global_factor = math.exp(-rate * elapsed_hours)
    state.valence *= global_factor
    state.arousal *= global_factor
    state.frustration *= global_factor
    state.offended *= global_factor

    grudge_rate = rate * (1.0 - config.dynamics["grudge_persistence"])
    relation_factor = math.exp(-grudge_rate * elapsed_hours)
    for relation in state.relationships.values():
        relation.irritation *= relation_factor
        relation.unresolved_tension *= relation_factor

    state.updated_at = datetime.now(timezone.utc).isoformat()
