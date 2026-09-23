# Dashboard privacy and security

## Trust boundary

The affect dashboard is an authenticated administrative observation surface,
not a public bot capability. Hermes owns the dashboard session, authentication
gate, and network listener. The feature must not create a parallel bearer
token, cookie, listener, or authorization database.

The deployment should remain restricted to its reviewed trusted network. An
authenticated user can read plugin routes, so dashboard credentials must be
treated as access to affect state.

## Default-off behavior

`HERMES_AFFECT_DASHBOARD` defaults to disabled. While disabled:

- the state endpoint returns `404`;
- the browser bundle does not register the Affect tab;
- affect processing and persistence continue normally;
- no additional port is opened.

`HERMES_AFFECT_DASHBOARD_CONTROLS` is a separate, default-off write gate. It
has no effect unless the dashboard flag is also enabled. With it off, state and
catalog reads work as before, the response advertises `controls_enabled: false`,
and the browser hides all editing controls. Invalid values fail closed.

An invalid flag value must fail closed and produce an administrative warning.

## Permitted response data

The first release may return the bounded current-state projection already
designed for `/affect state`:

- profile and session IDs;
- revision and update time;
- mood and response posture;
- affect dimensions and perceived atmosphere;
- derived expression drive;
- current relationship dimensions;
- active sensitivities, open conflicts, and tuning overrides.
- configured and effective `expression_gain` values needed by the session
  tuning control.
- A boolean `controls_enabled` capability so the browser can hide all
  mutation controls while keeping read-only inspection available.

The retained-session catalog exposes only bounded profile/session IDs, update
time, revision, mood, posture, and model version. Exact state selection requires
the paired profile and session IDs and returns the same safe current-state
projection as the state route.

These values can reveal interpersonal dynamics. They are acceptable only
behind the reviewed dashboard authentication boundary and must not be added to
normal model context or public chat responses by this feature.

## Prohibited response data

The endpoint must never return:

- raw user or assistant messages;
- conversation history or long quotations;
- classifier prompts, raw classifier output, or provider credentials;
- audit records;
- social-edge or observed-participant history;
- free-form SOUL content or its hash;
- the persisted predisposition snapshot;
- hidden reasoning or chain-of-thought;
- filesystem paths, lock contents, environment values, or stack traces.

## API constraints

- State and catalog routes are `GET`. Mutation routes are authenticated and
  registered only when both dashboard flags are enabled.
- The manual editor accepts only one JSON numeric source value at a time:
  valence `[-1, 1]`; arousal, frustration, offended, atmosphere tension,
  irritation, and unresolved tension `[0, 1]`; trust, affinity, and respect
  `[-1, 1]`. Relationship edits require an existing participant ID in that
  exact session.
- Every edit requires exact profile/session identity and `expected_revision`.
  The server rejects booleans, strings, non-finite values, unknown fields, and
  values outside the allowlist/ranges. Writes re-read and mutate under the
  state-file lock, after one elapsed-decay application.
- The existing expression-gain apply/restore endpoints are under the same
  write gate and revision check. They continue to share validation and mutation
  behavior with `/affect tune`.
- No calm, heat, reset, migration, raw expression-drive, trait, participant
  creation, sensitivity, or independent conflict-projection controls.
- Tuning values are bounded to `0.0` through `10.0`, and the shared service
  prevents unsupported fields from being changed.
- Errors are bounded and omit state-file contents and paths.
- Catalog pages are bounded and exact selection verifies parsed identifiers
  after sanitized path resolution.
- State values are parsed through the versioned domain model before rendering.
- Browser rendering uses text properties and never interpolates state as HTML.
- Polling is bounded, non-overlapping, and stops when the page unmounts.

## Relationship to `/affect state`

The existing public experimental command and this authenticated dashboard must
share one projection so their privacy behavior cannot drift. Once the
dashboard is validated, separately review whether `/affect state` should become
administrative-only or be removed before exposure to untrusted chat users.
