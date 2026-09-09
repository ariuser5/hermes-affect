# Privacy and retention

Temporary affective state is scoped to a Hermes profile and session. It is
stored separately from Hermes permanent memory and contains no raw transcript,
long quotation, or hidden chain-of-thought.

The MVP records only bounded state, relationship dimensions, audit metadata,
posture, revision timestamps, and the last processed turn identifier. State is
subject to configurable garbage collection; the initial documented default is
90 days for abandoned sessions.

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

Dynamic context returned from `pre_llm_call` may be represented in Hermes
session/API history depending on the installed Hermes version. The injected
summary is therefore deliberately short and never contains the complete JSON
state.

## Request-level privacy hardening

The MVP uses the public `pre_llm_call` surface because it is the compatibility
boundary currently covered by local fixtures. A future Hermes request-middleware
hook could attach internal guidance only while assembling one model request,
which may reduce the chance that the guidance becomes part of durable
session/API history. That approach also introduces a new version-specific
dependency and must be verified against the target runtime before adoption.

Until then, `shadow_mode`, conservative `expression_gain`, short guidance, and
the omission of numerical state or raw messages are the available privacy
controls. The plugin does not claim that the current hook guarantees
request-only visibility.

Administrative status/debug output is separate from normal response context.
Administrative commands must verify the configured user identity. A bot's
message is social influence, not administrative authority.

Any future public temperament signature must be opt-in and limited to coarse,
reviewed categories for playfulness, assertiveness, and social influence. It
must never publish private affect, relationship history, observed participant
style, influence estimates, or audit records.
