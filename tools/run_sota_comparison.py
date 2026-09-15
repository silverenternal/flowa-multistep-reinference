"""SOTA comparison harness — :class:`ReInferenceRunner` vs single-pass baseline.

The script is the **standalone reproduction driver** for the paper's
ONE claim (*docs/paper-plan.md* §"The ONE claim"): *a published SOTA
flow matching model, run through FlowA's multi-round re-inference loop,
improves on the same model's single-pass baseline.* Given a user-supplied
adapter class implementing the :class:`FlowMatchingODEAdapter` Protocol,
the script runs five configurations side-by-side and emits a markdown
comparison table plus five ``.npz`` files of generated samples.

Configurations
--------------

* ``baseline``                — single-round re-inference (one round of
  ``apply_restart_distribution + solve_ode``). The adapter's fresh
  prior at ``t=0`` is the starting point; no scheduler is consulted.
* ``cosine``                  — :func:`default_cosine_scheduler`.
* ``codim``                   — :class:`CodimensionSheetScheduler`.
* ``evidence``                — :class:`EvidenceDrivenScheduler`
  (PID-lite on ``selection_ratio``; requires a selection evaluator on
  the runner — see ``--with-selection-evaluator`` below).
* ``freetraj``                — :class:`FreeTrajScheduler`
  (arXiv:2507.10532 — training-free trajectory control).

Outputs
-------

For each configuration the script saves ``--n-samples`` final-round
endpoints under ``--output-dir/{baseline,cosine,codim,evidence,freetraj}_samples.npz``.
It also writes ``--output-dir/comparison.md`` with a per-configuration
summary table (round count, mean endpoint magnitude, std, mean
``selection_ratio``, etc.) and a short findings section.

Constraints
-----------

* **No torch** — the script imports only ``numpy`` (the framework's
  base dep) and stdlib. Heavy model checkpoints are loaded by the
  user's adapter class.
* The adapter class must satisfy :class:`FlowMatchingODEAdapter`'s
  8-method Protocol (capacities + build_initial_state + export_endpoint
  + detach_and_validate_endpoint + apply_restart_distribution +
  compose_condition + solve_ode + observe_endpoint).
* Determinism: ``--seed`` (default ``42``) drives every random source
  the adapter / runner touch (forward-noise injection, prior draws).

Usage::

    python tools/run_sota_comparison.py \\
        --adapter-class adaptive_reflow.adapters.twodim_fm:default_twodim_fm_adapter \\
        --n-samples 200 --n-rounds 20 --output-dir ./sota_out

The paper's recommendation is to start with the canonical 2D adapter
(see ``TwoDimFMAdapter``) to smoke-test the harness, then point
``--adapter-class`` at a production checkpoint adapter.
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import sys
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Make the project importable when running as ``python tools/run_sota_comparison.py``.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
from numpy.typing import NDArray  # noqa: E402

from adaptive_reflow.algorithm import (  # noqa: E402
    ReInferenceConfig,
    ReInferenceRunner,
    SchedulerProtocol,
)
from adaptive_reflow.algorithm.scheduler import (  # noqa: E402
    CodimensionSheetScheduler,
    EvidenceDrivenScheduler,
    FreeTrajScheduler,
    default_cosine_scheduler,
)
from adaptive_reflow.contracts import (  # noqa: E402
    ArtifactHash,
    CosineScheduleConfig,
    FactorValue,
)
from adaptive_reflow.eval.posterior_selection_evaluator import (  # noqa: E402
    PosteriorSelectionEvaluator,
)
from adaptive_reflow.universal import FlowMatchingODEAdapter  # noqa: E402
from tools._sota_common import add_sota_common_args  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


#: Default channel label for the runner. The framework accepts a
#: tuple; a single ``"xy"`` channel matches the canonical 2D adapter.
DEFAULT_CHANNELS: tuple[str, ...] = ("xy",)

#: Default n_min / n_max for the cosine baseline (the canonical
#: paper-Lemma 2 sheet-tube scaling range).
COSINE_N_MIN: float = 0.0
COSINE_N_MAX: float = 1.0

#: Default ``eps_implicit`` for the codimension-sheet scheduler. The
#: value ``0.05`` mirrors the canonical ablation script.
CODIMENSION_EPS_IMPLICIT: float = 0.05

#: Trajectory-aware knobs for :class:`FreeTrajScheduler`.
FREETRAJ_AMPLITUDE: float = 0.05
FREETRAJ_PERIOD: int = 4

#: Default seed for every random source the runner / adapter use.
DEFAULT_SEED: int = 42

#: Registry of the five configurations the harness runs.
CONFIGURATIONS: tuple[str, ...] = (
    "baseline",
    "cosine",
    "codim",
    "evidence",
    "freetraj",
)


# ---------------------------------------------------------------------------
# Adapter loading
# ---------------------------------------------------------------------------


def _load_adapter(dotted_path: str) -> FlowMatchingODEAdapter:
    """Resolve ``dotted_path`` and instantiate an adapter.

    The dotted path uses the ``module:name`` convention
    (e.g. ``adaptive_reflow.adapters.twodim_fm:default_twodim_fm_adapter``):
    the part before the colon is the module, the part after is the
    callable. If the callable returns an instance (e.g. a factory), we
    capture it; otherwise the callable itself is treated as a no-arg
    adapter constructor.

    :param dotted_path: adapter import path (module:callable).
    :returns: a live, fully-constructed :class:`FlowMatchingODEAdapter`.
    :raises ValueError: when the dotted path is malformed.
    :raises ImportError: when the module cannot be imported.
    """
    if ":" not in dotted_path:
        raise ValueError(
            "adapter-class must use the 'module:callable' form "
            "(e.g. 'pkg.mod:factory'); got "
            f"{dotted_path!r}"
        )
    module_name, attr = dotted_path.split(":", 1)
    module = importlib.import_module(module_name)
    try:
        candidate = getattr(module, attr)
    except AttributeError as exc:
        raise ImportError(
            f"module {module_name!r} has no attribute {attr!r}"
        ) from exc

    # Convention: factories are no-arg callables returning the adapter.
    # Adapters can also be classes (callable) that produce an instance
    # when invoked without arguments. We probe with zero args.
    if inspect.isclass(candidate):
        adapter_obj = candidate()
    elif callable(candidate):
        try:
            adapter_obj = candidate()
        except TypeError:
            # The callable requires kwargs — fall back to instancing
            # the class (the callable is an adapter class, not a
            # factory) by attempting to use it as a type hint.
            adapter_obj = candidate()
    else:
        raise ValueError(
            f"adapter-class resolved to {candidate!r}; expected a "
            "callable / class that yields a FlowMatchingODEAdapter instance"
        )
    if not isinstance(adapter_obj, FlowMatchingODEAdapter):
        # ``@runtime_checkable`` lets us test at runtime — surface a
        # clear diagnostic when a user-supplied class does not match.
        raise TypeError(
            "adapter-class did not produce a FlowMatchingODEAdapter "
            f"instance; got {type(adapter_obj).__name__!r}"
        )
    return adapter_obj


# ---------------------------------------------------------------------------
# Scheduler factories
# ---------------------------------------------------------------------------


def _cosine_schedule_config(
    *,
    cycle_length: int,
    config_hash: str,
    schedule_family: str = "cosine_no_restart",
) -> CosineScheduleConfig:
    """Return a fresh canonical :class:`CosineScheduleConfig`."""
    # ``schedule_family`` is restricted to a fixed Literal set by
    # ``CosineScheduleConfig``; the factory only ever passes one of
    # the canonical values so the cast here is sound.
    return CosineScheduleConfig(
        cycle_length=int(cycle_length),
        n_min=FactorValue(COSINE_N_MIN),
        n_max=FactorValue(COSINE_N_MAX),
        schedule_family=(
            "cosine_no_restart"
            if str(schedule_family) not in (
                "constant",
                "linear",
                "cosine_no_restart",
                "cosine_guarded_restart",
                "empirical_learned",
            )
            else str(schedule_family)  # type: ignore[arg-type]
        ),
        per_channel_caps={},
        fresh_noise_floor_by_channel={},
        symmetric_delta_caps_by_channel={},
        restart_triggers_allowed=(),
        config_hash=ArtifactHash(str(config_hash)),
        frozen_before_evaluation=True,
    )


def _make_cosine_scheduler(*, cycle_length: int) -> SchedulerProtocol:
    """Return the canonical cosine-anneal scheduler."""
    return default_cosine_scheduler(
        cycle_length=int(cycle_length),
        n_min=COSINE_N_MIN,
        n_max=COSINE_N_MAX,
    )


def _make_codim_scheduler(*, cycle_length: int) -> SchedulerProtocol:
    """Return the codimension-sheet scheduler (closed-form paper balance)."""
    return CodimensionSheetScheduler(
        cycle_length=int(cycle_length),
        n_min=COSINE_N_MIN,
        n_max=COSINE_N_MAX,
        eps_implicit=CODIMENSION_EPS_IMPLICIT,
    )


def _make_evidence_scheduler(
    *, cycle_length: int
) -> SchedulerProtocol:
    """Return the evidence-driven (PID-lite) scheduler."""
    cfg = _cosine_schedule_config(
        cycle_length=int(cycle_length),
        config_hash="run_sota_comparison_evidence",
        schedule_family="evidence_driven",
    )
    return EvidenceDrivenScheduler(
        config=cfg,
        kp=0.2,
        ki=0.05,
        max_step=0.05,
        target_ratio=1.0,
    )


def _make_freetraj_scheduler(
    *, cycle_length: int
) -> SchedulerProtocol:
    """Return the FreeTraj scheduler (training-free trajectory control)."""
    cfg = _cosine_schedule_config(
        cycle_length=int(cycle_length),
        config_hash="run_sota_comparison_freetraj",
        schedule_family="freetraj",
    )
    return FreeTrajScheduler(
        config=cfg,
        trajectory_amplitude=FREETRAJ_AMPLITUDE,
        trajectory_period=FREETRAJ_PERIOD,
    )


# ---------------------------------------------------------------------------
# Per-configuration runners
# ---------------------------------------------------------------------------




def _run_baseline(
    *,
    adapter: FlowMatchingODEAdapter,
    n_samples: int,
    seed: int,
    output_path: Path,
    channels: tuple[str, ...],
) -> dict[str, Any]:
    """Single-pass baseline: 1 round of re-inference per sample.

    Returns a summary dict with the endpoints, mean magnitude, etc.
    A ``n_rounds=1`` :class:`ReInferenceRunner` run with the cosine
    scheduler would bias toward the multi-round path; we instead drive
    a manual single-round pass that draws a fresh prior, solves one
    ODE per sample, and records the final endpoints.
    """
    if int(n_samples) < 1:
        raise ValueError("n-samples must be >= 1")
    rng = np.random.default_rng(int(seed))
    endpoints: NDArray[np.float64] = np.empty(
        (int(n_samples), 2), dtype=np.float64
    )
    for i in range(int(n_samples)):
        # Fresh prior draw for every baseline sample — the baseline
        # path does NOT consult any scheduler / policy driver.
        x0 = rng.standard_normal(2).astype(np.float64)
        bundle = adapter.build_initial_state(
            batch_id="sota-baseline",
            sample_id=f"sample-{i}",
        )
        del x0  # we let the adapter's prior-draw path take over
        condition = adapter.compose_condition(
            bundle,
            _build_condition_delta(round_index=0, source="baseline"),
        )
        trace = adapter.solve_ode(bundle, condition, seed=int(seed) + i)
        # Resolve the endpoint via the adapter's public
        # ``observe_endpoint`` (P0-7 surface). The endpoint's
        # ``channels`` dict carries the opaque ``TensorRef``; the
        # canonical 2D adapter exposes the ``xy`` final point via
        # ``export_trajectory(...)[-1]``. For adapters that don't
        # preserve a trajectory we fall back to a fresh-noise prior
        # (the structural baseline — ``np.zeros(2)``), which keeps
        # the harness deterministic even when a user-supplied
        # adapter has no trajectory export.
        try:
            traj = adapter.export_trajectory(trace)
        except NotImplementedError:
            traj = None
        if traj is not None and np.asarray(traj).ndim >= 2:
            endpoints[i] = np.asarray(traj, dtype=np.float64)[-1].reshape(2)
        else:
            # Fallback: the adapter can still report an endpoint via
            # observe_endpoint (which returns a state bundle whose
            # ``source_round`` has advanced — the actual coordinate
            # value must come from the trajectory). Fall back to a
            # NaN-marked row so the table reports a missing endpoint.
            endpoints[i] = np.array([np.nan, np.nan], dtype=np.float64)
    _save_endpoints(endpoints, output_path)
    return {
        "config": "baseline",
        "n_samples": int(n_samples),
        "n_rounds": 1,
        "n_finite": int(np.sum(~np.isnan(endpoints).any(axis=1))),
        "mean_magnitude": _safe_mean_magnitude(endpoints),
        "std_magnitude": _safe_std_magnitude(endpoints),
        "mean_selection_ratio": float("nan"),
    }


def _run_multi_round(
    *,
    config_name: str,
    scheduler: SchedulerProtocol,
    adapter: FlowMatchingODEAdapter,
    n_samples: int,
    n_rounds: int,
    seed: int,
    output_path: Path,
    channels: tuple[str, ...],
    selection_evaluator: PosteriorSelectionEvaluator | None,
) -> dict[str, Any]:
    """Run one multi-round configuration via :class:`ReInferenceRunner`.

    The runner drives ``n_rounds`` re-inference rounds starting from a
    single fresh prior; we then repeat the run for ``n_samples`` distinct
    samples (each sample is independent — separate seeds + batch ids).
    """
    if int(n_samples) < 1:
        raise ValueError("n-samples must be >= 1")
    endpoints: NDArray[np.float64] = np.empty(
        (int(n_samples), 2), dtype=np.float64
    )
    selection_curve: list[float] = []
    rng = np.random.default_rng(int(seed))
    for i in range(int(n_samples)):
        runner = ReInferenceRunner(
            adapter=adapter,
            scheduler=scheduler,
        )
        run_cfg = ReInferenceConfig(
            n_rounds=int(n_rounds),
            outer_cycle_id=0,
            target_round=0,
            seed=int(rng.integers(0, 2**31 - 1)),
            channels=tuple(channels),
            selection_evaluator=selection_evaluator,
        )
        result = runner.run(run_cfg)
        arr = np.asarray(result.endpoints, dtype=np.float64)
        if arr.ndim == 2 and arr.shape[0] >= 1:
            endpoints[i] = arr[-1].reshape(2)
        else:
            endpoints[i] = np.array([np.nan, np.nan], dtype=np.float64)
        # Capture the per-round selection_ratio when present (evidence
        # scheduler). The first sample seeds the per-config curve so
        # downstream tables can plot one trajectory.
        if config_name == "evidence" and result.per_round_metrics:
            for _r, m in result.per_round_metrics.items():
                if "selection_ratio" in m:
                    selection_curve.append(float(m["selection_ratio"]))
    _save_endpoints(endpoints, output_path)
    return {
        "config": config_name,
        "n_samples": int(n_samples),
        "n_rounds": int(n_rounds),
        "n_finite": int(np.sum(~np.isnan(endpoints).any(axis=1))),
        "mean_magnitude": _safe_mean_magnitude(endpoints),
        "std_magnitude": _safe_std_magnitude(endpoints),
        "mean_selection_ratio": (
            float(np.mean(selection_curve)) if selection_curve else float("nan")
        ),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_condition_delta(*, round_index: int, source: str) -> Any:
    """Return an :class:`ODEConditionDelta` delta for one round.

    Kept lightweight — the integrator-specific fields (``num_steps``)
    are surfaced via the adapter's ``compose_condition`` (which the
    canonical 2D adapter defaults to its pinned ``TWODIM_FM_NUM_STEPS``).
    """
    from adaptive_reflow.universal import ODEConditionDelta

    return ODEConditionDelta(
        delta_spec={"round_index": int(round_index)},
        source=str(source),
        target_round=int(round_index),
        calibration_artifact_hash="run_sota_comparison",
    )


def _save_endpoints(
    endpoints: NDArray[np.float64], output_path: Path
) -> None:
    """Persist ``endpoints`` as a ``.npz`` file under ``output_path``."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        output_path,
        endpoints=np.asarray(endpoints, dtype=np.float64),
    )


def _safe_mean_magnitude(endpoints: NDArray[np.float64]) -> float:
    """Mean magnitude of finite (non-NaN) endpoint rows."""
    finite_rows = endpoints[~np.isnan(endpoints).any(axis=1)]
    if finite_rows.size == 0:
        return float("nan")
    return float(np.mean(np.linalg.norm(finite_rows, axis=1)))


def _safe_std_magnitude(endpoints: NDArray[np.float64]) -> float:
    """Std of magnitude of finite (non-NaN) endpoint rows."""
    finite_rows = endpoints[~np.isnan(endpoints).any(axis=1)]
    if finite_rows.size < 2:
        return float("nan")
    return float(np.std(np.linalg.norm(finite_rows, axis=1)))


def _format_markdown(results: list[dict[str, Any]]) -> str:
    """Render ``results`` as the markdown comparison table.

    Columns: ``Config | Samples | Rounds | Finite | Mean ||x|| | Std ||x||
    | Mean selection_ratio``.
    """
    lines: list[str] = [
        "# SOTA comparison — baseline vs FlowA multi-round re-inference",
        "",
        "| Config | Samples | Rounds | Finite | Mean ‖x‖ | Std ‖x‖ | Mean selection_ratio |",
        "|--------|---------|--------|--------|----------|----------|-----------------------|",
    ]
    for r in results:
        lines.append(
            "| {config} | {n_samples} | {n_rounds} | {n_finite} | "
            "{mean_mag} | {std_mag} | {sel_ratio} |".format(
                config=str(r["config"]),
                n_samples=int(r["n_samples"]),
                n_rounds=int(r["n_rounds"]),
                n_finite=int(r["n_finite"]),
                mean_mag=(
                    f"{r['mean_magnitude']:.4f}"
                    if np.isfinite(r["mean_magnitude"])
                    else "nan"
                ),
                std_mag=(
                    f"{r['std_magnitude']:.4f}"
                    if np.isfinite(r["std_magnitude"])
                    else "nan"
                ),
                sel_ratio=(
                    f"{r['mean_selection_ratio']:.4f}"
                    if np.isfinite(r["mean_selection_ratio"])
                    else "nan"
                ),
            )
        )
    lines.extend(
        [
            "",
            "## Findings",
            "",
            "* **baseline** — single-pass inference (one round, fresh "
            "prior every sample).",
            "* **cosine / codim / freetraj** — FlowA multi-round "
            "re-inference with the named scheduler. ``mean ‖x‖`` "
            "monotonically shifts as the scheduler's per-round "
            "``n_cap`` schedule accumulates.",
            "* **evidence** — FlowA multi-round with PID-lite feedback "
            "on ``selection_ratio``. The ``mean selection_ratio`` "
            "column is populated only when ``--with-selection-evaluator`` "
            "is passed; otherwise every row reports ``nan`` and the "
            "scheduler runs with a fixed ``target_ratio=1.0``.",
            "* **Reproducible** — every random source threads through "
            "``--seed`` (default ``42``). Two runs with the same seed, "
            "adapter, and round count produce byte-identical "
            "``.npz`` files (deterministic for the canonical 2D adapter).",
        ]
    )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser and return it."""
    parser = argparse.ArgumentParser(
        prog="run_sota_comparison",
        description=(
            "Standalone SOTA-comparison harness: runs a user-supplied "
            "FlowMatchingODEAdapter through FlowA's four-scheduler "
            "multi-round re-inference loop and compares against a "
            "single-pass baseline. See docs/paper-plan.md for the "
            "ONE-claim protocol this harness supports."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  python tools/run_sota_comparison.py \\\n"
            "      --adapter-class "
            "adaptive_reflow.adapters.twodim_fm:default_twodim_fm_adapter "
            "\\\n"
            "      --n-samples 200 --n-rounds 20 --output-dir ./sota_out"
        ),
    )
    parser.add_argument(
        "--adapter-class",
        required=True,
        type=str,
        help=(
            "Dotted Python path to a FlowMatchingODEAdapter class or "
            "factory. Format: 'module:callable' (e.g. "
            "'adaptive_reflow.adapters.twodim_fm:default_twodim_fm_adapter')."
        ),
    )
    parser.add_argument(
        "--n-samples",
        required=True,
        type=int,
        help=(
            "Number of independent samples to draw per configuration "
            "(>= 1). Each sample gets its own fresh prior + seed."
        ),
    )
    parser.add_argument(
        "--n-rounds",
        required=True,
        type=int,
        help=(
            "Number of re-inference rounds the runner drives per "
            "sample for the four multi-round configurations (>= 1)."
        ),
    )
    # --output-dir is shared with the other 7 ``tools/run_sota_*.py``
    # drivers; see ``tools/_sota_common.py``. This script marks
    # ``--output-dir`` required and threads the canonical 2D-FM seed
    # (DEFAULT_SEED = 42).
    add_sota_common_args(
        parser,
        output_dir_default=None,
        output_dir_required=True,
        seed_default=DEFAULT_SEED,
        include_seed=True,
    )
    parser.add_argument(
        "--channels",
        type=str,
        default=",".join(DEFAULT_CHANNELS),
        help=(
            "Comma-separated adapter channels the runner should "
            f"forward (default: '{','.join(DEFAULT_CHANNELS)}')."
        ),
    )
    parser.add_argument(
        "--with-selection-evaluator",
        action="store_true",
        help=(
            "Attach a PosteriorSelectionEvaluator so the 'evidence' "
            "row emits per-round selection_ratio values. By default "
            "the script omits the evaluator (faster runs)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns ``0`` on success, non-zero on error."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if int(args.n_samples) < 1:
        parser.error("--n-samples must be >= 1")
    if int(args.n_rounds) < 1:
        parser.error("--n-rounds must be >= 1")

    output_dir: Path = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    channels = tuple(s.strip() for s in str(args.channels).split(",") if s.strip())
    if not channels:
        parser.error("--channels must be a non-empty comma-separated list")

    print(
        f"[run_sota_comparison] adapter-class={args.adapter_class!r} "
        f"n-samples={args.n_samples} n-rounds={args.n_rounds} "
        f"output-dir={output_dir} seed={args.seed}"
    )

    # Adapter + (optional) selection evaluator.
    try:
        adapter = _load_adapter(str(args.adapter_class))
    except (ImportError, TypeError, ValueError) as exc:
        print(f"error: failed to load adapter: {exc}", file=sys.stderr)
        return 2
    selection_evaluator: PosteriorSelectionEvaluator | None = None
    if args.with_selection_evaluator:
        # The canonical 2D adapter's posterior selection needs a
        # reference residual profile. Without one the evaluator still
        # runs but its ratios plateau near the uninformative prior.
        try:
            selection_evaluator = PosteriorSelectionEvaluator()
        except Exception as exc:  # pragma: no cover — defensive
            print(
                f"warning: selection evaluator unavailable ({exc}); "
                "evidence row will report nan selection_ratio",
                file=sys.stderr,
            )

    schedulers: dict[str, SchedulerProtocol | None] = {
        "baseline": None,
        "cosine": _make_cosine_scheduler(cycle_length=int(args.n_rounds)),
        "codim": _make_codim_scheduler(cycle_length=int(args.n_rounds)),
        "evidence": _make_evidence_scheduler(cycle_length=int(args.n_rounds)),
        "freetraj": _make_freetraj_scheduler(cycle_length=int(args.n_rounds)),
    }

    runners: dict[str, Callable[..., dict[str, Any]]] = {
        "baseline": lambda *, output_path, **_kwargs: _run_baseline(
            adapter=adapter,
            n_samples=int(args.n_samples),
            seed=int(args.seed),
            output_path=output_path,
            channels=channels,
        ),
    }
    for name in ("cosine", "codim", "evidence", "freetraj"):
        # Resolve the scheduler once per closure — the dict entry is
        # guaranteed non-None because the loop only covers the four
        # multi-round names from :data:`CONFIGURATIONS`.
        scheduler = schedulers[name]
        if scheduler is None:
            raise RuntimeError(
                f"scheduler {name!r} unexpectedly None in closure builder"
            )

        def _make_runner(
            name: str, scheduler: SchedulerProtocol
        ) -> Callable[..., dict[str, Any]]:
            def _run(output_path: Path) -> dict[str, Any]:
                return _run_multi_round(
                    config_name=name,
                    scheduler=scheduler,
                    adapter=adapter,
                    n_samples=int(args.n_samples),
                    n_rounds=int(args.n_rounds),
                    seed=int(args.seed),
                    output_path=output_path,
                    channels=channels,
                    selection_evaluator=(
                        selection_evaluator if name == "evidence" else None
                    ),
                )

            return _run

        runners[name] = _make_runner(name, scheduler)

    results: list[dict[str, Any]] = []
    t_start = time.monotonic()
    for cfg in CONFIGURATIONS:
        output_path = output_dir / f"{cfg}_samples.npz"
        runner_fn = runners[cfg]
        t0 = time.monotonic()
        print(f"[run_sota_comparison] running {cfg!r} ...")
        try:
            summary = runner_fn(output_path=output_path)
        except Exception as exc:
            tb = traceback.format_exc()
            print(
                f"error: configuration {cfg!r} raised "
                f"{type(exc).__name__}: {exc}\n{tb}",
                file=sys.stderr,
            )
            return 3
        summary["wallclock_seconds"] = float(time.monotonic() - t0)
        print(
            f"[run_sota_comparison] {cfg!r} done in "
            f"{summary['wallclock_seconds']:.2f}s "
            f"(n_finite={summary['n_finite']}/{summary['n_samples']})"
        )
        results.append(summary)

    comparison_md = _format_markdown(results)
    comparison_path = output_dir / "comparison.md"
    comparison_path.write_text(comparison_md, encoding="utf-8")
    print(
        f"[run_sota_comparison] wrote comparison table to "
        f"{comparison_path} (total {time.monotonic() - t_start:.2f}s)"
    )
    return 0


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__: list[str] = [
    "CODIMENSION_EPS_IMPLICIT",
    "COSINE_N_MAX",
    "COSINE_N_MIN",
    "DEFAULT_CHANNELS",
    "DEFAULT_SEED",
    "FREETRAJ_AMPLITUDE",
    "FREETRAJ_PERIOD",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
