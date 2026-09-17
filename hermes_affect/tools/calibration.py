"""Offline runtime scenarios and read-only v1 migration proposals.

Run python -m hermes_affect.tools.calibration --help. No Hermes/provider calls are made.
Each run uses isolated temporary storage and the same pipeline as the plugin.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..application.response.rendering import expression_tier
from ..application.session_runtime import AffectRuntime
from ..domain.calculations import effective_expression_drive, temperament_drives
from ..domain.configuration import (
    CORE_TRAIT_FIELDS,
    AffectConfig,
    neutral_config,
    validate_config,
)
from ..domain.state import AffectState
from ..infrastructure.configuration.soul_loader import parse_soul_affect

PRESETS = {
    "neutral": {},
    "mischievous": {"playfulness": 0.95, "assertiveness": 0.9, "receptiveness": 0.1},
    "sensitive": {"reactivity": 0.9, "pride": 0.9, "playfulness": 0.1, "assertiveness": 0.25},
    "mediator": {"reactivity": 0.35, "assertiveness": 0.85, "receptiveness": 0.95},
    "resilient": {"reactivity": 0.15, "pride": 0.15, "assertiveness": 0.8, "playfulness": 0.8},
}


def preset_config(name: str) -> AffectConfig:
    config = neutral_config()
    return replace(config, traits={**config.traits, **PRESETS[name]})


def scenario_turns(name: str) -> list[dict[str, Any]]:
    if name == "group":
        return [
            {"user_message": "C, nice try", "sender_id": "bot:B", "target_id": "bot:C"},
            {"user_message": "B, stop teasing me", "sender_id": "bot:C", "target_id": "bot:B"},
        ] * 4 + [
            {
                "user_message": "calm down",
                "sender_id": "user:admin",
                "verified_user": True,
                "sender_kind": "user",
            },
        ]
    messages = {
        "banter": ["nice try"] * 8 + ["sorry"],
        "repair": ["you are useless"] * 5 + ["sorry"] * 5 + ["calm down"],
        "praise": ["good job"] * 12,
        "disagreement": ["i disagree"] * 8,
        "cooling": ["you are useless"] * 5 + ["hello"],
    }[name]
    turns = [
        {"user_message": text, "sender_id": "bot:B", "target_id": "bot:A", "sender_kind": "bot"}
        for text in messages
    ]
    if name == "repair":
        turns[-1].update(sender_id="user:admin", sender_kind="user", verified_user=True)
    if name == "cooling":
        turns[-1]["elapsed_hours"] = 6.0
    return turns


class _Context:
    def __init__(self, root: str) -> None:
        self.config = {"state_dir": root, "soul_path": str(Path(root) / "absent-SOUL.md")}

    def get_config(self, name: str, default: Any = None) -> Any:
        return self.config.get(name, default)


def run_scenario(
    config: AffectConfig,
    scenario: str = "banter",
    *,
    turns: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if config.schema_version != 2:
        raise ValueError("Migrate the SOUL configuration to v2 before calibration")
    rows = []
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory(prefix="hermes-affect-calibration-") as root:
        runtime = AffectRuntime(_Context(root), now=lambda: now)
        state = AffectState.initial("bot:A", "calibration", predisposition=config.to_dict())
        state.created_at = state.updated_at = now.isoformat()
        runtime.store.save(state)
        for index, turn in enumerate(turns if turns is not None else scenario_turns(scenario)):
            values = dict(turn)
            hours = float(values.pop("elapsed_hours", 0.0))
            if not 0 <= hours <= 24 * 365:
                raise ValueError("elapsed_hours must be finite and between 0 and 8760")
            now += timedelta(hours=hours)
            kwargs = {
                "profile_id": "bot:A",
                "session_id": "calibration",
                "turn_id": str(index),
                "known_participants": ["bot:A", "bot:B", "bot:C"],
                "is_group": True,
                "sender_kind": "bot",
            }
            allowed = {"user_message", "sender_id", "sender_kind", "target_id", "verified_user"}
            if set(values) - allowed:
                raise ValueError("Unknown scenario turn fields")
            kwargs.update(values)
            guidance = runtime.pre_llm_call(**kwargs)
            state = runtime.store.load("bot:A", "calibration")
            assert state is not None
            drive = effective_expression_drive(state, config)
            rows.append(
                {
                    "turn": index + 1,
                    "posture": state.response_posture,
                    "expression_tier": expression_tier(drive),
                    "expression_drive": round(drive, 4),
                    "valence": round(state.valence, 4),
                    "frustration": round(state.frustration, 4),
                    "offended": round(state.offended, 4),
                    "perceived_tension": round(state.atmosphere_tension, 4),
                    "guidance": guidance["context"] if guidance else None,
                }
            )
        return {
            "scenario": scenario,
            "configuration": config.to_dict(),
            "derived_drives": temperament_drives(config),
            "turns": rows,
            "social_edges": state.social_edges,
            "observed_distress": state.observed_participants,
            "scope": "Plugin guidance only; not generated LLM replies or measured realism.",
        }


def migration_proposal(soul_text: str) -> dict[str, Any]:
    legacy, warnings = parse_soul_affect(soul_text)
    if any("Invalid" in warning for warning in warnings):
        raise ValueError("Fix invalid SOUL configuration before migration")
    if legacy.schema_version != 1:
        raise ValueError("Migration input must explicitly declare schema_version: 1")
    proposed = AffectConfig(
        traits={name: legacy.traits[name] for name in CORE_TRAIT_FIELDS},
        tuning={"expression_gain": legacy.tuning["expression_gain"]},
        sensitivities=legacy.sensitivities,
    )
    return {
        "proposed_session_affect": proposed.to_dict(),
        "removed": {
            "social_influence": legacy.traits["social_influence"],
            "escalation_gain": legacy.tuning["escalation_gain"],
            "repair_gain": legacy.tuning["repair_gain"],
        },
        "warnings": warnings
        + [
            "Behavior is not numerically equivalent. Compare offline scenarios before applying.",
            "No SOUL or state files were changed. Existing legacy sessions remain preserved.",
            "After applying reviewed v2 SOUL, start a new session or explicitly /affect reset.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--soul", type=Path, help="Read a v2 SOUL file instead of a preset")
    parser.add_argument("--preset", choices=PRESETS, default="neutral")
    parser.add_argument(
        "--scenario",
        choices=("banter", "group", "repair", "praise", "disagreement", "cooling"),
        default="banter",
    )
    parser.add_argument("--scenario-file", type=Path, help="Read a JSON list of synthetic turns")
    parser.add_argument("--trait", action="append", default=[], metavar="NAME=VALUE")
    parser.add_argument("--expression", type=float)
    parser.add_argument("--sweep", choices=CORE_TRAIT_FIELDS)
    parser.add_argument("--compare", action="store_true", help="Compare all temperament presets")
    parser.add_argument("--json", action="store_true", help="Include full guidance in JSON")
    parser.add_argument("--migrate-soul", type=Path, help="Print a read-only v1 migration proposal")
    args = parser.parse_args()
    try:
        if args.migrate_soul:
            print(
                json.dumps(
                    migration_proposal(args.migrate_soul.read_text(encoding="utf-8")),
                    ensure_ascii=True,
                    indent=2,
                )
            )
            return
        config = preset_config(args.preset)
        if args.soul:
            config, warnings = parse_soul_affect(args.soul.read_text(encoding="utf-8"))
            if warnings:
                raise ValueError("; ".join(warnings))
        raw = config.to_dict()
        for assignment in args.trait:
            name, value = assignment.split("=", 1)
            if name not in CORE_TRAIT_FIELDS:
                raise ValueError(f"Unknown trait: {name}")
            raw["traits"][name] = float(value)
        if args.expression is not None:
            raw["tuning"]["expression_gain"] = args.expression
        config, warnings = validate_config(raw)
        if warnings:
            raise ValueError("; ".join(warnings))
        turns = (
            json.loads(args.scenario_file.read_text(encoding="utf-8"))
            if args.scenario_file
            else None
        )
        if turns is not None and (
            not isinstance(turns, list) or not all(isinstance(t, dict) for t in turns)
        ):
            raise ValueError("Scenario file must be a list of turn objects")
        variants = {"configured": config}
        if args.compare:
            variants = {
                name: replace(config, traits={**config.traits, **values})
                for name, values in PRESETS.items()
            }
        if args.sweep:
            variants = {
                f"{args.sweep}={value}": replace(
                    config,
                    traits={**config.traits, args.sweep: value},
                )
                for value in (0.0, 0.25, 0.5, 0.75, 1.0)
            }
        reports = {
            name: run_scenario(cfg, args.scenario, turns=turns) for name, cfg in variants.items()
        }
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(reports, ensure_ascii=True, indent=2))
        return
    print("Offline plugin guidance only; no live configuration or provider calls.\n")
    print("| Variant | Turn | Posture | Expression | Frustration | Offense | Atmosphere |")
    print("|---|---:|---|---|---:|---:|---:|")
    for name, report in reports.items():
        for row in report["turns"]:
            print(
                f"| {name} | {row['turn']} | {row['posture']} | {row['expression_tier']} "
                f"| {row['frustration']} | {row['offended']} | {row['perceived_tension']} |"
            )
    print("\nUse --json for effective traits, derived drives and exact injected guidance.")


if __name__ == "__main__":
    main()
