"""Dashboard use case for reading the latest safe affect snapshot."""

from __future__ import annotations

import logging
from typing import Protocol

from hermes_affect.application.inspection import resolve_state_config, state_snapshot
from hermes_affect.domain.state import AffectState

from ..domain.view_models import DashboardStateResponse

logger = logging.getLogger("hermes-affect.dashboard")


class LatestStateReader(Protocol):
    def latest_state(self) -> AffectState | None: ...

    def exact_state(self, profile_id: str, session_id: str) -> AffectState | None: ...


class DashboardInspectionService:
    def __init__(self, reader: LatestStateReader) -> None:
        self.reader = reader

    def current_state(
        self,
        profile_id: str | None = None,
        session_id: str | None = None,
        *,
        controls_enabled: bool = False,
    ) -> DashboardStateResponse:
        if (profile_id is None) != (session_id is None):
            raise ValueError("profile_id and session_id must be provided together")
        state = (
            self.reader.latest_state()
            if profile_id is None
            else self.reader.exact_state(profile_id, session_id or "")
        )
        if state is None:
            return {"available": False, "state": None, "controls_enabled": controls_enabled}

        config, warnings = resolve_state_config(state)
        for warning in warnings:
            logger.warning("Saved affect configuration: %s", warning)
        return {
            "available": True,
            "state": state_snapshot(state, config),
            "controls_enabled": controls_enabled,
        }
