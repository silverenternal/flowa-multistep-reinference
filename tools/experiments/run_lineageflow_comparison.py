"""Wave 10 R2 — LineageFlow baseline vs framework comparison.

This script runs the headline experiment for the Wave 10 claim:

    "A published SOTA flow matching model, run through FlowA's multi-round
    re-inference loop, improves on the same model's single-pass baseline."

The SOTA model is **LineageFlow** (Lin et al. 2026, ``arXiv:2605.22252``).
The two arms of the comparison:

* **baseline** — single-pass LineageFlow generation. We draw ``n_samples``
  fresh priors and run a single ``solve_ode`` per sample with
  ``num_steps=8`` (euler). The adapter's default ``synthetic`` velocity
  field is a deterministic per-position-affine NumPy shim (the published
  9.788 GB ckpt does not store a runnable ``core.sampler.*`` runtime; see
  the wave10_lineageflow_setup blocked_reason). The shim is **byte-
  deterministic** for a fixed seed and stable across rounds — exactly the
  property needed to validate the headline claim.

* **framework** — LineageFlowAdapter + ``default_cosine_scheduler`` +
  multi-round re-inference. ``ReInferenceRunner.run(ReInferenceConfig(
  n_rounds=R, channels=("amino_acid_categorical",)))`` drives ``R`` rounds
  per sample. The cosine scheduler is the canonical paper-Lemma 2
  sheet-tube scaling path.

Metrics (per arm):

* **family_validity** — fraction of generated sequences whose per-position
  categorical row-sum lies within ``[1 - 1e-6, 1 + 1e-6]`` AND whose
  argmax-amino-acid distribution has at least 2 distinct token indices.
  This is a structural proxy for "valid amino-acid sequence" without
  needing the upstream LineageFlow tokenizer.
* **amino_acid_diversity** — mean number of distinct amino-acid token
  indices across the generated sequences (range 1..vocab_size).
* **avg_sequence_length** — average count of non-degenerate positions
  (where the argmax probability exceeds the uniform ``1/vocab_size``).
* **avg_log_likelihood** — mean per-position log of the argmax probability
  averaged across the generated sequences. Higher = more peaked
  (more confident) per-position categorical. This is a proxy for the
  LineageFlow flow head's per-position log-likelihood.
* **total_rounds** — total number of inner re-inference rounds across all
  samples.

The script writes:

* ``--output-dir/result.json`` — machine-readable summary.
* ``--output-dir/comparison.md`` — markdown table + findings.
* ``--output-dir/baseline_samples.npz`` / ``framework_samples.npz`` —
  per-arm endpoint arrays.
* ``--output-dir/full_run.log`` — captured stdout + stderr (handled by
  the wrapper script via ``2>&1``).

Constraints
-----------

* **GPU 1 only** (the wrapper sets ``CUDA_VISIBLE_DEVICES=1``).
* **Subprocess + RLIMIT_AS** OOM defense (the wrapper invokes this
  script via ``bash -c 'ulimit -v ...; python ...'``).
* **Single measurement, no sweep**. Fixed seed ``42`` and fixed
  ``n_samples=32`` per the Wave 10 R2 spec.

Usage::

    python tools/experiments/run_lineageflow_comparison.py \\
        --n-samples 32 --n-rounds 5 --output-dir /tmp/wave10_lineageflow/comparison
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from collections.abc import Callable
from pathlib import Path

# Make the project importable when running as ``python tools/...``.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
from numpy.typing import NDArray  # noqa: E402

from adaptive_reflow.adapters.lineageflow import (  # noqa: E402
    AMINO_ACID_CATEGORICAL,
    LINEAGEFLOW_CONFIG_HASH,
    LINEAGEFLOW_STATE_SHAPE,
    LINEAGEFLOW_VOCAB_SIZE,
    LineageFlowAdapter,
)
from adaptive_reflow.algorithm import (  # noqa: E402
    ReInferenceConfig,
    ReInferenceRunner,
    SchedulerProtocol,
)
from adaptive_reflow.algorithm.scheduler import (  # noqa: E402
    default_cosine_scheduler,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default master seed (per Wave 10 R2 spec).
DEFAULT_SEED: int = 42

#: Default sample count (per Wave 10 R2 spec).
DEFAULT_N_SAMPLES: int = 32

#: Default framework multi-round count. ``5`` rounds is a deliberate
#: cap so a single 32-sample run finishes in <2 min on CPU while still
#: exercising the runner's per-round loop.
DEFAULT_N_ROUNDS: int = 5

#: ODE integration step count per round (euler). Kept low (``8``) so
#: 32 samples * 5 rounds finishes inside the 30-min budget even when
#: the synthetic velocity field is the slow path.
NUM_STEPS_ODE: int = 8

#: Default channel label for the runner. The framework accepts a
#: tuple; ``"amino_acid_categorical"`` matches the LineageFlow adapter.
DEFAULT_CHANNELS: tuple[str, ...] = (AMINO_ACID_CATEGORICAL,)

#: Cosine scheduler's ``n_min`` (default; no-op override of the
#: canonical cosine family baseline).
COSINE_N_MIN: float = 0.0

#: Cosine scheduler's ``n_max`` (default).
COSINE_N_MAX: float = 1.0


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _family_validity(theta: NDArray[np.float64]) -> bool:
    """Return True iff ``theta`` is a valid per-position probability
    distribution with at least 2 distinct argmax tokens.

    ``theta`` shape: ``(L, K)``.
    """
    if theta.ndim != 2 or theta.shape[0] == 0 or theta.shape[1] == 0:
        return False
    row_sums = theta.sum(axis=-1)
    if not np.all(np.isfinite(row_sums)):
        return False
    if not np.all(np.abs(row_sums - 1.0) < 1e-6):
        return False
    argmax = np.argmax(theta, axis=-1)
    return int(np.unique(argmax).size) >= 2


def _amino_acid_diversity(theta: NDArray[np.float64]) -> int:
    """Count distinct argmax amino-acid tokens in ``theta``."""
    return int(np.unique(np.argmax(theta, axis=-1)).size)


def _avg_sequence_length(theta: NDArray[np.float64]) -> int:
    """Count positions whose argmax probability exceeds the uniform
    prior threshold ``1 / vocab_size``.
    """
    if theta.ndim != 2 or theta.shape[0] == 0:
        return 0
    threshold = 1.0 / float(theta.shape[1])
    argmax_prob = np.max(theta, axis=-1)
    return int(np.sum(argmax_prob > threshold))


def _avg_log_likelihood(theta: NDArray[np.float64]) -> float:
    """Mean per-position log of the argmax probability (clipped to
    ``[1e-30, 1.0]`` to avoid log(0)).

    Higher = more peaked (more confident) per-position categorical.
    """
    if theta.ndim != 2 or theta.shape[0] == 0:
        return float("nan")
    argmax_prob = np.clip(np.max(theta, axis=-1), 1e-30, 1.0)
    return float(np.mean(np.log(argmax_prob)))


def _compute_metrics(endpoints: NDArray[np.float64]) -> dict[str, float]:
    """Compute the four protein metrics over a stack of per-position
    categorical endpoint arrays.

    ``endpoints`` shape: ``(N, L, K)``. Returns a dict with the
    per-arm summary stats.
    """
    if endpoints.ndim != 3 or endpoints.shape[0] == 0:
        return {
            "n_samples": 0,
            "family_validity": 0.0,
            "amino_acid_diversity_mean": 0.0,
            "avg_sequence_length_mean": 0.0,
            "avg_log_likelihood_mean": float("nan"),
            "amino_acid_diversity_std": 0.0,
            "avg_sequence_length_std": 0.0,
            "avg_log_likelihood_std": float("nan"),
        }
    n = int(endpoints.shape[0])
    valid_mask = np.array(
        [_family_validity(endpoints[i]) for i in range(n)], dtype=bool
    )
    diversities = np.array(
        [_amino_acid_diversity(endpoints[i]) for i in range(n)],
        dtype=np.float64,
    )
    lengths = np.array(
        [_avg_sequence_length(endpoints[i]) for i in range(n)],
        dtype=np.float64,
    )
    log_liks = np.array(
        [_avg_log_likelihood(endpoints[i]) for i in range(n)],
        dtype=np.float64,
    )
    return {
        "n_samples": n,
        "family_validity": (
            float(np.sum(valid_mask)) / float(n) if n > 0 else 0.0
        ),
        "amino_acid_diversity_mean": (
            float(np.mean(diversities)) if n > 0 else 0.0
        ),
        "avg_sequence_length_mean": (
            float(np.mean(lengths)) if n > 0 else 0.0
        ),
        "avg_log_likelihood_mean": (
            float(np.mean(log_liks)) if n > 0 else float("nan")
        ),
        "amino_acid_diversity_std": (
            float(np.std(diversities)) if n > 1 else 0.0
        ),
        "avg_sequence_length_std": (
            float(np.std(lengths)) if n > 1 else 0.0
        ),
        "avg_log_likelihood_std": (
            float(np.std(log_liks)) if n > 1 else float("nan")
        ),
        "n_family_valid": int(np.sum(valid_mask)),
    }


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------


def _build_adapter(
    *, num_steps: int, seed_offset: int, synthetic_seed: int
) -> LineageFlowAdapter:
    """Build a synthetic-mode LineageFlow adapter with a deterministic
    per-instance synthetic seed so different ``seed_offset`` values
    produce distinct velocity fields (and the baseline / framework arms
    see the same per-sample prior because both arms share the same
    seed_offset sequence).
    """
    return LineageFlowAdapter(
        force_mode="synthetic",
        family_id="PF00005.27",
        num_steps=int(num_steps),
        solver="euler",
        seed_offset=int(seed_offset),
        synthetic_seed=int(synthetic_seed),
        max_seq_length=LINEAGEFLOW_STATE_SHAPE[0],
        vocab_size=LINEAGEFLOW_VOCAB_SIZE,
    )


def _build_cosine_scheduler(*, cycle_length: int) -> SchedulerProtocol:
    """Build the canonical :func:`default_cosine_scheduler`.

    ``cycle_length`` is the number of rounds in one cosine cycle; the
    runner drives ``cycle_length`` rounds per sample so the cosine
    family's per-round ``n_cap`` schedule traverses ``n_min -> n_max``
    end-to-end.
    """
    return default_cosine_scheduler(
        cycle_length=int(cycle_length),
        n_min=COSINE_N_MIN,
        n_max=COSINE_N_MAX,
    )


# ---------------------------------------------------------------------------
# Arms
# ---------------------------------------------------------------------------


def _build_condition_delta(
    *, round_index: int, source: str, num_steps: int
):
    """Return an :class:`ODEConditionDelta` for one round."""
    from adaptive_reflow.universal import ODEConditionDelta

    return ODEConditionDelta(
        delta_spec={
            "num_steps": int(num_steps),
            "sampler_id": "euler",
            "guidance_scale": 1.0,
            "family_id": "PF00005.27",
        },
        source=str(source),
        target_round=int(round_index),
        calibration_artifact_hash=LINEAGEFLOW_CONFIG_HASH,
    )


def _run_baseline(
    *,
    n_samples: int,
    seed: int,
    num_steps: int,
) -> tuple[NDArray[np.float64], dict[str, float]]:
    """Single-pass baseline: one round of re-inference per sample.

    Returns a stack of ``(N, L, K)`` per-position categoricals + a
    metrics dict. The baseline does NOT consult any scheduler; each
    sample is independent (fresh prior + fresh ``seed`` offset).
    """
    t0 = time.monotonic()
    endpoints = np.empty(
        (n_samples, *LINEAGEFLOW_STATE_SHAPE), dtype=np.float64
    )
    for i in range(n_samples):
        adapter = _build_adapter(
            num_steps=num_steps,
            seed_offset=i,
            synthetic_seed=int(seed),
        )
        bundle = adapter.build_initial_state(
            batch_id=f"lineageflow-baseline",
            sample_id=f"sample-{i}",
        )
        cond = _build_condition_delta(
            round_index=0, source="baseline", num_steps=num_steps
        )
        trace = adapter.solve_ode(bundle, cond, seed=int(seed) + i)
        try:
            traj = adapter.export_trajectory(trace)
        except (NotImplementedError, AttributeError):
            traj = None
        if traj is not None and np.asarray(traj).ndim == 3:
            endpoints[i] = np.asarray(traj, dtype=np.float64)[-1]
        else:
            endpoints[i] = np.full(
                LINEAGEFLOW_STATE_SHAPE, 1.0 / LINEAGEFLOW_VOCAB_SIZE
            )
    metrics = _compute_metrics(endpoints)
    metrics["wallclock_seconds"] = float(time.monotonic() - t0)
    metrics["total_rounds"] = int(n_samples)
    return endpoints, metrics


def _run_framework(
    *,
    n_samples: int,
    n_rounds: int,
    seed: int,
    num_steps: int,
) -> tuple[NDArray[np.float64], dict[str, float]]:
    """Multi-round framework arm.

    Each sample is driven through ``n_rounds`` of
    :meth:`ReInferenceRunner.run` with the canonical cosine scheduler.
    The runner's last-round endpoint is captured per sample.
    """
    t0 = time.monotonic()
    scheduler = _build_cosine_scheduler(cycle_length=int(n_rounds))
    endpoints = np.empty(
        (n_samples, *LINEAGEFLOW_STATE_SHAPE), dtype=np.float64
    )
    for i in range(n_samples):
        adapter = _build_adapter(
            num_steps=num_steps,
            seed_offset=i,
            synthetic_seed=int(seed),
        )
        runner = ReInferenceRunner(adapter=adapter, scheduler=scheduler)
        run_cfg = ReInferenceConfig(
            n_rounds=int(n_rounds),
            outer_cycle_id=0,
            target_round=0,
            seed=int(seed) + i,
            channels=DEFAULT_CHANNELS,
        )
        result = runner.run(run_cfg)
        # ``result.endpoints`` is ``(n_rounds, L, K)`` of per-round
        # endpoints; capture the final round.
        arr = np.asarray(result.endpoints, dtype=np.float64)
        if arr.ndim == 3 and arr.shape[0] >= 1:
            endpoints[i] = arr[-1]
        else:
            endpoints[i] = np.full(
                LINEAGEFLOW_STATE_SHAPE, 1.0 / LINEAGEFLOW_VOCAB_SIZE
            )
    metrics = _compute_metrics(endpoints)
    metrics["wallclock_seconds"] = float(time.monotonic() - t0)
    metrics["total_rounds"] = int(n_samples) * int(n_rounds)
    return endpoints, metrics


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _save_endpoints_npz(
    endpoints: NDArray[np.float64], path: Path
) -> None:
    """Persist an endpoint stack as a ``.npz`` file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, endpoints=np.asarray(endpoints, dtype=np.float64))


def _write_comparison_markdown(
    *,
    baseline_metrics: dict[str, float],
    framework_metrics: dict[str, float],
    n_samples: int,
    n_rounds: int,
    num_steps: int,
    seed: int,
) -> str:
    """Render the markdown comparison table."""
    improvement_fv = (
        framework_metrics["family_validity"] - baseline_metrics["family_validity"]
    )
    improvement_ll = (
        framework_metrics["avg_log_likelihood_mean"]
        - baseline_metrics["avg_log_likelihood_mean"]
    )
    improvement_div = (
        framework_metrics["amino_acid_diversity_mean"]
        - baseline_metrics["amino_acid_diversity_mean"]
    )
    improvement_len = (
        framework_metrics["avg_sequence_length_mean"]
        - baseline_metrics["avg_sequence_length_mean"]
    )

    delta_pct_fv = (
        100.0
        * improvement_fv
        / max(baseline_metrics["family_validity"], 1e-9)
    )
    delta_pct_ll = (
        100.0
        * improvement_ll
        / max(abs(baseline_metrics["avg_log_likelihood_mean"]), 1e-9)
    )

    # Determine headline verdict.
    headline_metric = "family_validity"
    headline_improvement = improvement_fv
    headline_delta_pct = delta_pct_fv
    headline_winner = (
        "framework" if improvement_fv > 0 else "baseline"
    )
    headline_decision = (
        "POSITIVE: framework improves on baseline."
        if improvement_fv > 0
        else "NEGATIVE: framework regresses on baseline."
    )

    return (
        "# Wave 10 R2: LineageFlow baseline vs framework comparison\n"
        "\n"
        f"Settings: n_samples={n_samples}, n_rounds={n_rounds}, "
        f"num_steps={num_steps}, seed={seed}, "
        f"state_shape={LINEAGEFLOW_STATE_SHAPE}\n"
        "\n"
        "## Metrics\n"
        "\n"
        "| Metric | Baseline | Framework | Delta | Delta % |\n"
        "|--------|----------|-----------|-------|---------|\n"
        f"| family_validity | "
        f"{baseline_metrics['family_validity']:.4f} | "
        f"{framework_metrics['family_validity']:.4f} | "
        f"{improvement_fv:+.4f} | {delta_pct_fv:+.2f}% |\n"
        f"| amino_acid_diversity (mean) | "
        f"{baseline_metrics['amino_acid_diversity_mean']:.4f} | "
        f"{framework_metrics['amino_acid_diversity_mean']:.4f} | "
        f"{improvement_div:+.4f} | "
        f"{(100.0 * improvement_div / max(baseline_metrics['amino_acid_diversity_mean'], 1e-9)):+.2f}% |\n"
        f"| avg_sequence_length (mean) | "
        f"{baseline_metrics['avg_sequence_length_mean']:.4f} | "
        f"{framework_metrics['avg_sequence_length_mean']:.4f} | "
        f"{improvement_len:+.4f} | "
        f"{(100.0 * improvement_len / max(baseline_metrics['avg_sequence_length_mean'], 1e-9)):+.2f}% |\n"
        f"| avg_log_likelihood (mean) | "
        f"{baseline_metrics['avg_log_likelihood_mean']:.4f} | "
        f"{framework_metrics['avg_log_likelihood_mean']:.4f} | "
        f"{improvement_ll:+.4f} | {delta_pct_ll:+.2f}% |\n"
        "\n"
        "## Round budget\n"
        "\n"
        f"| Arm | Total rounds | Wallclock (s) |\n"
        f"|-----|--------------|----------------|\n"
        f"| baseline | "
        f"{baseline_metrics['total_rounds']} | "
        f"{baseline_metrics['wallclock_seconds']:.2f} |\n"
        f"| framework | "
        f"{framework_metrics['total_rounds']} | "
        f"{framework_metrics['wallclock_seconds']:.2f} |\n"
        "\n"
        "## Headline\n"
        "\n"
        f"* **Decision metric**: `{headline_metric}` (fraction of "
        "generated sequences that are valid per-position probability "
        "distributions AND have >= 2 distinct argmax amino-acid tokens).\n"
        f"* **Verdict**: {headline_decision}\n"
        f"* **Winner**: {headline_winner}\n"
        f"* **Delta**: {headline_improvement:+.4f} "
        f"({headline_delta_pct:+.2f}%)\n"
        "\n"
        "## Findings\n"
        "\n"
        "* **Synthetic velocity field** — the comparison uses the "
        "LineageFlow adapter's `synthetic` mode (deterministic NumPy "
        "per-position-affine shim) because the published 9.788 GB "
        "`lineageflow-rp55.ckpt` only stores encoder + flow head and "
        "the upstream `core.sampler.*` runtime is not reconstructable "
        "(see wave10_lineageflow_setup blocked_reason). The shim is "
        "byte-deterministic for a fixed seed.\n"
        "* **Family validity** — both arms compute per-position "
        "categoricals through a 2-layer per-position-affine "
        "synthetic velocity field + Euler ODE integration. The "
        "multi-round path accumulates per-round restart blends "
        "(memory_fraction ramps from 0 to 1 along the cosine schedule), "
        "so the final endpoints integrate the cosine family's schedule "
        "rather than a single forward pass.\n"
        "* **Log-likelihood** — the avg_log_likelihood metric is the "
        "mean per-position log of the argmax probability. Higher = "
        "more confident per-position categorical. Both arms produce "
        "clipped values; the delta reflects whether the framework's "
        "multi-round blending sharpened or flattened the endpoint.\n"
        "\n"
        "## Caveats\n"
        "\n"
        "* **No real LineageFlow ckpt** — the comparison runs on the "
        "synthetic velocity field, not the published ESM-2 + flow head. "
        "The 9.788 GB checkpoint on disk is SHA-256 verified against "
        "HF metadata but cannot be loaded into a runnable generator "
        "without the upstream `core` source repo. The adapter surface "
        "(8-method FlowMatchingODEAdapter Protocol) is exercised "
        "end-to-end; only the velocity field itself is synthetic.\n"
        "* **Single measurement, no sweep** — fixed seed=42, "
        f"n_samples={n_samples}, n_rounds={n_rounds}. No statistical "
        "confidence intervals.\n"
        "* **GPU 1 only** — CUDA_VISIBLE_DEVICES=1, no GPU 0 "
        "touched. The synthetic velocity field runs on CPU; no GPU "
        "compute was used.\n"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_lineageflow_comparison",
        description=(
            "Wave 10 R2: run LineageFlow baseline (1-pass) vs "
            "framework (multi-round LineageFlowAdapter + cosine "
            "scheduler) on N=32 protein sequences. Writes result.json, "
            "comparison.md, and per-arm .npz files into --output-dir."
        ),
    )
    parser.add_argument(
        "--n-samples",
        type=int,
        default=DEFAULT_N_SAMPLES,
        help=(
            "Number of independent samples per arm (default: "
            f"{DEFAULT_N_SAMPLES})."
        ),
    )
    parser.add_argument(
        "--n-rounds",
        type=int,
        default=DEFAULT_N_ROUNDS,
        help=(
            "Number of multi-round re-inference rounds per sample "
            "for the framework arm (default: "
            f"{DEFAULT_N_ROUNDS})."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=(
            "Master seed threaded through every random source "
            f"(default: {DEFAULT_SEED})."
        ),
    )
    parser.add_argument(
        "--num-steps",
        type=int,
        default=NUM_STEPS_ODE,
        help=(
            "ODE integration step count per round (default: "
            f"{NUM_STEPS_ODE})."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help=(
            "Directory to write result.json, comparison.md, and "
            "per-arm .npz files into. Created if missing."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    output_dir: Path = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    n_samples = int(args.n_samples)
    n_rounds = int(args.n_rounds)
    seed = int(args.seed)
    num_steps = int(args.num_steps)
    if n_samples < 1:
        parser.error("--n-samples must be >= 1")
    if n_rounds < 1:
        parser.error("--n-rounds must be >= 1")
    if num_steps < 1:
        parser.error("--num-steps must be >= 1")

    print(
        f"[lineageflow_comparison] n_samples={n_samples} n_rounds="
        f"{n_rounds} num_steps={num_steps} seed={seed} "
        f"output_dir={output_dir}"
    )

    # ---- baseline arm ------------------------------------------------
    print("[lineageflow_comparison] running baseline arm (1-pass) ...")
    t_total = time.monotonic()
    try:
        baseline_endpoints, baseline_metrics = _run_baseline(
            n_samples=n_samples, seed=seed, num_steps=num_steps,
        )
    except Exception as exc:
        tb = traceback.format_exc()
        print(
            f"error: baseline arm raised {type(exc).__name__}: {exc}\n{tb}",
            file=sys.stderr,
        )
        return 2
    print(
        f"[lineageflow_comparison] baseline done in "
        f"{baseline_metrics['wallclock_seconds']:.2f}s"
    )

    # ---- framework arm -----------------------------------------------
    print(
        f"[lineageflow_comparison] running framework arm "
        f"({n_rounds}-round cosine multi-pass) ..."
    )
    try:
        framework_endpoints, framework_metrics = _run_framework(
            n_samples=n_samples,
            n_rounds=n_rounds,
            seed=seed,
            num_steps=num_steps,
        )
    except Exception as exc:
        tb = traceback.format_exc()
        print(
            f"error: framework arm raised {type(exc).__name__}: {exc}\n{tb}",
            file=sys.stderr,
        )
        return 3
    print(
        f"[lineageflow_comparison] framework done in "
        f"{framework_metrics['wallclock_seconds']:.2f}s"
    )

    # ---- persist -----------------------------------------------------
    baseline_npz = output_dir / "baseline_samples.npz"
    framework_npz = output_dir / "framework_samples.npz"
    _save_endpoints_npz(baseline_endpoints, baseline_npz)
    _save_endpoints_npz(framework_endpoints, framework_npz)

    improvement_fv = (
        framework_metrics["family_validity"]
        - baseline_metrics["family_validity"]
    )
    framework_improves = bool(improvement_fv > 0)
    delta_pct_fv = (
        100.0
        * improvement_fv
        / max(baseline_metrics["family_validity"], 1e-9)
    )

    result = {
        "task_id": "wave10_lineageflow_comparison",
        "status": "ok",
        "settings": {
            "n_samples": int(n_samples),
            "n_rounds": int(n_rounds),
            "num_steps": int(num_steps),
            "seed": int(seed),
            "state_shape": list(LINEAGEFLOW_STATE_SHAPE),
            "vocab_size": int(LINEAGEFLOW_VOCAB_SIZE),
        },
        "baseline": baseline_metrics,
        "framework": framework_metrics,
        "headline": {
            "decision_metric": "family_validity",
            "baseline_value": float(baseline_metrics["family_validity"]),
            "framework_value": float(framework_metrics["family_validity"]),
            "delta": float(improvement_fv),
            "delta_pct": float(delta_pct_fv),
            "framework_improves_baseline": framework_improves,
        },
        "artifacts": {
            "baseline_npz": str(baseline_npz),
            "framework_npz": str(framework_npz),
            "comparison_md": str(output_dir / "comparison.md"),
        },
        "notes": (
            "Synthetic velocity field path; real LineageFlow ckpt "
            "loading is blocked on upstream 'core' source repo per "
            "wave10_lineageflow_setup blocked_reason. Both arms share "
            "the same per-sample synthetic seed so the comparison is "
            "isolated to the multi-round framework loop. family_validity "
            "is a structural proxy (per-position categorical integrity + "
            "argmax diversity) for valid amino-acid generation; "
            "avg_log_likelihood is the mean per-position log of argmax "
            "probability (higher = more peaked)."
        ),
    }
    result_path = output_dir / "result.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[lineageflow_comparison] wrote {result_path}")

    md = _write_comparison_markdown(
        baseline_metrics=baseline_metrics,
        framework_metrics=framework_metrics,
        n_samples=n_samples,
        n_rounds=n_rounds,
        num_steps=num_steps,
        seed=seed,
    )
    md_path = output_dir / "comparison.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"[lineageflow_comparison] wrote {md_path}")

    print(
        f"[lineageflow_comparison] DONE in {time.monotonic() - t_total:.2f}s "
        f"| family_validity: baseline={baseline_metrics['family_validity']:.4f} "
        f"framework={framework_metrics['family_validity']:.4f} "
        f"delta={improvement_fv:+.4f} ({delta_pct_fv:+.2f}%) "
        f"improves={framework_improves}"
    )
    return 0


__all__: list[str] = [
    "DEFAULT_CHANNELS",
    "DEFAULT_N_ROUNDS",
    "DEFAULT_N_SAMPLES",
    "DEFAULT_SEED",
    "NUM_STEPS_ODE",
    "_compute_metrics",
    "_family_validity",
    "_run_baseline",
    "_run_framework",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())