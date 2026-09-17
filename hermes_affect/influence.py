"""Local social perception; no global atmosphere or access to other bot state."""

from __future__ import annotations

from .calculations import event_severity, temperament_drives
from .config import AffectConfig
from .events import AffectiveEvent, EventType
from .models import SOCIAL_RECORD_LIMIT, AffectState, ParticipantRelation, clamp, utc_now
from .parameters import HOSTILITY_STEP, POSITIVE_STEP, REPAIR_STEP, STYLE_LEARNING_RATE

HOSTILE_EVENTS = frozenset(
    {
        EventType.INSULT,
        EventType.BOT_PROVOCATION,
        EventType.LEADERSHIP_CHALLENGE,
    }
)
REPAIR_EVENTS = frozenset({EventType.APOLOGY, EventType.RECONCILIATION, EventType.BOT_MEDIATION})
POSITIVE_EVENTS = frozenset({EventType.PRAISE, EventType.SUPPORT, EventType.JOKE})


def observe_style(relation: ParticipantRelation, event_type: EventType) -> None:
    """Four binary behavioral signals replace the old 52-value style table."""
    signals = {
        "supportive": event_type in POSITIVE_EVENTS | REPAIR_EVENTS,
        "playful": event_type in {EventType.JOKE, EventType.TEASING},
        "confrontational": event_type in HOSTILE_EVENTS | {EventType.TEASING},
        "cooperative": event_type in POSITIVE_EVENTS | REPAIR_EVENTS | {EventType.TOPIC_STEERING},
    }
    for name, signal in signals.items():
        previous = relation.observed_style.get(name, 0.5)
        relation.observed_style[name] = previous + STYLE_LEARNING_RATE * (float(signal) - previous)
    relation.updated_at = utc_now()


def observe_exchange(state: AffectState, event: AffectiveEvent, config: AffectConfig) -> None:
    """Observe a resolved event. Receiving hostility is not proof of distress."""
    relation = state.relationships.setdefault(event.speaker_id, ParticipantRelation())
    observe_style(relation, event.event_type)
    severity = event_severity(event)
    sensitivity = temperament_drives(config)["atmosphere_sensitivity"]
    hostile = event.event_type in HOSTILE_EVENTS
    teasing = event.event_type == EventType.TEASING
    repair = event.event_type in REPAIR_EVENTS
    amount = HOSTILITY_STEP * severity * sensitivity if hostile or teasing else 0.0
    if teasing:
        amount *= 1.0 - config.traits["playfulness"]
    if event.event_type == EventType.FRUSTRATION:
        amount = HOSTILITY_STEP * severity * sensitivity
    if repair or event.event_type in POSITIVE_EVENTS:
        step = REPAIR_STEP if repair else POSITIVE_STEP
        amount = -step * severity
    state.atmosphere_tension = clamp(state.atmosphere_tension + amount, 0.0, 1.0)

    if event.target_id and event.target_id != event.speaker_id:
        edge = next(
            (
                e
                for e in state.social_edges
                if e["speaker_id"] == event.speaker_id and e["target_id"] == event.target_id
            ),
            None,
        )
        if edge is None:
            edge = {"speaker_id": event.speaker_id, "target_id": event.target_id, "tension": 0.0}
            state.social_edges.append(edge)
        else:
            state.social_edges.remove(edge)
            state.social_edges.append(edge)
        edge["tension"] = clamp(edge["tension"] + amount, 0.0, 1.0)
        edge["last_event"] = event.event_type.value
        if repair:
            for reverse in state.social_edges:
                if (
                    reverse["speaker_id"] == event.target_id
                    and reverse["target_id"] == event.speaker_id
                ):
                    reverse["tension"] = clamp(reverse["tension"] + amount, 0.0, 1.0)
        del state.social_edges[:-SOCIAL_RECORD_LIMIT]

    # Only expressed frustration raises an estimate of that speaker's distress.
    if event.event_type == EventType.FRUSTRATION:
        record = state.observed_participants.setdefault(event.speaker_id, {"frustration": 0.0})
        record["frustration"] = clamp(
            record.get("frustration", 0.0) + severity * HOSTILITY_STEP, 0.0, 1.0
        )
    elif repair and event.speaker_id in state.observed_participants:
        record = state.observed_participants[event.speaker_id]
        record["frustration"] = clamp(
            record.get("frustration", 0.0) - REPAIR_STEP * severity, 0.0, 1.0
        )
    while len(state.observed_participants) > SOCIAL_RECORD_LIMIT:
        del state.observed_participants[next(iter(state.observed_participants))]
