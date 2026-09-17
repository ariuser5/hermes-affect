"""Bounded affect transitions and persistence-based decay."""

from __future__ import annotations

from datetime import datetime, timezone

from .calculations import (
    event_severity,
    global_decay_factor,
    playful_signal_factor,
    pride_sensitivity,
    reactivity_factor,
    relation_decay_factor,
    sensitivity_multiplier,
    teasing_misunderstanding,
)
from .config import AffectConfig
from .events import AffectiveEvent, EventType
from .models import AffectState, ParticipantRelation, clamp, utc_now
from .parameters import (
    AFFINITY_GAIN,
    CONFLICT_CLEARED_TENSION_THRESHOLD,
    DISAGREEMENT_AROUSAL_GAIN,
    DISAGREEMENT_FRUSTRATION_GAIN,
    DISAGREEMENT_TENSION_GAIN,
    INSULT_AROUSAL_GAIN,
    INSULT_FRUSTRATION_GAIN,
    INSULT_IRRITATION_GAIN,
    INSULT_OFFENDED_GAIN,
    INSULT_TENSION_GAIN,
    INSULT_VALENCE_GAIN,
    IRRITATION_RELIEF_FROM_POSITIVE_SIGNAL,
    JOKE_AFFINITY_GAIN,
    JOKE_BASE_GAIN,
    JOKE_FRUSTRATION_GAIN,
    LEADERSHIP_CHALLENGE_BASE_GAIN,
    LEADERSHIP_CHALLENGE_RESPECT_LOSS,
    LEADERSHIP_CHALLENGE_TENSION_GAIN,
    MEDIATION_AROUSAL_RELIEF,
    MEDIATION_FRUSTRATION_RELIEF,
    MEDIATION_RESPECT_GAIN,
    MODERATION_CALM_AROUSAL_RELIEF,
    MODERATION_CALM_FRUSTRATION_RELIEF,
    MODERATION_CALM_IRRITATION_RELIEF,
    MODERATION_CALM_OFFENDED_RELIEF,
    MODERATION_CALM_TENSION_RELIEF,
    MODERATION_HEAT_AROUSAL_GAIN,
    MODERATION_HEAT_FRUSTRATION_GAIN,
    PRAISE_AROUSAL_GAIN,
    PRAISE_VALENCE_GAIN,
    REPAIR_AROUSAL_RELIEF,
    REPAIR_FRUSTRATION_RELIEF,
    REPAIR_IRRITATION_RELIEF,
    REPAIR_OFFENDED_RELIEF,
    REPAIR_TENSION_RELIEF,
    REPAIR_VALENCE_GAIN,
    SERIOUS_JOKE_IRRITATION_GAIN,
    SERIOUS_JOKE_PLAYFULNESS_THRESHOLD,
    TEASING_BASE_GAIN,
    TEASING_IRRITATION_GAIN,
    TEASING_TENSION_GAIN,
    TOPIC_STEERING_RESPECT_GAIN,
    TRUST_GAIN,
)


def _relation(state: AffectState, participant_id: str) -> ParticipantRelation:
    return state.relationships.setdefault(participant_id, ParticipantRelation())


def _change(state: AffectState, *, valence=0.0, arousal=0.0, frustration=0.0, offended=0.0) -> None:
    state.valence = clamp(state.valence + valence)
    state.arousal = clamp(state.arousal + arousal, 0.0, 1.0)
    state.frustration = clamp(state.frustration + frustration, 0.0, 1.0)
    state.offended = clamp(state.offended + offended, 0.0, 1.0)


def apply_event(state: AffectState, event: AffectiveEvent, config: AffectConfig) -> str:
    """Apply one event and return the inspectable rule name that fired."""

    escalation_gain = config.tuning["escalation_gain"]
    repair_gain = config.tuning["repair_gain"]
    reactivity = reactivity_factor(config)
    pride_factor = pride_sensitivity(config)
    sensitivity = sensitivity_multiplier(config, event)
    relation = _relation(state, event.speaker_id)

    if event.event_type in {EventType.PRAISE, EventType.SUPPORT}:
        _change(state, valence=PRAISE_VALENCE_GAIN, arousal=PRAISE_AROUSAL_GAIN)
        relation.trust = clamp(relation.trust + TRUST_GAIN)
        relation.affinity = clamp(relation.affinity + AFFINITY_GAIN)
        relation.irritation = clamp(
            relation.irritation - IRRITATION_RELIEF_FROM_POSITIVE_SIGNAL, 0.0, 1.0
        )
        return "positive_social_signal"
    if event.event_type == EventType.JOKE:
        playfulness = config.traits["playfulness"]
        _change(
            state,
            valence=JOKE_BASE_GAIN * playful_signal_factor(playfulness),
            arousal=JOKE_BASE_GAIN * playful_signal_factor(playfulness),
            frustration=JOKE_FRUSTRATION_GAIN * (1.0 - playfulness),
        )
        relation.affinity = clamp(
            relation.affinity + JOKE_AFFINITY_GAIN * playful_signal_factor(playfulness)
        )
        if playfulness < SERIOUS_JOKE_PLAYFULNESS_THRESHOLD:
            relation.irritation = clamp(
                relation.irritation + SERIOUS_JOKE_IRRITATION_GAIN, 0.0, 1.0
            )
            return "serious_joke_interpretation"
        return "playful_signal"
    if event.event_type == EventType.TEASING:
        misunderstanding = teasing_misunderstanding(config.traits["playfulness"])
        amount = TEASING_BASE_GAIN * escalation_gain * reactivity * misunderstanding
        _change(state, arousal=amount, frustration=amount)
        relation.irritation = clamp(
            relation.irritation + TEASING_IRRITATION_GAIN * escalation_gain * misunderstanding,
            0.0,
            1.0,
        )
        relation.unresolved_tension = clamp(
            relation.unresolved_tension + TEASING_TENSION_GAIN * escalation_gain * misunderstanding,
            0.0,
            1.0,
        )
        return "teasing_tension"
    if event.event_type in {EventType.INSULT, EventType.BOT_PROVOCATION}:
        impact = event_severity(event) * escalation_gain * reactivity * pride_factor * sensitivity
        _change(
            state,
            valence=-INSULT_VALENCE_GAIN * impact,
            arousal=INSULT_AROUSAL_GAIN * impact,
            frustration=INSULT_FRUSTRATION_GAIN * impact,
            offended=INSULT_OFFENDED_GAIN * impact,
        )
        relation.irritation = clamp(
            relation.irritation + INSULT_IRRITATION_GAIN * impact, 0.0, 1.0
        )
        relation.unresolved_tension = clamp(
            relation.unresolved_tension + INSULT_TENSION_GAIN * impact,
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
        amount = DISAGREEMENT_AROUSAL_GAIN * escalation_gain * reactivity
        _change(
            state,
            arousal=amount,
            frustration=DISAGREEMENT_FRUSTRATION_GAIN * escalation_gain * reactivity,
        )
        relation.unresolved_tension = clamp(
            relation.unresolved_tension + DISAGREEMENT_TENSION_GAIN * escalation_gain * reactivity,
            0.0,
            1.0,
        )
        return "disagreement_pressure"
    if event.event_type in {EventType.APOLOGY, EventType.RECONCILIATION}:
        _change(
            state,
            valence=REPAIR_VALENCE_GAIN * repair_gain,
            arousal=-REPAIR_AROUSAL_RELIEF * repair_gain,
            frustration=-REPAIR_FRUSTRATION_RELIEF * repair_gain,
            offended=-REPAIR_OFFENDED_RELIEF * repair_gain,
        )
        relation.irritation = clamp(
            relation.irritation - REPAIR_IRRITATION_RELIEF * repair_gain, 0.0, 1.0
        )
        relation.unresolved_tension = clamp(
            relation.unresolved_tension - REPAIR_TENSION_RELIEF * repair_gain,
            0.0,
            1.0,
        )
        if relation.unresolved_tension < CONFLICT_CLEARED_TENSION_THRESHOLD:
            state.open_conflicts.pop(event.speaker_id, None)
        return "repair_signal"
    if event.event_type == EventType.USER_MODERATION:
        if event.action == "calm":
            _change(
                state,
                arousal=-MODERATION_CALM_AROUSAL_RELIEF,
                frustration=-MODERATION_CALM_FRUSTRATION_RELIEF,
                offended=-MODERATION_CALM_OFFENDED_RELIEF,
            )
            for item in state.relationships.values():
                item.irritation = clamp(
                    item.irritation - MODERATION_CALM_IRRITATION_RELIEF, 0.0, 1.0
                )
                item.unresolved_tension = clamp(
                    item.unresolved_tension - MODERATION_CALM_TENSION_RELIEF, 0.0, 1.0
                )
            return "verified_user_calm"
        _change(
            state,
            arousal=MODERATION_HEAT_AROUSAL_GAIN,
            frustration=MODERATION_HEAT_FRUSTRATION_GAIN,
        )
        return "verified_user_heat"
    if event.event_type == EventType.BOT_MEDIATION:
        _change(
            state,
            arousal=-MEDIATION_AROUSAL_RELIEF,
            frustration=-MEDIATION_FRUSTRATION_RELIEF,
        )
        relation.respect = clamp(relation.respect + MEDIATION_RESPECT_GAIN)
        return "social_mediation"
    if event.event_type == EventType.LEADERSHIP_CHALLENGE:
        amount = LEADERSHIP_CHALLENGE_BASE_GAIN * escalation_gain * reactivity
        _change(state, arousal=amount, frustration=amount)
        relation.respect = clamp(relation.respect - LEADERSHIP_CHALLENGE_RESPECT_LOSS)
        relation.unresolved_tension = clamp(
            relation.unresolved_tension
            + LEADERSHIP_CHALLENGE_TENSION_GAIN * escalation_gain * reactivity,
            0.0,
            1.0,
        )
        return "leadership_challenge"
    if event.event_type == EventType.TOPIC_STEERING:
        relation.respect = clamp(relation.respect + TOPIC_STEERING_RESPECT_GAIN)
        return "topic_steering"
    return "unhandled_event"


def decay_state(state: AffectState, config: AffectConfig, elapsed_hours: float) -> None:
    """Decay state while letting high persistence retain tension longer."""

    if elapsed_hours <= 0:
        return
    global_factor = global_decay_factor(config, elapsed_hours)
    state.valence *= global_factor
    state.arousal *= global_factor
    state.frustration *= global_factor
    state.offended *= global_factor

    relation_factor = relation_decay_factor(config, elapsed_hours)
    for relation in state.relationships.values():
        relation.irritation *= relation_factor
        relation.unresolved_tension *= relation_factor

    state.updated_at = datetime.now(timezone.utc).isoformat()
