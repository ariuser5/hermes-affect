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

Dynamic context returned from `pre_llm_call` may be represented in Hermes
session/API history depending on the installed Hermes version. The injected
summary is therefore deliberately short and never contains the complete JSON
state.

Administrative status/debug output is separate from normal response context.
Administrative commands must verify the configured user identity. A bot's
message is social influence, not administrative authority.
