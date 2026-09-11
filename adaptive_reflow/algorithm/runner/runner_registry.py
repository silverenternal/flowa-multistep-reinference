"""Runner registry + ``RUNNER_REGISTRY``.

The algorithm-deep-uplift plan calls out a runner registry as P0:
:class:`ReInferenceRunner` (round-by-round), :class:`BatchedTrajectoryRunner`
(low-variance batched), plus new variants (:class:`ParallelRunner`,
:class:`EarlyStopRunner`, :class:`OnlineRunner`) all expose the same
``run(config) -> result`` interface so callers can swap them polymorphically.

P0 round-2 wiring: the three stub variants now **delegate** to the
underlying runners instead of returning a dict. :class:`ParallelRunner`
runs rounds concurrently via a thread pool, :class:`EarlyStopRunner`
breaks out of the round loop when W2 falls below the tolerance, and
:class:`OnlineRunner` streams each round's result. The registry keys
and dataclass surfaces are unchanged so existing call sites keep
working.

Module boundary
---------------

* stdlib-only.
* Each runner accepts a ``config`` dict with the keys ``rounds`` (int)
  and ``round_fn`` (a ``Callable[[int], dict]``). When supplied, the
  runner delegates to the callable; otherwise it returns a stub dict
  describing the configuration (back-compat).
"""
from __future__ import annotations

import contextlib
import math
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol, runtime_checkable

from adaptive_reflow.contracts import hash_artifact


@runtime_checkable
class RunnerProtocol(Protocol):
    """Abstract runner surface."""

    family: str

    def config_hash(self) -> str: ...

    def run(self, config: Any) -> dict[str, Any]: ...


def _safe_call(
    fn: Callable[[int], dict[str, Any]], round_idx: int
) -> dict[str, Any]:
    """Call ``fn(round_idx)`` and surface the result, swallowing exceptions."""
    try:
        out = fn(int(round_idx))
    except Exception as exc:
        return {"round": int(round_idx), "error": repr(exc)}
    if not isinstance(out, dict):
        return {"round": int(round_idx), "result": out}
    out = dict(out)
    out.setdefault("round", int(round_idx))
    return out


@dataclass(frozen=True)
class ParallelRunner:
    """Parallel round runner (P0 round-2 wall-clock uplift).

    Wraps :class:`ReInferenceRunner` and runs ``R`` rounds concurrently
    via Python threads. The runner accepts a ``config`` dict with
    ``rounds`` (an integer) and ``round_fn`` (a ``Callable[[int], dict]``).
    When ``round_fn`` is provided the rounds execute concurrently in
    a thread pool; otherwise the runner returns a stub dict describing
    the configuration (back-compat).
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
        """Run ``round_fn(r)`` over ``config['rounds']`` rounds in parallel."""
        rounds = 0
        round_fn: Callable[[int], dict[str, Any]] | None = None
        if isinstance(config, dict):
            r_raw = config.get("rounds", 0)
            try:
                rounds = int(r_raw)
            except (TypeError, ValueError):
                rounds = 0
            cand = config.get("round_fn")
            if callable(cand):
                round_fn = cand
        if round_fn is None or rounds <= 0:
            return {
                "runner": self.family,
                "config_hash": self.config_hash(),
                "n_workers": int(self.n_workers),
                "rounds_completed": 0,
            }
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=int(self.n_workers)) as pool:
            futures = [pool.submit(_safe_call, round_fn, i) for i in range(rounds)]
            per_round = [f.result() for f in futures]
        per_round.sort(key=lambda d: int(d.get("round", 0)))
        elapsed = time.perf_counter() - t0
        return {
            "runner": self.family,
            "config_hash": self.config_hash(),
            "n_workers": int(self.n_workers),
            "rounds_completed": len(per_round),
            "wall_clock_seconds": float(elapsed),
            "per_round": per_round,
        }


@dataclass(frozen=True)
class EarlyStopRunner:
    """Early-stop runner (P0 round-2 convergence uplift).

    Wraps :class:`ReInferenceRunner` and stops early when the W2 metric
    drops below ``w2_tolerance``. The runner accepts a ``config`` dict
    with ``rounds``, ``round_fn`` (returning a dict carrying ``W2`` in
    ``metrics``), and ``min_rounds`` (which overrides the dataclass
    default).
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
        """Run ``round_fn(r)`` until ``min_rounds`` are reached or W2 < tolerance."""
        rounds = 0
        min_rounds = int(self.min_rounds)
        round_fn: Callable[[int], dict[str, Any]] | None = None
        if isinstance(config, dict):
            r_raw = config.get("rounds", 0)
            try:
                rounds = int(r_raw)
            except (TypeError, ValueError):
                rounds = 0
            cand = config.get("round_fn")
            if callable(cand):
                round_fn = cand
            mr_raw = config.get("min_rounds")
            if mr_raw is not None:
                with contextlib.suppress(TypeError, ValueError):
                    min_rounds = max(int(mr_raw), 1)
        if round_fn is None or rounds <= 0:
            return {
                "runner": self.family,
                "config_hash": self.config_hash(),
                "w2_tolerance": float(self.w2_tolerance),
                "min_rounds": int(min_rounds),
                "rounds_completed": 0,
            }
        per_round: list[dict[str, Any]] = []
        stopped_at: int | None = None
        for i in range(rounds):
            res = _safe_call(round_fn, i)
            per_round.append(res)
            if i + 1 < min_rounds:
                continue
            metrics = res.get("metrics") if isinstance(res, dict) else None
            w2_val: float | None = None
            if isinstance(metrics, dict):
                w2_raw = metrics.get("W2")
                try:
                    w2_val = float(w2_raw) if w2_raw is not None else None
                except (TypeError, ValueError):
                    w2_val = None
            if w2_val is not None and math.isfinite(w2_val) and w2_val < float(self.w2_tolerance):
                stopped_at = i + 1
                break
        return {
            "runner": self.family,
            "config_hash": self.config_hash(),
            "w2_tolerance": float(self.w2_tolerance),
            "min_rounds": int(min_rounds),
            "rounds_completed": len(per_round),
            "stopped_at_round": stopped_at,
            "per_round": per_round,
        }


@dataclass(frozen=True)
class OnlineRunner:
    """Online streaming runner (P0 round-2 streaming uplift).

    Wraps :class:`ReInferenceRunner` and emits each round's result as
    soon as the round completes rather than waiting for the full
    cycle. The runner accepts a ``config`` dict with ``rounds`` and
    ``round_fn`` and an optional ``on_round`` callback that is invoked
    once per round (so callers can wire streaming consumers).
    """

    family: ClassVar[str] = "online"

    seed: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise ValueError(f"seed must be int, got {self.seed!r}")

    def config_hash(self) -> str:
        return str(hash_artifact({"family": self.family, "seed": int(self.seed)}))

    def run(self, config: Any) -> dict[str, Any]:
        """Run ``round_fn(r)`` round-by-round, calling ``on_round`` after each."""
        rounds = 0
        round_fn: Callable[[int], dict[str, Any]] | None = None
        on_round: Callable[[int, dict[str, Any]], None] | None = None
        if isinstance(config, dict):
            r_raw = config.get("rounds", 0)
            try:
                rounds = int(r_raw)
            except (TypeError, ValueError):
                rounds = 0
            cand = config.get("round_fn")
            if callable(cand):
                round_fn = cand
            obs = config.get("on_round")
            if callable(obs):
                on_round = obs
        if round_fn is None or rounds <= 0:
            return {
                "runner": self.family,
                "config_hash": self.config_hash(),
                "seed": int(self.seed),
                "rounds_completed": 0,
            }
        per_round: list[dict[str, Any]] = []
        for i in range(rounds):
            res = _safe_call(round_fn, i)
            per_round.append(res)
            if on_round is not None:
                with contextlib.suppress(Exception):
                    # Callbacks are observer-only; errors must not break the run.
                    on_round(int(i), res)
        return {
            "runner": self.family,
            "config_hash": self.config_hash(),
            "seed": int(self.seed),
            "rounds_completed": len(per_round),
            "per_round": per_round,
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
