"""Hermes-independent response shapes for retained session navigation."""

from __future__ import annotations

from typing import TypedDict


class SessionSummary(TypedDict):
    profile_id: str
    session_id: str
    updated_at: str
    revision: int
    mood: str
    response_posture: str
    model_version: int


class SessionCatalogResponse(TypedDict):
    items: list[SessionSummary]
    limit: int
    offset: int
    has_more: bool
