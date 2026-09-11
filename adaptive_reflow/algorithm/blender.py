"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.blender.blender`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.blender import ...``
for downstream tools and tests.

Note: do not confuse this top-level shim with the
:mod:`adaptive_reflow.algorithm.blender` subpackage — both names exist
because Python's import system allows a module ``blender`` and a
subpackage ``blender/`` to coexist at the same level (the subpackage
takes precedence when imported as ``adaptive_reflow.algorithm.blender``).

This shim also re-exports a small number of private symbols used by
the in-tree regression tests (e.g.
``_canonical_json_default``). Public-API callers should NOT depend on
these symbols.
"""

from __future__ import annotations

from .blender.blender import (
    BLENDER_MEMORY_FRACTION_CLIPPED,
    DEFAULT_DISTANCE_DECAY_CONFIG_HASH,
    DEFAULT_DISTANCE_DECAY_TEMPERATURE,
    DEFAULT_LINEAR_CONFIG_HASH,
    DISTANCE_DECAY_FAMILY,
    LINEAR_FAMILY,
    DistanceDecayBlender,
    LinearBlender,
    RestartBlenderProtocol,
    _canonical_json_default,
    default_blender,
)

__all__ = [
    "BLENDER_MEMORY_FRACTION_CLIPPED",
    "DEFAULT_DISTANCE_DECAY_CONFIG_HASH",
    "DEFAULT_DISTANCE_DECAY_TEMPERATURE",
    "DEFAULT_LINEAR_CONFIG_HASH",
    "DISTANCE_DECAY_FAMILY",
    "DistanceDecayBlender",
    "LINEAR_FAMILY",
    "LinearBlender",
    "RestartBlenderProtocol",
    "_canonical_json_default",  # private — exposed only for test_blender.py
    "default_blender",
]
