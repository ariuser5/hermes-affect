from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from dashboard.hermes_affect_dashboard.application.feature_gate import (
    dashboard_feature_enabled,
    parse_feature_flag,
)
from dashboard.hermes_affect_dashboard.application.inspection import (
    DashboardInspectionService,
)
from dashboard.hermes_affect_dashboard.infrastructure.state_reader import (
    FileStateReader,
    resolve_state_root,
)
from hermes_affect.application.inspection import resolve_state_config, state_snapshot
from hermes_affect.domain.state import AffectState, ParticipantRelation
from hermes_affect.infrastructure.persistence.json_store import StateStore

REPOSITORY_ROOT = Path(__file__).parents[2]


class FeatureGateTests(unittest.TestCase):
    def test_missing_and_documented_false_values_are_disabled(self) -> None:
        for value in (None, "", "0", "false", "NO", "off"):
            with self.subTest(value=value):
                self.assertEqual(parse_feature_flag(value), (False, None))

    def test_documented_true_values_are_enabled(self) -> None:
        for value in ("1", "true", "YES", "on"):
            with self.subTest(value=value):
                self.assertEqual(parse_feature_flag(value), (True, None))

    def test_invalid_value_fails_closed_with_warning(self) -> None:
        enabled, warning = parse_feature_flag("sometimes")

        self.assertFalse(enabled)
        self.assertIn("remains disabled", warning or "")
        with self.assertLogs("hermes-affect.dashboard", level="WARNING"):
            self.assertFalse(dashboard_feature_enabled({"HERMES_AFFECT_DASHBOARD": "invalid"}))


class InspectionTests(unittest.TestCase):
    def test_snapshot_is_bounded_and_excludes_private_state(self) -> None:
        state = AffectState.initial("bot:one", "session:one")
        state.relationships["user:one"] = ParticipantRelation(trust=0.3, irritation=0.7)
        state.open_conflicts["user:one"] = {
            "heat": 2.0,
            "status": "open",
            "private_note": "do not expose",
        }
        state.open_conflicts["malformed"] = "unexpected"  # type: ignore[assignment]
        state.active_sensitivities = ["competence"]
        state.audit_records = [{"private": "audit secret"}]
        state.observed_participants = {"user:two": {"frustration": 0.9}}
        state.social_edges = [
            {"speaker_id": "a", "target_id": "b", "tension": 1.0, "last_event": "insult"}
        ]
        state.soul_sha256 = "secret hash"
        state.last_turn_id = "secret turn"
        state.current_participant = "secret participant"
        state.tuning_overrides = {"expression_gain": 2.0, "unknown": 9.0}

        config, warnings = resolve_state_config(state)
        self.assertEqual(warnings, ())
        payload = state_snapshot(state, config)
        serialized = json.dumps(payload)

        self.assertEqual(payload["open_conflicts"]["user:one"], {"heat": 1.0, "status": "open"})
        self.assertNotIn("malformed", payload["open_conflicts"])
        self.assertEqual(payload["tuning_overrides"], {"expression_gain": 2.0})
        for private_value in (
            "do not expose",
            "audit secret",
            "secret hash",
            "secret turn",
            "secret participant",
            "last_event",
            "predisposition",
        ):
            self.assertNotIn(private_value, serialized)

    def test_legacy_state_is_marked_for_migration(self) -> None:
        state = AffectState.initial("bot:one", "legacy")
        state.model_version = 1

        config, warnings = resolve_state_config(state)
        payload = state_snapshot(state, config)

        self.assertIsNone(config)
        self.assertTrue(any("Legacy affect session" in warning for warning in warnings))
        self.assertTrue(payload["migration_required"])
        self.assertIsNone(payload["expression_drive"])


class StateReaderTests(unittest.TestCase):
    def test_state_root_uses_explicit_setting_then_hermes_home(self) -> None:
        explicit = resolve_state_root(
            {"HERMES_AFFECT_STATE_DIR": "C:/runtime/affect", "HERMES_HOME": "ignored"}
        )
        fallback = resolve_state_root({"HERMES_HOME": "C:/runtime/hermes"})

        self.assertEqual(explicit, Path("C:/runtime/affect"))
        self.assertEqual(fallback, Path("C:/runtime/hermes") / "affect-state")

    def test_reader_selects_latest_valid_state_across_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = StateStore(temporary)
            older = AffectState.initial("bot:one", "older")
            older.updated_at = "2026-09-19T08:00:00+00:00"
            newer = AffectState.initial("bot:two", "newer")
            newer.updated_at = "2026-09-19T09:00:00+00:00"
            store.save(older)
            store.save(newer)
            malformed = Path(temporary) / "bot_three" / "sessions" / "broken.json"
            malformed.parent.mkdir(parents=True)
            malformed.write_text("not json", encoding="utf-8")
            unsupported = Path(temporary) / "bot_four" / "sessions" / "unsupported.json"
            unsupported.parent.mkdir(parents=True)
            unsupported.write_text(
                json.dumps(
                    {
                        "schema_version": 99,
                        "profile_id": "bot:four",
                        "session_id": "unsupported",
                    }
                ),
                encoding="utf-8",
            )
            partial = Path(temporary) / "bot_two" / "sessions" / ".newer.json.pending"
            partial.write_text("partially written", encoding="utf-8")

            selected = FileStateReader(temporary).latest_state()

            self.assertIsNotNone(selected)
            assert selected is not None
            self.assertEqual((selected.profile_id, selected.session_id), ("bot:two", "newer"))

    def test_service_returns_explicit_empty_state(self) -> None:
        class EmptyReader:
            def latest_state(self) -> None:
                return None

        response = DashboardInspectionService(EmptyReader()).current_state()

        self.assertEqual(response, {"available": False, "state": None})

    def test_service_returns_shared_projection(self) -> None:
        state = AffectState.initial("bot:one", "session:one")

        class Reader:
            def latest_state(self) -> AffectState:
                return state

        response = DashboardInspectionService(Reader()).current_state()

        self.assertTrue(response["available"])
        assert response["state"] is not None
        self.assertEqual(response["state"]["profile_id"], "bot:one")


class PluginApiAdapterTests(unittest.TestCase):
    def _load_adapter(self, *, enabled: str) -> types.ModuleType:
        class FakeRouter:
            def __init__(self) -> None:
                self.routes: list[tuple[str, object]] = []

            def get(self, path: str):
                def decorator(callback):
                    self.routes.append((path, callback))
                    return callback

                return decorator

        class FakeHttpException(Exception):
            def __init__(self, *, status_code: int, detail: str) -> None:
                super().__init__(detail)
                self.status_code = status_code
                self.detail = detail

        fake_fastapi = types.ModuleType("fastapi")
        fake_fastapi.APIRouter = FakeRouter
        fake_fastapi.HTTPException = FakeHttpException
        module_name = "hermes_affect_dashboard_adapter_test"
        spec = importlib.util.spec_from_file_location(
            module_name, REPOSITORY_ROOT / "dashboard" / "plugin_api.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        with (
            patch.dict(sys.modules, {"fastapi": fake_fastapi, module_name: module}),
            patch.dict(os.environ, {"HERMES_AFFECT_DASHBOARD": enabled}, clear=False),
        ):
            spec.loader.exec_module(module)
        return module

    def test_adapter_exports_only_read_only_state_route(self) -> None:
        module = self._load_adapter(enabled="0")

        self.assertEqual([path for path, _ in module.router.routes], ["/state"])
        with self.assertRaises(module.HTTPException) as raised:
            asyncio.run(module.get_current_state())
        self.assertEqual(raised.exception.status_code, 404)

    def test_enabled_adapter_returns_service_response(self) -> None:
        module = self._load_adapter(enabled="1")

        class Inspection:
            def current_state(self) -> dict:
                return {"available": False, "state": None}

        module._INSPECTION = Inspection()
        response = asyncio.run(module.get_current_state())

        self.assertEqual(response, {"available": False, "state": None})


if __name__ == "__main__":
    unittest.main()
