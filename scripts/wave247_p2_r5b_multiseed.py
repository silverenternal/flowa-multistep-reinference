#!/usr/bin/env python3
"""Wave 247 P2: R5b CIFAR-10 RF n_rounds=1 multi-seed validation.

Per Wave 247 P1 history table, n_rounds=1 framework-WINS at N=200 with seed 0
(CosineAnneal -1.60% / Codim -2.53% / EvidenceDriven -0.12% / FreeTraj -0.66%).
This script replicates the finding across seeds {42, 43, 44} at N=100/200 to
verify seed-robustness of the n_rounds=1 framework-WINS headline.

This version uses the existing runner CLI (after adding `import os` to the
runner so the patch below works). At runtime we patch the two call sites in
`tools/run_sota_cifar_experiment.py` (lines 1348 and 1373) that hardcode
seed=0/seed_base=0 to read from `os.environ['WAVE247_SEED']`. The patch is
restored after each seed completes.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import scipy.stats

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "verification_outputs"
PYTHON_BIN = REPO_ROOT / ".venvs" / "lineageflow_venv" / "bin" / "python"

SEEDS = [42, 43, 44]
N_SAMPLES_DEFAULT = 100
N_ROUNDS = 1
NFE = 50
DEVICE = "cuda"
SCHEDULER_FILE_NAMES = {
    "CosineAnnealScheduler": "cosineanneal_samples.npz",
    "CodimensionSheetScheduler": "codimensionsheet_samples.npz",
    "EvidenceDrivenScheduler": "evidencedriven_samples.npz",
    "FreeTrajScheduler": "freetraj_samples.npz",
}


def _fid_numpy(feat_a, feat_b):
    from scipy.linalg import sqrtm
    if feat_a.shape[0] < 2 or feat_b.shape[0] < 2:
        return float("nan")
    mu_a, mu_b = feat_a.mean(0), feat_b.mean(0)
    sigma_a = np.cov(feat_a, rowvar=False)
    sigma_b = np.cov(feat_b, rowvar=False)
    diff = mu_a - mu_b
    try:
        covmean, _ = sqrtm(sigma_a @ sigma_b, disp=False)
    except TypeError:
        covmean = sqrtm(sigma_a @ sigma_b)
    if not np.isfinite(covmean).all():
        offset = np.eye(sigma_a.shape[0]) * 1e-6
        covmean = sqrtm((sigma_a + offset) @ (sigma_b + offset))
    if np.iscomplexobj(covmean):
        covmean = covmean.real
    fd = float(diff @ diff + np.trace(sigma_a) + np.trace(sigma_b) - 2 * np.trace(covmean))
    return fd if fd >= 0 else float("nan")


def _inception_features(samples):
    import torch
    from pytorch_fid.inception import InceptionV3
    block_idx = InceptionV3.BLOCK_INDEX_BY_DIM[2048]
    model = InceptionV3([block_idx])
    model.eval()
    n = int(samples.shape[0])
    out = np.empty((n, 2048), dtype=np.float32)
    with torch.no_grad():
        for i in range(0, n, 32):
            batch = torch.from_numpy(np.asarray(samples[i:i + 32], dtype=np.float32))
            x = (batch + 1.0) / 2.0
            pred = model(x)[0].squeeze(3).squeeze(2)
            out[i:i + int(batch.shape[0])] = pred.cpu().numpy()
    return out


def _load_or_compute_features(cache_dir, arm_name, npz_path):
    cache_path = cache_dir / f"{arm_name}.npy"
    if cache_path.exists():
        return np.load(cache_path).astype(np.float64)
    if not npz_path.exists():
        return None
    samples = np.load(npz_path)["samples"].astype(np.float64)
    feats = _inception_features(samples)
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache_path, feats)
    return feats


def _run_seed(seed, log_path, n_samples):
    """Patch the runner to read seed from env, invoke, restore."""
    runner_path = REPO_ROOT / "tools" / "run_sota_cifar_experiment.py"
    original_text = runner_path.read_text()

    patched = original_text.replace(
        "        seed=0,\n        output_dir=output_dir,\n    )\n    print(\n        f\"[run_sota_cifar_experiment] baseline: {baseline_path} \"",
        "        seed=int(os.environ.get('WAVE247_SEED', '0')),\n        output_dir=output_dir,\n    )\n    print(\n        f\"[run_sota_cifar_experiment] baseline: {baseline_path} \"",
    )
    patched = patched.replace(
        "            seed_base=0,\n            output_dir=output_dir,",
        "            seed_base=int(os.environ.get('WAVE247_SEED', '0')),\n            output_dir=output_dir,",
    )
    if patched == original_text:
        raise RuntimeError("Patches did not apply — runner text changed")

    runner_path.write_text(patched)
    try:
        out_dir = f"verification_outputs/wave247-p2-r5b-seed{seed}-n1-n{n_samples}"
        cmd = [
            str(PYTHON_BIN), "tools/run_sota_cifar_experiment.py",
            "--checkpoint", "data/rectified_flow_cifar10.pth",
            "--device", DEVICE,
            "--n-samples", str(n_samples),
            "--framework-samples", str(n_samples),
            "--n-rounds", str(N_ROUNDS),
            "--baseline-num-steps", str(NFE),
            "--framework-max-num-steps", str(NFE),
            "--integrator", "euler",
            "--match-nfe", "budget",
            "--ref-npz", "data/cifar10_test_ref.npz",
            "--output-dir", out_dir,
        ]
        env = os.environ.copy()
        env["WAVE247_SEED"] = str(seed)
        env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

        print(f"\n[wave247-p2] seed={seed}: launching", flush=True)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        with log_path.open("w") as log_f:
            proc = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env,
                                  capture_output=True, text=True, timeout=9000)
            log_f.write("STDOUT:\n")
            log_f.write(proc.stdout)
            log_f.write("\n\nSTDERR:\n")
            log_f.write(proc.stderr)
        wall = float(time.perf_counter() - started)
        if proc.returncode != 0:
            print(f"[wave247-p2] seed={seed} FAILED: tail:\n{proc.stderr[-2000:]}", flush=True)
            raise RuntimeError(f"seed={seed} failed with rc={proc.returncode}")
        print(f"[wave247-p2] seed={seed} done in {wall:.1f}s", flush=True)
        return {"wall_seconds": wall, "out_dir": out_dir, "log_path": str(log_path.relative_to(REPO_ROOT))}
    finally:
        runner_path.write_text(original_text)


def _evaluate_seed(seed, ref_feats, n_samples):
    run_dir = OUT_DIR / f"wave247-p2-r5b-seed{seed}-n1-n{n_samples}"
    cache_dir = run_dir / "inception_feats_cache"
    arm_feats = {}
    npz_baseline = run_dir / "baseline_samples.npz"
    feats = _load_or_compute_features(cache_dir, "baseline", npz_baseline)
    if feats is not None:
        arm_feats["baseline"] = feats
    for sch, fname in SCHEDULER_FILE_NAMES.items():
        npz = run_dir / fname
        f = _load_or_compute_features(cache_dir, sch, npz)
        if f is not None:
            arm_feats[sch] = f

    headline_fids = {a: _fid_numpy(f, ref_feats) for a, f in arm_feats.items()}
    baseline_fid = headline_fids.get("baseline", float("nan"))
    framework_arms_out = {}
    framework_present = [a for a in arm_feats if a != "baseline"]
    for arm_name in framework_present:
        bf = arm_feats["baseline"]
        af = arm_feats[arm_name]
        diff_sq = ((bf - af) ** 2).sum(axis=1)
        n = diff_sq.shape[0]
        mean_d = float(diff_sq.mean())
        sd_d = float(diff_sq.std(ddof=1))
        if sd_d > 0:
            t = mean_d / (sd_d / np.sqrt(n))
            p = float(2 * scipy.stats.t.sf(abs(t), df=n - 1))
            dz = mean_d / sd_d
        else:
            t, p, dz = float("nan"), float("nan"), float("nan")
        delta_pct = float((headline_fids[arm_name] - baseline_fid) / baseline_fid * 100.0)
        bonf_alpha = 0.05 / max(1, len(framework_present))
        bonf_p = float(min(p * len(framework_present), 1.0) if not math.isnan(p) else float("nan"))
        framework_arms_out[arm_name] = {
            "fid_headline": float(headline_fids[arm_name]),
            "delta_vs_baseline_fid_units": float(headline_fids[arm_name] - baseline_fid),
            "delta_vs_baseline_pct": delta_pct,
            "per_sample_l2_sq_distance_mean": mean_d,
            "per_sample_l2_sq_distance_std": sd_d,
            "p_value_raw": p, "p_value_bonferroni": bonf_p,
            "alpha_bonferroni": bonf_alpha,
            "bonferroni_significant": bool(bonf_p < 0.05) if not math.isnan(bonf_p) else False,
            "cohens_dz": dz, "t_stat": t, "df": int(n - 1), "n_paired": int(n),
        }

    return {
        "headline_fids": {k: float(v) for k, v in headline_fids.items()},
        "baseline_fid": float(baseline_fid) if not math.isnan(baseline_fid) else None,
        "framework_arms": framework_arms_out,
        "run_dir": str(run_dir.relative_to(REPO_ROOT)),
    }


def _per_seed_verdict(framework_arms):
    deltas = [a["delta_vs_baseline_pct"] for a in framework_arms.values()]
    n_neg = sum(1 for d in deltas if d < 0)
    n_pos = sum(1 for d in deltas if d > 0)
    if n_neg >= 3:
        return "framework_WINS"
    if n_pos >= 4:
        return "REGRESSES"
    if all(abs(d) < 1.0 for d in deltas):
        return "TIE"
    return "MIXED"


def _three_seed_pooled_d_z(per_seed_arms):
    pooled = {}
    for arm_name in next(iter(per_seed_arms)).keys():
        all_means, all_sds, all_ns = [], [], []
        for arms in per_seed_arms:
            a = arms[arm_name]
            all_means.append(a["per_sample_l2_sq_distance_mean"])
            all_sds.append(a["per_sample_l2_sq_distance_std"])
            all_ns.append(a["n_paired"])
        total_n = sum(all_ns)
        if total_n == 0:
            pooled[arm_name] = float("nan")
            continue
        pooled_mean = sum(m * n for m, n in zip(all_means, all_ns)) / total_n
        pooled_sd = max(all_sds) if all_sds else float("nan")
        pooled[arm_name] = float(pooled_mean / pooled_sd) if pooled_sd > 0 else float("nan")
    return pooled


def _emit_csv(per_seed_results, out_path, n_samples):
    bonf_alpha = 0.05 / 4
    with out_path.open("w", newline="") as f_:
        w = csv.writer(f_)
        w.writerow([
            "seed", "n_rounds", "scheduler", "fid_headline", "delta_pct", "cohens_d_z",
            "n_paired", "mean_diff", "sd_diff", "t_statistic", "df", "p_value_raw",
            "CI95_low", "CI95_high", "alpha_bonferroni", "bonf_sig", "baseline_fid",
        ])
        for seed, eval_data in per_seed_results.items():
            baseline_fid = eval_data["baseline_fid"]
            for arm_name, arm_data in eval_data["framework_arms"].items():
                mean_diff = arm_data["per_sample_l2_sq_distance_mean"]
                sd_diff = arm_data["per_sample_l2_sq_distance_std"]
                n_paired = arm_data["n_paired"]
                se = sd_diff / math.sqrt(n_paired)
                ci_low = mean_diff - 1.96 * se
                ci_high = mean_diff + 1.96 * se
                w.writerow([
                    seed, 1, arm_name,
                    arm_data["fid_headline"], arm_data["delta_vs_baseline_pct"],
                    arm_data["cohens_dz"], n_paired,
                    mean_diff, sd_diff,
                    arm_data["t_stat"], arm_data["df"], arm_data["p_value_raw"],
                    ci_low, ci_high,
                    bonf_alpha, arm_data["bonferroni_significant"],
                    baseline_fid,
                ])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--skip-runs", action="store_true")
    parser.add_argument("--n-samples", type=int, default=N_SAMPLES_DEFAULT)
    args = parser.parse_args()

    seeds = [int(s) for s in args.seeds.split(",")]
    n_samples = args.n_samples

    print(f"=== Wave 247 P2 — R5b CIFAR-10 RF n_rounds=1 multi-seed ===", flush=True)
    print(f"[wave247-p2] seeds={seeds}  n_rounds={N_ROUNDS}  NFE={NFE}  n_samples={n_samples}", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ref_feats = np.load(
        REPO_ROOT / "data" / "cifar10_inception_features.npz",
        allow_pickle=False,
    )["features"].astype(np.float64)
    print(f"[wave247-p2] ref features shape={ref_feats.shape}", flush=True)

    per_seed_results = {}
    per_seed_wall = {}
    if not args.skip_runs:
        log_dir = OUT_DIR / "_wave247-p2-logs"
        for seed in seeds:
            log_path = log_dir / f"wave247-p2-r5b-seed{seed}.log"
            wall = _run_seed(seed, log_path, n_samples)
            per_seed_wall[seed] = wall["wall_seconds"]

    for seed in seeds:
        per_seed_results[seed] = _evaluate_seed(seed, ref_feats, n_samples)
        for arm_name, arm_data in per_seed_results[seed]["framework_arms"].items():
            print(
                f"  [seed={seed}/{arm_name}] "
                f"ΔFID%={arm_data['delta_vs_baseline_pct']:+.2f}% "
                f"d_z={arm_data['cohens_dz']:+.4f}",
                flush=True,
            )

    per_seed_verdicts = {s: _per_seed_verdict(per_seed_results[s]["framework_arms"]) for s in seeds}
    per_seed_arms_list = [per_seed_results[s]["framework_arms"] for s in seeds]
    pooled = _three_seed_pooled_d_z(per_seed_arms_list)
    n_pooled_wins = sum(1 for dz in pooled.values() if dz > 0)
    n_pooled_losses = sum(1 for dz in pooled.values() if dz < 0)
    if n_pooled_wins >= 3:
        three_seed_verdict = "framework_WINS"
    elif n_pooled_losses >= 3:
        three_seed_verdict = "REGRESSES"
    else:
        three_seed_verdict = "MIXED"
    pooled_overall = float(np.mean(list(pooled.values())))
    n_rounds_1_win_seed_robust = all(v in ("framework_WINS", "TIE") for v in per_seed_verdicts.values())

    for seed, eval_data in per_seed_results.items():
        out_json = OUT_DIR / f"wave247-p2-r5b-seed{seed}-n1.json"
        out_json.write_text(json.dumps({
            "schema": "wave247_p2_r5b_seed_v1",
            "seed": seed, "n_rounds": N_ROUNDS, "nfe": NFE, "n_samples": n_samples,
            "device": DEVICE, "verdict": per_seed_verdicts[seed],
            "wall_seconds": per_seed_wall.get(seed),
            "evaluation": eval_data,
        }, indent=2, default=str) + "\n")

    out_csv = OUT_DIR / "wave247-p2-r5b-multiseed.csv"
    _emit_csv(per_seed_results, out_csv, n_samples)

    pooled_report = {
        "schema": "wave247_p2_r5b_multiseed_v1",
        "wave": "Wave 247 P2",
        "task": "R5b CIFAR-10 RF n_rounds=1 multi-seed validation (seeds 42, 43, 44)",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "device": DEVICE, "seeds": seeds, "n_rounds": N_ROUNDS, "nfe": NFE,
        "n_samples_per_seed": n_samples,
        "per_seed_results": {
            str(s): {
                "verdict": per_seed_verdicts[s],
                "wall_seconds": per_seed_wall.get(s),
                "baseline_fid": per_seed_results[s]["baseline_fid"],
                "framework_arms": per_seed_results[s]["framework_arms"],
                "run_dir": per_seed_results[s]["run_dir"],
            }
            for s in seeds
        },
        "three_seed_pooled_d_z_per_scheduler": pooled,
        "three_seed_pooled_d_z_overall_mean": pooled_overall,
        "three_seed_verdict": three_seed_verdict,
        "n_rounds_1_win_seed_robust": bool(n_rounds_1_win_seed_robust),
    }
    out_json_pooled = OUT_DIR / "wave247-p2-r5b-multiseed.json"
    out_json_pooled.write_text(json.dumps(pooled_report, indent=2, default=str) + "\n")

    print()
    print("=" * 78)
    print("HEADLINE — Wave 247 P2 multi-seed validation")
    print("=" * 78)
    for seed in seeds:
        v = per_seed_verdicts[seed]
        w = per_seed_wall.get(seed, float("nan"))
        print(f"  seed={seed}: verdict={v}  wall={w:.1f}s")
    print(f"  3-seed verdict: {three_seed_verdict}")
    print(f"  3-seed pooled mean d_z: {pooled_overall:+.4f}")
    print(f"  n_rounds=1 WIN seed-robust: {n_rounds_1_win_seed_robust}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
