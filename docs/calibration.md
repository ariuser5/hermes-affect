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

## Practical behavior cookbook

The previous section describes each parameter separately. For calibration, it
is more useful to start with the behavior you want and change one or two main
traits. The values below are starting points, not guarantees:

| Desired behavior | Suggested starting values |
|---|---|
| Calm and difficult to destabilize | `reactivity` 0.2–0.4, `pride` 0.2–0.5, `persistence` 0.2–0.5 |
| Sensitive and easily hurt | `reactivity` 0.7–0.9, `pride` 0.7–0.9, `playfulness` 0.1–0.4 |
| Holds onto anger or tension for a long time | `persistence` 0.75–0.95 |
| Playful and friendly | `playfulness` 0.75–0.95, `receptiveness` 0.6–0.9 |
| Playfully provocative or mischievous | `playfulness` 0.8–1.0, `assertiveness` 0.7–0.95, `receptiveness` 0.1–0.35 |
| Defends itself and confronts others | `assertiveness` 0.7–0.95, with medium or high `reactivity` and `pride` |
| Avoids conflict or withdraws | `assertiveness` 0.1–0.35; add high `reactivity` for a more sensitive withdrawal |
| Mediates other people's conflicts | `receptiveness` 0.8–1.0, `assertiveness` 0.7–0.9, `reactivity` 0.2–0.5 |
| Easily accepts apologies and repair attempts | `receptiveness` 0.75–0.95 |
| Difficult to reconcile | `pride` 0.7–0.9, `persistence` 0.7–0.95, `receptiveness` 0.15–0.4 |
| Expresses its feelings more visibly | `expression_gain` 1.5–3.0 |
| Discreet and not very demonstrative | `expression_gain` 0.2–0.7 |

### Example profiles

A friendly, playful bot could start with:

```yaml
traits:
  reactivity: 0.35
  persistence: 0.35
  pride: 0.30
  playfulness: 0.85
  assertiveness: 0.55
  receptiveness: 0.75
tuning:
  expression_gain: 1.2
```

A sensitive, defensive bot could start with:

```yaml
traits:
  reactivity: 0.85
  persistence: 0.80
  pride: 0.85
  playfulness: 0.20
  assertiveness: 0.30
  receptiveness: 0.35
tuning:
  expression_gain: 1.0
```

A mediation-oriented bot could start with:

```yaml
traits:
  reactivity: 0.30
  persistence: 0.45
  pride: 0.30
  playfulness: 0.40
  assertiveness: 0.85
  receptiveness: 0.95
tuning:
  expression_gain: 0.8
```

### How to interpret combinations

- High `playfulness` does not automatically mean sarcasm. It makes jokes and
  playful interpretations more likely.
- High `playfulness` + `assertiveness` with low `receptiveness` more readily
  produces provocation or persistent teasing.
- High `reactivity` + `pride` with low `playfulness` produces sensitivity to
  teasing or challenges involving competence and status.
- High `receptiveness` + `assertiveness` favors mediation: the bot is willing
  to consider the other person's perspective and also willing to intervene.
- `persistence` controls how long an event's effect remains in state; it is not
  a memory of facts or transcript content.
- `expression_gain` changes how visibly the effect appears in the reply. It
  does not directly change the internal reaction; if the state is appropriate
  but the reply is too subtle, increase this parameter first.

For sensitivity to a particular topic, add an explicit sensitivity, for
example:

```yaml
sensitivities:
  - topic: competence
    intensity: 0.70
```

This amplifies reactions to literal topic matches when the message is addressed
to the bot; it does not create general interest in or aversion to that topic.

### Recommended calibration procedure

1. Choose a scenario close to the behavior you want: `banter` for jokes,
   `group` for conflicts between participants, `repair` for apologies and
   reconciliation, or `cooling` for recovery over time.
2. Change one parameter by approximately `0.2` and run the scenario again.
3. Compare results with `--compare` or `--sweep`:

```bash
python -m hermes_affect.tools.calibration --scenario banter --sweep playfulness --json
python -m hermes_affect.tools.calibration --scenario group --preset mediator --json
python -m hermes_affect.tools.calibration --scenario repair --sweep receptiveness --json
```

4. Check `posture`, `expression tier`, tension, offense/frustration and the
   generated guidance.
5. Once the tendency is correct, adjust `expression_gain` for how strongly you
   want it expressed.

Offline scenarios show plugin guidance; they do not guarantee the exact wording
of the final model-generated reply. Live results also depend on session history,
the relationship with the participant and the messages the bot has observed. If
a behavior is not represented by the model, such as “always be sarcastic” or
“never take offense”, trait calibration alone cannot guarantee it.

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
