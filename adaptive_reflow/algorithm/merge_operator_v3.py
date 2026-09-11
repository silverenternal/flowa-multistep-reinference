"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.merge.merge_operator_v3`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.merge_operator_v3 import ...``
for downstream tools and tests.
"""

from __future__ import annotations

from .merge.merge_operator_v3 import (
    MEANFLOW_DECOMPOSITION_AUDIT,
    MEANFLOW_DEGENERATE_EPS,
    MEANFLOW_PAIR_INVALID,
    MeanFlowMergeOperator,
)

__all__ = [
    "MEANFLOW_DECOMPOSITION_AUDIT",
    "MEANFLOW_DEGENERATE_EPS",
    "MEANFLOW_PAIR_INVALID",
    "MeanFlowMergeOperator",
]
