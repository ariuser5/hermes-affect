"""Core library for the Hermes Affect plugin."""

from .config import AffectConfig, neutral_config, parse_soul_affect
from .events import AffectiveEvent, EventClassifier, EventType
from .models import AffectState, ParticipantRelation
from .posture import ResponsePosture, derive_posture

__all__ = [
    "AffectConfig",
    "AffectState",
    "AffectiveEvent",
    "EventClassifier",
    "EventType",
    "ParticipantRelation",
    "ResponsePosture",
    "derive_posture",
    "neutral_config",
    "parse_soul_affect",
]
