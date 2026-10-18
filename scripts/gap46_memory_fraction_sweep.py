#!/usr/bin/env python3
"""GAP-46 — sweep the restart memory fraction ``m`` under a tuned baseline.

`docs/audit/gap26-r5b-regime.md` §6 records the concrete next step: the
memory fraction is scheduler-derived (``1 - n_cap``) and is therefore not
a free lever, so the only configuration the GAP-24 boundary law predicts
could survive a tuned baseline was never tested. This driver:

1. runs the canonical R5b runner with an explicit ``--memory-fraction``
   (default: the scheduler-derived value, which is the byte-stable path);
2. evaluates every arm with the same headline FID as GAP-12
   (``data/cifar10_inception_features.npz`` + ``wave247`` helpers), so the
   numbers are directly comparable to the recorded 0/4 tuned-baseline
   result;
3. aggregates the per-seed paired statistics.

Protocol (default): baseline NFE = 200 (the GAP-12 tuned baseline),
framework NFE = 50 (the canonical matched budget), ``n_rounds = 3``
(the regime where ``m`` governs endpoint restarts rather than only the
round-0 initial condition), N = 200, seeds {42, 43, 44}, four schedulers.

Usage::

    CUDA_VISIBLE_DEVICES=0 .venvs/lineageflow_venv/bin/python \\
        scripts/gap46_memory_fraction_sweep.py --include-default

HARD CONSTRAINT: one GPU only (``cuda:0``).
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy import stats as _scipy_stats

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

OUT_ROOT = REPO_ROOT / "verification_outputs" / "gap46-r5b-memory"
PYTHON_BIN = REPO_ROOT / ".venvs" / "lineageflow_venv" / "bin" / "python"
RUNNER = REPO_ROOT / "tools" / "run_sota_cifar_experiment.py"
CHECKPOINT = REPO_ROOT / "data" / "rectified_flow_cifar10.pth"
REF_NPZ = REPO_ROOT / "data" / "cifar10_test_ref.npz"
REF_FEATS_NPZ = REPO_ROOT / "data" / "cifar10_inception_features.npz"

SCHEDULER_FILE_NAMES = {
    "CosineAnnealScheduler": "cosineanneal_samples.npz",
    "CodimensionSheetScheduler": "codimensionsheet_samples.npz",
    "EvidenceDrivenScheduler": "evidencedriven_samples.npz",
    "FreeTrajScheduler": "freetraj_samples.npz",
}


def _load_w247():
    path = REPO_ROOT / "scripts" / "wave247_p2_r5b_multiseed.py"
    spec = importlib.util.spec_from_file_location("_w247_gap46", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _tag(seed: int, memory_fraction: float | None) -> str:
    m = "default" if memory_fraction is None else f"m{memory_fraction:g}"
    return f"seed{seed}-{m}"


def _run_one(
    *,
    seed: int,
    memory_fraction: float | None,
    baseline_nfe: int,
    framework_nfe: int,
    n_rounds: int,
    n_samples: int,
    match_nfe: str,
    log_path: Path,
) -> dict:
    tag = _tag(seed, memory_fraction)
    out_dir = OUT_ROOT / tag
    cmd = [
        str(PYTHON_BIN),
        "tools/run_sota_cifar_experiment.py",
        "--checkpoint",
        str(CHECKPOINT),
        "--device",
        "cuda",
        "--n-samples",
        str(n_samples),
        "--framework-samples",
        str(n_samples),
        "--n-rounds",
        str(n_rounds),
        "--baseline-num-steps",
        str(baseline_nfe),
        "--framework-max-num-steps",
        str(framework_nfe),
        "--integrator",
        "euler",
        "--match-nfe",
        match_nfe,
        "--ref-npz",
        str(REF_NPZ),
        "--output-dir",
        str(out_dir),
    ]
    if memory_fraction is not None:
        cmd.extend(["--memory-fraction", f"{float(memory_fraction):g}"])

    env = os.environ.copy()
    env["WAVE247_SEED"] = str(seed)
    env["CUDA_VISIBLE_DEVICES"] = "0"
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    print(f"[gap46] {tag}: launching", flush=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with log_path.open("w") as log_f:
        proc = subprocess.run(
            cmd, cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=14400
        )
        log_f.write("STDOUT:\n")
        log_f.write(proc.stdout)
        log_f.write("\n\nSTDERR:\n")
        log_f.write(proc.stderr)
    wall = float(time.perf_counter() - started)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{tag} failed rc={proc.returncode}: {proc.stderr[-2000:]}"
        )
    print(f"[gap46] {tag}: done in {wall:.1f}s", flush=True)
    return {"tag": tag, "out_dir": str(out_dir.relative_to(REPO_ROOT)), "wall_seconds": wall}


def _evaluate_run(w247, run_dir: Path, ref_feats: np.ndarray) -> dict:
    """Headline FID + paired stats, identical to ``gap12_tuned_baseline``."""
    cache_dir = run_dir / "inception_feats_cache"
    arm_feats: dict[str, np.ndarray] = {}
    feats = w247._load_or_compute_features(cache_dir, "baseline", run_dir / "baseline_samples.npz")
    if feats is not None:
        arm_feats["baseline"] = feats
    for sch, fname in SCHEDULER_FILE_NAMES.items():
        f = w247._load_or_compute_features(cache_dir, sch, run_dir / fname)
        if f is not None:
            arm_feats[sch] = f

    headline_fids = {a: float(w247._fid_numpy(f, ref_feats)) for a, f in arm_feats.items()}
    baseline_fid = headline_fids.get("baseline", float("nan"))
    arms: dict[str, dict] = {}
    for arm_name, f in arm_feats.items():
        if arm_name == "baseline":
            continue
        bf = arm_feats["baseline"]
        diff_sq = ((bf - f) ** 2).sum(axis=1)
        n = int(diff_sq.shape[0])
        mean_d = float(diff_sq.mean())
        sd_d = float(diff_sq.std(ddof=1))
        dz = mean_d / sd_d if sd_d > 0 else float("nan")
        t = mean_d / (sd_d / np.sqrt(n)) if sd_d > 0 else float("nan")
        p = float(2 * _scipy_stats.t.sf(abs(t), df=n - 1)) if not math.isnan(t) else float("nan")
        delta_pct = float((headline_fids[arm_name] - baseline_fid) / baseline_fid * 100.0)
        arms[arm_name] = {
            "fid_headline": headline_fids[arm_name],
            "delta_vs_baseline_pct": delta_pct,
            "cohens_dz": dz,
            "t_stat": t,
            "p_value_raw": p,
            "n_paired": n,
        }
    return {"baseline_fid": baseline_fid, "framework_arms": arms}


def _aggregate(per_seed: dict[str, dict[str, dict]]) -> dict:
    """Seed-level aggregation of ``delta_vs_baseline_pct`` per (m, arm)."""
    out: dict[str, dict] = {}
    for m_key, arms in per_seed.items():
        out[m_key] = {}
        for arm, seed_rows in arms.items():
            deltas = [r["delta_vs_baseline_pct"] for r in seed_rows.values()]
            pvals = [r["p_value_raw"] for r in seed_rows.values()]
            n = len(deltas)
            mean = float(np.mean(deltas))
            sd = float(np.std(deltas, ddof=1)) if n > 1 else float("nan")
            se = sd / math.sqrt(n) if n > 1 else float("nan")
            t = mean / se if se and se > 0 else float("nan")
            p = float(2 * _scipy_stats.t.sf(abs(t), df=n - 1)) if not math.isnan(t) else float("nan")
            out[m_key][arm] = {
                "n_seeds": n,
                "seed_deltas_pct": deltas,
                "mean_delta_pct": mean,
                "sd_delta_pct": sd,
                "t_stat": t,
                "p_value": p,
                "n_seeds_negative": int(sum(d < 0 for d in deltas)),
                "per_seed_p_value": pvals,
                "all_seeds_significant_raw": bool(all(pp < 0.05 for pp in pvals)),
            }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--memory-fractions", default="0.25,0.5,0.75")
    ap.add_argument("--seeds", default="42,43,44")
    ap.add_argument("--baseline-nfe", type=int, default=200)
    ap.add_argument("--framework-nfe", type=int, default=50)
    ap.add_argument("--n-rounds", type=int, default=3)
    ap.add_argument("--n-samples", type=int, default=200)
    ap.add_argument("--match-nfe", choices=("budget", "sample"), default="budget")
    ap.add_argument("--include-default", action="store_true", default=False,
                    help="Also run the scheduler-derived arm (no --memory-fraction).")
    ap.add_argument("--skip-runs", action="store_true")
    args = ap.parse_args()

    m_values: list[float | None] = [
        float(x) for x in str(args.memory_fractions).split(",") if x.strip()
    ]
    if args.include_default:
        m_values = [None, *m_values]
    seeds = [int(x) for x in str(args.seeds).split(",") if x.strip()]

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    log_dir = OUT_ROOT / "_logs"
    w247 = _load_w247()
    ref_feats = np.load(REF_FEATS_NPZ, allow_pickle=False)["features"].astype(np.float64)

    print(
        f"[gap46] seeds={seeds} m={m_values} baseline_nfe={args.baseline_nfe} "
        f"framework_nfe={args.framework_nfe} n_rounds={args.n_rounds} "
        f"N={args.n_samples}",
        flush=True,
    )

    runs: list[dict] = []
    per_seed: dict[str, dict[str, dict]] = {}
    baseline_by_seed: dict[int, float] = {}
    for seed in seeds:
        for m in m_values:
            tag = _tag(seed, m)
            run_dir = OUT_ROOT / tag
            if not args.skip_runs:
                runs.append(
                    _run_one(
                        seed=seed,
                        memory_fraction=m,
                        baseline_nfe=args.baseline_nfe,
                        framework_nfe=args.framework_nfe,
                        n_rounds=args.n_rounds,
                        n_samples=args.n_samples,
                        match_nfe=str(args.match_nfe),
                        log_path=log_dir / f"{tag}.log",
                    )
                )
            ev = _evaluate_run(w247, run_dir, ref_feats)
            baseline_by_seed[seed] = ev["baseline_fid"]
            m_key = "default" if m is None else f"{m:g}"
            per_seed.setdefault(m_key, {})
            for arm, row in ev["framework_arms"].items():
                per_seed[m_key].setdefault(arm, {})[str(seed)] = row
            print(
                f"  [{tag}] baseline FID={ev['baseline_fid']:.4f} "
                + " ".join(
                    f"{a}={r['delta_vs_baseline_pct']:+.2f}%"
                    for a, r in ev["framework_arms"].items()
                ),
                flush=True,
            )

    agg = _aggregate(per_seed)
    alpha_arm = 0.05 / len(SCHEDULER_FILE_NAMES)
    survivors = [
        {"m": m_key, "arm": arm, **row}
        for m_key, arms in agg.items()
        for arm, row in arms.items()
        if row["mean_delta_pct"] < 0 and row["p_value"] < alpha_arm
    ]

    summary = {
        "kind": "gap46_r5b_memory_fraction",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "cell": "R5b (CIFAR-10 RF)",
        "protocol": {
            "baseline_nfe": int(args.baseline_nfe),
            "framework_nfe": int(args.framework_nfe),
            "n_rounds": int(args.n_rounds),
            "n_samples": int(args.n_samples),
            "seeds": seeds,
            "memory_fractions": ["default" if m is None else m for m in m_values],
            "match_nfe": str(args.match_nfe),
            "device": "cuda:0",
        },
        "baseline_fid_by_seed": {str(k): v for k, v in baseline_by_seed.items()},
        "per_seed": per_seed,
        "aggregate": agg,
        "alpha_per_arm": alpha_arm,
        "survivors": survivors,
        "runs": runs,
    }
    out_json = OUT_ROOT / "gap46-memory-fraction.json"
    out_json.write_text(json.dumps(summary, indent=2, default=str) + "\n")

    out_csv = OUT_ROOT / "gap46-memory-fraction.csv"
    with out_csv.open("w", newline="") as f_:
        w = csv.writer(f_)
        w.writerow(
            ["m", "arm", "mean_delta_pct", "sd_delta_pct", "t_stat", "p_value",
             "n_seeds", "n_seeds_negative", "seed_deltas_pct"]
        )
        for m_key, arms in agg.items():
            for arm, row in arms.items():
                w.writerow(
                    [m_key, arm, row["mean_delta_pct"], row["sd_delta_pct"],
                     row["t_stat"], row["p_value"], row["n_seeds"],
                     row["n_seeds_negative"], "|".join(f"{d:.4f}" for d in row["seed_deltas_pct"])]
                )

    print("\n" + "=" * 78)
    print("HEADLINE — GAP-46 memory-fraction sweep (R5b, tuned baseline)")
    print("=" * 78)
    for m_key, arms in agg.items():
        print(f"  m={m_key}")
        for arm, row in arms.items():
            print(
                f"    {arm:28s} mean dFID={row['mean_delta_pct']:+7.3f}% "
                f"sd={row['sd_delta_pct']:.3f} t={row['t_stat']:+.2f} "
                f"p={row['p_value']:.3g} neg={row['n_seeds_negative']}/{row['n_seeds']}"
            )
    print(f"  survivors (mean delta<0, p<{alpha_arm:.4f}): {len(survivors)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
