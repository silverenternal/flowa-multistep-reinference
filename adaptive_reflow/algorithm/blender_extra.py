"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.blender.blender_extra`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.blender_extra import ...``
for downstream tools and tests.
"""

from __future__ import annotations

from .blender.blender_extra import (
    MultiTemperatureDistanceDecayBlender,
    OTLinearBlender,
)

__all__ = [
    "MultiTemperatureDistanceDecayBlender",
    "OTLinearBlender",
]
