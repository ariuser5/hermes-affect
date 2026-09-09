from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hermes_affect.config import CORE_TRAIT_FIELDS, TUNING_FIELDS, neutral_config, parse_soul_affect
from hermes_affect.dynamics import apply_event, decay_state
from hermes_affect.events import AffectiveEvent, EventType
from hermes_affect.influence import (
    LayeredTraitResolver,
    ParticipantTraits,
    evaluate_influence,
)
from hermes_affect.models import AffectState, ParticipantRelation
from hermes_affect.posture import ResponsePosture, derive_posture
from hermes_affect.storage import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "soul"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class SoulConfigTests(unittest.TestCase):
    def test_missing_section_uses_neutral_defaults(self) -> None:
        config, warnings = parse_soul_affect("A free-form persona without configuration.")
        self.assertEqual(warnings, [])
        self.assertEqual(set(config.traits), set(CORE_TRAIT_FIELDS))
        self.assertTrue(all(value == 0.5 for value in config.traits.values()))
        self.assertEqual(dict(config.tuning), {name: 1.0 for name in TUNING_FIELDS})

    def test_valid_section_preserves_seven_traits_and_sensitivities(self) -> None:
        config, warnings = parse_soul_affect(fixture("valid.md"))
        self.assertEqual(warnings, [])
        self.assertEqual(set(config.traits), set(CORE_TRAIT_FIELDS))
        self.assertEqual(config.traits["persistence"], 0.75)
        self.assertEqual(config.traits["receptiveness"], 0.35)
        self.assertEqual(config.sensitivities[0].topic, "competence")

    def test_partial_section_fills_missing_values(self) -> None:
        config, warnings = parse_soul_affect(fixture("partial.md"))
        self.assertEqual(warnings, [])
        self.assertEqual(config.traits["pride"], 0.8)
        self.assertEqual(config.traits["reactivity"], 0.5)
        self.assertEqual(config.tuning["repair_gain"], 1.5)
        self.assertEqual(config.tuning["expression_gain"], 1.0)

    def test_trait_boundaries_are_inclusive(self) -> None:
        config, warnings = parse_soul_affect(
            """session_affect:
  schema_version: 1
  traits:
    reactivity: 0
    persistence: 1
    pride: 0
    playfulness: 1
    assertiveness: 0
    social_influence: 1
    receptiveness: 0
"""
        )
        self.assertEqual(warnings, [])
        self.assertEqual(config.traits["reactivity"], 0.0)
        self.assertEqual(config.traits["persistence"], 1.0)
        self.assertEqual(config.traits["playfulness"], 1.0)

    def test_invalid_section_falls_back_to_neutral(self) -> None:
        config, warnings = parse_soul_affect(fixture("invalid.md"))
        self.assertTrue(any("neutral defaults" in warning for warning in warnings))
        self.assertEqual(config.to_dict(), neutral_config().to_dict())

    def test_unknown_fields_warn_and_are_not_reinterpreted(self) -> None:
        config, warnings = parse_soul_affect(
            """session_affect:
  schema_version: 1
  traits:
    reactivity: 0.8
    unknown_trait: 0.95
  unknown_section:
    value: 1
"""
        )
        self.assertTrue(any("Unknown field" in warning for warning in warnings))
        self.assertEqual(config.traits["reactivity"], 0.8)
        self.assertEqual(set(config.traits), set(CORE_TRAIT_FIELDS))

    def test_tuning_is_separate_from_traits(self) -> None:
        config, _ = parse_soul_affect(fixture("valid.md"))
        serialized = config.to_dict()
        self.assertEqual(set(serialized["tuning"]), set(TUNING_FIELDS))
        self.assertEqual(
            set(serialized), {"schema_version", "traits", "tuning", "sensitivities"}
        )

    def test_schema_contains_only_the_compact_core_model(self) -> None:
        schema = json.loads(
            (Path(__file__).parents[1] / "schemas" / "session_affect.schema.json").read_text(
                encoding="utf-8"
            )
        )
        traits = schema["properties"]["traits"]["properties"]
        self.assertEqual(set(traits), set(CORE_TRAIT_FIELDS))
        self.assertEqual(
            set(schema["properties"]["tuning"]["properties"]), set(TUNING_FIELDS)
        )


class DynamicsTests(unittest.TestCase):
    def test_severe_insult_can_overcome_respect_for_proud_reactive_bot(self) -> None:
        config = replace(
            neutral_config(),
            traits={
                **neutral_config().traits,
                "pride": 1.0,
                "reactivity": 1.0,
                "assertiveness": 0.8,
            },
            tuning={**neutral_config().tuning, "escalation_gain": 2.0, "expression_gain": 2.0},
        )
        state = AffectState.initial("bot-a", "session-1")
        rule = apply_event(
            state,
            AffectiveEvent(
                EventType.INSULT,
                "bot:other",
                attributes={"severity": "severe", "topic": "competence"},
            ),
            config,
        )
        self.assertEqual(rule, "direct_offense")
        self.assertGreater(state.frustration, 0.3)
        self.assertIn("bot:other", state.open_conflicts)
        self.assertIn(
            derive_posture(state, config),
            {ResponsePosture.GUARDED, ResponsePosture.COUNTERATTACK},
        )

    def test_repeated_teasing_accumulates_relationship_tension(self) -> None:
        config = replace(
            neutral_config(),
            traits={**neutral_config().traits, "playfulness": 0.0},
        )
        state = AffectState.initial("bot-a", "session-1")
        teasing = AffectiveEvent(EventType.TEASING, "user:1")

        apply_event(state, teasing, config)
        first_tension = state.relationships["user:1"].unresolved_tension
        apply_event(state, teasing, config)

        self.assertGreater(state.relationships["user:1"].unresolved_tension, first_tension)
        self.assertGreater(state.frustration, 0.0)

    def test_high_pride_increases_escalation_from_the_same_insult(self) -> None:
        proud_config = replace(
            neutral_config(),
            traits={**neutral_config().traits, "pride": 1.0},
        )
        easygoing_config = replace(
            neutral_config(),
            traits={**neutral_config().traits, "pride": 0.0},
        )
        proud_state = AffectState.initial("bot-a", "proud")
        easygoing_state = AffectState.initial("bot-a", "easygoing")
        insult = AffectiveEvent(EventType.INSULT, "user:1")

        apply_event(proud_state, insult, proud_config)
        apply_event(easygoing_state, insult, easygoing_config)

        self.assertGreater(proud_state.offended, easygoing_state.offended)
        self.assertGreater(
            proud_state.relationships["user:1"].unresolved_tension,
            easygoing_state.relationships["user:1"].unresolved_tension,
        )

    def test_expression_gain_suppresses_counterattack_without_erasing_conflict(self) -> None:
        base = neutral_config()
        suppressed = replace(
            base,
            traits={**base.traits, "assertiveness": 0.9},
            tuning={**base.tuning, "escalation_gain": 2.0, "expression_gain": 0.5},
        )
        expressive = replace(
            suppressed,
            tuning={**suppressed.tuning, "expression_gain": 2.0},
        )
        suppressed_state = AffectState.initial("bot-a", "suppressed")
        expressive_state = AffectState.initial("bot-a", "expressive")
        insult = AffectiveEvent(
            EventType.INSULT,
            "user:1",
            attributes={"severity": "severe"},
        )

        apply_event(suppressed_state, insult, suppressed)
        apply_event(expressive_state, insult, expressive)

        self.assertEqual(derive_posture(suppressed_state, suppressed), ResponsePosture.GUARDED)
        self.assertEqual(
            derive_posture(expressive_state, expressive), ResponsePosture.COUNTERATTACK
        )
        self.assertIn("user:1", suppressed_state.open_conflicts)

    def test_event_postures_cover_mediation_steering_repair_and_pass(self) -> None:
        config = neutral_config()
        cases = (
            (EventType.BOT_MEDIATION, None, ResponsePosture.MEDIATION),
            (EventType.TOPIC_STEERING, None, ResponsePosture.TOPIC_STEERING),
            (EventType.RECONCILIATION, None, ResponsePosture.RECONCILIATION),
            (
                EventType.USER_MODERATION,
                "calm",
                ResponsePosture.PASS,
            ),
        )

        for event_type, action, expected in cases:
            state = AffectState.initial("bot-a", event_type.value)
            event = AffectiveEvent(event_type, "user:1", action=action)
            self.assertEqual(derive_posture(state, config, event), expected)

    def test_conflict_posture_can_avoid_topics_evade_or_refuse(self) -> None:
        evasive_config = replace(
            neutral_config(),
            traits={**neutral_config().traits, "assertiveness": 0.2},
            tuning={**neutral_config().tuning, "expression_gain": 0.5},
        )
        evasive_state = AffectState.initial("bot-a", "evasive")
        evasive_state.open_conflicts["user:1"] = {"status": "open"}
        evasive_state.frustration = 0.4
        self.assertEqual(
            derive_posture(evasive_state, evasive_config), ResponsePosture.EVASIVE
        )

        refusal_state = AffectState.initial("bot-a", "refusal")
        refusal_state.open_conflicts["user:1"] = {"status": "open"}
        refusal_state.frustration = 0.8
        refusal_state.offended = 0.8
        self.assertEqual(
            derive_posture(refusal_state, evasive_config), ResponsePosture.REFUSAL
        )

        avoidance_state = AffectState.initial("bot-a", "avoidance")
        avoidance_state.active_sensitivities.append("competence")
        avoidance_state.open_conflicts["user:1"] = {"status": "open"}
        avoidance_state.frustration = 0.4
        self.assertEqual(
            derive_posture(avoidance_state, evasive_config), ResponsePosture.TOPIC_AVOIDANCE
        )

    def test_reconciliation_can_clear_a_sudden_conflict(self) -> None:
        config = neutral_config()
        state = AffectState.initial("bot-a", "session-1")

        apply_event(state, AffectiveEvent(EventType.INSULT, "user:1"), config)
        frustrated = state.frustration
        apply_event(state, AffectiveEvent(EventType.RECONCILIATION, "user:1"), config)

        self.assertLess(state.frustration, frustrated)
        self.assertLess(state.relationships["user:1"].unresolved_tension, 0.15)
        self.assertNotIn("user:1", state.open_conflicts)

    def test_playfulness_changes_joke_interpretation(self) -> None:
        playful = replace(neutral_config(), traits={**neutral_config().traits, "playfulness": 1.0})
        serious = replace(neutral_config(), traits={**neutral_config().traits, "playfulness": 0.0})
        playful_state = AffectState.initial("bot-a", "playful")
        serious_state = AffectState.initial("bot-a", "serious")
        joke = AffectiveEvent(EventType.JOKE, "user:1")
        self.assertEqual(apply_event(playful_state, joke, playful), "playful_signal")
        self.assertEqual(
            apply_event(serious_state, joke, serious), "serious_joke_interpretation"
        )
        self.assertGreater(serious_state.frustration, playful_state.frustration)

    def test_persistence_controls_decay_rate(self) -> None:
        low = replace(neutral_config(), traits={**neutral_config().traits, "persistence": 0.0})
        high = replace(neutral_config(), traits={**neutral_config().traits, "persistence": 1.0})
        low_state = AffectState.initial("bot-a", "low")
        high_state = AffectState.initial("bot-a", "high")
        for state in (low_state, high_state):
            state.frustration = 0.8
            state.relationships["user:1"] = ParticipantRelation(unresolved_tension=0.7)
        decay_state(low_state, low, 1.0)
        decay_state(high_state, high, 1.0)
        self.assertLess(low_state.frustration, high_state.frustration)
        self.assertLess(
            low_state.relationships["user:1"].unresolved_tension,
            high_state.relationships["user:1"].unresolved_tension,
        )


class InfluenceTests(unittest.TestCase):
    def test_trait_resolution_prefers_public_then_observed_then_neutral(self) -> None:
        public = ParticipantTraits(playfulness=0.9)
        observed = ParticipantTraits(playfulness=0.2)
        resolver = LayeredTraitResolver(
            public_signatures={"bot:public": public},
            observed_traits={"bot:public": observed, "bot:observed": observed},
        )
        self.assertEqual(resolver.resolve("bot:public"), public)
        self.assertEqual(resolver.resolve("bot:observed"), observed)
        self.assertEqual(resolver.resolve("bot:unknown"), ParticipantTraits())

    def test_leadership_tendency_increases_with_assertiveness_and_influence(self) -> None:
        relation = ParticipantRelation(trust=0.7, respect=0.9)
        listener = ParticipantTraits(receptiveness=0.8, persistence=0.8)
        quiet = evaluate_influence(
            ParticipantTraits(assertiveness=0.2, social_influence=0.9), listener, relation
        )
        leader = evaluate_influence(
            ParticipantTraits(assertiveness=0.9, social_influence=0.9), listener, relation
        )
        self.assertGreater(
            leader.factors["leadership_tendency"], quiet.factors["leadership_tendency"]
        )
        self.assertGreater(leader.persuasion, quiet.persuasion)

    def test_effective_receptiveness_uses_receptiveness_respect_and_influence(self) -> None:
        relation = ParticipantRelation(trust=0.7, respect=0.9)
        influential = ParticipantTraits(assertiveness=0.8, social_influence=0.9)
        receptive = evaluate_influence(
            influential, ParticipantTraits(receptiveness=0.8, persistence=0.8), relation
        )
        resistant = evaluate_influence(
            influential, ParticipantTraits(receptiveness=0.1, persistence=0.8), relation
        )
        self.assertGreater(receptive.factors["effective_receptiveness"], resistant.factors[
            "effective_receptiveness"
        ])
        self.assertGreater(receptive.calming, resistant.calming)

    def test_respected_influential_bot_can_calm_receptive_listener(self) -> None:
        decision = evaluate_influence(
            ParticipantTraits(assertiveness=0.9, social_influence=0.9),
            ParticipantTraits(receptiveness=0.9, persistence=0.9),
            ParticipantRelation(trust=0.8, respect=0.95, unresolved_tension=0.1),
        )
        self.assertGreater(decision.calming, 0.2)
        self.assertLess(decision.conflict_risk, 0.5)

    def test_incompatible_temperaments_raise_conflict_risk(self) -> None:
        speaker = ParticipantTraits(assertiveness=0.9, social_influence=0.9)
        compatible = evaluate_influence(
            speaker,
            ParticipantTraits(
                reactivity=0.1,
                pride=0.1,
                receptiveness=0.9,
                persistence=0.9,
            ),
            ParticipantRelation(trust=0.7, respect=0.8),
        )
        incompatible = evaluate_influence(
            speaker,
            ParticipantTraits(
                reactivity=0.9,
                pride=0.9,
                receptiveness=0.1,
                persistence=0.2,
            ),
            ParticipantRelation(trust=-0.4, respect=0.1),
        )

        self.assertGreater(incompatible.conflict_risk, compatible.conflict_risk)
        self.assertLess(incompatible.calming, compatible.calming)


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

    def test_restart_resumes_existing_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first_process = StateStore(Path(temporary))
            state = AffectState.initial("bot/a", "session:1")
            state.revision = 4
            state.frustration = 0.6
            state.last_turn_id = "turn:4"
            first_process.save(state)

            restarted_process = StateStore(Path(temporary))
            resumed = restarted_process.load("bot/a", "session:1")
            self.assertIsNotNone(resumed)
            self.assertEqual(resumed.revision, 4)
            self.assertEqual(resumed.frustration, 0.6)
            self.assertEqual(resumed.last_turn_id, "turn:4")

    def test_profile_and_session_paths_are_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = StateStore(Path(temporary))
            profile_a_session_1 = AffectState.initial("bot/a", "session:1")
            profile_a_session_2 = AffectState.initial("bot/a", "session:2")
            profile_b_session_1 = AffectState.initial("bot/b", "session:1")
            profile_a_session_1.frustration = 0.1
            profile_a_session_2.frustration = 0.2
            profile_b_session_1.frustration = 0.3
            for state in (profile_a_session_1, profile_a_session_2, profile_b_session_1):
                store.save(state)

            paths = {
                store.state_path("bot/a", "session:1"),
                store.state_path("bot/a", "session:2"),
                store.state_path("bot/b", "session:1"),
            }
            self.assertEqual(len(paths), 3)
            self.assertEqual(store.load("bot/a", "session:1").frustration, 0.1)
            self.assertEqual(store.load("bot/a", "session:2").frustration, 0.2)
            self.assertEqual(store.load("bot/b", "session:1").frustration, 0.3)

    def test_future_state_schema_version_is_rejected(self) -> None:
        raw = AffectState.initial("bot/a", "session:1").to_dict()
        raw["schema_version"] = 2
        with self.assertRaisesRegex(ValueError, "Unsupported affect state schema version"):
            AffectState.from_dict(raw)

    def test_garbage_collection_removes_old_state_and_keeps_recent_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = StateStore(Path(temporary))
            now = datetime(2026, 1, 1, tzinfo=timezone.utc)
            old = AffectState.initial("bot/a", "old")
            old.updated_at = (now - timedelta(days=91)).isoformat()
            recent = AffectState.initial("bot/a", "recent")
            recent.updated_at = (now - timedelta(days=1)).isoformat()
            store.save(old)
            store.save(recent)

            report = store.garbage_collect(max_age_days=90, now=now)

            self.assertEqual(report.examined, 2)
            self.assertEqual(report.removed, (store.state_path("bot/a", "old"),))
            self.assertEqual(report.skipped, 1)
            self.assertIsNone(store.load("bot/a", "old"))
            self.assertIsNotNone(store.load("bot/a", "recent"))

    def test_garbage_collection_skips_excluded_and_locked_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = StateStore(Path(temporary))
            now = datetime(2026, 1, 1, tzinfo=timezone.utc)
            excluded = AffectState.initial("bot/a", "excluded")
            locked = AffectState.initial("bot/a", "locked")
            for state in (excluded, locked):
                state.updated_at = (now - timedelta(days=91)).isoformat()
                store.save(state)
            excluded_path = store.state_path("bot/a", "excluded")
            locked_path = store.state_path("bot/a", "locked")
            lock_path = locked_path.with_suffix(locked_path.suffix + ".lock")
            lock_path.write_text("active", encoding="ascii")
            try:
                report = store.garbage_collect(
                    max_age_days=90,
                    now=now,
                    exclude_paths={excluded_path},
                )
            finally:
                lock_path.unlink()

            self.assertEqual(report.removed, ())
            self.assertEqual(report.skipped, 2)
            self.assertTrue(excluded_path.exists())
            self.assertTrue(locked_path.exists())


if __name__ == "__main__":
    unittest.main()
