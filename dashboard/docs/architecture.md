# Dashboard architecture

## Objective

Provide a clear, read-only view of the latest affect state without creating a
second state model, web server, authentication system, or Docker exposure.

## Runtime flow

```text
Hermes dashboard browser tab
        |
        | authenticated GET /api/plugins/hermes-affect/state
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
loading. The feature owns only the affect-specific read adapter and page.

## Layering

The backend mirrors the main plugin:

- `domain/` defines bounded view models and validation without Hermes or
  FastAPI imports.
- `application/` chooses the state and assembles the response using the shared
  safe projection.
- `infrastructure/` reads the file-backed state store and translates storage
  failures at the boundary.
- `plugin_api.py` is the thin Hermes/FastAPI adapter.

The browser source uses equivalent boundaries:

- `domain/` validates the response and defines display scales and labels.
- `application/` owns polling and page state transitions.
- `infrastructure/` calls the authenticated plugin endpoint.
- `presentation/` renders components using the Hermes dashboard SDK.
- `index.js` is the thin registration boundary.

## State selection

The first release selects the latest valid state available in the current
container. The deployment currently uses a separate data root for each Hermes
container, so this normally represents one bot.

If multiple profiles are later enabled in one container, an explicit profile
selector may be added using a bounded `latest per profile` query. Cross-container
aggregation is intentionally excluded: it would introduce another service,
credential flow, or broad read mount and would weaken the existing isolation
model.

## API shape

The planned first endpoint is:

```text
GET /api/plugins/hermes-affect/state
```

The response wraps the same projection as `/affect state`:

```json
{
  "available": true,
  "state": {
    "profile_id": "bot-id",
    "session_id": "session-id"
  }
}
```

When no valid state exists, the endpoint returns
`{"available": false, "state": null}` with HTTP 200. A present state includes:

- profile and session identity;
- revision and update timestamp;
- mood, response posture, model version, and migration status;
- expression drive and perceived atmosphere tension;
- valence, arousal, frustration, and offended values;
- current relationships, active sensitivities, open conflicts, and tuning
  overrides.

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
- Frontend or plugin failure: Hermes' other dashboard pages remain functional.
