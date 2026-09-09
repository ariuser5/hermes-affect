# Hermes compatibility contract

This document separates the adapter behavior covered by local tests from the
parts that still require inspection of the target Hermes installation.

## Target installation

The current deployment target is documented as Hermes `0.20.2` with image tag
`v2026.8.16`. The image digest and the running Pi version are not recorded in
this source repository yet. Recording those values requires read-only access
to the deployment environment.

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

## Not yet verified against the target runtime

The following remain deployment compatibility checks rather than assumptions
that should be hidden in the adapter:

- the exact Hermes hook payload names and callback timing;
- the authenticated sender identity field and how bot-originated messages are
  marked;
- the command callback argument shape supplied by `ctx.register_command()`;
- profile-home discovery and the effective `SOUL.md` location;
- whether compression exposes `parent_session_id` and on which hook;
- the image digest and running Hermes version.

Until those checks are completed, the fake context tests are contract fixtures,
not proof of compatibility with a deployed Hermes process. No version-specific
adapter branch is currently needed; any future branch should remain at the
registration/payload boundary and be covered by a versioned fixture.
