# Hermes Affect implementation plan

This is the execution checklist for the `hermes-affect` Hermes Agent plugin.
Detailed design belongs in `docs/architecture.md`; deployment-specific
instructions belong in the infrastructure repository that runs Hermes.

## Current model revision — six traits, calibration and local social perception

The completed v1 milestones below are historical records. This section and
the current architecture supersede the seven-trait, three-gain and disconnected
influence designs; old checkmarks do not assert those old interfaces remain.

- [x] Introduce v2 with six traits and one expression gain.
- [x] Derive escalation, repair, mischief, conflict avoidance and mediation.
- [x] Connect relationship trust/respect, observed style and receptiveness to events.
- [x] Separate positive expression from conflict wording; remove duplicate temperament weighting.
- [x] Resolve effective configuration from the persisted session snapshot.
- [x] Normalize dominant event intent and verified moderation precedence.
- [x] Connect literal topic sensitivity matching and refresh active topics.
- [x] Derive conflict records from current tension and scope retaliation to the speaker.
- [x] Add per-bot perceived atmosphere and bounded directed third-party observations.
- [x] Distinguish observed teasing from evidence of expressed participant frustration.
- [x] Generate teasing, withdrawal, confrontation and mediation guidance from temperament.
- [x] Add an offline runtime scenario runner, preset comparison and single-trait sweeps.
- [x] Add authenticated explanation diagnostics and explicit read-only migration proposals.
- [ ] Validate actual generated replies and group message delivery in a real Hermes profile.
- [ ] Evaluate more communication patterns with scenario evidence before adding model dimensions.

## Future interests and conversational effort — requested 2026-09-17

- [ ] Model per-bot topic preferences: interested, neutral, disliked and strongly avoided.
- [ ] Let discussion of liked topics improve perceived atmosphere and relationships.
- [ ] Let unwanted-topic requests increase frustration, with reactions moderated by temperament.
- [ ] Track repeated clarification and perceived conversational effort without raw transcripts.
- [ ] Distinguish terse repeated prompts such as “why?” from clarification that demonstrates
      understanding and identifies a specific missing point.
- [ ] Treat brevity or confusion as ambiguous evidence, not proof of hostility or stubbornness.
- [ ] Model escalation, avoidance, patient explanation and repair according to temperament
      and context; ensure ordinary questions do not automatically become personal insults.
- [ ] Design optional topic representations, privacy bounds and calibration scenarios before
      implementing this feature. No topic-interest or clarification-frustration behavior is
      implemented by the current refactor.

## Optional authenticated affect dashboard — started 2026-09-19

- [x] Isolate the feature under `dashboard/` with its own durable plan and
      documentation.
- [x] Extract one bounded safe-state projection shared with `/affect state`.
- [x] Add a strict, default-off `HERMES_AFFECT_DASHBOARD` gate.
- [x] Add a read-only native Hermes dashboard route for the latest valid state
      visible inside one container.
- [x] Add a conditional Affect tab, responsive current-state visualization,
      five-second non-overlapping polling, and empty/stale behavior.
- [x] Add a deterministic dependency-free browser build and commit-ready
      generated IIFE/CSS assets.
- [x] Add backend, projection, feature-gate, manifest, asset, and frontend
      normalization tests; pass the complete 137-test repository suite.
- [x] Validate the implementation contract against pinned Hermes `v2026.9.7`
      source and document the adapter path bootstrap.
- [x] Run Ruff.
- [ ] Smoke-test the packaged extension in the pinned Hermes image.
- [ ] Measure polling cost on the target Pi and adjust only if evidence requires
      it.
- [ ] Propose and review the separate Docker/Compose feature flag change; do
      not modify or deploy infrastructure without explicit authorization.
- [x] Plan retained-session navigation with exact selection, bounded catalog
      pagination, responsive UI, privacy constraints, tests, and clean-code
      boundaries in `dashboard/SESSION_NAVIGATION_PLAN.md`.
- [ ] Implement retained-session navigation phase-by-phase from that plan.

Acceptance criteria:

- Affect processing remains independent from web enablement.
- Disabled or invalid feature-gate values disclose no state and register no
  dashboard tab.
- The route remains behind Hermes' dashboard authentication and publishes no
  extra port or mutation method.
- One container exposes only its latest valid local state; cross-container
  aggregation and historical charts remain deferred.
- Exact continuation status is maintained in `dashboard/PLAN.md`.

## Phase 0 — repository and CI baseline

- [x] Create the standalone plugin scaffold.
- [x] Add the general Hermes plugin adapter and manifest.
- [x] Add unit tests, packaging metadata, documentation, and CI.
- [x] Commit the Ruff fixes and manual-only workflow change.
- [x] Push the CI fix commit to `main`.
- [x] Trigger CI manually from `main`.
- [x] Confirm every Python matrix job passes before beginning runtime work.

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

## Phase 1 — public Hermes compatibility baseline

- [x] Define the documented general-plugin registration methods used by the
  adapter.
- [x] Define the documented lifecycle and command callback contract used by
  the adapter.
- [x] Keep callbacks tolerant of additive keyword payload fields.
- [x] Add a fake Hermes context fixture covering the public callback shapes.
- [x] Document the portable adapter contract and avoid private Hermes imports.
- [x] Validate the adapter against the newest documented Hermes public API.
- [x] Review the documented public contract for versioned differences; none
  currently requires version-specific behavior or a separate fixture. Add one
  only when Hermes documents a real compatibility difference.
- [x] Document the support policy: newest Hermes releases have priority, while
  older versions remain supported when the public contract is unchanged.

Acceptance criteria:

- The plugin can register without importing private Hermes internals.
- Hook payload assumptions are covered by tests.
- Compatibility uncertainty is documented instead of hidden behind broad
  exception handling.
- Compatibility logic stays at the public registration and payload boundary;
  deployment-specific observations do not define the supported version range.

## Phase 2 — SOUL configuration and initialization

- [x] Define the delimited `session_affect` YAML convention.
- [x] Define neutral defaults for all seven traits and tuning values.
- [x] Validate schema version, types, numeric ranges, and sensitivities.
- [x] Fall back safely when the section is missing or invalid.
- [x] Emit administrative warnings for invalid configuration.
- [x] Store the SOUL SHA-256 hash and predisposition snapshot in session state.
- [x] Add fixtures for missing, valid, partially specified, and invalid SOULs.
- [x] Confirm free-form SOUL prose is never sent to an LLM for configuration
  extraction during session startup.
- [x] Document the future calibration tool and its mandatory review step.

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

## Phase 4.5 — structured semantic classification

- [x] Verify the current documented Hermes `ctx.llm.complete_structured()` API
  and its active-provider/host-owned-auth behavior.
- [x] Keep the deterministic classifier and add source, candidate confidence,
  and matched-rule metadata.
- [x] Define a compact validated semantic result with event, target, target ID,
  confidence, and severity.
- [x] Bound message/context input and keep classifier instructions separate
  from the main affective guidance prompt.
- [x] Add target-aware arbitration, including semantic `none` override and
  deterministic moderation authority.
- [x] Add disabled-by-default configuration, safe failure behavior, and a
  local re-entry guard for unexpected hook recursion.
- [x] Route semantic calls through a plugin-owned auxiliary task so the
  operator can explicitly select the provider and avoid implicit provider
  discovery.
- [x] Add fake-Hermes tests for semantic events, target disambiguation,
  malformed/low-confidence/provider failure, fallback, privacy, and recursion.
- [ ] Run a real Hermes gateway/profile smoke test against the newest supported
  release and verify provider usage, latency, and deployment privacy behavior.

Acceptance criteria:

- Semantic classification is opt-in and makes no second gateway or credential
  configuration of its own; its provider route is explicit in Hermes'
  top-level `auxiliary.hermes_affect_classifier` configuration.
- Only validated high-confidence results targeting this bot become affective
  events; unrelated and ambiguous messages do not create personal offense.
- The deterministic classifier remains available through disabled mode or the
  explicit compatibility fallback.
- No raw classifier input or output is persisted in runtime state or audit.

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
- [x] Derive a runtime expression drive from current affect and temperament,
  using a smooth asymptotic curve whose curvature is controlled by
  `expression_gain` instead of a static wording switch.
- [x] Add graduated expression tiers with high-conflict rebuttal/sarcasm
  guidance, an explicit refusal emoji, and repair-posture precedence.
- [x] Document the public privacy behavior: `pre_llm_call` guidance is appended
  to the user message and may be retained in API-bound history; the plugin does
  not rely on request-only visibility.
- [x] Evaluate request middleware as a later privacy-hardening option; defer
  implementation until the target Hermes hook is verified.

Acceptance criteria:

- The model is not normally prompted to narrate affective mechanics.
- Shadow mode is safe to inspect in a real test profile.
- Strong state can produce clearly observable behavior when configured to do so.

## Phase 7 — user and bot interventions

- [x] Register the `/affect` command surface.
- [x] Implement `/affect status` as administrative debug output.
- [x] Implement public `/affect state [profile]` inspection as a current-state
  snapshot without journal or history output.
- [x] Implement `/affect reset` without changing Hermes session state.
- [x] Implement `/affect calm`.
- [x] Implement `/affect heat`.
- [x] Define reviewed behavior for `/affect tune`.
- [x] Handle authenticated sender identity at the command boundary when
  Hermes supplies it; the current raw-only public contract fails closed and
  identity-enriched callback payloads are covered by local tests.
- [x] Ensure bots cannot imitate verified-user administrative authority.
- [x] Add natural-language moderation tests for calm, stop, continue, and
  lower-tone interventions.
- [x] Add bot mediation and bot provocation tests.

Acceptance criteria:

- Administrative commands affect only plugin state.
- Mutating unverified or bot-originated commands are rejected; the read-only
  experimental state snapshot is intentionally public.
- Natural interventions use social/administrative authority appropriately.

## Phase 8 — lifecycle, compression, and recovery

- [x] Implement new-session initialization and affect-only reset semantics.
- [x] Preserve continuity when Hermes exposes `parent_session_id` after
  compression.
- [x] Add duplicate `turn_id` tests for retries and repeated hook delivery.
- [x] Add successful-turn checkpoint tests.
- [x] Document incomplete retry/crash idempotency as an MVP limitation.
- [x] Add lifecycle tests for process restart, `/reset`, `/new`, finalization,
  and compression continuation.

Acceptance criteria:

- `/affect reset` does not create or destroy a Hermes conversation session.
- `/reset` and `/new` create new affective session boundaries.
- Compression continuation does not accidentally reset affect.

## Phase 9 — rollout

- [x] Run one local fake-Hermes test profile in shadow mode.
- [x] Inspect its administrative state/audit output.
- [x] Enable normal injection with a conservative test expression gain in the
  local fake-Hermes flow.
- [x] Validate user relationships and moderation in the local fake-Hermes flow.
- [x] Simulate multiple bots entirely in unit tests.
- [ ] Confirm persistent runtime path and permissions in the Docker deployment.
- [ ] Run one real two-bot group only after single-bot behavior is stable.
- [ ] Pin the deployed plugin to an immutable commit.
- [x] Add rollback instructions for the plugin source and runtime state.
- [x] Record one observed Hermes deployment as non-normative compatibility
  evidence.
- [ ] Validate the plugin in a real test profile using the newest supported
  Hermes release.

Deployment gate:

- No Pi command is run automatically by this repository.
- No Hermes permanent-memory setting is changed automatically.
- No source or runtime data is placed in Git.
- Deployment changes are reviewed separately from plugin implementation.

## Refactoring track

- [x] Extract `/affect` command parsing, interventions, and state rendering into
  a dedicated command module without changing the public registration adapter.
- [x] Separate editable algorithm parameters and pure calculations from the
  state-transition and posture modules.
- [x] Move Hermes registration and hook wiring into a dedicated integration
  adapter while preserving `hermes_affect.plugin:register` as the entry point.
- [ ] Extract session lifecycle and state-loading orchestration from the Hermes
  adapter.
- [x] Extract participant targeting helpers; broader callback identity cleanup remains future work.
- [ ] Extract affect observation/audit bookkeeping from the runtime pipeline.
- [x] Extract injected-context rendering from state transition orchestration.

## Explicit MVP non-goals

- SQLite persistence transition.
- Complete retry and crash-recovery idempotency.
- Public temperament-signature discovery.
- Shared mutable group atmosphere.
- Coordinated group-wide reset.
- Distributed multi-machine affect state.
- Automatic semantic classification is disabled by default and is not required
  for deterministic-only deployments.
- Automatic SOUL calibration without human review.
- Historical visualization and cross-container aggregation tools.

## Future roadmap

When the MVP is stable, evaluate SQLite or another transactional/event-based
store, safe state-schema evolution, limited public temperament signatures,
better local social perception, coordinated room resets, distributed groups,
cheaper auxiliary-task routing, richer semantic target resolution, and tools
for visualizing relationship and influence changes over time.
