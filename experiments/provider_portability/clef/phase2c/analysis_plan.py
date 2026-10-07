"""Frozen descriptive comparison axes for Clef Phase 2C."""

STANDARD_ORDER = "standard_order"
ZERO_POSITION_ORDER = "zero_position_order"
SUFFIX_SHIFT = "suffix_shift"

FROZEN_METRICS = (
    "max_probability_delta",
    "state_backbone_raw_max_absolute_delta",
    "global_backbone_raw_max_absolute_delta",
    "question_backbone_raw_max_absolute_delta",
    "option_context_raw_max_absolute_delta",
)

FROZEN_THRESHOLDS = {
    "semantic": None,
    "numerical_noise": None,
    "sufficiency": None,
    "necessity": None,
    "causality": None,
}
