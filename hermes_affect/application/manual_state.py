"""Validated, session-scoped manual changes to persisted source values."""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import datetime, timezone

from ..domain.dynamics import decay_state, refresh_conflicts
from ..domain.state import AffectState
from ..infrastructure.persistence.json_store import StateStore
from .inspection import resolve_state_config
from .response.rendering import derive_mood

FIELD_RANGES: dict[str, dict[str, tuple[float, float]]] = {
    "affect": {
        "valence": (-1.0, 1.0),
        "arousal": (0.0, 1.0),
        "frustration": (0.0, 1.0),
        "offended": (0.0, 1.0),
    },
    "atmosphere": {"atmosphere_tension": (0.0, 1.0)},
    "relationship": {
        "trust": (-1.0, 1.0),
        "affinity": (-1.0, 1.0),
        "respect": (-1.0, 1.0),
        "irritation": (0.0, 1.0),
        "unresolved_tension": (0.0, 1.0),
    },
}
MOOD_SOURCE_FIELDS = {"valence", "frustration", "offended"}
_IDENTIFIER_LIMIT = 200
_MAX_REVISION = 2**53 - 1


class ManualStateControlService:
    """Apply one manual value after elapsed passive decay under the state lock."""

    def __init__(
        self,
        store: StateStore,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store
        self._now = now or (lambda: datetime.now(timezone.utc))

    def apply(
        self,
        *,
        profile_id: object,
        session_id: object,
        scope: object,
        field: object,
        value: object,
        expected_revision: object,
        participant_id: object = None,
    ) -> AffectState:
        profile, session = self._identity(profile_id, "profile_id"), self._identity(
            session_id, "session_id"
        )
        name, bounds = self._field_bounds(scope, field)
        number = self._number(value, bounds)
        revision = self._revision(expected_revision)
        participant = self._participant(scope, participant_id)

        def update(state: AffectState) -> bool:
            if state.model_version != 2:
                raise ValueError("Manual controls require a model v2 session")
            if state.revision >= _MAX_REVISION:
                raise ValueError("Selected session revision limit reached")
            config, _warnings = resolve_state_config(state)
            if config is None:
                raise ValueError("Manual controls require a compatible model v2 session")
            relation = None
            if participant is not None:
                relation = state.relationships.get(participant)
                if relation is None:
                    raise LookupError("Selected participant is unavailable")

            now = self._utc(self._now())
            mood_sources_before = (state.valence, state.frustration, state.offended)
            elapsed_hours = self._elapsed_hours(state.updated_at, now)
            decay_state(state, config, elapsed_hours)

            if scope == "affect":
                setattr(state, name, number)
            elif scope == "atmosphere":
                state.atmosphere_tension = number
            elif relation is not None:
                attribute = "unresolved_tension" if name == "unresolved_tension" else name
                setattr(relation, attribute, number)

            if name in MOOD_SOURCE_FIELDS or mood_sources_before != (
                state.valence,
                state.frustration,
                state.offended,
            ):
                state.mood = derive_mood(state)
            if name == "unresolved_tension":
                refresh_conflicts(state)
            state.updated_at = now.isoformat()
            state.revision += 1
            return True

        state, _changed = self.store.mutate_exact(
            profile,
            session,
            update,
            expected_revision=revision,
        )
        return state

    @staticmethod
    def _identity(value: object, name: str) -> str:
        if not isinstance(value, str) or not 0 < len(value) <= _IDENTIFIER_LIMIT:
            raise ValueError(f"Invalid {name}")
        return value

    @staticmethod
    def _field_bounds(scope: object, field: object) -> tuple[str, tuple[float, float]]:
        if not isinstance(scope, str) or not isinstance(field, str):
            raise ValueError("Unknown manual state field")
        ranges = FIELD_RANGES.get(scope)
        bounds = ranges.get(field) if ranges is not None else None
        if bounds is None:
            raise ValueError("Unknown manual state field")
        return field, bounds

    @staticmethod
    def _number(value: object, bounds: tuple[float, float]) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Manual state value must be a JSON number")
        try:
            number = float(value)
        except OverflowError as error:
            raise ValueError("Manual state value must be finite and in range") from error
        minimum, maximum = bounds
        if not math.isfinite(number) or not minimum <= number <= maximum:
            raise ValueError(f"Manual state value must be between {minimum:g} and {maximum:g}")
        return number

    @staticmethod
    def _revision(value: object) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= _MAX_REVISION
        ):
            raise ValueError("expected_revision must be a non-negative integer")
        return value

    @staticmethod
    def _participant(scope: object, value: object) -> str | None:
        if scope == "relationship":
            return ManualStateControlService._identity(value, "participant_id")
        if value is not None:
            raise ValueError("participant_id is only valid for relationship controls")
        return None

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def _elapsed_hours(cls, updated_at: str, now: datetime) -> float:
        try:
            updated = cls._utc(datetime.fromisoformat(updated_at))
        except (TypeError, ValueError):
            raise ValueError("Selected session update timestamp is invalid") from None
        return max(0.0, (now - updated).total_seconds() / 3600.0)
