# Hermes Affect implementation plan

This is the execution checklist for the `hermes-affect` Hermes Agent plugin.
Detailed design belongs in `docs/architecture.md`; deployment-specific
instructions belong in the infrastructure repository that runs Hermes.

## Phase 0 — repository and CI baseline

- [x] Create the standalone plugin scaffold.
- [x] Add the general Hermes plugin adapter and manifest.
- [x] Add unit tests, packaging metadata, documentation, and CI.
- [x] Commit the Ruff fixes and manual-only workflow change.
- [x] Push the CI fix commit to `main`.
- [ ] Trigger CI manually from `main`.
- [ ] Confirm every Python matrix job passes before beginning runtime work.

Acceptance criteria:

- `pytest` passes on every supported Python version.
- `ruff check .` passes.
- CI runs only through `workflow_dispatch`.
- No deployment repository or running Hermes configuration is changed.

## Design revision — compact seven-trait model

- [x] Replace overlapping core fields with reactivity, persistence, pride,
  playfulness, assertiveness, social influence, and receptiveness.
- [x] Move expression, escalation, and repair controls under `tuning`.
- [x] Add the JSON Schema authoring reference and update the example SOUL.
- [x] Derive leadership, receptiveness, humor interpretation, and persistence
  behaviors instead of storing duplicate traits.
- [x] Warn about unknown fields without silently reinterpreting them.
- [x] Add boundary, fallback, derivation, decay, tuning, and style-separation
  tests.

Acceptance criteria:

- The runtime and authoring schema expose exactly seven core traits.
- Missing values use neutral defaults; invalid recognized values use a complete
  neutral fallback with an administrative warning.
- Unknown fields do not silently change behavior.

## Phase 1 — freeze the Hermes compatibility contract

- [ ] Record the target image tag and digest used by the Docker deployment.
- [ ] Record the running Hermes version from the Pi using read-only commands.
- [ ] Verify the target version's general-plugin registration contract.
- [ ] Verify callback payloads for `pre_llm_call`, `post_llm_call`,
  `on_session_start`, `on_session_end`, `on_session_finalize`, and
  `on_session_reset`.
- [ ] Verify `ctx.register_command()` callback arguments.
- [ ] Verify profile-home and `SOUL.md` discovery behavior.
- [ ] Verify how compression exposes `parent_session_id`.
- [x] Add a fake Hermes context fixture covering the agreed callback shapes.
- [x] Document the current adapter contract and any version-specific code.

Acceptance criteria:

- The plugin can register without importing private Hermes internals.
- Hook payload assumptions are covered by tests.
- Compatibility uncertainty is documented instead of hidden behind broad
  exception handling.

## Phase 2 — SOUL configuration and initialization

- [x] Define the delimited `session_affect` YAML convention.
- [x] Define neutral defaults for all seven traits and tuning values.
- [x] Validate schema version, types, numeric ranges, and sensitivities.
- [x] Fall back safely when the section is missing or invalid.
- [x] Emit administrative warnings for invalid configuration.
- [x] Store the SOUL SHA-256 hash and predisposition snapshot in session state.
- [x] Add fixtures for missing, valid, partially specified, and invalid SOULs.
- [ ] Confirm free-form SOUL prose is never sent to an LLM for configuration
  extraction during session startup.
- [ ] Document the future calibration tool and its mandatory review step.

Acceptance criteria:

- A malformed SOUL section cannot interrupt a conversation.
- A new session records exactly the configuration used to initialize it.
- Existing session state is not silently reinitialized after a process restart.

## Phase 3 — durable session state

- [x] Define bounded global state and participant relationship models.
- [x] Use one JSON file per profile/session.
- [x] Use one lock file per state file.
- [x] Use atomic temporary-file replacement.
- [x] Keep runtime state outside the source repository.
- [x] Add a duplicate-processing guard using `last_turn_id`.
- [x] Add configurable abandoned-state garbage collection with a 90-day
  initial default.
- [x] Add restart tests that resume an existing session without resetting it.
- [x] Add explicit tests for profile and session path isolation.
- [x] Document stale-lock and crash-recovery limitations.
- [x] Add a safe state schema version boundary.

Acceptance criteria:

- A container restart preserves state for a resumable Hermes session.
- A genuinely new Hermes session gets new affective state.
- No raw transcript, long quotation, or hidden chain-of-thought is persisted.
- No shared mutable group-state file exists in the MVP.

## Phase 4 — affective dynamics and event handling

- [x] Add deterministic event classification interfaces.
- [x] Cover praise, support, jokes, teasing, insults, disagreement, apology,
  reconciliation, moderation, mediation, provocation, topic steering, and
  leadership challenges.
- [x] Add persistence-based emotional decay.
- [x] Add independent escalation, expression, and repair tuning gains.
- [x] Activate topic sensitivities without adding another core trait.
- [x] Allow rapid escalation, lingering tension, and reconciliation.
- [x] Add active sensitivity activation and topic matching.
- [x] Add bounded audit records containing event type, affected dimensions,
  old/new values, posture, and rule name.
- [x] Add tests for repeated teasing, high-pride escalation, suppressed
  conflict, sudden reconciliation, and incompatible temperaments.

Acceptance criteria:

- Similar messages can produce different effects based on current state and
  relationship history.
- Numerical bounds are enforced without imposing an artificially weak global
  influence cap.
- Audit output never records hidden reasoning.

## Phase 5 — participant relationships and social influence

- [x] Add `ParticipantTraitResolver`.
- [x] Support `bot:<profile-id>`, `user:<platform-user-id>`, and stable custom
  participant identifiers.
- [x] Use neutral traits for unknown participants.
- [x] Model influence through separate inspectable factors.
- [x] Persist observed participant style and influence estimates.
- [x] Add tests for respected leaders, low-receptive resistance, leadership
  challenges, bot-to-bot conflict, and bot-to-user relationships.
- [x] Document a future limited public temperament signature.
- [ ] Do not implement shared mutable group atmosphere in the MVP.

Acceptance criteria:

- Social influence is never treated as administrative authority.
- Respect lowers conflict probability without making conflict impossible.
- Pride, reactivity, tension, and incompatible temperaments can overcome
  respect.

## Phase 6 — response posture and context injection

- [x] Derive normal, warm, playful, guarded, terse, and conflict postures.
- [x] Keep numerical state out of ordinary model context.
- [x] Mark injected material as internal guidance.
- [x] Add evasive, topic-avoidance, refusal, counterattack, mediation, topic
  steering, and `pass` behaviors where the Hermes surface supports them.
- [x] Add shadow mode that updates/logs state without injecting context.
- [x] Add configurable expression strength.
- [ ] Confirm whether injected context appears in session/API history for the
  target Hermes version.
- [ ] Evaluate request middleware as a later privacy-hardening option.

Acceptance criteria:

- The model is not normally prompted to narrate affective mechanics.
- Shadow mode is safe to inspect in a real test profile.
- Strong state can produce clearly observable behavior when configured to do so.

## Phase 7 — user and bot interventions

- [x] Register the `/affect` command surface.
- [x] Implement `/affect status` as administrative debug output.
- [x] Implement `/affect reset` without changing Hermes session state.
- [x] Implement `/affect calm`.
- [x] Implement `/affect heat`.
- [ ] Define reviewed behavior for `/affect tune`.
- [ ] Verify sender identity using Hermes-provided authenticated identity data.
- [ ] Ensure bots cannot imitate verified-user administrative authority.
- [ ] Add natural-language moderation tests for calm, stop, continue, and
  lower-tone interventions.
- [ ] Add bot mediation and bot provocation tests.

Acceptance criteria:

- Administrative commands affect only plugin state.
- Unverified or bot-originated commands are rejected.
- Natural interventions use social/administrative authority appropriately.

## Phase 8 — lifecycle, compression, and recovery

- [ ] Implement new-session initialization and affect-only reset semantics.
- [ ] Preserve continuity when Hermes exposes `parent_session_id` after
  compression.
- [ ] Add duplicate `turn_id` tests for retries and repeated hook delivery.
- [ ] Add successful-turn checkpoint tests.
- [ ] Document incomplete retry/crash idempotency as an MVP limitation.
- [ ] Add lifecycle tests for process restart, `/reset`, `/new`, finalization,
  and compression continuation.

Acceptance criteria:

- `/affect reset` does not create or destroy a Hermes conversation session.
- `/reset` and `/new` create new affective session boundaries.
- Compression continuation does not accidentally reset affect.

## Phase 9 — rollout

- [ ] Run one test profile in shadow mode.
- [ ] Inspect administrative state/audit output.
- [ ] Enable normal injection with a conservative test expression gain.
- [ ] Validate user relationships and moderation.
- [ ] Simulate multiple bots entirely in unit tests.
- [ ] Confirm persistent runtime path and permissions in the Docker deployment.
- [ ] Run one real two-bot group only after single-bot behavior is stable.
- [ ] Pin the deployed plugin to an immutable commit.
- [ ] Add rollback instructions for the plugin source and runtime state.

Deployment gate:

- No Pi command is run automatically by this repository.
- No Hermes permanent-memory setting is changed automatically.
- No source or runtime data is placed in Git.
- Deployment changes are reviewed separately from plugin implementation.

## Explicit MVP non-goals

- SQLite persistence transition.
- Complete retry and crash-recovery idempotency.
- Public temperament-signature discovery.
- Shared mutable group atmosphere.
- Coordinated group-wide reset.
- Distributed multi-machine affect state.
- Automatic LLM classification for every message.
- Automatic SOUL calibration without human review.
- Visualization and history tools.

## Future roadmap

When the MVP is stable, evaluate SQLite or another transactional/event-based
store, safe state-schema evolution, limited public temperament signatures, group
atmosphere with clear ownership, coordinated room resets, distributed groups,
optional structured LLM classification, and tools for visualizing relationship
and influence changes over time.
