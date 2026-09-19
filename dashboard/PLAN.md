# Hermes Affect dashboard implementation plan

This is the durable execution and handoff plan for the optional Hermes Affect
dashboard. Update its checkboxes and checkpoint whenever a phase or acceptance
criterion is completed.

## Current checkpoint

Checkpoint date: 2026-09-19.

- [x] Create an isolated dashboard feature directory.
- [x] Record the native Hermes dashboard-extension architecture.
- [x] Define the initial security, privacy, deployment, and feature-toggle
      boundaries.
- [x] Create a Python package scaffold with the same layering as the main
      plugin.
- [ ] Implement the shared safe-state projection.
- [ ] Implement or activate any dashboard endpoint or UI.

No runtime behavior, Docker configuration, deployed Hermes configuration, or
Raspberry Pi state was changed at this checkpoint. Hermes will not discover
this scaffold because `dashboard/manifest.json` and
`dashboard/plugin_api.py` do not exist yet.

## Decisions already made

1. Use Hermes' native dashboard plugin surface: a manifest, a pre-built browser
   bundle, and a FastAPI router mounted by Hermes.
2. Do not start a plugin-owned web server and do not publish a new Docker port.
3. Require both Hermes' dashboard and `HERMES_AFFECT_DASHBOARD=1`. The affect
   flag defaults to disabled.
4. Keep the API read-only in the first release.
5. Reuse one shared safe-state projection for `/affect state` and the HTTP API.
6. Show the latest state available in the current container first. Do not
   weaken separate-container state isolation to build an all-bot view.
7. Poll periodically in the browser for the first release. Do not add WebSocket
   lifecycle complexity until measurements show it is useful.
8. Show current state rather than a time-series graph. Historical visualization
   requires a separately reviewed bounded history model.
9. Keep Hermes compatibility code at the dashboard adapter boundary and avoid
   private Hermes imports in the feature's domain or application layers.

## Target layout

Files marked `(generated)` are build outputs and must not become the editable
source of truth.

```text
dashboard/
├── manifest.json                         # Hermes dashboard manifest
├── plugin_api.py                         # thin FastAPI/Hermes adapter
├── dist/
│   ├── index.js                          # generated browser bundle
│   └── style.css                         # generated or reviewed CSS
├── hermes_affect_dashboard/
│   ├── application/
│   │   ├── inspection.py                 # use cases and response assembly
│   │   └── feature_gate.py               # strict environment toggle
│   ├── domain/
│   │   └── view_models.py                # bounded API response models
│   └── infrastructure/
│       └── state_reader.py                # StateStore-backed read adapter
├── frontend/
│   ├── src/
│   │   ├── application/                  # polling and view-model orchestration
│   │   ├── domain/                       # scales, labels, state validation
│   │   ├── infrastructure/               # authenticated API client
│   │   ├── presentation/                 # Hermes SDK components and styles
│   │   └── index.js                      # registration boundary
│   └── README.md
├── tests/                                # focused dashboard tests
├── docs/
└── tools/                                # deterministic asset build, if needed
```

## Phase 1 — shared inspection projection

- [ ] Extract the payload construction currently embedded in
      `AffectCommandHandler._state_debug` into a pure application function in
      the main plugin.
- [ ] Keep `/affect state [profile]` output backward-compatible.
- [ ] Define explicit included and excluded fields.
- [ ] Add tests proving audit records, social observations, raw messages,
      predisposition, and SOUL hashes are absent.
- [ ] Add a store query that safely enumerates the latest valid state per
      profile only if the per-container UI needs it.

Acceptance criteria:

- Command and dashboard callers receive the same canonical projection.
- Atomic writer replacement continues to make lock-free reads safe from partial
  JSON files.
- Malformed or unsupported state files are skipped or reported explicitly;
  errors are not broadly suppressed.

## Phase 2 — optional dashboard backend

- [ ] Add a strict parser for `HERMES_AFFECT_DASHBOARD`; only documented true
      and false values are accepted, and invalid values fail closed with a
      warning.
- [ ] Add a thin `dashboard/plugin_api.py` exporting a FastAPI `router`.
- [ ] Add `GET /state` for the latest current-container snapshot.
- [ ] Return `404` while the feature flag is disabled so no state is disclosed.
- [ ] Add no POST, PUT, PATCH, or DELETE routes.
- [ ] Reuse `HERMES_AFFECT_STATE_DIR` for the state root.
- [ ] Verify behavior when the directory is missing, empty, malformed, or
      concurrently updated.

Acceptance criteria:

- The endpoint is mounted only by Hermes' dashboard process and remains behind
  its normal authentication gate.
- Enabling the affect engine does not automatically enable web inspection.
- The backend adds no runtime dependency beyond packages already provided by
  the documented Hermes dashboard extension contract.

## Phase 3 — dashboard frontend

- [ ] Add `manifest.json` only when the backend feature gate is implemented.
- [ ] Create layered browser source under `frontend/src/`.
- [ ] Register an Affect tab only after the enabled backend responds
      successfully; do not leave a misleading tab when the feature is off.
- [ ] Render mood, posture, freshness, expression drive, perceived atmosphere,
      affect values, relationships, sensitivities, and conflicts.
- [ ] Treat valence as `[-1, 1]` and the other gauges as `[0, 1]`.
- [ ] Poll conservatively and stop polling when the component unmounts.
- [ ] Show explicit loading, disabled, empty, stale, and error states.
- [ ] Use Hermes dashboard SDK components and theme variables.
- [ ] Produce one reviewable pre-built IIFE bundle without bundling React.

Acceptance criteria:

- The page remains useful on a narrow screen and does not require a custom
  theme.
- No endpoint URL, state value, or identity is inserted as unsafe HTML.
- A backend or bundle failure does not interfere with the rest of the Hermes
  dashboard.

## Phase 4 — tests and compatibility

- [ ] Add focused unit tests for the feature flag, projection, state selection,
      disabled route, successful route, and excluded fields.
- [ ] Add a small frontend test or deterministic validation for state parsing
      and scale conversion.
- [ ] Verify the manifest and generated bundle paths.
- [ ] Run the main plugin test suite and Ruff.
- [ ] Smoke-test against the pinned Hermes image without changing the running
      deployment.
- [ ] Record any actual public-contract difference before adding compatibility
      branching.

Acceptance criteria:

- Existing plugin behavior remains unchanged when the dashboard flag is off.
- The dashboard does not depend on private gateway runtime objects.
- Python 3.10 compatibility and Raspberry Pi ARM64 suitability are preserved.

## Phase 5 — documentation and deployment handoff

- [ ] Update this directory's documents with the implemented names and payload.
- [ ] Link the dashboard from the repository README and relevant architecture,
      installation, compatibility, and privacy documents.
- [ ] Document enable, disable, upgrade, and rollback behavior.
- [ ] Propose the separate `home-config` change for review; do not modify or
      deploy it without explicit authorization.
- [ ] Validate that the existing dashboard port and authentication are used and
      that no extra port is published.
- [ ] Keep actual secrets, state, and screenshots containing identifiers out of
      Git.

Acceptance criteria:

- A new session can identify the exact implementation status from this file.
- Turning the feature off removes state access without disabling affect
  processing.
- Rollback preserves affect state and only removes the optional web surface.

## Deferred work

- Cross-container aggregation for several bot instances.
- Historical charts and long-term affect trends.
- WebSocket or server-sent-event updates.
- Mutating controls such as calm, heat, tune, or reset.
- Public or unauthenticated temperament summaries.

Each item requires its own privacy, authorization, and deployment review.

## Open questions to resolve during implementation

1. Confirm how the pinned Hermes image places `dashboard/plugin_api.py` on
   `sys.path`; keep any path bootstrap in the thin adapter if needed.
2. Choose and document the smallest deterministic browser build process. A
   dev-only bundler is acceptable, but it must not add a Node runtime to the
   deployed container.
3. Confirm whether a bundle that does not call `register()` is completely
   absent from dashboard navigation on the pinned Hermes image.
4. Decide the polling interval after measuring state update frequency and Pi
   resource use; begin conservatively around five seconds.

## Resume procedure

At the start of a new session:

1. Read the repository `AGENTS.md`, `README.md`, `TODO.md`, and relevant main
   plugin documents.
2. Read this `README.md`, this plan, and every file under `dashboard/docs/`.
3. Run `git status --short --branch` and inspect recent commits. Preserve all
   existing user changes.
4. Confirm the current checkpoint and start with the first unchecked phase.
5. Keep this plan updated as work and acceptance criteria are completed.
6. Run focused tests, the broader suite when boundaries change, and review the
   final diff before handoff.
7. Do not run Raspberry Pi, SSH, deployment, commit, push, or release commands
   without explicit authorization.

