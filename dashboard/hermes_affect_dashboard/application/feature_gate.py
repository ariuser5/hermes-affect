"""Strict, default-off feature gating for affect state web inspection."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping

logger = logging.getLogger("hermes-affect.dashboard")

DASHBOARD_FEATURE_ENV = "HERMES_AFFECT_DASHBOARD"
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
FALSE_VALUES = frozenset({"", "0", "false", "no", "off"})


def parse_feature_flag(value: str | None) -> tuple[bool, str | None]:
    """Return ``(enabled, warning)``; missing and invalid values fail closed."""

    if value is None:
        return False, None
    normalized = value.strip().casefold()
    if normalized in TRUE_VALUES:
        return True, None
    if normalized in FALSE_VALUES:
        return False, None
    return False, f"Invalid {DASHBOARD_FEATURE_ENV} value; affect dashboard remains disabled"


def dashboard_feature_enabled(environ: Mapping[str, str] | None = None) -> bool:
    values = os.environ if environ is None else environ
    enabled, warning = parse_feature_flag(values.get(DASHBOARD_FEATURE_ENV))
    if warning:
        logger.warning("%s", warning)
    return enabled

