# Dashboard architecture

## Objective

Provide a clear view of the latest affect state and optional, session-scoped
manual controls without creating a second state model, web server,
authentication system, or Docker exposure.

## Runtime flow

```text
Hermes dashboard browser tab
        |
        | authenticated reads and explicitly gated exact-session writes
        v
dashboard/plugin_api.py
        |
        v
dashboard application use case
        |
        v
shared safe-state projection + StateStore
        |
        v
HERMES_AFFECT_STATE_DIR/<profile>/sessions/<session>.json
```

Hermes owns HTTP serving, authentication, route mounting, and static-asset
loading. The feature owns only the affect-specific state adapter, narrow tuning
use case, and page.

## Layering

The backend mirrors the main plugin:

- `domain/` defines bounded view models and validation without Hermes or
  FastAPI imports.
- `application/` chooses the latest or exact state, assembles the response
  using the shared safe projection, produces bounded session catalog pages, and
  validates session tuning and manual source-value mutations.
- `infrastructure/` reads the file-backed state store and provides
  lock-protected exact-state mutation with revision checks and atomic writes.
- `plugin_api.py` is the thin Hermes/FastAPI adapter.

The browser source uses equivalent boundaries:

- `domain/` validates the response and defines display scales and labels.
- `application/` owns polling and page state transitions.
- `infrastructure/` calls the authenticated plugin endpoint.
- `presentation/` renders components using the Hermes dashboard SDK.
- `index.js` is the thin registration boundary.

## State selection

The page first selects the latest valid state available in the current
container. A bounded catalog can then select one exact profile/session pair.
The deployment currently uses a separate data root for each Hermes container,
so this normally represents one bot, while profile grouping keeps the UI
correct if a container sees more than one profile.

Cross-container aggregation is intentionally excluded: it would introduce
another service, credential flow, or broad read mount and would weaken the
existing isolation model.

## API shape

The state and catalog endpoints are:

```text
GET /api/plugins/hermes-affect/state
GET /api/plugins/hermes-affect/state?profile_id=<id>&session_id=<id>
GET /api/plugins/hermes-affect/sessions?limit=50&offset=0
```

The existing session-tuning endpoints and the manual source-value endpoint are
registered only when both `HERMES_AFFECT_DASHBOARD` and
`HERMES_AFFECT_DASHBOARD_CONTROLS` are explicitly enabled:

```text
POST /api/plugins/hermes-affect/tuning?profile_id=<id>&session_id=<id>&expression_gain=<0..10>&expected_revision=<n>
DELETE /api/plugins/hermes-affect/tuning?profile_id=<id>&session_id=<id>&expected_revision=<n>
POST /api/plugins/hermes-affect/controls
```

The tuning endpoints apply or remove only the v2 `expression_gain` override.
The JSON controls request edits one allowed v2 source field: affect valence,
arousal, frustration, or offended; atmosphere tension; or trust, affinity,
respect, irritation, or unresolved tension for an existing participant. The
manual editor applies elapsed decay and the requested value under one lock,
then refreshes only derived mood/conflict projections. Classification and
provider calls remain outside the lock; the final event transition re-reads the
latest state under lock before applying decay and events. Lifecycle timestamp
updates likewise mutate the latest locked state. The administrative command
and dashboard tuning endpoints share the same `SessionTuningService` for
expression-gain validation and mutation.

The response wraps the same projection as `/affect state`:

```json
{
  "available": true,
  "controls_enabled": true,
  "state": {
    "profile_id": "bot-id",
    "session_id": "session-id"
  }
}
```

When no valid state exists, the endpoint returns
`{"available": false, "state": null, "controls_enabled": false}` with HTTP
200 (the capability is true when controls are enabled). A present state
includes:

- profile and session identity;
- revision and update timestamp;
- mood, response posture, model version, and migration status;
- expression drive and perceived atmosphere tension;
- valence, arousal, frustration, and offended values;
- current relationships, active sensitivities, open conflicts, and tuning
  overrides.

Every mutation requires the selected exact identity and expected revision.
Stale revisions return a bounded conflict response; invalid values return
`422`, and unavailable sessions or participants return `404`. This prevents a
dashboard poll or an older form from overwriting newer session state.

The catalog route returns only profile/session IDs and bounded update, revision,
mood, posture, and model-version summaries. Exact selection requires both IDs;
missing, malformed, collected, or mismatched exact state returns a bounded 404.

Excluded fields are recorded in
[`privacy-and-security.md`](privacy-and-security.md).

## Update model

The initial page polls the endpoint. Affect updates occur around conversation
turns, so a five-second starting interval should be responsive without adding
continuous server work. The component must cancel its timer when unmounted and
must not issue overlapping requests.

Historical charts are deferred because the persisted audit ring is not a
dashboard time-series contract. Adding trends requires a separately designed,
bounded, transcript-free history projection.

## Failure behavior

- Feature disabled: backend returns `404`; the bundle does not register a tab.
- No state: page shows an empty-state explanation.
- Malformed or unsupported state files are skipped while selecting the latest
  valid state; if none remain, the page receives the normal empty response.
- Stale state: page remains readable and labels the update age.
- Controls disabled: the read-only page remains available and all editing
  controls are hidden; a manual edit conflict triggers refresh and draft reset.
- Frontend or plugin failure: Hermes' other dashboard pages remain functional.
