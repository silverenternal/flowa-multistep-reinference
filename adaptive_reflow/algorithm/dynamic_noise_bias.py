"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.perturbation.dynamic_noise_bias`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.dynamic_noise_bias import ...``
for downstream tools and tests.
"""

from __future__ import annotations

from .perturbation.dynamic_noise_bias import (
    CategoricalDynamicNoiseBias,
    DEFAULT_DECAY_KIND,
    DEFAULT_MIN_GUMBEL_TEMP,
    DynamicNoiseBiasProtocol,
    DynamicNoiseBiasResult,
    IdentityDynamicNoiseBias,
    NEW_DYNAMIC_NOISE_BIAS_COMPUTED,
    NEW_DYNAMIC_NOISE_BIAS_DIGEST_ONLY,
    NEW_DYNAMIC_NOISE_BIAS_EPSILON_FLOORED_BY_PAPER_EXTERIOR_GAP,
    NEW_DYNAMIC_NOISE_BIAS_EPSILON_NONPOSITIVE,
    NEW_DYNAMIC_NOISE_BIAS_GUMBEL_HEURISTIC,
    NEW_DYNAMIC_NOISE_BIAS_GUMBEL_TEMP_COMPUTED,
    NEW_DYNAMIC_NOISE_BIAS_NO_MATERIALIZER,
    NEW_DYNAMIC_NOISE_BIAS_PREV_ANCHORED_TO_PREV_ENDPOINT,
    NEW_DYNAMIC_NOISE_BIAS_SHEET_NONPOSITIVE,
    Theorem1DynamicNoiseBias,
    default_dynamic_noise_bias,
)

__all__ = [
    "CategoricalDynamicNoiseBias",
    "DEFAULT_DECAY_KIND",
    "DEFAULT_MIN_GUMBEL_TEMP",
    "DynamicNoiseBiasProtocol",
    "DynamicNoiseBiasResult",
    "IdentityDynamicNoiseBias",
    "NEW_DYNAMIC_NOISE_BIAS_COMPUTED",
    "NEW_DYNAMIC_NOISE_BIAS_DIGEST_ONLY",
    "NEW_DYNAMIC_NOISE_BIAS_EPSILON_FLOORED_BY_PAPER_EXTERIOR_GAP",
    "NEW_DYNAMIC_NOISE_BIAS_EPSILON_NONPOSITIVE",
    "NEW_DYNAMIC_NOISE_BIAS_GUMBEL_HEURISTIC",
    "NEW_DYNAMIC_NOISE_BIAS_GUMBEL_TEMP_COMPUTED",
    "NEW_DYNAMIC_NOISE_BIAS_NO_MATERIALIZER",
    "NEW_DYNAMIC_NOISE_BIAS_PREV_ANCHORED_TO_PREV_ENDPOINT",
    "NEW_DYNAMIC_NOISE_BIAS_SHEET_NONPOSITIVE",
    "Theorem1DynamicNoiseBias",
    "default_dynamic_noise_bias",
]
