"""Hermes plugin entry point for the ``hermes-affect`` source checkout."""

import sys
from pathlib import Path


# Hermes loads a user plugin's root ``__init__.py`` directly from its checkout.
# Make the checkout importable before resolving the package implementation.
_PLUGIN_ROOT = str(Path(__file__).resolve().parent)
if _PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT)

from hermes_affect.plugin import register  # noqa: E402

__all__ = ["register"]
