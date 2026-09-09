# Architecture

`hermes-affect` is a general Python Hermes plugin. It is not a memory provider,
context engine, or skill-only mechanism.

The MVP keeps one JSON file per profile/session under a configurable runtime
directory. A lock file protects each state file, and writes use a temporary file
plus atomic replacement. Runtime state is not source code and must not be
committed.

The state contains bounded global affect, participant-specific relationships,
open conflict metadata, posture, bounded audit records, revision information,
and the last processed turn identifier. Audit records contain event type, rule,
posture, participant identifier, and changed dimensions with before/after
values. The state never stores raw transcripts, long quotations, or hidden
chain-of-thought.

## Lifecycle

1. `on_session_start` loads and validates the delimited `SOUL.md` section.
2. The plugin stores the SOUL hash and predisposition snapshot in new state.
3. `pre_llm_call` applies persistence-based decay, classifies clear
   deterministic events, applies interventions, derives posture, and injects a
   concise internal summary.
4. `post_llm_call` checkpoints bounded state only.
5. `on_session_reset` and a genuinely new Hermes session establish the relevant
   boundary; `/affect reset` resets only plugin state.

Response posture is derived from the latest clear event plus bounded current
state. The MVP can express mediation, reconciliation, topic steering, topic
avoidance, guarded/evasive/refusal behavior, counterattack, and pass guidance
through the internal context summary. Separate response-routing hooks are not
assumed until the target Hermes version is verified.

When `shadow_mode` is enabled, the plugin performs the same state, observation,
and audit updates but returns no affective context to Hermes. This makes a
test profile observable without changing model prompting.

The `tuning.expression_gain` setting controls context expression separately
from event escalation: zero suppresses affective context while retaining state
updates, low values request restrained guidance, and high values make the
current posture more explicit. Numerical state is never included in the
injected text.

Verified administrators may use `/affect tune` to set a session-scoped override
for `expression_gain`, `escalation_gain`, or `repair_gain` within `[0, 10]`.
Overrides are persisted with plugin state, do not alter `SOUL.md`, and cannot
change core traits or Hermes configuration.

When Hermes supplies `parent_session_id` for compression, a new plugin session
clones the bounded parent snapshot and records the lineage while leaving the
parent file unchanged. Richer middleware, full retry idempotency, and
coordinated group state remain follow-up work.

## Core temperament model

The stable configuration has seven independent traits, each in the inclusive
range `[0, 1]`:

- `reactivity`: how quickly and strongly affect changes after an event.
- `persistence`: how slowly frustration, offense, and relational tension decay.
- `pride`: sensitivity to disrespect, embarrassment, status, and competence
  challenges.
- `playfulness`: how readily ambiguity is interpreted as banter or humor.
- `assertiveness`: tendency to confront, intervene, lead, resist, or express
  disagreement instead of withdrawing.
- `social_influence`: how much this participant affects others.
- `receptiveness`: how much this participant is affected by trusted, respected,
  or influential participants.

These are stable predispositions, not mutable session state. Runtime state
contains mood and relationships separately. `expression_gain`,
`escalation_gain`, and `repair_gain` live under `tuning` and control how
strongly the engine expresses, escalates, and repairs events. They are bounded
for numeric stability without imposing a low global influence ceiling.

The engine derives narrower concepts instead of adding overlapping knobs:
leadership tendency is mainly `assertiveness × social_influence`; effective
receptiveness is `listener.receptiveness × relationship respect ×
speaker.social_influence`; persistence and current state derive behavioral
stability and lingering tension. Free-form style guidance remains
outside the numeric schema and can be amplified or suppressed through posture.

## Social influence

`LayeredTraitResolver` resolves a public temperament signature when one is
available, otherwise observed behavior/history, and finally neutral defaults.
The resolver is deliberately local and has no shared mutable group state.
Public signatures should remain limited to non-sensitive traits such as
playfulness, assertiveness, and social influence.

### Future public temperament signature

The future public signature is intentionally narrower than the private
configuration. It may expose only an explicit signature version and coarse
categories for `playfulness`, `assertiveness`, and `social_influence`. It must
be opt-in, self-declared or administrator-reviewed, and treated as descriptive
context rather than permission or authority. It must not expose pride,
reactivity, persistence, receptiveness, current mood, relationship history,
conflict state, observed-style estimates, or audit records. Automatic
publication and automatic LLM-generated calibration are out of scope until a
human review flow exists.

The policy returns inspectable factors plus persuasion, calming, and
conflict-risk decisions. An influential bot can calm a receptive participant;
a low-receptive participant can resist; a proud bot can challenge a leader; a
playful influential participant can turn ambiguity into banter; and a serious
participant can become irritated by the same joke. Social influence never
grants administrative authority. The runtime stores bounded, transcript-free
style estimates (`supportive`, `playful`, `confrontational`, and `cooperative`)
on each participant relationship, plus an exponentially smoothed influence
estimate and observation count. These are local observations, not public
temperament claims, and unknown configuration fields are warned about and
ignored without changing recognized values.
