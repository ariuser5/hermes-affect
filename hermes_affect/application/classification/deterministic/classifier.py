"""Deterministic event classification rules."""

from __future__ import annotations

import re

from ....domain.events import AffectiveEvent, EventType


class EventClassifier:
    """Classify only clear signals; ambiguous text remains unclassified."""

    _rules = (
        (
            EventType.FRUSTRATION,
            (
                r"\bi am frustrated\b",
                r"\bi'm frustrated\b",
                r"\bstop teasing me\b",
                r"\bthis is getting annoying\b",
            ),
            0.90,
            "expressed_frustration",
        ),
        (
            EventType.PRAISE,
            (r"\bgood job\b", r"\bwell done\b", r"\bexcellent\b", r"\bthank you\b"),
            0.90,
            "praise_explicit_phrase",
        ),
        (
            EventType.SUPPORT,
            (r"\bi agree\b", r"\bi support\b", r"\bi('m| am) with you\b"),
            0.90,
            "support_explicit_phrase",
        ),
        (
            EventType.JOKE,
            (r"\b哈哈\b", r"\bhaha\b", r"\blol\b", r"just kidding", r"joking"),
            0.90,
            "joke_explicit_phrase",
        ),
        (
            EventType.APOLOGY,
            (r"\bsorry\b", r"my apologies", r"i apologize"),
            0.90,
            "apology_explicit_phrase",
        ),
        (
            EventType.RECONCILIATION,
            (r"move on", r"make peace", r"let's reset", r"no hard feelings"),
            0.90,
            "reconciliation_explicit_phrase",
        ),
        (
            EventType.INSULT,
            (r"\bidiot\b", r"\bstupid\b"),
            0.55,
            "insult_generic_keyword",
        ),
        (
            EventType.INSULT,
            (r"\bshut up\b", r"\byou are useless\b"),
            0.90,
            "insult_explicit_direct_phrase",
        ),
        (
            EventType.DISAGREEMENT,
            (r"\bi disagree\b", r"\bthat is wrong\b"),
            0.90,
            "disagreement_explicit_phrase",
        ),
        (
            EventType.DISAGREEMENT,
            (r"\bno,\b", r"but that"),
            0.55,
            "disagreement_ambiguous_pattern",
        ),
        (
            EventType.TEASING,
            (r"you always", r"look who is talking", r"nice try"),
            0.40,
            "teasing_ambiguous_pattern",
        ),
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
            events.append(
                AffectiveEvent(
                    EventType.USER_MODERATION,
                    speaker_id,
                    action="calm",
                    confidence=1.0,
                    matched_rule="verified_moderation_calm",
                )
            )
        elif verified_user and re.search(
            r"\b(don't hold back|continue the argument|you may continue)\b", text
        ):
            events.append(
                AffectiveEvent(
                    EventType.USER_MODERATION,
                    speaker_id,
                    action="heat",
                    confidence=1.0,
                    matched_rule="verified_moderation_heat",
                )
            )

        if speaker_kind == "bot" and re.search(
            r"\b(both of you|calm down|lower the tone|mediate)\b", text
        ):
            events.append(
                AffectiveEvent(
                    EventType.BOT_MEDIATION,
                    speaker_id,
                    confidence=0.90,
                    matched_rule="bot_mediation_explicit_phrase",
                )
            )
        if speaker_kind == "bot" and re.search(
            r"\b(challenge|provoke|fight|you are useless)\b", text
        ):
            events.append(
                AffectiveEvent(
                    EventType.BOT_PROVOCATION,
                    speaker_id,
                    confidence=0.55,
                    matched_rule="bot_provocation_keyword",
                )
            )
        if re.search(r"\b(you are not in charge|who put you in charge|stop ordering us)\b", text):
            events.append(
                AffectiveEvent(
                    EventType.LEADERSHIP_CHALLENGE,
                    speaker_id,
                    confidence=0.90,
                    matched_rule="leadership_challenge_explicit_phrase",
                )
            )
        if re.search(
            r"\b(let's talk about|change the subject|back to the topic|moving on to)\b", text
        ):
            events.append(
                AffectiveEvent(
                    EventType.TOPIC_STEERING,
                    speaker_id,
                    confidence=0.90,
                    matched_rule="topic_steering_explicit_phrase",
                )
            )

        for event_type, patterns, confidence, matched_rule in self._rules:
            if any(re.search(pattern, text) for pattern in patterns):
                events.append(
                    AffectiveEvent(
                        event_type,
                        speaker_id,
                        confidence=confidence,
                        matched_rule=matched_rule,
                    )
                )
        return normalize_events(events)


def normalize_events(events: list[AffectiveEvent]) -> list[AffectiveEvent]:
    """One dominant intent per turn; authority precedes repair, then hostile signals.

    This intentionally avoids multiplying one phrase across overlapping regex rules.
    Semantic classification already supplies one intent. Mixed intent composition is
    deferred until clause-level targeting exists.
    """
    priority = (
        EventType.USER_MODERATION,
        EventType.APOLOGY,
        EventType.RECONCILIATION,
        EventType.BOT_MEDIATION,
        EventType.FRUSTRATION,
        EventType.BOT_PROVOCATION,
        EventType.INSULT,
        EventType.LEADERSHIP_CHALLENGE,
        EventType.TOPIC_STEERING,
        EventType.TEASING,
        EventType.JOKE,
        EventType.DISAGREEMENT,
        EventType.SUPPORT,
        EventType.PRAISE,
    )
    for kind in priority:
        matches = [e for e in events if e.event_type == kind]
        if matches:
            return [max(matches, key=lambda e: e.confidence)]
    return []
