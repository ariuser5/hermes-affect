# Installation and deployment

The source repository is independent from any particular infrastructure or
deployment repository. A deployment may install a pinned commit through the
Hermes plugin manager or mount the plugin into the configured user-plugin path.

General installation shape:

```text
<hermes-home>/plugins/hermes-affect/
```

Enable the plugin explicitly in Hermes configuration. Keep runtime state in a
separate persistent directory, for example:

```text
<runtime-root>/hermes-affect/<profile-id>/sessions/<session-id>.json
```

For a test profile, set the plugin's boolean `shadow_mode` setting to `true`.
The plugin will update and persist affect state while suppressing affective
context injection. Leave it disabled for normal context injection.

Expression strength is configured in the `session_affect.tuning` section of
`SOUL.md` with `expression_gain` from `0` through `10`. A value of `0` keeps
state updates enabled but suppresses affective context; the neutral default is
`1`.

The plugin performs abandoned-state cleanup on session startup. The default
retention threshold is 90 days; override it with the numeric plugin setting
`state_gc_days`. Cleanup skips the active session, malformed state files, and
files whose lock cannot be acquired. It does not reclaim stale locks
automatically.

For a Docker deployment, inspect the existing persistent Hermes bind mount
before selecting the runtime path. Prefer a dedicated subdirectory of that
mount when ownership and backup boundaries are clear; otherwise use a separate
Docker volume. Do not use `tmpfs` for production state because it is lost on
container restart.

The plugin does not change Hermes memory settings. It does not call the memory
tool and does not write `MEMORY.md`, `USER.md`, skills, or external memory
providers.
