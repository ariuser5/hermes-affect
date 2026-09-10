# Hermes Affect repository instructions

These instructions help a new agent resume work safely. Follow higher-priority
platform instructions and the shared agent instructions first.

## Resume procedure

At the start of every session:

1. Read `README.md`, `TODO.md`, and the relevant files under `docs/`.
2. Run `git status --short --branch` and preserve all existing user changes.
3. Read the latest commits before deciding what remains.
4. Use `TODO.md` as the implementation sequence and update it when a phase or
   acceptance criterion is completed.
5. Run focused tests and review the diff before handing work back.

## Current checkpoint

Checkpoint date: 2026-09-10.

- The repository is `hermes-affect`.
- `a346a0b` (`docs: record successful CI matrix validation`) is the current
  local `main` commit and matches `origin/main`.
- The compact seven-trait design is implemented: reactivity, persistence,
  pride, playfulness, assertiveness, social influence, and receptiveness, with
  independent expression/escalation/repair tuning.
- The plugin scaffold is implemented: manifest, Hermes registration adapter,
  SOUL configuration validation, state models, JSON storage, deterministic
  event classification, affect dynamics, social-influence policy, response
  posture, documentation, examples, tests, and CI.
- CI is intentionally manual-only through `workflow_dispatch`.
- A local fake Hermes context now covers registration, lifecycle callbacks,
  state persistence, verified-admin command behavior, and affect-only command
  interventions. The adapter is built against the documented public Hermes
  general-plugin contract. One target deployment has provided compatibility
  observations, but those observations do not define a fixed supported
  version. Raw-only slash commands fail closed because the public command
  contract does not currently provide authenticated sender context.
- The durable-state restart, profile/session isolation, schema-version,
  command-intervention, conservative 90-day garbage-collection, bounded
  transcript-free audit-record, Phase 4 dynamics/influence coverage, Phase 1
  compatibility-contract, Phase 2 configuration-safety, Phase 6 response,
  Phase 7 intervention/tuning, Phase 8 compression/lifecycle, and the Phase 8
  retry-boundary documentation, Phase 9 rollout smoke tests, and the Phase 6
  privacy-hardening, public-compatibility strategy, explicit command
  verification, and CI validation slices are committed. Run `git status
  --short --branch` before continuing because the repository may contain
  pending changes from the last handoff.
- The current Python 3.10–3.13 matrix has passed from a fresh manual run on
  `main`; do not change CI again unless a new failure provides evidence.
- `TODO.md` is the current planning file and now records the compact-trait
  design checkpoint. Preserve it unless the user explicitly asks for changes.

## Immediate next work

1. Continue through the remaining TODO phases using the documented public
   Hermes API as the compatibility baseline; add versioned fixtures only when
   Hermes documents a real public contract difference.
2. Do not run the Raspberry Pi commands or use SSH unless the user explicitly
   authorizes that action.
3. Continue through the TODO phases incrementally, keeping tests and
   documentation synchronized.

## Repository and deployment boundaries

- This repository contains plugin source, tests, examples, and generic
  deployment guidance only.
- Do not modify the separate infrastructure/deployment repository unless the
  user explicitly asks for that integration.
- Do not change the running Hermes configuration, Docker Compose files, image
  tags, profile files, or permanent-memory settings without explicit approval.
- Do not call Hermes memory APIs or write `MEMORY.md` or `USER.md` for
  temporary affective state.
- Keep runtime state outside Git and never commit credentials, sessions, logs,
  or affective JSON state.
- Do not commit, push, publish, release, or deploy unless the user explicitly
  requests that operation.

## Implementation conventions

- Keep the plugin a general Python Hermes plugin, not a memory provider,
  context engine, or skill-only mechanism.
- Preserve Python 3.10 compatibility and Raspberry Pi ARM64 suitability.
- Prefer standard-library runtime dependencies and small, inspectable modules.
- Use `apply_patch` for source edits.
- Do not hide errors with broad catches or silent fallbacks; invalid SOUL
  configuration may fall back to documented neutral defaults, but must emit an
  administrative warning.
- Avoid raw transcripts, long quotations, and hidden chain-of-thought in
  affective state or audit output.
