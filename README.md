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

The scaffold is intentionally not yet a complete production integration. Exact
Hermes hook payloads, profile-home discovery, compression lineage handling,
administrative identity plumbing, garbage collection, and full retry
idempotency must be validated against the target Hermes image before deployment.

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
[`docs/installation.md`](docs/installation.md),
[`docs/privacy-and-retention.md`](docs/privacy-and-retention.md), and
[`examples/soul/basic.md`](examples/soul/basic.md).
