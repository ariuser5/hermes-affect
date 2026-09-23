# Hermes Affect dashboard

This directory contains the optional, authenticated Hermes Affect web dashboard.
It follows the same application/domain/infrastructure layering as the main
plugin and uses Hermes' native dashboard-extension surface rather than running
another web server.

The feature is implemented but disabled by default. Hermes discovers
`manifest.json`, serves the pre-built files in `dist/`, and mounts
`plugin_api.py` below `/api/plugins/hermes-affect/`. The Affect tab registers
only when an initial authenticated request succeeds.

## Enablement boundary

Both controls must be enabled:

1. Hermes' dashboard and the `hermes-affect` plugin are enabled normally.
2. The Hermes dashboard process receives `HERMES_AFFECT_DASHBOARD=1`.

Only `1`, `true`, `yes`, and `on` enable a flag, case-insensitively. Missing
and documented false values disable it. Invalid values fail closed and emit an
administrative warning. While the dashboard flag is disabled, `GET /state`
returns `404` and the browser does not add an Affect tab. State reads remain
available when the dashboard is enabled but controls are not.

The endpoint uses the existing Hermes dashboard authentication and port. It
does not open another listener or publish another Docker port. Mutations are
separately gated by `HERMES_AFFECT_DASHBOARD_CONTROLS=1`, which defaults off.
With both flags enabled, the dashboard can update only the selected session's
supported source values and `expression_gain`; it never changes SOUL
configuration or another session.

## What the page shows

The page opens in **Latest session** mode and polls the latest valid state
visible in the current container every five seconds. It also provides a
bounded retained-session dropdown, grouped by profile, with exact
profile/session selection, refresh, and load-more pagination. Long session IDs
are shortened inside the options while the complete selected profile/session
identity remains visible beside the selector. Exact selections remain pinned
while polling; if retention removes one, the page reports it as unavailable
instead of switching silently.

The state view shows mood, posture, freshness, expression drive, perceived
atmosphere, affect values, relationships, active sensitivities, open conflicts,
and temporary tuning overrides.

When dashboard controls are enabled, “Manual state controls” provides sliders,
numeric inputs, and explicit Apply buttons for valence, arousal, frustration,
offended, atmosphere tension, and existing participant relationship values
(trust, affinity, respect, irritation, and unresolved tension). Each request
targets one exact profile/session and, for relationships, an existing
participant ID. Under the state-file lock, the service applies elapsed passive
decay once, then the selected value, refreshes only dependent mood/conflict
projections, increments the revision once, and saves. A genuinely new session
starts with fresh defaults; compression continuation retains the same
conversation state.

Valence and relationship trust/affinity/respect range from `-1` to `1`.
Arousal, frustration, offended, atmosphere tension, irritation, and unresolved
tension range from `0` to `1`.

The API exposes the existing latest-state route plus these selection forms and
narrow exact-session mutation routes:

```text
GET /api/plugins/hermes-affect/state?profile_id=<id>&session_id=<id>
GET /api/plugins/hermes-affect/sessions?limit=50&offset=0
POST /api/plugins/hermes-affect/tuning?profile_id=<id>&session_id=<id>&expression_gain=<0..10>&expected_revision=<n>
DELETE /api/plugins/hermes-affect/tuning?profile_id=<id>&session_id=<id>&expected_revision=<n>
POST /api/plugins/hermes-affect/controls
```

The JSON controls request contains `profile_id`, `session_id`, `scope`, `field`,
`value`, and `expected_revision`; relationship edits also require
`participant_id`. The server rejects unknown fields, non-number JSON values,
out-of-range values, unavailable sessions/participants, and stale revisions.
All mutation routes are absent unless both dashboard flags are enabled.

The catalog is capped at 100 entries per page and returns summaries only.

The response reuses the safe projection used by `/affect state`. It excludes
raw messages, audit records, observed-participant history, SOUL contents and
hashes, predisposition data, provider material, credentials, and filesystem
details. See [`docs/privacy-and-security.md`](docs/privacy-and-security.md).

## Layout and build

```text
dashboard/
├── manifest.json
├── plugin_api.py
├── dist/                         # committed, generated Hermes assets
├── hermes_affect_dashboard/
│   ├── application/
│   ├── domain/
│   └── infrastructure/
├── frontend/
│   ├── src/                      # editable browser source
│   └── tests/
├── tests/
├── tools/build_dashboard.py
├── docs/
├── PLAN.md
├── SESSION_NAVIGATION_PLAN.md
└── SESSION_STATE_CONTROLS_PLAN.md
```

Rebuild and verify the browser assets with:

```bash
python -m dashboard.tools.build_dashboard
python -m dashboard.tools.build_dashboard --check
node dashboard/frontend/tests/domain.test.js
node dashboard/frontend/tests/manual_state_controller.test.js
node dashboard/frontend/tests/manual_state_presentation.test.js
node dashboard/frontend/tests/poll_refresh_queue.test.js
node --check dashboard/dist/index.js
```

Run the feature tests with:

```bash
python -m unittest discover -s dashboard/tests -t .
```

The build is dependency-free: it concatenates the ordered browser modules into
one inspectable IIFE and copies the reviewed CSS. React and common UI components
come from Hermes' dashboard SDK at runtime.

## Deployment scope

The first release deliberately selects the latest state inside one Hermes
container. Deployments that isolate each bot in its own container therefore
get one bot per dashboard. Cross-container aggregation, history charts,
WebSockets, reset/moderation controls, and controls outside the documented
source-value allowlist remain deferred. Every dashboard mutation is limited to
the selected exact session.

No deployment repository, running Hermes configuration, or Raspberry Pi state
is changed by this feature directory. See [`docs/deployment.md`](docs/deployment.md)
for the reviewed handoff and [`PLAN.md`](PLAN.md) for the exact checkpoint.
