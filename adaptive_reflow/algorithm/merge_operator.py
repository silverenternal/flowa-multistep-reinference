"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.merge.merge_operator`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.merge_operator import ...``
for downstream tools and tests.

CLM-042 derivation note: the canonical implementation enforces the paper
``e_rho / 4`` merge floor; this compatibility shim intentionally re-exports it.

Note: do not confuse this top-level shim with the
:mod:`adaptive_reflow.algorithm.merge` subpackage — both names exist
because Python's import system allows a module ``merge_operator`` and a
subpackage ``merge/`` to coexist at the same level (the subpackage
takes precedence when imported as ``adaptive_reflow.algorithm.merge``).
"""

from __future__ import annotations

from .merge.merge_operator import (
    ERR_PREV_REQUIRED,
    MERGE_CAP_OUT_OF_RANGE,
    MERGE_DEGENERATE_INTERVAL,
    MERGE_FLOOR_FALLBACK,
    MERGE_FLOOR_OUT_OF_RANGE,
    MERGE_NONFINITE_DYNAMIC_CLIPPED,
    MERGE_NONFINITE_PREV_CLIPPED,
    MERGE_PAPER_QUANTITY_FLOOR_LIFTED,
    MERGE_PREV_ANCHORED_TO_LAST_EMITTED,
    BoundedMergeOperator,
    EMAOperator,
    IdentityOperator,
    MergeAuthorityError,
    MergeOperatorProtocol,
    _ERR_CAP_BELOW_FLOOR,
    default_bounded_merge_operator,
)

__all__ = [
    "ERR_PREV_REQUIRED",
    "MERGE_CAP_OUT_OF_RANGE",
    "MERGE_DEGENERATE_INTERVAL",
    "MERGE_FLOOR_FALLBACK",
    "MERGE_FLOOR_OUT_OF_RANGE",
    "MERGE_NONFINITE_DYNAMIC_CLIPPED",
    "MERGE_NONFINITE_PREV_CLIPPED",
    "MERGE_PAPER_QUANTITY_FLOOR_LIFTED",
    "MERGE_PREV_ANCHORED_TO_LAST_EMITTED",
    "BoundedMergeOperator",
    "EMAOperator",
    "IdentityOperator",
    "MergeAuthorityError",
    "MergeOperatorProtocol",
    "_ERR_CAP_BELOW_FLOOR",
    "default_bounded_merge_operator",
]
