# Hermes compatibility contract

This document separates the adapter behavior covered by local tests from the
parts that still require inspection of the target Hermes installation.

## Target installation

The current deployment target is Hermes `0.20.2` with image tag
`v2026.8.16`. Read-only inspection of the running container recorded the
immutable image digest as
`sha256:f8f548d87d16634d1ad9e3777280f3f577ba2358703f04e18e74007ffd3621bf`.
The target is an ARM64 Raspberry Pi deployment.
The running container sets `HERMES_HOME=/opt/data`; this is the container-side
Hermes home, not a host or Compose path. The persistent deployment mount is
therefore the relevant location to inspect for profiles, `SOUL.md`, plugins,
and runtime state.

## Locally covered public surface

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
has no configured override. The target Hermes profile-home and effective
`SOUL.md` discovery rules still require deployment verification.
Environment fallback tests also cover `HERMES_HOME/SOUL.md` and
`HERMES_PROFILE`; these validate the adapter's local defaults, not the target
runtime's actual environment values.
The runtime directory also falls back to `HERMES_AFFECT_STATE_DIR` when the
context does not provide `state_dir`; local tests also verify that an explicit
context `state_dir` takes precedence over that environment fallback.
An incomplete session-start payload also skips both state initialization and
garbage collection, so it cannot clean up unrelated sessions accidentally.

## Target-verified public surface

Source inspection of the running Hermes `0.20.2` installation confirms that
the general plugin manager exposes `register_hook()` and `register_command()`.
Lifecycle dispatch invokes callbacks with keyword arguments and passes the
complete payload to callbacks that accept `**kwargs`.

The target `pre_llm_call` payload includes `session_id`, `task_id`, `turn_id`,
`user_message`, `conversation_history`, `is_first_turn`, `model`, `platform`,
`parent_session_id`, and `sender_id`. Hermes inserts returned plugin context
into the user message rather than the system prompt.

Target source inspection also confirms that SOUL loading is scoped to the
active agent home. The default profile reads `<HERMES_HOME>/SOUL.md`; a named
profile reads `<HERMES_HOME>/profiles/<profile-name>/SOUL.md`. The plugin should
therefore receive or derive the active profile home rather than assuming that
the process-wide Hermes home is always the effective SOUL location.

The target lifecycle payloads are also verified:

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

The target command contract is `handler(raw_args: str) -> str | None`; the
registered command name is normalized before dispatch. The adapter's existing
positional command test covers this calling convention.

## Not yet verified against the target runtime

The following remain deployment compatibility checks rather than assumptions
that should be hidden in the adapter:

- the authenticated sender identity field and how bot-originated messages are
  marked;
- profile-home discovery and the effective `SOUL.md` location;
- whether compression exposes `parent_session_id` and on which hook;
- whether injected context is retained in session/API history.

## Target verification worksheet

Complete this worksheet from the target Hermes installation using the
deployment's normal read-only inspection procedure. Keep deployment-specific
paths, credentials, and runtime state outside this source repository.

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

For each observed payload, record the exact field names and whether the value
is absent, null, or an empty string. Compare those observations with the local
fixture contract above before changing the adapter. Do not mark the related
TODO items complete based only on this worksheet; they require evidence from
the target runtime.

Until those checks are completed, the fake context tests are contract fixtures,
not proof of compatibility with a deployed Hermes process. No version-specific
adapter branch is currently needed; any future branch should remain at the
registration/payload boundary and be covered by a versioned fixture.
