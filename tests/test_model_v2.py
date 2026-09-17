"""Behavioral regressions through the real runtime, using deterministic synthetic input."""

from __future__ import annotations

import json
import math
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hermes_affect.calculations import effective_expression_drive, event_severity
from hermes_affect.calibration import migration_proposal, preset_config, run_scenario
from hermes_affect.config import Sensitivity, neutral_config, parse_soul_affect
from hermes_affect.events import AffectiveEvent, EventClassifier, EventType
from hermes_affect.models import AffectState
from hermes_affect.runtime import AffectRuntime
from hermes_affect.targeting import route_events
from tests.fakes import FakeHermesContext, FakePluginLlm, FakeStructuredResult


def configured(**traits):
    base = neutral_config()
    return replace(base, traits={**base.traits, **traits})


class ModelBehaviorTests(unittest.TestCase):
    def test_expression_changes_guidance_but_not_transitions(self):
        base = neutral_config()
        quiet = run_scenario(replace(base, tuning={"expression_gain": 0}), "repair")
        loud = run_scenario(replace(base, tuning={"expression_gain": 3}), "repair")
        for a, b in zip(quiet["turns"], loud["turns"]):
            for field in ("frustration", "offended", "valence", "perceived_tension"):
                self.assertEqual(a[field], b[field])
            self.assertIsNone(a["guidance"])
            self.assertIsNotNone(b["guidance"])

    def test_positive_intensity_never_requests_a_rebuttal(self):
        report = run_scenario(replace(neutral_config(), tuning={"expression_gain": 10}), "praise")
        self.assertEqual(report["turns"][-1]["expression_tier"], "intense")
        for row in report["turns"]:
            self.assertNotIn("rebuttal", row["guidance"])
            self.assertNotIn("conflict is intense", row["guidance"])
            self.assertEqual(row["offended"], 0)

    def test_neutral_expression_can_reach_every_tier(self):
        report = run_scenario(
            neutral_config(),
            turns=[
                {"user_message": "you are useless", "sender_id": "bot:B", "target_id": "bot:A"},
            ]
            * 8,
        )
        self.assertTrue(
            {"visible", "strong", "intense"} <= {row["expression_tier"] for row in report["turns"]}
        )
        self.assertEqual(effective_expression_drive(AffectState("a", "s"), neutral_config()), 0)

    def test_reactivity_controls_positive_and_negative_reactions(self):
        for scenario, field in (("praise", "valence"), ("repair", "offended")):
            low = run_scenario(configured(reactivity=0), scenario)["turns"][0]
            high = run_scenario(configured(reactivity=1), scenario)["turns"][0]
            self.assertLess(low[field], high[field])

    def test_persistence_only_changes_passive_decay(self):
        low = run_scenario(configured(persistence=0), "cooling")["turns"]
        high = run_scenario(configured(persistence=1), "cooling")["turns"]
        self.assertEqual(low[:-1], high[:-1])
        self.assertLess(low[-1]["offended"], high[-1]["offended"])

    def test_pride_affects_disrespect_without_penalizing_praise(self):
        low = run_scenario(configured(pride=0), "repair")["turns"][0]
        high = run_scenario(configured(pride=1), "repair")["turns"][0]
        self.assertLess(low["offended"], high["offended"])
        self.assertEqual(
            run_scenario(configured(pride=0), "praise")["turns"],
            run_scenario(configured(pride=1), "praise")["turns"],
        )

    def test_mischievous_temperament_generates_visible_provocation_guidance(self):
        mischievous = run_scenario(preset_config("mischievous"))
        neutral = run_scenario(neutral_config())
        self.assertEqual(mischievous["turns"][0]["posture"], "mischievous_teasing")
        self.assertIn("cheeky tease", mischievous["turns"][0]["guidance"])
        self.assertNotEqual(neutral["turns"][0]["posture"], "mischievous_teasing")

    def test_compatible_banter_and_sensitive_conflict_diverge(self):
        playful = run_scenario(preset_config("mischievous"))["turns"][7]
        sensitive = run_scenario(preset_config("sensitive"))["turns"][7]
        self.assertLess(playful["offended"], sensitive["offended"])
        self.assertGreater(playful["valence"], sensitive["valence"])
        self.assertEqual(sensitive["posture"], "deliberate_topic_avoidance")

    def test_assertiveness_changes_response_to_same_personal_offense(self):
        low = run_scenario(configured(assertiveness=0, reactivity=0.4), "repair")["turns"][4]
        high = run_scenario(configured(assertiveness=1, reactivity=0.4), "repair")["turns"][4]
        self.assertEqual(low["offended"], high["offended"])
        self.assertNotEqual(low["posture"], high["posture"])

    def test_receptiveness_changes_repair(self):
        low = run_scenario(configured(receptiveness=0), "repair")["turns"]
        high = run_scenario(configured(receptiveness=1), "repair")["turns"]
        # Compare the repair delta, since receptiveness also softens earlier insults.
        self.assertGreater(
            high[4]["frustration"] - high[5]["frustration"],
            low[4]["frustration"] - low[5]["frustration"],
        )

    def test_disagreement_does_not_create_personal_offense(self):
        report = run_scenario(preset_config("sensitive"), "disagreement")
        self.assertTrue(all(row["offended"] == 0 for row in report["turns"]))

    def test_group_tension_is_perceived_without_personal_offense(self):
        emotional = run_scenario(preset_config("sensitive"), "group")
        resilient = run_scenario(preset_config("resilient"), "group")
        self.assertGreater(
            emotional["turns"][1]["perceived_tension"], resilient["turns"][1]["perceived_tension"]
        )
        self.assertTrue(all(row["offended"] == 0 for row in emotional["turns"]))
        self.assertTrue(all(row["frustration"] == 0 for row in emotional["turns"]))

    def test_observer_distinguishes_teasing_from_expressed_distress(self):
        report = run_scenario(preset_config("mediator"), "group")
        self.assertTrue(
            any(
                e["speaker_id"] == "bot:B"
                and e["target_id"] == "bot:C"
                and e["last_event"] == "teasing"
                for e in report["social_edges"]
            )
        )
        self.assertIn("bot:C", report["observed_distress"])
        self.assertNotIn("bot:B", report["observed_distress"])
        self.assertIn("appears_frustrated", report["turns"][5]["guidance"])
        self.assertIn("may be mistaken", report["turns"][5]["guidance"])
        self.assertEqual(report["turns"][5]["posture"], "mediation")
        first = run_scenario(
            neutral_config(),
            turns=[
                {
                    "user_message": "nice try",
                    "sender_id": "bot:B",
                    "target_id": "bot:C",
                }
            ],
        )
        self.assertEqual(first["observed_distress"], {})

    def test_ambiguous_group_hostility_does_not_create_personal_injury(self):
        report = run_scenario(
            neutral_config(),
            turns=[
                {
                    "user_message": "you are useless",
                    "sender_id": "bot:B",
                }
            ],
        )
        self.assertEqual(report["turns"][0]["offended"], 0)
        self.assertEqual(report["social_edges"], [])

    def test_an_unrelated_participant_does_not_receive_retaliation(self):
        turns = [
            {"user_message": "you are useless", "sender_id": "bot:B", "target_id": "bot:A"}
        ] * 7
        turns += [{"user_message": "hello", "sender_id": "bot:C", "target_id": "bot:A"}]
        report = run_scenario(configured(assertiveness=1), turns=turns)["turns"]
        self.assertEqual(report[-2]["posture"], "verbal_counterattack")
        self.assertNotIn(report[-1]["posture"], {"verbal_counterattack", "refusal_to_cooperate"})

    def test_moderation_precedence_survives_mixed_signals(self):
        report = run_scenario(
            preset_config("sensitive"),
            turns=[
                {"user_message": "you are useless", "sender_id": "bot:B", "target_id": "bot:A"},
                {
                    "user_message": "calm down you idiot",
                    "sender_id": "user:admin",
                    "verified_user": True,
                    "sender_kind": "user",
                },
            ],
        )
        self.assertEqual(report["turns"][-1]["posture"], "pass")
        self.assertLess(report["turns"][-1]["offended"], report["turns"][0]["offended"])

    def test_duplicate_matches_apply_one_event(self):
        events = EventClassifier().classify("you are useless", speaker_id="b", speaker_kind="bot")
        self.assertEqual(len(events), 1)

    def test_sensitivity_activates_and_clears_in_runtime(self):
        base = configured(reactivity=1, pride=1, assertiveness=1)
        sensitive = replace(base, sensitivities=(Sensitivity("competence", 1),))
        turns = [
            {
                "user_message": "you are useless at competence",
                "sender_id": "bot:B",
                "target_id": "bot:A",
            }
        ] * 3
        turns += [{"user_message": "hello", "sender_id": "bot:C", "target_id": "bot:A"}]
        normal = run_scenario(base, turns=turns)["turns"]
        affected = run_scenario(sensitive, turns=turns)["turns"]
        self.assertGreater(affected[0]["offended"], normal[0]["offended"])
        self.assertEqual(affected[2]["posture"], "deliberate_topic_avoidance")
        self.assertNotEqual(affected[3]["posture"], "deliberate_topic_avoidance")

    def test_nonfinite_severity_does_not_poison_state(self):
        for value in ("nan", "inf", "-inf"):
            event = AffectiveEvent(EventType.INSULT, "b", attributes={"severity": value})
            self.assertTrue(math.isfinite(event_severity(event)))

    def test_synthetic_runs_are_reproducible(self):
        self.assertEqual(
            run_scenario(neutral_config(), "group"), run_scenario(neutral_config(), "group")
        )


class SnapshotAndMigrationTests(unittest.TestCase):
    def test_documented_fenced_soul_does_not_consume_surrounding_prose(self):
        path = Path(__file__).parents[1] / "examples" / "soul" / "basic.md"
        config, warnings = parse_soul_affect(path.read_text(encoding="utf-8"))
        self.assertEqual(warnings, [])
        self.assertEqual(config.traits["reactivity"], 0.68)
        self.assertEqual(config.sensitivities[0].topic, "competence")

    def test_diagnostic_uses_selected_profile_snapshot_and_is_read_only(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = AffectRuntime(
                FakeHermesContext(
                    state_dir=root,
                    soul_path=Path(root) / "absent",
                    admin_user_ids=["admin"],
                )
            )
            config = replace(neutral_config(), tuning={"expression_gain": 0})
            state = AffectState.initial("other", "s", predisposition=config.to_dict())
            state.frustration = 0.9
            state.social_edges = [
                {"speaker_id": "b", "target_id": "c", "tension": 0.8, "last_event": "teasing"}
            ]
            runtime.store.save(state)
            runtime.config = replace(neutral_config(), tuning={"expression_gain": 10})
            payload = json.loads(
                runtime.command(
                    args_raw="state other",
                    profile_id="caller",
                    session_id="caller-session",
                )
            )
            self.assertEqual(payload["expression_drive"], 0)
            self.assertNotIn("social_edges", payload)
            self.assertIsNone(runtime.store.load("caller", "caller-session"))
            denied = runtime.command(args_raw="explain", profile_id="other", session_id="s")
            self.assertIn("verified user", denied)
            explanation = json.loads(
                runtime.command(
                    args_raw="explain",
                    profile_id="other",
                    session_id="s",
                    sender_id="admin",
                )
            )
            self.assertEqual(explanation["social_edges"], state.social_edges)

    def test_targeting_handles_own_aliases_without_guessing_unknown_recipients(self):
        event = AffectiveEvent(EventType.INSULT, "bot:B")
        resolved = route_events(
            [event],
            "A, you are useless",
            bot_ids=["bot:A", "A"],
            participants=["bot:A", "A", "bot:B"],
            is_group=True,
            config=neutral_config(),
        )
        self.assertEqual(resolved[0].target, "bot")
        self.assertEqual(resolved[0].target_id, "bot:A")
        unresolved = route_events(
            [event],
            "you are useless",
            bot_ids=["bot:A"],
            participants=["bot:A"],
            explicit_target="unknown-person",
            config=neutral_config(),
        )
        self.assertEqual(unresolved, [])

    def test_ordinary_semantic_families_apply_severity_in_runtime(self):
        for kind in (
            "praise",
            "joke",
            "teasing",
            "insult",
            "disagreement",
            "apology",
            "reconciliation",
            "bot_mediation",
        ):
            effects = []
            for severity in ("mild", "high"):
                with (
                    self.subTest(kind=kind, severity=severity),
                    tempfile.TemporaryDirectory() as root,
                ):
                    llm = FakePluginLlm(
                        FakeStructuredResult(
                            parsed={
                                "event": kind,
                                "target": "bot",
                                "target_id": "a",
                                "confidence": 0.99,
                                "severity": severity,
                            }
                        )
                    )
                    runtime = AffectRuntime(
                        FakeHermesContext(
                            state_dir=root,
                            soul_path=Path(root) / "absent",
                            llm=llm,
                            semantic_classifier={"enabled": True},
                        )
                    )
                    now = datetime.now(timezone.utc)
                    runtime._now = lambda: now
                    state = AffectState.initial("a", "s")
                    state.frustration = 0.5
                    state.offended = 0.5
                    state.updated_at = now.isoformat()
                    runtime.store.save(state)
                    runtime.pre_llm_call(
                        profile_id="a",
                        session_id="s",
                        turn_id="1",
                        sender_id="b",
                        user_message="synthetic",
                    )
                    updated = runtime.store.load("a", "s")
                    effects.append(
                        sum(
                            abs(getattr(updated, name) - getattr(state, name))
                            for name in ("valence", "arousal", "frustration", "offended")
                        )
                    )
            self.assertGreater(effects[1], effects[0], kind)

    def test_unknown_semantic_participant_is_not_observed(self):
        with tempfile.TemporaryDirectory() as root:
            llm = FakePluginLlm(
                FakeStructuredResult(
                    parsed={
                        "event": "insult",
                        "target": "participant",
                        "target_id": "unknown",
                        "confidence": 0.99,
                        "severity": "high",
                    }
                )
            )
            runtime = AffectRuntime(
                FakeHermesContext(
                    state_dir=root,
                    soul_path=Path(root) / "absent",
                    llm=llm,
                    semantic_classifier={"enabled": True},
                )
            )
            runtime.pre_llm_call(
                profile_id="a",
                session_id="s",
                turn_id="1",
                sender_id="b",
                user_message="synthetic",
                known_participants=["a", "b", "c"],
            )
            state = runtime.store.load("a", "s")
            self.assertEqual(state.social_edges, [])
            self.assertEqual(state.offended, 0)

    def test_legacy_compression_does_not_clone_or_convert_state(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = AffectRuntime(
                FakeHermesContext(
                    state_dir=root,
                    soul_path=Path(root) / "absent",
                )
            )
            parent = AffectState("a", "parent", model_version=1)
            parent.predisposition["schema_version"] = 1
            runtime.store.save(parent)
            self.assertIsNone(
                runtime._state(
                    {
                        "profile_id": "a",
                        "session_id": "child",
                        "parent_session_id": "parent",
                    }
                )
            )
            self.assertIsNone(runtime.store.load("a", "child"))
            self.assertEqual(runtime.store.load("a", "parent").model_version, 1)

    def test_restart_uses_snapshot_for_subsequent_behavior(self):
        with tempfile.TemporaryDirectory() as root:
            soul = Path(root) / "SOUL.md"
            soul.write_text(
                "session_affect:\n  schema_version: 2\n  traits:\n    reactivity: 0.8\n"
            )
            ctx = FakeHermesContext(state_dir=root, soul_path=soul)
            first = AffectRuntime(ctx)
            first.on_session_start(profile_id="a", session_id="s")
            soul.write_text(
                "session_affect:\n  schema_version: 2\n  traits:\n    reactivity: 0.2\n"
            )
            restarted = AffectRuntime(ctx)
            restarted.on_session_start(profile_id="a", session_id="s")
            restarted.pre_llm_call(
                profile_id="a", session_id="s", user_message="good job", sender_id="b", turn_id="1"
            )
            state = restarted.store.load("a", "s")
            self.assertAlmostEqual(state.valence, 0.12 * (0.25 + 0.75 * 0.8))
            self.assertEqual(restarted._config_for_state(state).traits["reactivity"], 0.8)

    def test_legacy_state_is_not_written_until_explicit_reset(self):
        with tempfile.TemporaryDirectory() as root:
            soul = Path(root) / "SOUL.md"
            soul.write_text("session_affect:\n  schema_version: 2\n")
            runtime = AffectRuntime(
                FakeHermesContext(
                    state_dir=root,
                    soul_path=soul,
                    admin_user_ids=["admin"],
                )
            )
            legacy = AffectState("a", "s")
            raw = legacy.to_dict()
            raw["schema_version"] = 1
            raw.pop("model_version")
            raw["predisposition"]["schema_version"] = 1
            path = runtime.store.state_path("a", "s")
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(raw))
            before = path.read_bytes()
            self.assertIsNone(
                runtime.pre_llm_call(
                    profile_id="a", session_id="s", user_message="idiot", turn_id="1"
                )
            )
            runtime.post_llm_call(profile_id="a", session_id="s")
            runtime.on_session_end(profile_id="a", session_id="s")
            self.assertEqual(path.read_bytes(), before)
            runtime.command(
                args_raw="reset",
                profile_id="a",
                session_id="s",
                sender_id="admin",
                verified_user=True,
            )
            self.assertEqual(runtime.store.load("a", "s").model_version, 2)

    def test_migration_proposal_reports_lossy_controls(self):
        proposal = migration_proposal(
            "session_affect:\n  schema_version: 1\n  tuning:\n    repair_gain: 4\n",
        )
        self.assertEqual(proposal["removed"]["repair_gain"], 4)
        self.assertEqual(proposal["proposed_session_affect"]["schema_version"], 2)
        self.assertNotIn("repair_gain", proposal["proposed_session_affect"]["tuning"])

    def test_legacy_configuration_is_recognized_not_neutralized(self):
        config, warnings = parse_soul_affect(
            "session_affect:\n  schema_version: 1\n  traits:\n    reactivity: 0.9\n",
        )
        self.assertEqual(config.schema_version, 1)
        self.assertEqual(config.traits["reactivity"], 0.9)
        self.assertTrue(any("migration" in w for w in warnings))

    def test_semantic_third_party_target_updates_observation_not_offense(self):
        with tempfile.TemporaryDirectory() as root:
            llm = FakePluginLlm(
                FakeStructuredResult(
                    parsed={
                        "event": "teasing",
                        "target": "participant",
                        "target_id": "bot:C",
                        "confidence": 0.99,
                        "severity": "high",
                    }
                )
            )
            runtime = AffectRuntime(
                FakeHermesContext(
                    state_dir=root,
                    soul_path=Path(root) / "absent",
                    semantic_classifier={"enabled": True},
                    llm=llm,
                )
            )
            runtime.pre_llm_call(
                profile_id="bot:A",
                session_id="s",
                sender_id="bot:B",
                user_message="C, nice try",
                turn_id="1",
                known_participants=["bot:A", "bot:B", "bot:C"],
            )
            state = runtime.store.load("bot:A", "s")
            self.assertEqual(state.offended, 0)
            self.assertEqual(state.social_edges[0]["target_id"], "bot:C")
            self.assertGreater(state.atmosphere_tension, 0)

    def test_decay_clears_conflict_projection(self):
        with tempfile.TemporaryDirectory() as root:
            now = datetime(2026, 1, 1, tzinfo=timezone.utc)
            runtime = AffectRuntime(
                FakeHermesContext(
                    state_dir=root,
                    soul_path=Path(root) / "absent",
                ),
                now=lambda: now,
            )
            state = AffectState.initial("a", "s")
            state.updated_at = now.isoformat()
            runtime.store.save(state)
            for i in range(8):
                runtime.pre_llm_call(
                    profile_id="a",
                    session_id="s",
                    sender_id="b",
                    user_message="idiot",
                    turn_id=str(i),
                )
            self.assertIn("b", runtime.store.load("a", "s").open_conflicts)
            now += timedelta(hours=100)
            runtime.pre_llm_call(
                profile_id="a", session_id="s", sender_id="b", user_message="hello", turn_id="later"
            )
            self.assertEqual(runtime.store.load("a", "s").open_conflicts, {})


if __name__ == "__main__":
    unittest.main()
