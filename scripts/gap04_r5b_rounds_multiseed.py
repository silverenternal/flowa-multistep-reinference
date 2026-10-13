#!/usr/bin/env python3
"""GAP-04-R5B-ROUNDS — matched multi-seed CIFAR-10 RF round-count test.

`todo.json` GAP-04-R5B-ROUNDS asks for a **matched-protocol multi-seed
round-count test** (``n_rounds in {1,2,3} x 4 schedulers x 3 seeds at matched
NFE``). The existing evidence is:

* ``n_rounds = 1`` multi-seed (Wave 247 P2, seeds 42/43/44) -> framework-WINS;
* ``n_rounds >= 2`` **single-seed** (Wave 225 P7, N=200) -> framework-REGRESSES.

This driver closes the missing cell: it runs ``n_rounds in {1,2,3}`` across
seeds ``{42,43,44}`` at matched NFE (baseline ``--baseline-num-steps 50`` ==
framework ``--framework-max-num-steps 50``, ``--match-nfe budget``), evaluates
the headline FID per arm, and reports the per-``n_rounds`` x per-scheduler
multi-seed verdict + pooled ``d_z``.

The runner reads its seed from the ``WAVE247_SEED`` env var (committed at
``tools/run_sota_cifar_experiment.py:1423,1448``), so no in-place patching is
required (unlike the historical Wave 247 P2 driver).

Usage::

    CUDA_VISIBLE_DEVICES=0 python scripts/gap04_r5b_rounds_multiseed.py \\
        --seeds 42,43,44 --n-rounds 1,2,3 --n-samples 200

HARD CONSTRAINT: cuda:0 ONLY (user directive "只能用GPU0").
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

OUT_DIR = REPO_ROOT / "verification_outputs"
PYTHON_BIN = REPO_ROOT / ".venvs" / "lineageflow_venv" / "bin" / "python"
RUNNER = REPO_ROOT / "tools" / "run_sota_cifar_experiment.py"
CHECKPOINT = REPO_ROOT / "data" / "rectified_flow_cifar10.pth"
REF_NPZ = REPO_ROOT / "data" / "cifar10_test_ref.npz"
REF_FEATS_NPZ = REPO_ROOT / "data" / "cifar10_inception_features.npz"

NFE = 50
SCHEDULER_FILE_NAMES = {
    "CosineAnnealScheduler": "cosineanneal_samples.npz",
    "CodimensionSheetScheduler": "codimensionsheet_samples.npz",
    "EvidenceDrivenScheduler": "evidencedriven_samples.npz",
    "FreeTrajScheduler": "freetraj_samples.npz",
}


def _load_w247():
    """Import the Wave 247 P2 FID helpers (reuse, do not duplicate)."""
    path = REPO_ROOT / "scripts" / "wave247_p2_r5b_multiseed.py"
    spec = importlib.util.spec_from_file_location("_w247", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _run_one(n_rounds: int, seed: int, n_samples: int, log_path: Path) -> dict:
    out_dir = f"verification_outputs/gap04-r5b-rounds{n_rounds}-seed{seed}-n{n_samples}"
    cmd = [
        str(PYTHON_BIN), "tools/run_sota_cifar_experiment.py",
        "--checkpoint", str(CHECKPOINT),
        "--device", "cuda",
        "--n-samples", str(n_samples),
        "--framework-samples", str(n_samples),
        "--n-rounds", str(n_rounds),
        "--baseline-num-steps", str(NFE),
        "--framework-max-num-steps", str(NFE),
        "--integrator", "euler",
        "--match-nfe", "budget",
        "--ref-npz", str(REF_NPZ),
        "--output-dir", out_dir,
    ]
    env = os.environ.copy()
    env["WAVE247_SEED"] = str(seed)
    env["CUDA_VISIBLE_DEVICES"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    print(f"\n[gap04] n_rounds={n_rounds} seed={seed}: launching", flush=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with log_path.open("w") as log_f:
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env,
                              capture_output=True, text=True, timeout=14400)
        log_f.write("STDOUT:\n")
        log_f.write(proc.stdout)
        log_f.write("\n\nSTDERR:\n")
        log_f.write(proc.stderr)
    wall = float(time.perf_counter() - started)
    if proc.returncode != 0:
        raise RuntimeError(
            f"n_rounds={n_rounds} seed={seed} failed rc={proc.returncode}: "
            f"{proc.stderr[-2000:]}"
        )
    print(f"[gap04] n_rounds={n_rounds} seed={seed} done in {wall:.1f}s", flush=True)
    return {"wall_seconds": wall, "out_dir": out_dir}


def _evaluate(w247, n_rounds: int, seed: int, n_samples: int, ref_feats) -> dict:
    run_dir = OUT_DIR / f"gap04-r5b-rounds{n_rounds}-seed{seed}-n{n_samples}"
    cache_dir = run_dir / "inception_feats_cache"
    arm_feats = {}
    feats = w247._load_or_compute_features(cache_dir, "baseline", run_dir / "baseline_samples.npz")
    if feats is not None:
        arm_feats["baseline"] = feats
    for sch, fname in SCHEDULER_FILE_NAMES.items():
        f = w247._load_or_compute_features(cache_dir, sch, run_dir / fname)
        if f is not None:
            arm_feats[sch] = f

    headline_fids = {a: w247._fid_numpy(f, ref_feats) for a, f in arm_feats.items()}
    baseline_fid = headline_fids.get("baseline", float("nan"))
    framework_arms_out = {}
    present = [a for a in arm_feats if a != "baseline"]
    for arm_name in present:
        bf = arm_feats["baseline"]
        af = arm_feats[arm_name]
        diff_sq = ((bf - af) ** 2).sum(axis=1)
        n = diff_sq.shape[0]
        mean_d = float(diff_sq.mean())
        sd_d = float(diff_sq.std(ddof=1))
        if sd_d > 0:
            t = mean_d / (sd_d / np.sqrt(n))
            p = float(2 * _scipy_stats.t.sf(abs(t), df=n - 1))
            dz = mean_d / sd_d
        else:
            t, p, dz = float("nan"), float("nan"), float("nan")
        delta_pct = float((headline_fids[arm_name] - baseline_fid) / baseline_fid * 100.0)
        bonf_k = max(1, len(present))
        bonf_p = float(min(p * bonf_k, 1.0)) if not math.isnan(p) else float("nan")
        framework_arms_out[arm_name] = {
            "fid_headline": float(headline_fids[arm_name]),
            "delta_vs_baseline_pct": delta_pct,
            "per_sample_l2_sq_distance_mean": mean_d,
            "per_sample_l2_sq_distance_std": sd_d,
            "p_value_raw": p, "p_value_bonferroni": bonf_p,
            "alpha_bonferroni": 0.05 / bonf_k,
            "bonferroni_significant": bool(bonf_p < 0.05) if not math.isnan(bonf_p) else False,
            "cohens_dz": dz, "t_stat": t, "df": int(n - 1), "n_paired": int(n),
        }
    return {
        "headline_fids": {k: float(v) for k, v in headline_fids.items()},
        "baseline_fid": float(baseline_fid) if not math.isnan(baseline_fid) else None,
        "framework_arms": framework_arms_out,
        "run_dir": str(run_dir.relative_to(REPO_ROOT)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="42,43,44")
    ap.add_argument("--n-rounds", default="1,2,3")
    ap.add_argument("--n-samples", type=int, default=200)
    ap.add_argument("--skip-runs", action="store_true")
    args = ap.parse_args()

    seeds = [int(s) for s in args.seeds.split(",")]
    rounds = [int(r) for r in args.n_rounds.split(",")]
    n = args.n_samples

    w247 = _load_w247()
    ref_feats = np.load(REF_FEATS_NPZ, allow_pickle=False)["features"].astype(np.float64)
    print(f"[gap04] seeds={seeds} n_rounds={rounds} N={n} NFE={NFE} "
          f"ref_feats={ref_feats.shape} CUDA_VISIBLE_DEVICES="
          f"{os.environ.get('CUDA_VISIBLE_DEVICES', 'unset')}", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log_dir = OUT_DIR / "_gap04-logs"
    walls: dict[str, float] = {}
    per_cell: dict[str, dict] = {}

    for n_rounds in rounds:
        for seed in seeds:
            key = f"r{n_rounds}_s{seed}"
            log_path = log_dir / f"gap04-r{n_rounds}-seed{seed}.log"
            if not args.skip_runs:
                walls[key] = _run_one(n_rounds, seed, n, log_path)["wall_seconds"]
            per_cell[key] = _evaluate(w247, n_rounds, seed, n, ref_feats)
            for arm, d in per_cell[key]["framework_arms"].items():
                print(f"  [n_rounds={n_rounds} seed={seed} {arm}] "
                      f"dFID%={d['delta_vs_baseline_pct']:+.2f}% "
                      f"d_z={d['cohens_dz']:+.4f}", flush=True)

    # aggregate per n_rounds x scheduler
    agg: dict[str, dict] = {}
    for n_rounds in rounds:
        for sch in SCHEDULER_FILE_NAMES:
            deltas, dzs, pcts = [], [], []
            for seed in seeds:
                cell = per_cell[f"r{n_rounds}_s{seed}"]["framework_arms"].get(sch)
                if cell is None:
                    continue
                deltas.append(cell["per_sample_l2_sq_distance_mean"])
                dzs.append(cell["cohens_dz"])
                pcts.append(cell["delta_vs_baseline_pct"])
            if not dzs:
                continue
            n_neg = sum(1 for d in pcts if d < 0)
            n_pos = sum(1 for d in pcts if d > 0)
            verdict = ("framework_WINS" if n_neg == len(pcts)
                       else "REGRESSES" if n_pos == len(pcts)
                       else "TIE" if all(abs(d) < 1.0 for d in pcts) else "MIXED")
            agg[f"r{n_rounds}_{sch}"] = {
                "n_rounds": n_rounds, "scheduler": sch,
                "n_seeds": len(pcts),
                "delta_pct_per_seed": pcts,
                "mean_delta_pct": float(np.mean(pcts)),
                "d_z_per_seed": dzs,
                "mean_d_z": float(np.mean(dzs)),
                "verdict": verdict,
            }

    summary = {
        "kind": "gap04_r5b_rounds_multiseed",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "seeds": seeds, "n_rounds": rounds, "n_samples": n, "nfe": NFE,
        "device": "cuda", "match_nfe": "budget",
        "wall_seconds": walls,
        "per_cell": per_cell,
        "aggregate": agg,
    }
    out_json = OUT_DIR / "gap04-r5b-rounds-multiseed.json"
    out_json.write_text(json.dumps(summary, indent=2, default=str) + "\n")

    out_csv = OUT_DIR / "gap04-r5b-rounds-multiseed.csv"
    with out_csv.open("w", newline="") as f_:
        w = csv.writer(f_)
        w.writerow(["n_rounds", "scheduler", "n_seeds", "mean_delta_pct",
                    "mean_d_z", "verdict", "delta_pct_per_seed", "d_z_per_seed"])
        for rec in agg.values():
            w.writerow([rec["n_rounds"], rec["scheduler"], rec["n_seeds"],
                        rec["mean_delta_pct"], rec["mean_d_z"], rec["verdict"],
                        ";".join(f"{x:+.3f}" for x in rec["delta_pct_per_seed"]),
                        ";".join(f"{x:+.4f}" for x in rec["d_z_per_seed"])])

    print("\n" + "=" * 78)
    print("HEADLINE — GAP-04 R5b round-count multi-seed")
    print("=" * 78)
    for n_rounds in rounds:
        rows = [v for v in agg.values() if v["n_rounds"] == n_rounds]
        wins = sum(1 for v in rows if v["verdict"] == "framework_WINS")
        regs = sum(1 for v in rows if v["verdict"] == "REGRESSES")
        print(f"  n_rounds={n_rounds}: {wins} WINS / {regs} REGRESSES "
              f"of {len(rows)} schedulers")
    print(f"wrote {out_json}")
    print(f"wrote {out_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
