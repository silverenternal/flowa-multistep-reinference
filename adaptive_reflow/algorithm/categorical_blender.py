"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.blender.categorical_blender`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.categorical_blender import ...``
for downstream tools and tests.
"""

from __future__ import annotations

from .blender.categorical_blender import (
    CATEGORICAL_AWARE_FAMILY,
    CATEGORICAL_BLEND_MASK_FRESH_FALLBACK,
    CATEGORICAL_BLEND_SENTINEL_PASSTHROUGH,
    CATEGORICAL_BLEND_TAU_FLOOR_HIT,
    CategoricalAwareBlender,
    DEFAULT_CATEGORICAL_AWARE_CONFIG_HASH,
    DEFAULT_TAU_FLOOR,
    DEFAULT_TAU_SCHEDULE_KIND,
    _logit_space_blend,
    default_categorical_blender,
)

__all__ = [
    "CATEGORICAL_AWARE_FAMILY",
    "CATEGORICAL_BLEND_MASK_FRESH_FALLBACK",
    "CATEGORICAL_BLEND_SENTINEL_PASSTHROUGH",
    "CATEGORICAL_BLEND_TAU_FLOOR_HIT",
    "CategoricalAwareBlender",
    "DEFAULT_CATEGORICAL_AWARE_CONFIG_HASH",
    "DEFAULT_TAU_FLOOR",
    "DEFAULT_TAU_SCHEDULE_KIND",
    "_logit_space_blend",
    "default_categorical_blender",
]
