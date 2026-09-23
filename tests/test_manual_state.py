from __future__ import annotations

import math
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from hermes_affect.application.manual_state import FIELD_RANGES, ManualStateControlService
from hermes_affect.domain.dynamics import decay_state
from hermes_affect.domain.state import AffectState, ParticipantRelation
from hermes_affect.infrastructure.persistence.json_store import (
    ExactStateUnavailable,
    StateRevisionConflict,
    StateStore,
)


class ManualStateControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = StateStore(self.temporary.name)
        self.now = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)
        self.service = ManualStateControlService(self.store, now=lambda: self.now)
        self.state = AffectState.initial("profile:one", "session:one")
        self.state.revision = 7
        self.state.updated_at = (self.now - timedelta(hours=8)).isoformat()
        self.state.valence = 0.8
        self.state.arousal = 0.6
        self.state.frustration = 0.5
        self.state.offended = 0.4
        self.state.atmosphere_tension = 0.7
        self.state.relationships["user:one"] = ParticipantRelation(
            trust=0.2,
            affinity=0.3,
            irritation=0.6,
            respect=0.4,
            unresolved_tension=0.8,
        )
        self.store.save(self.state)

    def apply_value(
        self,
        scope: str,
        field: str,
        value: float,
        *,
        expected_revision: int = 7,
        **extra: object,
    ) -> AffectState:
        return self.service.apply(
            profile_id="profile:one",
            session_id="session:one",
            scope=scope,
            field=field,
            value=value,
            expected_revision=expected_revision,
            **extra,
        )

    def test_applies_one_selected_source_after_one_decay_and_updates_clock(self) -> None:
        expected = AffectState.from_dict(self.state.to_dict())
        from hermes_affect.application.inspection import resolve_state_config

        config, _ = resolve_state_config(expected)
        assert config is not None
        decay_state(expected, config, 8)

        updated = self.apply_value("affect", "valence", -0.25)

        self.assertEqual(updated.valence, -0.25)
        self.assertAlmostEqual(updated.arousal, expected.arousal)
        self.assertAlmostEqual(updated.frustration, expected.frustration)
        self.assertAlmostEqual(updated.offended, expected.offended)
        self.assertAlmostEqual(updated.atmosphere_tension, expected.atmosphere_tension)
        self.assertAlmostEqual(
            updated.relationships["user:one"].unresolved_tension,
            expected.relationships["user:one"].unresolved_tension,
        )
        self.assertEqual(updated.updated_at, self.now.isoformat())
        self.assertEqual(updated.revision, 8)

    def test_mood_and_conflict_projections_follow_only_their_source_edits(self) -> None:
        mood_state = self.apply_value("affect", "frustration", 0.9)
        self.assertNotEqual(mood_state.mood, self.state.mood)

        conflict_state = self.service.apply(
            profile_id="profile:one",
            session_id="session:one",
            scope="relationship",
            field="unresolved_tension",
            participant_id="user:one",
            value=0.0,
            expected_revision=8,
        )
        self.assertNotIn("user:one", conflict_state.open_conflicts)
        self.assertEqual(conflict_state.response_posture, self.state.response_posture)

    def test_existing_participant_is_required_and_other_sessions_are_untouched(self) -> None:
        other = AffectState.initial("profile:one", "session:two")
        self.store.save(other)

        with self.assertRaises(LookupError):
            self.service.apply(
                profile_id="profile:one",
                session_id="session:one",
                scope="relationship",
                field="trust",
                participant_id="user:missing",
                value=0.5,
                expected_revision=7,
            )

        updated = self.service.apply(
            profile_id="profile:one",
            session_id="session:one",
            scope="relationship",
            field="trust",
            participant_id="user:one",
            value=0.5,
            expected_revision=7,
        )
        self.assertEqual(updated.relationships["user:one"].trust, 0.5)
        self.assertEqual(self.store.load_exact("profile:one", "session:two").revision, 0)

    def test_invalid_scope_field_type_and_range_are_rejected(self) -> None:
        for scope, field, value in (
            ("affect", "mood", 0.5),
            ("affect", "valence", True),
            ("affect", "valence", "0.5"),
            ("affect", "valence", math.nan),
            ("affect", "valence", 1.01),
            ("affect", "arousal", -0.01),
            ("atmosphere", "atmosphere_tension", 1.01),
            ("relationship", "trust", -1.01),
            ("relationship", "irritation", 1.01),
        ):
            with self.subTest(scope=scope, field=field, value=value), self.assertRaises(
                ValueError
            ):
                self.service.apply(
                    profile_id="profile:one",
                    session_id="session:one",
                    scope=scope,
                    field=field,
                    participant_id="user:one" if scope == "relationship" else None,
                    value=value,
                    expected_revision=7,
                )

    def test_every_supported_field_accepts_both_documented_endpoints(self) -> None:
        current_revision = 7
        for scope, fields in FIELD_RANGES.items():
            for field, (minimum, maximum) in fields.items():
                for value in (minimum, maximum):
                    updated = self.service.apply(
                        profile_id="profile:one",
                        session_id="session:one",
                        scope=scope,
                        field=field,
                        participant_id="user:one" if scope == "relationship" else None,
                        value=value,
                        expected_revision=current_revision,
                    )
                    current_revision += 1
                    if scope == "affect":
                        self.assertEqual(getattr(updated, field), value)
                    elif scope == "atmosphere":
                        self.assertEqual(updated.atmosphere_tension, value)
                    else:
                        self.assertEqual(
                            getattr(updated.relationships["user:one"], field), value
                        )

    def test_new_session_starts_fresh_and_compression_continuation_keeps_edit(self) -> None:
        edited = self.apply_value("affect", "valence", -0.7)
        compressed = AffectState.continued_from(edited, "session:compressed")
        fresh = AffectState.initial("profile:one", "session:new")

        self.assertEqual(compressed.valence, -0.7)
        self.assertEqual(compressed.parent_session_id, "session:one")
        self.assertNotEqual(fresh.valence, -0.7)
        self.assertEqual(fresh.revision, 0)

    def test_stale_revision_and_colliding_storage_identity_fail_closed(self) -> None:
        with self.assertRaises(StateRevisionConflict):
            self.apply_value("affect", "valence", 0.5, expected_revision=6)

        colliding = AffectState.initial("profile:one", "session?one")
        self.store.save(colliding)
        with self.assertRaises(ExactStateUnavailable):
            self.apply_value("affect", "valence", 0.5)

    def test_missing_and_legacy_states_are_not_mutated(self) -> None:
        with self.assertRaises(ExactStateUnavailable):
            self.service.apply(
                profile_id="profile:missing",
                session_id="session:missing",
                scope="affect",
                field="valence",
                value=0.5,
                expected_revision=0,
            )
        legacy = AffectState.initial("profile:legacy", "session:legacy")
        legacy.model_version = 1
        legacy.predisposition["schema_version"] = 1
        self.store.save(legacy)
        with self.assertRaises(ValueError):
            self.service.apply(
                profile_id="profile:legacy",
                session_id="session:legacy",
                scope="affect",
                field="valence",
                value=0.5,
                expected_revision=0,
            )
        self.assertEqual(self.store.load_exact("profile:legacy", "session:legacy").revision, 0)

    def test_malformed_file_and_invalid_revision_fail_closed(self) -> None:
        path = self.store.state_path("profile:broken", "session:broken")
        path.parent.mkdir(parents=True)
        path.write_text("{not-json", encoding="utf-8")
        with self.assertRaises(ExactStateUnavailable):
            self.service.apply(
                profile_id="profile:broken",
                session_id="session:broken",
                scope="affect",
                field="valence",
                value=0.5,
                expected_revision=0,
            )
        for revision in (True, -1, 2**53):
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                self.apply_value("affect", "valence", 0.5, expected_revision=revision)
        self.state.updated_at = "invalid timestamp"
        self.store.save(self.state)
        with self.assertRaisesRegex(ValueError, "timestamp is invalid"):
            self.apply_value("affect", "valence", 0.5)
        self.assertEqual(self.store.load_exact("profile:one", "session:one").revision, 7)


if __name__ == "__main__":
    unittest.main()
