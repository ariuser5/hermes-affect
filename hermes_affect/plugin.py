"""Stable public entry point for the Hermes plugin package.

The actual host wiring is kept in ``integration.adapter`` and the runtime is
kept in ``runtime`` so this compatibility module stays intentionally thin.
"""

from .integration.adapter import register
from .runtime import SEMANTIC_CLASSIFIER_TASK, AffectRuntime

__all__ = ["AffectRuntime", "SEMANTIC_CLASSIFIER_TASK", "register"]
