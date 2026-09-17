"""Hermes LLM provider adapter for semantic event classification."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from typing import Any

from ...application.classification.semantic.classifier import (
    CLASSIFIER_INSTRUCTIONS,
    SEMANTIC_CLASSIFICATION_SCHEMA,
    SemanticClassifierConfig,
    SemanticOutcome,
    build_classifier_input,
    validate_semantic_result,
)

logger = logging.getLogger("hermes-affect")


def _result_parsed(result: Any) -> Any:
    if isinstance(result, Mapping):
        parsed = result.get("parsed")
        text = result.get("text")
    else:
        parsed = getattr(result, "parsed", None)
        text = getattr(result, "text", None)
    if parsed is not None:
        if isinstance(parsed, str):
            try:
                return json.loads(parsed)
            except (TypeError, ValueError, json.JSONDecodeError):
                return None
        return parsed
    if isinstance(text, str):
        try:
            return json.loads(text)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
    return None


class SemanticClassifier:
    """Call Hermes' out-of-band structured LLM lane and fail closed."""

    def __init__(
        self,
        ctx: Any,
        config: SemanticClassifierConfig,
        *,
        task_name: str | None = None,
        task_registration_available: bool = True,
    ) -> None:
        self.ctx = ctx
        self.config = config
        self.task_name = task_name
        self.task_registration_available = task_registration_available

    def classify(
        self,
        message: str,
        *,
        sender_id: str,
        sender_kind: str,
        bot_name: str,
        bot_aliases: Sequence[str] = (),
        known_participants: Sequence[str] = (),
        conversation_history: Any = (),
    ) -> SemanticOutcome:
        if not self.config.enabled:
            return SemanticOutcome(None, "disabled")
        if not message.strip():
            return SemanticOutcome(None, "empty_message")
        if not self.task_registration_available:
            logger.warning(
                "semantic_classification status=unavailable "
                "reason=auxiliary_task_registration_missing"
            )
            return SemanticOutcome(None, "unavailable")
        llm = getattr(self.ctx, "llm", None)
        complete_structured = getattr(llm, "complete_structured", None)
        if not callable(complete_structured):
            logger.warning("semantic_classification status=unavailable reason=llm_surface_missing")
            return SemanticOutcome(None, "unavailable")
        classifier_input = build_classifier_input(
            message,
            sender_id=sender_id,
            sender_kind=sender_kind,
            bot_name=bot_name,
            bot_aliases=bot_aliases,
            known_participants=known_participants,
            conversation_history=conversation_history,
            config=self.config,
        )
        try:
            call_kwargs: dict[str, Any] = {
                "instructions": CLASSIFIER_INSTRUCTIONS,
                "input": [{"type": "text", "text": classifier_input}],
                "json_schema": SEMANTIC_CLASSIFICATION_SCHEMA,
                "schema_name": "hermes-affect.semantic-event",
                "purpose": "hermes-affect.semantic-classifier",
                "temperature": 0.0,
                "max_tokens": 128,
                "timeout": self.config.timeout_seconds,
            }
            if self.task_name is not None:
                call_kwargs["task"] = self.task_name
            result = complete_structured(**call_kwargs)
        except Exception as exc:  # The host/provider boundary must fail open to chat.
            logger.warning(
                "semantic_classification status=provider_failure error_type=%s",
                type(exc).__name__,
            )
            return SemanticOutcome(None, "provider_failure")

        classification = validate_semantic_result(_result_parsed(result))
        if classification is None:
            logger.warning("semantic_classification status=invalid_output")
            return SemanticOutcome(None, "invalid_output")
        logger.info(
            "semantic_classification status=ok event=%s target=%s target_id=%s "
            "confidence=%.2f severity=%s",
            classification.event,
            classification.target,
            classification.target_id or "",
            classification.confidence,
            classification.severity,
        )
        return SemanticOutcome(classification, "ok")
