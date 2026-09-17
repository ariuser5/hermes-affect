"""SOUL.md boundary parsing for the structured affect configuration."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from ...domain.configuration import AffectConfig, neutral_config, validate_config

_SECTION_RE = re.compile(
    r"(?m)^[ \t]*session_affect:[ \t]*\r?\n"
    r"(?P<body>(?:^[ \t]+[^\r\n]*(?:\r?\n|$)|^[ \t]*\r?\n)*)"
)


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
    """Parse the small mapping/list subset used by the SOUL convention."""

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
