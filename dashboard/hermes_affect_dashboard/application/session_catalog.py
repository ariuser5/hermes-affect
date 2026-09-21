"""Pure projections for retained affect-session navigation."""

from __future__ import annotations

from hermes_affect.domain.state import AffectState

from ..domain.session_models import SessionSummary

_IDENTIFIER_LIMIT = 200
_TIMESTAMP_LIMIT = 80
_LABEL_LIMIT = 80


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
