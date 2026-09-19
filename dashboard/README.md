# Hermes Affect dashboard

This directory is the self-contained feature area for the optional Hermes
Affect web dashboard. It will contain the dashboard backend, browser source,
generated dashboard assets, feature-specific tests, and documentation.

The dashboard is not implemented or activated yet. In particular, there is no
`manifest.json` or `plugin_api.py`, so Hermes will not discover a partial
dashboard extension.

## Intended integration

The feature will use Hermes' native dashboard-extension contract rather than
starting another HTTP server. When enabled, Hermes will mount the read-only
backend below `/api/plugins/hermes-affect/` and load a dedicated Affect tab
through the existing authenticated dashboard on port 9119.

The initial release is deliberately limited to the latest state visible inside
one Hermes container. The current deployment gives every bot container its own
data root, so a combined cross-container view is a separate future feature.

## Feature boundary

- The dashboard is opt-in through `HERMES_AFFECT_DASHBOARD=1`.
- Hermes' own dashboard must also be enabled.
- The first version exposes current state only and has no mutating routes.
- It reuses the safe state projection used by `/affect state`; it does not
  invent a second affect model.
- It does not expose raw messages, audit records, observed-participant history,
  SOUL contents or hashes, classifier material, or credentials.
- It shares the existing dashboard port and authentication gate. It does not
  create or publish another Docker port.

## Layout

```text
dashboard/
├── README.md
├── PLAN.md
├── docs/
│   ├── architecture.md
│   ├── deployment.md
│   └── privacy-and-security.md
├── hermes_affect_dashboard/
│   ├── application/
│   ├── domain/
│   └── infrastructure/
└── frontend/
    └── README.md
```

The Python package mirrors the main plugin's `application`, `domain`, and
`infrastructure` boundaries. The future root-level `plugin_api.py` will remain
a thin Hermes adapter, just as the main plugin keeps its Hermes registration
adapter thin. Browser code will follow the equivalent boundaries described in
[`frontend/README.md`](frontend/README.md).

## Resuming work

Start with [`PLAN.md`](PLAN.md). It records the current checkpoint, decisions,
implementation sequence, acceptance criteria, and unresolved questions for a
new session.

