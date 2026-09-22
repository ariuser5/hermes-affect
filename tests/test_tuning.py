from __future__ import annotations

import unittest

from hermes_affect.application.tuning import SessionTuningService
from hermes_affect.domain.state import AffectState


class SessionTuningServiceTests(unittest.TestCase):
    def test_set_override_validates_and_mutates_one_session(self) -> None:
        state = AffectState.initial("bot:one", "session:one")
        service = SessionTuningService()

        value = service.set_override(state, "expression_gain", "2.5")

        self.assertEqual(value, 2.5)
        self.assertEqual(state.tuning_overrides, {"expression_gain": 2.5})
        self.assertEqual(state.revision, 1)

    def test_set_override_rejects_unsupported_or_out_of_range_values(self) -> None:
        state = AffectState.initial("bot:one", "session:one")
        service = SessionTuningService()

        with self.assertRaisesRegex(ValueError, "Only expression_gain"):
            service.set_override(state, "pride", 2)
        for value in (-0.1, 10.1, "nan", "inf", "not-a-number"):
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "finite number between 0 and 10"
            ):
                service.set_override(state, "expression_gain", value)
        self.assertEqual(state.tuning_overrides, {})
        self.assertEqual(state.revision, 0)

    def test_restore_removes_override_without_extra_revision_when_clear(self) -> None:
        state = AffectState.initial("bot:one", "session:one")
        service = SessionTuningService()
        service.set_override(state, "expression_gain", 4.0)

        self.assertTrue(service.restore_configured(state, "expression_gain"))
        self.assertFalse(service.restore_configured(state, "expression_gain"))
        self.assertEqual(state.tuning_overrides, {})
        self.assertEqual(state.revision, 2)

    def test_new_session_is_clear_and_compression_continuation_preserves_override(self) -> None:
        service = SessionTuningService()
        state = AffectState.initial("bot:one", "session:one")
        service.set_override(state, "expression_gain", 3.0)

        new_state = AffectState.initial("bot:one", "session:new")
        continuation = AffectState.continued_from(state, "session:continued")

        self.assertEqual(new_state.tuning_overrides, {})
        self.assertEqual(continuation.tuning_overrides, {"expression_gain": 3.0})


if __name__ == "__main__":
    unittest.main()
