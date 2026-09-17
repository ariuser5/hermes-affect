"""Stable public entry point for the Hermes plugin package.

The actual host wiring is kept in ``infrastructure.hermes.adapter`` and the
runtime is kept in ``application.session_runtime`` so this compatibility
module stays intentionally thin.
"""

from .application.session_runtime import SEMANTIC_CLASSIFIER_TASK, AffectRuntime
from .infrastructure.hermes.adapter import register

__all__ = ["AffectRuntime", "SEMANTIC_CLASSIFIER_TASK", "register"]
