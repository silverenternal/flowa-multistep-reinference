"""Backward-compat re-export shim for :mod:`adaptive_reflow.algorithm.blender_extra`.

All canonical implementations were merged into
:mod:`adaptive_reflow.algorithm.blender` in Wave 105 P2-B. This module
remains as a thin re-export so legacy ``from .blender_extra import
...`` statements continue to resolve unchanged.

See :mod:`adaptive_reflow.algorithm.blender` for the merged surface.
"""
from __future__ import annotations

from .blender import (
    BarycentricBlender,
    DEFAULT_MEMORY_FRACTION_FALLBACK,
    DerivationContext,
    DerivationRule,
    JointOTLinearBlender,
    MultiTemperatureDistanceDecayBlender,
    OTLinearBlender,
    PolyakMemoryFraction,
    derive_default_memory_fraction,
    make_derivation_context,
)

__all__ = [
    "BarycentricBlender",
    "DEFAULT_MEMORY_FRACTION_FALLBACK",
    "DerivationContext",
    "DerivationRule",
    "JointOTLinearBlender",
    "MultiTemperatureDistanceDecayBlender",
    "OTLinearBlender",
    "PolyakMemoryFraction",
    "derive_default_memory_fraction",
    "make_derivation_context",
]
