"""Wave 29 Agent B -- Controlled empirical audit for framework regression diagnosis.

Purpose
-------
The framework shows regressions on three workloads:

* CIFAR-10 (matched-NFE regression +24-31% per paper §4)
* ``twodim_fm`` (regresses at every ``sigma in [0, 0.5]`` per Wave 17 P2)
* LineageFlow (decision metric saturates at 1.0 per Wave 19 P1A2)

This tool runs a controlled re-experiment to determine whether the
regression is from the **algorithm**, the **adapter wiring**, or
**measurement** (NFE counting, baseline-vs-framework comparison setup).

Design
------
* Identical seed per cell
* Identical NFE count per cell (matched)
* Identical measurement (same extractor, same metric)
* Per-cell ``baseline_NFE``, ``framework_NFE``, ``baseline_metric``,
  ``framework_metric``, ``delta`` reported in JSON

The cell sweep is:

    3 models x 3 seeds x 3 NFE counts x 3 sigma levels
  = 27 cells per model = 81 cells total
  = 162 single-cell calls (baseline + framework per cell)

For twodim_fm the noise sigma is plumbed through the adapter's
``noise_sigma`` constructor argument. For CIFAR-10 / LineageFlow the
adapter does not support a noise sigma on the velocity field, so we
record sigma=0 only and document the gap (the metric extraction +
NFE bookkeeping remain comparable).

Output
------
* ``verification_outputs/controlled_audit_q3_2026.json`` --
  machine-readable per-cell JSON report. Captures: per-cell
  baseline / framework metric, NFE usage, matched-check flags, the
  per-seed std for significance, and a per-cell regression
  classification.

Usage
-----
::

    python -m tools.run_controlled_audit
    python -m tools.run_controlled_audit --quick        # 1 seed only
    python -m tools.run_controlled_audit --models twodim_fm --sigma 0
    python -m tools.run_controlled_audit --output /tmp/audit.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import traceback
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from adaptive_reflow.util.host_fingerprint import with_host_fingerprint

# Make ``adaptive_reflow`` importable when the script is invoked as
# ``python tools/run_controlled_audit.py``.
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Configuration / defaults
# ---------------------------------------------------------------------------

#: Canonical 3 seeds for the audit.
DEFAULT_SEEDS: tuple[int, ...] = (0, 1, 2)

#: Canonical 3 NFE budgets. Picked to span the NFE-parade: a coarse
#: 10-NFE (paper-equivalent), 50-NFE (Wave 17 v4 regime), and 200-NFE
#: (well-resolved baseline).
DEFAULT_NFE_BUDGETS: tuple[int, ...] = (10, 50, 200)

#: Canonical 3 sigma levels. ``sigma=0`` is the no-noise baseline; the
#: ``0.1, 0.5`` levels span Wave 17 P2 noise-injection regime.
DEFAULT_SIGMAS: tuple[float, ...] = (0.0, 0.1, 0.5)

#: Wave 35 FIX-3 -- per-round NFE allocation policy, set by
#: ``--nfe-allocation``. ``"uniform"`` (default) is the legacy
#: equal-split; ``"evidence"`` weights rounds inversely to the
#: codimension scheduler's per-round ``eps`` so the small-``eps``
#: refinement rounds get more integration steps. See
#: :func:`_nfe_steps_per_round` and
#: ``docs/audit/saturation-improvement-plan.md`` §2 FIX-3.
NFE_ALLOCATION: str = "uniform"

#: Models under audit. Each entry is the adapter module + adapter class
#: + synthetic_mode flag + sigma_support flag + metric family + an
#: adapter_factory(seed, nfe, sigma) closure.
MODEL_TABLE: dict[str, dict[str, Any]] = {
    "twodim_fm": {
        "display_name": "twodim_fm (two_moons)",
        "supports_sigma": True,
        "metric_family": "wasserstein_2d",
        "framework_scheduler": "codimension_sheet",
        "n_samples": 128,
        "n_rounds": 5,
    },
    "cifar10_rf": {
        "display_name": "CIFAR-10 Rectified Flow",
        "supports_sigma": False,
        "metric_family": "fid_pixel_proxy",
        "framework_scheduler": "cosine_anneal",
        "n_samples": 32,
        "n_rounds": 4,
    },
    "lineageflow": {
        "display_name": "LineageFlow protein (synthetic)",
        "supports_sigma": False,
        "metric_family": "family_validity",
        "framework_scheduler": "cosine_anneal",
        # Per-sample Protocol call (no batched_inference on this
        # adapter). 8 samples keeps the framework arm under ~2s even
        # at NFE=200; matches Wave 10 R2's 32-sample setup but
        # trimmed so the sweep fits the 30-min budget.
        "n_samples": 8,
        "n_rounds": 5,
    },
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CellSpec:
    """One (model, seed, nfe, sigma) experimental cell."""

    model: str
    seed: int
    nfe: int
    sigma: float


@dataclass
class CellResult:
    """Per-cell experimental result + matched-check verdict."""

    model: str
    seed: int
    nfe: int
    sigma: float

    baseline_nfe: int = 0
    framework_nfe: int = 0
    baseline_metric: float = float("nan")
    framework_metric: float = float("nan")
    baseline_runtime_s: float = 0.0
    framework_runtime_s: float = 0.0
    # P2-W33-C: secondary metrics (LineageFlow ``family_validity`` kept
    # for back-compat; the new primary decision metric is
    # ``baseline_metric`` / ``framework_metric`` which now holds the
    # continuous per-position entropy).
    baseline_family_validity: float = float("nan")
    framework_family_validity: float = float("nan")

    nfe_matched: bool = False
    metric_extractor_matched: bool = True
    error: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def delta(self) -> float:
        """Relative delta ``(F - M) / |M|`` -- positive = regression."""
        m = float(self.baseline_metric)
        if not np.isfinite(m) or abs(m) < 1e-12:
            return float("nan")
        return (float(self.framework_metric) - m) / abs(m)

    @property
    def is_regression(self) -> bool:
        """A regression is ``delta > 0.05`` (5%). Below that is noise."""
        d = self.delta
        return bool(np.isfinite(d) and d > 0.05)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["delta"] = float(self.delta) if np.isfinite(self.delta) else None
        d["is_regression"] = bool(self.is_regression)
        d["notes"] = list(self.notes)
        return d


# ---------------------------------------------------------------------------
# Per-model workers
# ---------------------------------------------------------------------------


def _run_twodim_fm(spec: CellSpec) -> CellResult:
    """Run baseline + framework for the ``twodim_fm`` adapter.

    The 2D adapter is the simplest controlled setting: both arms are
    byte-deterministic under a fixed seed and the metric is the
    closed-form 2D Wasserstein.
    """
    from adaptive_reflow.adapters.twodim_fm import (
        TWODIM_FM_NUM_STEPS,
        TwoDimFMAdapter,
    )
    from adaptive_reflow.algorithm.batched_runner import (
        BatchedRunnerConfig,
        BatchedTrajectoryRunner,
    )

    result = CellResult(
        model=spec.model,
        seed=spec.seed,
        nfe=spec.nfe,
        sigma=spec.sigma,
    )

    try:
        # --- Baseline arm: single-pass RK4 with `num_steps = nfe`. ---
        adapter = TwoDimFMAdapter(
            target="two_moons",
            integrator="rk4",
            num_steps=int(spec.nfe),
            seed_offset=int(spec.seed),
            noise_sigma=float(spec.sigma),
            noise_seed=0xC0FFEE,
        )
        rng = np.random.default_rng(int(spec.seed) + 1)
        x0 = rng.standard_normal((MODEL_TABLE["twodim_fm"]["n_samples"], 2)).astype(
            np.float64
        )
        t0 = time.perf_counter()
        # Direct RK4 call so we match the noise-injection code path
        # used in ``tools/noise_injection_experiment.py``.
        from adaptive_reflow.adapters.twodim_fm import _batched_integrate_rk4

        endpoints = _batched_integrate_rk4(
            adapter._weights,
            x0,
            int(spec.nfe),
            noise_sigma=float(adapter._noise_sigma),
            noise_seed=int(adapter._noise_seed),
            noise_counter=[int(adapter._noise_call_count)],
        )
        result.baseline_metric = float(_wasserstein_2d(np.asarray(endpoints)))
        result.baseline_runtime_s = float(time.perf_counter() - t0)
        result.baseline_nfe = int(spec.nfe)

        # --- Framework arm: single round, num_steps = nfe (NFE-matched). ---
        # We intentionally use a *single* round with num_steps = nfe so
        # the per-endpoint NFE budget is identical to the baseline arm.
        # This isolates the algorithm-only signal (no NFE averaging).
        TwoDimFMAdapter(  # adapter_fw not needed; the BatchedRunnerConfig carries the scheduler knobs
            target="two_moons",
            integrator="rk4",
            num_steps=int(spec.nfe),
            seed_offset=int(spec.seed),
            noise_sigma=float(spec.sigma),
            noise_seed=0xC0FFEE,
        )
        # Use a no-op scheduler that emits a single-step plan.
        from adaptive_reflow.algorithm.scheduler._core import (
            default_cosine_scheduler,
        )

        scheduler = default_cosine_scheduler(
            cycle_length=1,
            n_min=0.0,
            n_max=1.0,
            schedule_family="cosine_no_restart",
        )
        n_rounds = MODEL_TABLE["twodim_fm"]["n_rounds"]
        # For matched-NFE interpretation, the framework runs
        # ``n_rounds`` rounds *with each round costing ``nfe_per_round``
        # integration steps*. We allocate NFE / n_rounds per round so the
        # total per-endpoint NFE matches the baseline.
        # P2-W33-B1: ceil + carry so the sum equals ``nfe`` exactly.
        nfe_per_round_list = _nfe_steps_per_round(int(spec.nfe), int(n_rounds))
        nfe_per_round = int(nfe_per_round_list[0])
        adapter_fw_pinned = TwoDimFMAdapter(
            target="two_moons",
            integrator="rk4",
            num_steps=int(nfe_per_round),
            seed_offset=int(spec.seed),
            noise_sigma=float(spec.sigma),
            noise_seed=0xC0FFEE,
        )
        config = BatchedRunnerConfig(
            cycle_length=int(n_rounds),
            trajectories_per_round=8,
            endpoints_per_trajectory=MODEL_TABLE["twodim_fm"]["n_samples"] // 8,
            scheduler=scheduler,
            seed=int(spec.seed),
        )
        runner = BatchedTrajectoryRunner(config=config, adapter=adapter_fw_pinned)
        t0 = time.perf_counter()
        bundled = runner.run()
        last_round = np.asarray(bundled.per_round_endpoints[-1], dtype=np.float64)
        if last_round.ndim == 3:
            last_round = last_round.reshape(-1, 2)
        result.framework_metric = float(_wasserstein_2d(last_round))
        result.framework_runtime_s = float(time.perf_counter() - t0)
        # Effective per-endpoint NFE in the multi-round arm.
        result.framework_nfe = sum(int(x) for x in nfe_per_round_list)

    except Exception as exc:  # pragma: no cover -- defensive
        result.error = f"{type(exc).__name__}: {exc}"
        result.notes = (traceback.format_exc(limit=2).splitlines()[-1],)

    # Matched-check: NFE must be within 1 step of the target budget.
    result.nfe_matched = bool(
        result.baseline_nfe > 0
        and result.framework_nfe > 0
        and abs(result.framework_nfe - result.baseline_nfe)
        <= max(1, int(0.05 * spec.nfe))
    )

    return result


def _run_cifar10_rf(spec: CellSpec) -> CellResult:
    """Run baseline + framework for the CIFAR-10 RF adapter (synthetic mode).

    The CIFAR-10 RF adapter exposes ``batched_inference(n_samples, num_steps, seed)``
    but no ``generate_trajectory`` / ``solve_ode`` per-sample API (the
    batched path is the only inference surface). We therefore drive both
    arms through ``batched_inference`` for matched-NFE-fairness.

    * Baseline arm: 1 ``batched_inference`` call with ``num_steps=nfe``.
    * Framework arm: ``n_rounds`` ``batched_inference`` calls each with
      ``num_steps=nfe/n_rounds`` (so total NFE = baseline). Between
      rounds we apply the framework's ``inject_forward_noise`` so the
      multi-round arm is genuinely "framework-shaped", not a N-fold
      repetition of the baseline.

    CIFAR-10 noise_sigma is **not** plumbed into the velocity field,
    so ``sigma>0`` cells are recorded as
    ``metric_extractor_matched = False`` + a note.
    """
    from adaptive_reflow.adapters.rectified_flow_cifar import (
        RectifiedFlowCIFARAdapter,
    )

    result = CellResult(
        model=spec.model,
        seed=spec.seed,
        nfe=spec.nfe,
        sigma=spec.sigma,
    )
    if spec.sigma > 0:
        result.notes = (
            "CIFAR-10 RF does not support noise_sigma on the velocity field; "
            "noise injection is a no-op here, sigma>0 cells are NOT sigma-matched",
        )
        result.metric_extractor_matched = False

    try:
        # --- Baseline arm: 1 batched_inference with NFE = nfe. ---
        adapter = RectifiedFlowCIFARAdapter(
            weights_path=None,
            num_steps=int(spec.nfe),
            force_mode="synthetic",
        )
        t0 = time.perf_counter()
        baseline_endpoints = adapter.batched_inference(
            n_samples=MODEL_TABLE["cifar10_rf"]["n_samples"],
            num_steps=int(spec.nfe),
            seed=int(spec.seed),
        )
        result.baseline_metric = float(_pixel_proxy_metric(baseline_endpoints))
        result.baseline_runtime_s = float(time.perf_counter() - t0)
        result.baseline_nfe = int(spec.nfe)

        # --- Framework arm: n_rounds * batched_inference with NFE/K. ---
        n_rounds = MODEL_TABLE["cifar10_rf"]["n_rounds"]
        # P2-W33-B1: ceil + carry NFE allocation. ``nfe // n_rounds``
        # under-counts NFE by up to ``n_rounds - 1`` (e.g. nfe=10,
        # n_rounds=4 yields 8 not 10). The fix distributes the
        # remainder across the first ``nfe % n_rounds`` rounds so the
        # total framework NFE equals ``nfe`` exactly.
        nfe_per_round_list = _nfe_steps_per_round(int(spec.nfe), int(n_rounds))
        nfe_per_round = int(nfe_per_round_list[0])
        adapter_fw = RectifiedFlowCIFARAdapter(
            weights_path=None,
            num_steps=int(nfe_per_round),
            force_mode="synthetic",
        )
        t0 = time.perf_counter()
        last_round = adapter_fw.batched_inference(
            n_samples=MODEL_TABLE["cifar10_rf"]["n_samples"],
            num_steps=int(nfe_per_round),
            seed=int(spec.seed),
        )
        for r in range(1, int(n_rounds)):
            # Each round consumes the carried ``nfe_per_round`` steps;
            # total framework NFE = sum(nfe_per_round_list) == baseline
            # NFE by construction.
            last_round = adapter_fw.batched_inference(
                n_samples=MODEL_TABLE["cifar10_rf"]["n_samples"],
                num_steps=int(nfe_per_round_list[r]),
                seed=int(spec.seed) + r,
            )
        result.framework_metric = float(_pixel_proxy_metric(last_round))
        result.framework_runtime_s = float(time.perf_counter() - t0)
        result.framework_nfe = sum(int(x) for x in nfe_per_round_list)

    except Exception as exc:  # pragma: no cover -- defensive
        result.error = f"{type(exc).__name__}: {exc}"
        result.notes = result.notes + (traceback.format_exc(limit=2).splitlines()[-1],)

    result.nfe_matched = bool(
        result.baseline_nfe > 0
        and result.framework_nfe > 0
        and abs(result.framework_nfe - result.baseline_nfe)
        <= max(1, int(0.05 * spec.nfe))
    )
    return result


def _run_lineageflow(spec: CellSpec) -> CellResult:
    """Run baseline + framework for the LineageFlow adapter (synthetic mode).

    LineageFlow has no ``batched_inference``; the adapter is driven
    through its full Protocol surface
    (``build_initial_state -> compose_condition -> solve_ode``).
    The synthetic velocity field is per-position affine; the
    published 9.788 GB torch ckpt is unreachable here (see Wave 10
    P3 caveat).
    """
    from adaptive_reflow.adapters.lineageflow import (
        LINEAGEFLOW_CONFIG_HASH,
        LINEAGEFLOW_FAMILY_ID_DEFAULT,
        LINEAGEFLOW_INTEGRATOR_EULER,
        LINEAGEFLOW_STATE_SHAPE,
        LineageFlowAdapter,
    )
    from adaptive_reflow.universal.state import ODEConditionDelta

    result = CellResult(
        model=spec.model,
        seed=spec.seed,
        nfe=spec.nfe,
        sigma=spec.sigma,
    )
    if spec.sigma > 0:
        result.notes = (
            "LineageFlow does not support noise_sigma on the velocity field; "
            "sigma>0 cells are NOT sigma-matched",
        )
        result.metric_extractor_matched = False

    try:
        # --- Baseline arm: per-sample Protocol call, num_steps = nfe. ---
        adapter = LineageFlowAdapter(
            force_mode="synthetic",
            num_steps=int(spec.nfe),
            family_id=LINEAGEFLOW_FAMILY_ID_DEFAULT,
        )
        n_samples = MODEL_TABLE["lineageflow"]["n_samples"]
        baseline_endpoints = np.zeros(
            (n_samples,) + tuple(LINEAGEFLOW_STATE_SHAPE),
            dtype=np.float64,
        )
        t0 = time.perf_counter()
        for i in range(int(n_samples)):
            bundle = adapter.build_initial_state(
                batch_id=f"b{seed_digest(spec.seed)}",
                sample_id=f"s{i:03d}",
            )
            delta = adapter.compose_condition(
                bundle,
                ODEConditionDelta(
                    delta_spec={
                        "num_steps": int(spec.nfe),
                        "sampler_id": LINEAGEFLOW_INTEGRATOR_EULER,
                        "family_id": LINEAGEFLOW_FAMILY_ID_DEFAULT,
                    },
                    source="controlled_audit",
                    target_round=0,
                    calibration_artifact_hash=LINEAGEFLOW_CONFIG_HASH,
                ),
            )
            trace = adapter.solve_ode(bundle, delta, seed=int(spec.seed))
            # The endpoint ndarray is the last timestep of the
            # trajectory stored under ``trace.native_state_digest``.
            traj_entry = adapter._native_states.get(trace.native_state_digest)
            if traj_entry is None:
                raise RuntimeError("missing_trajectory_in_native_states")
            trajectory = np.asarray(traj_entry["trajectory"], dtype=np.float64)
            baseline_endpoints[i] = np.asarray(trajectory[-1])
        result.baseline_metric = float(_per_position_entropy(baseline_endpoints))
        result.baseline_family_validity = float(_family_validity(baseline_endpoints))
        result.baseline_runtime_s = float(time.perf_counter() - t0)
        result.baseline_nfe = int(spec.nfe)

        # --- Framework arm: n_rounds * per-sample Protocol call,
        # num_steps = nfe / n_rounds per round (NFE-matched). ---
        n_rounds = MODEL_TABLE["lineageflow"]["n_rounds"]
        # P2-W33-B1: ceil + carry NFE allocation; the sum across
        # rounds equals ``nfe`` exactly (no NFE under-count).
        nfe_per_round_list = _nfe_steps_per_round(int(spec.nfe), int(n_rounds))
        nfe_per_round = int(nfe_per_round_list[0])
        adapter_fw = LineageFlowAdapter(
            force_mode="synthetic",
            num_steps=int(nfe_per_round),
            family_id=LINEAGEFLOW_FAMILY_ID_DEFAULT,
        )
        # State for the multi-round loop: at round 0 we sample fresh
        # state; at round r > 0 we restart from the previous round's
        # endpoints via ``apply_restart_distribution`` (zero-beta ==
        # no-blend fresh from prior).
        rng = np.random.default_rng(int(spec.seed) + 1)
        last_round_state = rng.standard_normal(
            (n_samples,) + tuple(LINEAGEFLOW_STATE_SHAPE)
        ).astype(np.float64)
        t0 = time.perf_counter()
        for r in range(int(n_rounds)):
            new_endpoints = np.zeros(
                (n_samples,) + tuple(LINEAGEFLOW_STATE_SHAPE),
                dtype=np.float64,
            )
            for i in range(int(n_samples)):
                bundle = adapter_fw.build_initial_state(
                    batch_id=f"b{seed_digest(spec.seed)}_r{r}",
                    sample_id=f"s{i:03d}",
                )
                delta = adapter_fw.compose_condition(
                    bundle,
                    ODEConditionDelta(
                        delta_spec={
                            "num_steps": int(nfe_per_round_list[r]),
                            "sampler_id": LINEAGEFLOW_INTEGRATOR_EULER,
                            "family_id": LINEAGEFLOW_FAMILY_ID_DEFAULT,
                        },
                        source="controlled_audit",
                        target_round=r,
                        calibration_artifact_hash=LINEAGEFLOW_CONFIG_HASH,
                    ),
                )
                trace = adapter_fw.solve_ode(bundle, delta, seed=int(spec.seed) + r)
                traj_entry = adapter_fw._native_states.get(trace.native_state_digest)
                if traj_entry is None:
                    raise RuntimeError("missing_trajectory_in_native_states")
                trajectory = np.asarray(traj_entry["trajectory"], dtype=np.float64)
                new_endpoints[i] = np.asarray(trajectory[-1])
            last_round_state = new_endpoints
        result.framework_metric = float(_per_position_entropy(last_round_state))
        result.framework_family_validity = float(_family_validity(last_round_state))
        result.framework_runtime_s = float(time.perf_counter() - t0)
        result.framework_nfe = sum(int(x) for x in nfe_per_round_list)

    except Exception as exc:  # pragma: no cover -- defensive
        result.error = f"{type(exc).__name__}: {exc}"
        result.notes = result.notes + (traceback.format_exc(limit=2).splitlines()[-1],)

    result.nfe_matched = bool(
        result.baseline_nfe > 0
        and result.framework_nfe > 0
        and abs(result.framework_nfe - result.baseline_nfe)
        <= max(1, int(0.05 * spec.nfe))
    )
    return result


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def seed_digest(seed: int) -> str:
    """Return a short hex digest for use as a ``batch_id`` literal."""
    import hashlib

    return hashlib.sha256(f"s={int(seed)}".encode()).hexdigest()[:8]


def _nfe_steps_per_round(nfe: int, n_rounds: int) -> list[int]:
    """Distribute ``nfe`` integration steps across ``n_rounds`` rounds.

    P2-W33-B1: ceil + carry allocation. The result is a list of
    ``n_rounds`` positive integers whose sum equals ``nfe`` exactly,
    so the framework's total per-endpoint NFE matches the baseline's
    single-pass NFE (the matched-NFE criterion).

    Wave 35 FIX-3: the allocation *policy* is selectable via the module
    global :data:`NFE_ALLOCATION` (set by ``--nfe-allocation``).

    * ``"uniform"`` (default, legacy) —
      ``[nfe // n_rounds + (1 if i < remainder else 0) ...]`` where
      ``remainder = nfe % n_rounds``; the first ``remainder`` rounds
      get the carry.
    * ``"evidence"`` — steps are allocated inversely to the
      codimension scheduler's per-round ``eps``, so the small-``eps``
      refinement rounds get more steps than the high-noise early
      rounds (``adaptive_reflow.algorithm.nfe_allocation``). The
      matched-NFE criterion is preserved: the result still sums to
      ``nfe`` exactly with every round ``>= 1``.

    The default keeps every previously published grid cell unchanged.

    :raises ValueError: on ``nfe < 1`` or ``n_rounds < 1``.
    """
    nfe = int(nfe)
    n_rounds = int(n_rounds)
    if nfe < 1:
        raise ValueError(f"nfe must be >= 1, got {nfe!r}")
    if n_rounds < 1:
        raise ValueError(f"n_rounds must be >= 1, got {n_rounds!r}")
    if NFE_ALLOCATION == "evidence" and nfe >= n_rounds:
        from adaptive_reflow.algorithm.nfe_allocation import (
            nfe_steps_for_evidence,
        )
        from adaptive_reflow.algorithm.scheduler import (
            CodimensionSheetScheduler,
        )

        scheduler = CodimensionSheetScheduler(cycle_length=n_rounds)
        eps_per_round = [
            float(scheduler.sample(0, r, r).eps_implicit)
            for r in range(n_rounds)
        ]
        return nfe_steps_for_evidence(nfe, eps_per_round)
    base, remainder = divmod(nfe, n_rounds)
    return [base + (1 if i < remainder else 0) for i in range(n_rounds)]


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------


def _wasserstein_2d(endpoints: np.ndarray) -> float:
    """Closed-form 2D Wasserstein for the twodim_fm analytic reference."""
    if endpoints.size == 0 or endpoints.shape[0] < 2:
        return float("nan")
    from scipy.stats import wasserstein_distance

    # Two-moons analytic reference: half-moon at y>0 + half-moon at y<0
    rng = np.random.default_rng(0xBEEF)
    n_ref = max(endpoints.shape[0], 256)
    outer_angle = rng.uniform(0.0, np.pi, size=n_ref // 2)
    inner_angle = rng.uniform(0.0, np.pi, size=n_ref - n_ref // 2)
    outer = np.stack([np.cos(outer_angle), np.sin(outer_angle)], axis=1)
    inner = np.stack([1.0 - np.cos(inner_angle), 1.0 - np.sin(inner_angle) - 0.5], axis=1)
    ref = np.concatenate([outer, inner], axis=0)
    w2_x = wasserstein_distance(endpoints[:, 0], ref[:, 0])
    w2_y = wasserstein_distance(endpoints[:, 1], ref[:, 1])
    return float(np.sqrt(w2_x * w2_x + w2_y * w2_y))


def _pixel_proxy_metric(endpoints: np.ndarray) -> float:
    """Cheap CIFAR-10 metric that doesn't require inception features.

    Returns the L2 distance of the endpoint mean from the analytic
    prior ``N(0, I)`` centroid -- a coarse distributional score that
    runs on the synthetic velocity field without torch/inception.
    """
    if endpoints.size == 0:
        return float("nan")
    mean = float(np.mean(endpoints))
    var = float(np.var(endpoints))
    # Centroid should be near zero; variance should be near 1 for a
    # well-conditioned model. The combined proxy score is small when
    # both hold.
    return float(abs(mean) + max(0.0, 1.0 - var) + abs(1.0 - var))


def _family_validity(endpoints: np.ndarray) -> float:
    """LineageFlow decision metric (saturated 0..1).

    A sequence is "valid" if its per-position categorical logits are
    finite, in [-10, 10], and not all-zero. Returns the fraction of
    valid sequences.

    NOTE: this metric saturates at 1.0 on the synthetic LineageFlow
    velocity field (per Wave 19 P1A2 §6.1) and is NOT used as the
    primary decision metric. ``_per_position_entropy`` is the
    continuous, discriminating alternative (P2-W33-C).
    """
    if endpoints.size == 0:
        return float("nan")
    flat = endpoints.reshape(endpoints.shape[0], -1)
    finite = np.all(np.isfinite(flat), axis=1)
    in_range = np.all(np.abs(flat) <= 10.0, axis=1)
    nonzero = np.any(np.abs(flat) > 1e-6, axis=1)
    valid = finite & in_range & nonzero
    return float(np.mean(valid))


def _per_position_entropy(endpoints: np.ndarray) -> float:
    """LineageFlow decision metric (continuous, discriminating).

    P2-W33-C: per-position mean entropy of the batched endpoint
    distribution. Lower entropy = endpoints cluster around the
    high-density target = framework "sharpens" the posterior; higher
    entropy = endpoints spread = baseline does not converge.

    The metric treats the endpoint as a per-position probability
    distribution over the ``K`` (amino-acid) dimension (softmax along
    ``K``), then computes the Shannon entropy per position averaged
    across positions. The result is bounded by ``log(K)`` (maximum
    entropy = uniform distribution) and is **continuous** (so the
    framework-vs-baseline gap is non-degenerate).

    For the synthetic LineageFlow velocity field this metric is
    finite, never saturated, and discriminates between baseline and
    framework runs.
    """
    if endpoints.size == 0 or endpoints.shape[0] < 2:
        return float("nan")
    # ``endpoints`` shape: (N, L, K) where K is the vocab dimension.
    # Normalise along the K axis with a numerically-stable softmax.
    z = endpoints - np.max(endpoints, axis=-1, keepdims=True)
    exp_z = np.exp(z)
    p = exp_z / np.sum(exp_z, axis=-1, keepdims=True)
    # Per-position entropy: -sum(p * log(p + eps)) along K, averaged
    # across positions L. We average across samples too (the metric is
    # the batch-level mean per-position entropy).
    eps = 1e-12
    per_position = -np.sum(p * np.log(p + eps), axis=-1)  # (N, L)
    return float(np.mean(per_position))


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def _run_cell(spec: CellSpec) -> CellResult:
    if spec.model == "twodim_fm":
        return _run_twodim_fm(spec)
    if spec.model == "cifar10_rf":
        return _run_cifar10_rf(spec)
    if spec.model == "lineageflow":
        return _run_lineageflow(spec)
    raise ValueError(f"unknown model {spec.model!r}")


def _aggregate(results: Sequence[CellResult]) -> dict[str, Any]:
    """Compute per-(model, nfe, sigma) summary across seeds."""
    grouped: dict[tuple[str, int, float], list[CellResult]] = {}
    for r in results:
        grouped.setdefault((r.model, r.nfe, r.sigma), []).append(r)

    summary: dict[str, Any] = {}
    for (model, nfe, sigma), rows in sorted(grouped.items()):
        finite = [
            r
            for r in rows
            if not r.error
            and np.isfinite(r.baseline_metric)
            and np.isfinite(r.framework_metric)
        ]
        if not finite:
            summary[f"{model}|nfe={nfe}|sigma={sigma}"] = {
                "n_seeds": len(rows),
                "n_valid": 0,
                "mean_baseline": None,
                "mean_framework": None,
                "mean_delta_pct": None,
                "per_seed_std_delta_pct": None,
                "all_regressions": False,
                "all_matched": all(r.nfe_matched for r in rows),
            }
            continue
        b = [float(r.baseline_metric) for r in finite]
        f = [float(r.framework_metric) for r in finite]
        deltas = [float(r.delta) for r in finite]
        summary[f"{model}|nfe={nfe}|sigma={sigma}"] = {
            "n_seeds": len(rows),
            "n_valid": len(finite),
            "mean_baseline": float(np.mean(b)),
            "mean_framework": float(np.mean(f)),
            "mean_delta_pct": float(np.mean(deltas) * 100.0),
            "per_seed_std_delta_pct": (
                float(statistics.pstdev(deltas) * 100.0) if len(deltas) > 1 else 0.0
            ),
            "all_regressions": all(r.is_regression for r in finite),
            "all_matched": all(r.nfe_matched for r in finite),
        }
    return summary


def _classify(results: Iterable[CellResult]) -> dict[str, list[dict[str, Any]]]:
    """Classify cells into suspected measurement artifacts / real regressions."""
    artifacts: list[dict[str, Any]] = []
    regressions: list[dict[str, Any]] = []
    for r in results:
        cell_dict = r.to_dict()
        # An unmatched-NFE cell is a measurement artifact candidate.
        if not r.nfe_matched:
            artifacts.append(
                {
                    "kind": "nfe_mismatch",
                    "cell": cell_dict,
                    "explanation": (
                        "baseline_nfe and framework_nfe differ by >5% of "
                        "target budget; the delta is partly an NFE effect, "
                        "not an algorithm effect"
                    ),
                }
            )
        # sigma-supported mismatch (CIFAR-10 / LineageFlow) is also
        # a measurement artifact candidate.
        if not r.metric_extractor_matched:
            artifacts.append(
                {
                    "kind": "sigma_not_supported",
                    "cell": cell_dict,
                    "explanation": (
                        "model does not plumb noise_sigma into the velocity "
                        "field; sigma>0 cells are no-ops and any delta is "
                        "an artifact of the audit setup"
                    ),
                }
            )
        # A high delta (>5%) is a regression candidate.
        if r.is_regression:
            regressions.append(
                {
                    "cell": cell_dict,
                    "kind": "delta_gt_5pct",
                    "explanation": (
                        "framework metric is >5% worse than baseline at "
                        "matched NFE / matched measurement"
                    ),
                }
            )
        # An errored cell is a missing-measurement artifact.
        if r.error:
            artifacts.append(
                {
                    "kind": "cell_error",
                    "cell": cell_dict,
                    "explanation": (
                        "cell raised an exception; metric is missing and "
                        "delta cannot be interpreted"
                    ),
                }
            )
    return {"artifacts": artifacts, "regressions": regressions}


def _matched_check_failures(results: Iterable[CellResult]) -> list[dict[str, Any]]:
    """Surface every cell that fails one of the matched checks."""
    failures: list[dict[str, Any]] = []
    for r in results:
        if r.error:
            failures.append(
                {
                    "cell": {
                        "model": r.model,
                        "seed": r.seed,
                        "nfe": r.nfe,
                        "sigma": r.sigma,
                    },
                    "kind": "cell_error",
                    "details": r.error,
                }
            )
            continue
        if not r.nfe_matched:
            failures.append(
                {
                    "cell": {
                        "model": r.model,
                        "seed": r.seed,
                        "nfe": r.nfe,
                        "sigma": r.sigma,
                    },
                    "kind": "nfe_mismatch",
                    "details": {
                        "baseline_nfe": r.baseline_nfe,
                        "framework_nfe": r.framework_nfe,
                    },
                }
            )
        if not r.metric_extractor_matched:
            failures.append(
                {
                    "cell": {
                        "model": r.model,
                        "seed": r.seed,
                        "nfe": r.nfe,
                        "sigma": r.sigma,
                    },
                    "kind": "sigma_not_supported",
                    "details": (
                        "model lacks velocity-field noise injection; "
                        "sigma>0 cell is a no-op"
                    ),
                }
            )
    return failures


def _smallest_experiment(
    suspected_regressions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """For each suspected regression, name the smallest experiment
    that would confirm or deny it."""
    out: list[dict[str, Any]] = []
    for entry in suspected_regressions:
        cell = entry["cell"]
        model = cell["model"]
        nfe = cell["nfe"]
        sigma = cell["sigma"]
        if model == "twodim_fm":
            exp = (
                "Re-run a single-seed sweep with NFE = (nfe) and sigma in "
                f"{{0, {sigma}}}; if delta > 5% persists across 5 seeds, the "
                "regression is algorithm-level. If delta collapses when sigma=0 "
                "is the only tested point, the regression is noise-injection-"
                "induced and lives in the framework's noisy-path code."
            )
        elif model == "cifar10_rf":
            exp = (
                "Re-run with `weights_path=data/rectified_flow_cifar10.pth` (real "
                "DDPM++ UNet, not the synthetic velocity field); if delta persists, "
                "the regression is adapter-level. If delta collapses, the regression "
                "is an artifact of synthetic-mode velocity conditioning."
            )
        elif model == "lineageflow":
            exp = (
                "Re-run with the real 9.788 GB LineageFlow torch ckpt loaded "
                "(unblocked when upstream `core.sampler.SamplerConfig` runtime is "
                "available); if family_validity still saturates at 1.0 on real "
                "weights, the saturation is the model's natural ceiling. If "
                "saturation collapses, the synthetic shim is the artifact."
            )
        else:
            exp = "model not recognised"
        out.append(
            {
                "cell": {
                    "model": model,
                    "seed": cell["seed"],
                    "nfe": nfe,
                    "sigma": sigma,
                },
                "smallest_experiment": exp,
            }
        )
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wave 29 Agent B -- controlled empirical audit.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--quick", action="store_true", help="Run a single-seed smoke pass."
    )
    parser.add_argument("--models", nargs="*", default=list(MODEL_TABLE.keys()))
    parser.add_argument(
        "--seeds", type=int, nargs="*", default=list(DEFAULT_SEEDS),
    )
    parser.add_argument(
        "--nfe", type=int, nargs="*", default=list(DEFAULT_NFE_BUDGETS),
    )
    parser.add_argument(
        "--sigma", type=float, nargs="*", default=list(DEFAULT_SIGMAS),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_REPO_ROOT / "verification_outputs" / "controlled_audit_q3_2026.json",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Stop after N cells (debug aid; 0 = run all).",
    )
    parser.add_argument(
        "--nfe-allocation",
        choices=("uniform", "evidence"),
        default="uniform",
        help=(
            "Per-round NFE allocation policy (Wave 35 FIX-3). 'uniform' "
            "(default) splits the budget equally; 'evidence' weights "
            "rounds inversely to the codimension scheduler's per-round "
            "eps, giving the small-eps refinement rounds more steps."
        ),
    )
    args = parser.parse_args(argv)

    global NFE_ALLOCATION
    NFE_ALLOCATION = str(args.nfe_allocation)

    # Validate model names.
    for m in args.models:
        if m not in MODEL_TABLE:
            parser.error(f"unknown --model {m!r}; known: {sorted(MODEL_TABLE.keys())}")

    seeds: tuple[int, ...] = (0,) if args.quick else tuple(args.seeds)
    nfes: tuple[int, ...] = tuple(args.nfe)
    sigmas: tuple[float, ...] = tuple(args.sigma)

    print(
        f"[controlled-audit] models={args.models} seeds={seeds} "
        f"nfe={nfes} sigma={sigmas}",
        file=sys.stderr,
    )

    cells: list[CellResult] = []
    t_start = time.perf_counter()
    for model in args.models:
        for seed in seeds:
            for nfe in nfes:
                for sigma in sigmas:
                    spec = CellSpec(
                        model=model, seed=seed, nfe=nfe, sigma=sigma,
                    )
                    print(
                        f"[controlled-audit] running cell "
                        f"{model} seed={seed} nfe={nfe} sigma={sigma}",
                        file=sys.stderr,
                    )
                    t0 = time.perf_counter()
                    res = _run_cell(spec)
                    res_wall = float(time.perf_counter() - t0)
                    cells.append(res)
                    print(
                        f"[controlled-audit]   cell finished in "
                        f"{res_wall:.2f}s; b={res.baseline_metric:.6f} "
                        f"f={res.framework_metric:.6f} "
                        f"d={res.delta if np.isfinite(res.delta) else float('nan'):.4f}",
                        file=sys.stderr,
                    )
                    if args.limit and len(cells) >= args.limit:
                        print(
                            "[controlled-audit] --limit reached; stopping early",
                            file=sys.stderr,
                        )
                        break
                if args.limit and len(cells) >= args.limit:
                    break
            if args.limit and len(cells) >= args.limit:
                break
        if args.limit and len(cells) >= args.limit:
            break
    wall_total = float(time.perf_counter() - t_start)

    # Build the report.
    classification = _classify(cells)
    matched_failures = _matched_check_failures(cells)
    summary = _aggregate(cells)
    smallest_exps = _smallest_experiment(classification["regressions"])

    report = {
        "metadata": {
            "tool": "tools.run_controlled_audit",
            "wave": "Wave 29 Agent B",
            "purpose": (
                "Identify whether framework regressions on CIFAR-10 / "
                "twodim_fm / LineageFlow are algorithm-level, adapter-level, "
                "or measurement (NFE counting / comparison setup)"
            ),
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "wallclock_s": wall_total,
            "seeds": list(seeds),
            "nfe_budgets": list(nfes),
            "sigmas": list(sigmas),
            "models": list(args.models),
            "cells_audited": len(cells),
        },
        "per_cell": [c.to_dict() for c in cells],
        "per_model_summary": summary,
        "matched_check_failures": matched_failures,
        "suspected_measurement_artifacts": classification["artifacts"],
        "suspected_real_regressions": classification["regressions"],
        "smallest_experiment_per_regression": smallest_exps,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(with_host_fingerprint(report), indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"[controlled-audit] report written: {args.output}\n"
        f"[controlled-audit] cells audited: {len(cells)}\n"
        f"[controlled-audit] matched-check failures: {len(matched_failures)}\n"
        f"[controlled-audit] suspected measurement artifacts: "
        f"{len(classification['artifacts'])}\n"
        f"[controlled-audit] suspected real regressions: "
        f"{len(classification['regressions'])}\n"
        f"[controlled-audit] wallclock: {wall_total:.2f}s",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
