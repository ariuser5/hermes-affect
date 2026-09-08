from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hermes_affect.config import neutral_config, parse_soul_affect
from hermes_affect.dynamics import apply_event, decay_state
from hermes_affect.events import AffectiveEvent, EventType
from hermes_affect.influence import ParticipantTraits, evaluate_influence
from hermes_affect.models import AffectState, ParticipantRelation
from hermes_affect.posture import ResponsePosture, derive_posture
from hermes_affect.storage import StateStore


class SoulConfigTests(unittest.TestCase):
    def test_missing_section_uses_neutral_defaults(self) -> None:
        config, warnings = parse_soul_affect("A free-form persona without configuration.")
        self.assertEqual(warnings, [])
        self.assertEqual(config.traits["social_influence"], 0.5)
        self.assertEqual(config.dynamics["expression_gain"], 1.0)

    def test_invalid_section_falls_back(self) -> None:
        config, warnings = parse_soul_affect(
            """session_affect:\n  schema_version: 1\n  traits:\n    pride: 8\n"""
        )
        self.assertTrue(warnings)
        self.assertEqual(config.traits, neutral_config().traits)

    def test_valid_section_preserves_social_traits(self) -> None:
        config, warnings = parse_soul_affect(
            """session_affect:
  schema_version: 1
  traits:
    social_influence: 0.9
    leadership_drive: 0.8
    deference: 0.2
"""
        )
        self.assertEqual(warnings, [])
        self.assertEqual(config.traits["social_influence"], 0.9)
        self.assertEqual(config.traits["leadership_drive"], 0.8)
        self.assertEqual(config.traits["deference"], 0.2)


class DynamicsTests(unittest.TestCase):
    def test_insult_can_create_strong_conflict(self) -> None:
        config = neutral_config()
        config = config.__class__(
            config.schema_version,
            config.traits,
            {**config.dynamics, "escalation_gain": 2.0, "expression_gain": 2.0},
            config.sensitivities,
        )
        state = AffectState.initial("bot-a", "session-1")
        rule = apply_event(state, AffectiveEvent(EventType.INSULT, "bot:other"), config)
        self.assertEqual(rule, "direct_offense")
        self.assertGreater(state.frustration, 0.3)
        self.assertIn("bot:other", state.open_conflicts)
        self.assertIn(
            derive_posture(state, config),
            {ResponsePosture.GUARDED, ResponsePosture.COUNTERATTACK},
        )

    def test_decay_reduces_state_without_erasing_relationship(self) -> None:
        config = neutral_config()
        state = AffectState.initial("bot-a", "session-1")
        state.frustration = 0.8
        state.relationships["user:1"] = ParticipantRelation(unresolved_tension=0.7)
        decay_state(state, config, 1.0)
        self.assertLess(state.frustration, 0.8)
        self.assertGreater(state.relationships["user:1"].unresolved_tension, 0.0)


class InfluenceTests(unittest.TestCase):
    def test_respect_and_deference_can_reduce_conflict_risk(self) -> None:
        speaker = ParticipantTraits(social_influence=0.9, leadership_drive=0.9)
        listener = ParticipantTraits(deference=0.8, pride=0.4, patience=0.8)
        decision = evaluate_influence(
            speaker,
            listener,
            ParticipantRelation(trust=0.7, respect=0.9, unresolved_tension=0.1),
        )
        self.assertGreater(decision.calming, 0.2)
        self.assertLess(decision.conflict_risk, 0.5)
        self.assertIn("leadership_signal", decision.factors)


class StorageTests(unittest.TestCase):
    def test_state_round_trip_is_profile_and_session_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = StateStore(Path(temporary))
            state = AffectState.initial("bot/a", "session:1")
            store.save(state)
            loaded = store.load("bot/a", "session:1")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.profile_id, "bot/a")
            self.assertIsNone(store.load("bot/a", "session:2"))
            self.assertTrue(store.state_path("bot/a", "session:1").exists())


if __name__ == "__main__":
    unittest.main()
