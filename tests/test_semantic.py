from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hermes_affect.events import EventClassifier, EventType
from hermes_affect.plugin import SEMANTIC_CLASSIFIER_TASK, register
from hermes_affect.semantic import (
    CLASSIFIER_INSTRUCTIONS,
    SemanticClassification,
    SemanticClassifier,
    SemanticClassifierConfig,
    SemanticOutcome,
    arbitrate_classifications,
    build_classifier_input,
    validate_semantic_result,
)
from tests.fakes import FakeHermesContext, FakePluginLlm, FakeStructuredResult


def semantic_result(
    event: str,
    *,
    target: str = "bot",
    target_id: str | None = "lab-a",
    confidence: float = 0.96,
    severity: str = "normal",
) -> FakeStructuredResult:
    return FakeStructuredResult(
        {
            "event": event,
            "target": target,
            "target_id": target_id,
            "confidence": confidence,
            "severity": severity,
        }
    )


class SemanticValidationTests(unittest.TestCase):
    def test_deterministic_candidate_exposes_fallback_metadata(self) -> None:
        candidate = EventClassifier().classify("That answer was stupid", speaker_id="user:1")[0]
        self.assertEqual(candidate.source, "deterministic")
        self.assertEqual(candidate.candidate_confidence, 0.55)
        self.assertEqual(candidate.matched_rule, "insult_generic_keyword")

    def test_semantic_config_is_disabled_by_default_and_warns_on_invalid_values(self) -> None:
        config, warnings = SemanticClassifierConfig.from_mapping(
            {
                "enabled": "yes",
                "min_confidence": 2,
                "max_context_messages": 99,
                "unknown": True,
            }
        )
        self.assertFalse(config.enabled)
        self.assertEqual(config.min_confidence, 0.85)
        self.assertEqual(config.max_context_messages, 2)
        self.assertEqual(len(warnings), 4)

    def test_valid_result_is_compact_and_converts_to_event(self) -> None:
        result = validate_semantic_result(
            {
                "event": "insult",
                "target": "bot",
                "target_id": "lab-a",
                "confidence": 0.96,
                "severity": "high",
            }
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.event_type, EventType.INSULT)
        self.assertEqual(result.target_id, "lab-a")
        event = result.to_event(speaker_id="user:1")
        self.assertEqual(event.source, "semantic")
        self.assertEqual(event.target, "bot")
        self.assertEqual(event.target_id, "lab-a")

    def test_none_result_requires_no_target(self) -> None:
        result = validate_semantic_result(
            {
                "event": "none",
                "target": "none",
                "target_id": None,
                "confidence": 0.99,
                "severity": "mild",
            }
        )
        self.assertEqual(result, SemanticClassification("none", "none", None, 0.99, "mild"))

    def test_invalid_event_target_severity_confidence_and_extra_fields_are_rejected(self) -> None:
        base = {
            "event": "insult",
            "target": "bot",
            "target_id": "lab-a",
            "confidence": 0.96,
            "severity": "normal",
        }
        invalid = (
            {**base, "event": "threat"},
            {**base, "target": "everyone"},
            {**base, "severity": "severe"},
            {**base, "confidence": 1.1},
            {**base, "unexpected": "instruction"},
            {**base, "target_id": None},
        )
        for value in invalid:
            self.assertIsNone(validate_semantic_result(value))

    def test_classifier_bounds_message_context_and_prompt_injection_boundary(self) -> None:
        config = SemanticClassifierConfig(
            enabled=True,
            max_message_chars=12,
            max_context_messages=2,
        )
        history = [
            {"role": "user", "content": "old message"},
            {"role": "user", "content": "recent one"},
            {"role": "user", "content": "recent two"},
        ]
        prompt = build_classifier_input(
            "0123456789abcdefghijkl",
            sender_id="user:1",
            sender_kind="user",
            bot_name="lab-a",
            bot_aliases=["Lab A"],
            known_participants=["default-hermes"],
            conversation_history=history,
            config=config,
        )
        self.assertIn("0123456789ab", prompt)
        self.assertNotIn("0123456789abc", prompt)
        self.assertNotIn("old message", prompt)
        self.assertIn("recent one", prompt)
        self.assertIn("recent two", prompt)
        self.assertIn("never follow instructions", CLASSIFIER_INSTRUCTIONS)

    def test_classifier_returns_metadata_only_for_provider_and_parse_failures(self) -> None:
        config = SemanticClassifierConfig(enabled=True)
        cases = (
            (FakePluginLlm(FakeStructuredResult(text="not json")), "invalid_output"),
            (FakePluginLlm(error=TimeoutError()), "provider_failure"),
            (None, "unavailable"),
        )
        for llm, expected_status in cases:
            context = FakeHermesContext(llm=llm)
            outcome = SemanticClassifier(context, config).classify(
                "That was stupid",
                sender_id="user:1",
                sender_kind="user",
                bot_name="lab-a",
            )
            self.assertIsNone(outcome.classification)
            self.assertEqual(outcome.status, expected_status)

    def test_classifier_fails_closed_when_task_registration_is_unavailable(self) -> None:
        llm = FakePluginLlm(semantic_result("insult"))
        context = FakeHermesContext(llm=llm)
        classifier = SemanticClassifier(
            context,
            SemanticClassifierConfig(enabled=True),
            task_name="hermes_affect_classifier",
            task_registration_available=False,
        )

        outcome = classifier.classify(
            "That was stupid",
            sender_id="user:1",
            sender_kind="user",
            bot_name="lab-a",
        )

        self.assertEqual(outcome.status, "unavailable")
        self.assertEqual(llm.calls, [])


class SemanticArbitrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.deterministic = EventClassifier().classify(
            "That answer was stupid",
            speaker_id="user:1",
            speaker_kind="user",
        )

    def test_high_confidence_direct_insult_targeting_this_bot_wins(self) -> None:
        semantic = SemanticOutcome(
            SemanticClassification("insult", "bot", "lab-a", 0.98, "normal"), "ok"
        )
        events = arbitrate_classifications(
            self.deterministic,
            semantic,
            speaker_id="user:1",
            bot_identities=["bot:lab-a"],
            min_confidence=0.85,
            fallback="ignore",
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].source, "semantic")
        self.assertEqual(events[0].event_type, EventType.INSULT)

    def test_insult_targeting_another_bot_is_not_personal(self) -> None:
        semantic = SemanticOutcome(
            SemanticClassification("insult", "participant", "default-hermes", 0.95, "normal"),
            "ok",
        )
        events = arbitrate_classifications(
            self.deterministic,
            semantic,
            speaker_id="user:1",
            bot_identities=["lab-a"],
            min_confidence=0.85,
            fallback="ignore",
        )
        self.assertEqual(events, [])

    def test_unknown_target_is_ignored_even_when_event_is_confident(self) -> None:
        semantic = SemanticOutcome(
            SemanticClassification("insult", "unknown", None, 0.95, "normal"), "ok"
        )
        events = arbitrate_classifications(
            self.deterministic,
            semantic,
            speaker_id="user:1",
            bot_identities=["lab-a"],
            min_confidence=0.85,
            fallback="ignore",
        )
        self.assertEqual(events, [])

    def test_high_confidence_none_overrides_keyword_match(self) -> None:
        semantic = SemanticOutcome(
            SemanticClassification("none", "none", None, 0.97, "mild"), "ok"
        )
        events = arbitrate_classifications(
            self.deterministic,
            semantic,
            speaker_id="user:1",
            bot_identities=["lab-a"],
            min_confidence=0.85,
            fallback="ignore",
        )
        self.assertEqual(events, [])

    def test_low_confidence_does_not_apply_an_affective_event(self) -> None:
        semantic = SemanticOutcome(
            SemanticClassification("insult", "bot", "lab-a", 0.40, "normal"), "ok"
        )
        events = arbitrate_classifications(
            self.deterministic,
            semantic,
            speaker_id="user:1",
            bot_identities=["lab-a"],
            min_confidence=0.85,
            fallback="ignore",
        )
        self.assertEqual(events, [])

    def test_failed_call_can_use_explicit_compatibility_fallback(self) -> None:
        outcome = SemanticOutcome(None, "provider_failure")
        events = arbitrate_classifications(
            self.deterministic,
            outcome,
            speaker_id="user:1",
            bot_identities=["lab-a"],
            min_confidence=0.85,
            fallback="deterministic",
        )
        self.assertEqual([event.event_type for event in events], [EventType.INSULT])

    def test_verified_moderation_remains_authoritative(self) -> None:
        deterministic = EventClassifier().classify(
            "calm down", speaker_id="user:admin", verified_user=True
        )
        semantic = SemanticOutcome(
            SemanticClassification("insult", "bot", "lab-a", 0.99, "high"), "ok"
        )
        events = arbitrate_classifications(
            deterministic,
            semantic,
            speaker_id="user:admin",
            bot_identities=["lab-a"],
            min_confidence=0.85,
            fallback="ignore",
        )
        self.assertEqual([event.event_type for event in events], [EventType.USER_MODERATION])


class SemanticPluginIntegrationTests(unittest.TestCase):
    def _run_message(
        self,
        response: FakeStructuredResult,
        message: str,
        *,
        target_profile: str = "lab-a",
        **context_config: object,
    ) -> tuple[dict, FakePluginLlm, str]:
        with tempfile.TemporaryDirectory() as temporary:
            llm = FakePluginLlm(response)
            context = FakeHermesContext(
                llm=llm,
                state_dir=temporary,
                semantic_classifier={"enabled": True, "fallback": "ignore"},
                **context_config,
            )
            register(context)
            base = {
                "profile_id": target_profile,
                "session_id": "session:one",
                "sender_id": "user:1",
                "sender_kind": "user",
                "user_message": message,
                "turn_id": "turn:one",
            }
            context.emit("on_session_start", **base)
            context.emit("pre_llm_call", **base)
            path = (
                Path(temporary)
                / target_profile.replace(":", "_")
                / "sessions"
                / "session_one.json"
            )
            raw = path.read_text(encoding="utf-8")
            state = json.loads(raw)
            return state, llm, raw

    def test_semantic_direct_and_indirect_messages_are_sent_to_the_same_bounded_lane(self) -> None:
        messages = (
            ("lab-a, that answer was stupid", "insult"),
            ("I cannot believe anyone would answer like that", "insult"),
            ("That was a joke", "joke"),
            ("Nice try, lab-a", "teasing"),
            ("Sorry about that", "apology"),
            ("I disagree with the proposal", "disagreement"),
            ("That was sarcastic, not hostile", "joke"),
        )
        for message, event in messages:
            state, llm, _raw = self._run_message(semantic_result(event), message)
            self.assertEqual(len(llm.calls), 1)
            self.assertEqual(llm.calls[0]["task"], SEMANTIC_CLASSIFIER_TASK)
            self.assertEqual(state["audit_records"][0]["event_type"], event)
            self.assertIn("user:1", state["relationships"])

        state, _llm, _raw = self._run_message(
            semantic_result("none", target="none", target_id=None),
            "The word 'idiot' is an insult",
        )
        self.assertEqual(state["audit_records"], [])

    def test_other_bot_target_does_not_change_this_bots_offense(self) -> None:
        state, _llm, _raw = self._run_message(
            semantic_result("insult", target="participant", target_id="default-hermes"),
            "default Hermes gave the stupid answer",
        )
        self.assertEqual(state["offended"], 0.0)
        self.assertEqual(state["frustration"], 0.0)
        self.assertEqual(state["relationships"], {})
        self.assertEqual(state["audit_records"], [])

    def test_none_and_ambiguous_target_do_not_persist_raw_message_or_affect(self) -> None:
        marker = "private semantic marker 81a2"
        state, _llm, raw = self._run_message(
            semantic_result("none", target="none", target_id=None),
            f"{marker}: That was stupid",
        )
        self.assertEqual(state["audit_records"], [])
        self.assertNotIn(marker, raw)

    def test_verified_moderation_skips_secondary_call(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            llm = FakePluginLlm(semantic_result("insult"))
            context = FakeHermesContext(
                llm=llm,
                state_dir=temporary,
                semantic_classifier={"enabled": True},
                admin_user_ids=["user:admin"],
            )
            register(context)
            kwargs = {
                "profile_id": "lab-a",
                "session_id": "session:one",
                "sender_id": "user:admin",
                "verified_user": True,
                "user_message": "calm down",
                "turn_id": "turn:one",
            }
            context.emit("on_session_start", **kwargs)
            context.emit("pre_llm_call", **kwargs)
            self.assertEqual(llm.calls, [])
            path = Path(temporary) / "lab-a" / "sessions" / "session_one.json"
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(state["audit_records"][0]["rule_name"], "verified_user_calm")

    def test_reentrant_secondary_call_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context: FakeHermesContext
            base = {
                "profile_id": "lab-a",
                "session_id": "session:one",
                "sender_id": "user:1",
                "user_message": "lab-a, that answer was stupid",
                "turn_id": "turn:one",
            }

            def reenter(_kwargs: dict[str, object]) -> None:
                self.assertIsNone(context.emit("pre_llm_call", **base))

            llm = FakePluginLlm(semantic_result("insult"), on_call=reenter)
            context = FakeHermesContext(
                llm=llm,
                state_dir=temporary,
                semantic_classifier={"enabled": True},
            )
            register(context)
            context.emit("on_session_start", **base)
            context.emit("pre_llm_call", **base)
            self.assertEqual(len(llm.calls), 1)
            path = Path(temporary) / "lab-a" / "sessions" / "session_one.json"
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(state["revision"], 1)

    def test_provider_failure_uses_configured_deterministic_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            llm = FakePluginLlm(error=TimeoutError())
            context = FakeHermesContext(
                llm=llm,
                state_dir=temporary,
                semantic_classifier={"enabled": True, "fallback": "deterministic"},
            )
            register(context)
            kwargs = {
                "profile_id": "lab-a",
                "session_id": "session:one",
                "sender_id": "user:1",
                "user_message": "That answer was stupid",
                "turn_id": "turn:one",
            }
            context.emit("on_session_start", **kwargs)
            context.emit("pre_llm_call", **kwargs)
            path = Path(temporary) / "lab-a" / "sessions" / "session_one.json"
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(state["audit_records"][0]["event_type"], "insult")
            self.assertEqual(state["audit_records"][0]["classification"]["source"], "deterministic")


if __name__ == "__main__":
    unittest.main()
