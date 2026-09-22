# hermes-affect

Hermes Affect is a session-scoped affective state engine for Hermes Agent. It gives each bot dynamic moods, participant-specific relationships, social influence, conflict escalation, reconciliation, and emotional decay, guided by its SOUL.md. Temporary affective state influences tone, cooperation, and participation without automatically becoming permanent memory.

This repository is the source repository for the `hermes-affect` general
Python plugin. The plugin is designed for Hermes profiles and sessions, not
for a particular infrastructure or deployment repository.

## Current status

The repository currently contains the MVP scaffold: validated `SOUL.md`
configuration, bounded state models, deterministic and optional semantic event
classification, target-aware arbitration, decay and transition primitives,
social-influence policy interfaces, JSON storage, response-posture derivation,
a Hermes registration adapter, examples, and unit tests. Semantic
classification is disabled by default and uses the active Hermes provider only
when explicitly enabled.

An optional authenticated affect dashboard is also implemented under
[`dashboard/`](dashboard/README.md). It uses Hermes' dashboard extension
surface, shares the existing dashboard port, and remains disabled unless
`HERMES_AFFECT_DASHBOARD=1` is explicitly supplied to the dashboard process.
Its only write control is a session-scoped `expression_gain` override with an
explicit restore action; it does not modify SOUL configuration or other
sessions.

The plugin is intentionally developed against Hermes' documented public
general-plugin API rather than a single pinned runtime image. Newest Hermes
versions have priority; older versions remain candidates when they preserve
the documented registration and callback contract. Version-specific behavior,
deployment paths, and full retry idempotency are validated separately from the
portable plugin implementation.

## Session affect configuration

The version-2 machine-readable `session_affect` section uses six stable traits:
`reactivity`, `persistence`, `pride`, `playfulness`, `assertiveness`,
`receptiveness`. Each is inclusive `[0, 1]`. The single per-bot tuning control
is `expression_gain`; escalation and repair derive from temperament and the
relationship. Missing fields use neutral defaults;
invalid recognized values fall back safely with an administrative warning.

The full authoring schema is [`schemas/session_affect.schema.json`](schemas/session_affect.schema.json).
Derived concepts and configuration behavior are documented in
[`docs/architecture.md`](docs/architecture.md). Unknown fields are ignored
with an administrative warning.

Each bot now maintains its own perceived atmosphere and observations of directed
exchanges among known participants. Temperament can produce playful provocation,
sensitivity to teasing, conflict avoidance, confrontation and mediation.
Awareness is limited to messages actually delivered to the bot.

Compare temperaments without touching a running bot:

```bash
python -m hermes_affect.tools.calibration --scenario banter --compare
python -m hermes_affect.tools.calibration --scenario group --compare
python -m hermes_affect.tools.calibration --scenario repair --sweep receptiveness --json
```

See [the calibration guide](docs/calibration.md) for examples, derived controls,
administrative `/affect explain` and read-only v1 migration proposals.
Existing v1 sessions are preserved and require a reviewed migration/reset;
the reduced model is not numerically equivalent to v1.

## Development

```bash
python -m pip install -e '.[dev]'
python -m pytest
python -m ruff check .
```

Runtime state belongs outside this repository. Configure a persistent state
directory with the plugin setting `state_dir` or the
`HERMES_AFFECT_STATE_DIR` environment variable.

See [`docs/architecture.md`](docs/architecture.md),
[`docs/hermes-compatibility.md`](docs/hermes-compatibility.md),
[`docs/installation.md`](docs/installation.md),
[`docs/privacy-and-retention.md`](docs/privacy-and-retention.md),
[`dashboard/README.md`](dashboard/README.md), and
[`examples/soul/basic.md`](examples/soul/basic.md).
