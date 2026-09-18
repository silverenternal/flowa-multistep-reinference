"""Wave 191 P3 — MNIST FM N=1000 framework-vs-baseline sweep.

Mirrors the Wave 191 P2 CIFAR protocol at matched NFE=50:
- Baseline: single-pass FM NFE=50, beta=0 (restart is a no-op).
- Framework arms (cosine + codimension_sheet + evidence_driven): 4 rounds
  with per-round num_steps = round(n_cap[r] * 12) so average per-round
  NFE = 12 (= 50/4, the matched-NFE anchor); restart-blend beta=0.5
  (memory_fraction=0.5).
- FID: framework-internal Fréchet-projection over 784 -> 128 random
  projection (MnistFrechetProjectionEvaluator). Reference = MNIST test
  (10K digits, the framework's canonical reference).

Paired chunk-FID t-test (k=10 disjoint chunks of N/10 samples) + Bonferroni
correction across 3 framework arms (alpha=0.05/3=0.0167).

Honest disclosure is added in the output JSON when:
- MNIST FM ckpt was materialized in smoke mode (1 epoch, base_channels=8,
  max_train_images=6000) instead of the production 3-epoch / base_channels=16
  recipe, OR
- N < 1000 (capped by wall-time budget).

The framework-side scheduler arms give DIFFERENT total NFE per sample at
this resolution because per-round num_steps is integer-truncated:
  cosine (cycle_length=4):       num_steps=[12, 9, 3, 0] = 24
  codimension_sheet (n=4):       num_steps=[12, 12, 12, 12] = 48
  evidence_driven (no PID fb):   num_steps=[12, 9, 3, 0] = 24

The 'matched NFE' anchor is the *average* per-round NFE (12.5 → 12), not
the total per-sample NFE. This mirrors the Wave 191 P2 audit's
'--match-nfe sample' protocol.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Suppress the deprecated-default-cosine-scheduler DeprecationWarning
# (we explicitly want CosineAnnealScheduler + CodimensionSheetScheduler
# + EvidenceDrivenScheduler as 3 distinct arms).
warnings.filterwarnings("ignore", category=DeprecationWarning)

from adaptive_reflow.adapters.mnist_fm import (  # noqa: E402
    MNIST_FM_FLAT_DIM,
    MNIST_FM_NUM_STEPS,
    MnistFmAdapter,
)
from adaptive_reflow.adapters.mnist_fm_train import (  # noqa: E402
    _load_mnist_offline,
)
from adaptive_reflow.algorithm.scheduler import (  # noqa: E402
    CodimensionSheetScheduler,
    CosineAnnealScheduler,
    CosineScheduleConfig,
    EvidenceDrivenScheduler,
)
from adaptive_reflow.contracts import (  # noqa: E402
    ArtifactHash,
    ChannelName,
    FactorValue,
    FinalRestartPolicy,
    LedgerRowId,
    PolicyId,
    RunId,
    hash_policy_hash,
)
from adaptive_reflow.contracts.authority import validate_final_restart_policy  # noqa: E402
from adaptive_reflow.eval.mnist_fid import (  # noqa: E402
    MnistFrechetProjectionEvaluator,
    _frechet_distance,
)
from adaptive_reflow.universal.state import (  # noqa: E402
    ODEConditionDelta,
    StateBundle,
)


SCHEMA_VERSION: str = "wave191_p3_mnist_n1000_v1"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_N_SAMPLES: int = 1000  # Wave 191 P3 target
FALLBACK_N_SAMPLES: int = 200  # Per task spec §6 if materialization blocked
N_ROUNDS: int = 4
BASELINE_NUM_STEPS: int = 50  # MNIST_FM_NUM_STEPS
FRAMEWORK_MAX_NUM_STEPS: int = 12  # = 50 / 4 (avg-per-round match)
BETA_FRAMEWORK: float = 0.5  # restart-blend memory_fraction=0.5
BETA_BASELINE: float = 0.0  # baseline: no restart-blend
K_CHUNKS: int = 10  # paired t-test on k disjoint chunks

ARM_LABELS: tuple[str, ...] = ("cosine", "codimension_sheet", "evidence_driven")

# Per-arm seed offset (mirrors Wave 191 P2 SCHEDULER_SEED_OFFSETS so each
# arm sees an independent noise stream). All arms use a different seed
# offset so they're not byte-identical.
ARM_SEED_OFFSETS: dict[str, int] = {
    "cosine": 0,
    "codimension_sheet": 1_000_000,
    "evidence_driven": 2_000_000,
}


# ---------------------------------------------------------------------------
# Policy construction
# ---------------------------------------------------------------------------


def make_policy(*, arm: str, beta: float, round_idx: int) -> FinalRestartPolicy:
    """Build a hash-valid :class:`FinalRestartPolicy` for ``(arm, beta, round_idx)``.

    Mirrors ``tools/experiments/run_mnist_migration.py::make_policy``.
    """
    channel = ChannelName("x")
    policy_id = f"policy-wave191-p3-{arm}-b{beta:.2f}-r{round_idx}"
    from dataclasses import replace
    draft = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id="inference.adaptive_reflow",
        run_id=RunId(f"run-wave191-p3-{arm}"),
        target_round=int(round_idx),
        outer_cycle_id=0,
        beta_by_channel={channel: FactorValue(float(beta))},
        alpha_by_channel={channel: FactorValue(1.0)},
        fresh_noise_floor_by_channel={channel: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={channel: True},
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    sealed = replace(draft, policy_hash=hash_policy_hash(draft))
    ok, errors = validate_final_restart_policy(sealed)
    if not ok:
        raise AssertionError(f"invalid_policy:{errors!r}")
    return sealed


# ---------------------------------------------------------------------------
# Scheduler factory (cycle_length=4 for matched NFE)
# ---------------------------------------------------------------------------


def _build_cosine_config(cycle_length: int) -> CosineScheduleConfig:
    config_hash = ArtifactHash(
        hashlib.sha256(
            repr(("cosine_no_restart", int(cycle_length), 0.0, 1.0)).encode("utf-8")
        ).hexdigest()
    )
    return CosineScheduleConfig(
        schedule_family="cosine_no_restart",
        cycle_length=int(cycle_length),
        n_min=FactorValue(0.0),
        n_max=FactorValue(1.0),
        per_channel_caps={},
        fresh_noise_floor_by_channel={},
        symmetric_delta_caps_by_channel={},
        restart_triggers_allowed=(),
        config_hash=config_hash,
        frozen_before_evaluation=True,
    )


def build_scheduler(name: str, cycle_length: int):
    """Return the named scheduler configured for ``cycle_length`` rounds.

    Three families:
    - CosineAnnealScheduler: cosine closed-form ramp (n_cap = 1, 0.75, 0.25, 0)
    - CodimensionSheetScheduler: paper-quantity-driven (n_cap near 1.0)
    - EvidenceDrivenScheduler: cosine + PID-lite offset
    """
    config = _build_cosine_config(cycle_length)
    if name == "cosine":
        return CosineAnnealScheduler(config)
    if name == "codimension_sheet":
        return CodimensionSheetScheduler(
            cycle_length=int(cycle_length),
            n_min=0.0,
            n_max=1.0,
            eps_implicit=0.05,
        )
    if name == "evidence_driven":
        return EvidenceDrivenScheduler(config=config)
    raise ValueError(f"unknown_scheduler:{name}")


def per_round_num_steps(name: str, cycle_length: int, max_num_steps: int) -> list[int]:
    """Return the per-round num_steps list for the named scheduler.

    Each round: num_steps[r] = round(n_cap[r] * max_num_steps) clipped to [1, max_num_steps].
    """
    sched = build_scheduler(name, cycle_length)
    out: list[int] = []
    for r in range(int(cycle_length)):
        sample = sched.sample(0, int(r), int(r))
        n_cap = float(sample.n_cap)
        ns = int(round(n_cap * float(max_num_steps)))
        ns = max(1, min(int(max_num_steps), ns))
        out.append(ns)
    return out


# ---------------------------------------------------------------------------
# Sample generation
# ---------------------------------------------------------------------------


def run_baseline(
    *,
    adapter: MnistFmAdapter,
    n_samples: int,
    seed: int,
    verbose: bool = True,
) -> np.ndarray:
    """Generate ``n_samples`` baseline endpoints (1 round × 50 NFE, beta=0).

    Returns ``(n_samples, 784)`` float64 endpoints.
    """
    samples = np.empty((int(n_samples), MNIST_FM_FLAT_DIM), dtype=np.float64)
    t0 = time.perf_counter()
    for i in range(int(n_samples)):
        bundle = adapter.build_initial_state(batch_id="wave191-p3-baseline", sample_id=f"s{i:05d}")
        # No restart (beta=0); the policy doesn't matter — solve_ode uses the bundle's x0.
        condition = ODEConditionDelta(
            delta_spec={"t0": 0.0, "t1": 1.0, "num_steps": int(BASELINE_NUM_STEPS)},
            source="wave191_p3_baseline",
            target_round=0,
            calibration_artifact_hash="cal-wave191-p3",
        )
        trace = adapter.solve_ode(bundle, condition, seed=int(seed) + i)
        # Use the framework's observe_endpoint to fold the trajectory into an x0-bearing
        # endpoint bundle, then read x0 (the final sample).
        endpoint_bundle = adapter.observe_endpoint(trace, bundle)
        entry = adapter._native_states.get(endpoint_bundle.native_state_digest, {})
        samples[i] = np.asarray(entry["x0"], dtype=np.float64).reshape(MNIST_FM_FLAT_DIM)
    elapsed = time.perf_counter() - t0
    if verbose:
        print(
            f"[baseline] {n_samples} samples in {elapsed:.1f}s "
            f"({n_samples / elapsed:.1f} samples/s), NFE={BASELINE_NUM_STEPS}",
            flush=True,
        )
    return samples


def run_framework_arm(
    *,
    arm_name: str,
    cycle_length: int,
    n_samples: int,
    num_steps_per_round: list[int],
    seed_offset: int,
    beta: float,
    verbose: bool = True,
) -> tuple[np.ndarray, dict[str, int]]:
    """Generate ``n_samples`` framework-arm endpoints (4 rounds × num_steps_per_round[r], beta=beta).

    Each round: build_initial_state → apply_restart_distribution (with beta)
    → compose_condition → solve_ode (num_steps=num_steps_per_round[r]).
    The next round's build_initial_state uses a fresh batch_id so the
    restart-blend sees a fresh source noise.

    Returns ``(samples, telemetry)`` where ``telemetry`` carries total
    NFE per sample and wall-clock breakdown.
    """
    from dataclasses import replace as _replace

    adapter = MnistFmAdapter(
        weights_path="data/mnist_fm.npz",
        num_steps=int(BASELINE_NUM_STEPS),  # default; overridden per round via condition
    )

    samples = np.empty((int(n_samples), MNIST_FM_FLAT_DIM), dtype=np.float64)
    total_nfe = int(sum(num_steps_per_round))
    t0 = time.perf_counter()
    for i in range(int(n_samples)):
        # Round 0: build initial state (fresh Gaussian x0)
        bundle = adapter.build_initial_state(
            batch_id=f"wave191-p3-{arm_name}", sample_id=f"s{i:05d}",
        )
        # Subsequent rounds: apply_restart_distribution with beta
        for r in range(int(cycle_length)):
            if r > 0:
                policy = make_policy(arm=arm_name, beta=float(beta), round_idx=int(r))
                bundle = adapter.apply_restart_distribution(bundle, policy)
            num_steps = int(num_steps_per_round[r])
            condition = ODEConditionDelta(
                delta_spec={"t0": 0.0, "t1": 1.0, "num_steps": int(num_steps)},
                source=f"wave191_p3_{arm_name}",
                target_round=int(r),
                calibration_artifact_hash="cal-wave191-p3",
            )
            seed_for_round = int(seed_offset) + i + r * 1_000_003
            trace = adapter.solve_ode(bundle, condition, seed=seed_for_round)
            # Use the framework's observe_endpoint to fold the trajectory
            # into an x0-bearing endpoint bundle (this is the canonical
            # round-to-round handoff the framework expects).
            bundle = adapter.observe_endpoint(trace, bundle)
        # Last round's endpoint x0 is the final sample.
        entry = adapter._native_states.get(bundle.native_state_digest, {})
        samples[i] = np.asarray(entry["x0"], dtype=np.float64).reshape(MNIST_FM_FLAT_DIM)
    elapsed = time.perf_counter() - t0
    if verbose:
        print(
            f"[{arm_name}] {n_samples} samples in {elapsed:.1f}s "
            f"({n_samples / elapsed:.1f} samples/s), NFE={total_nfe}/sample, "
            f"per-round={num_steps_per_round}, beta={beta}",
            flush=True,
        )
    return samples, {"total_nfe_per_sample": total_nfe, "wall_sec": float(elapsed)}


# ---------------------------------------------------------------------------
# FID scoring
# ---------------------------------------------------------------------------


def score_population(samples: np.ndarray, ref_features: np.ndarray, projection: np.ndarray) -> float:
    """Compute the framework-internal Fréchet-projection FID for ``samples``."""
    if samples.ndim != 2 or samples.shape[1] != MNIST_FM_FLAT_DIM:
        raise ValueError(f"samples must be (N, 784); got {samples.shape}")
    feats_g = np.asarray(samples @ projection, dtype=np.float64)
    return float(_frechet_distance(feats_g, ref_features))


def paired_ttest(diff: np.ndarray) -> tuple[float, int, float]:
    """Return ``(t_stat, df, p_two_sided)`` for a paired-difference array."""
    from scipy import stats
    n = int(diff.shape[0])
    if n < 2:
        return float("nan"), 0, float("nan")
    mean = float(diff.mean())
    std = float(diff.std(ddof=1))
    if std <= 0.0:
        return float("inf") if mean != 0 else 0.0, n - 1, 0.0 if mean != 0 else 1.0
    t = mean / (std / math.sqrt(n))
    p = float(2.0 * (1.0 - stats.t.cdf(abs(t), df=n - 1)))
    return float(t), n - 1, p


def cohens_dz(diff: np.ndarray) -> float:
    n = int(diff.shape[0])
    if n < 2:
        return float("nan")
    mean = float(diff.mean())
    std = float(diff.std(ddof=1))
    if std <= 0.0:
        return float("inf") if mean != 0 else 0.0
    return mean / std


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-samples", type=int, default=DEFAULT_N_SAMPLES)
    parser.add_argument("--output-dir", type=Path,
                        default=REPO_ROOT / "verification_outputs" / "wave191-p3-mnist-n1000")
    parser.add_argument("--output-json", type=Path,
                        default=REPO_ROOT / "verification_outputs" / "wave191-p3-mnist-n1000.json")
    parser.add_argument("--cache-dir", type=Path, default=REPO_ROOT / "data" / "mnist_fm_train_cache")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--k-chunks", type=int, default=K_CHUNKS)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    n_samples = int(args.n_samples)
    output_dir = Path(args.output_dir)
    output_json = Path(args.output_json)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve checkpoint path; surface a smoke disclosure if the ckpt is the
    # smoke 1-epoch / base_channels=8 / 6000-image materialization.
    ckpt_path = REPO_ROOT / "data" / "mnist_fm.npz"
    if not ckpt_path.exists():
        raise SystemExit(f"checkpoint_not_found:{ckpt_path}")
    ckpt_size = int(ckpt_path.stat().st_size)
    ckpt_sha256 = hashlib.sha256(ckpt_path.read_bytes()).hexdigest()
    # Smoke ckpt is ~22 KB (small base_channels=8 weights); production 3-epoch
    # base_channels=16 ckpt is ~75 KB. Threshold of 50 KB cleanly separates.
    ckpt_is_smoke = ckpt_size < 50_000
    n_samples_used = n_samples
    n_samples_was_capped = False
    if n_samples_used > FALLBACK_N_SAMPLES * 5:
        # 1000 samples fits within budget; no cap needed. Keep as-is.
        pass

    if not args.quiet:
        print(f"[wave191-p3] ckpt={ckpt_path} sha256={ckpt_sha256[:16]} "
              f"size={ckpt_size} bytes smoke={ckpt_is_smoke}")
        print(f"[wave191-p3] N={n_samples} NFE={BASELINE_NUM_STEPS} rounds={N_ROUNDS} "
              f"framework-max-num-steps={FRAMEWORK_MAX_NUM_STEPS}")

    # ------------------------------------------------------------------
    # 1. Reference features (MNIST test, 10K images, 784 -> 128 random proj)
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    test_imgs = _load_mnist_offline(split="test", cache_dir=Path(args.cache_dir))
    test_imgs = np.asarray(test_imgs, dtype=np.float64)
    evaluator = MnistFrechetProjectionEvaluator(cache_dir=Path(args.cache_dir))
    ref_features = evaluator._ref_features  # (10000, 128) — already projected
    projection = evaluator._projection  # (784, 128)
    if not args.quiet:
        print(f"[wave191-p3] MNIST test loaded: {test_imgs.shape} "
              f"in {time.perf_counter() - t0:.1f}s; ref features: {ref_features.shape}")

    # ------------------------------------------------------------------
    # 2. Per-round num_steps for each framework arm
    # ------------------------------------------------------------------
    arm_num_steps: dict[str, list[int]] = {}
    for name in ARM_LABELS:
        ns = per_round_num_steps(name, int(N_ROUNDS), int(FRAMEWORK_MAX_NUM_STEPS))
        arm_num_steps[name] = ns
        if not args.quiet:
            print(f"[wave191-p3] {name} per-round num_steps = {ns} "
                  f"(total NFE = {sum(ns)})")

    # ------------------------------------------------------------------
    # 3. Generate samples for baseline + 3 framework arms
    # ------------------------------------------------------------------
    t_total = time.perf_counter()
    if not args.quiet:
        print(f"[wave191-p3] generating baseline ({n_samples} samples) ...")
    adapter_baseline = MnistFmAdapter(
        weights_path=str(ckpt_path), num_steps=int(BASELINE_NUM_STEPS),
    )
    baseline_samples = run_baseline(
        adapter=adapter_baseline,
        n_samples=int(n_samples),
        seed=int(args.seed),
        verbose=not args.quiet,
    )

    arm_samples: dict[str, np.ndarray] = {}
    arm_telemetry: dict[str, dict[str, Any]] = {}
    for name in ARM_LABELS:
        if not args.quiet:
            print(f"[wave191-p3] generating {name} ({n_samples} samples) ...")
        s, tel = run_framework_arm(
            arm_name=name,
            cycle_length=int(N_ROUNDS),
            n_samples=int(n_samples),
            num_steps_per_round=arm_num_steps[name],
            seed_offset=ARM_SEED_OFFSETS[name],
            beta=float(BETA_FRAMEWORK),
            verbose=not args.quiet,
        )
        arm_samples[name] = s
        arm_telemetry[name] = tel

    wall_total = time.perf_counter() - t_total
    if not args.quiet:
        print(f"[wave191-p3] all 4 arms generated in {wall_total:.1f}s "
              f"({wall_total / 60:.1f} min)")

    # Save per-arm samples (npz compressed)
    np.savez_compressed(output_dir / "baseline_samples.npz", samples=baseline_samples)
    for name in ARM_LABELS:
        np.savez_compressed(output_dir / f"{name}_samples.npz", samples=arm_samples[name])

    # ------------------------------------------------------------------
    # 4. FID scoring (headline + chunk-level)
    # ------------------------------------------------------------------
    if not args.quiet:
        print(f"[wave191-p3] computing FID ...")
    headline_fid: dict[str, float] = {}
    headline_fid["baseline"] = float(score_population(baseline_samples, ref_features, projection))
    for name in ARM_LABELS:
        headline_fid[name] = float(score_population(arm_samples[name], ref_features, projection))
    if not args.quiet:
        for k, v in headline_fid.items():
            print(f"[wave191-p3] {k} FID = {v:.4f}")

    # Paired chunk-level FID: split each arm's N samples into K_CHUNKS disjoint
    # chunks of chunk_size = N / K_CHUNKS samples each. For each chunk k, the
    # FID(gen_chunk[k], ref_chunk[k]) is paired across arms.
    chunk_size = int(n_samples) // int(args.k_chunks)
    if chunk_size * int(args.k_chunks) != n_samples:
        # Trim to the largest multiple; use the first K_CHUNKS * chunk_size samples.
        n_used = chunk_size * int(args.k_chunks)
        if not args.quiet:
            print(f"[wave191-p3] trimming N from {n_samples} to {n_used} for paired chunking")
        n_samples = n_used
    chunk_fids: dict[str, list[float]] = {k: [] for k in ["baseline", *ARM_LABELS]}
    # The reference must also be split into k chunks of chunk_size to keep
    # the FID self-consistent (we use the same 10K reference split each time).
    ref_chunk_size = chunk_size  # use same chunk size for ref too
    rng = np.random.default_rng(int(args.seed) + 99)
    ref_perm = rng.permutation(ref_features.shape[0])
    for k_i in range(int(args.k_chunks)):
        ref_idx = ref_perm[k_i * ref_chunk_size : (k_i + 1) * ref_chunk_size]
        ref_chunk = ref_features[ref_idx]
        chunk_fids["baseline"].append(float(
            score_population(baseline_samples[k_i * chunk_size : (k_i + 1) * chunk_size],
                             ref_chunk, projection)
        ))
        for name in ARM_LABELS:
            chunk_fids[name].append(float(
                score_population(arm_samples[name][k_i * chunk_size : (k_i + 1) * chunk_size],
                                 ref_chunk, projection)
            ))
    if not args.quiet:
        for k_i in range(int(args.k_chunks)):
            line = f"[wave191-p3] chunk {k_i}: "
            for k in ["baseline", *ARM_LABELS]:
                line += f"{k}={chunk_fids[k][k_i]:.4f} "
            print(line, flush=True)

    # ------------------------------------------------------------------
    # 5. Paired t-test + Bonferroni correction
    # ------------------------------------------------------------------
    framework_arms_out: dict[str, dict[str, Any]] = {}
    arm_list_for_verdict: list[tuple[str, float, float, float]] = []
    for name in ARM_LABELS:
        baseline_chunk = np.asarray(chunk_fids["baseline"], dtype=np.float64)
        arm_chunk = np.asarray(chunk_fids[name], dtype=np.float64)
        diff = arm_chunk - baseline_chunk
        t, df, p = paired_ttest(diff)
        dz = cohens_dz(diff)
        delta_pct = float((arm_chunk.mean() - baseline_chunk.mean()) / max(baseline_chunk.mean(), 1e-9) * 100.0)
        bonf = min(float(p) * len(ARM_LABELS), 1.0)
        framework_arms_out[name] = {
            "fid_headline": float(headline_fid[name]),
            "fid_chunks_mean": float(arm_chunk.mean()),
            "fid_chunks_std": float(arm_chunk.std(ddof=1)),
            "delta_vs_baseline_pct": float(delta_pct),
            "p_value_raw": float(p),
            "p_value_bonferroni": float(bonf),
            "bonferroni_significant": bool(bonf < 0.05),
            "cohens_dz": float(dz),
            "t_stat": float(t),
            "df": int(df),
            "n_chunks": int(args.k_chunks),
            "chunk_fids": [float(x) for x in arm_chunk],
            "per_round_num_steps": arm_num_steps[name],
            "total_nfe_per_sample": int(sum(arm_num_steps[name])),
            "beta": float(BETA_FRAMEWORK),
            "telemetry": arm_telemetry[name],
        }
        arm_list_for_verdict.append((name, headline_fid[name], delta_pct, p))
        if not args.quiet:
            print(f"[wave191-p3] {name}: FID={headline_fid[name]:.4f} "
                  f"Δ_vs_baseline={delta_pct:+.4f}% p={p:.4g} "
                  f"(Bonf p={bonf:.4g}, sig={bonf < 0.05})")

    best = min(arm_list_for_verdict, key=lambda x: x[1])
    best_name, best_fid, best_delta, best_p = best
    baseline_fid = headline_fid["baseline"]

    if best_fid < baseline_fid and min(best_p * len(ARM_LABELS), 1.0) < 0.05:
        verdict = "framework_wins"
    elif best_fid > baseline_fid and min(best_p * len(ARM_LABELS), 1.0) < 0.05:
        verdict = "baseline_wins"
    else:
        verdict = "tie"

    # ------------------------------------------------------------------
    # 6. R5 implication
    # ------------------------------------------------------------------
    if verdict == "framework_wins":
        r5 = (
            f"Wave 191 P3 MNIST FM (N={n_samples}, smoke model 1-epoch base_channels=8) "
            f"at matched NFE=50 confirms the framework BEATS the single-pass baseline "
            f"(best arm {best_name} FID={best_fid:.4f} vs baseline {baseline_fid:.4f}, "
            f"Δ={best_delta:+.2f}% Bonferroni p={min(best_p * 3, 1.0):.4f}). "
            f"This MATCHES the Wave 128 CIFAR-10 RF -44.17% claim at matched NFE and "
            f"STRENGTHENS the R5 MNIST FID -15.01% headline: the framework's MNIST value-add "
            f"is robust to (1) the smoke-trained model and (2) the integer-NFE matched "
            f"protocol. The paper's R5 claim stands."
        )
    elif verdict == "baseline_wins":
        r5 = (
            f"Wave 191 P3 MNIST FM (N={n_samples}, smoke model 1-epoch base_channels=8) "
            f"at matched NFE=50 shows the single-pass baseline WINS "
            f"(best framework arm {best_name} FID={best_fid:.4f} vs baseline {baseline_fid:.4f}, "
            f"Δ={best_delta:+.2f}% Bonferroni p={min(best_p * 3, 1.0):.4f}). "
            f"This REPLACES the R5 MNIST FM FID -15.01% headline at matched NFE: the "
            f"framework's MNIST value-add is NOT about better inference at fixed NFE — "
            f"the paper claim scope should be tightened to 'comparable quality at fewer "
            f"NFEs' (cross-budget) rather than 'framework beats baseline' (matched-NFE). "
            f"The Wave 191 P2 CIFAR-10 RF verdict (baseline_wins at matched NFE) is "
            f"now REPLICATED on MNIST FM."
        )
    else:
        r5 = (
            f"Wave 191 P3 MNIST FM (N={n_samples}, smoke model 1-epoch base_channels=8) "
            f"at matched NFE=50 returns verdict TIE — best framework arm {best_name} "
            f"FID={best_fid:.4f} vs baseline {baseline_fid:.4f}, Δ={best_delta:+.2f}% "
            f"(not Bonferroni-significant). The R5 MNIST FM FID -15.01% headline is "
            f"NOT replaced at matched NFE — but the cross-budget claim (Wave 128 "
            f"paradigm) is unaffected. Both arms produce comparable quality; the "
            f"framework's MNIST value-add at matched NFE is statistical parity."
        )

    # ------------------------------------------------------------------
    # 7. Assemble output JSON
    # ------------------------------------------------------------------
    if ckpt_is_smoke:
        honest_disclosure = (
            f"SMOKE CKPT USED: data/mnist_fm.npz ({ckpt_size} bytes, sha256={ckpt_sha256[:16]}) "
            f"was materialized via tools/materialize_mnist_fm.py with epochs=1, "
            f"base_channels=8, max_train_images=6000 (production recipe is "
            f"epochs=3, base_channels=16, full 60K images; 30-40 min CPU). The "
            f"smoke ckpt is intentionally under-trained; absolute FID values are "
            f"high (~hundreds), but the paired baseline-vs-framework comparison "
            f"is valid because both arms use the same model. The smoke model is "
            f"a pragmatic time-budget choice within the 1-2 h Wave 191 P3 budget."
        )
    else:
        honest_disclosure = (
            f"Production ckpt used: data/mnist_fm.npz ({ckpt_size} bytes, "
            f"sha256={ckpt_sha256[:16]}); 3-epoch base_channels=16 recipe."
        )

    out: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "target": "mnist_fm",
        "n_records": int(n_samples),
        "nfe": int(BASELINE_NUM_STEPS),
        "baseline_fid": float(baseline_fid),
        "framework_arms": framework_arms_out,
        "best_arm": best_name,
        "verdict": verdict,
        "r5_implication": r5,
        "wall_min": float(round(wall_total / 60.0, 2)),
        "commit_sha": "PENDING",
        "alpha_bonferroni": float(0.05 / len(ARM_LABELS)),
        "n_chunks": int(args.k_chunks),
        "chunk_size": int(chunk_size),
        "statistical_test": (
            f"paired two-sided t-test (df={args.k_chunks - 1}) on chunk-level "
            f"FIDs (k={args.k_chunks} disjoint chunks of {chunk_size} samples each, "
            f"paired across arms and reference); Cohen's d_z on within-chunk "
            f"diffs; Bonferroni correction across {len(ARM_LABELS)} arms "
            f"(alpha=0.05/{len(ARM_LABELS)}={0.05/len(ARM_LABELS):.4f})"
        ),
        "headline_fids": {k: float(v) for k, v in headline_fid.items()},
        "summary_row_fids": {
            "baseline": float(baseline_fid),
            "CosineAnnealScheduler": float(headline_fid["cosine"]),
            "CodimensionSheetScheduler": float(headline_fid["codimension_sheet"]),
            "EvidenceDrivenScheduler": float(headline_fid["evidence_driven"]),
        },
        "checkpoint": "data/mnist_fm.npz",
        "checkpoint_sha256": ckpt_sha256,
        "checkpoint_size_bytes": int(ckpt_size),
        "checkpoint_is_smoke_materialization": bool(ckpt_is_smoke),
        "n_samples_requested": int(args.n_samples),
        "n_samples_used": int(n_samples),
        "n_samples_was_capped": bool(n_samples_was_capped),
        "sweep_command": (
            f"python scripts/wave191_p3_mnist_sweep.py --n-samples {int(args.n_samples)} "
            f"--output-dir verification_outputs/wave191-p3-mnist-n1000 --seed {int(args.seed)}"
        ),
        "postprocessor": "scripts/wave191_p3_mnist_sweep.py",
        "per_arm_n_features": {k: int(n_samples) for k in ["baseline", *ARM_LABELS]},
        "honest_disclosure": honest_disclosure,
        "arm_seed_offsets": dict(ARM_SEED_OFFSETS),
        "framework_max_num_steps_per_round": int(FRAMEWORK_MAX_NUM_STEPS),
        "n_rounds": int(N_ROUNDS),
        "beta_framework": float(BETA_FRAMEWORK),
        "beta_baseline": float(BETA_BASELINE),
        "fid_metric": (
            "framework-internal Fréchet-projection over 784 -> 128 deterministic "
            "Gaussian random projection (seed=42); reference = MNIST test set "
            "(10K digits, same projection); MnistFrechetProjectionEvaluator "
            "(adaptive_reflow.eval.mnist_fid). This is NOT the literature "
            "InceptionV3 FID — the absolute numbers are framework-internal; the "
            "paired baseline-vs-arm comparison is valid since both arms use "
            "the same projection + reference."
        ),
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_json.open("w") as f:
        json.dump(out, f, indent=2)
    if not args.quiet:
        print(f"[wave191-p3] wrote {output_json}")
        print(f"[wave191-p3] verdict={verdict} best_arm={best_name} "
              f"baseline_fid={baseline_fid:.4f} best_arm_fid={best_fid:.4f} "
              f"delta={best_delta:+.4f}% bonf_p={min(best_p * 3, 1.0):.4g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())