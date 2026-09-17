"""Shared event-family transitions and decay for the v2 affect model."""

from __future__ import annotations

from .calculations import (
    event_severity,
    global_decay_factor,
    humor_compatibility,
    pride_sensitivity,
    reactivity_factor,
    relation_decay_factor,
    repair_factor,
    sensitivity_multiplier,
    social_receptivity,
    teasing_misunderstanding,
)
from .configuration import AffectConfig
from .events import AffectiveEvent, EventType
from .parameters import (
    FRICTION_STEP,
    HOSTILITY_STEP,
    HUMOR_STEP,
    MODERATION_STEP,
    POSITIVE_STEP,
    REPAIR_STEP,
    SECONDARY_SHARE,
)
from .relationships import HOSTILE_EVENTS, REPAIR_EVENTS
from .state import AffectState, ParticipantRelation, clamp


def _change(state: AffectState, *, valence=0.0, arousal=0.0, frustration=0.0, offended=0.0) -> None:
    state.valence = clamp(state.valence + valence)
    state.arousal = clamp(state.arousal + arousal, 0.0, 1.0)
    state.frustration = clamp(state.frustration + frustration, 0.0, 1.0)
    state.offended = clamp(state.offended + offended, 0.0, 1.0)


def _repair_relation(relation: ParticipantRelation, amount: float) -> None:
    relation.irritation = clamp(relation.irritation - amount, 0.0, 1.0)
    relation.unresolved_tension = clamp(relation.unresolved_tension - amount, 0.0, 1.0)


def refresh_conflicts(state: AffectState) -> None:
    """Heat/status are a projection of current relationships, including after decay."""
    state.open_conflicts = {
        participant: {"heat": relation.unresolved_tension, "status": "open"}
        for participant, relation in state.relationships.items()
        if relation.unresolved_tension > POSITIVE_STEP * SECONDARY_SHARE
    }


def apply_event(state: AffectState, event: AffectiveEvent, config: AffectConfig) -> str:
    """Apply a personally addressed event. Observations of others use observe_exchange."""
    if config.schema_version != 2:
        raise ValueError("Legacy affect configuration requires migration")
    relation = state.relationships.setdefault(event.speaker_id, ParticipantRelation())
    severity = event_severity(event)
    reaction = severity * reactivity_factor(config)
    kind = event.event_type
    rule = "unhandled_event"

    if kind == EventType.USER_MODERATION:
        # Authority has a fixed effect, never weighted by personality or speaker credibility.
        amount = MODERATION_STEP
        if event.action == "calm":
            _change(state, arousal=-amount, frustration=-amount, offended=-amount)
            state.atmosphere_tension = clamp(state.atmosphere_tension - amount, 0.0, 1.0)
            for item in state.relationships.values():
                _repair_relation(item, amount)
            for edge in state.social_edges:
                edge["tension"] = clamp(edge["tension"] - amount, 0.0, 1.0)
            for record in state.observed_participants.values():
                record["frustration"] = clamp(record.get("frustration", 0.0) - amount, 0.0, 1.0)
            rule = "verified_user_calm"
        else:
            _change(state, arousal=amount, frustration=amount * SECONDARY_SHARE)
            rule = "verified_user_heat"
    elif kind in {EventType.PRAISE, EventType.SUPPORT}:
        amount = POSITIVE_STEP * reaction
        _change(state, valence=amount, arousal=amount * SECONDARY_SHARE)
        relation.trust = clamp(relation.trust + amount)
        relation.affinity = clamp(relation.affinity + amount)
        _repair_relation(relation, amount * SECONDARY_SHARE)
        rule = "positive_social_signal"
    elif kind == EventType.JOKE:
        playfulness = config.traits["playfulness"]
        amount = HUMOR_STEP * reaction
        _change(
            state,
            valence=amount * playfulness,
            arousal=amount,
            frustration=amount * (1.0 - playfulness) * SECONDARY_SHARE,
        )
        relation.affinity = clamp(relation.affinity + amount * playfulness)
        rule = "playful_signal" if playfulness >= SECONDARY_SHARE else "serious_joke_interpretation"
    elif kind == EventType.TEASING:
        # Similar playful temperaments turn teasing into banter; pride/status raises its cost.
        playfulness = config.traits["playfulness"]
        compatibility = humor_compatibility(config, relation)
        friction = (
            HUMOR_STEP
            * reaction
            * teasing_misunderstanding(playfulness)
            * pride_sensitivity(config)
            * (2.0 - compatibility)
        )
        friction *= sensitivity_multiplier(config, event)
        friction *= 1.0 + relation.unresolved_tension
        enjoyment = HUMOR_STEP * reaction * playfulness * compatibility
        _change(
            state,
            valence=enjoyment - friction,
            arousal=max(enjoyment, friction),
            frustration=friction,
            offended=friction * config.traits["pride"],
        )
        relation.affinity = clamp(relation.affinity + enjoyment - friction)
        relation.irritation = clamp(relation.irritation + friction, 0.0, 1.0)
        relation.unresolved_tension = clamp(
            relation.unresolved_tension + max(0.0, friction - enjoyment),
            0.0,
            1.0,
        )
        rule = "playful_banter" if enjoyment >= friction else "teasing_tension"
    elif kind in HOSTILE_EVENTS:
        amount = HOSTILITY_STEP * reaction
        offense = amount * pride_sensitivity(config) * sensitivity_multiplier(config, event)
        # Existing relationships can soften an injury but cannot erase it.
        offense *= 1.0 - SECONDARY_SHARE * social_receptivity(config, relation)
        offense *= 1.0 + relation.unresolved_tension
        _change(state, valence=-amount, arousal=amount, frustration=amount, offended=offense)
        relation.irritation = clamp(relation.irritation + amount, 0.0, 1.0)
        relation.unresolved_tension = clamp(relation.unresolved_tension + offense, 0.0, 1.0)
        relation.trust = clamp(relation.trust - offense * SECONDARY_SHARE)
        relation.respect = clamp(relation.respect - offense * SECONDARY_SHARE)
        relation.affinity = clamp(relation.affinity - offense)
        rule = (
            "leadership_challenge" if kind == EventType.LEADERSHIP_CHALLENGE else "direct_offense"
        )
    elif kind == EventType.DISAGREEMENT:
        amount = FRICTION_STEP * reaction
        _change(state, arousal=amount, frustration=amount * SECONDARY_SHARE)
        # Civil disagreement alone is not personal disrespect or an open conflict.
        rule = "disagreement_pressure"
    elif kind in REPAIR_EVENTS:
        amount = REPAIR_STEP * reaction * repair_factor(config, relation)
        _change(
            state,
            valence=amount * SECONDARY_SHARE,
            arousal=-amount,
            frustration=-amount,
            offended=-amount,
        )
        if kind == EventType.BOT_MEDIATION:
            for item in state.relationships.values():
                _repair_relation(item, amount)
            relation.respect = clamp(relation.respect + amount)
            rule = "social_mediation"
        else:
            _repair_relation(relation, amount)
            relation.trust = clamp(relation.trust + amount * SECONDARY_SHARE)
            rule = "repair_signal"
    elif kind == EventType.TOPIC_STEERING:
        relation.respect = clamp(relation.respect + POSITIVE_STEP * reaction * SECONDARY_SHARE)
        rule = "topic_steering"
    elif kind == EventType.FRUSTRATION:
        # This is evidence of the speaker's distress, not an insult to the listener.
        rule = "expressed_frustration"

    refresh_conflicts(state)
    return rule


def decay_state(state: AffectState, config: AffectConfig, elapsed_hours: float) -> None:
    """The caller owns the clock; persistence has only this passive decay role."""
    if elapsed_hours <= 0:
        refresh_conflicts(state)
        return
    factor = global_decay_factor(config, elapsed_hours)
    for name in ("valence", "arousal", "frustration", "offended"):
        setattr(state, name, getattr(state, name) * factor)
    state.atmosphere_tension *= factor
    relation_factor = relation_decay_factor(config, elapsed_hours)
    for relation in state.relationships.values():
        relation.irritation *= relation_factor
        relation.unresolved_tension *= relation_factor
    for edge in state.social_edges:
        edge["tension"] *= relation_factor
    for record in state.observed_participants.values():
        record["frustration"] = record.get("frustration", 0.0) * factor
    refresh_conflicts(state)
