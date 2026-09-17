"""Validated affect configuration and neutral defaults."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

CORE_TRAIT_FIELDS = (
    "reactivity",
    "persistence",
    "pride",
    "playfulness",
    "assertiveness",
    "receptiveness",
)
TUNING_FIELDS = ("expression_gain",)
LEGACY_TRAIT_FIELDS = (*CORE_TRAIT_FIELDS, "social_influence")
LEGACY_TUNING_FIELDS = (*TUNING_FIELDS, "escalation_gain", "repair_gain")
CONFIG_SCHEMA_VERSION = 2

_TOP_LEVEL_FIELDS = {"schema_version", "traits", "tuning", "sensitivities"}


@dataclass(frozen=True)
class Sensitivity:
    topic: str
    intensity: float


@dataclass(frozen=True)
class AffectConfig:
    schema_version: int = CONFIG_SCHEMA_VERSION
    traits: Mapping[str, float] = field(default_factory=dict)
    tuning: Mapping[str, float] = field(default_factory=dict)
    sensitivities: tuple[Sensitivity, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "traits": dict(self.traits),
            "tuning": dict(self.tuning),
            "sensitivities": [asdict(item) for item in self.sensitivities],
        }


def neutral_config() -> AffectConfig:
    """Return documented neutral predispositions for a missing SOUL section."""

    return AffectConfig(
        traits={name: 0.5 for name in CORE_TRAIT_FIELDS},
        tuning={name: 1.0 for name in TUNING_FIELDS},
    )


def _number(value: Any, *, field_name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}")
    return number


def _warn_unknown_fields(
    values: Mapping[str, Any],
    *,
    location: str,
    allowed: set[str],
    warnings: list[str],
) -> None:
    for name in values:
        if name in allowed:
            continue
        warnings.append(f"Unknown field {location}.{name} is ignored.")


def validate_config(raw: Any) -> tuple[AffectConfig, list[str]]:
    """Validate a decoded ``session_affect`` mapping.

    Unknown fields are never reinterpreted. Recognized fields are still used,
    while malformed recognized values cause a complete neutral fallback so a
    bad SOUL.md cannot interrupt a session.
    """

    defaults = neutral_config()
    warnings: list[str] = []
    try:
        if not isinstance(raw, Mapping):
            raise ValueError("session_affect must be a mapping")

        _warn_unknown_fields(
            raw,
            location="session_affect",
            allowed=_TOP_LEVEL_FIELDS,
            warnings=warnings,
        )
        schema_version = raw.get("schema_version", CONFIG_SCHEMA_VERSION)
        if isinstance(schema_version, bool) or schema_version not in (1, 2):
            raise ValueError("unsupported schema_version")
        trait_fields = LEGACY_TRAIT_FIELDS if schema_version == 1 else CORE_TRAIT_FIELDS
        tuning_fields = LEGACY_TUNING_FIELDS if schema_version == 1 else TUNING_FIELDS

        traits_raw = raw.get("traits", {})
        tuning_raw = raw.get("tuning", {})
        if not isinstance(traits_raw, Mapping) or not isinstance(tuning_raw, Mapping):
            raise ValueError("traits and tuning must be mappings")

        _warn_unknown_fields(
            traits_raw,
            location="session_affect.traits",
            allowed=set(trait_fields),
            warnings=warnings,
        )
        _warn_unknown_fields(
            tuning_raw,
            location="session_affect.tuning",
            allowed=set(tuning_fields),
            warnings=warnings,
        )

        traits = {name: 0.5 for name in trait_fields}
        for name in trait_fields:
            if name in traits_raw:
                traits[name] = _number(
                    traits_raw[name], field_name=f"traits.{name}", minimum=0.0, maximum=1.0
                )

        tuning = {name: 1.0 for name in tuning_fields}
        for name in tuning_fields:
            if name in tuning_raw:
                tuning[name] = _number(
                    tuning_raw[name], field_name=f"tuning.{name}", minimum=0.0, maximum=10.0
                )

        sensitivities_raw = raw.get("sensitivities", [])
        if not isinstance(sensitivities_raw, list):
            raise ValueError("sensitivities must be a list")
        sensitivities: list[Sensitivity] = []
        for index, item in enumerate(sensitivities_raw):
            if not isinstance(item, Mapping) or not isinstance(item.get("topic"), str):
                raise ValueError(f"sensitivities[{index}] must contain a topic")
            topic = item["topic"].strip()
            if not topic:
                raise ValueError(f"sensitivities[{index}].topic must not be empty")
            _warn_unknown_fields(
                item,
                location=f"session_affect.sensitivities[{index}]",
                allowed={"topic", "intensity"},
                warnings=warnings,
            )
            sensitivities.append(
                Sensitivity(
                    topic=topic,
                    intensity=_number(
                        item.get("intensity", 0.5),
                        field_name=f"sensitivities[{index}].intensity",
                        minimum=0.0,
                        maximum=1.0,
                    ),
                )
            )
        if schema_version == 1:
            warnings.append("Legacy session_affect model: migration to schema_version 2 required.")
        return AffectConfig(schema_version, traits, tuning, tuple(sensitivities)), warnings
    except (TypeError, ValueError) as exc:
        warnings.append(f"Invalid session_affect configuration: {exc}; using neutral defaults")
        return defaults, warnings
