"""Dashboard use case for session-scoped tuning overrides."""

from __future__ import annotations

from hermes_affect.application.inspection import resolve_state_config
from hermes_affect.application.tuning import SessionTuningService
from hermes_affect.domain.state import AffectState
from hermes_affect.infrastructure.persistence.json_store import StateStore


class DashboardTuningService:
    """Apply supported dashboard controls to one retained exact session."""

    def __init__(self, store: StateStore) -> None:
        self.store = store
        self.tuning = SessionTuningService()

    def set_expression_gain(
        self,
        profile_id: str,
        session_id: str,
        value: object,
        expected_revision: int,
    ) -> AffectState:
        def update(state: AffectState) -> bool:
            self._require_current_model(state)
            self.tuning.set_override(state, "expression_gain", value)
            return True

        state, _changed = self.store.mutate_exact(
            profile_id, session_id, update, expected_revision=expected_revision
        )
        return state

    def restore_expression_gain(
        self, profile_id: str, session_id: str, expected_revision: int
    ) -> AffectState:
        def update(state: AffectState) -> bool:
            self._require_current_model(state)
            return self.tuning.restore_configured(state, "expression_gain")

        state, _changed = self.store.mutate_exact(
            profile_id, session_id, update, expected_revision=expected_revision
        )
        return state

    @staticmethod
    def _require_current_model(state: AffectState) -> None:
        config, _warnings = resolve_state_config(state)
        if config is None:
            raise ValueError("Legacy affect session requires migration/reset; state was preserved.")
