# Affect dashboard manual state controls plan

This plan covers editable live affect, atmosphere, and existing participant
relationship values in the authenticated Hermes Affect dashboard. The
implementation must preserve session boundaries, expected-revision checks,
passive decay semantics, and the existing feature's privacy constraints.

Plan date: 2026-09-22.

## Current checkpoint

Phases 1–4 are implemented and their focused checks pass. Documentation and
build ordering are updated. The generated bundle check, all frontend tests and
syntax checks, focused backend tests, Ruff, `git diff --check`, and the complete
171-test repository suite pass. Live Hermes and packaged-image verification
remain intentionally pending.

## User outcome

An authenticated dashboard operator can select one retained profile/session,
review the complete target identity, edit one allowed source value, and apply
that value explicitly. The dashboard derives only the existing mood and
conflict projections that depend on edited sources. It does not replay events
or change unrelated sources to imitate an event.

The edit first applies passive decay through the current edit time, then sets
the requested value. Therefore already-aged values may decay during an edit;
the newly assigned value begins its normal decay clock at that edit time. The
edit updates `updated_at`, so the edited retained session may move to the top
of Latest-session ordering.

## Supported source values

- Affect: `valence` in `[-1, 1]`; `arousal`, `frustration`, and `offended` in
  `[0, 1]`.
- Atmosphere: `atmosphere_tension` in `[0, 1]`.
- Existing participant relationship: `trust`, `affinity`, and `respect` in
  `[-1, 1]`; `irritation` and `unresolved_tension` in `[0, 1]`.
- Relationship controls target only IDs already stored in that exact
  session's `relationships` mapping. This UI never creates participants.

Every control has a synchronized slider and number input plus an explicit
Apply button. One field is sent per mutation. A changed value is never sent
while the user is moving a slider.

## Consistency and lifecycle rules

- Validate the scope/field allowlist, exact profile/session/participant
  identity, numeric type, finite value, range, model version, and expected
  revision before persisting.
- Under one state-file lock, read the newest exact state, verify its parsed
  identity and expected revision, apply `decay_state()` once using the saved
  effective configuration, then apply the requested field.
- Recompute stored mood only for `valence`, `frustration`, or `offended` edits
  with the existing `derive_mood()` helper.
- Rebuild `open_conflicts` only for `unresolved_tension` edits with the existing
  `refresh_conflicts()` helper.
- Keep `response_posture` as the last processed turn's posture. The dashboard
  labels it “Last response posture.” Expression drive remains derived by the
  existing safe-state inspection calculation.
- Do not directly edit mood, posture, expression drive, conflict projections,
  social edges, observed-participant estimates, audit history, or other source
  values.
- New sessions retain fresh defaults. Compression continuation preserves the
  existing copied-state behavior.
- Conversation classification, including any provider call, remains outside
  the file lock. The final transition re-reads the latest state under lock,
  applies elapsed decay and the classified event(s), derives turn results,
  and saves atomically. Lifecycle timestamp updates also mutate the newest
  state under lock so they cannot overwrite a dashboard edit.

## Authorization and API

- Add strict default-off `HERMES_AFFECT_DASHBOARD_CONTROLS`. Invalid values
  produce one bounded warning and disable writes.
- Keep state and catalog reads available under
  `HERMES_AFFECT_DASHBOARD`; register no mutation routes unless both flags are
  enabled. This includes the existing expression-gain Apply and Restore routes.
- Return an explicit `controls_enabled` capability in the safe dashboard
  response. The frontend uses that capability to hide every editing control.
- Add one authenticated JSON mutation endpoint for the supported source values.
  Use `expected_revision`; return a safe updated projection or bounded `404`,
  `409`, or `422` responses. Never include storage paths or file contents.
- Preserve Hermes authentication, `SDK.fetchJSON`, and the existing listener.

## Frontend design

- Add focused application and presentation modules for manual state controls;
  keep session selection and expression-gain tuning components small.
- Capture the exact profile/session/participant target and expected revision at
  submission time. Latest mode resolves to the actual identity in the displayed
  response.
- Retain an edit draft during routine five-second polls. Reset it when the
  target changes or after a revision conflict; after conflict, refresh state
  and require a fresh Apply.
- Reject late mutation responses when the selected target has changed. Refresh
  the selected state after successful edits and display the resulting value and
  revision.
- Keep saving, success, validation, conflict, and unavailable states explicit;
  prevent duplicate submissions and keep keyboard/focus, narrow layouts, and
  light/dark themes usable.

## Implementation phases

### Phase 1 — locked state mutation foundation

- [x] Add a lock-protected exact-state mutation method that re-reads the file,
      verifies parsed identity and expected revision, and atomically writes
      under the same lock.
- [x] Refactor the writer to avoid nested lock acquisition.
- [x] Add a shared application service for strict manual-field validation,
      elapsed decay, field assignment, mood/conflict refresh, revision, and
      update timestamp.
- [x] Add unit tests for ranges/types, stale revisions, missing/legacy state,
      session isolation, mood/conflict projections, passive decay, and clock
      semantics.

Checkpoint: concurrent mutations cannot overwrite one another, and the
service edits one source field after applying the elapsed decay exactly once.

### Phase 2 — runtime concurrency

- [x] Move event classification and provider calls outside the state lock.
- [x] Re-read the latest exact state under lock before applying decay, routed
      events, observations, derived mood/posture, revision, and save.
- [x] Make duplicate-turn detection effective against the locked latest state.
- [x] Refactor post-call and session-end timestamp saves to mutate the latest
      locked state instead of saving an old snapshot.
- [x] Cover races between dashboard edits, conversation transitions, and
      lifecycle saves with deterministic synchronization tests.

Checkpoint: no plugin runtime path in scope can replace newer dashboard state
with a snapshot loaded before the edit; no file lock spans a classifier/provider
request.

### Phase 3 — gated backend routes

- [x] Add and test strict controls-flag parsing and bounded warnings.
- [x] Expose a `controls_enabled` capability without broadening the safe state
      projection with private data.
- [x] Gate expression-gain POST/DELETE routes and the new manual edit route on
      both feature flags.
- [x] Add one JSON endpoint with strict scope/field allowlists and 404/409/422
      mapping.
- [x] Test disabled flags, invalid values, path collisions, malformed/legacy
      states, unknown participants, and safe error bodies.

Checkpoint: reads continue with controls off, but no mutation route is
registered until both flags are explicitly enabled.

### Phase 4 — frontend controls

- [x] Add focused manual-control controller and presentation modules.
- [x] Add affect, atmosphere, and participant selector/control sets with
      sliders, synchronized number inputs, and explicit Apply buttons.
- [x] Display the full target identity, revision, save/error/conflict states,
      and last response posture label.
- [x] Preserve drafts during normal polls, reset them on target changes or
      conflicts, and reject stale target responses.
- [x] Add frontend tests for capability hiding, single-field submissions,
      target changes, drafts, conflict recovery, and no autosave.

Checkpoint: edits affect only the selected exact state, and successful edits
refresh its displayed value and revision.

### Phase 5 — docs, generated assets, and verification

- [x] Update deterministic build ordering and regenerate `dashboard/dist/`.
- [x] Update the dashboard README, architecture, privacy/security, deployment,
      implementation plan, root TODO, and this plan's checkpoint.
- [x] Run focused backend/frontend tests, full repository tests, Ruff,
      JavaScript syntax checks, the generated-asset check, and `git diff --check`.
- [x] Record that live Hermes visual and packaged-image checks remain pending
      if unavailable locally.

## Boundaries

- Do not modify Docker, Compose, `home-config`, a running Hermes deployment,
  Raspberry Pi state, or deployment configuration.
- Do not add controls for temperament traits, calm/heat/reset, relationships
  creation, sensitivities, or conflicts as independent values.
- Do not add dependencies or hold a state lock across external/provider work.
- Keep all changes local and unstaged; do not commit or push.
