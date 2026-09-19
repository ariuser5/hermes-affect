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


class DashboardInspectionService:
    def __init__(self, reader: LatestStateReader) -> None:
        self.reader = reader

    def current_state(self) -> DashboardStateResponse:
        state = self.reader.latest_state()
        if state is None:
            return {"available": False, "state": None}

        config, warnings = resolve_state_config(state)
        for warning in warnings:
            logger.warning("Saved affect configuration: %s", warning)
        return {"available": True, "state": state_snapshot(state, config)}

