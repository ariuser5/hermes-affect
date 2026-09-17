"""Core library for the Hermes Affect plugin."""

from .application.classification.deterministic.classifier import EventClassifier
from .application.classification.semantic.classifier import (
    SemanticClassification,
    SemanticClassifierConfig,
    SemanticOutcome,
    arbitrate_classifications,
    validate_semantic_result,
)
from .domain.configuration import AffectConfig, neutral_config
from .domain.events import AffectiveEvent, EventType
from .domain.posture import ResponsePosture, derive_posture
from .domain.state import AffectState, ParticipantRelation
from .infrastructure.configuration.soul_loader import parse_soul_affect
from .infrastructure.hermes.semantic_provider import SemanticClassifier

__all__ = [
    "AffectConfig",
    "AffectState",
    "AffectiveEvent",
    "EventClassifier",
    "EventType",
    "ParticipantRelation",
    "ResponsePosture",
    "SemanticClassification",
    "SemanticClassifier",
    "SemanticClassifierConfig",
    "SemanticOutcome",
    "arbitrate_classifications",
    "derive_posture",
    "neutral_config",
    "parse_soul_affect",
    "validate_semantic_result",
]
