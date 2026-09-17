"""Hermes registration and hook wiring.

Keep this module deliberately small.  It translates the public Hermes plugin
contract into callbacks on :class:`hermes_affect.application.session_runtime.AffectRuntime`; the
affect behavior itself belongs in the runtime and domain modules.
"""

from __future__ import annotations

import logging
from typing import Any

from ...application.session_runtime import SEMANTIC_CLASSIFIER_TASK, AffectRuntime

logger = logging.getLogger("hermes-affect")


def _register_semantic_classifier_task(ctx: Any) -> bool:
    register_task = getattr(ctx, "register_auxiliary_task", None)
    if not callable(register_task):
        logger.warning(
            "semantic_classification status=unavailable reason=auxiliary_task_registration_missing"
        )
        return False
    register_task(
        SEMANTIC_CLASSIFIER_TASK,
        display_name="Hermes Affect semantic classifier",
        description="Bounded semantic event classification for hermes-affect.",
    )
    return True


def register(ctx: Any) -> None:
    """Register the general Hermes plugin surface."""

    runtime = AffectRuntime(ctx)
    runtime.semantic_classifier.task_registration_available = (
        _register_semantic_classifier_task(ctx) if runtime.semantic_config.enabled else True
    )
    ctx.register_hook("on_session_start", runtime.on_session_start)
    ctx.register_hook("pre_llm_call", runtime.pre_llm_call)
    ctx.register_hook("post_llm_call", runtime.post_llm_call)
    ctx.register_hook("on_session_end", runtime.on_session_end)
    ctx.register_hook("on_session_reset", runtime.on_session_reset)
    ctx.register_hook("on_session_finalize", runtime.on_session_finalize)
    ctx.register_command(
        "affect",
        runtime.command,
        "Inspect or control session-scoped affective state",
    )
