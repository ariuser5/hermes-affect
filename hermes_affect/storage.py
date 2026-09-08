"""Small, file-based runtime store with per-state locking and atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .models import AffectState


def _path_component(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in value)
    return safe[:160] or "unknown"


class StateFileLock:
    def __init__(self, path: Path, timeout: float = 5.0) -> None:
        self.path = path
        self.timeout = timeout
        self._handle: int | None = None

    def __enter__(self) -> "StateFileLock":
        deadline = time.monotonic() + self.timeout
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                self._handle = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self._handle, str(os.getpid()).encode("ascii"))
                return self
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Timed out waiting for affect state lock: {self.path}")
                time.sleep(0.05)

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        if self._handle is not None:
            os.close(self._handle)
            self._handle = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


class StateStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()

    def state_path(self, profile_id: str, session_id: str) -> Path:
        return self.root / _path_component(profile_id) / "sessions" / f"{_path_component(session_id)}.json"

    @contextmanager
    def locked(self, profile_id: str, session_id: str) -> Iterator[Path]:
        path = self.state_path(profile_id, session_id)
        with StateFileLock(path.with_suffix(path.suffix + ".lock")):
            yield path

    def load(self, profile_id: str, session_id: str) -> AffectState | None:
        path = self.state_path(profile_id, session_id)
        try:
            with path.open("r", encoding="utf-8") as handle:
                return AffectState.from_dict(json.load(handle))
        except FileNotFoundError:
            return None

    def save(self, state: AffectState) -> Path:
        path = self.state_path(state.profile_id, state.session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with StateFileLock(path.with_suffix(path.suffix + ".lock")):
            fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(state.to_dict(), handle, indent=2, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_name, path)
                try:
                    os.chmod(path, 0o600)
                except OSError:
                    pass
                return path
            finally:
                try:
                    os.unlink(temporary_name)
                except FileNotFoundError:
                    pass
