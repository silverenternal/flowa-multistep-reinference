"""Blender subpackage.

Aggregates the canonical blender surface across the framework:

* :class:`LinearBlender` + :class:`DistanceDecayBlender` —
  core linear / distance-decay blender families (``blender.py``).
* :class:`MultiTemperatureDistanceDecayBlender` + ``OTLinearBlender``
  — extra blender variants (``blender_extra.py``, wave-18 B-extensions).
* :class:`CategoricalAwareBlender` — categorical-aware blender with
  Gumbel anneal sampling (``categorical_blender.py``).
* :class:`PerChannelBlender` — per-channel strategy blender with
  Gumbel / linear / logit / masked / sample strategies
  (``per_channel_blender.py``).

Each canonical module preserves its public symbol set; this
``__init__`` re-exports the names so that downstream code can use
either ``from adaptive_reflow.algorithm.blender import X`` (preferred
new path) or the historical top-level shims
``from adaptive_reflow.algorithm.X import Y``.
"""

from __future__ import annotations

# Alias-import the ``blender`` submodule so the subpackage's own name
# does not shadow it. ``from .blender import X`` would be a self-import
# (the subpackage itself), which causes a partial-init error. Bind the
# module to a local alias instead.
from . import blender as _blender_mod
from .blender_extra import (
    MultiTemperatureDistanceDecayBlender,
    OTLinearBlender,
)
from .categorical_blender import (
    CATEGORICAL_AWARE_FAMILY,
    CATEGORICAL_BLEND_MASK_FRESH_FALLBACK,
    CATEGORICAL_BLEND_SENTINEL_PASSTHROUGH,
    CATEGORICAL_BLEND_TAU_FLOOR_HIT,
    DEFAULT_CATEGORICAL_AWARE_CONFIG_HASH,
    DEFAULT_TAU_FLOOR,
    DEFAULT_TAU_SCHEDULE_KIND,
    CategoricalAwareBlender,
    default_categorical_blender,
)
from .per_channel_blender import (
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

DEFAULT_DISTANCE_DECAY_CONFIG_HASH = _blender_mod.DEFAULT_DISTANCE_DECAY_CONFIG_HASH
DEFAULT_DISTANCE_DECAY_TEMPERATURE = _blender_mod.DEFAULT_DISTANCE_DECAY_TEMPERATURE
DEFAULT_LINEAR_CONFIG_HASH = _blender_mod.DEFAULT_LINEAR_CONFIG_HASH
DISTANCE_DECAY_FAMILY = _blender_mod.DISTANCE_DECAY_FAMILY
LINEAR_FAMILY = _blender_mod.LINEAR_FAMILY
DistanceDecayBlender = _blender_mod.DistanceDecayBlender
LinearBlender = _blender_mod.LinearBlender
RestartBlenderProtocol = _blender_mod.RestartBlenderProtocol
BLENDER_MEMORY_FRACTION_CLIPPED = _blender_mod.BLENDER_MEMORY_FRACTION_CLIPPED
_canonical_json_default = _blender_mod._canonical_json_default
_linear_blend_arrays = _blender_mod._linear_blend_arrays
_coerce_memory_fraction = _blender_mod._coerce_memory_fraction
_sigmoid = _blender_mod._sigmoid
default_blender = _blender_mod.default_blender
del _blender_mod

__all__ = [
    "BLEND_FAMILY_BY_CHANNEL",
    "BLENDER_MEMORY_FRACTION_CLIPPED",
    "_canonical_json_default",  # private — exposed only for test_blender.py
    "_linear_blend_arrays",  # private — exposed only for test_blender_delegation.py
    "_coerce_memory_fraction",  # private compatibility helper
    "_sigmoid",
    "CATEGORICAL_AWARE_FAMILY",
    "CATEGORICAL_BLEND_MASK_FRESH_FALLBACK",
    "CATEGORICAL_BLEND_SENTINEL_PASSTHROUGH",
    "CATEGORICAL_BLEND_TAU_FLOOR_HIT",
    "CategoricalAwareBlender",
    "DEFAULT_BLEND_FAMILY_BY_CHANNEL",
    "DEFAULT_CATEGORICAL_AWARE_CONFIG_HASH",
    "DEFAULT_DISTANCE_DECAY_CONFIG_HASH",
    "DEFAULT_DISTANCE_DECAY_TEMPERATURE",
    "DEFAULT_LINEAR_CONFIG_HASH",
    "DEFAULT_TAU_DEFAULT",
    "DEFAULT_TAU_FLOOR",
    "DEFAULT_TAU_SCHEDULE_KIND",
    "DISTANCE_DECAY_FAMILY",
    "DistanceDecayBlender",
    "EPS_LOG",
    "GRAPH_FAMILY",
    "GUMBEL_FAMILY",
    "GumbelBlend",
    "LINEAR_FAMILY",
    "LinearBlend",
    "LinearBlender",
    "LOGIT_FAMILY",
    "LogitBlend",
    "MASKED_FAMILY",
    "MaskedBlend",
    "MultiTemperatureDistanceDecayBlender",
    "OTLinearBlender",
    "PER_CHANNEL_BLEND_FALLTHROUGH",
    "PER_CHANNEL_BLEND_MASK_FRESH_FALLBACK",
    "PER_CHANNEL_BLEND_M_ONE_SHORTCIRCUIT",
    "PER_CHANNEL_BLEND_M_ZERO_SHORTCIRCUIT",
    "PER_CHANNEL_BLEND_SENTINEL_PASSTHROUGH",
    "PER_CHANNEL_BLEND_TAU_FLOOR_HIT",
    "PerChannelBlender",
    "BlendStrategy",
    "RestartBlenderProtocol",
    "SAMPLE_FAMILY",
    "SampleBlend",
    "GraphBlend",
    "default_blender",
    "default_categorical_blender",
    "default_per_channel_blender",
]
