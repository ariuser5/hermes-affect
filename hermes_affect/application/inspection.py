"""Safe, bounded current-state inspection shared by commands and dashboards."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from ..domain.calculations import effective_expression_drive
from ..domain.configuration import TUNING_FIELDS, AffectConfig, validate_config
from ..domain.state import AffectState

INSPECTION_COLLECTION_LIMIT = 64
INSPECTION_ID_LIMIT = 200
INSPECTION_LABEL_LIMIT = 200


def resolve_state_config(state: AffectState) -> tuple[AffectConfig | None, tuple[str, ...]]:
    """Resolve the effective saved configuration without consulting live SOUL state."""

    config, raw_warnings = validate_config(state.predisposition)
    warnings = list(raw_warnings)
    if state.model_version != 2 or config.schema_version != 2:
        warnings.append("Legacy affect session requires explicit migration/reset; preserved")
        return None, tuple(warnings)

    tuning = dict(config.tuning)
    tuning.update(
        {key: value for key, value in state.tuning_overrides.items() if key in TUNING_FIELDS}
    )
    return replace(config, tuning=tuning), tuple(warnings)


def _bounded_text(value: Any, limit: int = INSPECTION_LABEL_LIMIT) -> str:
    return str(value)[:limit]


def _bounded_relationships(state: AffectState) -> dict[str, dict[str, float]]:
    relationships: dict[str, dict[str, float]] = {}
    recent_relationships = list(state.relationships.items())[-INSPECTION_COLLECTION_LIMIT:]
    for participant_id, relation in recent_relationships:
        relationships[_bounded_text(participant_id, INSPECTION_ID_LIMIT)] = {
            "trust": relation.trust,
            "affinity": relation.affinity,
            "irritation": relation.irritation,
            "respect": relation.respect,
            "unresolved_tension": relation.unresolved_tension,
        }
    return relationships


def _bounded_conflicts(state: AffectState) -> dict[str, dict[str, Any]]:
    conflicts: dict[str, dict[str, Any]] = {}
    for participant_id, raw_record in list(state.open_conflicts.items())[
        -INSPECTION_COLLECTION_LIMIT:
    ]:
        if not isinstance(raw_record, Mapping):
            continue
        record: dict[str, Any] = {}
        heat = raw_record.get("heat")
        if (
            isinstance(heat, (int, float))
            and not isinstance(heat, bool)
            and math.isfinite(float(heat))
        ):
            record["heat"] = max(0.0, min(1.0, float(heat)))
        status = raw_record.get("status")
        if status is not None:
            record["status"] = _bounded_text(status, 40)
        conflicts[_bounded_text(participant_id, INSPECTION_ID_LIMIT)] = record
    return conflicts


def _tuning_configuration(
    state: AffectState, config: AffectConfig | None
) -> dict[str, Any]:
    if config is None:
        return {"available": False, "configured": {}, "effective": {}, "overrides": {}}

    configured, _warnings = validate_config(state.predisposition)
    return {
        "available": True,
        "configured": {
            name: configured.tuning[name]
            for name in TUNING_FIELDS
            if name in configured.tuning
        },
        "effective": {
            name: config.tuning[name] for name in TUNING_FIELDS if name in config.tuning
        },
        "overrides": {
            name: state.tuning_overrides[name]
            for name in TUNING_FIELDS
            if name in state.tuning_overrides
        },
    }


def state_snapshot(state: AffectState, config: AffectConfig | None) -> dict[str, Any]:
    """Return the public current-state projection, excluding histories and internals."""

    return {
        "profile_id": _bounded_text(state.profile_id, INSPECTION_ID_LIMIT),
        "session_id": _bounded_text(state.session_id, INSPECTION_ID_LIMIT),
        "revision": state.revision,
        "updated_at": _bounded_text(state.updated_at, 80),
        "mood": _bounded_text(state.mood, 80),
        "response_posture": _bounded_text(state.response_posture, 80),
        "model_version": state.model_version,
        "migration_required": config is None,
        "expression_drive": effective_expression_drive(state, config) if config else None,
        "perceived_atmosphere_tension": state.atmosphere_tension,
        "affect": {
            "valence": state.valence,
            "arousal": state.arousal,
            "frustration": state.frustration,
            "offended": state.offended,
        },
        "relationships": _bounded_relationships(state),
        "active_sensitivities": [
            _bounded_text(topic)
            for topic in state.active_sensitivities[-INSPECTION_COLLECTION_LIMIT:]
        ],
        "open_conflicts": _bounded_conflicts(state),
        "tuning_overrides": {
            name: value for name, value in state.tuning_overrides.items() if name in TUNING_FIELDS
        },
        "tuning_configuration": _tuning_configuration(state, config),
    }
