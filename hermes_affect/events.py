"""Deterministic event classification for the MVP."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class EventType(str, Enum):
    PRAISE = "praise"
    SUPPORT = "support"
    JOKE = "joke"
    TEASING = "teasing"
    INSULT = "insult"
    DISAGREEMENT = "disagreement"
    IGNORED = "being_ignored"
    APOLOGY = "apology"
    RECONCILIATION = "reconciliation"
    USER_MODERATION = "user_moderation"
    BOT_MEDIATION = "bot_mediation"
    BOT_PROVOCATION = "bot_provocation"
    TOPIC_STEERING = "topic_steering"
    LEADERSHIP_CHALLENGE = "challenge_to_leadership"


@dataclass(frozen=True)
class AffectiveEvent:
    event_type: EventType
    speaker_id: str
    action: str | None = None
    confidence: float = 1.0
    attributes: dict[str, str] = field(default_factory=dict)


class EventClassifier:
    """Classify only clear signals; ambiguous text remains unclassified."""

    _rules = (
        (EventType.PRAISE, (r"\bgood job\b", r"\bwell done\b", r"\bexcellent\b", r"\bthank you\b")),
        (EventType.SUPPORT, (r"\bi agree\b", r"\bi support\b", r"\bi('m| am) with you\b")),
        (EventType.JOKE, (r"\b哈哈\b", r"\bhaha\b", r"\blol\b", r"just kidding", r"joking")),
        (EventType.APOLOGY, (r"\bsorry\b", r"my apologies", r"i apologize")),
        (EventType.RECONCILIATION, (r"move on", r"make peace", r"let's reset", r"no hard feelings")),
        (EventType.INSULT, (r"\bidiot\b", r"\bstupid\b", r"\bshut up\b", r"\byou are useless\b")),
        (EventType.DISAGREEMENT, (r"\bi disagree\b", r"\bthat is wrong\b", r"\bno,\b", r"but that")),
        (EventType.TEASING, (r"you always", r"look who is talking", r"nice try")),
    )

    def classify(
        self,
        message: str,
        *,
        speaker_id: str,
        speaker_kind: str = "unknown",
        verified_user: bool = False,
    ) -> list[AffectiveEvent]:
        text = " ".join(message.lower().split())
        events: list[AffectiveEvent] = []

        if verified_user and re.search(
            r"\b(stop this|calm down|lower the tone|do not continue being rude|don't be rude)\b",
            text,
        ):
            events.append(AffectiveEvent(EventType.USER_MODERATION, speaker_id, action="calm"))
        elif verified_user and re.search(r"\b(don't hold back|continue the argument|you may continue)\b", text):
            events.append(AffectiveEvent(EventType.USER_MODERATION, speaker_id, action="heat"))

        if speaker_kind == "bot" and re.search(r"\b(both of you|calm down|lower the tone|mediate)\b", text):
            events.append(AffectiveEvent(EventType.BOT_MEDIATION, speaker_id))
        if speaker_kind == "bot" and re.search(r"\b(challenge|provoke|fight|you are useless)\b", text):
            events.append(AffectiveEvent(EventType.BOT_PROVOCATION, speaker_id))
        if re.search(r"\b(you are not in charge|who put you in charge|stop ordering us)\b", text):
            events.append(AffectiveEvent(EventType.LEADERSHIP_CHALLENGE, speaker_id))
        if re.search(r"\b(let's talk about|change the subject|back to the topic|moving on to)\b", text):
            events.append(AffectiveEvent(EventType.TOPIC_STEERING, speaker_id))

        for event_type, patterns in self._rules:
            if any(re.search(pattern, text) for pattern in patterns):
                events.append(AffectiveEvent(event_type, speaker_id))
        return events
