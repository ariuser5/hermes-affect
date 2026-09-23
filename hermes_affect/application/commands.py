"""Hermes command parsing and session-state inspection."""

from __future__ import annotations

import json
from typing import Any

from ..domain.calculations import (
    credibility,
    effective_expression_drive,
    social_receptivity,
    temperament_drives,
)
from ..domain.state import AffectState
from .inspection import state_snapshot
from .tuning import SessionTuningService


class AffectCommandHandler:
    """Dispatch read-only inspection and verified state interventions."""

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime
        self.tuning = SessionTuningService()

    def handle(self, *args: Any, **kwargs: Any) -> str:
        raw_args = kwargs.get("args_raw") or kwargs.get("args") or (args[0] if args else "status")
        parts = str(raw_args).split()
        action = parts[0] if parts else "status"

        if action == "state":
            if len(parts) > 2:
                return "Usage: /affect state [profile]"
            profile_id = parts[1] if len(parts) == 2 else self.runtime._profile_id(kwargs)
            return self._state_debug(profile_id, kwargs)

        if not self.runtime._is_verified_admin(kwargs):
            return "Affect administration requires a verified user identity."
        state = self.runtime._state(kwargs)
        if state is None:
            return "No active Hermes session was supplied."
        if action == "status":
            return self._admin_status(state)
        if action == "reset":
            config = self.runtime._config_for_state(state)
            soul_hash = state.soul_sha256
            if config is None:
                config, soul_hash = self.runtime._load_config(kwargs)
                if config.schema_version != 2:
                    return "Migrate SOUL to schema_version 2 before resetting this legacy session."

            def reset(latest: AffectState) -> bool:
                current_config = self.runtime._config_for_state(latest)
                current_hash = latest.soul_sha256
                if current_config is None:
                    current_config = config
                    current_hash = soul_hash
                replacement = AffectState.initial(
                    latest.profile_id,
                    latest.session_id,
                    soul_sha256=current_hash,
                    predisposition=current_config.to_dict(),
                )
                replacement.revision = latest.revision + 1
                latest.__dict__.clear()
                latest.__dict__.update(replacement.__dict__)
                return True

            try:
                self.runtime.store.mutate_exact(state.profile_id, state.session_id, reset)
            except ValueError as error:
                return str(error)
            except LookupError:
                return "Selected affect session is unavailable."
            return "Affective state reset for this session."
        if self.runtime._config_for_state(state) is None:
            return "Legacy affect session requires migration/reset; state was preserved."
        if action == "explain":
            config = self.runtime._config_for_state(state)
            return json.dumps(
                {
                    "effective_configuration": config.to_dict(),
                    "derived_drives": temperament_drives(config),
                    "expression_drive": effective_expression_drive(state, config),
                    "perceived_atmosphere_tension": state.atmosphere_tension,
                    "relationships": {
                        participant: {
                            "credibility": credibility(relation),
                            "social_receptivity": social_receptivity(config, relation),
                        }
                        for participant, relation in state.relationships.items()
                    },
                    "social_edges": state.social_edges,
                    "observed_distress": state.observed_participants,
                    "interpretation": "Local impressions; no knowledge of private peer state.",
                },
                ensure_ascii=True,
                indent=2,
            )
        if action in {"calm", "heat"}:
            message = "calm down" if action == "calm" else "continue the argument"
            intervention_kwargs = dict(kwargs)
            intervention_kwargs.update(
                user_message=message,
                sender_id=str(kwargs.get("sender_id", "user:admin")),
                verified_user=True,
                turn_id=f"admin-{state.revision + 1}",
            )
            result = self.runtime.pre_llm_call(**intervention_kwargs)
            del result
            return f"Affective state instructed to {action}."
        if action == "tune":
            if len(parts) != 3:
                return "Usage: /affect tune expression_gain <0..10>"
            name = parts[1]

            def update(latest: AffectState) -> bool:
                if self.runtime._config_for_state(latest) is None:
                    raise ValueError(
                        "Legacy affect session requires migration/reset; state was preserved."
                    )
                self.tuning.set_override(latest, name, parts[2])
                return True

            try:
                updated, _changed = self.runtime.store.mutate_exact(
                    state.profile_id,
                    state.session_id,
                    update,
                )
            except ValueError as error:
                return str(error)
            except LookupError:
                return "Selected affect session is unavailable."
            return f"Session tuning override set: {name}={updated.tuning_overrides[name]:g}."
        return "Usage: /affect state [profile] | status|explain|reset|calm|heat|tune"

    def _state_debug(self, profile_id: str, kwargs: dict[str, Any]) -> str:
        state = None
        if profile_id == self.runtime._profile_id(kwargs):
            session_id = kwargs.get("session_id")
            if session_id:
                state = self.runtime.store.load(profile_id, str(session_id))
        if state is None:
            state = self.runtime.store.latest_for_profile(profile_id)
        if state is None:
            return f"No affect state found for profile={profile_id}."

        config = self.runtime._config_for_state(state)
        payload = state_snapshot(state, config)
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)

    @staticmethod
    def _admin_status(state: AffectState) -> str:
        return (
            f"session={state.session_id} revision={state.revision} mood={state.mood} "
            f"posture={state.response_posture} relationships={len(state.relationships)}"
        )
