"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.merge.merge_operator_extra`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.merge_operator_extra import ...``
for downstream tools and tests.
"""

from __future__ import annotations

from .merge.merge_operator_extra import (
    BayesianMergeOperator,
    KalmanBoundedMergeOperator,
    PIDIdentityOperator,
    ScheduleAwareEMAOperator,
)

__all__ = [
    "BayesianMergeOperator",
    "KalmanBoundedMergeOperator",
    "PIDIdentityOperator",
    "ScheduleAwareEMAOperator",
]
