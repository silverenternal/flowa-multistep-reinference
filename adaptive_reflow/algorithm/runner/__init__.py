"""Runner subpackage.

Aggregates the canonical runner surface across the framework:

* :class:`ReInferenceRunner` — legacy single-endpoint runner
  (``runner.py``).
* :class:`BatchedTrajectoryRunner` — multi-trajectory runner with
  per-round selection metric (``batched_runner.py``).
* :class:`SequentialScheduler` — slot-based sequential runner
  (``sequential.py``).
* :class:`RUNNER_REGISTRY` + ``build_runner`` + per-family wrappers
  (``runner_registry.py``).

Each canonical module preserves its public symbol set; this
``__init__`` re-exports the names so that downstream code can use
either ``from adaptive_reflow.algorithm.runner import X`` (preferred
new path) or the historical top-level shims
``from adaptive_reflow.algorithm.X import Y``.

Lazy ``runner.py`` import
------------------------

``runner.py`` imports :mod:`adaptive_reflow.frame.adapter` which
transitively pulls in :mod:`adaptive_reflow.frame.merge` which
re-enters the partially-initialised ``adaptive_reflow.algorithm``
namespace. Loading the runner subpackage therefore triggers an
import-time circular error. To break the cycle we defer the import
of :mod:`runner.runner` to first attribute access via PEP 562
``__getattr__`` so the symbols are materialised only after
``adaptive_reflow.algorithm`` has finished initialising.
"""

from __future__ import annotations

from .batched_runner import (
    BatchedRunnerConfig,
    BatchedTrajectoryResult,
    BatchedTrajectoryRunner,
)
from .runner_registry import (
    RUNNER_REGISTRY,
    BatchedTrajectoryRunnerFamily,
    EarlyStopRunner,
    OnlineRunner,
    ParallelRunner,
    ReInferenceRunnerFamily,
    RunnerProtocol,
    build_runner,
)
from .sequential import (
    SEQUENTIAL_FAMILY,
    SequentialScheduler,
    SequentialSlot,
)


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    """PEP 562 lazy lookup for ``runner.py`` symbols.

    Loaded on first attribute access to break the algorithm →
    frame.adapter → algorithm circular chain at subpackage load
    time. This is the same pattern used in
    :mod:`adaptive_reflow.algorithm.perturbation` for
    ``round2_extra``.
    """
    if name in {
        "FORWARD_NOISE_INJECTED",
        "ReInferenceConfig",
        "ReInferenceResult",
        "ReInferenceRunner",
    }:
        from . import runner as _runner_mod

        g = globals()
        for sym in (
            "FORWARD_NOISE_INJECTED",
            "ReInferenceConfig",
            "ReInferenceResult",
            "ReInferenceRunner",
        ):
            g.setdefault(sym, getattr(_runner_mod, sym))
        return g[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "FORWARD_NOISE_INJECTED",
    "RUNNER_REGISTRY",
    "BatchedRunnerConfig",
    "BatchedTrajectoryResult",
    "BatchedTrajectoryRunner",
    "BatchedTrajectoryRunnerFamily",
    "EarlyStopRunner",
    "OnlineRunner",
    "ParallelRunner",
    "ReInferenceConfig",
    "ReInferenceRunnerFamily",
    "ReInferenceResult",
    "ReInferenceRunner",
    "RunnerProtocol",
    "SEQUENTIAL_FAMILY",
    "SequentialScheduler",
    "SequentialSlot",
    "build_runner",
]
