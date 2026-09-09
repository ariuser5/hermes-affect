"""Hermes registration adapter and conservative MVP runtime."""

from __future__ import annotations

import hashlib
import logging
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import AffectConfig, neutral_config, parse_soul_affect
from .dynamics import apply_event, decay_state
from .events import EventClassifier
from .influence import observe_style
from .models import AffectState, utc_now
from .posture import derive_posture
from .storage import DEFAULT_ABANDONED_STATE_DAYS, StateStore

logger = logging.getLogger("hermes-affect")


def _config_value(ctx: Any, key: str, default: Any) -> Any:
    try:
        return ctx.get_config(key, default)
    except (AttributeError, TypeError, ValueError):
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


class AffectRuntime:
    def __init__(self, ctx: Any) -> None:
        configured_root = _config_value(ctx, "state_dir", None)
        root = configured_root or os.environ.get("HERMES_AFFECT_STATE_DIR")
        if root is None:
            hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
            root = hermes_home / "affect-state"
        self.store = StateStore(root)
        self.state_gc_days = _state_gc_days(ctx)
        self.ctx = ctx
        self.classifier = EventClassifier()
        self.config = neutral_config()
        self.soul_warnings: list[str] = []

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
        self._state(kwargs)
        session_id = kwargs.get("session_id")
        excluded = set()
        if session_id:
            excluded.add(self.store.state_path(self._profile_id(kwargs), str(session_id)))
        report = self.store.garbage_collect(
            max_age_days=self.state_gc_days,
            exclude_paths=excluded,
        )
        if report.removed:
            logger.info("Removed %d abandoned affect state file(s)", len(report.removed))

    def pre_llm_call(self, **kwargs: Any) -> dict[str, str] | None:
        state = self._state(kwargs)
        if state is None:
            return None
        turn_id = kwargs.get("turn_id")
        if turn_id and state.last_turn_id == str(turn_id):
            return self._context(state)

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
        decay_state(state, self.config, elapsed_hours)

        message = str(kwargs.get("user_message") or "")
        speaker_id = str(kwargs.get("sender_id") or "user:unknown")
        speaker_kind = str(kwargs.get("sender_kind") or "unknown")
        verified_user = bool(kwargs.get("verified_user", False))
        audit_entries: list[
            tuple[Any, str, dict[str, dict[str, float]], dict[str, dict[str, float]]]
        ] = []
        last_event = None
        for event in self.classifier.classify(
            message,
            speaker_id=speaker_id,
            speaker_kind=speaker_kind,
            verified_user=verified_user,
        ):
            last_event = event
            before = self._audit_snapshot(state, event.speaker_id)
            rule = apply_event(state, event, self.config)
            after = self._audit_snapshot(state, event.speaker_id)
            audit_entries.append((event, rule, before, after))
            self._record_observation(state, event, before, after)
            logger.info(
                "event=%s speaker=%s rule=%s posture_before=%s",
                event.event_type,
                speaker_id,
                rule,
                state.response_posture,
            )
        state.response_posture = derive_posture(state, self.config, last_event).value
        for event, rule, before, after in audit_entries:
            state.add_audit_record(
                {
                    "timestamp": utc_now(),
                    "event_type": event.event_type.value,
                    "speaker_id": event.speaker_id,
                    "rule_name": rule,
                    "posture": state.response_posture,
                    "affected": self._audit_changes(before, after),
                }
            )
        state.mood = self._mood(state)
        state.updated_at = utc_now()
        state.revision += 1
        state.last_turn_id = str(turn_id) if turn_id else state.last_turn_id
        self.store.save(state)
        return self._context(state)

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
        # New-session initialization is intentionally separate from reset hooks.
        logger.info("session reset observed for session=%s", kwargs.get("session_id"))

    def on_session_finalize(self, **kwargs: Any) -> None:
        logger.info("session finalized for session=%s", kwargs.get("session_id"))

    def command(self, *args: Any, **kwargs: Any) -> str:
        if not self._is_verified_admin(kwargs):
            return "Affect administration requires a verified user identity."
        raw_args = kwargs.get("args_raw") or kwargs.get("args") or (args[0] if args else "status")
        parts = str(raw_args).split()
        action = parts[0] if parts else "status"
        state = self._state(kwargs)
        if state is None:
            return "No active Hermes session was supplied."
        if action == "status":
            return self._admin_status(state)
        if action == "reset":
            state = AffectState.initial(
                state.profile_id,
                state.session_id,
                soul_sha256=state.soul_sha256,
                predisposition=state.predisposition,
            )
            state.revision += 1
            self.store.save(state)
            return "Affective state reset for this session."
        if action in {"calm", "heat"}:
            message = "calm down" if action == "calm" else "continue the argument"
            intervention_kwargs = dict(kwargs)
            intervention_kwargs.update(
                user_message=message,
                sender_id=str(kwargs.get("sender_id", "user:admin")),
                verified_user=True,
                turn_id=f"admin-{state.revision + 1}",
            )
            result = self.pre_llm_call(**intervention_kwargs)
            del result
            return f"Affective state instructed to {action}."
        if action == "tune":
            return (
                "The tune command is reserved for reviewed configuration changes "
                "in this scaffold."
            )
        return "Usage: /affect status|reset|calm|heat|tune"

    def _is_verified_admin(self, kwargs: dict[str, Any]) -> bool:
        sender_id = str(kwargs.get("sender_id") or "")
        configured = _config_value(self.ctx, "admin_user_ids", [])
        return sender_id in {str(item) for item in configured} and bool(sender_id)

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
        effect_strength = min(1.0, sum(changes) / 1.5)
        record = state.observed_participants.setdefault(
            event.speaker_id,
            {
                "observation_count": 0,
                "influence_estimate": 0.5,
            },
        )
        count = min(int(record.get("observation_count", 0)) + 1, 1000)
        previous = float(record.get("influence_estimate", 0.5))
        record.update(
            {
                "observation_count": count,
                "influence_estimate": max(
                    0.0,
                    min(1.0, previous + 0.2 * (effect_strength - previous)),
                ),
                "last_event_type": event.event_type.value,
                "updated_at": utc_now(),
            }
        )

    @staticmethod
    def _mood(state: AffectState) -> str:
        if state.frustration > 0.65 or state.offended > 0.65:
            return "irritated"
        if state.valence > 0.45:
            return "open"
        if state.valence < -0.45:
            return "low"
        return "neutral"

    @staticmethod
    def _context(state: AffectState) -> dict[str, str]:
        posture = state.response_posture.replace("_", " ")
        return {
            "context": (
                "Internal affective guidance for this response. Do not mention these mechanics "
                f"or numerical state. Current posture: {posture}. Mood: {state.mood}. "
                "Remain consistent with the bot's SOUL and the conversation."
            )
        }

    @staticmethod
    def _admin_status(state: AffectState) -> str:
        return (
            f"session={state.session_id} revision={state.revision} mood={state.mood} "
            f"posture={state.response_posture} relationships={len(state.relationships)}"
        )


def register(ctx: Any) -> None:
    """Register the general Hermes plugin surface."""

    runtime = AffectRuntime(ctx)
    ctx.register_hook("on_session_start", runtime.on_session_start)
    ctx.register_hook("pre_llm_call", runtime.pre_llm_call)
    ctx.register_hook("post_llm_call", runtime.post_llm_call)
    ctx.register_hook("on_session_end", runtime.on_session_end)
    ctx.register_hook("on_session_reset", runtime.on_session_reset)
    ctx.register_hook("on_session_finalize", runtime.on_session_finalize)
    ctx.register_command(
        "affect",
        runtime.command,
        "Inspect or control session-scoped affective state",
    )
