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

For a Docker deployment, inspect the existing persistent Hermes bind mount
before selecting the runtime path. Prefer a dedicated subdirectory of that
mount when ownership and backup boundaries are clear; otherwise use a separate
Docker volume. Do not use `tmpfs` for production state because it is lost on
container restart.

The plugin does not change Hermes memory settings. It does not call the memory
tool and does not write `MEMORY.md`, `USER.md`, skills, or external memory
providers.
