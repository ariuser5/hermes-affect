"""Dashboard use case for session-scoped tuning overrides."""

from __future__ import annotations

from typing import Protocol

from hermes_affect.application.inspection import resolve_state_config
from hermes_affect.application.tuning import SessionTuningService
from hermes_affect.domain.state import AffectState


class DashboardTuningReader(Protocol):
    def exact_state(self, profile_id: str, session_id: str) -> AffectState | None: ...

    def save_state(self, state: AffectState) -> None: ...


class DashboardTuningService:
    """Apply supported dashboard controls to one retained exact session."""

    def __init__(self, reader: DashboardTuningReader) -> None:
        self.reader = reader
        self.tuning = SessionTuningService()

    def set_expression_gain(
        self, profile_id: str, session_id: str, value: object
    ) -> AffectState:
        state = self._load_state(profile_id, session_id)
        self._require_current_model(state)
        self.tuning.set_override(state, "expression_gain", value)
        self.reader.save_state(state)
        return state

    def restore_expression_gain(self, profile_id: str, session_id: str) -> AffectState:
        state = self._load_state(profile_id, session_id)
        self._require_current_model(state)
        if self.tuning.restore_configured(state, "expression_gain"):
            self.reader.save_state(state)
        return state

    def _load_state(self, profile_id: str, session_id: str) -> AffectState:
        state = self.reader.exact_state(profile_id, session_id)
        if state is None:
            raise LookupError("Selected affect state is unavailable")
        return state

    @staticmethod
    def _require_current_model(state: AffectState) -> None:
        config, _warnings = resolve_state_config(state)
        if config is None:
            raise ValueError("Legacy affect session requires migration/reset; state was preserved.")
