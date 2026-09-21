"""Read-only adapter for the existing affect JSON store."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from hermes_affect.domain.state import AffectState
from hermes_affect.infrastructure.persistence.json_store import StateStore


def resolve_state_root(
    environ: Mapping[str, str] | None = None,
    *,
    user_home: Path | None = None,
) -> Path:
    values = os.environ if environ is None else environ
    configured = values.get("HERMES_AFFECT_STATE_DIR")
    if configured:
        return Path(configured).expanduser()
    home = Path(values.get("HERMES_HOME", user_home or Path.home() / ".hermes"))
    return home.expanduser() / "affect-state"


class FileStateReader:
    """Find the newest valid state in this container without writing it."""

    def __init__(self, root: str | Path) -> None:
        self.store = StateStore(root)

    @classmethod
    def from_environment(cls) -> FileStateReader:
        return cls(resolve_state_root())

    def latest_state(self) -> AffectState | None:
        return self.store.latest()

    def exact_state(self, profile_id: str, session_id: str) -> AffectState | None:
        return self.store.load_exact(profile_id, session_id)

    def recent_states(self, limit: int, offset: int = 0) -> list[AffectState]:
        return self.store.recent(limit, offset)
