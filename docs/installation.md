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

Semantic classification is opt-in. A conservative test configuration is:

```yaml
plugins:
  enabled:
    - hermes-affect
  entries:
    hermes-affect:
      settings:
        semantic_classifier:
          enabled: true
          mode: always
          min_confidence: 0.85
          timeout_seconds: 3
          max_message_chars: 1200
          max_context_messages: 2
          fallback: ignore
        bot_name: lab-a
        bot_aliases: ["lab a"]
        shadow_mode: true
```

The classifier registers a plugin-owned auxiliary task. Configure its provider
at the top level of Hermes' `config.yaml`; for a deployment authenticated with
Codex OAuth, use:

```yaml
auxiliary:
  hermes_affect_classifier:
    provider: codex
```

The plugin does not read or store provider credentials. `fallback: deterministic`
is available as an explicit compatibility mode, while `ignore` is the safe
group-chat default. The configuration accepts `bot_name`,
`bot_aliases`, and known participant fields from the callback or plugin
settings so target matching can distinguish this bot from another bot in the
room.

The local fake-Hermes rollout smoke test exercises this operator flow without
calling a real model:

```bash
python -m unittest \
  tests.test_plugin_adapter.PluginAdapterTests.test_local_shadow_rollout_exposes_safe_status_and_audit_output
```

It verifies that shadow mode records bounded audit data, keeps response context
suppressed, and exposes only coarse session status to an authenticated admin.

After that passes, the conservative normal-injection smoke test verifies that
`expression_gain: 1` produces internal guidance while relationships and a
verified moderation intervention are still persisted:

```bash
python -m unittest \
  tests.test_plugin_adapter.PluginAdapterTests.test_local_conservative_injection_covers_relationships_and_moderation
```

Expression strength is configured in the `session_affect.tuning` section of
`SOUL.md` with `expression_gain` from `0` through `10`. It controls the
curvature of a smooth runtime expression drive derived from current affect and
temperament, so expression can intensify as state accumulates even when the
configured gain is below `1`. A value of `0` keeps state updates enabled but
suppresses affective context; the neutral default is `1`.

An administrator can temporarily override one of the three tuning values for
the active plugin session with `/affect tune <field> <value>`. Only the three
tuning fields are accepted; core traits and `SOUL.md` are not modified.

During development, `/affect state [profile]` returns the selected profile's
current affect snapshot, including mood, posture, numerical affect, current
relationships, and derived `expression_drive`. It intentionally omits audit
records and participant history from the response. This diagnostic is public
only for the current experiment and should be removed or protected before
exposing the bot to untrusted users.

The plugin reads numeric affect configuration only from the explicitly
delimited `session_affect` YAML section in `SOUL.md`. It does not ask an LLM to
extract settings from the surrounding persona prose. Any future calibration
tool must produce a reviewable proposal and require administrator approval
before changing configuration; automatic calibration is not enabled.

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

## Pinning and rollback

Install the plugin from a full immutable Git commit SHA, not from `main`, a
mutable branch, or an unpinned moving tag. Record the active SHA alongside the
deployment configuration so the source can be identified before an upgrade.

Before upgrading, preserve both the active plugin SHA and a restricted backup
of the runtime state directory. Source rollback and state rollback are separate
operations:

1. Restore the previous plugin commit through the deployment's normal install
   or mount mechanism.
2. Keep the runtime state directory unchanged initially and restart Hermes
   through the normal deployment procedure.
3. If the previous plugin cannot read the state because of a schema boundary,
   stop and restore the matching state backup for that plugin version; do not
   delete state files to make startup succeed.
4. Start with `shadow_mode` enabled and inspect administrative status before
   returning to normal context injection.

Enable semantic classification only after the local fake-Hermes tests pass.
Inspect classifier metadata and bounded audit records for direct insults,
other-bot targets, quoted insults, jokes, apologies, ordinary statements, and
ambiguous targets. A real Hermes gateway/profile smoke test remains a separate
deployment validation step because this source repository does not run or
modify a deployment.

Keep source and state backups access-controlled and outside Git. The repository
does not perform deployment, restart Hermes, or restore runtime state
automatically.

The plugin does not change Hermes memory settings. It does not call the memory
tool and does not write `MEMORY.md`, `USER.md`, skills, or external memory
providers.
