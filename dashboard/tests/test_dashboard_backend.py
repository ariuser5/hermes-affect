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
from dashboard.hermes_affect_dashboard.application.session_catalog import session_summary
from dashboard.hermes_affect_dashboard.domain.session_models import SessionCatalogResponse
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

    def test_exact_state_rejects_sanitized_path_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = StateStore(temporary)
            stored = AffectState.initial("bot/a", "session/a")
            path = store.state_path("bot:a", "session:a")
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(stored.to_dict()), encoding="utf-8")

            self.assertIsNone(store.load_exact("bot:a", "session:a"))
            selected = store.load_exact("bot/a", "session/a")

            self.assertIsNotNone(selected)
            assert selected is not None
            self.assertEqual((selected.profile_id, selected.session_id), ("bot/a", "session/a"))

    def test_recent_returns_valid_states_in_deterministic_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = StateStore(temporary)
            tied_later = AffectState.initial("bot:z", "session:z")
            tied_later.updated_at = "2026-09-19T09:00:00+00:00"
            tied_earlier = AffectState.initial("bot:a", "session:a")
            tied_earlier.updated_at = "2026-09-19T09:00:00+00:00"
            older = AffectState.initial("bot:old", "session:old")
            older.updated_at = "2026-09-19T08:00:00+00:00"
            for state in (tied_later, tied_earlier, older):
                store.save(state)

            first_page = store.recent(limit=2)
            second_page = store.recent(limit=2, offset=2)

            self.assertEqual(
                [(state.profile_id, state.session_id) for state in first_page],
                [("bot:a", "session:a"), ("bot:z", "session:z")],
            )
            self.assertEqual(
                [(state.profile_id, state.session_id) for state in second_page],
                [("bot:old", "session:old")],
            )

    def test_recent_rejects_invalid_pagination(self) -> None:
        store = StateStore("unused")

        for limit, offset in ((0, 0), (-1, 0), (True, 0), (1, -1), (1, True)):
            with self.subTest(limit=limit, offset=offset), self.assertRaises(ValueError):
                store.recent(limit, offset)


class SessionSummaryTests(unittest.TestCase):
    def test_projection_is_bounded_and_contains_only_navigation_metadata(self) -> None:
        state = AffectState.initial("p" * 300, "s" * 300)
        state.updated_at = "t" * 120
        state.revision = -4
        state.model_version = -2
        state.mood = "m" * 120
        state.response_posture = "r" * 120
        state.audit_records = [{"private": "secret"}]
        state.soul_sha256 = "hash"

        summary = session_summary(state)
        typed_summary: SessionCatalogResponse = {
            "items": [summary],
            "limit": 50,
            "offset": 0,
            "has_more": False,
        }

        self.assertEqual(set(summary), {
            "profile_id",
            "session_id",
            "updated_at",
            "revision",
            "mood",
            "response_posture",
            "model_version",
        })
        self.assertEqual(len(summary["profile_id"]), 200)
        self.assertEqual(len(summary["session_id"]), 200)
        self.assertEqual(len(summary["updated_at"]), 80)
        self.assertEqual(len(summary["mood"]), 80)
        self.assertEqual(summary["revision"], 0)
        self.assertEqual(summary["model_version"], 0)
        self.assertNotIn("secret", json.dumps(typed_summary))

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
