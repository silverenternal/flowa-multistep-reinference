"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.merge.merge_r2`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.merge_r2 import ...``
for downstream tools and tests.
"""

from __future__ import annotations

from .merge.merge_r2 import (
    MULTI_SOURCE_KALMAN_FAMILY,
    MultiSourceKalmanMergeOperator,
    bayesian_effective_count_schedule,
)

__all__ = [
    "MULTI_SOURCE_KALMAN_FAMILY",
    "MultiSourceKalmanMergeOperator",
    "bayesian_effective_count_schedule",
]
