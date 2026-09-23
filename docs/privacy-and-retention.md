# Privacy and retention

Temporary affective state is scoped to a Hermes profile and session. It is
stored separately from Hermes permanent memory and contains no raw transcript,
long quotation, or hidden chain-of-thought.

When semantic classification is enabled, the current bounded message and the
configured small context window are sent to the active Hermes provider for the
secondary structured call. The plugin does not persist those inputs, provider
credentials, raw model output, or a classifier prompt. Only validated event
metadata that leads to an affect update may appear in bounded audit records.
Disable the feature or use `shadow_mode` when this provider call is not
acceptable for a deployment's privacy review.

The MVP records only bounded state, relationship dimensions, audit metadata,
posture, revision timestamps, and the last processed turn identifier. State is
subject to configurable garbage collection; the initial documented default is
90 days for abandoned sessions.

Model v2 additionally stores the bot's own perceived atmosphere, at most 64
directed social edges and 64 expressed-distress estimates. These are fallible
local impressions from delivered events, not access to others' private
emotions or a shared global room state. They retain identifiers, bounded
numeric values and event labels, never raw messages. Short qualitative
impressions may enter injected guidance and therefore API-bound history.
The public state snapshot exposes perceived atmosphere but excludes these
third-party observations. Authenticated `/affect explain` includes them.

Garbage collection runs on session startup and examines only valid state JSON
files older than the configured threshold. It acquires the per-file lock before
removing a file and skips files with an active or stale lock. A stale lock is
not reclaimed automatically; after confirming that no Hermes process is using
the state, an administrator may remove the lock through the deployment's
normal runtime-state maintenance procedure.

Atomic replacement prevents a normal interrupted write from leaving a partial
state file. Malformed state files are skipped and should be reviewed through
administrative logs rather than deleted automatically.

Duplicate delivery is guarded by the persisted `last_turn_id` after a
successful checkpoint. This is not full crash-safe exactly-once processing: a
process failure between event application and the durable checkpoint can allow
Hermes to redeliver the turn and the event to be applied again. The MVP keeps
this limitation explicit rather than pretending that the file lock closes the
transactional window.

The [official Hermes hook reference](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md)
documents that `pre_llm_call` context is appended to the current user message
and that Hermes may persist the exact API-bound message in its `api_content`
sidecar. The plugin therefore treats injected guidance as potentially visible
in session/API history on supported runtimes; it never relies on this hook for
request-only visibility. The injected summary is deliberately short and never
contains the complete JSON state.

## Request-level privacy hardening

The MVP uses the public `pre_llm_call` surface because it is the compatibility
boundary covered by local fixtures. A future Hermes request-middleware hook
could attach internal guidance only while assembling one model request, which
may reduce the chance that the guidance becomes part of durable session/API
history. That approach introduces another compatibility dependency and should
be adopted only when the documented public contract and compatibility fixtures
support it.

Until then, `shadow_mode`, conservative `expression_gain`, short guidance, and
the omission of numerical state or raw messages are the available privacy
controls. A deployment that requires request-only visibility must validate a
documented request-level hook separately before enabling that design.

Administrative status and mutating commands remain separate from normal
response context and must verify the configured user identity. The experimental
read-only `/affect state [profile]` command is intentionally public during the
current development phase: it returns the selected profile's newest valid,
bounded current-state snapshot plus the derived expression drive. It can expose
numerical affect, current relationships, active sensitivities, open conflicts,
and tuning overrides, but excludes audit records and observed-participant
history. The state model does not contain raw messages or classifier prompts.
Disable or remove this public diagnostic before exposing the command to
untrusted users.

## Optional authenticated dashboard

`HERMES_AFFECT_DASHBOARD` is a separate default-off disclosure boundary. When
enabled, the native Hermes dashboard extension serves the same bounded
current-state projection behind Hermes' existing dashboard authentication. It
adds no public listener. A second default-off gate,
`HERMES_AFFECT_DASHBOARD_CONTROLS`, is required for all dashboard mutations,
including `expression_gain` apply/restore and the allowlisted exact-session
manual source controls. Mutations do not modify SOUL configuration or other
sessions. The projection includes profile
and session identifiers, numerical affect, relationships, sensitivities,
conflicts, and tuning, so dashboard credentials must be treated as access to
private interpersonal state.

The response excludes raw messages, audits, directed social observations,
expressed-distress estimates, SOUL content and hashes, saved predisposition,
classifier material, credentials, paths, and stack traces. The frontend uses
text rendering rather than HTML interpolation. Disabling the flag returns
`404` and prevents tab registration while leaving affect processing and state
retention unchanged. See
[`../dashboard/docs/privacy-and-security.md`](../dashboard/docs/privacy-and-security.md).

Any future public temperament signature must be opt-in and limited to coarse,
reviewed categories such as playfulness and assertiveness. It
must never publish private affect, relationship history, observed participant
style, influence estimates, or audit records.
