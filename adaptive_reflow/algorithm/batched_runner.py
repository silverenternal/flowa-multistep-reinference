"""Batched trajectory runner — populates the metric on a per-round basis.

Companion to :class:`adaptive_reflow.algorithm.runner.ReInferenceRunner`.
The legacy runner captures exactly **one** endpoint per round, leaving the
selection-ratio metric with a noise floor wider than the effect it is
supposed to measure (see ``docs/review/B5-VERIFICATION.md`` §1.1 and the
B5 design at ``docs/design/B5_BATCHED_TRAJECTORIES.md``).

This module adds a deliberately thin, additive batched runner:

* :class:`BatchedRunnerConfig` — frozen config carrying the scheduler
  and (optional) selection evaluator in addition to the four numeric
  batch-shape knobs (``cycle_length``, ``trajectories_per_round``,
  ``endpoints_per_trajectory``, ``seed``). The legacy
  ``policy_driver`` / ``blender`` slots are deprecated: they were
  never wired into the batched ``run()`` loop and are kept only so
  legacy callers do not break at construction time. Each unused slot
  emits a :class:`DeprecationWarning` at construction time. Three
  optional post-P0/P1 infrastructure toggles are exposed:

  * ``forward_noise`` — when ``True`` (default ``False``), the runner
    invokes the scheduler's ``inject_noise`` once per round so the
    forward-noise API is exercised end-to-end (P0-7).
  * ``merge_operator`` — optional
    :class:`adaptive_reflow.algorithm.merge_operator.MergeOperatorProtocol`;
    when supplied, the runner threads the schedule's ``n_cap`` through
    it each round and emits the merged value in
    ``per_round_metric["merged_beta"]``. ``None`` (default) keeps the
    legacy behaviour and omits the key.
  * ``ledger_chain`` — when ``True`` (default ``False``), the runner
    builds a SHA-256 hash chain over the per-round metric dict and
    stores the row hashes in ``ledger_chain``. ``ledger_chain_integrity``
    is set to ``True`` after a successful recompute on every run.

* :class:`BatchedTrajectoryResult` — the per-round endpoint matrix
  (round → trajectory → ``(endpoints_per_trajectory, dim)`` array),
  per-round W2 against the canonical mode centres, the per-round
  schedule ``n_cap`` and the per-round selection ratio (when an
  evaluator is supplied), plus a stable ``config_hash`` payload. When
  the optional infrastructure toggles are enabled, the result also
  carries ``ledger_chain`` (round → row hash) and
  ``ledger_chain_integrity`` (always ``True`` after recompute; raises
  on tamper).
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
* Post-P0/P1 infrastructure toggles: ``forward_noise``,
  ``merge_operator``, ``ledger_chain`` (defaults preserve legacy
  behaviour).
"""
from __future__ import annotations

import hashlib
import inspect
import json
import warnings
from collections.abc import Callable, Mapping
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
    from adaptive_reflow.algorithm.merge_operator import MergeOperatorProtocol
    from adaptive_reflow.eval.posterior_selection_evaluator import (
        EvidenceScaleGapMetric,
    )
    from adaptive_reflow.eval.w2 import W2EstimatorProtocol


DEFAULT_W2_FAMILY: str = "mode_centre_mse"
"""Mirror of :data:`adaptive_reflow.eval.w2.DEFAULT_W2_FAMILY`.

Duplicated as a bare string rather than imported because
``adaptive_reflow.eval`` imports the adapters, which import the frame,
which imports this package -- the same cycle the lazy imports elsewhere
in this module break. :func:`_build_w2_estimator` asserts the two
constants agree the first time a non-default estimator is built, so the
duplication cannot silently drift.
"""


def _scheduler_accepts_paper_quantities(scheduler: Any) -> bool:
    """Return ``True`` when ``scheduler.record_round_feedback`` accepts the
    ``paper_quantities`` kwarg (Wave 38 MEDIUM-8 dispatcher).

    Introspects the bound method's signature once per scheduler
    instance; the caller caches the result on the scheduler so the
    per-round cost is constant. Mirrors the helper of the same name
    in :mod:`adaptive_reflow.algorithm.sequential`.
    """
    method = getattr(scheduler, "record_round_feedback", None)
    if method is None or not callable(method):
        return False
    try:
        sig = inspect.signature(method)
    except (TypeError, ValueError):
        return False
    return "paper_quantities" in sig.parameters


def _scheduler_accepts_metrics(scheduler: Any) -> bool:
    """Return ``True`` when ``scheduler.record_round_feedback`` accepts the
    ``metrics`` kwarg (Wave 38 MEDIUM-8 dispatcher).

    Mirror of :func:`_scheduler_accepts_paper_quantities`. A scheduler
    that accepts only ``paper_quantities`` (e.g. the fully-integrated
    :class:`PaperRatioAdaptiveScheduler`) returns ``False`` here so the
    dispatcher passes the paper-quantities payload only.
    """
    method = getattr(scheduler, "record_round_feedback", None)
    if method is None or not callable(method):
        return False
    try:
        sig = inspect.signature(method)
    except (TypeError, ValueError):
        return False
    return "metrics" in sig.parameters


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


@runtime_checkable
class BatchedVectorisedAdapterProtocol(Protocol):
    """OPTIONAL capability surface for the vectorised batched runner (P0 #8).

    An adapter that can integrate every trajectory of a round in one
    BLAS-vectorised call -- rather than ``T`` sequential
    :meth:`_BatchedAdapterProtocol.generate_trajectory` calls -- declares
    it by implementing :meth:`generate_trajectories_batched`.

    The protocol is **purely additive**: adapters that do not implement
    it keep working unchanged, and :class:`BatchedTrajectoryRunner` only
    consults it when the caller sets
    ``BatchedRunnerConfig.vectorised=True``. The runner falls back to the
    sequential loop (and reports ``vectorised_rounds == 0`` on the
    result) whenever the capability is absent, so opting in can never
    break a run.

    CONTRACT -- bit-equivalence: for the same ``seeds`` tuple the
    returned stack MUST equal, within ``1e-9``, the stack the caller
    would obtain by looping ``generate_trajectory(seed=s)`` over
    ``seeds``. That equivalence is what lets the runner treat the
    vectorised path as a pure *performance* switch rather than a
    behavioural one, and it is asserted directly in the runner tests.
    """

    def generate_trajectories_batched(
        self,
        *,
        seeds: tuple[int, ...],
        endpoints_per_trajectory: int,
        n_gen: int,
    ) -> NDArray[np.float64]:
        """Return ``(len(seeds), endpoints_per_trajectory, n_gen, dim)``."""
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
        Deprecated. Retained for protocol parity with the legacy runner;
        not exercised in the batched ``run()`` loop (the batch axis lives
        outside the engine). Supplying a non-``None`` value emits a
        :class:`DeprecationWarning` at construction time. Will be
        removed in a future release.
    blender:
        Deprecated. Retained for protocol parity with the legacy runner;
        not exercised in the batched ``run()`` loop. Same deprecation
        status as ``policy_driver``.
    selection_evaluator:
        Optional :class:`EvidenceScaleGapMetric`. When supplied, the
        runner scores the round's endpoint population and emits the
        canonical ``selection_ratio`` per round.
    seed:
        Base seed. Per-trajectory effective seed is
        ``seed + r * T + t`` for round ``r`` and trajectory ``t``.
    outer_cycle_id:
        Identifier of the outer cycle. Forwarded to
        ``scheduler.sample`` as its first positional argument so two
        runners configured with different cycle IDs but the same
        ``seed`` produce distinguishable endpoint populations. The
        default ``0`` preserves the legacy hard-coded behaviour.
    """

    cycle_length: int = 20
    trajectories_per_round: int = 8
    endpoints_per_trajectory: int = 16
    scheduler: SchedulerProtocol | None = None
    policy_driver: PolicyDriverProtocol | None = None
    blender: RestartBlenderProtocol | None = None
    selection_evaluator: EvidenceScaleGapMetric | None = None
    seed: int = 42
    outer_cycle_id: int = 0
    #: Post-P0/P1 infrastructure toggle. When ``True`` the runner
    #: invokes ``scheduler.inject_noise`` once per round so the
    #: forward-noise API is exercised end-to-end (P0-7). ``False``
    #: (default) preserves the legacy behaviour where the runner only
    #: generates trajectories.
    forward_noise: bool = False
    #: Post-P0/P1 infrastructure toggle. Optional
    #: :class:`MergeOperatorProtocol` (typically
    #: :class:`BoundedMergeOperator` or :class:`IdentityOperator`);
    #: when supplied, the runner threads the schedule's ``n_cap``
    #: through it each round and emits the merged value in
    #: ``per_round_metric["merged_beta"]``. ``None`` (default) keeps
    #: the legacy behaviour and omits the key.
    merge_operator: MergeOperatorProtocol | None = None
    #: Post-P0/P1 infrastructure toggle. When ``True`` the runner
    #: builds a SHA-256 hash chain over the per-round metric dict and
    #: stores the row hashes in ``result.ledger_chain``. The
    #: ``ledger_chain_integrity`` flag on the result is set to
    #: ``True`` after a successful recompute on every run (P0-8).
    ledger_chain: bool = False
    #: P0 #3 -- W2 estimator family key (see
    #: :data:`adaptive_reflow.eval.w2.W2_REGISTRY`). Defaults to the
    #: legacy ``"mode_centre_mse"`` surrogate so every existing run stays
    #: byte-identical; set to ``"projection_free"`` / ``"kernelized"`` /
    #: ``"sinkhorn"`` to opt into a genuine Wasserstein-2 estimate.
    w2_family: str = DEFAULT_W2_FAMILY
    #: P0 #3 -- constructor kwargs forwarded to the W2 estimator factory
    #: (e.g. ``{"n_projections": 256}``). ``None`` uses the family's own
    #: defaults.
    w2_kwargs: Mapping[str, Any] | None = None
    #: P0 #8 -- vectorised trajectory generation. When ``True`` and the
    #: adapter implements :class:`BatchedVectorisedAdapterProtocol`, the
    #: runner asks for all ``T`` trajectories of a round in a single
    #: BLAS-vectorised call instead of ``T`` sequential ones. Falls back
    #: to the sequential loop when the adapter does not declare the
    #: capability, so opting in is always safe.
    vectorised: bool = False
    #: Wave 35 FIX-2 -- convergence-aware early termination. When
    #: ``True`` and the scheduler exposes ``should_terminate_round``,
    #: the runner stops the round loop as soon as the scheduler reports
    #: that the cycle's metric has plateaued, instead of always paying
    #: ``cycle_length * nfe_per_round``. ``False`` (default) preserves
    #: the legacy open-loop behaviour exactly, so no existing run or
    #: pinned vector changes. See
    #: ``docs/audit/saturation-improvement-plan.md`` §2 FIX-2.
    early_termination: bool = False

    def __post_init__(self) -> None:
        """Emit deprecation warnings for unused legacy slots.

        ``policy_driver`` and ``blender`` were never wired into the
        batched ``run()`` loop; the batch axis lives outside the engine
        and the runner's selection-ratio metric is computed from the
        endpoint population directly (P2-12 audit). They are kept on
        the dataclass so legacy callers do not break at construction
        time, but supplying a non-``None`` value emits a
        :class:`DeprecationWarning` so callers can migrate.
        """
        if self.policy_driver is not None:
            warnings.warn(
                "BatchedRunnerConfig.policy_driver is deprecated and "
                "unused by BatchedTrajectoryRunner.run(); the batched "
                "loop operates outside the engine's policy-driver path. "
                "Pass ``policy_driver=None`` to silence this warning. "
                "The slot will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
        if self.blender is not None:
            warnings.warn(
                "BatchedRunnerConfig.blender is deprecated and unused "
                "by BatchedTrajectoryRunner.run(); the batched loop "
                "operates outside the engine's blender path. Pass "
                "``blender=None`` to silence this warning. The slot "
                "will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )


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
    #: Optional per-round SHA-256 row hashes (P0-8). Populated only
    #: when ``BatchedRunnerConfig.ledger_chain=True``; empty otherwise.
    ledger_chain: list[str] = field(default_factory=list)
    #: ``True`` after a successful recompute on every run (P0-8).
    #: ``True`` even when ``ledger_chain`` is empty (the default
    #: ``False`` config does not exercise the ledger, so integrity
    #: trivially holds).
    ledger_chain_integrity: bool = True
    #: P0 #3 -- the W2 estimator family actually used for
    #: ``per_round_w2``. ``"mode_centre_mse"`` on the legacy path.
    w2_family: str = DEFAULT_W2_FAMILY
    #: P0 #8 -- number of rounds served by the adapter's vectorised
    #: batch call. ``0`` means every round fell back to the sequential
    #: per-trajectory loop (either because ``vectorised`` was ``False``
    #: or because the adapter does not implement
    #: :class:`BatchedVectorisedAdapterProtocol`).
    vectorised_rounds: int = 0
    #: Wave 35 FIX-2 -- number of rounds actually executed. Equal to
    #: ``cfg.cycle_length`` unless ``early_termination`` was enabled and
    #: the scheduler reported convergence, in which case it is smaller.
    rounds_run: int = 0
    #: Wave 35 FIX-2 -- ``True`` when the round loop exited early
    #: because the scheduler reported convergence. Always ``False``
    #: when ``early_termination`` was not enabled.
    early_terminated: bool = False


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


def _reshape_round_endpoints(
    traj_arr: NDArray[np.float64],
    endpoints_per_trajectory: int,
) -> NDArray[np.float64]:
    """Normalise one adapter trajectory to a contiguous ``(K, 2)`` block.

    Adapters may return the canonical ``(1, K, 1, 2)`` shape, the
    ``n_gen``-squeezed ``(1, K, 2)``, the trajectory-axis-squeezed
    ``(K, 1, 2)`` that falls out of slicing a batched
    ``(T, K, 1, 2)`` stack, or an already-flat ``(K, 2)``. Anything
    else is a contract violation and raises, so a silently-misshaped
    population can never reach the W2 estimator.
    """
    arr = np.asarray(traj_arr, dtype=np.float64)
    k = int(endpoints_per_trajectory)
    if (arr.ndim == 4 and arr.shape == (1, k, 1, 2)) or (
        arr.ndim == 3 and arr.shape in {(1, k, 2), (k, 1, 2)}
    ):
        arr = arr.reshape(k, 2)
    elif arr.ndim != 2 or arr.shape != (k, 2):
        raise ValueError(
            f"unexpected generate_trajectory shape {arr.shape!r}; "
            f"expected (1, {k}, 1, 2)"
        )
    return np.ascontiguousarray(arr, dtype=np.float64)


def _build_w2_estimator(cfg: BatchedRunnerConfig) -> W2EstimatorProtocol | None:
    """Return the configured W2 estimator, or ``None`` for the legacy path.

    ``None`` means "keep calling :func:`_w2_to_mode_centres` directly",
    which is what happens when ``cfg.w2_family`` is the legacy
    ``"mode_centre_mse"`` family and no ``w2_kwargs`` were supplied. The
    default run therefore stays byte-identical, pays no extra import
    cost, and puts no new module in the hot loop for callers who did not
    opt in.

    The :mod:`adaptive_reflow.eval.w2` import is deferred to call time:
    ``adaptive_reflow.eval`` pulls in the adapters, which pull in the
    frame, which pulls in this package.
    """
    family = str(cfg.w2_family).strip().lower()
    kwargs = dict(cfg.w2_kwargs or {})
    if family == DEFAULT_W2_FAMILY and not kwargs:
        return None
    from adaptive_reflow.eval import w2 as _w2

    if _w2.DEFAULT_W2_FAMILY != DEFAULT_W2_FAMILY:  # pragma: no cover - drift guard
        raise RuntimeError(
            "batched_runner.DEFAULT_W2_FAMILY drifted from "
            f"eval.w2.DEFAULT_W2_FAMILY ({DEFAULT_W2_FAMILY!r} != "
            f"{_w2.DEFAULT_W2_FAMILY!r})"
        )
    return _w2.build_w2_estimator(family, **kwargs)


def _config_hash(cfg: BatchedRunnerConfig) -> str:
    """Compute the stable :class:`BatchedTrajectoryResult` ``config_hash``."""
    payload: dict[str, Any] = {
        "cycle_length": int(cfg.cycle_length),
        "trajectories_per_round": int(cfg.trajectories_per_round),
        "endpoints_per_trajectory": int(cfg.endpoints_per_trajectory),
        "seed": int(cfg.seed),
        "outer_cycle_id": int(cfg.outer_cycle_id),
        "scheduler": str(cfg.scheduler.config_hash())
        if cfg.scheduler is not None
        else None,
        "policy_driver": str(cfg.policy_driver.config_hash())
        if cfg.policy_driver is not None
        else None,
        "blender": str(cfg.blender.config_hash())
        if cfg.blender is not None
        else None,
        "forward_noise": bool(cfg.forward_noise),
        "merge_operator": (
            type(cfg.merge_operator).__name__
            if cfg.merge_operator is not None
            else None
        ),
        "ledger_chain": bool(cfg.ledger_chain),
    }
    # Additive keys are folded in ONLY when the caller opted out of the
    # legacy defaults, so every pre-existing ``config_hash`` (and the
    # golden fixtures pinned against it) stays byte-identical.
    if str(cfg.w2_family).strip().lower() != DEFAULT_W2_FAMILY or cfg.w2_kwargs:
        payload["w2_family"] = str(cfg.w2_family).strip().lower()
        payload["w2_kwargs"] = _stable(dict(cfg.w2_kwargs or {}))
    if cfg.early_termination:
        payload["early_termination"] = True
    if cfg.vectorised:
        payload["vectorised"] = True
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
        *,
        paper_quantities_fn: Callable[[int], Mapping[str, float] | None] | None = None,
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
        if paper_quantities_fn is not None and not callable(paper_quantities_fn):
            raise ValueError(
                "paper_quantities_fn must be callable or None, got "
                f"{paper_quantities_fn!r}"
            )
        self._config = config
        self._adapter = adapter
        # Wave 38 MEDIUM-8: optional callable ``paper_quantities_fn(round)
        # -> Mapping | None`` invoked per round so the runner can
        # forward literal paper quantities (``sheet_A`` / ``cell_C`` /
        # ``packing_B`` / ``sheet_vs_cells_proxy``) to the scheduler's
        # ``record_round_feedback`` hook. ``None`` (default) preserves
        # the legacy behaviour where only ``{"W2": float(w2)}`` is
        # forwarded, so paper-quantity-aware schedulers stay dormant
        # until the caller wires the carrier explicitly.
        self._paper_quantities_fn = paper_quantities_fn
        self._mode_centres = _canonical_mode_centres(adapter)
        # P0 #3 -- resolved once per runner so the per-round loop pays
        # no factory cost. ``None`` keeps the legacy inline surrogate.
        self._w2_estimator = _build_w2_estimator(config)
        # P0 #8 -- capability probe, also resolved once. An adapter that
        # does not advertise the batched entry point silently keeps the
        # sequential path.
        self._vectorised = bool(config.vectorised) and callable(
            getattr(adapter, "generate_trajectories_batched", None)
        )

    @property
    def config(self) -> BatchedRunnerConfig:
        """Return the runner's frozen :class:`BatchedRunnerConfig`."""
        return self._config

    @property
    def adapter(self) -> _BatchedAdapterProtocol:
        """Return the adapter the runner wraps."""
        return self._adapter

    def _estimate_w2(self, flat: NDArray[np.float64]) -> float:
        """Return the round's raw W2 under the configured family (P0 #3).

        Dispatches to the registered :class:`W2EstimatorProtocol` when
        the caller opted into a non-legacy family, and otherwise calls
        :func:`_w2_to_mode_centres` verbatim so the default run is
        byte-identical to every historical result.
        """
        if self._w2_estimator is None:
            return _w2_to_mode_centres(flat, self._mode_centres)
        return float(self._w2_estimator.estimate(flat, self._mode_centres))

    def _generate_round_vectorised(
        self,
        seeds: tuple[int, ...],
        endpoints_per_trajectory: int,
    ) -> list[NDArray[np.float64]]:
        """Generate a whole round's trajectories in one adapter call (P0 #8).

        Only reached when :attr:`_vectorised` is ``True``, i.e. the
        caller opted in AND the adapter advertises
        :class:`BatchedVectorisedAdapterProtocol`. The result is split
        back into the same ``list[(K, 2)]`` shape the sequential path
        produces, so everything downstream (W2, selection ratio, ledger)
        is unaware of which path ran.
        """
        # The attribute is guaranteed present: ``self._vectorised`` is
        # only ``True`` after the constructor's capability probe found a
        # callable here. ``_BatchedAdapterProtocol`` does not declare it
        # (it is the optional capability), hence the dynamic lookup.
        batched = self._adapter.generate_trajectories_batched  # type: ignore[attr-defined]
        stacked = np.asarray(
            batched(
                seeds=tuple(int(x) for x in seeds),
                endpoints_per_trajectory=int(endpoints_per_trajectory),
                n_gen=1,
            ),
            dtype=np.float64,
        )
        if stacked.shape[0] != len(seeds):
            raise ValueError(
                f"generate_trajectories_batched returned {stacked.shape[0]} "
                f"trajectories for {len(seeds)} seeds"
            )
        return [
            _reshape_round_endpoints(stacked[t], endpoints_per_trajectory)
            for t in range(len(seeds))
        ]

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
        # ``per_round_metric`` ALWAYS carries the three core series
        # (``n_cap``, ``W2``, and ``selection_ratio``) when an
        # evaluator is configured. When no evaluator is configured,
        # the ``selection_ratio`` key is OMITTED (rather than populated
        # with ``NaN``) so downstream consumers can detect "no
        # evaluator" via ``"selection_ratio" not in result.per_round_metric``
        # without having to special-case ``NaN`` (P1-9 audit). The
        # ``per_round_selection_ratio`` field remains ``None`` for the
        # no-evaluator path.
        per_round_metric: dict[str, list[float]] = {
            "n_cap": [],
            "W2": [],
        }
        if cfg.selection_evaluator is not None:
            per_round_metric["selection_ratio"] = []
        if cfg.merge_operator is not None:
            per_round_metric["merged_beta"] = []

        primary_channel = ChannelName("xy")
        scheduler = cfg.scheduler
        if scheduler is None:
            raise RuntimeError("scheduler_required")

        # P0-7 forward noise generator: deterministic
        # ``np.random.Generator`` rooted at ``cfg.seed``. Used only
        # when ``cfg.forward_noise`` is ``True``; one
        # ``standard_normal`` draw per round so the per-round
        # injection is reproducible across replays.
        forward_noise_generator = np.random.default_rng(int(cfg.seed))

        # P0-8 ledger chain accumulator: SHA-256 over the JSON-stable
        # representation of each round's metric dict, chained to the
        # previous round's hash. Empty when ``cfg.ledger_chain`` is
        # ``False``.
        ledger_chain: list[str] = []
        prev_ledger_row_hash: str | None = None

        # P0 #8 -- how many rounds the adapter's vectorised batch call
        # actually served. Reported on the result so a caller can verify
        # the fast path engaged rather than silently falling back.
        vectorised_rounds = 0

        # Wave 35 FIX-2 -- round-loop bookkeeping. ``rounds_run`` is
        # updated at the end of each iteration; the initial ``0``
        # covers a ``cycle_length`` of 0 rounds (which the config
        # validation forbids, but the accounting stays honest).
        rounds_run = 0
        early_terminated = False

        for r in range(int(cfg.cycle_length)):
            sample = scheduler.sample(int(cfg.outer_cycle_id), r, r)
            n_cap_r = float(sample.n_cap)
            round_endpoints: list[NDArray[np.float64]] = []
            # Per-trajectory seeds. Bound to ``n_cap_r`` AND
            # ``outer_cycle_id`` so two schedulers that emit different
            # ``n_cap`` trajectories, or two runners configured with
            # different ``outer_cycle_id`` values, yield different
            # endpoint populations (and hence different selection
            # ratios). The ``1_000_000`` scale keeps ``n_cap`` within the
            # low-integer range so the seed space stays disjoint across
            # distinct capacities; the ``* 100_000_000`` term carves out
            # an entirely disjoint seed range per outer cycle.
            seeds_r = tuple(
                int(cfg.seed)
                + r * T
                + t
                + int(round(n_cap_r * 1_000_000))
                + int(cfg.outer_cycle_id) * 100_000_000
                for t in range(T)
            )
            if self._vectorised:
                # P0 #8 -- one BLAS-vectorised call for the whole round.
                # The seeds are exactly the sequential path's, so the two
                # paths are numerically equivalent (asserted in the
                # runner tests): this is a pure performance switch.
                round_endpoints = self._generate_round_vectorised(seeds_r, K)
                vectorised_rounds += 1
            else:
                for t in range(T):
                    traj_arr = self._adapter.generate_trajectory(
                        n_trajectories=1,
                        endpoints_per_trajectory=K,
                        n_gen=1,
                        seed=seeds_r[t],
                    )
                    round_endpoints.append(_reshape_round_endpoints(traj_arr, K))

            per_round_endpoints.append(round_endpoints)
            flat = np.concatenate(round_endpoints, axis=0)
            raw_w2 = self._estimate_w2(flat)
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

            # P0-7 — forward noise injection (symmetric forward step).
            # The runner consumes one ``standard_normal`` draw per round
            # so the injection is reproducible across replays. The
            # runner only exercises this code path when the caller
            # explicitly opted into ``cfg.forward_noise`` (default
            # ``False``); the legacy no-injection path is preserved.
            if cfg.forward_noise and hasattr(scheduler, "inject_noise"):
                _ = scheduler.inject_noise(
                    np.zeros(2, dtype=np.float64),
                    sample.as_cosine_schedule_sample(),
                    generator=forward_noise_generator,
                )

            # P0-3 + P0-7 — clip-and-audit merge operator. When the
            # caller supplied a ``merge_operator``, the runner threads
            # the schedule's ``n_cap`` through it each round (so the
            # operator is reachable from the batched loop) and records
            # the merged value under ``per_round_metric["merged_beta"]``.
            # The audit_codes list is captured locally; non-clamping
            # operators (identity / EMA) never emit on legitimate input.
            if cfg.merge_operator is not None:
                merge_audit: list[str] = []
                merged_beta = float(
                    cfg.merge_operator.merge(
                        prev=0.0 if r == 0 else float(
                            per_round_metric["merged_beta"][r - 1]
                        ),
                        dynamic=float(n_cap_r),
                        cap=float(n_cap_r),
                        floor=float(sample.n_min),
                        delta_cap_up=1.0,
                        delta_cap_down=1.0,
                        audit_codes=merge_audit,
                    )
                )
                per_round_metric["merged_beta"].append(float(merged_beta))
                del merge_audit  # silence unused-collector lint; non-clamping ops stay silent

            if cfg.selection_evaluator is not None and per_round_selection_ratio is not None:
                ratio = _evaluate_selection_ratio_for_round(
                    cfg.selection_evaluator,
                    round_endpoints,
                    channel=primary_channel,
                    seed=int(cfg.seed) + r,
                )
                per_round_selection_ratio.append(float(ratio))
                per_round_metric["selection_ratio"].append(float(ratio))
            # No-evaluator path: the ``selection_ratio`` key is omitted
            # from ``per_round_metric`` (P1-9 audit). Downstream
            # consumers can detect "no evaluator" via
            # ``"selection_ratio" not in result.per_round_metric``
            # rather than special-casing ``NaN``.

            # P0-8 — hash-chained ledger over per-round metrics. Each
            # row hashes the JSON-stable representation of the round's
            # flat metric snapshot, chained to ``prev_ledger_row_hash``
            # (P0-8 contract). ``None`` anchors round 0.
            if cfg.ledger_chain:
                ledger_payload: dict[str, Any] = {
                    "round": int(r),
                    "n_cap": float(n_cap_r),
                    "W2": float(w2),
                    "outer_cycle_id": int(cfg.outer_cycle_id),
                    "forward_noise": bool(cfg.forward_noise),
                    "merge_operator": (
                        type(cfg.merge_operator).__name__
                        if cfg.merge_operator is not None
                        else None
                    ),
                    "selection_ratio": (
                        float(per_round_selection_ratio[-1])
                        if cfg.selection_evaluator is not None
                        and per_round_selection_ratio is not None
                        else None
                    ),
                    "prev_ledger_row_hash": prev_ledger_row_hash,
                }
                row_text = json.dumps(ledger_payload, sort_keys=True, default=str)
                row_hash = hashlib.sha256(row_text.encode("utf-8")).hexdigest()
                ledger_chain.append(row_hash)
                prev_ledger_row_hash = row_hash

            # Feedback to adaptive schedulers (e.g.
            # ``ConvergenceAdaptiveScheduler``). The ``hasattr`` guard
            # keeps the runner backward-compatible with non-adaptive
            # scheduler families that ignore the hook.
            if hasattr(scheduler, "record_round_feedback"):
                feedback: Mapping[str, float] = {"W2": float(w2)}
                # Wave 38 MEDIUM-8: when ``paper_quantities_fn`` was
                # supplied to the runner constructor, resolve it for
                # the current round and forward the literal paper
                # quantities alongside ``feedback``. The legacy
                # ``metrics``-only call is preserved when the callable
                # returns ``None`` (or no callable was supplied), so
                # every existing scheduler keeps working unchanged.
                pq_payload: Mapping[str, float] | None = None
                if self._paper_quantities_fn is not None:
                    try:
                        pq_payload = self._paper_quantities_fn(int(r))
                    except Exception:
                        pq_payload = None
                if pq_payload is None:
                    scheduler.record_round_feedback(r, feedback)
                else:
                    # Mirror the dispatcher pattern in
                    # :class:`SequentialScheduler`: inspect the
                    # scheduler's ``record_round_feedback`` signature so
                    # we forward *only* the kwargs it actually accepts.
                    # A scheduler that takes ``metrics`` only (legacy
                    # family) keeps the metrics-only call; one that
                    # takes ``paper_quantities`` only (the fully
                    # integrated :class:`PaperRatioAdaptiveScheduler`)
                    # receives the paper-quantities payload only.
                    accepts_metrics = _scheduler_accepts_metrics(scheduler)
                    accepts_pq = _scheduler_accepts_paper_quantities(scheduler)
                    kwargs: dict[str, object] = {
                        "round_in_cycle": int(r),
                    }
                    if accepts_metrics:
                        kwargs["metrics"] = feedback
                    if accepts_pq:
                        kwargs["paper_quantities"] = pq_payload
                    try:
                        scheduler.record_round_feedback(**kwargs)
                    except TypeError:
                        # Defensive fallback — keep the runner
                        # backward-compatible with any scheduler family
                        # whose signature changed under us.
                        try:
                            scheduler.record_round_feedback(
                                int(r), feedback
                            )
                        except TypeError:
                            scheduler.record_round_feedback(
                                int(r), paper_quantities=pq_payload
                            )

            # Wave 35 FIX-2 -- convergence-aware early termination.
            # Opt-in only (``cfg.early_termination``), and only for
            # schedulers that expose the hook, so the legacy open-loop
            # behaviour is preserved bit-for-bit by default. The check
            # runs AFTER the feedback call so the scheduler judges on a
            # history that includes the round just completed.
            rounds_run = r + 1
            if cfg.early_termination and hasattr(
                scheduler, "should_terminate_round"
            ):
                if bool(scheduler.should_terminate_round(r)):
                    early_terminated = True
                    break

        # P0-8 — verify the ledger chain integrity on every run when
        # ``ledger_chain=True``. A tamper-evident recompute confirms
        # that the runner-built chain round-trips byte-for-byte. The
        # flag is also ``True`` when ``ledger_chain=False`` (trivially
        # empty chain holds vacuously).
        chain_ok = True
        if cfg.ledger_chain:
            re_prev: str | None = None
            for r, expected in enumerate(ledger_chain):
                ratio_val = (
                    float(per_round_selection_ratio[r])
                    if cfg.selection_evaluator is not None
                    and per_round_selection_ratio is not None
                    else None
                )
                payload: dict[str, Any] = {
                    "round": int(r),
                    "n_cap": float(per_round_n_cap[r]),
                    "W2": float(per_round_w2[r]),
                    "outer_cycle_id": int(cfg.outer_cycle_id),
                    "forward_noise": bool(cfg.forward_noise),
                    "merge_operator": (
                        type(cfg.merge_operator).__name__
                        if cfg.merge_operator is not None
                        else None
                    ),
                    "selection_ratio": ratio_val,
                    "prev_ledger_row_hash": re_prev,
                }
                re_text = json.dumps(payload, sort_keys=True, default=str)
                re_hash = hashlib.sha256(re_text.encode("utf-8")).hexdigest()
                if re_hash != expected:
                    chain_ok = False
                    break
                re_prev = expected

        return BatchedTrajectoryResult(
            per_round_endpoints=per_round_endpoints,
            per_round_w2=per_round_w2,
            per_round_n_cap=per_round_n_cap,
            per_round_metric=per_round_metric,
            per_round_selection_ratio=per_round_selection_ratio,
            config_hash=_config_hash(cfg),
            ledger_chain=list(ledger_chain),
            ledger_chain_integrity=bool(chain_ok),
            w2_family=str(cfg.w2_family).strip().lower(),
            vectorised_rounds=int(vectorised_rounds),
            rounds_run=int(rounds_run),
            early_terminated=bool(early_terminated),
        )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "BatchedRunnerConfig",
    "BatchedTrajectoryResult",
    "BatchedTrajectoryRunner",
    "BatchedVectorisedAdapterProtocol",
    "DEFAULT_W2_FAMILY",
]
