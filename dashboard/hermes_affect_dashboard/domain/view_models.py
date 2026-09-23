"""Wire-level types for the read-only affect dashboard API."""

from __future__ import annotations

from typing import Any, TypedDict


class DashboardStateResponse(TypedDict):
    available: bool
    state: dict[str, Any] | None
    controls_enabled: bool
