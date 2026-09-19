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

- Initial routes are `GET` only.
- No calm, heat, tune, reset, migration, or deletion controls.
- Errors are bounded and omit state-file contents and paths.
- State values are parsed through the versioned domain model before rendering.
- Browser rendering uses text properties and never interpolates state as HTML.
- Polling is bounded, non-overlapping, and stops when the page unmounts.

## Relationship to `/affect state`

The existing public experimental command and this authenticated dashboard must
share one projection so their privacy behavior cannot drift. Once the
dashboard is validated, separately review whether `/affect state` should become
administrative-only or be removed before exposure to untrusted chat users.

