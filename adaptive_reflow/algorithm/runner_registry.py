"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.runner.runner_registry`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.runner_registry import ...``
for downstream tools and tests.
"""

from __future__ import annotations

from .runner.runner_registry import (
    RUNNER_REGISTRY,
    BatchedTrajectoryRunnerFamily,
    EarlyStopRunner,
    OnlineRunner,
    ParallelRunner,
    ReInferenceRunnerFamily,
    RunnerProtocol,
    build_runner,
)

__all__ = [
    "RUNNER_REGISTRY",
    "BatchedTrajectoryRunnerFamily",
    "EarlyStopRunner",
    "OnlineRunner",
    "ParallelRunner",
    "ReInferenceRunnerFamily",
    "RunnerProtocol",
    "build_runner",
]
