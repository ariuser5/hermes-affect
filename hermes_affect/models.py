"""Serializable affective state models."""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .config import TUNING_FIELDS

STATE_SCHEMA_VERSION = 1
AUDIT_RECORD_LIMIT = 64


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp(value: float, minimum: float = -1.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))


@dataclass
class ParticipantRelation:
    trust: float = 0.0
    affinity: float = 0.0
    irritation: float = 0.0
    respect: float = 0.0
    unresolved_tension: float = 0.0
    observed_style: dict[str, float] = field(default_factory=dict)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trust": self.trust,
            "affinity": self.affinity,
            "irritation": self.irritation,
            "respect": self.respect,
            "unresolved_tension": self.unresolved_tension,
            "observed_style": dict(self.observed_style),
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> ParticipantRelation:
        return cls(
            trust=float(raw.get("trust", 0.0)),
            affinity=float(raw.get("affinity", 0.0)),
            irritation=float(raw.get("irritation", 0.0)),
            respect=float(raw.get("respect", 0.0)),
            unresolved_tension=float(raw.get("unresolved_tension", 0.0)),
            observed_style=dict(raw.get("observed_style", {})),
            updated_at=str(raw.get("updated_at", utc_now())),
        )


@dataclass
class AffectState:
    profile_id: str
    session_id: str
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    revision: int = 0
    last_turn_id: str | None = None
    valence: float = 0.0
    arousal: float = 0.0
    frustration: float = 0.0
    offended: float = 0.0
    mood: str = "neutral"
    relationships: dict[str, ParticipantRelation] = field(default_factory=dict)
    active_sensitivities: list[str] = field(default_factory=list)
    open_conflicts: dict[str, dict[str, Any]] = field(default_factory=dict)
    observed_participants: dict[str, dict[str, Any]] = field(default_factory=dict)
    audit_records: list[dict[str, Any]] = field(default_factory=list)
    response_posture: str = "normal_engagement"
    soul_sha256: str | None = None
    predisposition: dict[str, Any] = field(default_factory=dict)
    tuning_overrides: dict[str, float] = field(default_factory=dict)
    parent_session_id: str | None = None

    @classmethod
    def initial(
        cls,
        profile_id: str,
        session_id: str,
        *,
        soul_sha256: str | None = None,
        predisposition: Mapping[str, Any] | None = None,
    ) -> AffectState:
        return cls(
            profile_id=profile_id,
            session_id=session_id,
            soul_sha256=soul_sha256,
            predisposition=dict(predisposition or {}),
        )

    @classmethod
    def continued_from(cls, parent: AffectState, session_id: str) -> AffectState:
        """Start a compressed session from a bounded parent-state snapshot."""

        state = copy.deepcopy(parent)
        state.session_id = session_id
        state.created_at = utc_now()
        state.updated_at = utc_now()
        state.parent_session_id = parent.session_id
        return state

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "profile_id": self.profile_id,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "revision": self.revision,
            "last_turn_id": self.last_turn_id,
            "valence": self.valence,
            "arousal": self.arousal,
            "frustration": self.frustration,
            "offended": self.offended,
            "mood": self.mood,
            "relationships": {key: value.to_dict() for key, value in self.relationships.items()},
            "active_sensitivities": list(self.active_sensitivities),
            "open_conflicts": self.open_conflicts,
            "observed_participants": self.observed_participants,
            "audit_records": [dict(item) for item in self.audit_records[-AUDIT_RECORD_LIMIT:]],
            "response_posture": self.response_posture,
            "soul_sha256": self.soul_sha256,
            "predisposition": self.predisposition,
            "tuning_overrides": dict(self.tuning_overrides),
            "parent_session_id": self.parent_session_id,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> AffectState:
        schema_version = raw.get("schema_version", STATE_SCHEMA_VERSION)
        if isinstance(schema_version, bool) or schema_version != STATE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported affect state schema version: {schema_version}")
        audit_raw = raw.get("audit_records", [])
        audit_records = (
            [dict(item) for item in audit_raw if isinstance(item, Mapping)][-AUDIT_RECORD_LIMIT:]
            if isinstance(audit_raw, list)
            else []
        )
        raw_overrides = raw.get("tuning_overrides", {})
        tuning_overrides = {}
        if isinstance(raw_overrides, Mapping):
            for name in TUNING_FIELDS:
                value = raw_overrides.get(name)
                if (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(float(value))
                    and 0.0 <= float(value) <= 10.0
                ):
                    tuning_overrides[name] = float(value)
        return cls(
            profile_id=str(raw["profile_id"]),
            session_id=str(raw["session_id"]),
            created_at=str(raw.get("created_at", utc_now())),
            updated_at=str(raw.get("updated_at", utc_now())),
            revision=int(raw.get("revision", 0)),
            last_turn_id=raw.get("last_turn_id"),
            valence=clamp(float(raw.get("valence", 0.0))),
            arousal=clamp(float(raw.get("arousal", 0.0)), 0.0, 1.0),
            frustration=clamp(float(raw.get("frustration", 0.0)), 0.0, 1.0),
            offended=clamp(float(raw.get("offended", 0.0)), 0.0, 1.0),
            mood=str(raw.get("mood", "neutral")),
            relationships={
                key: ParticipantRelation.from_dict(value)
                for key, value in dict(raw.get("relationships", {})).items()
            },
            active_sensitivities=list(raw.get("active_sensitivities", [])),
            open_conflicts=dict(raw.get("open_conflicts", {})),
            observed_participants=dict(raw.get("observed_participants", {})),
            audit_records=audit_records,
            response_posture=str(raw.get("response_posture", "normal_engagement")),
            soul_sha256=raw.get("soul_sha256"),
            predisposition=dict(raw.get("predisposition", {})),
            tuning_overrides=tuning_overrides,
            parent_session_id=raw.get("parent_session_id"),
        )

    def add_audit_record(self, record: Mapping[str, Any]) -> None:
        """Append one bounded, non-transcript audit record."""

        self.audit_records.append(dict(record))
        del self.audit_records[:-AUDIT_RECORD_LIMIT]
