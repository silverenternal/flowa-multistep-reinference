"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.runner.batched_runner`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.batched_runner import ...``
for downstream tools and tests.

A small set of private symbols (``DEFAULT_W2_FAMILY``, ``_w2_to_mode_centres``)
are also re-exported here so the in-tree regression tests can reach them
without depending on the new subpackage path. Public-API callers should
NOT depend on these symbols.
"""

from __future__ import annotations

from .runner.batched_runner import (
    DEFAULT_W2_FAMILY,
    BatchedRunnerConfig,
    BatchedTrajectoryResult,
    BatchedTrajectoryRunner,
    _w2_to_mode_centres,
)

__all__ = [
    "DEFAULT_W2_FAMILY",
    "BatchedRunnerConfig",
    "BatchedTrajectoryResult",
    "BatchedTrajectoryRunner",
    "_w2_to_mode_centres",  # private — exposed only for test_batched_runner.py
]
