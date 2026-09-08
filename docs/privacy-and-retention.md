# Privacy and retention

Temporary affective state is scoped to a Hermes profile and session. It is
stored separately from Hermes permanent memory and contains no raw transcript,
long quotation, or hidden chain-of-thought.

The MVP records only bounded state, relationship dimensions, audit metadata,
posture, revision timestamps, and the last processed turn identifier. State is
subject to configurable garbage collection; the initial documented default is
90 days for abandoned sessions.

Dynamic context returned from `pre_llm_call` may be represented in Hermes
session/API history depending on the installed Hermes version. The injected
summary is therefore deliberately short and never contains the complete JSON
state.

Administrative status/debug output is separate from normal response context.
Administrative commands must verify the configured user identity. A bot's
message is social influence, not administrative authority.
