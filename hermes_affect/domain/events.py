"""Domain event types and affective event value objects."""

from __future__ import annotations

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
    FRUSTRATION = "expressed_frustration"


@dataclass(frozen=True)
class AffectiveEvent:
    event_type: EventType
    speaker_id: str
    action: str | None = None
    confidence: float = 1.0
    attributes: dict[str, str] = field(default_factory=dict)
    source: str = "deterministic"
    matched_rule: str | None = None
    target: str = "unknown"
    target_id: str | None = None

    @property
    def candidate_confidence(self) -> float:
        """Expose the deterministic confidence name used by arbitration."""

        return self.confidence
