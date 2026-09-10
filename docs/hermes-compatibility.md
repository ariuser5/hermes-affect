# Hermes compatibility contract

This document defines the portable public Hermes plugin contract used by the
adapter. It deliberately does not make one Hermes image or deployment the
minimum supported version. Newest Hermes releases have priority; older
versions remain candidates when they preserve this documented contract.

The canonical references are the [Hermes plugin guide](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/plugins.md)
and the [Hermes hook reference](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md).
They define the public registration methods, accepted hook names, callback
signatures, timing, return handling, and privacy notes used here.

## Compatibility strategy

The implementation uses only public general-plugin registration methods and
keeps all callbacks at the public keyword-payload boundary. Additive fields
are ignored by the adapter, and missing optional fields use safe defaults.
Version-specific branches belong at this boundary only when a public Hermes
release documents a real contract difference and a versioned fixture covers it.

Local fake-Hermes tests are the primary development contract. A real Hermes
profile smoke test is a release-validation activity, not a requirement to
reverse-engineer or hard-code one deployment.

## Documented public surface

The plugin uses only the public registration methods represented by the fake
context fixture:

```python
ctx.register_hook(name, callback)
ctx.register_command(name, callback, description)
```

The callbacks accept keyword payloads. The adapter currently recognizes these
fields:

- session identity: `profile_id` or `profile_name`, and `session_id`
- turn identity: optional `turn_id`
- message identity: optional `user_message`, `sender_id`, `sender_kind`, and
  `verified_user`
- configuration overrides: `state_dir`, `soul_path`, `state_gc_days`,
  `shadow_mode`, and `admin_user_ids`
- command arguments: `args_raw`, `args`, or a positional first argument
- reset boundary: optional `new_session_id` or `replacement_session_id`

Lifecycle hooks are registered for `on_session_start`, `pre_llm_call`,
`post_llm_call`, `on_session_end`, `on_session_reset`, and
`on_session_finalize`.

The adapter has no private Hermes imports and does not require Hermes internals
at import time. Missing optional fields use the documented neutral/default
behavior; a missing `session_id` means no state is loaded or created.
Local adapter tests exercise both command argument aliases (`args_raw` and
`args`) and both reset replacement aliases (`new_session_id` and
`replacement_session_id`). These are fixture coverage points, not confirmation
that the target Hermes version uses either spelling.

`session_id` is the state-creation boundary: when it is absent, lifecycle and
model hooks return without loading or creating affect state, and an
administrative command reports that no active session was supplied. Local tests
exercise this behavior across startup, model, checkpoint, reset, finalize, and
end hooks.
The local fixture also covers a callback-provided `soul_path` when the context
has no configured override. The runtime must provide the effective profile
home or SOUL path; a release smoke test can verify that integration without
making one host layout part of the plugin contract.
Environment fallback tests also cover `HERMES_HOME/SOUL.md` and
`HERMES_PROFILE`; these validate the adapter's local defaults, not the target
runtime's actual environment values.
The runtime directory also falls back to `HERMES_AFFECT_STATE_DIR` when the
context does not provide `state_dir`; local tests also verify that an explicit
context `state_dir` takes precedence over that environment fallback.
An incomplete session-start payload also skips both state initialization and
garbage collection, so it cannot clean up unrelated sessions accidentally.

## Compatibility observations

The following observations were collected from one Hermes `0.20.2` deployment.
They are useful validation evidence, but are not a version pin or the
definition of the supported range.

The observed general plugin manager exposes `register_hook()` and
`register_command()`. Lifecycle dispatch invokes callbacks with keyword
arguments and passes the complete payload to callbacks that accept `**kwargs`.

The observed `pre_llm_call` payload includes `session_id`, `task_id`, `turn_id`,
`user_message`, `conversation_history`, `is_first_turn`, `model`, `platform`,
`parent_session_id`, and `sender_id`. Hermes inserts returned plugin context
into the user message rather than the system prompt.

The observed runtime also confirms that SOUL loading is scoped to the
active agent home. The default profile reads `<HERMES_HOME>/SOUL.md`; a named
profile reads `<HERMES_HOME>/profiles/<profile-name>/SOUL.md`. The plugin should
therefore receive or derive the active profile home rather than assuming that
the process-wide Hermes home is always the effective SOUL location.

The observed lifecycle payloads are:

- `on_session_start` fires for a new session with `session_id`, `model`, and
  `platform`.
- `post_llm_call` fires after a non-interrupted final response with session,
  task, turn, user-message, assistant-response, history, model, and platform
  fields.
- `on_session_end` fires at the end of each conversation run with session,
  task, turn, completion, failure, interruption, exit-reason, model, and
  platform fields.
- `on_session_reset` fires for `/new` with the old/new session IDs, platform,
  and reset reason.
- `on_session_finalize` accepts `session_id`, `platform`, `reason`, and
  optional extra keyword fields.

The observed command contract is `handler(raw_args: str) -> str | None`; the
registered command name is normalized before dispatch. The adapter's existing
positional command test covers this calling convention.

The public raw-only command contract does not carry authenticated sender
identity. The adapter therefore fails closed for administrative commands when
no identity metadata is available. The local fixture also exercises an
identity-enriched call so a future documented Hermes context extension can be
supported without trusting identity values embedded in `raw_args`.

## Compatibility checks still needed

The following are release or deployment checks rather than assumptions that
should be hidden in the portable adapter:

- the authenticated sender identity field and how bot-originated messages are
  marked;
- whether compression exposes `parent_session_id` and on which hook;
- whether injected context is retained in session/API history.

## Optional deployment evidence worksheet

Use this worksheet when validating a particular Hermes release or deployment.
Keep deployment-specific paths, credentials, and runtime state outside this
source repository. These values document an observation; they do not define
the plugin's supported version range.

```text
target image reference: nousresearch/hermes-agent:v2026.8.16
target image digest: sha256:f8f548d87d16634d1ad9e3777280f3f577ba2358703f04e18e74007ffd3621bf
running Hermes version: 0.20.2
container Hermes home: /opt/data (from HERMES_HOME)
registration method and result: register_hook() and register_command() exposed by the general plugin manager
observed hook names and callback timing: lifecycle hooks are dispatched with keyword payloads at the documented session and turn boundaries
observed command callback arguments: handler(raw_args: str) -> str | None
effective profile-home and SOUL.md path: default <HERMES_HOME>/SOUL.md; named <HERMES_HOME>/profiles/<profile-name>/SOUL.md
compression hook and parent_session_id behavior:
evidence location or command output summary:
```

For each observed payload, record exact field names and whether values are
absent, null, or empty. Compare them with the public fixture contract before
changing the adapter. Any version-specific branch must remain at the
registration/payload boundary and be covered by a versioned fixture.
