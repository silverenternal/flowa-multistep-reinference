"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.runner.sequential`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.sequential import ...``
for downstream tools and tests.
"""

from __future__ import annotations

from .runner.sequential import (
    SEQUENTIAL_FAMILY,
    SequentialScheduler,
    SequentialSlot,
    _dispatch_scheduler_config,
    _validate_positive_int,
)

__all__ = [
    "SEQUENTIAL_FAMILY",
    "SequentialScheduler",
    "SequentialSlot",
    "_dispatch_scheduler_config",
    "_validate_positive_int",
]
