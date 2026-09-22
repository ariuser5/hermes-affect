"""Session-scoped tuning validation and mutation."""

from __future__ import annotations

import math

from ..domain.configuration import TUNING_FIELDS
from ..domain.state import AffectState, utc_now


class SessionTuningService:
    """Apply the small set of supported per-session tuning overrides."""

    @staticmethod
    def validate_name(name: str) -> None:
        if name not in TUNING_FIELDS:
            raise ValueError("Only expression_gain may be tuned in model v2.")

    @staticmethod
    def validate_value(name: str, value: object) -> float:
        SessionTuningService.validate_name(name)
        if isinstance(value, bool):
            raise ValueError("Tune value must be a finite number between 0 and 10.")
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError("Tune value must be a finite number between 0 and 10.") from error
        if not math.isfinite(number) or not 0.0 <= number <= 10.0:
            raise ValueError("Tune value must be a finite number between 0 and 10.")
        return number

    @classmethod
    def set_override(cls, state: AffectState, name: str, value: object) -> float:
        number = cls.validate_value(name, value)
        state.tuning_overrides[name] = number
        state.updated_at = utc_now()
        state.revision += 1
        return number

    @classmethod
    def restore_configured(cls, state: AffectState, name: str) -> bool:
        cls.validate_name(name)
        if name not in state.tuning_overrides:
            return False
        del state.tuning_overrides[name]
        state.updated_at = utc_now()
        state.revision += 1
        return True
