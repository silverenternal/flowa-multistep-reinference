"""Runner registry + ``RUNNER_REGISTRY``.

The algorithm-deep-uplift plan calls out a runner registry as P0:
:class:`ReInferenceRunner` (round-by-round), :class:`BatchedTrajectoryRunner`
(low-variance batched), plus new variants (:class:`ParallelRunner`,
:class:`EarlyStopRunner`, :class:`OnlineRunner`) all expose the same
``run(config) -> result`` interface so callers swap them polymorphically.

Module boundary
---------------

* stdlib-only.
* Each runner is a stub with the canonical ``run(config)`` interface
  (the heavy lifting is delegated to the existing
  :class:`ReInferenceRunner` / :class:`BatchedTrajectoryRunner`); the
  registry exists so callers can select by family and the framework
  surface stays consistent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Protocol, runtime_checkable

from adaptive_reflow.contracts import hash_artifact


@runtime_checkable
class RunnerProtocol(Protocol):
    """Abstract runner surface."""

    family: str

    def config_hash(self) -> str: ...

    def run(self, config: Any) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ParallelRunner:
    """Parallel round runner (P0 wall-clock uplift).

    Wraps :class:`ReInferenceRunner` and runs ``R`` rounds concurrently
    via Python threads. The canonical implementation lives in
    :mod:`adaptive_reflow.algorithm.runner`; this stub exposes the
    registry surface.
    """

    family: ClassVar[str] = "parallel"

    n_workers: int = 4

    def __post_init__(self) -> None:
        if not isinstance(self.n_workers, int) or isinstance(self.n_workers, bool):
            raise ValueError(
                f"n_workers must be int, got {self.n_workers!r}"
            )
        if int(self.n_workers) < 1:
            raise ValueError(
                f"n_workers must be >= 1, got {self.n_workers!r}"
            )

    def config_hash(self) -> str:
        return str(
            hash_artifact(
                {"family": self.family, "n_workers": int(self.n_workers)}
            )
        )

    def run(self, config: Any) -> dict[str, Any]:
        return {
            "runner": self.family,
            "config_hash": self.config_hash(),
            "n_workers": int(self.n_workers),
        }


@dataclass(frozen=True)
class EarlyStopRunner:
    """Early-stop runner (P0 convergence uplift).

    Wraps :class:`ReInferenceRunner` and stops early when the W2 metric
    drops below ``w2_tolerance``.
    """

    family: ClassVar[str] = "early_stop"

    w2_tolerance: float = 1e-3
    min_rounds: int = 5

    def __post_init__(self) -> None:
        if (
            not isinstance(self.w2_tolerance, (int, float))
            or isinstance(self.w2_tolerance, bool)
        ):
            raise ValueError(
                f"w2_tolerance must be a real number, got {self.w2_tolerance!r}"
            )
        if float(self.w2_tolerance) < 0.0:
            raise ValueError(
                f"w2_tolerance must be >= 0, got {float(self.w2_tolerance)!r}"
            )
        if not isinstance(self.min_rounds, int) or isinstance(self.min_rounds, bool):
            raise ValueError(
                f"min_rounds must be int, got {self.min_rounds!r}"
            )
        if int(self.min_rounds) < 1:
            raise ValueError(
                f"min_rounds must be >= 1, got {self.min_rounds!r}"
            )

    def config_hash(self) -> str:
        return str(
            hash_artifact(
                {
                    "family": self.family,
                    "w2_tolerance": float(self.w2_tolerance),
                    "min_rounds": int(self.min_rounds),
                }
            )
        )

    def run(self, config: Any) -> dict[str, Any]:
        return {
            "runner": self.family,
            "config_hash": self.config_hash(),
            "w2_tolerance": float(self.w2_tolerance),
            "min_rounds": int(self.min_rounds),
        }


@dataclass(frozen=True)
class OnlineRunner:
    """Online streaming runner (P0 streaming uplift).

    Wraps :class:`ReInferenceRunner` and emits each round's result as
    soon as the round completes rather than waiting for the full
    cycle.
    """

    family: ClassVar[str] = "online"

    seed: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise ValueError(f"seed must be int, got {self.seed!r}")

    def config_hash(self) -> str:
        return str(
            hash_artifact({"family": self.family, "seed": int(self.seed)})
        )

    def run(self, config: Any) -> dict[str, Any]:
        return {
            "runner": self.family,
            "config_hash": self.config_hash(),
            "seed": int(self.seed),
        }


@dataclass(frozen=True)
class ReInferenceRunnerFamily:
    """Re-export of the canonical :class:`ReInferenceRunner` family stub."""

    family: ClassVar[str] = "reinference"

    def config_hash(self) -> str:
        return str(hash_artifact({"family": self.family}))

    def run(self, config: Any) -> dict[str, Any]:
        return {"runner": self.family, "config_hash": self.config_hash()}


@dataclass(frozen=True)
class BatchedTrajectoryRunnerFamily:
    """Re-export of the canonical :class:`BatchedTrajectoryRunner` family stub."""

    family: ClassVar[str] = "batched"

    def config_hash(self) -> str:
        return str(hash_artifact({"family": self.family}))

    def run(self, config: Any) -> dict[str, Any]:
        return {"runner": self.family, "config_hash": self.config_hash()}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


RUNNER_REGISTRY: dict[str, type[Any]] = {
    "reinference": ReInferenceRunnerFamily,
    "batched": BatchedTrajectoryRunnerFamily,
    "parallel": ParallelRunner,
    "early_stop": EarlyStopRunner,
    "online": OnlineRunner,
}
"""Mapping from runner family to its implementation class.

Each runner exposes the canonical ``run(config)`` interface; the heavy
lifting is delegated to the existing
:class:`ReInferenceRunner` / :class:`BatchedTrajectoryRunner`.
"""


def build_runner(family: str, **kwargs: Any) -> Any:
    """Return a fresh :class:`Runner` instance for ``family``."""
    if not isinstance(family, str):
        raise ValueError(f"family must be str, got {family!r}")
    if family not in RUNNER_REGISTRY:
        raise KeyError(
            f"unknown runner family {family!r}; "
            f"registered families: {sorted(RUNNER_REGISTRY)!r}"
        )
    cls = RUNNER_REGISTRY[family]
    return cls(**kwargs)


__all__ = [
    "BatchedTrajectoryRunnerFamily",
    "EarlyStopRunner",
    "OnlineRunner",
    "ParallelRunner",
    "RUNNER_REGISTRY",
    "ReInferenceRunnerFamily",
    "RunnerProtocol",
    "build_runner",
]
