from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hermes_affect.models import AffectState
from hermes_affect.plugin import register
from tests.fakes import FakeHermesContext


class PluginAdapterTests(unittest.TestCase):
    def test_registers_public_hooks_and_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary, admin_user_ids=["user:admin"])
            register(context)

            self.assertEqual(
                set(context.hooks),
                {
                    "on_session_start",
                    "pre_llm_call",
                    "post_llm_call",
                    "on_session_end",
                    "on_session_reset",
                    "on_session_finalize",
                },
            )
            self.assertIn("affect", context.commands)
            self.assertIn("session-scoped", context.commands["affect"][1])

    def test_lifecycle_persists_state_and_injects_internal_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            soul_path = Path(temporary) / "SOUL.md"
            soul_path.write_text(
                """session_affect:
  schema_version: 1
  traits:
    reactivity: 0.8
    pride: 0.7
""",
                encoding="utf-8",
            )
            context = FakeHermesContext(
                state_dir=temporary,
                soul_path=soul_path,
                admin_user_ids=["user:admin"],
            )
            register(context)
            kwargs = {
                "profile_id": "bot:one",
                "session_id": "session:one",
                "turn_id": "turn:one",
                "sender_id": "user:1",
                "user_message": "good job",
            }

            context.emit("on_session_start", **kwargs)
            injected = context.emit("pre_llm_call", **kwargs)
            duplicate = context.emit("pre_llm_call", **kwargs)
            context.emit("post_llm_call", **kwargs)
            context.emit("on_session_end", **kwargs)

            self.assertIn("context", injected)
            self.assertIn("Internal affective guidance", injected["context"])
            self.assertIn("Internal affective guidance", duplicate["context"])
            state_path = Path(temporary) / "bot_one" / "sessions" / "session_one.json"
            self.assertTrue(state_path.exists())
            state = AffectState.from_dict(json.loads(state_path.read_text(encoding="utf-8")))
            self.assertEqual(state.soul_sha256 and len(state.soul_sha256), 64)
            self.assertEqual(state.predisposition["traits"]["reactivity"], 0.8)
            self.assertEqual(state.last_turn_id, "turn:one")

    def test_accepts_target_hermes_lifecycle_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary)
            register(context)

            context.emit(
                "on_session_start",
                session_id="session:one",
                model="test-model",
                platform="discord",
            )
            context.emit(
                "pre_llm_call",
                session_id="session:one",
                task_id="task:one",
                turn_id="turn:one",
                user_message="hello",
                conversation_history=[],
                is_first_turn=True,
                model="test-model",
                platform="discord",
                parent_session_id="",
                sender_id="user:one",
            )
            context.emit(
                "post_llm_call",
                session_id="session:one",
                task_id="task:one",
                turn_id="turn:one",
                user_message="hello",
                assistant_response="hi",
                conversation_history=[],
                model="test-model",
                platform="discord",
            )
            context.emit(
                "on_session_end",
                session_id="session:one",
                task_id="task:one",
                turn_id="turn:one",
                completed=True,
                failed=False,
                interrupted=False,
                turn_exit_reason="completed",
                model="test-model",
                platform="discord",
            )
            context.emit(
                "on_session_reset",
                session_id="session:two",
                platform="discord",
                reason="new_session",
                old_session_id="session:one",
                new_session_id="session:two",
            )
            context.emit(
                "on_session_finalize",
                session_id="session:two",
                platform="discord",
                reason="session_expired",
            )

            self.assertTrue(
                (Path(temporary) / "default" / "sessions" / "session_two.json").exists()
            )

    def test_restart_does_not_replace_existing_soul_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            soul_path = Path(temporary) / "SOUL.md"
            soul_path.write_text(
                """session_affect:
  schema_version: 1
  traits:
    reactivity: 0.8
""",
                encoding="utf-8",
            )
            first_context = FakeHermesContext(state_dir=temporary, soul_path=soul_path)
            register(first_context)
            base = {"profile_id": "bot:one", "session_id": "session:one"}
            first_context.emit("on_session_start", **base)
            state_path = Path(temporary) / "bot_one" / "sessions" / "session_one.json"
            first_state = AffectState.from_dict(
                json.loads(state_path.read_text(encoding="utf-8"))
            )

            soul_path.write_text(
                """session_affect:
  schema_version: 1
  traits:
    reactivity: 0.2
""",
                encoding="utf-8",
            )
            restarted_context = FakeHermesContext(state_dir=temporary, soul_path=soul_path)
            register(restarted_context)
            restarted_context.emit("on_session_start", **base)
            restarted_state = AffectState.from_dict(
                json.loads(state_path.read_text(encoding="utf-8"))
            )

            self.assertEqual(restarted_state.soul_sha256, first_state.soul_sha256)
            self.assertEqual(restarted_state.predisposition, first_state.predisposition)

    def test_callback_soul_path_is_used_without_context_override(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            soul_path = Path(temporary) / "callback-SOUL.md"
            soul_path.write_text(
                """session_affect:
  schema_version: 1
  traits:
    reactivity: 0.9
""",
                encoding="utf-8",
            )
            context = FakeHermesContext(state_dir=temporary)
            register(context)
            context.emit(
                "on_session_start",
                profile_id="bot:one",
                session_id="session:one",
                soul_path=soul_path,
            )

            state_path = Path(temporary) / "bot_one" / "sessions" / "session_one.json"
            state = AffectState.from_dict(json.loads(state_path.read_text(encoding="utf-8")))
            self.assertEqual(state.predisposition["traits"]["reactivity"], 0.9)
            self.assertEqual(len(state.soul_sha256 or ""), 64)

    def test_environment_defaults_provide_profile_and_soul_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            hermes_home = Path(temporary) / "hermes-home"
            state_dir = Path(temporary) / "state"
            hermes_home.mkdir()
            (hermes_home / "SOUL.md").write_text(
                """session_affect:
  schema_version: 1
  traits:
    pride: 0.85
""",
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "HERMES_HOME": str(hermes_home),
                    "HERMES_PROFILE": "bot:environment",
                },
                clear=False,
            ):
                context = FakeHermesContext(state_dir=state_dir)
                register(context)
                context.emit("on_session_start", session_id="session:one")

            state_path = state_dir / "bot_environment" / "sessions" / "session_one.json"
            state = AffectState.from_dict(json.loads(state_path.read_text(encoding="utf-8")))
            self.assertEqual(state.profile_id, "bot:environment")
            self.assertEqual(state.predisposition["traits"]["pride"], 0.85)

    def test_environment_state_dir_is_used_without_context_override(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = Path(temporary) / "environment-state"
            with patch.dict(
                os.environ,
                {
                    "HERMES_AFFECT_STATE_DIR": str(state_dir),
                    "HERMES_PROFILE": "bot:environment",
                },
                clear=False,
            ):
                context = FakeHermesContext()
                register(context)
                context.emit("on_session_start", session_id="session:one")

            state_path = state_dir / "bot_environment" / "sessions" / "session_one.json"
            self.assertTrue(state_path.exists())

    def test_context_state_dir_precedes_environment_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            environment_dir = Path(temporary) / "environment-state"
            context_dir = Path(temporary) / "context-state"
            with patch.dict(
                os.environ,
                {
                    "HERMES_AFFECT_STATE_DIR": str(environment_dir),
                    "HERMES_PROFILE": "bot:environment",
                },
                clear=False,
            ):
                context = FakeHermesContext(state_dir=context_dir)
                register(context)
                context.emit("on_session_start", session_id="session:one")

            context_path = context_dir / "bot_environment" / "sessions" / "session_one.json"
            self.assertTrue(context_path.exists())
            self.assertEqual(list(environment_dir.rglob("*.json")), [])

    def test_compression_continues_parent_affect_without_mutating_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary)
            register(context)
            parent_kwargs = {
                "profile_id": "bot:one",
                "session_id": "session:parent",
                "sender_id": "user:1",
            }
            context.emit("on_session_start", **parent_kwargs)
            context.emit(
                "pre_llm_call",
                **parent_kwargs,
                user_message="you are an idiot",
                turn_id="turn:parent",
            )
            parent_path = Path(temporary) / "bot_one" / "sessions" / "session_parent.json"
            parent_before = AffectState.from_dict(
                json.loads(parent_path.read_text(encoding="utf-8"))
            )

            compressed_kwargs = {
                "profile_id": "bot:one",
                "session_id": "session:compressed",
                "parent_session_id": "session:parent",
            }
            context.emit("on_session_start", **compressed_kwargs)
            compressed_path = (
                Path(temporary) / "bot_one" / "sessions" / "session_compressed.json"
            )
            continued = AffectState.from_dict(
                json.loads(compressed_path.read_text(encoding="utf-8"))
            )

            self.assertEqual(continued.parent_session_id, "session:parent")
            self.assertEqual(continued.session_id, "session:compressed")
            self.assertEqual(continued.frustration, parent_before.frustration)
            self.assertIn("user:1", continued.open_conflicts)

            context.emit(
                "pre_llm_call",
                **compressed_kwargs,
                user_message="sorry, no hard feelings",
                turn_id="turn:compressed",
            )
            parent_after = AffectState.from_dict(
                json.loads(parent_path.read_text(encoding="utf-8"))
            )
            self.assertEqual(parent_after.to_dict(), parent_before.to_dict())

    def test_shadow_mode_updates_state_without_injecting_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary, shadow_mode=True)
            register(context)
            kwargs = {
                "profile_id": "bot:one",
                "session_id": "session:one",
                "sender_id": "user:1",
                "user_message": "you are an idiot",
                "turn_id": "turn:one",
            }

            context.emit("on_session_start", **kwargs)
            first_result = context.emit("pre_llm_call", **kwargs)
            duplicate_result = context.emit("pre_llm_call", **kwargs)

            state_path = Path(temporary) / "bot_one" / "sessions" / "session_one.json"
            state = AffectState.from_dict(json.loads(state_path.read_text(encoding="utf-8")))
            self.assertIsNone(first_result)
            self.assertIsNone(duplicate_result)
            self.assertEqual(state.revision, 1)
            self.assertEqual(len(state.audit_records), 1)
            self.assertEqual(state.last_turn_id, "turn:one")

    def test_local_shadow_rollout_exposes_safe_status_and_audit_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(
                state_dir=temporary,
                shadow_mode=True,
                admin_user_ids=["user:admin"],
            )
            register(context)
            base = {
                "profile_id": "bot:test",
                "session_id": "session:shadow",
                "sender_id": "user:1",
            }

            context.emit("on_session_start", **base)
            result = context.emit(
                "pre_llm_call",
                **base,
                user_message="you are an idiot",
                turn_id="turn:one",
            )
            status = context.invoke_command(
                "affect",
                args_raw="status",
                **{**base, "sender_id": "user:admin"},
            )

            state_path = Path(temporary) / "bot_test" / "sessions" / "session_shadow.json"
            raw_state = state_path.read_text(encoding="utf-8")
            state = AffectState.from_dict(json.loads(raw_state))

            self.assertIsNone(result)
            self.assertIn("session=session:shadow", status)
            self.assertIn("revision=1", status)
            self.assertEqual(state.audit_records[-1]["event_type"], "insult")
            self.assertNotIn("you are an idiot", raw_state)
            self.assertNotIn("frustration", status)

    def test_expression_gain_controls_context_without_disabling_state_updates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            soul_path = Path(temporary) / "SOUL.md"
            soul_path.write_text(
                """session_affect:
  schema_version: 1
  tuning:
    expression_gain: 0
""",
                encoding="utf-8",
            )
            context = FakeHermesContext(state_dir=temporary, soul_path=soul_path)
            register(context)
            kwargs = {
                "profile_id": "bot:one",
                "session_id": "session:one",
                "sender_id": "user:1",
                "user_message": "good job",
                "turn_id": "turn:one",
            }

            context.emit("on_session_start", **kwargs)
            result = context.emit("pre_llm_call", **kwargs)

            state_path = Path(temporary) / "bot_one" / "sessions" / "session_one.json"
            state = AffectState.from_dict(json.loads(state_path.read_text(encoding="utf-8")))
            self.assertIsNone(result)
            self.assertEqual(state.revision, 1)
            self.assertEqual(len(state.audit_records), 1)

    def test_local_conservative_injection_covers_relationships_and_moderation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            soul_path = Path(temporary) / "SOUL.md"
            soul_path.write_text(
                """session_affect:
  schema_version: 1
  tuning:
    expression_gain: 1
""",
                encoding="utf-8",
            )
            context = FakeHermesContext(
                state_dir=temporary,
                soul_path=soul_path,
                admin_user_ids=["user:admin"],
            )
            register(context)
            base = {
                "profile_id": "bot:test",
                "session_id": "session:normal",
                "sender_id": "user:1",
            }

            context.emit("on_session_start", **base)
            injected = context.emit(
                "pre_llm_call",
                **base,
                user_message="you are an idiot",
                turn_id="turn:insult",
            )
            state_path = Path(temporary) / "bot_test" / "sessions" / "session_normal.json"
            before_calm = AffectState.from_dict(
                json.loads(state_path.read_text(encoding="utf-8"))
            )
            context.emit(
                "pre_llm_call",
                **base,
                user_message="calm down",
                verified_user=True,
                turn_id="turn:calm",
            )
            after_calm = AffectState.from_dict(
                json.loads(state_path.read_text(encoding="utf-8"))
            )

            self.assertIsNotNone(injected)
            self.assertIn("Internal affective guidance", injected["context"])
            self.assertIn("user:1", before_calm.relationships)
            self.assertLess(after_calm.frustration, before_calm.frustration)
            self.assertEqual(after_calm.audit_records[-1]["rule_name"], "verified_user_calm")

    def test_injected_guidance_omits_numeric_state_and_raw_message(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary)
            register(context)
            kwargs = {
                "profile_id": "bot:test",
                "session_id": "session:privacy",
                "sender_id": "user:1",
                "user_message": "private phrase that must not be echoed",
                "turn_id": "turn:one",
            }

            context.emit("on_session_start", **kwargs)
            result = context.emit("pre_llm_call", **kwargs)

            self.assertIsNotNone(result)
            guidance = result["context"]
            self.assertIn("Internal affective guidance", guidance)
            self.assertNotIn("private phrase that must not be echoed", guidance)
            self.assertNotIn("reactivity", guidance)
            self.assertNotIn("frustration", guidance)
            self.assertNotIn("relationships", guidance)

    def test_accepts_profile_name_and_positional_command_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary, admin_user_ids=["user:admin"])
            register(context)
            kwargs = {
                "profile_name": "bot:one",
                "session_id": "session:one",
                "sender_id": "user:1",
            }

            context.emit("on_session_start", **kwargs)
            result = context.invoke_command(
                "affect",
                "status",
                sender_id="user:admin",
                profile_name="bot:one",
                session_id="session:one",
            )

            self.assertIn("session=session:one", result)
            self.assertTrue(
                (Path(temporary) / "bot_one" / "sessions" / "session_one.json").exists()
            )

    def test_accepts_args_and_replacement_session_id_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary, admin_user_ids=["user:admin"])
            register(context)
            old_kwargs = {
                "profile_id": "bot:one",
                "session_id": "session:old",
            }
            context.emit("on_session_start", **old_kwargs)

            status = context.invoke_command(
                "affect",
                args="status",
                sender_id="user:admin",
                **old_kwargs,
            )
            context.emit(
                "on_session_reset",
                profile_id="bot:one",
                session_id="session:old",
                replacement_session_id="session:new",
            )

            old_path = Path(temporary) / "bot_one" / "sessions" / "session_old.json"
            new_path = Path(temporary) / "bot_one" / "sessions" / "session_new.json"
            self.assertIn("session=session:old", status)
            self.assertTrue(old_path.exists())
            self.assertTrue(new_path.exists())
            self.assertNotEqual(
                old_path.read_text(encoding="utf-8"),
                new_path.read_text(encoding="utf-8"),
            )

    def test_missing_session_identity_does_not_create_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(
                state_dir=temporary,
                admin_user_ids=["user:admin"],
            )
            register(context)
            payload = {
                "profile_id": "bot:one",
                "sender_id": "user:1",
                "user_message": "you are an idiot",
                "turn_id": "turn:one",
            }

            context.emit("on_session_start", **payload)
            result = context.emit("pre_llm_call", **payload)
            context.emit("post_llm_call", **payload)
            context.emit("on_session_reset", **payload)
            context.emit("on_session_finalize", **payload)
            context.emit("on_session_end", **payload)
            status = context.invoke_command(
                "affect",
                args_raw="status",
                profile_id="bot:one",
                sender_id="user:admin",
            )

            self.assertIsNone(result)
            self.assertEqual(status, "No active Hermes session was supplied.")
            self.assertEqual(list(Path(temporary).rglob("*.json")), [])

    def test_incomplete_session_start_does_not_collect_existing_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            initial_context = FakeHermesContext(state_dir=temporary)
            register(initial_context)
            initial_context.emit(
                "on_session_start",
                profile_id="bot:one",
                session_id="session:old",
            )
            state_path = Path(temporary) / "bot_one" / "sessions" / "session_old.json"
            stale_state = json.loads(state_path.read_text(encoding="utf-8"))
            stale_state["updated_at"] = "2000-01-01T00:00:00+00:00"
            state_path.write_text(json.dumps(stale_state), encoding="utf-8")

            incomplete_context = FakeHermesContext(
                state_dir=temporary,
                state_gc_days=1,
            )
            register(incomplete_context)
            incomplete_context.emit("on_session_start", profile_id="bot:one")

            self.assertTrue(state_path.exists())

    def test_lifecycle_hooks_accept_payload_without_optional_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary)
            register(context)
            kwargs = {"profile_id": "bot:one", "session_id": "session:one"}

            context.emit("on_session_start", **kwargs)
            context.emit("pre_llm_call", **kwargs)
            context.emit("post_llm_call", **kwargs)
            context.emit("on_session_reset", **kwargs)
            context.emit("on_session_finalize", **kwargs)
            context.emit("on_session_end", **kwargs)

            self.assertTrue(
                (Path(temporary) / "bot_one" / "sessions" / "session_one.json").exists()
            )

    def test_audit_records_are_bounded_and_transcript_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary)
            register(context)
            base = {
                "profile_id": "bot:one",
                "session_id": "session:one",
                "sender_id": "user:1",
            }
            context.emit("on_session_start", **base)
            for index in range(80):
                context.emit(
                    "pre_llm_call",
                    **base,
                    user_message="good job",
                    turn_id=f"turn:{index}",
                )

            state_path = Path(temporary) / "bot_one" / "sessions" / "session_one.json"
            state = AffectState.from_dict(json.loads(state_path.read_text(encoding="utf-8")))
            self.assertEqual(len(state.audit_records), 64)
            self.assertEqual(state.audit_records[-1]["event_type"], "praise")
            self.assertEqual(state.audit_records[-1]["rule_name"], "positive_social_signal")
            self.assertIn("global", state.audit_records[-1]["affected"])
            self.assertNotIn("good job", state_path.read_text(encoding="utf-8"))
            self.assertNotIn("user_message", state_path.read_text(encoding="utf-8"))

    def test_observed_style_and_influence_estimates_persist_without_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary)
            register(context)
            base = {
                "profile_id": "bot:one",
                "session_id": "session:one",
                "sender_id": "user:1",
            }
            context.emit("on_session_start", **base)
            context.emit(
                "pre_llm_call",
                **base,
                user_message="good job",
                turn_id="turn:one",
            )
            context.emit(
                "pre_llm_call",
                **base,
                user_message="you are an idiot",
                turn_id="turn:two",
            )

            state_path = Path(temporary) / "bot_one" / "sessions" / "session_one.json"
            raw_state = state_path.read_text(encoding="utf-8")
            state = AffectState.from_dict(json.loads(raw_state))
            relation = state.relationships["user:1"]
            observation = state.observed_participants["user:1"]

            self.assertNotEqual(relation.observed_style["supportive"], 0.5)
            self.assertGreater(relation.observed_style["confrontational"], 0.5)
            self.assertEqual(observation["observation_count"], 2)
            self.assertGreaterEqual(observation["influence_estimate"], 0.0)
            self.assertLessEqual(observation["influence_estimate"], 1.0)
            self.assertNotIn("good job", raw_state)
            self.assertNotIn("you are an idiot", raw_state)

    def test_command_requires_verified_admin_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary, admin_user_ids=["user:admin"])
            register(context)
            kwargs = {"profile_id": "bot:one", "session_id": "session:one"}
            context.emit("on_session_start", **kwargs)

            raw_only = context.invoke_command("affect", "status")
            denied = context.invoke_command("affect", args_raw="status", **kwargs)
            allowed = context.invoke_command(
                "affect", args_raw="status", sender_id="user:admin", **kwargs
            )
            bot_denied = context.invoke_command(
                "affect",
                args_raw="status",
                sender_id="user:admin",
                sender_kind="bot",
                **kwargs,
            )
            explicitly_unverified = context.invoke_command(
                "affect",
                args_raw="status",
                sender_id="user:admin",
                verified_user=False,
                **kwargs,
            )
            self.assertEqual(
                raw_only, "Affect administration requires a verified user identity."
            )
            self.assertEqual(denied, "Affect administration requires a verified user identity.")
            self.assertEqual(bot_denied, "Affect administration requires a verified user identity.")
            self.assertEqual(
                explicitly_unverified,
                "Affect administration requires a verified user identity.",
            )
            self.assertIn("session=session:one", allowed)

    def test_natural_moderation_changes_state_only_for_verified_user(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary)
            register(context)
            base = {
                "profile_id": "bot:one",
                "session_id": "session:one",
                "sender_id": "user:1",
            }
            context.emit("on_session_start", **base)
            context.emit(
                "pre_llm_call",
                **base,
                user_message="you are an idiot",
                turn_id="turn:one",
            )
            store_path = Path(temporary) / "bot_one" / "sessions" / "session_one.json"
            before = AffectState.from_dict(json.loads(store_path.read_text(encoding="utf-8")))

            context.emit(
                "pre_llm_call",
                **base,
                user_message="calm down",
                verified_user=False,
                turn_id="turn:two",
            )
            unverified = AffectState.from_dict(
                json.loads(store_path.read_text(encoding="utf-8"))
            )
            context.emit(
                "pre_llm_call",
                **base,
                user_message="calm down",
                verified_user=True,
                turn_id="turn:three",
            )
            verified = AffectState.from_dict(json.loads(store_path.read_text(encoding="utf-8")))

            self.assertAlmostEqual(unverified.frustration, before.frustration, places=5)
            self.assertLess(verified.frustration, unverified.frustration)
            self.assertEqual(verified.audit_records[-1]["rule_name"], "verified_user_calm")

    def test_bot_mediation_and_provocation_change_affect_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary)
            register(context)
            base = {
                "profile_id": "bot:one",
                "session_id": "session:one",
            }
            context.emit("on_session_start", **base)
            context.emit(
                "pre_llm_call",
                **base,
                sender_id="bot:hostile",
                sender_kind="bot",
                user_message="provoke them",
                turn_id="turn:one",
            )
            store_path = Path(temporary) / "bot_one" / "sessions" / "session_one.json"
            provoked = AffectState.from_dict(json.loads(store_path.read_text(encoding="utf-8")))
            context.emit(
                "pre_llm_call",
                **base,
                sender_id="bot:helper",
                sender_kind="bot",
                user_message="mediate this",
                turn_id="turn:two",
            )
            mediated = AffectState.from_dict(json.loads(store_path.read_text(encoding="utf-8")))

            self.assertIn("bot:hostile", provoked.open_conflicts)
            self.assertEqual(provoked.audit_records[-1]["event_type"], "bot_provocation")
            self.assertGreater(mediated.relationships["bot:helper"].respect, 0.0)
            self.assertEqual(mediated.audit_records[-1]["event_type"], "bot_mediation")

    def test_multiple_bot_profiles_keep_group_affect_state_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bot_one = FakeHermesContext(state_dir=temporary)
            bot_two = FakeHermesContext(state_dir=temporary)
            register(bot_one)
            register(bot_two)

            bot_one_base = {"profile_id": "bot:one", "session_id": "group:one"}
            bot_two_base = {"profile_id": "bot:two", "session_id": "group:one"}
            bot_one.emit("on_session_start", **bot_one_base)
            bot_two.emit("on_session_start", **bot_two_base)

            bot_one.emit(
                "pre_llm_call",
                **bot_one_base,
                sender_id="bot:two",
                sender_kind="bot",
                user_message="provoke them",
                turn_id="bot-one-turn",
            )
            bot_two.emit(
                "pre_llm_call",
                **bot_two_base,
                sender_id="bot:one",
                sender_kind="bot",
                user_message="mediate this",
                turn_id="bot-two-turn",
            )

            bot_one_path = Path(temporary) / "bot_one" / "sessions" / "group_one.json"
            bot_two_path = Path(temporary) / "bot_two" / "sessions" / "group_one.json"
            bot_one_state = AffectState.from_dict(
                json.loads(bot_one_path.read_text(encoding="utf-8"))
            )
            bot_two_state = AffectState.from_dict(
                json.loads(bot_two_path.read_text(encoding="utf-8"))
            )

            self.assertIn("bot:two", bot_one_state.open_conflicts)
            self.assertNotIn("bot:two", bot_two_state.open_conflicts)
            self.assertEqual(bot_one_state.audit_records[-1]["event_type"], "bot_provocation")
            self.assertEqual(bot_two_state.audit_records[-1]["event_type"], "bot_mediation")
            self.assertIn("bot:one", bot_two_state.relationships)
            self.assertNotIn("bot:one", bot_one_state.relationships)

    def test_reset_reinitializes_plugin_state_without_changing_session_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary, admin_user_ids=["user:admin"])
            register(context)
            kwargs = {
                "profile_id": "bot:one",
                "session_id": "session:one",
                "sender_id": "user:1",
                "user_message": "you are an idiot",
                "turn_id": "turn:one",
            }
            context.emit("on_session_start", **kwargs)
            context.emit("pre_llm_call", **kwargs)
            reset = context.invoke_command(
                "affect",
                args_raw="reset",
                sender_id="user:admin",
                profile_id="bot:one",
                session_id="session:one",
            )

            state = context.emit(
                "pre_llm_call",
                profile_id="bot:one",
                session_id="session:one",
            )
            self.assertEqual(reset, "Affective state reset for this session.")
            self.assertIn("Mood: neutral", state["context"])

            reset_state = AffectState.from_dict(
                json.loads(
                    (Path(temporary) / "bot_one" / "sessions" / "session_one.json")
                    .read_text(encoding="utf-8")
                )
            )
            self.assertEqual(reset_state.session_id, "session:one")
            self.assertEqual(reset_state.relationships, {})

    def test_reset_hook_with_replacement_session_starts_fresh_affect_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary)
            register(context)
            old_kwargs = {
                "profile_id": "bot:one",
                "session_id": "session:old",
                "sender_id": "user:1",
            }
            context.emit("on_session_start", **old_kwargs)
            context.emit(
                "pre_llm_call",
                **old_kwargs,
                user_message="you are an idiot",
                turn_id="turn:old",
            )
            old_path = Path(temporary) / "bot_one" / "sessions" / "session_old.json"
            old_before = AffectState.from_dict(
                json.loads(old_path.read_text(encoding="utf-8"))
            )

            context.emit(
                "on_session_reset",
                profile_id="bot:one",
                session_id="session:old",
                new_session_id="session:new",
            )
            new_path = Path(temporary) / "bot_one" / "sessions" / "session_new.json"
            new_state = AffectState.from_dict(
                json.loads(new_path.read_text(encoding="utf-8"))
            )
            old_after = AffectState.from_dict(
                json.loads(old_path.read_text(encoding="utf-8"))
            )

            self.assertEqual(new_state.session_id, "session:new")
            self.assertEqual(new_state.frustration, 0.0)
            self.assertEqual(new_state.relationships, {})
            self.assertEqual(old_after.to_dict(), old_before.to_dict())

    def test_calm_and_heat_commands_change_only_plugin_affect(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary, admin_user_ids=["user:admin"])
            register(context)
            base = {
                "profile_id": "bot:one",
                "session_id": "session:one",
                "sender_id": "user:1",
            }
            context.emit("on_session_start", **base)
            context.emit(
                "pre_llm_call",
                **base,
                user_message="you are an idiot",
                turn_id="turn:one",
            )
            store_path = Path(temporary) / "bot_one" / "sessions" / "session_one.json"
            before = AffectState.from_dict(json.loads(store_path.read_text(encoding="utf-8")))
            admin_base = {**base, "sender_id": "user:admin"}

            calm = context.invoke_command(
                "affect", args_raw="calm", **admin_base
            )
            after_calm = AffectState.from_dict(
                json.loads(store_path.read_text(encoding="utf-8"))
            )
            heat = context.invoke_command(
                "affect", args_raw="heat", **admin_base
            )
            after_heat = AffectState.from_dict(
                json.loads(store_path.read_text(encoding="utf-8"))
            )

            self.assertEqual(calm, "Affective state instructed to calm.")
            self.assertEqual(heat, "Affective state instructed to heat.")
            self.assertLess(after_calm.frustration, before.frustration)
            self.assertGreater(after_heat.frustration, after_calm.frustration)
            self.assertEqual(after_heat.session_id, "session:one")

    def test_tune_command_persists_bounded_session_override(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary, admin_user_ids=["user:admin"])
            register(context)
            kwargs = {
                "profile_id": "bot:one",
                "session_id": "session:one",
                "sender_id": "user:admin",
            }
            context.emit("on_session_start", **kwargs)

            invalid = context.invoke_command(
                "affect", args_raw="tune pride 2", **kwargs
            )
            tuned = context.invoke_command(
                "affect", args_raw="tune expression_gain 0", **kwargs
            )
            store_path = Path(temporary) / "bot_one" / "sessions" / "session_one.json"
            state = AffectState.from_dict(json.loads(store_path.read_text(encoding="utf-8")))

            self.assertIn("Only expression_gain", invalid)
            self.assertEqual(tuned, "Session tuning override set: expression_gain=0.")
            self.assertEqual(state.tuning_overrides, {"expression_gain": 0.0})

            restarted = FakeHermesContext(
                state_dir=temporary,
                admin_user_ids=["user:admin"],
            )
            register(restarted)
            restarted.emit("on_session_start", **kwargs)
            result = restarted.emit(
                "pre_llm_call",
                profile_id="bot:one",
                session_id="session:one",
                sender_id="user:1",
                user_message="good job",
                turn_id="turn:one",
            )
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
