#!/usr/bin/env python3
"""GAP-12-BASELINE — tuned-baseline fairness check on the CIFAR-10 RF cell.

`todo.json` GAP-12-BASELINE asks for "matched-NFE + at least one tuned baseline
per headline cell (straw-man exposure)". The classic framework-paper failure is
a **straw-man baseline**: the framework wins because the baseline was denied
compute. The direct test on a solver-based cell is to **give the baseline more
NFE** and check whether the framework's *matched-NFE* win survives.

This driver sweeps the **baseline** NFE over {50, 100, 200} while holding the
framework at the matched NFE=50 (single round), and reports the headline FID of
each arm. If the framework's matched-NFE FID still beats the baseline's *best*
NFE, the R5b win is not a compute artifact.

Usage::

    CUDA_VISIBLE_DEVICES=1 python scripts/gap12_tuned_baseline.py \\
        --baseline-nfes 50,100,200 --framework-nfe 50 --n-samples 200 --seed 42

HARD CONSTRAINT: one GPU only; cuda:1 unless overridden.
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

SCHEDULER_FILE_NAMES = {
    "CosineAnnealScheduler": "cosineanneal_samples.npz",
    "CodimensionSheetScheduler": "codimensionsheet_samples.npz",
    "EvidenceDrivenScheduler": "evidencedriven_samples.npz",
    "FreeTrajScheduler": "freetraj_samples.npz",
}


def _load_w247():
    path = REPO_ROOT / "scripts" / "wave247_p2_r5b_multiseed.py"
    spec = importlib.util.spec_from_file_location("_w247", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _run_one(baseline_nfe: int, framework_nfe: int, n_rounds: int, seed: int,
             n_samples: int, log_path: Path) -> dict:
    out_dir = (f"verification_outputs/gap12-tuned-baseline-bnfe{baseline_nfe}"
               f"-fnfe{framework_nfe}-n{n_samples}")
    cmd = [
        str(PYTHON_BIN), "tools/run_sota_cifar_experiment.py",
        "--checkpoint", str(CHECKPOINT),
        "--device", "cuda",
        "--n-samples", str(n_samples),
        "--framework-samples", str(n_samples),
        "--n-rounds", str(n_rounds),
        "--baseline-num-steps", str(baseline_nfe),
        "--framework-max-num-steps", str(framework_nfe),
        "--integrator", "euler",
        "--match-nfe", "budget",
        "--ref-npz", str(REF_NPZ),
        "--output-dir", out_dir,
    ]
    env = os.environ.copy()
    env["WAVE247_SEED"] = str(seed)
    env["CUDA_VISIBLE_DEVICES"] = os.environ.get("CUDA_VISIBLE_DEVICES", "1")
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    print(f"\n[gap12] baseline_nfe={baseline_nfe} framework_nfe={framework_nfe}: launching",
          flush=True)
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
        raise RuntimeError(f"baseline_nfe={baseline_nfe} failed rc={proc.returncode}: "
                           f"{proc.stderr[-2000:]}")
    print(f"[gap12] baseline_nfe={baseline_nfe} done in {wall:.1f}s", flush=True)
    return {"wall_seconds": wall, "out_dir": out_dir}


def _evaluate(w247, baseline_nfe: int, framework_nfe: int, n_samples: int, ref_feats) -> dict:
    run_dir = OUT_DIR / (f"gap12-tuned-baseline-bnfe{baseline_nfe}"
                         f"-fnfe{framework_nfe}-n{n_samples}")
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
    out = {}
    for arm_name, f in arm_feats.items():
        if arm_name == "baseline":
            continue
        bf = arm_feats["baseline"]
        diff_sq = ((bf - f) ** 2).sum(axis=1)
        n = diff_sq.shape[0]
        mean_d = float(diff_sq.mean())
        sd_d = float(diff_sq.std(ddof=1))
        dz = mean_d / sd_d if sd_d > 0 else float("nan")
        t = mean_d / (sd_d / np.sqrt(n)) if sd_d > 0 else float("nan")
        p = float(2 * _scipy_stats.t.sf(abs(t), df=n - 1)) if not math.isnan(t) else float("nan")
        delta_pct = float((headline_fids[arm_name] - baseline_fid) / baseline_fid * 100.0)
        out[arm_name] = {
            "fid_headline": float(headline_fids[arm_name]),
            "delta_vs_baseline_pct": delta_pct,
            "cohens_dz": dz, "t_stat": t, "p_value_raw": p, "n_paired": int(n),
        }
    return {
        "baseline_fid": float(baseline_fid) if not math.isnan(baseline_fid) else None,
        "framework_arms": out,
        "run_dir": str(run_dir.relative_to(REPO_ROOT)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline-nfes", default="50,100,200")
    ap.add_argument("--framework-nfe", type=int, default=50)
    ap.add_argument("--n-rounds", type=int, default=1)
    ap.add_argument("--n-samples", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--skip-runs", action="store_true")
    args = ap.parse_args()

    baseline_nfes = [int(x) for x in args.baseline_nfes.split(",")]
    w247 = _load_w247()
    ref_feats = np.load(REF_FEATS_NPZ, allow_pickle=False)["features"].astype(np.float64)
    print(f"[gap12] baseline_nfes={baseline_nfes} framework_nfe={args.framework_nfe} "
          f"n_rounds={args.n_rounds} N={args.n_samples} seed={args.seed}", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log_dir = OUT_DIR / "_gap12-logs"
    per_nfe: dict[str, dict] = {}
    for bnfe in baseline_nfes:
        if not args.skip_runs:
            _run_one(bnfe, args.framework_nfe, args.n_rounds, args.seed,
                     args.n_samples, log_dir / f"gap12-bnfe{bnfe}.log")
        per_nfe[str(bnfe)] = _evaluate(w247, bnfe, args.framework_nfe, args.n_samples, ref_feats)
        ev = per_nfe[str(bnfe)]
        print(f"  [baseline_nfe={bnfe}] baseline FID={ev['baseline_fid']:.4f}", flush=True)
        for arm, d in ev["framework_arms"].items():
            print(f"    {arm}: FID={d['fid_headline']:.4f} dFID%={d['delta_vs_baseline_pct']:+.2f}% "
                  f"d_z={d['cohens_dz']:+.4f}", flush=True)

    # baseline's BEST FID across the sweep
    baseline_fids = {k: v["baseline_fid"] for k, v in per_nfe.items()}
    best_bnfe = min(baseline_fids, key=lambda k: baseline_fids[k])
    best_baseline_fid = baseline_fids[best_bnfe]

    # framework at matched NFE (the bnfe == framework_nfe run), per scheduler
    matched = per_nfe.get(str(args.framework_nfe), {})
    verdict = {}
    for arm, d in matched.get("framework_arms", {}).items():
        fw_fid = d["fid_headline"]
        verdict[arm] = {
            "framework_fid_matched_nfe": fw_fid,
            "best_baseline_fid": best_baseline_fid,
            "best_baseline_nfe": int(best_bnfe),
            "framework_beats_tuned_baseline": bool(fw_fid < best_baseline_fid),
            "margin_vs_best_baseline_pct": float((fw_fid - best_baseline_fid) / best_baseline_fid * 100.0),
        }

    summary = {
        "kind": "gap12_tuned_baseline_cifar",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "cell": "R5b (CIFAR-10 RF)",
        "seed": args.seed, "n_samples": args.n_samples,
        "n_rounds": args.n_rounds, "framework_nfe": args.framework_nfe,
        "baseline_nfes": baseline_nfes,
        "per_baseline_nfe": per_nfe,
        "best_baseline": {"nfe": int(best_bnfe), "fid": best_baseline_fid},
        "verdict": verdict,
    }
    out_json = OUT_DIR / "gap12-tuned-baseline-cifar.json"
    out_json.write_text(json.dumps(summary, indent=2, default=str) + "\n")

    out_csv = OUT_DIR / "gap12-tuned-baseline-cifar.csv"
    with out_csv.open("w", newline="") as f_:
        w = csv.writer(f_)
        w.writerow(["baseline_nfe", "framework_nfe", "arm", "baseline_fid",
                    "framework_fid", "delta_pct", "cohens_dz", "n_paired"])
        for bnfe, ev in per_nfe.items():
            for arm, d in ev["framework_arms"].items():
                w.writerow([bnfe, args.framework_nfe, arm, ev["baseline_fid"],
                            d["fid_headline"], d["delta_vs_baseline_pct"],
                            d["cohens_dz"], d["n_paired"]])

    print("\n" + "=" * 78)
    print("HEADLINE — GAP-12 tuned baseline (CIFAR-10 RF)")
    print("=" * 78)
    print(f"  best baseline: NFE={best_bnfe} FID={best_baseline_fid:.4f}")
    for arm, v in verdict.items():
        print(f"  {arm}: framework@NFE{args.framework_nfe} FID={v['framework_fid_matched_nfe']:.4f} "
              f"vs best baseline FID={v['best_baseline_fid']:.4f} -> "
              f"{'BEATS' if v['framework_beats_tuned_baseline'] else 'LOSES'} "
              f"({v['margin_vs_best_baseline_pct']:+.2f}%)")
    print(f"wrote {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
