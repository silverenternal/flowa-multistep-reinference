"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.blender.per_channel_blender`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.per_channel_blender import ...``
for downstream tools and tests.
"""

from __future__ import annotations

from .blender.per_channel_blender import (
    BLEND_FAMILY_BY_CHANNEL,
    DEFAULT_BLEND_FAMILY_BY_CHANNEL,
    DEFAULT_TAU_DEFAULT,
    DEFAULT_TAU_FLOOR,
    EPS_LOG,
    GRAPH_FAMILY,
    GUMBEL_FAMILY,
    LINEAR_FAMILY,
    LOGIT_FAMILY,
    MASKED_FAMILY,
    PER_CHANNEL_BLEND_FALLTHROUGH,
    PER_CHANNEL_BLEND_M_ONE_SHORTCIRCUIT,
    PER_CHANNEL_BLEND_M_ZERO_SHORTCIRCUIT,
    PER_CHANNEL_BLEND_MASK_FRESH_FALLBACK,
    PER_CHANNEL_BLEND_SENTINEL_PASSTHROUGH,
    PER_CHANNEL_BLEND_TAU_FLOOR_HIT,
    SAMPLE_FAMILY,
    BlendStrategy,
    GraphBlend,
    GumbelBlend,
    LinearBlend,
    LogitBlend,
    MaskedBlend,
    PerChannelBlender,
    SampleBlend,
    default_per_channel_blender,
)

__all__ = [
    "BLEND_FAMILY_BY_CHANNEL",
    "DEFAULT_BLEND_FAMILY_BY_CHANNEL",
    "DEFAULT_TAU_DEFAULT",
    "DEFAULT_TAU_FLOOR",
    "EPS_LOG",
    "GRAPH_FAMILY",
    "GUMBEL_FAMILY",
    "GumbelBlend",
    "LINEAR_FAMILY",
    "LinearBlend",
    "LOGIT_FAMILY",
    "LogitBlend",
    "MASKED_FAMILY",
    "MaskedBlend",
    "PER_CHANNEL_BLEND_FALLTHROUGH",
    "PER_CHANNEL_BLEND_MASK_FRESH_FALLBACK",
    "PER_CHANNEL_BLEND_M_ONE_SHORTCIRCUIT",
    "PER_CHANNEL_BLEND_M_ZERO_SHORTCIRCUIT",
    "PER_CHANNEL_BLEND_SENTINEL_PASSTHROUGH",
    "PER_CHANNEL_BLEND_TAU_FLOOR_HIT",
    "PerChannelBlender",
    "BlendStrategy",
    "SAMPLE_FAMILY",
    "SampleBlend",
    "GraphBlend",
    "default_per_channel_blender",
]
