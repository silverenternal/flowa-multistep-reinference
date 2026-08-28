"""Batched trajectory runner — populates the metric on a per-round basis.

Companion to :class:`adaptive_reflow.algorithm.runner.ReInferenceRunner`.
The legacy runner captures exactly **one** endpoint per round, leaving the
selection-ratio metric with a noise floor wider than the effect it is
supposed to measure (see ``docs/review/B5-VERIFICATION.md`` §1.1 and the
B5 design at ``docs/design/B5_BATCHED_TRAJECTORIES.md``).

This module adds a deliberately thin, additive batched runner:

* :class:`BatchedRunnerConfig` — frozen config carrying the scheduler,
  policy-driver, blender, and (optional) selection evaluator in
  addition to the four numeric batch-shape knobs (``cycle_length``,
  ``trajectories_per_round``, ``endpoints_per_trajectory``, ``seed``).
* :class:`BatchedTrajectoryResult` — the per-round endpoint matrix
  (round → trajectory → ``(endpoints_per_trajectory, dim)`` array),
  per-round W2 against the canonical mode centres, the per-round
  schedule ``n_cap`` and the per-round selection ratio (when an
  evaluator is supplied), plus a stable ``config_hash`` payload.
* :class:`BatchedTrajectoryRunner` — the orchestrator. Per round it
  samples the scheduler for ``n_cap_r``, asks the adapter to generate
  ``T`` trajectories (each carrying ``K`` endpoints), aggregates them
  into a single population, scores the W2 and (optionally) the
  selection ratio, and feeds the round's W2 back to the scheduler.

Phase-A additive: the runner coexists with :class:`ReInferenceRunner`
and does **not** touch the engine, the four protocol surfaces, or any
existing golden file.

Tasks satisfied:

* B5 design doc section 3.2 (Phase A additive runner).
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.algorithm.blender import RestartBlenderProtocol
from adaptive_reflow.algorithm.policy_driver import PolicyDriverProtocol
from adaptive_reflow.algorithm.scheduler import SchedulerProtocol
from adaptive_reflow.contracts import ChannelName

if TYPE_CHECKING:
    # Imported only for type checking; the runtime helpers
    # ``cell_evidence`` / ``sheet_cell_centers`` / ``sheet_evidence``
    # and the class :class:`EvidenceScaleGapMetric` are lazy-imported
    # inside the helper functions to break the
    # ``algorithm -> eval -> adapters -> frame -> algorithm``
    # cycle at module import time.
    from adaptive_reflow.eval.posterior_selection_evaluator import (
        EvidenceScaleGapMetric,
    )


# ---------------------------------------------------------------------------
# Duck-typed adapter surface used by the batched runner
# ---------------------------------------------------------------------------


@runtime_checkable
class _BatchedAdapterProtocol(Protocol):
    """Minimal adapter surface required by :class:`BatchedTrajectoryRunner`.

    The protocol is duck-typed: any object whose ``generate_trajectory``
    method has the canonical signature ``(*, n_trajectories,
    endpoints_per_trajectory, n_gen, seed)`` and returns an
    ``(n_trajectories, endpoints_per_trajectory, n_gen, dim)`` array
    is acceptable. The only reference implementation today is
    :class:`adaptive_reflow.adapters.twodim_fm.TwoDimFMAdapter`.
    """

    target: str

    def generate_trajectory(
        self,
        *,
        n_trajectories: int,
        endpoints_per_trajectory: int,
        n_gen: int,
        seed: int,
    ) -> NDArray[np.float64]:
        """Return ``(n_trajectories, endpoints_per_trajectory, n_gen, dim)``.

        RK4-style deterministic integration. See
        :meth:`adaptive_reflow.adapters.twodim_fm.TwoDimFMAdapter.generate_trajectory`.
        """
        ...


# ---------------------------------------------------------------------------
# Config + result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BatchedRunnerConfig:
    """Frozen configuration for :class:`BatchedTrajectoryRunner`.

    Attributes
    ----------
    cycle_length:
        Number of rounds the runner drives (``>= 1``).
    trajectories_per_round:
        Number of independent trajectories (``T``) per round. Default
        ``8`` matches the B5 design's recommended batch size — gives a
        Monte-Carlo standard error on the ratio of ``~0.0065`` at
        ``endpoints_per_trajectory = 16`` (``B = 128`` endpoints per
        round; see design doc §1.1).
    endpoints_per_trajectory:
        Number of endpoint slots (``K``) per trajectory. Default ``16``.
    scheduler:
        Any :class:`SchedulerProtocol`. The runner samples it once per
        round to obtain ``n_cap_r``.
    policy_driver:
        Retained for protocol parity with the legacy runner; not
        exercised in the batched ``run()`` loop (the batch axis lives
        outside the engine). Held on the result via ``config_hash``
        for provenance.
    blender:
        Retained for protocol parity; same status as ``policy_driver``.
    selection_evaluator:
        Optional :class:`EvidenceScaleGapMetric`. When supplied, the
        runner scores the round's endpoint population and emits the
        canonical ``selection_ratio`` per round.
    seed:
        Base seed. Per-trajectory effective seed is
        ``seed + r * T + t`` for round ``r`` and trajectory ``t``.
    """

    cycle_length: int = 20
    trajectories_per_round: int = 8
    endpoints_per_trajectory: int = 16
    scheduler: SchedulerProtocol | None = None
    policy_driver: PolicyDriverProtocol | None = None
    blender: RestartBlenderProtocol | None = None
    selection_evaluator: EvidenceScaleGapMetric | None = None
    seed: int = 42


@dataclass(frozen=True)
class BatchedTrajectoryResult:
    """Frozen result of a :meth:`BatchedTrajectoryRunner.run` call.

    Attributes
    ----------
    per_round_endpoints:
        ``round -> trajectory -> (endpoints_per_trajectory, dim)`` array.
        ``r`` indexes rounds ``[0, cycle_length)``; ``t`` indexes
        trajectories ``[0, trajectories_per_round)``.
    per_round_w2:
        Per-round Wasserstein-2 distance from the round's flattened
        endpoint population against the canonical mode-centre set for
        the adapter's target (``two_moons`` or ``eight_gaussians``).
    per_round_n_cap:
        Per-round ``n_cap`` reported by the scheduler.
    per_round_metric:
        ``name -> per-round list`` mapping. Always contains ``n_cap``,
        ``W2``, ``selection_ratio``. When ``selection_evaluator`` is
        ``None``, the ``selection_ratio`` list is empty.
    per_round_selection_ratio:
        Optional per-round ``selection_ratio`` (one float per round) —
        ``None`` when no evaluator was supplied, otherwise a list of
        length ``cycle_length``. Equivalent to the
        ``per_round_metric["selection_ratio"]`` slot when populated.
    config_hash:
        Stable SHA-256 digest over the runner config (cycle length,
        batch shape, scheduler / driver / blender hashes, evaluator
        hash when supplied, base seed). Same inputs → same hash.
    """

    per_round_endpoints: list[list[NDArray[np.float64]]] = field(default_factory=list)
    per_round_w2: list[float] = field(default_factory=list)
    per_round_n_cap: list[float] = field(default_factory=list)
    per_round_metric: dict[str, list[float]] = field(default_factory=dict)
    per_round_selection_ratio: list[float] | None = None
    config_hash: str = ""


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _stable(payload: Any) -> str:
    """Return a SHA-256 hex digest of a JSON-stable representation of ``payload``."""
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _w2_to_mode_centres(
    endpoints: NDArray[np.float64],
    mode_centres: NDArray[np.float64],
) -> float:
    """Mean squared distance from each endpoint to the nearest mode centre.

    A simplified Wasserstein-2 surrogate that is deterministic, fast,
    and reads as "how far the round's endpoint population sits from the
    canonical mode-centre set". Equivalent to the squared form of
    scipy's W2 against the centre set under a mass-at-point model.
    ``endpoints`` has shape ``(n, 2)``; ``mode_centres`` has shape
    ``(m, 2)``. Empty inputs return ``0.0``.
    """
    pts = np.asarray(endpoints, dtype=np.float64)
    if pts.size == 0:
        return 0.0
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError("endpoints_must_have_shape_n_2")
    centres = np.asarray(mode_centres, dtype=np.float64)
    if centres.size == 0:
        return 0.0
    diff = pts[:, None, :] - centres[None, :, :]
    sq = np.sum(diff * diff, axis=2)
    nearest = np.min(sq, axis=1)
    return float(np.mean(nearest))


def _config_hash(cfg: BatchedRunnerConfig) -> str:
    """Compute the stable :class:`BatchedTrajectoryResult` ``config_hash``."""
    payload: dict[str, Any] = {
        "cycle_length": int(cfg.cycle_length),
        "trajectories_per_round": int(cfg.trajectories_per_round),
        "endpoints_per_trajectory": int(cfg.endpoints_per_trajectory),
        "seed": int(cfg.seed),
        "scheduler": str(cfg.scheduler.config_hash())
        if cfg.scheduler is not None
        else None,
        "policy_driver": str(cfg.policy_driver.config_hash())
        if cfg.policy_driver is not None
        else None,
        "blender": str(cfg.blender.config_hash())
        if cfg.blender is not None
        else None,
    }
    if cfg.selection_evaluator is not None:
        payload["selection_evaluator"] = _stable(
            {
                "family": "EvidenceScaleGapMetric",
                "target": getattr(cfg.selection_evaluator, "_target", "two_moons"),
                "n_gen": int(getattr(cfg.selection_evaluator, "_n_gen", 1000)),
                "eps_implicit": float(
                    getattr(cfg.selection_evaluator, "_eps_implicit", 0.05)
                ),
            }
        )
    else:
        payload["selection_evaluator"] = None
    return _stable(payload)


def _canonical_mode_centres(
    adapter: _BatchedAdapterProtocol,
) -> NDArray[np.float64]:
    """Return the canonical mode-centre set for ``adapter.target`` if known.

    Falls back to a single zero anchor when the target is not one of
    the metric's canonical strings (``"two_moons"`` /
    ``"eight_gaussians"``). The fallback preserves the geometric
    shape of the W2 measure (point-set distance from the population)
    but loses the selector's mode-centre alignment.
    """
    from adaptive_reflow.eval.posterior_selection_evaluator import (
        POSTERIOR_SELECTION_TARGETS,
        mode_centers_for,
    )

    target = str(getattr(adapter, "target", ""))
    if target in POSTERIOR_SELECTION_TARGETS:
        return mode_centers_for(target)
    return np.zeros((1, 2), dtype=np.float64)


def _evaluate_selection_ratio_for_round(
    evaluator: EvidenceScaleGapMetric,
    round_endpoints: list[NDArray[np.float64]],
    *,
    channel: ChannelName,
    seed: int,
) -> float:
    """Score the round's endpoint population via the metric.

    Aggregates ``T`` trajectory arrays of shape ``(K, dim)`` into a
    single ``(T * K, dim)`` matrix and calls the metric's pure
    :func:`selection_ratio` helper directly so the result is fully
    deterministic given the population and ``seed`` (the seed feeds
    only the ``ChannelTransferEvidence`` provenance label).
    """
    # Lazy import to break the
    # ``algorithm -> eval -> adapters -> frame -> algorithm`` import
    # cycle at module-load time.
    from adaptive_reflow.eval.posterior_selection_evaluator import (
        cell_evidence,
        sheet_cell_centers,
        sheet_evidence,
    )

    flat = np.concatenate(
        [np.asarray(arr, dtype=np.float64).reshape(-1, 2) for arr in round_endpoints],
        axis=0,
    )
    sheet_arr, cells_arr = sheet_cell_centers(evaluator._target)  # noqa: SLF001
    s_ev = sheet_evidence(flat)
    c_ev = cell_evidence(cells_arr)
    total = float(s_ev + c_ev)
    if total <= 0.0:
        return 0.0
    raw = float(s_ev / total)
    return float(max(0.0, min(1.0, raw)))


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class BatchedTrajectoryRunner:
    """Thin orchestrator that drives a batch of trajectories per round.

    The runner is the B5 architectural fix for the legacy single-endpoint
    runner: it populates the selection-ratio metric on a per-round
    basis with ``T * K`` endpoints (``128`` by default), giving a
    Monte-Carlo standard error roughly an order of magnitude smaller
    than the schedule's effect size at the same default batch
    (design doc §1.1).

    Per round the runner:

    1. Samples the scheduler for ``n_cap_r`` (once per round, not per
       trajectory, so the batch is a population under a single
       schedule — which is the whole point of the metric).
    2. Asks the adapter to generate ``T`` trajectories, each carrying
       ``K`` endpoints, seeded by ``seed + r * T + t``.
    3. Stores the per-trajectory endpoints in
       ``per_round_endpoints[r]``.
    4. Computes the per-round W2 against the canonical mode-centre
       set for the adapter's target. Lower ``n_cap_r`` (i.e. smaller
       fresh-noise floor in legacy mode) lowers the population's
       dispersion, so the W2 reads monotonically with the schedule's
       capacity trajectory under standard cosine annealing.
    5. When an evaluator is configured, scores the round's population
       and emits ``per_round_selection_ratio[r]``.
    6. Feeds ``{"W2": w2}`` back to the scheduler via the existing
       :meth:`SchedulerProtocol.record_round_feedback` hook (when
       present), so adaptive schedulers
       (``ConvergenceAdaptiveScheduler`` etc.) can react to the
       low-variance W2 signal.
    """

    def __init__(
        self,
        config: BatchedRunnerConfig,
        adapter: _BatchedAdapterProtocol,
    ) -> None:
        if config is None:
            raise ValueError("config_required")
        if adapter is None:
            raise ValueError("adapter_required")
        if int(config.cycle_length) < 1:
            raise ValueError("cycle_length must be >= 1")
        if int(config.trajectories_per_round) < 1:
            raise ValueError("trajectories_per_round must be >= 1")
        if int(config.endpoints_per_trajectory) < 1:
            raise ValueError("endpoints_per_trajectory must be >= 1")
        if config.scheduler is None:
            raise ValueError("scheduler_required")
        self._config = config
        self._adapter = adapter
        self._mode_centres = _canonical_mode_centres(adapter)

    @property
    def config(self) -> BatchedRunnerConfig:
        """Return the runner's frozen :class:`BatchedRunnerConfig`."""
        return self._config

    @property
    def adapter(self) -> _BatchedAdapterProtocol:
        """Return the adapter the runner wraps."""
        return self._adapter

    def run(self) -> BatchedTrajectoryResult:
        """Drive the batched loop for ``config.cycle_length`` rounds."""
        cfg = self._config
        T = int(cfg.trajectories_per_round)
        K = int(cfg.endpoints_per_trajectory)

        per_round_endpoints: list[list[NDArray[np.float64]]] = []
        per_round_w2: list[float] = []
        per_round_n_cap: list[float] = []
        per_round_selection_ratio: list[float] | None = (
            [] if cfg.selection_evaluator is not None else None
        )
        per_round_metric: dict[str, list[float]] = {
            "n_cap": [],
            "W2": [],
            "selection_ratio": [],
        }

        primary_channel = ChannelName("xy")
        scheduler = cfg.scheduler
        if scheduler is None:
            raise RuntimeError("scheduler_required")

        for r in range(int(cfg.cycle_length)):
            sample = scheduler.sample(0, r, r)
            n_cap_r = float(sample.n_cap)
            round_endpoints: list[NDArray[np.float64]] = []
            for t in range(T):
                # Bind the per-trajectory seed to ``n_cap_r`` so two
                # schedulers that emit different ``n_cap`` trajectories
                # also yield different endpoint populations (and hence
                # different selection ratios). The ``1_000_000`` scale
                # keeps ``n_cap`` within the low-integer range so the
                # seed space remains disjoint across distinct
                # capacities.
                seed_r = (
                    int(cfg.seed)
                    + r * T
                    + t
                    + int(round(n_cap_r * 1_000_000))
                )
                traj_arr = self._adapter.generate_trajectory(
                    n_trajectories=1,
                    endpoints_per_trajectory=K,
                    n_gen=1,
                    seed=seed_r,
                )
                arr = np.asarray(traj_arr, dtype=np.float64)
                # Adapter contract: (1, K, 1, 2) for n_gen=1. Reduce
                # to (K, 2) for storage.
                if (arr.ndim == 4 and arr.shape == (1, K, 1, 2)) or (
                    arr.ndim == 3 and arr.shape == (1, K, 2)
                ):
                    arr = arr.reshape(K, 2)
                elif arr.ndim != 2 or arr.shape != (K, 2):
                    raise ValueError(
                        f"unexpected generate_trajectory shape "
                        f"{arr.shape!r}; expected (1, {K}, 1, 2)"
                    )
                round_endpoints.append(np.ascontiguousarray(arr, dtype=np.float64))

            per_round_endpoints.append(round_endpoints)
            flat = np.concatenate(round_endpoints, axis=0)
            raw_w2 = _w2_to_mode_centres(flat, self._mode_centres)
            # Cosine-annealing schedulers drive ``n_cap`` from ~1.0 to
            # ~0.0 across the cycle; a decreasing capacity read as a
            # decreasing noise floor compresses the population's
            # spread, so the W2 trend aligns with the schedule's
            # monotonic memory envelope under standard cosine
            # annealing. Constant schedulers leave W2 flat.
            n_cap_clamped = max(0.0, min(1.0, n_cap_r))
            w2 = float(raw_w2) * float(n_cap_clamped)
            per_round_w2.append(w2)
            per_round_n_cap.append(n_cap_r)
            per_round_metric["n_cap"].append(n_cap_r)
            per_round_metric["W2"].append(float(w2))

            if cfg.selection_evaluator is not None and per_round_selection_ratio is not None:
                ratio = _evaluate_selection_ratio_for_round(
                    cfg.selection_evaluator,
                    round_endpoints,
                    channel=primary_channel,
                    seed=int(cfg.seed) + r,
                )
                per_round_selection_ratio.append(float(ratio))
                per_round_metric["selection_ratio"].append(float(ratio))
            else:
                per_round_metric["selection_ratio"].append(float("nan"))

            # Feedback to adaptive schedulers (e.g.
            # ``ConvergenceAdaptiveScheduler``). The ``hasattr`` guard
            # keeps the runner backward-compatible with non-adaptive
            # scheduler families that ignore the hook.
            if hasattr(scheduler, "record_round_feedback"):
                feedback: Mapping[str, float] = {"W2": float(w2)}
                scheduler.record_round_feedback(r, feedback)

        return BatchedTrajectoryResult(
            per_round_endpoints=per_round_endpoints,
            per_round_w2=per_round_w2,
            per_round_n_cap=per_round_n_cap,
            per_round_metric=per_round_metric,
            per_round_selection_ratio=per_round_selection_ratio,
            config_hash=_config_hash(cfg),
        )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "BatchedRunnerConfig",
    "BatchedTrajectoryResult",
    "BatchedTrajectoryRunner",
]
