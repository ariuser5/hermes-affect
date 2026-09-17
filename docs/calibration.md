# Calibrating behavior

Model v2 exposes six temperament traits and one expression gain. All traits are
finite values in [0,1], default 0.5; expression_gain is [0,10], default 1.
Use expression_gain to adjust how visibly the plugin affects replies. Change
traits to change what the bot reacts to, how it interprets interactions and
whether it confronts, withdraws, teases or mediates.

## Fast offline comparison

From the repository, with the development Python environment:

```bash
python -m hermes_affect.tools.calibration --scenario banter --compare
python -m hermes_affect.tools.calibration --scenario group --compare
python -m hermes_affect.tools.calibration --scenario repair --sweep receptiveness
python -m hermes_affect.tools.calibration --scenario praise --expression 2
python -m hermes_affect.tools.calibration --preset sensitive --trait assertiveness=0.9 --json
python -m hermes_affect.tools.calibration --soul examples/soul/basic.md --scenario cooling --json
```

`hermes_affect.tools.calibration` is the canonical module path. The older
`python -m hermes_affect.calibration` path remains supported as a compatibility
alias for existing callers.

The table shows posture, expression tier, frustration, offense and perceived
atmosphere after every turn. JSON additionally shows effective configuration,
derived drives and the exact guidance the plugin would inject.

These runs use the actual runtime and isolated temporary state with a fixed
clock. They do not call Hermes, an LLM, a provider or another bot; do not change
SOUL; and do not access live affect storage. Results measure plugin guidance,
not the final model's wording, psychological realism or a live multi-bot loop.

Available scenarios: banter, group, repair, praise, disagreement, cooling.
Presets are expanded configurations, not extra behavioral parameters:

| Preset | Trait changes from neutral |
|---|---|
| mischievous | playfulness .95, assertiveness .9, receptiveness .1 |
| sensitive | reactivity .9, pride .9, playfulness .1, assertiveness .25 |
| mediator | reactivity .35, assertiveness .85, receptiveness .95 |
| resilient | reactivity .15, pride .15, assertiveness .8, playfulness .8 |

Use --trait NAME=VALUE repeatedly to tune a candidate. --sweep replaces one
trait with 0, .25, .5, .75 and 1 while holding others fixed. --compare overlays
each preset on the selected baseline. --sweep takes precedence over --compare.

For your own synthetic conversations, --scenario-file accepts a JSON list:

```json
[
  {"sender_id":"bot:B","target_id":"bot:C","user_message":"C, nice try"},
  {"sender_id":"bot:C","target_id":"bot:B","user_message":"B, stop teasing me"},
  {"sender_id":"user:admin","sender_kind":"user","verified_user":true,
   "user_message":"calm down","elapsed_hours":0.25}
]
```

The observer is bot:A and known participants are A, B and C. Each entry may
contain user_message, sender_id, sender_kind, target_id, verified_user, and
elapsed_hours since the previous entry. The verified_user value belongs to
this offline simulator; it does not grant authority in a running Hermes bot.
Prefer synthetic text. Reports omit input messages but do include participant
labels and the generated internal guidance.

## What to adjust

| Desired difference | Change |
|---|---|
| Same internal state, stronger outward behavior | expression_gain |
| Faster emotional response to both kindness and hostility | reactivity |
| Longer recovery time after conversation stops | persistence |
| Greater sensitivity to disrespect/status challenges | pride |
| Enjoyment of banter and less hostile interpretation of teasing | playfulness |
| Confrontation/intervention instead of withdrawal | assertiveness |
| Accepting apologies and trusted mediation more readily | receptiveness |
| Playful baiting / trolling-like communication | high playfulness + assertiveness, low receptiveness |
| Easily hurt by teasing | high reactivity + pride, low playfulness |
| Avoiding tense discussions | high reactivity, low assertiveness |
| Mediating observed conflict | high receptiveness + assertiveness |

These are tendencies and opportunities, not guarantees. High mischief selects
teasing guidance on humorous or disagreeing turns; it does not make every reply
a provocation. A compatible playful receiver interprets the same teasing more
positively; a serious, reactive, proud receiver can accumulate offense.
The same six dimensions cannot represent every human communication pattern.
Future additions should be justified by scenarios the current model cannot
represent, rather than adding a knob for each named behavior.

## Shared calibration and diagnostics

parameters.py holds 15 shared scalar choices and three expression tier
boundaries. calculations.py also has four distinct severity calibration
multipliers (.5, 1, 1.75, 2.5). Numeric domain bounds and storage/input limits are
not personality parameters. There is no 52-number style table: observations
use four binary event-family signals and one shared smoothing rate.

The event-family strengths are POSITIVE_STEP, HUMOR_STEP, FRICTION_STEP,
HOSTILITY_STEP, REPAIR_STEP and MODERATION_STEP. Edit them only to recalibrate
all bots, then rerun comparisons. Derived channel couplings share
SECONDARY_SHARE; persistence derives the relationship decay rate from the mood
rate rather than using a second independent range. Trait factors share one
nonzero floor. See architecture.md for formulas and intentional coupling.

This is a reduction from 98 named scalar constants plus 52 numeric style-table
entries in v1 to 18 numeric choices in parameters.py plus the four distinct
severity levels. These are counts of calibration choices, not a claim that
every literal in either model is an independent degree of freedom.

In a supported authenticated admin session:

```text
/affect explain
/affect tune expression_gain 0.5
/affect tune expression_gain 2
/affect calm
```

explain shows the session's effective configuration, derived tendencies,
relationship credibility/receptivity and local social observations. The public
state command remains a smaller current snapshot, excluding social observations
and audit history. Raw-only command payloads still fail closed for administration.

Editing SOUL affects new sessions. Existing v2 sessions use their saved snapshot.
To compare trait changes immediately use the offline runner, then apply a reviewed
SOUL and start a new Hermes session. /affect reset preserves temperament for an
existing v2 session; it is not a SOUL reload command.

## Migrating v1

```bash
python -m hermes_affect.tools.calibration --migrate-soul path/to/SOUL.md
```

This prints a proposed v2 configuration and explicitly reports removed
social_influence, escalation_gain and repair_gain values. It never writes
SOUL or state. The new model is not numerically equivalent.

Legacy sessions remain readable but affect processing and checkpoint writes
are skipped with an administrative warning. Review and apply the proposed
SOUL outside this source-only workflow, then start a new session. Alternatively,
an explicitly authenticated /affect reset on that legacy session initializes
fresh v2 affect from the reviewed v2 SOUL; old emotional continuity is lost.
Compression does not silently convert legacy sessions. Normal abandoned-state
retention still applies; keep a backup if a legacy snapshot must be retained.

## Real reply validation

After the offline comparisons, separately authorize a real Hermes smoke test.
Compare the same controlled conversations with injection disabled, measured
expression and stronger expression. Assess warmth, teasing, withdrawal,
mediation, repeated conflict and moderation recovery. Inspect target attribution
and which group messages each observer actually receives. Do not infer a
successful live rollout solely from the deterministic reports.
