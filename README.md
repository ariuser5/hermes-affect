# hermes-affect

Hermes Affect is a session-scoped affective state engine for Hermes Agent. It gives each bot dynamic moods, participant-specific relationships, social influence, conflict escalation, reconciliation, and emotional decay, guided by its SOUL.md. Temporary affective state influences tone, cooperation, and participation without automatically becoming permanent memory.

This repository is the source repository for the `hermes-affect` general
Python plugin. The plugin is designed for Hermes profiles and sessions, not
for a particular infrastructure or deployment repository.

## Current status

The repository currently contains the MVP scaffold: validated `SOUL.md`
configuration, bounded state models, deterministic event classification,
decay and transition primitives, social-influence policy interfaces, JSON
storage, response-posture derivation, a Hermes registration adapter, examples,
and unit tests.

The plugin is intentionally developed against Hermes' documented public
general-plugin API rather than a single pinned runtime image. Newest Hermes
versions have priority; older versions remain candidates when they preserve
the documented registration and callback contract. Version-specific behavior,
deployment paths, and full retry idempotency are validated separately from the
portable plugin implementation.

## Session affect configuration

The machine-readable `session_affect` section uses seven stable traits:
`reactivity`, `persistence`, `pride`, `playfulness`, `assertiveness`,
`social_influence`, and `receptiveness`. Each is inclusive `[0, 1]`. Event
strength controls are separate under `tuning`: `expression_gain`,
`escalation_gain`, and `repair_gain`. Missing fields use neutral defaults;
invalid recognized values fall back safely with an administrative warning.

The full authoring schema is [`schemas/session_affect.schema.json`](schemas/session_affect.schema.json).
Derived concepts and configuration behavior are documented in
[`docs/architecture.md`](docs/architecture.md). Unknown fields are ignored
with an administrative warning.

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
[`docs/privacy-and-retention.md`](docs/privacy-and-retention.md), and
[`examples/soul/basic.md`](examples/soul/basic.md).
