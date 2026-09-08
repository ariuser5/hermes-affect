"""Bounded affect transitions and persistence-based decay."""

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


def _severity(event: AffectiveEvent) -> float:
    value = event.attributes.get("severity", "normal").lower()
    if value in {"low", "mild"}:
        return 0.5
    if value in {"high", "severe"}:
        return 1.75 if value == "high" else 2.5
    try:
        return max(0.0, min(float(value), 5.0))
    except ValueError:
        return 1.0


def _sensitivity_multiplier(config: AffectConfig, event: AffectiveEvent) -> float:
    topic = event.attributes.get("topic", "").strip().lower()
    if not topic:
        return 1.0
    matching = [item.intensity for item in config.sensitivities if item.topic.lower() in topic]
    return 1.0 + max(matching, default=0.0)


def apply_event(state: AffectState, event: AffectiveEvent, config: AffectConfig) -> str:
    """Apply one event and return the inspectable rule name that fired."""

    escalation_gain = config.tuning["escalation_gain"]
    repair_gain = config.tuning["repair_gain"]
    reactivity = 0.25 + 0.75 * config.traits["reactivity"]
    pride_sensitivity = 0.40 + 0.60 * config.traits["pride"]
    sensitivity = _sensitivity_multiplier(config, event)
    relation = _relation(state, event.speaker_id)

    if event.event_type in {EventType.PRAISE, EventType.SUPPORT}:
        _change(state, valence=0.12, arousal=0.04)
        relation.trust = clamp(relation.trust + 0.08)
        relation.affinity = clamp(relation.affinity + 0.10)
        relation.irritation = clamp(relation.irritation - 0.04, 0.0, 1.0)
        return "positive_social_signal"
    if event.event_type == EventType.JOKE:
        playfulness = config.traits["playfulness"]
        _change(
            state,
            valence=0.08 * (0.35 + 0.65 * playfulness),
            arousal=0.08 * (0.35 + 0.65 * playfulness),
            frustration=0.05 * (1.0 - playfulness),
        )
        relation.affinity = clamp(relation.affinity + 0.05 * (0.35 + 0.65 * playfulness))
        if playfulness < 0.35:
            relation.irritation = clamp(relation.irritation + 0.04, 0.0, 1.0)
            return "serious_joke_interpretation"
        return "playful_signal"
    if event.event_type == EventType.TEASING:
        misunderstanding = 0.35 + 0.65 * (1.0 - config.traits["playfulness"])
        amount = 0.08 * escalation_gain * reactivity * misunderstanding
        _change(state, arousal=amount, frustration=amount)
        relation.irritation = clamp(
            relation.irritation + 0.10 * escalation_gain * misunderstanding,
            0.0,
            1.0,
        )
        relation.unresolved_tension = clamp(
            relation.unresolved_tension + 0.08 * escalation_gain * misunderstanding,
            0.0,
            1.0,
        )
        return "teasing_tension"
    if event.event_type in {EventType.INSULT, EventType.BOT_PROVOCATION}:
        impact = _severity(event) * escalation_gain * reactivity * pride_sensitivity * sensitivity
        _change(
            state,
            valence=-0.18 * impact,
            arousal=0.18 * impact,
            frustration=0.20 * impact,
            offended=0.24 * impact,
        )
        relation.irritation = clamp(relation.irritation + 0.22 * impact, 0.0, 1.0)
        relation.unresolved_tension = clamp(
            relation.unresolved_tension + 0.25 * impact,
            0.0,
            1.0,
        )
        state.open_conflicts[event.speaker_id] = {
            "heat": relation.unresolved_tension,
            "status": "open",
            "updated_at": utc_now(),
        }
        return "direct_offense"
    if event.event_type == EventType.DISAGREEMENT:
        amount = 0.06 * escalation_gain * reactivity
        _change(state, arousal=amount, frustration=0.08 * escalation_gain * reactivity)
        relation.unresolved_tension = clamp(
            relation.unresolved_tension + 0.08 * escalation_gain * reactivity,
            0.0,
            1.0,
        )
        return "disagreement_pressure"
    if event.event_type in {EventType.APOLOGY, EventType.RECONCILIATION}:
        _change(
            state,
            valence=0.10 * repair_gain,
            arousal=-0.08 * repair_gain,
            frustration=-0.16 * repair_gain,
            offended=-0.20 * repair_gain,
        )
        relation.irritation = clamp(relation.irritation - 0.20 * repair_gain, 0.0, 1.0)
        relation.unresolved_tension = clamp(
            relation.unresolved_tension - 0.24 * repair_gain,
            0.0,
            1.0,
        )
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
        amount = 0.10 * escalation_gain * reactivity
        _change(state, arousal=amount, frustration=amount)
        relation.respect = clamp(relation.respect - 0.08)
        relation.unresolved_tension = clamp(
            relation.unresolved_tension + 0.10 * escalation_gain * reactivity,
            0.0,
            1.0,
        )
        return "leadership_challenge"
    if event.event_type == EventType.TOPIC_STEERING:
        relation.respect = clamp(relation.respect + 0.02)
        return "topic_steering"
    return "unhandled_event"


def decay_state(state: AffectState, config: AffectConfig, elapsed_hours: float) -> None:
    """Decay state while letting high persistence retain tension longer."""

    if elapsed_hours <= 0:
        return
    persistence = config.traits["persistence"]
    global_rate = 0.20 + 0.80 * (1.0 - persistence)
    global_factor = math.exp(-global_rate * elapsed_hours)
    state.valence *= global_factor
    state.arousal *= global_factor
    state.frustration *= global_factor
    state.offended *= global_factor

    relation_rate = 0.08 + 0.42 * (1.0 - persistence)
    relation_factor = math.exp(-relation_rate * elapsed_hours)
    for relation in state.relationships.values():
        relation.irritation *= relation_factor
        relation.unresolved_tension *= relation_factor

    state.updated_at = datetime.now(timezone.utc).isoformat()
