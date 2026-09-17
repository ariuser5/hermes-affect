"""Shared model calibration, separate from the six per-bot traits.

These are the independent numeric choices in the v2 behavioral engine.
Event families share channel updates; diagnostic limits live in models.py.
Use the offline calibration runner before editing these shared defaults.
"""

from typing import Final

# Base change per normal-severity event; other channels derive from this change.
POSITIVE_STEP: Final = 0.12
HUMOR_STEP: Final = 0.10
FRICTION_STEP: Final = 0.10
HOSTILITY_STEP: Final = 0.24
REPAIR_STEP: Final = 0.24
MODERATION_STEP: Final = 0.35

# floor + (1 - floor) * trait gives bounded, nonzero ordinary reactions.
TRAIT_FLOOR: Final = 0.25
# Positive arousal share; also the residual acceptance of strained relationships.
SECONDARY_SHARE: Final = 0.5
# Mood half-life ranges from log(2) hours to log(2)/0.2 hours.
MIN_DECAY_RATE: Final = 0.20
RELATION_TIME_MULTIPLIER: Final = 2.0
# Personality already affects state; expression reads state only.
EXPRESSION_CURVATURE: Final = 2.0
ACTIVE_THRESHOLD: Final = 0.30
STRONG_THRESHOLD: Final = 0.65
STRATEGY_THRESHOLD: Final = 0.45
STYLE_LEARNING_RATE: Final = 0.20
# Wording tiers: measured, visible, strong, intense.
EXPRESSION_TIERS: Final = (0.20, 0.50, 0.80)
