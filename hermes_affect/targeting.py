"""Conservative identity resolution using only delivered host metadata and message text."""

from __future__ import annotations

import re
from dataclasses import replace

from .config import AffectConfig
from .events import AffectiveEvent, EventType


def identity_variants(value: str) -> set[str]:
    value = value.strip().casefold()
    return {value, value.split(":", 1)[-1]}


def canonical_target(value: str, participants: list[str]) -> str | None:
    matches = [p for p in participants if value.strip().casefold() in identity_variants(p)]
    return matches[0] if len(matches) == 1 else None


def route_events(
    events: list[AffectiveEvent],
    message: str,
    *,
    bot_ids: list[str],
    participants: list[str],
    explicit_target: str = "",
    is_group: bool = False,
    config: AffectConfig,
) -> list[AffectiveEvent]:
    bot_variants = set().union(*(identity_variants(value) for value in bot_ids))
    result = []
    for event in events:
        if event.event_type == EventType.USER_MODERATION:
            result.append(replace(event, target="bot", target_id=bot_ids[0]))
            continue
        target_id = event.target_id
        target = event.target
        if event.source == "deterministic":
            if explicit_target:
                target_id = canonical_target(explicit_target, participants)
                if explicit_target.casefold() in bot_variants:
                    target_id = bot_ids[0]
                if target_id is None:
                    # An explicit unknown recipient must not fall back to a personal event.
                    continue
            else:
                # Only a direct vocative prefix, not incidental mention of another participant.
                candidates = [
                    p
                    for p in participants
                    if any(
                        re.match(
                            rf"^\s*@?{re.escape(alias)}(?:\s*[:,]|\s+you\b)",
                            message,
                            re.I,
                        )
                        for alias in identity_variants(p)
                    )
                ]
                candidates = list(
                    dict.fromkeys(
                        bot_ids[0] if p.casefold() in bot_variants else p for p in candidates
                    )
                )
                target_id = candidates[0] if len(candidates) == 1 else None
            if target_id:
                target = "bot" if target_id.casefold() in bot_variants else "participant"
            elif is_group:
                # Expressed distress is evidence about the speaker even with no addressee.
                if event.event_type != EventType.FRUSTRATION:
                    continue
                target = "participant"
            else:
                target, target_id = "bot", bot_ids[0]
        attributes = dict(event.attributes)
        if target == "bot":
            matches = [
                s
                for s in config.sensitivities
                if re.search(rf"(?<!\w){re.escape(s.topic)}(?!\w)", message, re.I)
            ]
            if matches:
                attributes["topic"] = max(matches, key=lambda s: s.intensity).topic
        result.append(
            replace(
                event,
                target=target,
                target_id=target_id[:200] if target_id else None,
                attributes=attributes,
            )
        )
    return result
