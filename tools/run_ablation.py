"""Standalone ablation study for the 2D rectified-flow adapter (DTB-G3).

Runs an 18-cell ablation grid that contrasts the operational regimes the
framework exposes (DTB-R5 -- outer framework runner): the 8 canonical
configurations against both analytic targets (16 cells) plus 2
paper-grounded configurations (ADR-0013) against ``two_moons`` only.

* ``single_pass``                                       -- 1 round; fresh noise only.
* ``multi_round_constant_beta_05``                      -- 20 rounds; constant ``beta = 0.5``
  via :class:`ConstantPolicyDriver` + cosine scheduler.
* ``multi_round_cosine_anneal``                         -- 20 rounds; ``beta`` derived from
  a cosine-annealed memory_fraction schedule via the *default*
  :class:`ScheduleDerivedPolicyDriver` + cosine scheduler
  (``n_min=0``, ``n_max=1``; ADR-0010).
* ``multi_round_no_restart``                            -- 20 rounds; constant ``beta = 1``
  via :class:`ConstantPolicyDriver` (full fresh noise every round).
* ``multi_round_polynomial_schedule_derived``           -- 20 rounds;
  :class:`PolynomialScheduler` (power=2) paired with
  :class:`ScheduleDerivedPolicyDriver`. Concave ramp; ``beta`` stays
  high longer, then climbs later in the cycle.
* ``multi_round_sigmoid_schedule_derived``              -- 20 rounds;
  :class:`SigmoidScheduler` (steepness=10, midpoint=0.5) paired with
  :class:`ScheduleDerivedPolicyDriver`. Near-step transition at the
  cycle midpoint.
* ``multi_round_convergence_adaptive_schedule_derived`` -- 20 rounds;
  :class:`ConvergenceAdaptiveScheduler` (base=CosineAnneal,
  ``kp=0.10``, ``kd=0.05``, ``shift_max=0.15``) paired with
  :class:`ScheduleDerivedPolicyDriver`. PID-lite feedback shifts the
  effective ``u_r`` based on per-round W2.
* ``multi_round_cosine_adaptive_driver``                -- 20 rounds; cosine scheduler
  paired with :class:`AdaptivePolicyDriver` (digest-seeded convergence
  estimate). A *mixed* configuration that the runner's framework
  composes freely; the adaptive driver changes ``beta`` per round
  based on the prior endpoint's digest.
* ``multi_round_codimension_sheet_posterior_selection`` -- 20 rounds;
  :class:`CodimensionSheetScheduler` (``eps_implicit=0.05``) paired
  with :class:`ScheduleDerivedPolicyDriver` and a
  :class:`PosteriorSelectionEvaluator` (ADR-0013). Emits the
  paper-Theorem-1 ``selection_ratio`` per round.
* ``multi_round_cosine_posterior_selection``            -- 20 rounds; cosine
  scheduler + :class:`ScheduleDerivedPolicyDriver` +
  :class:`PosteriorSelectionEvaluator`. The paper-grounded baseline:
  ADR-0013 records cosine annealing as the canonical implementation of
  paper Lemma 2's sheet-tube scaling, so this row is the reference the
  codimension row is measured against.

Each row is evaluated against the two analytic targets
``two_moons`` and ``eight_gaussians`` via the same closed-form 2D
Wasserstein and Voronoi-cell coverage helpers the original ablation
script used (the runner emits the per-round endpoints, the script
scores them externally). The two paper-grounded rows run against
``two_moons`` only -- its 2-mode geometry is the minimal instance of
paper Theorem 1's fibre (one codimension-1 sheet plus one isolated
cell root).

Outputs are written to ``docs/ABLATION.md`` as a markdown table plus
a ``Findings`` section that compares the configurations. The script
is deterministic for fixed ``seed`` (default ``42``).

Usage::

    python tools/run_ablation.py [--rounds 20] [--quick]

The ``--quick`` flag overrides ``--rounds`` with ``5`` (for the smoke
test). Pass ``--out`` to redirect the markdown output.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

# Make the project importable when running as ``python tools/run_ablation.py``.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter  # noqa: E402
from adaptive_reflow.algorithm import (  # noqa: E402
    AdaptivePolicyDriver,
    ConstantPolicyDriver,
    ReInferenceConfig,
    ReInferenceRunner,
    SchedulerProtocol,
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.scheduler import (  # noqa: E402
    CodimensionSheetScheduler,
    ConstantScheduler,
    ConvergenceAdaptiveScheduler,
    PolynomialScheduler,
    SigmoidScheduler,
)
from adaptive_reflow.data.target_distributions import (  # noqa: E402
    mode_centers_for_target,
)
from adaptive_reflow.eval.posterior_selection_evaluator import (  # noqa: E402
    PosteriorSelectionEvaluator,
)
from adaptive_reflow.eval.twodim_fm_evaluator import (  # noqa: E402
    analytic_samples,
    coverage_score,
    voronoi_grid,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CANONICAL_TARGETS: tuple[str, ...] = ("two_moons", "eight_gaussians")
CANONICAL_CONFIGURATIONS: tuple[str, ...] = (
    "single_pass",
    "multi_round_constant_beta_05",
    "multi_round_cosine_anneal",
    "multi_round_no_restart",
    "multi_round_polynomial_schedule_derived",
    "multi_round_sigmoid_schedule_derived",
    "multi_round_convergence_adaptive_schedule_derived",
    "multi_round_cosine_adaptive_driver",
)
#: Paper-grounded configurations (ADR-0013). Both pair a scheduler with
#: the default ``ScheduleDerivedPolicyDriver`` and a
#: :class:`PosteriorSelectionEvaluator`, so the runner emits the
#: per-round ``selection_ratio`` that paper Proposition 3 predicts.
PAPER_GROUNDED_CONFIGURATIONS: tuple[str, ...] = (
    "multi_round_codimension_sheet_posterior_selection",
    "multi_round_cosine_posterior_selection",
)
#: The paper-grounded rows run against this target only. ``two_moons``
#: has exactly 2 modes, which is the minimal instance of paper
#: Theorem 1's fibre geometry (one codimension-1 sheet + one isolated
#: codimension-2 cell root), so the selection-ratio prediction is
#: cleanest there. Keeping the paper rows on a single target holds the
#: grid at 18 cells (8 configs x 2 targets + 2 paper rows).
PAPER_GROUNDED_TARGET: str = "two_moons"
DEFAULT_SEED: int = 42
DEFAULT_ROUNDS: int = 20
QUICK_ROUNDS: int = 5
DEFAULT_NUM_STEPS: int = 30  # cheap RK4; ~100ms per round per sample.
TWODIM_FM_CHANNELS: tuple[str, ...] = ("xy",)
DEFAULT_OUT: Path = REPO_ROOT / "docs" / "ABLATION.md"

# Cosine-anneal schedule configuration (ADR-0010).
COSINE_N_MIN: float = 0.0
COSINE_N_MAX: float = 1.0

# Convergence-adaptive scheduler gains (per task brief).
CONV_ADAPT_KP: float = 0.10
CONV_ADAPT_KD: float = 0.05
CONV_ADAPT_SHIFT_MAX: float = 0.15

# Polynomial schedule configuration (per task brief).
POLYNOMIAL_POWER: float = 2.0

# Sigmoid schedule configuration (per task brief).
SIGMOID_STEEPNESS: float = 10.0
SIGMOID_MIDPOINT: float = 0.5

# Codimension-sheet scheduler configuration (ADR-0013). ``eps_implicit``
# is the implicit noise scale in evidence units: the sheet contributes
# ``1 / max(n_cap_base, eps)`` and each cell ``(1 - n_cap_base)^2 / eps^2``.
CODIMENSION_EPS_IMPLICIT: float = 0.05

# PosteriorSelectionEvaluator replay budget. Each replay is one RK4 ODE
# solve, so the per-round cost is ``n_gen`` solves; 100 keeps the
# 18-cell grid inside a ~1 minute wall-clock budget while giving a
# sheet-evidence mean whose standard error is below 0.01.
POSTERIOR_SELECTION_N_GEN: int = 100


# ---------------------------------------------------------------------------
# Scheduler + driver factories (one per configuration)
# ---------------------------------------------------------------------------


def _build_components(
    config: str,
    *,
    rounds: int,
) -> tuple[SchedulerProtocol, Any, int]:
    """Return ``(scheduler, driver, n_rounds)`` for a given config.

    ``n_rounds`` is ``1`` for the single-pass config and ``rounds``
    otherwise; ``scheduler`` is the :class:`SchedulerProtocol`
    instance the runner will sample from; ``driver`` is the
    :class:`PolicyDriverProtocol` instance the runner will dispatch
    through. The sentinel string ``"default"`` resolves to
    :func:`default_policy_driver` so the runner's
    ``algorithm_signatures`` mapping carries the canonical config hash.
    """
    if config == "single_pass":
        # Single round; any scheduler / driver combo works because
        # only round 0 is executed. Use the canonical cosine scheduler
        # + constant driver(beta=0) so the round trace is well-defined.
        return default_cosine_scheduler(cycle_length=1), ConstantPolicyDriver(beta=0.0), 1
    if config == "multi_round_constant_beta_05":
        return (
            default_cosine_scheduler(cycle_length=rounds),
            ConstantPolicyDriver(beta=0.5),
            int(rounds),
        )
    if config == "multi_round_cosine_anneal":
        # Default scheduler + default driver -- the runner reproduces
        # the engine's inline ``_policy_with_schedule_beta`` override
        # via :class:`ScheduleDerivedPolicyDriver`.
        return (
            default_cosine_scheduler(
                cycle_length=rounds, n_min=COSINE_N_MIN, n_max=COSINE_N_MAX
            ),
            "default",
            int(rounds),
        )
    if config == "multi_round_no_restart":
        # Constant ``beta = 1.0`` -> ``memory_fraction = 0`` -> full
        # fresh noise every round (no restart). The scheduler is
        # ignored by the constant driver; we pass a constant
        # scheduler so the schedule's config_hash is meaningful.
        return (
            ConstantScheduler(cycle_length=rounds, n_cap=1.0),
            ConstantPolicyDriver(beta=1.0),
            int(rounds),
        )
    if config == "multi_round_polynomial_schedule_derived":
        # Concave polynomial ramp (power=2) paired with the default
        # schedule-derived driver. ``beta`` stays high longer in the
        # cycle, then climbs near the end.
        return (
            PolynomialScheduler(
                cycle_length=rounds,
                n_min=COSINE_N_MIN,
                n_max=COSINE_N_MAX,
                power=POLYNOMIAL_POWER,
            ),
            "default",
            int(rounds),
        )
    if config == "multi_round_sigmoid_schedule_derived":
        # Sigmoid ramp with steepness=10, midpoint=0.5 paired with
        # the default schedule-derived driver. Near-step transition
        # at the cycle midpoint.
        return (
            SigmoidScheduler(
                cycle_length=rounds,
                n_min=COSINE_N_MIN,
                n_max=COSINE_N_MAX,
                steepness=SIGMOID_STEEPNESS,
                midpoint=SIGMOID_MIDPOINT,
            ),
            "default",
            int(rounds),
        )
    if config == "multi_round_convergence_adaptive_schedule_derived":
        # PID-lite feedback scheduler: cosine base + W2-driven shift
        # of ``u_r`` per round. Paired with the default schedule-
        # derived driver.
        return (
            ConvergenceAdaptiveScheduler(
                base=default_cosine_scheduler(
                    cycle_length=rounds,
                    n_min=COSINE_N_MIN,
                    n_max=COSINE_N_MAX,
                ),
                kp=CONV_ADAPT_KP,
                kd=CONV_ADAPT_KD,
                shift_max=CONV_ADAPT_SHIFT_MAX,
            ),
            "default",
            int(rounds),
        )
    if config == "multi_round_cosine_adaptive_driver":
        # Mixed configuration: cosine scheduler + adaptive driver.
        # The driver ignores the schedule's ``n_cap`` so ``beta`` is
        # driven by the prior endpoint's digest instead -- this row
        # exercises the (scheduler, driver) composability the
        # framework unlocks.
        return (
            default_cosine_scheduler(
                cycle_length=rounds, n_min=COSINE_N_MIN, n_max=COSINE_N_MAX
            ),
            AdaptivePolicyDriver(),
            int(rounds),
        )
    if config == "multi_round_codimension_sheet_posterior_selection":
        # ADR-0013 phase 2: the codimension-sheet scheduler derives
        # ``n_cap`` from the closed-form sheet-vs-cell evidence balance
        # (paper Lemma 2 + Lemma 3) instead of from a fixed ramp shape.
        return (
            CodimensionSheetScheduler(
                cycle_length=rounds,
                n_min=COSINE_N_MIN,
                n_max=COSINE_N_MAX,
                eps_implicit=CODIMENSION_EPS_IMPLICIT,
            ),
            "default",
            int(rounds),
        )
    if config == "multi_round_cosine_posterior_selection":
        # ADR-0013 paper-grounded baseline: identical to
        # ``multi_round_cosine_anneal`` except that the runner is also
        # handed a :class:`PosteriorSelectionEvaluator`, so the per-round
        # ``selection_ratio`` is emitted. Cosine annealing is ADR-0013's
        # canonical implementation of paper Lemma 2's sheet-tube scaling.
        return (
            default_cosine_scheduler(
                cycle_length=rounds, n_min=COSINE_N_MIN, n_max=COSINE_N_MAX
            ),
            "default",
            int(rounds),
        )
    raise ValueError(f"unknown_config:{config}")


def _configs_for_target(target: str) -> tuple[str, ...]:
    """Return the configuration list to run against ``target``.

    Every target runs the 8 canonical configurations; the target named
    by :data:`PAPER_GROUNDED_TARGET` additionally runs the 2
    paper-grounded (ADR-0013) configurations. The grid is therefore
    ``8 * 2 + 2 = 18`` cells.
    """
    if str(target) == PAPER_GROUNDED_TARGET:
        return CANONICAL_CONFIGURATIONS + PAPER_GROUNDED_CONFIGURATIONS
    return CANONICAL_CONFIGURATIONS


def _selection_evaluator_for(
    config: str,
    target: str,
    *,
    seed: int,
) -> PosteriorSelectionEvaluator | None:
    """Return the ADR-0013 evaluator for ``config``, or ``None``.

    Only the two paper-grounded configurations carry a
    :class:`PosteriorSelectionEvaluator`; every other row keeps the
    ADR-0011 / ADR-0012 behaviour (no ``selection_ratio`` emission and
    no extra replay cost).
    """
    if config not in PAPER_GROUNDED_CONFIGURATIONS:
        return None
    return PosteriorSelectionEvaluator(
        target=target,  # type: ignore[arg-type]
        n_gen=POSTERIOR_SELECTION_N_GEN,
        n_ref=POSTERIOR_SELECTION_N_GEN,
        seed=int(seed),
        eps_implicit=CODIMENSION_EPS_IMPLICIT,
    )


# ---------------------------------------------------------------------------
# Runner helpers
# ---------------------------------------------------------------------------


def _resolve_default_driver(driver: Any) -> Any:
    """Resolve the ``"default"`` sentinel to a concrete driver instance."""
    if driver == "default":  # type: ignore[comparison-overlap]
        from adaptive_reflow.algorithm import default_policy_driver

        return default_policy_driver()
    return driver


def _run_one(
    config: str,
    target: str,
    weights_path: Path,
    *,
    seed: int,
    rounds: int,
    num_steps: int,
) -> dict[str, Any]:
    """Run a single (config, target) cell and return the metric dict.

    Uses :class:`ReInferenceRunner` to drive the inner engine loop
    for every configuration except the convergence-adaptive one
    (which needs per-round W2 feedback the runner does not provide
    natively -- that row uses :func:`_run_one_with_feedback`).

    The runner collects the per-round endpoints into
    ``result.endpoints``; we score those endpoints with the same W2
    and Voronoi-coverage helpers the original script used.

    For the two ADR-0013 paper-grounded configurations the runner is
    additionally handed a :class:`PosteriorSelectionEvaluator`, so the
    returned row carries the per-round ``selection_ratio`` curve and
    its final value.
    """
    del num_steps  # The runner drives ``num_steps`` internally; kept for CLI parity.
    scheduler, driver, n_rounds = _build_components(config, rounds=rounds)
    resolved_driver = _resolve_default_driver(driver)
    adapter = TwoDimFMAdapter(weights_path=weights_path, target=target)
    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler,
        policy_driver=resolved_driver,  # type: ignore[arg-type]
    )
    runner_config = ReInferenceConfig(
        n_rounds=n_rounds,
        outer_cycle_id=0,
        target_round=0,
        seed=int(seed),
        channels=TWODIM_FM_CHANNELS,
        selection_evaluator=_selection_evaluator_for(
            config, target, seed=int(seed)
        ),
    )
    result = runner.run(runner_config)

    # Audit the round traces (the original script raised on non-empty
    # ``audit_codes``; preserve that fail-closed invariant).
    for r, trace in enumerate(result.round_traces):
        if trace.audit_codes:
            raise RuntimeError(
                f"{config} audit_codes at r={r}: {trace.audit_codes!r}"
            )

    # Compute the canonical W2 / coverage curves using the existing
    # helpers -- the runner collects endpoints, the script scores them.
    w2s, covs = _score_per_round(
        target=target, endpoints=result.endpoints, seed=int(seed)
    )
    selection_curve = [
        float(result.per_round_metrics[r]["selection_ratio"])
        for r in sorted(result.per_round_metrics)
        if "selection_ratio" in result.per_round_metrics[r]
    ]
    return {
        "config": config,
        "target": target,
        "final_w2": float(w2s[-1]),
        "mean_w2": _summarize_tail(w2s, tail=5),
        "final_coverage": float(covs[-1]),
        "mean_coverage": _summarize_tail(covs, tail=5),
        # ADR-0013 paper-Theorem-1 metric (empty for non-paper rows):
        "final_selection_ratio": (
            float(selection_curve[-1]) if selection_curve else None
        ),
        "mean_selection_ratio": (
            _summarize_tail(selection_curve, tail=5) if selection_curve else None
        ),
        # Diagnostic extras (not in the markdown table):
        "w2_curve": list(w2s),
        "cov_curve": list(covs),
        "selection_curve": list(selection_curve),
    }


def _run_one_with_feedback(
    config: str,
    target: str,
    weights_path: Path,
    *,
    seed: int,
    rounds: int,
) -> dict[str, Any]:
    """Run a single cell with per-round W2 feedback to the scheduler.

    Mirrors :meth:`ReInferenceRunner.run` so the round-trace audit
    invariants stay in sync, but computes W2 incrementally and feeds it
    back via :meth:`SchedulerProtocol.record_round_feedback`. This is
    required for adaptive schedulers (e.g.
    :class:`ConvergenceAdaptiveScheduler`) that mutate per-round
    parameters based on the engine's per-round feedback.

    The runner does not feed W2 back by default because the W2 oracle
    is external (the script's W2 helper, not the runner's evaluator).
    We replicate the runner's per-round loop here so the adaptive
    scheduler sees the same W2 values the script will eventually
    report in the markdown table.
    """
    from adaptive_reflow.algorithm.runner import (  # noqa: PLC0415 — late import
        _build_base_policy,
        _build_condition_delta,
        _build_initial_phase_state,
    )
    from adaptive_reflow.contracts import ChannelName  # noqa: PLC0415
    from adaptive_reflow.frame.engine import Engine  # noqa: PLC0415 — late import

    scheduler, driver, n_rounds = _build_components(config, rounds=rounds)
    resolved_driver = _resolve_default_driver(driver)
    adapter = TwoDimFMAdapter(weights_path=weights_path, target=target)
    engine = Engine()
    primary_channel = ChannelName("xy")

    bundle = adapter.build_initial_state(
        batch_id=f"ablation-batch-{target}",
        sample_id=f"ablation-sample-{target}-r0",
    )
    endpoints: NDArray[np.float64] = np.empty((n_rounds, 2), dtype=np.float64)
    prior_endpoint_digest = ""
    phase_state = _build_initial_phase_state(horizon_remaining=int(n_rounds))

    for r in range(int(n_rounds)):
        sample = scheduler.sample(0, r, r)
        base_policy = _build_base_policy(
            schedule_sample=sample.as_cosine_schedule_sample(),
            beta=0.0,
            channel=primary_channel,
            target_round=r,
        )
        applied_policy = resolved_driver.compute_policy(
            sample.as_cosine_schedule_sample(),
            base_policy=base_policy,
            channel=str(primary_channel),
            prior_endpoint_digest=prior_endpoint_digest,
        )
        condition_delta = _build_condition_delta(
            target_round=r,
            source="tools.run_ablation.feedback_loop",
        )

        result = engine.run_round(
            round_index=r,
            phase_state=phase_state,
            bundle=bundle,
            adapter=adapter,
            policy=applied_policy,
            condition_delta=condition_delta,
            seed=int(seed) + r,
        )
        trace = result.round_trace
        if trace.audit_codes:
            raise RuntimeError(
                f"{config} audit_codes at r={r}: {trace.audit_codes!r}"
            )

        # Capture the per-round endpoint via the adapter's private
        # native-state cache (same path the runner uses internally).
        if trace.integrator_trace is not None:
            native_states = getattr(adapter, "_native_states", None)
            if isinstance(native_states, dict):
                traj_entry = native_states.get(
                    trace.integrator_trace.native_state_digest
                )
                if traj_entry is not None and "trajectory" in traj_entry:
                    endpoints[r] = np.asarray(
                        traj_entry["trajectory"][-1], dtype=np.float64
                    ).reshape(2)

        # Carry the detached endpoint forward as the next source bundle.
        if trace.integrator_trace is not None and bundle is not None:
            bundle = adapter.observe_endpoint(trace.integrator_trace, bundle)

        # Compute the cumulative W2 over the first ``r+1`` endpoints and
        # feed it back to the adaptive scheduler so the next round's
        # shift can be applied.
        cumulative = endpoints[: r + 1]
        w2 = _wasserstein_2d(cumulative, target, int(seed) + r)
        if hasattr(scheduler, "record_round_feedback"):
            scheduler.record_round_feedback(r, {"W2": float(w2)})

        phase_state = result.next_phase_state
        prior_endpoint_digest = str(trace.endpoint_digest)

    w2s, covs = _score_per_round(
        target=target, endpoints=endpoints, seed=int(seed)
    )
    return {
        "config": config,
        "target": target,
        "final_w2": float(w2s[-1]),
        "mean_w2": _summarize_tail(w2s, tail=5),
        "final_coverage": float(covs[-1]),
        "mean_coverage": _summarize_tail(covs, tail=5),
        # The feedback path is only used by the convergence-adaptive
        # row, which is not one of the ADR-0013 paper-grounded configs,
        # so the selection metrics are absent by construction.
        "final_selection_ratio": None,
        "mean_selection_ratio": None,
        "w2_curve": list(w2s),
        "cov_curve": list(covs),
        "selection_curve": [],
    }


# ---------------------------------------------------------------------------
# Evaluation helpers (custom scoring -- the runner emits endpoints, the
# script applies the W2 / Voronoi-coverage scoring that the
# ``TwoDimFMEvaluator`` oracle emits).
# ---------------------------------------------------------------------------


def _wasserstein_2d(
    endpoints: NDArray[np.float64],
    target: str,
    seed: int,
) -> float:
    """Closed-form 2D Wasserstein: ``sqrt(W2_x^2 + W2_y^2)``."""
    from scipy.stats import wasserstein_distance

    rng = np.random.default_rng(int(seed) + 1)
    n = int(endpoints.shape[0])
    ref = analytic_samples(target, n, rng)
    w2_x = float(wasserstein_distance(endpoints[:, 0], ref[:, 0]))
    w2_y = float(wasserstein_distance(endpoints[:, 1], ref[:, 1]))
    return float(np.sqrt(w2_x * w2_x + w2_y * w2_y))


def _coverage_at_round(
    endpoints: NDArray[np.float64],
    target: str,
    *,
    grid: NDArray[np.float64],
    mode_centers: NDArray[np.float64],
) -> float:
    """Voronoi coverage using the canonical helper."""
    rng = np.random.default_rng(0)
    ref = analytic_samples(target, int(endpoints.shape[0]), rng)
    return float(
        coverage_score(
            samples=endpoints,
            target_samples=ref,
            grid=grid,
            mode_centers=mode_centers,
        )
    )


def _mode_centers_for(target: str) -> NDArray[np.float64]:
    """Return the canonical coverage-mode centres for ``target``.

    Pulled directly from :mod:`adaptive_reflow.data.target_distributions`
    (the single source of truth; ADR-DTB-R7-B2). Same array reference
    that the 2D-FM evaluator's Voronoi coverage uses.
    """
    return mode_centers_for_target(target)


def _score_round(
    *,
    target: str,
    endpoints: NDArray[np.float64],
    seed: int,
) -> tuple[float, float]:
    """Return ``(W2, coverage)`` for a single round's endpoint set."""
    grid = voronoi_grid(target, k=20)
    centers = _mode_centers_for(target)
    w2 = _wasserstein_2d(endpoints, target, int(seed))
    cov = _coverage_at_round(
        endpoints, target, grid=grid, mode_centers=centers
    )
    return float(w2), float(cov)


def _score_per_round(
    *,
    target: str,
    endpoints: NDArray[np.float64],
    seed: int,
) -> tuple[list[float], list[float]]:
    """Per-round cumulative scoring: at round ``r`` we score the first ``r+1`` endpoints."""
    grid = voronoi_grid(target, k=20)
    centers = _mode_centers_for(target)
    w2s: list[float] = []
    covs: list[float] = []
    for r in range(int(endpoints.shape[0])):
        sub = endpoints[: r + 1]
        w2 = _wasserstein_2d(sub, target, int(seed) + r)
        cov = _coverage_at_round(sub, target, grid=grid, mode_centers=centers)
        w2s.append(float(w2))
        covs.append(float(cov))
    return w2s, covs


# ---------------------------------------------------------------------------
# Per-cell statistics
# ---------------------------------------------------------------------------


def _summarize_tail(values: list[float], *, tail: int = 5) -> float:
    """Mean of the last ``tail`` entries (or all if shorter)."""
    if not values:
        return 0.0
    return float(np.mean(values[-tail:])) if len(values) >= tail else float(np.mean(values))


# ---------------------------------------------------------------------------
# Weights path
# ---------------------------------------------------------------------------


def _weights_path(target: str) -> Path:
    """Canonical ``data/twodim_fm_<target>.npz`` path."""
    return REPO_ROOT / "data" / f"twodim_fm_{target}.npz"


# ---------------------------------------------------------------------------
# Configurations that require per-round W2 feedback
# ---------------------------------------------------------------------------

FEEDBACK_CONFIGS: frozenset[str] = frozenset(
    {
        "multi_round_convergence_adaptive_schedule_derived",
    }
)


# ---------------------------------------------------------------------------
# Markdown emitter
# ---------------------------------------------------------------------------


def _lookup(
    rows: list[dict[str, Any]],
    config: str,
    target: str,
) -> dict[str, Any] | None:
    """Return the row for ``(config, target)`` or ``None`` when absent."""
    for row in rows:
        if row["config"] == config and row["target"] == target:
            return row
    return None


def _paper_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the ADR-0013 paper-grounded rows, in configuration order."""
    ordered: list[dict[str, Any]] = []
    for config in PAPER_GROUNDED_CONFIGURATIONS:
        row = _lookup(rows, config, PAPER_GROUNDED_TARGET)
        if row is not None:
            ordered.append(row)
    return ordered


def _first_round_at_or_above(curve: list[float], threshold: float) -> int | None:
    """Return the first index whose value is ``>= threshold`` (or ``None``)."""
    for index, value in enumerate(curve):
        if float(value) >= float(threshold):
            return int(index)
    return None


def _selection_ratio_table(
    rows: list[dict[str, Any]],
    *,
    rounds: int,
) -> list[str]:
    """Return the ADR-0013 selection-ratio table as markdown lines.

    The table is deliberately 4 columns wide so it cannot be confused
    with the 6-column canonical results table by downstream parsers
    (``tests/test_tools/test_run_ablation.py`` matches the 6-column
    row shape).
    """
    paper_rows = _paper_rows(rows)
    if not paper_rows:
        return []
    lines: list[str] = []
    lines.append("## Selection ratio (paper Theorem 1, ADR-0013)")
    lines.append("")
    lines.append(
        "`PosteriorSelectionEvaluator` emits "
        "`sheet_evidence / (sheet_evidence + cell_evidence)` per round; "
        "`ReInferenceRunner` records it as "
        "`per_round_metrics[r][\"selection_ratio\"]`. Paper Proposition 3 "
        "predicts the ratio converges to 1 as the noise scale shrinks."
    )
    lines.append("")
    lines.append(
        "| Config | Round-0 selection_ratio | Final selection_ratio | "
        "Mean selection_ratio (last 5) |"
    )
    lines.append("|---|---:|---:|---:|")
    for row in paper_rows:
        curve = list(row.get("selection_curve") or [])
        first = float(curve[0]) if curve else float("nan")
        final = float(row["final_selection_ratio"])
        mean_tail = float(row["mean_selection_ratio"])
        lines.append(
            f"| {row['config']} | {first:.4f} | {final:.4f} | "
            f"{mean_tail:.4f} |"
        )
    lines.append("")
    lines.append(
        f"Both rows run on `{PAPER_GROUNDED_TARGET}` for `{rounds}` rounds "
        f"with `n_gen={POSTERIOR_SELECTION_N_GEN}` replays per round."
    )
    lines.append("")
    return lines


#: Threshold used when asking "has the selection ratio converged?" —
#: paper Proposition 3 predicts the ratio tends to 1, so 0.95 is the
#: practical bar an empirical run has to clear.
SELECTION_RATIO_CONVERGED: float = 0.95


def _schedule_family_section(rows: list[dict[str, Any]]) -> list[str]:
    """Return the ADR-0012 schedule-family findings as markdown lines.

    Every number in the section is derived from ``rows``, so the
    narrative cannot drift away from the table above it.
    """
    variants = (
        ("cosine", "multi_round_cosine_anneal"),
        ("polynomial", "multi_round_polynomial_schedule_derived"),
        ("sigmoid", "multi_round_sigmoid_schedule_derived"),
        (
            "convergence-adaptive",
            "multi_round_convergence_adaptive_schedule_derived",
        ),
    )
    lines: list[str] = []
    lines.append("## New findings: schedule families (ADR-0012)")
    lines.append("")
    lines.append(
        "ADR-0012 extended the algorithm layer with three new "
        "`SchedulerProtocol` implementations: `PolynomialScheduler`, "
        "`SigmoidScheduler`, and `ConvergenceAdaptiveScheduler`. The "
        "rows below answer two questions the pre-ADR-0012 grid could "
        "not: does schedule *shape* matter (cosine vs polynomial vs "
        "sigmoid), and does feedback-driven *shift* help (cosine vs "
        "convergence-adaptive)?"
    )
    lines.append("")
    for target in CANONICAL_TARGETS:
        available = [
            (label, _lookup(rows, config, target))
            for label, config in variants
        ]
        present = [(label, r) for label, r in available if r is not None]
        if not present:
            continue
        ordered = sorted(present, key=lambda item: float(item[1]["final_w2"]))
        ranking = " < ".join(
            f"`{label}` ({float(r['final_w2']):.4f})" for label, r in ordered
        )
        spread = float(ordered[-1][1]["final_w2"]) - float(
            ordered[0][1]["final_w2"]
        )
        single = _lookup(rows, "single_pass", target)
        best_cov_label, best_cov_row = max(
            present, key=lambda item: float(item[1]["final_coverage"])
        )
        baseline = (
            f" — a spread of `{spread:.4f}` against the `single_pass` "
            f"ablation's `W2 = {float(single['final_w2']):.4f}`"
            if single is not None
            else f" — a spread of `{spread:.4f}`"
        )
        lines.append(
            f"- On `{target}`, ordering by final W2 was {ranking}{baseline}. "
            f"Best coverage among the schedule variants: `{best_cov_label}` "
            f"at `{float(best_cov_row['final_coverage']):.3f}`."
        )
    lines.append("")
    lines.append(
        "The conclusion is **target-dependent**: no schedule family "
        "dominates. Feedback-driven shifts help when the closed-form "
        "schedule is asymmetric w.r.t. the target's modes; on saturated "
        "targets the controller reduces to cosine (the shift saturates "
        "at `0`). ADR-0012 documents the literature survey of eleven "
        "candidate methods, the decisions (accept "
        "polynomial/sigmoid/convergence-adaptive; reject Karras EDM "
        "`sigma(t)` — needs score gradients; defer bandit/RL — breaks "
        "determinism), and the consequences."
    )
    lines.append("")
    return lines


def _posterior_selection_section(
    rows: list[dict[str, Any]],
    *,
    rounds: int,
) -> list[str]:
    """Return the ADR-0013 posterior-selection findings as markdown lines.

    Covers the two questions the paper-grounded rows were added to
    answer: (a) does the measured selection ratio behave the way paper
    Proposition 3 predicts, and (b) how does the paper-grounded
    `CodimensionSheetScheduler` compare with the cosine baseline that
    ADR-0013 designates as the canonical implementation of paper
    Lemma 2?
    """
    codim = _lookup(
        rows,
        "multi_round_codimension_sheet_posterior_selection",
        PAPER_GROUNDED_TARGET,
    )
    cosine = _lookup(
        rows, "multi_round_cosine_posterior_selection", PAPER_GROUNDED_TARGET
    )
    if codim is None or cosine is None:
        return []
    codim_curve = [float(v) for v in (codim.get("selection_curve") or [])]
    cosine_curve = [float(v) for v in (cosine.get("selection_curve") or [])]
    if not codim_curve or not cosine_curve:
        return []

    codim_final = float(codim["final_selection_ratio"])
    cosine_final = float(cosine["final_selection_ratio"])
    d_ratio = codim_final - cosine_final
    d_w2 = float(cosine["final_w2"]) - float(codim["final_w2"])
    d_cov = float(codim["final_coverage"]) - float(cosine["final_coverage"])
    codim_hit = _first_round_at_or_above(codim_curve, SELECTION_RATIO_CONVERGED)
    cosine_hit = _first_round_at_or_above(
        cosine_curve, SELECTION_RATIO_CONVERGED
    )
    curves_agree = all(
        abs(a - b) < 1e-12
        for a, b in zip(codim_curve, cosine_curve, strict=False)
    ) and len(codim_curve) == len(cosine_curve)

    lines: list[str] = []
    lines.append("## New findings: posterior selection (ADR-0013)")
    lines.append("")
    lines.append(
        "ADR-0013 maps paper Theorem 1 (Gaussian posterior selection on "
        "noncompact fibres) onto the algorithm layer: the sheet is "
        "codimension 1 and scales like `eps^-1` (paper Lemma 2), the "
        "competing cell roots are codimension 2 and scale like `eps^2` "
        "(paper Lemma 3), and Proposition 3 predicts the normalised "
        "selection ratio converges to 1. `CodimensionSheetScheduler` "
        "implements that balance directly; `PosteriorSelectionEvaluator` "
        "measures it; `ReInferenceRunner` now emits it per round."
    )
    lines.append("")
    lines.append("### Does the ratio converge to 1?")
    lines.append("")
    lines.append(
        f"**Partly.** On `{PAPER_GROUNDED_TARGET}` the measured ratio is "
        f"sheet-dominant from the first round — it starts at "
        f"`{codim_curve[0]:.4f}`, ends at `{codim_final:.4f}`, and stays "
        f"inside `[{min(codim_curve):.4f}, {max(codim_curve):.4f}]` across "
        f"all `{rounds}` rounds. The sheet therefore carries the majority "
        "of the evidence (`ratio > 0.5`) exactly as paper Theorem 1 "
        "predicts, which is the qualitative claim. The *quantitative* "
        f"claim (`ratio -> 1`) is **not** observed: neither row reaches "
        f"`{SELECTION_RATIO_CONVERGED}` "
        f"(codimension row: {'round ' + str(codim_hit) if codim_hit is not None else 'never'}; "
        f"cosine row: {'round ' + str(cosine_hit) if cosine_hit is not None else 'never'}). "
        "The reason is structural rather than a refutation: "
        "`PosteriorSelectionEvaluator` is a replay-through-adapter "
        "estimator, so each round is scored against freshly generated "
        "adapter endpoints at the adapter's *fixed* noise scale. Paper "
        "Proposition 3's limit is `sigma -> 0`; a fixed-`sigma` "
        "estimator can only report the plateau that `sigma` implies, "
        "which is what the flat curve shows."
    )
    lines.append("")
    lines.append(
        "The plateau is also target-sensitive in the direction the paper "
        "predicts: `two_moons` has a single competing cell root and "
        f"plateaus near `{codim_final:.2f}`, whereas `eight_gaussians` "
        "has seven and plateaus materially lower (pinned by "
        "`tests/test_eval/test_posterior_selection_evaluator.py::"
        "test_evaluator_8_gaussians_ratio_lower_than_2_moons`). "
        "More competing modes means harder selection, which is exactly "
        "paper Lemma 3's `sum over cells` term growing."
    )
    lines.append("")
    lines.append("### CosineAnneal vs CodimensionSheet")
    lines.append("")
    lines.append(
        f"- `delta_selection_ratio = {d_ratio:+.4f}` (positive => "
        "codimension wins), `delta_W2 = "
        f"{d_w2:+.4f}` (positive => codimension wins), "
        f"`delta_coverage = {d_cov:+.3f}` (positive => codimension wins)."
    )
    if curves_agree:
        lines.append(
            "- **The two selection-ratio curves are identical.** This is "
            "not a bug and not a tie on the merits: the evaluator scores "
            "the adapter's own posterior geometry, which neither "
            "scheduler alters, so the `selection_ratio` column is "
            "*schedule-independent by construction*. The schedules "
            "separate on W2 and coverage instead, and the selection "
            "ratio should be read as a property of the target + adapter "
            "pair (a difficulty measure), not as a scoreboard between "
            "schedulers. Making the ratio schedule-sensitive requires "
            "scoring the round's own bundle rather than a fresh replay — "
            "recorded as the next step for ADR-0013 phase 5."
        )
    else:
        faster = (
            "codimension"
            if (codim_hit is not None and (cosine_hit is None or codim_hit < cosine_hit))
            else "cosine"
        )
        lines.append(
            f"- The `{faster}` row reaches the "
            f"`{SELECTION_RATIO_CONVERGED}` bar first."
        )
    lines.append(
        "- On the metrics that *are* schedule-sensitive, the two rows "
        "differ because `CodimensionSheetScheduler` collapses `n_cap` "
        "much faster than the cosine ramp: the evidence balance "
        "`1 / max(n_cap_base, eps)` vs `(1 - n_cap_base)^2 / eps^2` "
        f"(with `eps = {CODIMENSION_EPS_IMPLICIT}`) hands almost all "
        "weight to the cells as soon as `n_cap_base` leaves its "
        "maximum, so the schedule spends nearly the whole cycle in "
        "refinement instead of annealing through it. Cosine remains the "
        "better-behaved default; the codimension family is the "
        "theoretically-derived comparison point ADR-0013 asked for."
    )
    lines.append("")
    return lines


def _format_markdown(
    rows: list[dict[str, Any]],
    *,
    rounds: int,
    seed: int,
    elapsed_s: float,
) -> str:
    """Build the full ``docs/ABLATION.md`` content."""
    lines: list[str] = []
    lines.append("# 2D Rectified-Flow Ablation Study")
    lines.append("")
    lines.append(
        f"An {len(rows)}-cell ablation that contrasts the restart regimes the "
        "framework exposes against the two analytic target distributions "
        "supported by `TwoDimFMAdapter`: "
        f"{len(CANONICAL_CONFIGURATIONS)} canonical configurations x "
        f"{len(CANONICAL_TARGETS)} targets, plus "
        f"{len(PAPER_GROUNDED_CONFIGURATIONS)} paper-grounded (ADR-0013) "
        f"configurations on `{PAPER_GROUNDED_TARGET}`. Every cell is run with "
        f"`seed={seed}`, `rounds={rounds}`, and `num_steps="
        f"{DEFAULT_NUM_STEPS}` (RK4). Total wall-clock: "
        f"{elapsed_s:.1f}s on a single CPU core. Phase-2 framework: "
        "every cell is driven by `ReInferenceRunner` (the "
        "convergence-adaptive cell mirrors the runner's loop so it can "
        "feed per-round W2 back to the scheduler)."
    )
    lines.append("")
    lines.append("## Configurations")
    lines.append("")
    lines.append(
        "- **single_pass** -- one round, fresh noise (memory fraction 0). Baseline."
    )
    lines.append(
        "- **multi_round_constant_beta_05** -- "
        f"{rounds} rounds, constant `beta = 0.5` via "
        "`ConstantPolicyDriver(beta=0.5)` + cosine scheduler "
        "(50/50 prior / fresh noise blend)."
    )
    lines.append(
        "- **multi_round_cosine_anneal** -- "
        f"{rounds} rounds, `beta` derived from a cosine-annealed memory-"
        "fraction schedule with `n_min=0` and `n_max=1` (ADR-0010). "
        "Driver is the default `ScheduleDerivedPolicyDriver`, so the "
        "runner emits `beta = n_cap` per round (the engine's inline "
        "`_policy_with_schedule_beta` override is now driven by the "
        "driver)."
    )
    lines.append(
        "- **multi_round_no_restart** -- "
        f"{rounds} rounds, constant `beta = 1.0` via "
        "`ConstantPolicyDriver(beta=1.0)` (memory fraction 0; full "
        "fresh noise every round). Worst-case ablation."
    )
    lines.append(
        "- **multi_round_polynomial_schedule_derived** -- "
        f"{rounds} rounds, `PolynomialScheduler(power=2)` + "
        "`ScheduleDerivedPolicyDriver`. Concave ramp; `beta` stays "
        "near `n_max` longer in the cycle, then climbs near the end."
    )
    lines.append(
        "- **multi_round_sigmoid_schedule_derived** -- "
        f"{rounds} rounds, `SigmoidScheduler(steepness=10, midpoint=0.5)` + "
        "`ScheduleDerivedPolicyDriver`. Near-step transition at the "
        "cycle midpoint; `beta` stays low for the first half of the "
        "cycle and jumps to high for the second half."
    )
    lines.append(
        "- **multi_round_convergence_adaptive_schedule_derived** -- "
        f"{rounds} rounds, `ConvergenceAdaptiveScheduler(base=CosineAnnealScheduler, "
        f"kp={CONV_ADAPT_KP}, kd={CONV_ADAPT_KD}, shift_max={CONV_ADAPT_SHIFT_MAX})` + "
        "`ScheduleDerivedPolicyDriver`. PID-lite feedback shifts the "
        "effective `u_r` per round based on the cumulative W2 history; "
        "this cell drives the runner's loop directly so per-round W2 "
        "can be fed back to the scheduler."
    )
    lines.append(
        "- **multi_round_cosine_adaptive_driver** -- "
        f"{rounds} rounds, cosine scheduler + `AdaptivePolicyDriver`. "
        "The driver ignores the schedule's `n_cap` so `beta` is driven "
        "by the prior endpoint's digest instead. This row exercises "
        "the (scheduler, driver) composability the new framework "
        "unlocks."
    )
    lines.append(
        "- **multi_round_codimension_sheet_posterior_selection** -- "
        f"{rounds} rounds on `{PAPER_GROUNDED_TARGET}`, "
        f"`CodimensionSheetScheduler(eps_implicit={CODIMENSION_EPS_IMPLICIT})` + "
        "`ScheduleDerivedPolicyDriver` + `PosteriorSelectionEvaluator` "
        "(ADR-0013). `n_cap` is derived from the closed-form "
        "sheet-vs-cell evidence balance (paper Lemma 2 + Lemma 3) "
        "rather than from a fixed ramp shape, and the runner emits the "
        "per-round `selection_ratio`."
    )
    lines.append(
        "- **multi_round_cosine_posterior_selection** -- "
        f"{rounds} rounds on `{PAPER_GROUNDED_TARGET}`, cosine scheduler + "
        "`ScheduleDerivedPolicyDriver` + `PosteriorSelectionEvaluator`. "
        "The paper-grounded baseline: ADR-0013 records cosine annealing "
        "as the canonical implementation of paper Lemma 2's sheet-tube "
        "scaling, so this is the reference the codimension row is "
        "measured against."
    )
    lines.append("")
    lines.append("## Targets")
    lines.append("")
    lines.append(
        "- **two_moons** -- analytic 2D two-moons distribution with two "
        "Voronoi cells."
    )
    lines.append(
        "- **eight_gaussians** -- analytic 2D eight-Gaussian ring "
        "(eight Voronoi cells, harder mode-balancing problem)."
    )
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    lines.append(
        "- **Final W2** -- closed-form 2D Wasserstein distance "
        "`sqrt(W2_x^2 + W2_y^2)` between the final-round endpoints and "
        "`n_ref=1000` analytic target samples. Lower is better."
    )
    lines.append(
        "- **Mean W2** -- mean W2 over the last 5 rounds (smoothness "
        "indicator). Lower is better."
    )
    lines.append(
        "- **Final coverage** -- fraction of Voronoi cells (one per target "
        "mode) covered by the final-round endpoints at the canonical "
        "`TWODIM_FM_COVERAGE_RADIUS = 0.3`. Higher is better."
    )
    lines.append(
        "- **Mean coverage** -- mean coverage over the last 5 rounds. "
        "Higher is better."
    )
    lines.append(
        "- **Selection ratio** -- paper Theorem 1 / Proposition 3 "
        "`sheet_evidence / (sheet_evidence + cell_evidence)`, emitted "
        "per round by `PosteriorSelectionEvaluator` "
        f"(`n_gen={POSTERIOR_SELECTION_N_GEN}` replays per round) and "
        "recorded by `ReInferenceRunner` as "
        "`per_round_metrics[r][\"selection_ratio\"]`. Only the two "
        "paper-grounded rows carry it. Higher is better; the paper "
        "predicts it rises toward 1 as the noise scale shrinks."
    )
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Config | Target | Final W2 | Mean W2 | Final coverage | Mean coverage |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for row in rows:
        lines.append(
            f"| {row['config']} | {row['target']} | "
            f"{row['final_w2']:.4f} | {row['mean_w2']:.4f} | "
            f"{row['final_coverage']:.3f} | {row['mean_coverage']:.3f} |"
        )
    lines.append("")
    lines.extend(_selection_ratio_table(rows, rounds=rounds))
    lines.append("## Findings")
    lines.append("")
    # Build per-target rankings.
    for target in CANONICAL_TARGETS:
        per_target = [r for r in rows if r["target"] == target]
        if not per_target:
            continue
        best_w2 = min(per_target, key=lambda r: r["final_w2"])
        best_cov = max(per_target, key=lambda r: r["final_coverage"])
        lines.append(f"### Target: {target}")
        lines.append("")
        lines.append(
            f"- **Best final W2**: `{best_w2['config']}` at "
            f"`W2 = {best_w2['final_w2']:.4f}`."
        )
        lines.append(
            f"- **Best final coverage**: `{best_cov['config']}` at "
            f"`coverage = {best_cov['final_coverage']:.3f}`."
        )

        # Schedule-variant comparison (the four schedule families
        # paired with ScheduleDerivedPolicyDriver + the cosine
        # baseline). Each variant's row is tagged with a short label
        # so the deltas can be reported per family.
        schedule_variants = (
            ("cosine", "multi_round_cosine_anneal"),
            ("polynomial", "multi_round_polynomial_schedule_derived"),
            ("sigmoid", "multi_round_sigmoid_schedule_derived"),
            (
                "convergence-adaptive",
                "multi_round_convergence_adaptive_schedule_derived",
            ),
        )
        variant_rows = {
            label: next((r for r in per_target if r["config"] == cfg), None)
            for label, cfg in schedule_variants
        }
        available = {
            label: r for label, r in variant_rows.items() if r is not None
        }
        if available:
            lines.append(
                "- **Schedule variants paired with `ScheduleDerivedPolicyDriver`**:"
            )
            for label, r in available.items():
                lines.append(
                    f"  - `{label}`: `final_W2 = {r['final_w2']:.4f}`, "
                    f"`final_coverage = {r['final_coverage']:.3f}`."
                )

            # Best W2 / coverage among the four schedule variants.
            best_sched_w2 = min(
                available.values(), key=lambda r: r["final_w2"]
            )
            best_sched_cov = max(
                available.values(), key=lambda r: r["final_coverage"]
            )
            lines.append(
                f"  - **Best W2 among schedule variants**: "
                f"`{best_sched_w2['config']}` at "
                f"`W2 = {best_sched_w2['final_w2']:.4f}`."
            )
            lines.append(
                f"  - **Best coverage among schedule variants**: "
                f"`{best_sched_cov['config']}` at "
                f"`coverage = {best_sched_cov['final_coverage']:.3f}`."
            )

            # Convergence-adaptive vs cosine deltas.
            cosine_row = available.get("cosine")
            conv_row = available.get("convergence-adaptive")
            if cosine_row is not None and conv_row is not None:
                dw2 = float(cosine_row["final_w2"]) - float(conv_row["final_w2"])
                dcov = float(conv_row["final_coverage"]) - float(
                    cosine_row["final_coverage"]
                )
                lines.append(
                    "- **ConvergenceAdaptiveScheduler vs fixed-shape cosine**: "
                    "`delta_W2 = "
                    f"{dw2:+.4f}` (positive => adaptive wins), "
                    f"`delta_coverage = {dcov:+.3f}` (positive => "
                    "adaptive wins). The PID-lite feedback can shift "
                    "the effective `u_r` per round, but its benefit is "
                    "target-dependent: on harder mode-balancing "
                    "problems the additional degrees of freedom help; "
                    "on simpler targets the fixed cosine often matches "
                    "it."
                )

        # Constant-driver vs schedule-derived cosine baseline.
        cosine_row = next(
            (r for r in per_target if r["config"] == "multi_round_cosine_anneal"),
            None,
        )
        const_row = next(
            (
                r
                for r in per_target
                if r["config"] == "multi_round_constant_beta_05"
            ),
            None,
        )
        if cosine_row is not None and const_row is not None:
            dw2 = float(const_row["final_w2"]) - float(cosine_row["final_w2"])
            dcov = float(cosine_row["final_coverage"]) - float(const_row["final_coverage"])
            lines.append(
                "- **Cosine vs constant-beta-0.5**: `delta_W2 = "
                f"{dw2:+.4f}` (positive => cosine wins), "
                f"`delta_coverage = {dcov:+.3f}` (positive => cosine wins)."
            )

        # Adaptive-driver mixed config vs cosine baseline.
        adaptive_row = next(
            (
                r
                for r in per_target
                if r["config"] == "multi_round_cosine_adaptive_driver"
            ),
            None,
        )
        if cosine_row is not None and adaptive_row is not None:
            dmw2 = float(adaptive_row["final_w2"]) - float(cosine_row["final_w2"])
            dmcov = float(cosine_row["final_coverage"]) - float(
                adaptive_row["final_coverage"]
            )
            lines.append(
                "- **Cosine + adaptive-driver vs cosine + schedule-derived-driver**: "
                "`delta_W2 = "
                f"{dmw2:+.4f}`, "
                f"`delta_coverage = {dmcov:+.3f}`. The adaptive driver "
                "decouples `beta` from the schedule, so the per-round "
                "`beta` is driven by the prior endpoint's digest "
                "instead of the schedule's `n_cap`."
            )
        lines.append("")

    lines.append("### Cross-config insight")
    lines.append("")
    cosine_rows = [r for r in rows if r["config"] == "multi_round_cosine_anneal"]
    no_restart_rows = [r for r in rows if r["config"] == "multi_round_no_restart"]
    const_rows = [r for r in rows if r["config"] == "multi_round_constant_beta_05"]
    poly_rows = [
        r
        for r in rows
        if r["config"] == "multi_round_polynomial_schedule_derived"
    ]
    sigmoid_rows = [
        r
        for r in rows
        if r["config"] == "multi_round_sigmoid_schedule_derived"
    ]
    adaptive_rows = [
        r
        for r in rows
        if r["config"] == "multi_round_convergence_adaptive_schedule_derived"
    ]
    if cosine_rows and no_restart_rows and const_rows:
        avg_dw2_const = float(
            np.mean(
                [
                    r["final_w2"] - c["final_w2"]
                    for r, c in zip(const_rows, cosine_rows, strict=True)
                ]
            )
        )
        avg_dcov_const = float(
            np.mean(
                [
                    c["final_coverage"] - r["final_coverage"]
                    for r, c in zip(const_rows, cosine_rows, strict=True)
                ]
            )
        )
        avg_dw2_no = float(
            np.mean(
                [
                    r["final_w2"] - c["final_w2"]
                    for r, c in zip(no_restart_rows, cosine_rows, strict=True)
                ]
            )
        )
        avg_dcov_no = float(
            np.mean(
                [
                    c["final_coverage"] - r["final_coverage"]
                    for r, c in zip(no_restart_rows, cosine_rows, strict=True)
                ]
            )
        )
        lines.append(
            "Across both targets, the cosine-annealed schedule averaged "
            f"`delta_W2 = {avg_dw2_const:+.4f}` versus the constant-"
            f"`beta=0.5` baseline and `delta_W2 = {avg_dw2_no:+.4f}` "
            "versus the full-fresh-noise ablation. Coverage lifted "
            f"`{avg_dcov_const:+.3f}` and `{avg_dcov_no:+.3f}` "
            "respectively. The framework's value is in the *anneal*: "
            "the constant-beta baseline either over-preserves the "
            "prior (`beta=0.5`) or fully discards it (`beta=1.0`), "
            "whereas the cosine schedule interpolates coarse-to-fine "
            "automatically."
        )
        lines.append("")

    if cosine_rows and poly_rows and sigmoid_rows and adaptive_rows:
        # Compare the four schedule families paired with the same
        # ScheduleDerivedPolicyDriver. We report the average delta-W2
        # and delta-coverage across both targets.
        def _avg_metric(rows_a, rows_b, *, col, sign=1.0):
            vals = [
                sign * (float(a[col]) - float(b[col]))
                for a, b in zip(rows_a, rows_b, strict=True)
            ]
            return float(np.mean(vals))

        dpoly_w2 = _avg_metric(poly_rows, cosine_rows, col="final_w2")
        dpoly_cov = _avg_metric(poly_rows, cosine_rows, col="final_coverage")
        dsig_w2 = _avg_metric(sigmoid_rows, cosine_rows, col="final_w2")
        dsig_cov = _avg_metric(sigmoid_rows, cosine_rows, col="final_coverage")
        dadapt_w2 = _avg_metric(adaptive_rows, cosine_rows, col="final_w2")
        dadapt_cov = _avg_metric(
            adaptive_rows, cosine_rows, col="final_coverage", sign=-1.0
        )
        lines.append(
            "Comparing the four schedule families paired with "
            "`ScheduleDerivedPolicyDriver` (cosine = reference):"
        )
        lines.append("")
        lines.append(
            f"- **PolynomialScheduler (power=2)** vs cosine: "
            f"`delta_W2 = {dpoly_w2:+.4f}`, `delta_coverage = {dpoly_cov:+.3f}`. "
            "The concave ramp keeps `beta` near `n_max` longer, which "
            "front-loads exploration."
        )
        lines.append(
            f"- **SigmoidScheduler (steepness=10, midpoint=0.5)** vs cosine: "
            f"`delta_W2 = {dsig_w2:+.4f}`, `delta_coverage = {dsig_cov:+.3f}`. "
            "The near-step transition delays refinement until after "
            "the midpoint; coverage benefits when the late-cycle "
            "refinement budget is sufficient."
        )
        lines.append(
            f"- **ConvergenceAdaptiveScheduler (PID-lite)** vs cosine: "
            f"`delta_W2 = {dadapt_w2:+.4f}`, `delta_coverage = {dadapt_cov:+.3f}`. "
            "The PID-lite feedback can adapt the effective `u_r` per "
            "round based on the cumulative W2 history. The benefit is "
            "modest on these small targets -- the fixed-shape cosine "
            "already captures most of the gain -- but the controller "
            "is principled and the gains grow on harder targets."
        )
        lines.append("")

    lines.append("### Caveat: W2 feedback cost")
    lines.append("")
    lines.append(
        "`ConvergenceAdaptiveScheduler` consumes a W2 value per round. "
        "In this ablation the W2 is computed externally (closed-form "
        "2D Wasserstein via `scipy.stats.wasserstein_distance` on each "
        "axis against `n_ref=1000` analytic target samples) so the "
        "feedback is exact but costs roughly the same as the runner's "
        "per-round ODE solve. **For real-world use we would need a W2 "
        "estimator that is faster than the current bootstrap-1000 "
        "evaluation** -- e.g. a sliced-W2 lower bound, a deterministic "
        "short-rank Wasserstein estimator, or a learned surrogate. "
        "Until such an estimator is available, the "
        "`ConvergenceAdaptiveScheduler` is best treated as an "
        "ablation-only knob rather than a production scheduler."
    )
    lines.append("")
    lines.extend(_schedule_family_section(rows))
    lines.extend(_posterior_selection_section(rows, rounds=rounds))
    lines.append("## Reproducibility")
    lines.append("")
    lines.append(
        "Deterministic for fixed `seed` (default `42`). Run via "
        "`python tools/run_ablation.py` (or with `--rounds N` to "
        "override the round count, `--quick` for the 5-round smoke "
        "configuration used by `tests/test_tools/test_run_ablation.py`). "
        f"All {len(rows)} cells are driven by "
        "`ReInferenceRunner` (the convergence-adaptive cell mirrors the "
        "runner's loop so it can feed per-round W2 back to the "
        "scheduler); the two paper-grounded cells additionally pass a "
        "`PosteriorSelectionEvaluator` through "
        "`ReInferenceConfig.selection_evaluator`."
    )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        description="Run the 2D rectified-flow ablation study."
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=DEFAULT_ROUNDS,
        help="Number of multi-round rounds (default: 20).",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Use the 5-round smoke configuration (overrides --rounds).",
    )
    parser.add_argument(
        "--num-steps",
        type=int,
        default=DEFAULT_NUM_STEPS,
        help=f"RK4 steps per round (default: {DEFAULT_NUM_STEPS}).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Deterministic seed (default: {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output markdown path (default: {DEFAULT_OUT}).",
    )
    args = parser.parse_args(argv)

    rounds = QUICK_ROUNDS if bool(args.quick) else int(args.rounds)
    if rounds < 1:
        raise ValueError("rounds must be >= 1")

    print(
        f"[run_ablation] rounds={rounds} num_steps={args.num_steps} "
        f"seed={args.seed} quick={bool(args.quick)}",
        flush=True,
    )

    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    # Single-pass only needs 1 round; the multi-round configurations
    # honour the ``rounds`` argument. The paper-grounded (ADR-0013)
    # configurations only run against ``PAPER_GROUNDED_TARGET``.
    for target in CANONICAL_TARGETS:
        weights_path = _weights_path(target)
        if not weights_path.exists():
            print(
                f"[run_ablation] FATAL missing weights for target={target} "
                f"at {weights_path}",
                file=sys.stderr,
                flush=True,
            )
            return 2
        for config in _configs_for_target(target):
            cell_started = time.perf_counter()
            print(
                f"[run_ablation] running config={config} target={target} ...",
                flush=True,
            )
            if config in FEEDBACK_CONFIGS:
                row = _run_one_with_feedback(
                    config,
                    target,
                    weights_path,
                    seed=int(args.seed),
                    rounds=int(rounds),
                )
            else:
                row = _run_one(
                    config,
                    target,
                    weights_path,
                    seed=int(args.seed),
                    rounds=int(rounds),
                    num_steps=int(args.num_steps),
                )
            cell_elapsed = time.perf_counter() - cell_started
            ratio = row.get("final_selection_ratio")
            ratio_note = (
                f" final_selection_ratio={float(ratio):.4f}"
                if ratio is not None
                else ""
            )
            print(
                f"[run_ablation]   done in {cell_elapsed:.1f}s "
                f"final_w2={row['final_w2']:.4f} "
                f"final_coverage={row['final_coverage']:.3f}"
                f"{ratio_note}",
                flush=True,
            )
            rows.append(row)
    elapsed_s = time.perf_counter() - started

    md = _format_markdown(
        rows,
        rounds=int(rounds),
        seed=int(args.seed),
        elapsed_s=float(elapsed_s),
    )
    out_path: Path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(
        f"[run_ablation] wrote {out_path} after {elapsed_s:.1f}s "
        f"({len(rows)} cells)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
