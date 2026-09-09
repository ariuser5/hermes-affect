"""Small, file-based runtime store with per-state locking and atomic writes."""

from __future__ import annotations

import json
import math
import os
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import AffectState

DEFAULT_ABANDONED_STATE_DAYS = 90


@dataclass(frozen=True)
class GarbageCollectionReport:
    examined: int
    removed: tuple[Path, ...]
    skipped: int


def _path_component(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in value)
    return safe[:160] or "unknown"


class StateFileLock:
    def __init__(self, path: Path, timeout: float = 5.0) -> None:
        self.path = path
        self.timeout = timeout
        self._handle: int | None = None

    def __enter__(self) -> StateFileLock:
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
        filename = f"{_path_component(session_id)}.json"
        return self.root / _path_component(profile_id) / "sessions" / filename

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

    @staticmethod
    def _load_path(path: Path) -> AffectState:
        with path.open("r", encoding="utf-8") as handle:
            return AffectState.from_dict(json.load(handle))

    @staticmethod
    def _updated_at(state: AffectState) -> datetime:
        updated_at = datetime.fromisoformat(state.updated_at)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        return updated_at.astimezone(timezone.utc)

    def garbage_collect(
        self,
        *,
        max_age_days: float = DEFAULT_ABANDONED_STATE_DAYS,
        now: datetime | None = None,
        exclude_paths: set[Path] | None = None,
    ) -> GarbageCollectionReport:
        """Remove valid, unlocked state files older than ``max_age_days``.

        Files with invalid JSON/state data and files whose lock cannot be
        acquired are skipped. The caller can use the report for administrative
        logging without exposing state contents.
        """

        if (
            isinstance(max_age_days, bool)
            or not isinstance(max_age_days, (int, float))
            or not math.isfinite(float(max_age_days))
            or max_age_days <= 0
        ):
            raise ValueError("max_age_days must be a positive finite number")
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        cutoff = current.astimezone(timezone.utc) - timedelta(days=float(max_age_days))
        excluded = exclude_paths or set()

        examined = 0
        skipped = 0
        removed: list[Path] = []
        for path in sorted(self.root.rglob("*.json")):
            if not path.is_file():
                continue
            examined += 1
            if path in excluded:
                skipped += 1
                continue
            try:
                state = self._load_path(path)
                if self._updated_at(state) >= cutoff:
                    skipped += 1
                    continue
            except (FileNotFoundError, KeyError, OSError, TypeError, ValueError):
                skipped += 1
                continue

            lock_path = path.with_suffix(path.suffix + ".lock")
            try:
                with StateFileLock(lock_path, timeout=0):
                    try:
                        state = self._load_path(path)
                        if self._updated_at(state) >= cutoff:
                            skipped += 1
                            continue
                        path.unlink()
                    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError):
                        skipped += 1
                        continue
                    removed.append(path)
            except (FileNotFoundError, OSError, TimeoutError):
                skipped += 1

        return GarbageCollectionReport(examined, tuple(removed), skipped)

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
