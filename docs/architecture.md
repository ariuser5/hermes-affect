# Architecture

`hermes-affect` is a general Python Hermes plugin. It is not a memory provider,
context engine, or skill-only mechanism.

The MVP keeps one JSON file per profile/session under a configurable runtime
directory. A lock file protects each state file, and writes use a temporary file
plus atomic replacement. Runtime state is not source code and must not be
committed.

The state contains bounded global affect, participant-specific relationships,
open conflict metadata, posture, revision information, and the last processed
turn identifier. It never stores raw transcripts, long quotations, or hidden
chain-of-thought.

## Lifecycle

1. `on_session_start` loads and validates the delimited `SOUL.md` section.
2. The plugin stores the SOUL hash and predisposition snapshot in new state.
3. `pre_llm_call` applies decay, classifies clear deterministic events, applies
   interventions, derives posture, and injects a concise internal summary.
4. `post_llm_call` checkpoints bounded state only.
5. `on_session_reset` and a genuinely new Hermes session establish the relevant
   boundary; `/affect reset` resets only plugin state.

Compression lineage handling through `parent_session_id`, richer middleware,
full retry idempotency, and coordinated group state remain follow-up work.

## Social influence

`ParticipantTraitResolver` deliberately separates the speaker's influence and
leadership from the listener's deference, respect, trust, tension, and
temperament. The policy returns inspectable factors plus persuasion, calming,
and conflict-risk decisions. It does not collapse all social behavior into one
unconditional multiplier.

Unknown participants use neutral traits. The MVP has no shared mutable group
state document.
