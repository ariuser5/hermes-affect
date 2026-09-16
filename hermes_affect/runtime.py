"""Affect runtime orchestration behind the Hermes integration adapter."""

from __future__ import annotations

import hashlib
import logging
import math
import os
from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .commands import AffectCommandHandler
from .config import AffectConfig, neutral_config, parse_soul_affect
from .dynamics import apply_event, decay_state
from .events import EventClassifier, EventType
from .influence import observe_style
from .models import AffectState, utc_now
from .parameters import (
    CONTEXT_CONTROLLED_DRIVE_THRESHOLD,
    CONTEXT_GENTLE_DRIVE_THRESHOLD,
    CONTEXT_TENSE_DRIVE_THRESHOLD,
    INFLUENCE_ESTIMATE_LEARNING_RATE,
    MAX_OBSERVATION_COUNT,
    OBSERVATION_EFFECT_NORMALIZER,
    TERSE_AFFECT_THRESHOLD,
    WARM_VALENCE_THRESHOLD,
)
from .posture import ResponsePosture, derive_posture, effective_expression_drive
from .semantic import (
    SemanticClassifier,
    SemanticClassifierConfig,
    arbitrate_classifications,
)
from .storage import DEFAULT_ABANDONED_STATE_DAYS, StateStore

logger = logging.getLogger("hermes-affect")
SEMANTIC_CLASSIFIER_TASK = "hermes_affect_classifier"


def _config_value(ctx: Any, key: str, default: Any) -> Any:
    missing = object()
    try:
        value = ctx.get_config(key, missing)
        if value is not missing and value is not None:
            return value
        plugin_config = ctx.get_config("hermes-affect", missing)
        if isinstance(plugin_config, Mapping) and key in plugin_config:
            return plugin_config[key]
    except (AttributeError, TypeError, ValueError):
        pass
    return default


def _state_gc_days(ctx: Any) -> float:
    configured = _config_value(ctx, "state_gc_days", DEFAULT_ABANDONED_STATE_DAYS)
    if (
        isinstance(configured, bool)
        or not isinstance(configured, (int, float))
        or not math.isfinite(float(configured))
        or configured <= 0
    ):
        logger.warning(
            "Invalid state_gc_days setting; using default of %s days",
            DEFAULT_ABANDONED_STATE_DAYS,
        )
        return float(DEFAULT_ABANDONED_STATE_DAYS)
    return float(configured)


def _shadow_mode(ctx: Any) -> bool:
    configured = _config_value(ctx, "shadow_mode", False)
    if isinstance(configured, bool):
        return configured
    logger.warning("Invalid shadow_mode setting; using disabled mode")
    return False


class AffectRuntime:
    def __init__(self, ctx: Any) -> None:
        configured_root = _config_value(ctx, "state_dir", None)
        root = configured_root or os.environ.get("HERMES_AFFECT_STATE_DIR")
        if root is None:
            hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
            root = hermes_home / "affect-state"
        self.store = StateStore(root)
        self.state_gc_days = _state_gc_days(ctx)
        self.shadow_mode = _shadow_mode(ctx)
        self.ctx = ctx
        self.classifier = EventClassifier()
        self.semantic_config, semantic_warnings = SemanticClassifierConfig.from_mapping(
            _config_value(ctx, "semantic_classifier", None)
        )
        for warning in semantic_warnings:
            logger.warning("%s", warning)
        self.semantic_classifier = SemanticClassifier(
            ctx,
            self.semantic_config,
            task_name=SEMANTIC_CLASSIFIER_TASK,
        )
        self._semantic_call_active = False
        self.config = neutral_config()
        self.soul_warnings: list[str] = []
        self.command_handler = AffectCommandHandler(self)

    def _profile_id(self, kwargs: dict[str, Any]) -> str:
        profile_id = kwargs.get("profile_id") or kwargs.get("profile_name")
        return str(profile_id or os.environ.get("HERMES_PROFILE", "default"))

    def _soul_path(self, kwargs: dict[str, Any]) -> Path:
        configured = _config_value(self.ctx, "soul_path", None)
        if configured:
            return Path(configured).expanduser()
        if kwargs.get("soul_path"):
            return Path(kwargs["soul_path"]).expanduser()
        hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
        return hermes_home / "SOUL.md"

    def _load_config(self, kwargs: dict[str, Any]) -> tuple[AffectConfig, str | None]:
        path = self._soul_path(kwargs)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self.soul_warnings = []
            return neutral_config(), None
        config, warnings = parse_soul_affect(text)
        self.soul_warnings = warnings
        for warning in warnings:
            logger.warning("%s", warning)
        return config, hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _state(self, kwargs: dict[str, Any]) -> AffectState | None:
        session_id = kwargs.get("session_id")
        if not session_id:
            return None
        profile_id = self._profile_id(kwargs)
        state = self.store.load(profile_id, str(session_id))
        if state is None:
            parent_session_id = kwargs.get("parent_session_id")
            if parent_session_id and str(parent_session_id) != str(session_id):
                parent = self.store.load(profile_id, str(parent_session_id))
                if parent is not None:
                    state = AffectState.continued_from(parent, str(session_id))
                    self.store.save(state)
                    return state
            config, soul_hash = self._load_config(kwargs)
            state = AffectState.initial(
                profile_id,
                str(session_id),
                soul_sha256=soul_hash,
                predisposition=config.to_dict(),
            )
            self.store.save(state)
        return state

    def on_session_start(self, **kwargs: Any) -> None:
        self.config, _ = self._load_config(kwargs)
        session_id = kwargs.get("session_id")
        if not session_id:
            logger.warning(
                "Session start has no session_id; skipping affect state initialization "
                "and garbage collection"
            )
            return
        self._state(kwargs)
        excluded = {self.store.state_path(self._profile_id(kwargs), str(session_id))}
        report = self.store.garbage_collect(
            max_age_days=self.state_gc_days,
            exclude_paths=excluded,
        )
        if report.removed:
            logger.info("Removed %d abandoned affect state file(s)", len(report.removed))

    def pre_llm_call(self, **kwargs: Any) -> dict[str, str] | None:
        if self._semantic_call_active:
            logger.warning("semantic_classification status=reentrant_call_ignored")
            return None
        state = self._state(kwargs)
        if state is None:
            return None
        config = self._config_for_state(state)
        turn_id = kwargs.get("turn_id")
        if turn_id and state.last_turn_id == str(turn_id):
            return None if self.shadow_mode else self._context(state, config)

        try:
            elapsed_hours = max(
                0.0,
                (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(state.updated_at)
                ).total_seconds()
                / 3600.0,
            )
        except (TypeError, ValueError):
            elapsed_hours = 0.0
        decay_state(state, config, elapsed_hours)

        message = str(kwargs.get("user_message") or "")
        speaker_id = str(kwargs.get("sender_id") or "user:unknown")
        speaker_kind = str(kwargs.get("sender_kind") or "unknown")
        verified_user = bool(kwargs.get("verified_user", False))
        audit_entries: list[
            tuple[Any, str, dict[str, dict[str, float]], dict[str, dict[str, float]]]
        ] = []
        deterministic_events = self.classifier.classify(
            message,
            speaker_id=speaker_id,
            speaker_kind=speaker_kind,
            verified_user=verified_user,
        )
        events = deterministic_events
        if self.semantic_config.enabled and not any(
            event.event_type == EventType.USER_MODERATION for event in deterministic_events
        ):
            self._semantic_call_active = True
            try:
                semantic_outcome = self.semantic_classifier.classify(
                    message,
                    sender_id=speaker_id,
                    sender_kind=speaker_kind,
                    bot_name=self._bot_name(kwargs),
                    bot_aliases=self._bot_aliases(kwargs),
                    known_participants=self._known_participants(kwargs),
                    conversation_history=kwargs.get("conversation_history", ()),
                )
            finally:
                self._semantic_call_active = False
            events = arbitrate_classifications(
                deterministic_events,
                semantic_outcome,
                speaker_id=speaker_id,
                bot_identities=self._bot_identities(kwargs),
                min_confidence=self.semantic_config.min_confidence,
                fallback=self.semantic_config.fallback,
            )

        last_event = None
        for event in events:
            last_event = event
            before = self._audit_snapshot(state, event.speaker_id)
            rule = apply_event(state, event, config)
            after = self._audit_snapshot(state, event.speaker_id)
            audit_entries.append((event, rule, before, after))
            self._record_observation(state, event, before, after)
            logger.info(
                "event=%s source=%s confidence=%.2f speaker=%s rule=%s posture_before=%s",
                event.event_type,
                event.source,
                event.candidate_confidence,
                speaker_id,
                rule,
                state.response_posture,
            )
        state.response_posture = derive_posture(state, config, last_event).value
        for event, rule, before, after in audit_entries:
            state.add_audit_record(
                {
                    "timestamp": utc_now(),
                    "event_type": event.event_type.value,
                    "speaker_id": event.speaker_id,
                    "rule_name": rule,
                    "classification": {
                        "source": event.source,
                        "candidate_confidence": event.candidate_confidence,
                        "matched_rule": event.matched_rule,
                        "target": event.target,
                        "target_id": event.target_id,
                    },
                    "posture": state.response_posture,
                    "affected": self._audit_changes(before, after),
                }
            )
        state.mood = self._mood(state)
        state.updated_at = utc_now()
        state.revision += 1
        state.last_turn_id = str(turn_id) if turn_id else state.last_turn_id
        self.store.save(state)
        if self.shadow_mode:
            logger.info("shadow_mode active; affect context injection suppressed")
            return None
        return self._context(state, config)

    def post_llm_call(self, **kwargs: Any) -> None:
        state = self._state(kwargs)
        if state is not None:
            state.updated_at = utc_now()
            self.store.save(state)

    def on_session_end(self, **kwargs: Any) -> None:
        state = self._state(kwargs)
        if state is not None:
            state.updated_at = utc_now()
            self.store.save(state)

    def on_session_reset(self, **kwargs: Any) -> None:
        replacement_session_id = kwargs.get("new_session_id") or kwargs.get(
            "replacement_session_id"
        )
        if replacement_session_id:
            new_session_kwargs = dict(kwargs)
            new_session_kwargs["session_id"] = str(replacement_session_id)
            new_session_kwargs.pop("parent_session_id", None)
            self._state(new_session_kwargs)
            logger.info(
                "session reset established new affect session=%s",
                replacement_session_id,
            )
            return
        # Without a replacement ID, wait for the normal new-session callback.
        logger.info("session reset observed for session=%s", kwargs.get("session_id"))

    def on_session_finalize(self, **kwargs: Any) -> None:
        logger.info("session finalized for session=%s", kwargs.get("session_id"))

    def command(self, *args: Any, **kwargs: Any) -> str:
        return self.command_handler.handle(*args, **kwargs)

    def _is_verified_admin(self, kwargs: dict[str, Any]) -> bool:
        sender_id = str(kwargs.get("sender_id") or "")
        if str(kwargs.get("sender_kind") or "").lower() == "bot":
            return False
        if "verified_user" in kwargs and not bool(kwargs["verified_user"]):
            return False
        configured = _config_value(self.ctx, "admin_user_ids", [])
        return sender_id in {str(item) for item in configured} and bool(sender_id)

    def _config_for_state(self, state: AffectState) -> AffectConfig:
        tuning = dict(self.config.tuning)
        tuning.update(state.tuning_overrides)
        return replace(self.config, tuning=tuning)

    @staticmethod
    def _string_values(value: Any) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, Mapping):
            values = list(value.keys()) + list(value.values())
        elif isinstance(value, (list, tuple, set)):
            values = list(value)
        else:
            return []
        return [str(item) for item in values if isinstance(item, (str, int, float))]

    def _bot_name(self, kwargs: dict[str, Any]) -> str:
        for key in ("bot_name", "agent_name", "profile_name", "profile_id"):
            value = kwargs.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        configured = _config_value(self.ctx, "bot_name", "")
        return str(configured).strip() or self._profile_id(kwargs)

    def _bot_aliases(self, kwargs: dict[str, Any]) -> list[str]:
        values = []
        for key in ("bot_aliases", "agent_aliases"):
            values.extend(self._string_values(kwargs.get(key)))
        values.extend(self._string_values(_config_value(self.ctx, "bot_aliases", [])))
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))

    def _bot_identities(self, kwargs: dict[str, Any]) -> list[str]:
        values = []
        for key in (
            "bot_id",
            "bot_name",
            "agent_id",
            "agent_name",
            "profile_id",
            "profile_name",
        ):
            values.extend(self._string_values(kwargs.get(key)))
        values.extend(self._bot_aliases(kwargs))
        values.extend(self._string_values(_config_value(self.ctx, "bot_name", "")))
        values.extend(self._string_values(_config_value(self.ctx, "bot_id", "")))
        values.append(self._profile_id(kwargs))
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))

    def _known_participants(self, kwargs: dict[str, Any]) -> list[str]:
        values = []
        for key in (
            "known_participants",
            "known_bots",
            "participant_names",
            "bot_names",
            "participants",
        ):
            values.extend(self._string_values(kwargs.get(key)))
        configured = _config_value(self.ctx, "known_participants", [])
        values.extend(self._string_values(configured))
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))

    @staticmethod
    def _audit_snapshot(
        state: AffectState, participant_id: str
    ) -> dict[str, dict[str, float]]:
        relation = state.relationships.get(participant_id)
        return {
            "global": {
                "valence": state.valence,
                "arousal": state.arousal,
                "frustration": state.frustration,
                "offended": state.offended,
            },
            "relationship": {
                "trust": relation.trust if relation else 0.0,
                "affinity": relation.affinity if relation else 0.0,
                "irritation": relation.irritation if relation else 0.0,
                "respect": relation.respect if relation else 0.0,
                "unresolved_tension": relation.unresolved_tension if relation else 0.0,
            },
        }

    @staticmethod
    def _audit_changes(
        before: dict[str, dict[str, float]], after: dict[str, dict[str, float]]
    ) -> dict[str, dict[str, dict[str, float]]]:
        changed: dict[str, dict[str, dict[str, float]]] = {}
        for group, values in before.items():
            group_changes = {
                name: {"before": value, "after": after[group][name]}
                for name, value in values.items()
                if value != after[group][name]
            }
            if group_changes:
                changed[group] = group_changes
        return changed

    @staticmethod
    def _record_observation(
        state: AffectState,
        event: Any,
        before: dict[str, dict[str, float]],
        after: dict[str, dict[str, float]],
    ) -> None:
        relation = state.relationships[event.speaker_id]
        observe_style(relation, event.event_type)
        changes = [
            abs(after[group][name] - value)
            for group, values in before.items()
            for name, value in values.items()
            if (after[group][name] - value) != 0
        ]
        effect_strength = min(1.0, sum(changes) / OBSERVATION_EFFECT_NORMALIZER)
        record = state.observed_participants.setdefault(
            event.speaker_id,
            {
                "observation_count": 0,
                "influence_estimate": 0.5,
            },
        )
        count = min(int(record.get("observation_count", 0)) + 1, MAX_OBSERVATION_COUNT)
        previous = float(record.get("influence_estimate", 0.5))
        record.update(
            {
                "observation_count": count,
                "influence_estimate": max(
                    0.0,
                    min(
                        1.0,
                        previous
                        + INFLUENCE_ESTIMATE_LEARNING_RATE * (effect_strength - previous),
                    ),
                ),
                "last_event_type": event.event_type.value,
                "updated_at": utc_now(),
            }
        )

    @staticmethod
    def _mood(state: AffectState) -> str:
        if state.frustration > TERSE_AFFECT_THRESHOLD or state.offended > TERSE_AFFECT_THRESHOLD:
            return "irritated"
        if state.valence > WARM_VALENCE_THRESHOLD:
            return "open"
        if state.valence < -WARM_VALENCE_THRESHOLD:
            return "low"
        return "neutral"

    @staticmethod
    def _context(state: AffectState, config: AffectConfig) -> dict[str, str] | None:
        expression_gain = config.tuning["expression_gain"]
        if expression_gain <= 0.0:
            return None
        posture = state.response_posture.replace("_", " ")
        expression_drive = effective_expression_drive(state, config)
        if state.response_posture == ResponsePosture.RECONCILIATION.value:
            instruction = (
                "Acknowledge the repair attempt and lower the tension while remaining "
                "consistent with the bot's SOUL."
            )
        elif state.response_posture == ResponsePosture.PASS.value:
            instruction = (
                "Accept the moderation and return to calm, cooperative engagement while "
                "remaining consistent with the bot's SOUL."
            )
        elif state.response_posture == ResponsePosture.REFUSAL.value:
            instruction = (
                "Refuse to continue this exchange. Respond with exactly 🤨 and no other "
                "text. Resume normal engagement only after an apology or moderation has "
                "calmed the interaction."
            )
        elif expression_drive < CONTEXT_GENTLE_DRIVE_THRESHOLD:
            instruction = (
                "Keep the response measured and avoid amplifying the current emotional tone."
            )
        elif expression_drive < CONTEXT_CONTROLLED_DRIVE_THRESHOLD:
            instruction = (
                "Keep the response controlled, but let the current tension make it more "
                "concise and firm while remaining consistent with the bot's SOUL."
            )
        elif expression_drive < CONTEXT_TENSE_DRIVE_THRESHOLD:
            instruction = (
                "Keep the response terse and skeptical. A restrained sarcastic remark or "
                "direct challenge is acceptable when warranted, but do not add gratuitous "
                "hostility or pretend the conflict is resolved."
            )
        else:
            instruction = (
                "The conflict is intense. Let the current posture strongly shape tone and "
                "directness. If the user's message remains antagonistic, a proportional "
                "rebuttal, restrained sarcasm, or direct call-out is acceptable. Do not use "
                "threats, slurs, or gratuitous abuse. If refusing to engage, respond only "
                "with 🤨. Do not act reconciled until an apology or moderation calms the "
                "interaction."
            )
        return {
            "context": (
                "Internal affective guidance for this response. Do not mention these mechanics "
                f"or numerical state. Current posture: {posture}. Mood: {state.mood}. "
                f"{instruction}"
            )
        }
