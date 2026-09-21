# Affect dashboard session-navigation plan

This is the implementation handoff for adding session selection to the
existing Hermes Affect dashboard. It is a plan only: no endpoint, storage, or
frontend behavior described here is implemented at this checkpoint.

Plan date: 2026-09-21.

## User outcome

When the Affect tab opens, it continues to display the newest valid affect
state available inside the current Hermes container. The page also provides a
session navigator so an authenticated dashboard user can select a retained
session and inspect that session's persisted affect snapshot.

The selected session is a snapshot selector, not a timeline. Historical charts,
cross-container aggregation, and state mutation remain out of scope.

## Required behavior

1. Open the Affect tab in **Latest session** mode, preserving today's behavior.
2. Show a navigation area containing retained valid sessions, newest first.
3. Group or label entries by profile so the UI remains correct if one container
   can see more than one profile.
4. Show only useful summary metadata in the navigator: profile ID, session ID,
   update age/time, revision, mood, posture, and model version.
5. Selecting an entry loads the existing safe-state projection for that exact
   profile/session pair.
6. Keep polling the selected session without switching it to another session.
   **Latest session** mode may move naturally when a newer state appears.
7. If a selected state is removed by retention or becomes unreadable, retain
   the selection, show a clear unavailable message, and offer a return to
   **Latest session**. Do not silently display a different session.
8. Refresh the session catalog on initial mount and from an explicit refresh
   control. Do not add another aggressive background scan.
9. On narrow screens, present the navigator as a compact selector or drawer
   above the state view. On wider screens, use a restrained sidebar or split
   layout without shrinking the existing cards excessively.
10. A browser reload returns to **Latest session** mode for this first version.
    URL deep links and persisted browser selection are deferred.

## API contract

Keep the current endpoint backward-compatible:

```text
GET /api/plugins/hermes-affect/state
```

With no query parameters it continues to return the newest valid state.

Add exact selection through the same endpoint:

```text
GET /api/plugins/hermes-affect/state?profile_id=<id>&session_id=<id>
```

Rules:

- both identifiers are required together;
- each identifier must be non-empty and bounded to the existing 200-character
  inspection limit;
- a present exact state returns the existing `DashboardStateResponse` shape;
- a missing, collected, mismatched, malformed, or unsupported selected state
  returns a bounded `404` without paths or file content;
- no-query behavior and the default-off feature gate remain unchanged.

Add a paged catalog endpoint:

```text
GET /api/plugins/hermes-affect/sessions?limit=50&offset=0
```

Use a default page size of 50 and a maximum of 100. Reject negative offsets and
out-of-range limits through ordinary FastAPI validation. Offset pagination is
acceptable here because the catalog is administrative and eventually
consistent; the UI must tolerate a newly inserted session between requests.

Proposed response:

```json
{
  "items": [
    {
      "profile_id": "bot:one",
      "session_id": "session:one",
      "updated_at": "2026-09-21T10:00:00+00:00",
      "revision": 12,
      "mood": "guarded",
      "response_posture": "terse",
      "model_version": 2
    }
  ],
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

The endpoint must return summaries, not full state projections. It must skip
invalid files using the same explicit error boundary as current latest-state
selection and must never expose filesystem paths, timestamps taken from file
metadata, audits, social observations, SOUL data, or raw persisted JSON.

## Backend design

### Persistence

Extend `StateStore` with small public read operations rather than duplicating
JSON discovery and parsing in the dashboard package:

- `load_exact(profile_id, session_id)` loads through the existing sanitized
  path and then verifies that the parsed state's original identifiers exactly
  equal the requested identifiers. This prevents sanitized-name collisions
  from returning the wrong session.
- `recent(limit, offset)` returns valid states ordered by parsed `updated_at`
  descending, with profile ID and session ID as deterministic tie-breakers.
  Read one extra item to compute `has_more` at the application boundary.
- Reuse one private valid-state iterator/parser for `latest()`,
  `latest_for_profile()`, and `recent()` so malformed-file handling does not
  drift between methods.

Do not add writes, indexes, cache files, SQLite, or new locks. Atomic replacement
already makes individual reads safe. Catalog performance should be measured in
the packaged-image smoke test before introducing caching.

### Dashboard layers

Keep responsibilities explicit:

- `domain/session_models.py`: typed session-summary and catalog response shapes.
- `application/session_catalog.py`: pagination validation-independent use case,
  state-to-summary projection, and exact-selection orchestration.
- `infrastructure/session_reader.py`: small adapter around the new `StateStore`
  read operations.
- `application/inspection.py`: continue to own full safe-state response
  assembly; do not duplicate `state_snapshot()`.
- `plugin_api.py`: parse HTTP inputs, enforce the feature gate, translate
  expected missing-selection results to `404`, and delegate. It must remain a
  thin adapter with no filesystem traversal or response assembly.

If extending an existing module keeps one clear responsibility and remains
small, reuse it. If it begins mixing catalog, exact lookup, and presentation
concerns, split it at the boundaries above rather than growing a multipurpose
file.

## Frontend design

### State model

Represent selection explicitly:

```text
{ mode: "latest" }
{ mode: "exact", profileId: "...", sessionId: "..." }
```

Do not overload `null`, the currently displayed response, or a session ID alone
to mean several modes. Profile ID is part of the identity.

Add domain normalization for catalog pages and summaries. Bound strings and
numbers exactly as the current state normalization does. Invalid catalog items
should be discarded rather than partially rendered.

### Requests and polling

- Keep the initial `/state` request as the feature preflight used before tab
  registration.
- Add `loadSessions(limit, offset)` and
  `loadState(selection)` to the infrastructure layer. Build query strings with
  `URLSearchParams`; never concatenate raw identifiers into URLs.
- Poll the state every five seconds as today. In exact mode, every poll must
  include the same profile/session pair.
- Use a monotonically increasing request generation or equivalent cancellation
  guard so a slow response for the previous selection cannot overwrite the
  newly selected session.
- Fetch the catalog on mount and explicit refresh. Support **Load more** using
  the API page metadata; do not repeatedly fetch every retained session in the
  background.
- Keep separate state for catalog errors and selected-state errors. A catalog
  refresh failure must not erase the affect snapshot already on screen.

### Presentation

Refactor the current presentation before adding navigation so `page.js` does
not become a giant file:

```text
frontend/src/presentation/
├── primitives.js          # cards, badges, metric bars, chips
├── state_view.js          # mood core and affect-state sections
├── session_navigator.js   # latest item, session list, refresh/load-more UI
├── page.js                # layout and composition only
└── style.css
```

Recommended navigation behavior:

- **Latest session** is the first and visually distinct entry.
- The selected entry has an accessible active state, not color alone.
- Each session row shows a shortened visual ID while retaining the complete ID
  in a safe title/label.
- A lightweight client-side filter may search the currently loaded summaries
  by profile or session ID; it must not imply that unloaded pages were searched.
- Loading a selection should preserve the current layout and show a localized
  loading state rather than blanking the entire plugin page.
- Keyboard navigation, focus visibility, readable contrast, and reduced-motion
  behavior must remain intact.

Update `dashboard/tools/build_dashboard.py` with a clear dependency order for
the new modules. The generated `dist/` files remain build outputs, not editable
source.

## Clean-code requirements

Clean, organized implementation is a requirement, not a later refactoring
task.

- Keep functions single-purpose and name them for the behavior they own.
- Do not create giant functions, giant files, broad manager classes, or a
  catch-all utilities module.
- Treat a function approaching roughly 40 lines or a source file approaching
  roughly 300 lines as a review signal. These are not mechanical limits, but
  crossing them requires a clear reason; otherwise split by responsibility.
- Prefer small pure projection/normalization functions over deeply nested
  conditionals and mutable shared objects.
- Keep HTTP, persistence, application, domain, and presentation concerns in
  their existing layers.
- Do not duplicate state parsing, privacy filtering, polling, or error mapping.
- Avoid boolean combinations whose meaning is unclear; use explicit selection
  and request-state models.
- Do not hide malformed data or programming errors with broad exception
  catches. Continue using the repository's narrow, documented malformed-file
  boundary.
- Add no dependency unless the existing standard-library and Hermes SDK
  surfaces genuinely cannot express the requirement.
- Refactor the existing presentation in reviewable steps before layering new UI
  behavior onto it.

## Security and privacy constraints

- Both new read forms stay behind Hermes dashboard authentication and the
  existing `HERMES_AFFECT_DASHBOARD` gate.
- Keep all routes `GET`-only and read-only.
- Never accept a filesystem path from the browser.
- Verify exact parsed profile/session identity after resolving the sanitized
  storage path.
- Reuse the existing safe full-state projection.
- Keep the catalog summary minimal and bounded.
- Do not expose raw messages, audits, observed participants, social edges,
  SOUL content/hash, predisposition, credentials, paths, or stack traces.
- Do not broaden container mounts or aggregate states across containers.

## Implementation phases

### Phase 1 — contracts and persistence reads

- [ ] Add backend response types and pure summary projection tests.
- [ ] Add `StateStore.load_exact()` with collision/mismatch tests.
- [ ] Refactor shared valid-state iteration without changing current latest
      behavior.
- [ ] Add ordered, bounded recent-state reads with pagination tests.

Checkpoint: storage tests pass and no dashboard route or UI behavior changes.

### Phase 2 — dashboard backend

- [ ] Add catalog and exact-selection application services.
- [ ] Add `GET /sessions` with bounded pagination.
- [ ] Extend `GET /state` with paired optional identifiers.
- [ ] Cover disabled mode, partial identifiers, invalid bounds, exact hit,
      exact miss, garbage-collected state, malformed files, and sanitized-name
      collision behavior.
- [ ] Confirm all responses retain the existing privacy exclusions.

Checkpoint: focused backend tests pass; the existing no-query endpoint remains
backward-compatible.

### Phase 3 — frontend domain and controller

- [ ] Add catalog/selection normalizers and query construction.
- [ ] Add explicit latest/exact selection state.
- [ ] Add race-safe exact-session polling.
- [ ] Add catalog pagination, refresh, loading, and error state without coupling
      it to the displayed snapshot.
- [ ] Test pure state transitions and stale-response rejection with Node's
      standard test/assertion facilities.

Checkpoint: controller behavior is testable without rendering React.

### Phase 4 — navigation presentation

- [ ] Split reusable presentation primitives and the state view out of the
      current `page.js` before adding navigation.
- [ ] Implement the responsive session navigator and active-selection states.
- [ ] Add explicit exact-session loading, unavailable, and return-to-latest
      behavior.
- [ ] Preserve the existing visual language and narrow-screen usability.
- [ ] Perform a real visual check in Hermes at desktop and narrow widths.

Checkpoint: selecting several retained sessions changes only the state view and
never loses the chosen identity during polling.

### Phase 5 — build, tests, and documentation

- [ ] Update deterministic bundle ordering and regenerate `dist/`.
- [ ] Run focused backend tests, frontend domain/controller tests, JavaScript
      syntax validation, generated-asset checks, Ruff, and the full repository
      suite.
- [ ] Update dashboard README, architecture, privacy, and deployment notes.
- [ ] Update `dashboard/PLAN.md` and the root `TODO.md` with the achieved
      checkpoint.
- [ ] Smoke-test the packaged plugin with the existing dashboard feature gate;
      do not modify live deployment configuration without explicit approval.

## Acceptance criteria

- The first view is still the latest valid state.
- An authenticated user can page through retained sessions and select an exact
  profile/session state.
- Exact selection remains pinned while polling and cannot be overwritten by an
  earlier request.
- Missing or collected selected state is explained without falling back to a
  different session.
- The session catalog is bounded, ordered, read-only, and contains no prohibited
  fields or filesystem information.
- Existing default-off behavior, dashboard authentication, privacy projection,
  and no-extra-port design remain unchanged.
- The implementation has clear layer boundaries and no giant or convoluted
  functions/files.
- Generated assets are current and all focused and repository-wide checks pass.

## Explicitly deferred

- Time-series charts or replaying intermediate affect changes.
- Session comparison or diff views.
- Cross-container/all-bot aggregation.
- Conversation titles or transcript lookup through private Hermes APIs.
- URL deep links and browser-persisted selection.
- Dashboard mutations such as calm, heat, tune, reset, migrate, or delete.
- Automatic caching/index files before catalog performance is measured.

## Luna handoff order

1. Read repository `AGENTS.md`, root `README.md`, root `TODO.md`,
   `dashboard/README.md`, `dashboard/PLAN.md`, and every file under
   `dashboard/docs/`.
2. Read this plan completely, then inspect current backend/frontend tests and
   source before editing.
3. Run `git status --short --branch` and preserve existing work.
4. Implement one phase at a time, updating checkboxes only after its checkpoint
   passes.
5. Keep changes reviewable and refactor before any function or file becomes
   multi-purpose or difficult to scan.
6. Do not change Docker, Compose, the Raspberry Pi, a live Hermes instance, or
   deployment state without separate explicit authorization.
