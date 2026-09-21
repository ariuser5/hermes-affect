"""Thin Hermes dashboard adapter for the read-only affect state endpoint."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

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
from hermes_affect_dashboard.application.session_catalog import (  # noqa: E402
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    DashboardSessionCatalogService,
)
from hermes_affect_dashboard.infrastructure.state_reader import FileStateReader  # noqa: E402

router = APIRouter()
_FEATURE_ENABLED = dashboard_feature_enabled()
_READER = FileStateReader.from_environment()
_INSPECTION = DashboardInspectionService(_READER)
_SESSION_CATALOG = DashboardSessionCatalogService(_READER)


def _require_feature() -> None:
    if not _FEATURE_ENABLED:
        raise HTTPException(status_code=404, detail="Affect dashboard is disabled")


def _validate_identifier(name: str, value: str | None) -> None:
    if value is not None and not 0 < len(value) <= 200:
        raise HTTPException(status_code=422, detail=f"Invalid {name}")


def _validate_selection(profile_id: str | None, session_id: str | None) -> None:
    _validate_identifier("profile_id", profile_id)
    _validate_identifier("session_id", session_id)
    if (profile_id is None) != (session_id is None):
        raise HTTPException(
            status_code=422,
            detail="profile_id and session_id must be provided together",
        )


@router.get("/state")
async def get_current_state(
    profile_id: str | None = Query(default=None, min_length=1, max_length=200),
    session_id: str | None = Query(default=None, min_length=1, max_length=200),
) -> dict:
    _require_feature()
    _validate_selection(profile_id, session_id)
    if profile_id is None:
        return _INSPECTION.current_state()

    response = _INSPECTION.current_state(profile_id, session_id)
    if not response["available"]:
        raise HTTPException(status_code=404, detail="Selected affect state is unavailable")
    return response


@router.get("/sessions")
async def get_sessions(
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
) -> dict:
    _require_feature()
    try:
        return _SESSION_CATALOG.page(limit, offset)
    except ValueError as error:
        raise HTTPException(
            status_code=422, detail="Invalid session catalog pagination"
        ) from error
