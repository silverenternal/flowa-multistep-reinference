"""Merge-operator subpackage.

Aggregates the canonical merge-operator surface across the framework:

* :class:`BoundedMergeOperator` + :class:`EMAOperator` +
  :class:`IdentityOperator` — canonical merge-operator families
  (``merge_operator.py``).
* :class:`MeanFlowMergeOperator` — Wave 18 mean-flow extension
  (``merge_operator_v3.py``).
* :class:`BayesianMergeOperator` + :class:`KalmanBoundedMergeOperator` +
  :class:`PIDIdentityOperator` + :class:`ScheduleAwareEMAOperator` —
  extra variants (``merge_operator_extra.py``).
* Wave-18 round-2 utilities (``merge_r2.py``).

Each canonical module preserves its public symbol set; this
``__init__`` re-exports the names so that downstream code can use
either ``from adaptive_reflow.algorithm.merge import X`` (preferred
new path) or the historical top-level shims
``from adaptive_reflow.algorithm.X import Y``.
"""

from __future__ import annotations

from .merge_operator import (
    ERR_PREV_REQUIRED,
    MERGE_CAP_OUT_OF_RANGE,
    MERGE_DEGENERATE_INTERVAL,
    MERGE_FLOOR_FALLBACK,
    MERGE_FLOOR_OUT_OF_RANGE,
    MERGE_NONFINITE_DYNAMIC_CLIPPED,
    MERGE_NONFINITE_PREV_CLIPPED,
    MERGE_PREV_ANCHORED_TO_LAST_EMITTED,
    BoundedMergeOperator,
    EMAOperator,
    IdentityOperator,
    MergeAuthorityError,
    MergeOperatorProtocol,
    default_bounded_merge_operator,
)
from .merge_operator_extra import (
    BayesianMergeOperator,
    KalmanBoundedMergeOperator,
    PIDIdentityOperator,
    ScheduleAwareEMAOperator,
)
from .merge_operator_v3 import (
    MEANFLOW_DECOMPOSITION_AUDIT,
    MEANFLOW_DEGENERATE_EPS,
    MEANFLOW_PAIR_INVALID,
    MeanFlowMergeOperator,
)
from .merge_r2 import *  # noqa: F401,F403 — merge_r2 exports helpers used downstream

__all__ = [
    "ERR_PREV_REQUIRED",
    "MEANFLOW_DECOMPOSITION_AUDIT",
    "MEANFLOW_DEGENERATE_EPS",
    "MEANFLOW_PAIR_INVALID",
    "MERGE_CAP_OUT_OF_RANGE",
    "MERGE_DEGENERATE_INTERVAL",
    "MERGE_FLOOR_FALLBACK",
    "MERGE_FLOOR_OUT_OF_RANGE",
    "MERGE_NONFINITE_DYNAMIC_CLIPPED",
    "MERGE_NONFINITE_PREV_CLIPPED",
    "MERGE_PREV_ANCHORED_TO_LAST_EMITTED",
    "BayesianMergeOperator",
    "BoundedMergeOperator",
    "EMAOperator",
    "IdentityOperator",
    "KalmanBoundedMergeOperator",
    "MeanFlowMergeOperator",
    "MergeAuthorityError",
    "MergeOperatorProtocol",
    "PIDIdentityOperator",
    "ScheduleAwareEMAOperator",
    "default_bounded_merge_operator",
]
