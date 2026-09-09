from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

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
            context.emit("post_llm_call", **kwargs)
            context.emit("on_session_end", **kwargs)

            self.assertIn("context", injected)
            self.assertIn("Internal affective guidance", injected["context"])
            state_path = Path(temporary) / "bot_one" / "sessions" / "session_one.json"
            self.assertTrue(state_path.exists())
            state = AffectState.from_dict(json.loads(state_path.read_text(encoding="utf-8")))
            self.assertEqual(state.soul_sha256 and len(state.soul_sha256), 64)
            self.assertEqual(state.predisposition["traits"]["reactivity"], 0.8)
            self.assertEqual(state.last_turn_id, "turn:one")

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

    def test_command_requires_verified_admin_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeHermesContext(state_dir=temporary, admin_user_ids=["user:admin"])
            register(context)
            kwargs = {"profile_id": "bot:one", "session_id": "session:one"}
            context.emit("on_session_start", **kwargs)

            denied = context.invoke_command("affect", args_raw="status", **kwargs)
            allowed = context.invoke_command(
                "affect", args_raw="status", sender_id="user:admin", **kwargs
            )
            self.assertEqual(denied, "Affect administration requires a verified user identity.")
            self.assertIn("session=session:one", allowed)

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


if __name__ == "__main__":
    unittest.main()
