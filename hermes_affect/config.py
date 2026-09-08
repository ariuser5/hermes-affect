"""Validated SOUL.md configuration and neutral defaults."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

CORE_TRAIT_FIELDS = (
    "reactivity",
    "persistence",
    "pride",
    "playfulness",
    "assertiveness",
    "social_influence",
    "receptiveness",
)
TUNING_FIELDS = ("expression_gain", "escalation_gain", "repair_gain")

_TOP_LEVEL_FIELDS = {"schema_version", "traits", "tuning", "sensitivities"}
_SECTION_RE = re.compile(
    r"(?ms)^\s*session_affect:\s*\n(?P<body>(?:^[ \t]+.*(?:\n|$))*)"
)


@dataclass(frozen=True)
class Sensitivity:
    topic: str
    intensity: float


@dataclass(frozen=True)
class AffectConfig:
    schema_version: int = 1
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
        schema_version = raw.get("schema_version", 1)
        if isinstance(schema_version, bool) or schema_version != 1:
            raise ValueError("unsupported schema_version")

        traits_raw = raw.get("traits", {})
        tuning_raw = raw.get("tuning", {})
        if not isinstance(traits_raw, Mapping) or not isinstance(tuning_raw, Mapping):
            raise ValueError("traits and tuning must be mappings")

        _warn_unknown_fields(
            traits_raw,
            location="session_affect.traits",
            allowed=set(CORE_TRAIT_FIELDS),
            warnings=warnings,
        )
        _warn_unknown_fields(
            tuning_raw,
            location="session_affect.tuning",
            allowed=set(TUNING_FIELDS),
            warnings=warnings,
        )

        traits = dict(defaults.traits)
        for name in CORE_TRAIT_FIELDS:
            if name in traits_raw:
                traits[name] = _number(
                    traits_raw[name], field_name=f"traits.{name}", minimum=0.0, maximum=1.0
                )

        tuning = dict(defaults.tuning)
        for name in TUNING_FIELDS:
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
        return AffectConfig(1, traits, tuning, tuple(sensitivities)), warnings
    except (TypeError, ValueError) as exc:
        warnings.append(f"Invalid session_affect configuration: {exc}; using neutral defaults")
        return defaults, warnings


def _minimal_yaml_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return None
    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        return value[1:-1]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.lower() in {"null", "~"}:
        return None
    try:
        return float(value) if any(char in value for char in ".eE") else int(value)
    except ValueError:
        return value


def _minimal_yaml_load(document: str) -> Any:
    """Parse the small mapping/list subset used by the SOUL convention.

    This keeps the plugin usable without adding a runtime dependency on a YAML
    package. Full YAML remains supported when PyYAML is installed.
    """

    lines: list[tuple[int, str]] = []
    for raw_line in document.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        lines.append((indent, raw_line.strip()))

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(lines) or lines[index][0] < indent:
            return {}, index
        is_list = lines[index][1].startswith("- ")
        result: Any = [] if is_list else {}
        while index < len(lines) and lines[index][0] == indent:
            _, content = lines[index]
            if is_list:
                if not content.startswith("- "):
                    raise ValueError("mixed YAML list and mapping")
                item_text = content[2:].strip()
                if ":" in item_text:
                    key, value = item_text.split(":", 1)
                    item: dict[str, Any] = {key.strip(): _minimal_yaml_scalar(value)}
                    index += 1
                    if index < len(lines) and lines[index][0] > indent:
                        child, index = parse_block(index, lines[index][0])
                        if not isinstance(child, Mapping):
                            raise ValueError("list item continuation must be a mapping")
                        item.update(child)
                    result.append(item)
                    continue
                result.append(_minimal_yaml_scalar(item_text))
                index += 1
                continue

            if content.startswith("- ") or ":" not in content:
                raise ValueError("invalid YAML mapping entry")
            key, value = content.split(":", 1)
            key = key.strip()
            value = value.strip()
            index += 1
            if value:
                result[key] = _minimal_yaml_scalar(value)
            elif index < len(lines) and lines[index][0] > indent:
                result[key], index = parse_block(index, lines[index][0])
            else:
                result[key] = {}
        return result, index

    parsed, position = parse_block(0, lines[0][0] if lines else 0)
    if position != len(lines):
        raise ValueError("unsupported YAML indentation")
    return parsed


def parse_soul_affect(soul_text: str) -> tuple[AffectConfig, list[str]]:
    """Read the delimited YAML section from SOUL.md without interpreting prose."""

    match = _SECTION_RE.search(soul_text)
    if not match:
        return neutral_config(), []

    try:
        try:
            import yaml
        except ImportError:
            decoded = _minimal_yaml_load("session_affect:\n" + match.group("body"))
        else:
            try:
                decoded = yaml.safe_load("session_affect:\n" + match.group("body"))
            except yaml.YAMLError as exc:
                warning = f"Invalid session_affect YAML: {exc}; using neutral defaults"
                return neutral_config(), [warning]
        return validate_config(decoded.get("session_affect"))
    except (AttributeError, TypeError, ValueError) as exc:
        return neutral_config(), [f"Invalid session_affect YAML: {exc}; using neutral defaults"]
