"""Thin Hermes dashboard adapter for the read-only affect state endpoint."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

_DASHBOARD_ROOT = Path(__file__).resolve().parent
_PLUGIN_ROOT = _DASHBOARD_ROOT.parent
for _path in (_PLUGIN_ROOT, _DASHBOARD_ROOT):
    _value = str(_path)
    if _value not in sys.path:
        sys.path.insert(0, _value)

from hermes_affect_dashboard.application.feature_gate import (  # noqa: E402
    dashboard_feature_enabled,
)
from hermes_affect_dashboard.application.inspection import (  # noqa: E402
    DashboardInspectionService,
)
from hermes_affect_dashboard.infrastructure.state_reader import FileStateReader  # noqa: E402

router = APIRouter()
_FEATURE_ENABLED = dashboard_feature_enabled()
_INSPECTION = DashboardInspectionService(FileStateReader.from_environment())


@router.get("/state")
async def get_current_state() -> dict:
    if not _FEATURE_ENABLED:
        raise HTTPException(status_code=404, detail="Affect dashboard is disabled")
    return _INSPECTION.current_state()

