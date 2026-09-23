# Architecture

Hermes Affect is a general Python Hermes plugin. It is neither a memory
provider nor a context engine. Temporary state belongs to one profile and
conversation and is never written to permanent memory.

## Model v2: six traits and one expression gain

The six independently authored traits are reactivity, persistence, pride,
playfulness, assertiveness and receptiveness, each in [0,1], default .5.
The only ordinary tuning control is expression_gain in [0,10], default 1.
Optional topic sensitivities are separate from temperament. Operational
settings for storage, administration, retention and semantic classification
are also separate.

The machine-readable SOUL configuration is versioned. Missing fields use neutral
defaults; invalid recognized values produce an administrative warning and a
complete neutral fallback. Unknown fields are warned about and ignored.
Recognized v1 configurations retain their identity and values for migration;
they do not silently become neutral v2 configurations. SOUL prose is not used
to infer numeric traits.

The schema is schemas/session_affect.schema.json. For calibration commands,
presets, formula responsibilities and migration, see [calibration.md](calibration.md).

## Code layout

- plugin.py preserves the public hermes_affect.plugin:register entry point.
- domain/ contains affect state, event values, configuration values, dynamics,
  relationships, calculations and response-posture policy without Hermes or
  filesystem dependencies.
- application/session_runtime.py orchestrates session loading, classification,
  observation, state transitions, auditing and persistence.
- application/classification/deterministic/ contains rule-based event
  classification; application/classification/semantic/ contains semantic
  result validation and deterministic/semantic arbitration.
- application/commands.py and application/response/ handle commands and
  qualitative guidance rendered for the LLM.
- infrastructure/hermes/ registers Hermes callbacks and owns the auxiliary LLM
  provider call; infrastructure/persistence/ owns JSON state files, locking,
  atomic writes and garbage collection.
- infrastructure/configuration/ loads the structured session_affect section
  from SOUL.md.
- tools/calibration.py replays synthetic scenarios through the same runtime,
  using temporary storage and a fixed clock, and proposes read-only v1
  migration.
- application/inspection.py builds the bounded current-state projection shared
  by `/affect state` and the optional authenticated extension in `dashboard/`.

No private Hermes imports, live peer-state reads, mutable shared room files or
automatic LLM configuration extraction are required.

## Processing a turn

1. Load the profile/session snapshot. If the model/configuration is legacy,
   warn and skip affect processing without rewriting it.
2. Resolve configuration from the saved predisposition plus permitted session
   overrides. Current SOUL does not replace an existing session's temperament.
3. Check the last-turn duplicate guard and apply elapsed-time decay.
4. Classify a dominant event deterministically; optionally use the configured
   semantic auxiliary task to replace that candidate.
5. Resolve its target. A message to this bot may affect personal emotion and its
   relationship with the speaker. A resolved exchange between others updates
   this bot's observations and perceived atmosphere, not personal offense.
6. Match any configured topic phrases for a personally addressed event.
7. Apply event changes, record local observations and recompute conflict status.
8. Derive posture from the current participant/event, personal state and locally
   perceived atmosphere. Render guidance and write bounded audit changes.
9. Save state atomically; shadow mode suppresses guidance but preserves updates.

Deterministic classification intentionally chooses one dominant intent per
turn: verified moderation, repair/mediation, expressed distress, hostility,
then other social signals. This prevents duplicate impact from overlapping
regex matches. It is not clause-level mixed-intent understanding. Unresolved
group targets are ignored for personal offense; expressed frustration can
still be observed as a speaker signal. Deterministic rules remain limited
phrase matching and cannot reliably disambiguate all quotation, irony or intent.

## Derived quantities

Let r, p, h, a and o denote reactivity, pride, playfulness, assertiveness and
receptiveness. All are [0,1]. Let f(x) = .25 + .75*x.

- Ordinary event reaction = severity * f(r).
- Disrespect sensitivity = f(p), multiplied by an applicable topic sensitivity.
- Humor interpretation uses h, f(1-h) and observed humor compatibility.
- Credibility = (2 + relationship.trust + relationship.respect) / 4.
  A stranger starts at .5; credibility is local, not universal charisma.
- Social receptivity = o * credibility * (1 - .5 * unresolved_tension).
- Repair factor = f(social receptivity), so even the least receptive relationship
  has an ordinary repair path.
- Mischief = h * a * (1-o).
- Conflict avoidance = r * (1-a).
- Mediation tendency = o * a.
- Teasing sensitivity diagnostic = r * (p + 1-h) / 2.
- Atmosphere sensitivity = f((r + p + 1-a) / 3).

These are inspectable engineering heuristics. The teasing-sensitivity summary
is descriptive; the actual teasing transition also uses relationship history,
topic sensitivity, observed style and the shared event-family strength.
The model does not estimate a psychological diagnosis or another participant's
private personality.

Mood decays exponentially: factor = exp(-rate * elapsed_hours), where
rate = .2 + .8*(1-persistence). Relationship irritation/tension decays on
twice the mood timescale. Perceived atmosphere and expressed-distress estimates
also decay; directed social tension uses the relationship timescale.
Trust, respect, affinity and observed style change through evidence rather
than this short-term decay.

Expression drive = 1 - exp(-2 * expression_gain * intensity).
Intensity is the maximum of absolute valence, arousal, frustration, offense
and perceived atmosphere tension. Traits are not multiplied into expression
a second time. Wording tiers split at .2, .5 and .8. Magnitude never determines
emotional direction: positive excitement receives warm/playful guidance.
Default gain can reach the highest tier when intensity is sufficiently high.

## Event families and relationships

Praise/support share a positive step; jokes and teasing share a humor step.
Disagreement uses a smaller friction step and does not itself create personal
offense or unresolved personal conflict. Insults, provocation and status
challenges share a hostility step. Apology, reconciliation and mediation share
a repair step. Verified moderation has its own fixed intervention step.

Severity consistently scales ordinary event families. It is distinct from
classification confidence. Verified moderation deliberately ignores classifier
severity, credibility and temperament.

Trust/respect can soften an injury without eliminating it. Repeated unresolved
hostility increases sensitivity; ordinary repair depends on receptiveness and
the relationship. Observed playful style changes whether teasing is interpreted
as compatible banter or irritating friction. Similar playful temperaments can
cooperate; a proud, serious, reactive recipient may instead escalate or withdraw.
No compatibility score forces conflict without a triggering interaction.

The model retains valence, arousal, frustration and offense because they can
represent different histories. Relationships retain trust, affinity, irritation,
respect and unresolved tension. Some values are diagnostics or groundwork
rather than independent posture controls; do not interpret every stored field
as an additional authored parameter.

Conflict heat/status is projected from unresolved relationship tension after
updates and decay. A conflict is cleared below half a positive event step.
Posture also requires active personal frustration/offense; it considers the
current speaker instead of transferring personal retaliation to uninvolved
participants. Mood and rendered expression are likewise derived; persisted
posture denotes the last processed response, not a newly classified event.

## Perceived atmosphere and third-party awareness

Each bot owns its own atmosphere_tension, directed social_edges and limited
observed_participants estimates in its profile/session snapshot. Bots observing
the same exchange can disagree about its intensity. There is no objective
shared global atmosphere and no shared mutable group-state file.

Directed observations record speaker ID, recipient ID, perceived tension and
the latest event type. At most 64 directed edges and 64 expressed-distress
records are retained. Edge order reflects recent observation. Values decay and
repair signals can reduce both directions of an observed conflict.

For example, A may observe B teasing C and subsequently hear C say "stop teasing
me." A records B->C teasing and a local impression that C appears frustrated.
Teasing alone does not assert knowledge that C is frustrated. Guidance can
mention these bounded observations as fallible impressions, never access to
another bot's private state. Raw messages are not stored in those records.
Participant identifiers in guidance are bounded and JSON-encoded as data.

A receptive, assertive observer may mediate. A reactive, low-assertiveness
observer may withdraw or steer away. A resilient observer can remain engaged
through the same signals. Mischievous behavior arises from high playfulness
and assertiveness with low receptiveness, without a separate trolling knob.
It is expressed through optional cheeky teasing or provocative disagreement;
it is not a command to be hostile on every turn.

Awareness is limited to messages actually delivered to this bot's callbacks.
The plugin does not subscribe to an undocumented room-wide stream, inspect
other profiles' state files or silently import private peer temperament.
See [hermes-compatibility.md](hermes-compatibility.md) for integration limits.

## Classification, identity and topic sensitivity

Semantic classification is disabled by default and uses the explicit
hermes_affect_classifier auxiliary task when enabled. Hermes owns its provider
route and credentials. Input size, context length, timeout and output schema
remain bounded. Recursive callbacks are guarded.

High-confidence events addressed to this bot can affect it personally.
High-confidence events addressed to another known participant can update
local social observations. Unknown participants/targets are rejected.
Confident none suppresses keyword matches. Invalid/provider failure follows
the configured fallback, whose default is ignore. Verified moderation wins.

The adapter can use delivered target_id/recipient_id and is_group hints, or
an unambiguous participant vocative at the beginning of the message. Group
callers should supply known_participants and stable sender IDs. These are
optional boundary inputs covered by local fixtures, not a claim that every
Hermes release provides them.

Configured sensitivities match literal topic phrases in personally addressed
messages. No semantic topic inference is implied. The strongest matched topic
amplifies offense/teasing, and active topic avoidance refreshes each turn.

## Persistence, privacy and commands

State uses JSON per profile/session with atomic replacement and a per-file
write lock. Runtime state belongs outside source control. The storage schema
and affect model are versioned. Legacy files remain inspectable; v2 processing
requires a reviewed v2 configuration and explicit new-session/reset boundary.

New sessions snapshot the validated SOUL and its SHA-256. Process restart
preserves effective temperament. Compression clones a compatible parent's
bounded state. Affective reset does not reset the Hermes conversation.

The persisted last_turn_id prevents ordinary duplicate hook processing.
File writes do not provide transactional exactly-once processing across
crashes or a lock over the entire read/modify/write pipeline. Full retry and
concurrent-writer guarantees remain separate work.

Verified admin commands support status, explain, reset, calm, heat and
expression-only tune. The public experimental state [profile] command returns
a current snapshot, using that state's configuration, excluding social
observations, participant histories and audits. explain is administrative.

Injected guidance contains no numeric state or raw transcript. The public
pre_llm_call hook may retain guidance in API-bound conversation history;
there is no request-only privacy guarantee. See
[privacy-and-retention.md](privacy-and-retention.md).

The optional dashboard reuses this same current-state projection. Its thin
FastAPI adapter reads the newest valid state available to one Hermes container,
and its browser page polls through Hermes' authenticated plugin route. The
feature is independently gated by `HERMES_AFFECT_DASHBOARD`, defaults off,
and adds no listener or Docker port. All writes additionally require the
default-off `HERMES_AFFECT_DASHBOARD_CONTROLS` gate and are limited to exact
sessions: expression-gain tuning plus allowlisted affect, atmosphere, and
existing-participant relationship source values. Cross-container aggregation,
other mutation, and historical charts remain outside this design. See
[`../dashboard/README.md`](../dashboard/README.md).

## Deferred interests and conversational effort

The requested interests model is tracked in TODO.md, not implemented here.
It should distinguish liked, neutral, disliked and strongly avoided topics,
and separately consider repeated clarification, demonstrated understanding
and perceived conversational effort. A short "why?" alone should not be
treated as proof of bad intent. Context and temperament must mediate any
future frustration response.
