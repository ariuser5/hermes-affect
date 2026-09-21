"""Pure projections for retained affect-session navigation."""

from __future__ import annotations

from typing import Protocol

from hermes_affect.domain.state import AffectState

from ..domain.session_models import SessionCatalogResponse, SessionSummary

_IDENTIFIER_LIMIT = 200
_TIMESTAMP_LIMIT = 80
_LABEL_LIMIT = 80
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


def _bounded_text(value: object, limit: int) -> str:
    return str(value)[:limit]


def session_summary(state: AffectState) -> SessionSummary:
    """Project only the metadata needed to choose a retained session."""

    return {
        "profile_id": _bounded_text(state.profile_id, _IDENTIFIER_LIMIT),
        "session_id": _bounded_text(state.session_id, _IDENTIFIER_LIMIT),
        "updated_at": _bounded_text(state.updated_at, _TIMESTAMP_LIMIT),
        "revision": max(0, int(state.revision)),
        "mood": _bounded_text(state.mood, _LABEL_LIMIT),
        "response_posture": _bounded_text(state.response_posture, _LABEL_LIMIT),
        "model_version": max(0, int(state.model_version)),
    }


class SessionCatalogReader(Protocol):
    def recent_states(self, limit: int, offset: int = 0) -> list[AffectState]:
        ...

    def exact_state(self, profile_id: str, session_id: str) -> AffectState | None:
        ...


class DashboardSessionCatalogService:
    def __init__(self, reader: SessionCatalogReader) -> None:
        self.reader = reader

    def page(
        self, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0
    ) -> SessionCatalogResponse:
        self._validate_pagination(limit, offset)
        states = self.reader.recent_states(limit + 1, offset)
        return {
            "items": [session_summary(state) for state in states[:limit]],
            "limit": limit,
            "offset": offset,
            "has_more": len(states) > limit,
        }

    def exact_state(self, profile_id: str, session_id: str) -> AffectState | None:
        return self.reader.exact_state(profile_id, session_id)

    @staticmethod
    def _validate_pagination(limit: int, offset: int) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValueError("limit must be an integer")
        if not 1 <= limit <= MAX_PAGE_SIZE:
            raise ValueError("limit is outside the supported range")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be a non-negative integer")
