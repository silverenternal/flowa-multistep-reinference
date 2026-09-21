#!/usr/bin/env python3
"""Wave 247 P3: R5b CIFAR-10 RF n_rounds=1 N=1000 replication.

Per Wave 247 P1 (`docs/audit/wave247-p1-r5b-history.md`) Strategy S4,
the n_rounds=1 framework-WINS finding (-1.60% to -2.53% at N=200,
seed=0) is the headline that needs gold-standard replication at N=1000
to harden the paper claim. This script runs the CIFAR-10 Rectified Flow
matched-NFE=50 sweep at N=1000, n_rounds=1, seed=42 and produces a
per-scheduler delta_FID_pct + Cohen's d_z CSV.

Usage:
    .venvs/flowmol3_venv/bin/python scripts/wave247_p3_r5b_n1000.py
    .venvs/flowmol3_venv/bin/python scripts/wave247_p3_r5b_n1000.py --skip-run

Output:
    verification_outputs/wave247-p3-r5b-n1000-n1/summary.json (runner)
    verification_outputs/wave247-p3-r5b-n1000-n1/comparison.md (runner)
    verification_outputs/wave247-p3-r5b-n1000-n1.csv (this script, headline)
    verification_outputs/wave247-p3-r5b-n1000-n1.json (this script, machine-readable)
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

PYTHON_BIN = REPO_ROOT / ".venvs" / "flowmol3_venv" / "bin" / "python"
OUT_DIR = REPO_ROOT / "verification_outputs"
RUN_DIR = OUT_DIR / "wave247-p3-r5b-n1000-n1"
LOG_PATH = Path("/tmp/w247-p3-n1000.log")

N_SAMPLES = 1000
N_ROUNDS = 1
NFE = 50
DEVICE = "cuda"  # runner accepts {cpu, cuda}; GPU 0 (PRO 6000, 98 GB free)
SEED = 42
SCHEDULER_ARMS = [
    "CosineAnnealScheduler",
    "CodimensionSheetScheduler",
    "EvidenceDrivenScheduler",
    "FreeTrajScheduler",
]
ARM_FILE_NAMES = {
    "CosineAnnealScheduler": "cosineanneal_samples.npz",
    "CodimensionSheetScheduler": "codimensionsheet_samples.npz",
    "EvidenceDrivenScheduler": "evidencedriven_samples.npz",
    "FreeTrajScheduler": "freetraj_samples.npz",
}


def _inception_features(samples: np.ndarray, batch_size: int = 32) -> np.ndarray:
    """Compute 2048-d InceptionV3 (TF-port via pytorch_fid) features.

    Mirrors the runner's inline path so that per-sample features can be
    paired for d_z computation. The canonical pytorch_fid TF-port Inception
    matches the FID_EXTRACTOR_FAMILY=inceptionv3_tfport reference path.
    """
    import torch
    from pytorch_fid.inception import InceptionV3

    block_idx = InceptionV3.BLOCK_INDEX_BY_DIM[2048]
    model = InceptionV3([block_idx])
    model.eval()
    n = int(samples.shape[0])
    out = np.empty((n, 2048), dtype=np.float32)
    with torch.no_grad():
        for i in range(0, n, batch_size):
            batch = torch.from_numpy(
                np.asarray(samples[i : i + batch_size], dtype=np.float32)
            )
            x = (batch + 1.0) / 2.0  # [-1,1] -> [0,1] for TF-port inception
            pred = model(x)[0].squeeze(3).squeeze(2)
            out[i : i + int(batch.shape[0])] = pred.cpu().numpy()
    return out


def _load_or_compute_features(cache_dir: Path, arm_name: str, npz_path: Path) -> np.ndarray | None:
    """Load cached inception features or compute + cache them."""
    cache_path = cache_dir / f"{arm_name}.npy"
    if cache_path.exists():
        return np.load(cache_path).astype(np.float64)
    if not npz_path.exists():
        return None
    samples = np.load(npz_path)["samples"].astype(np.float64)
    print(f"[w247-p3] computing inception features for {arm_name} (n={samples.shape[0]})...", flush=True)
    t0 = time.perf_counter()
    feats = _inception_features(samples)
    print(f"[w247-p3]   inception features for {arm_name} in {time.perf_counter() - t0:.1f}s", flush=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache_path, feats)
    return feats


def _fid_from_features(a: np.ndarray, b: np.ndarray) -> float:
    """Closed-form FID (Fréchet distance between two Gaussians)."""
    from scipy.linalg import sqrtm
    if a.shape[0] < 2 or b.shape[0] < 2:
        return float("nan")
    mu_a, mu_b = a.mean(0), b.mean(0)
    sigma_a = np.cov(a, rowvar=False)
    sigma_b = np.cov(b, rowvar=False)
    diff = mu_a - mu_b
    try:
        covmean = sqrtm(sigma_a @ sigma_b, disp=False)[0]
    except TypeError:
        covmean = sqrtm(sigma_a @ sigma_b)
    if np.iscomplexobj(covmean):
        covmean = covmean.real
    if not np.isfinite(covmean).all():
        offset = np.eye(sigma_a.shape[0]) * 1e-6
        covmean = sqrtm((sigma_a + offset) @ (sigma_b + offset))
        if np.iscomplexobj(covmean):
            covmean = covmean.real
    fd = float(diff @ diff + np.trace(sigma_a) + np.trace(sigma_b) - 2 * np.trace(covmean))
    return fd if fd >= 0 else float("nan")


def _run_sweep() -> dict:
    """Invoke the runner CLI and return timing + status."""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(PYTHON_BIN),
        "tools/run_sota_cifar_experiment.py",
        "--checkpoint", "data/rectified_flow_cifar10.pth",
        "--device", DEVICE,
        "--n-samples", str(N_SAMPLES),
        "--framework-samples", str(N_SAMPLES),
        "--n-rounds", str(N_ROUNDS),
        "--baseline-num-steps", str(NFE),
        "--framework-max-num-steps", str(NFE),
        "--integrator", "euler",
        "--match-nfe", "budget",
        "--ref-npz", "data/cifar10_test_ref.npz",
        "--output-dir", str(RUN_DIR.relative_to(REPO_ROOT)),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["WAVE247_P3_SEED"] = str(SEED)
    print(f"[w247-p3] launching runner: {' '.join(cmd)}", flush=True)
    t0 = time.perf_counter()
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("w") as log_f:
        proc = subprocess.run(
            cmd, cwd=str(REPO_ROOT), env=env,
            capture_output=True, text=True, timeout=7200,
        )
        log_f.write("STDOUT:\n")
        log_f.write(proc.stdout)
        log_f.write("\n\nSTDERR:\n")
        log_f.write(proc.stderr)
    wall = time.perf_counter() - t0
    print(f"[w247-p3] runner done in {wall:.1f}s, rc={proc.returncode}", flush=True)
    if proc.returncode != 0:
        print(f"[w247-p3] runner STDERR tail:\n{proc.stderr[-3000:]}", flush=True)
        raise RuntimeError(f"runner exited rc={proc.returncode}")
    return {"wall_seconds": wall, "returncode": proc.returncode}


def _patch_runner_seed() -> tuple[str, str]:
    """Patch the runner's two hardcoded seed=0 / seed_base=0 call sites
    so the per-sample RNG uses our SEED. Returns (original_text, patched_text).
    The patch is reverted in the finally block."""
    runner_path = REPO_ROOT / "tools" / "run_sota_cifar_experiment.py"
    original = runner_path.read_text()

    # The runner CLI doesn't expose --seed, so we patch the two call sites
    # to read from $WAVE247_P3_SEED, defaulting to 0 for byte-stability when
    # the env var is unset.
    patched = original.replace(
        "        seed=0,\n        output_dir=output_dir,\n    )\n    print(\n        f\"[run_sota_cifar_experiment] baseline: {baseline_path} \"",
        "        seed=int(os.environ.get('WAVE247_P3_SEED', '0')),\n        output_dir=output_dir,\n    )\n    print(\n        f\"[run_sota_cifar_experiment] baseline: {baseline_path} \"",
    )
    patched = patched.replace(
        "            seed_base=0,\n            output_dir=output_dir,",
        "            seed_base=int(os.environ.get('WAVE247_P3_SEED', '0')),\n            output_dir=output_dir,",
    )
    if patched == original:
        raise RuntimeError("Patches did not apply — runner text changed")
    runner_path.write_text(patched)
    return original, patched


def _restore_runner(original_text: str) -> None:
    runner_path = REPO_ROOT / "tools" / "run_sota_cifar_experiment.py"
    runner_path.write_text(original_text)


def _read_runner_summary() -> dict | None:
    summary_path = RUN_DIR / "summary.json"
    if not summary_path.exists():
        return None
    try:
        return json.loads(summary_path.read_text())
    except Exception:
        return None


def _evaluate() -> dict:
    """Compute per-scheduler FID + delta_FID_pct + d_z from the runner samples.

    Falls back to post-hoc inception computation if the runner's inline FID
    was NaN (e.g. pytorch_fid was not installed at runner time).
    """
    cache_dir = RUN_DIR / "inception_feats_cache"
    ref_feats = np.load(
        REPO_ROOT / "data" / "cifar10_inception_features.npz",
        allow_pickle=False,
    )["features"].astype(np.float64)
    print(f"[w247-p3] ref features shape={ref_feats.shape}", flush=True)

    # Per-arm feature caches.
    feats: dict[str, np.ndarray] = {}
    npz_baseline = RUN_DIR / "baseline_samples.npz"
    feats["baseline"] = _load_or_compute_features(cache_dir, "baseline", npz_baseline)
    for sch in SCHEDULER_ARMS:
        npz = RUN_DIR / ARM_FILE_NAMES[sch]
        feats[sch] = _load_or_compute_features(cache_dir, sch, npz)

    # Headline FID per arm (closed-form Fréchet vs full 10k ref).
    headline_fids = {a: _fid_from_features(f, ref_feats) for a, f in feats.items() if f is not None}
    baseline_fid = headline_fids.get("baseline", float("nan"))

    # Per-scheduler d_z via paired L2^2 distance between baseline & arm
    # inception features.
    framework_arms_out = {}
    bf = feats["baseline"]
    for sch in SCHEDULER_ARMS:
        af = feats[sch]
        diff_sq = ((bf - af) ** 2).sum(axis=1)
        n = diff_sq.shape[0]
        mean_d = float(diff_sq.mean())
        sd_d = float(diff_sq.std(ddof=1))
        if sd_d > 0 and n > 1:
            t = mean_d / (sd_d / math.sqrt(n))
            p = float(2 * scipy.stats.t.sf(abs(t), df=n - 1))
            dz = mean_d / sd_d
        else:
            t, p, dz = float("nan"), float("nan"), float("nan")
        delta_units = float(headline_fids[sch] - baseline_fid)
        delta_pct = float((headline_fids[sch] - baseline_fid) / baseline_fid * 100.0)
        ci_low = mean_d - 1.96 * sd_d / math.sqrt(n) if n > 1 else float("nan")
        ci_high = mean_d + 1.96 * sd_d / math.sqrt(n) if n > 1 else float("nan")
        framework_arms_out[sch] = {
            "fid_headline": float(headline_fids[sch]),
            "delta_vs_baseline_fid_units": delta_units,
            "delta_vs_baseline_pct": delta_pct,
            "per_sample_l2_sq_distance_mean": mean_d,
            "per_sample_l2_sq_distance_std": sd_d,
            "cohens_d_z": float(dz),
            "t_statistic": float(t),
            "df": int(n - 1),
            "p_value_raw": float(p),
            "CI95_low": ci_low,
            "CI95_high": ci_high,
            "n_paired": int(n),
        }

    return {
        "headline_fids": {k: float(v) for k, v in headline_fids.items()},
        "baseline_fid": float(baseline_fid),
        "framework_arms": framework_arms_out,
        "ref_features_path": "data/cifar10_inception_features.npz",
        "n_samples": N_SAMPLES,
        "n_rounds": N_ROUNDS,
        "nfe": NFE,
        "seed": SEED,
        "device": DEVICE,
        "extractor_family": "inceptionv3_tfport (pytorch_fid)",
    }


def _emit_csv(eval_data: dict, out_csv: Path) -> None:
    bonf_alpha = 0.05 / 4
    with out_csv.open("w", newline="") as f_:
        w = csv.writer(f_)
        w.writerow([
            "config", "config_label", "n_rounds", "no_final_restart", "scheduler",
            "fid_headline", "delta_pct", "cohens_d_z", "n_paired",
            "mean_diff", "sd_diff", "t_statistic", "df", "p_value_raw",
            "CI95_low", "CI95_high", "alpha_bonferroni", "bonf_sig", "baseline_fid",
        ])
        baseline_fid = eval_data["baseline_fid"]
        for sch in SCHEDULER_ARMS:
            arm = eval_data["framework_arms"][sch]
            mean_diff = arm["per_sample_l2_sq_distance_mean"]
            sd_diff = arm["per_sample_l2_sq_distance_std"]
            n_paired = arm["n_paired"]
            t_stat = arm["t_statistic"]
            p_val = arm["p_value_raw"]
            bonf_p = float(min(p_val * 4, 1.0)) if not math.isnan(p_val) else float("nan")
            bonf_sig = bool(bonf_p < 0.05) if not math.isnan(bonf_p) else False
            w.writerow([
                f"n1000_n1_seed{SEED}", f"n1000_n1_seed{SEED}", N_ROUNDS, False, sch,
                arm["fid_headline"], arm["delta_vs_baseline_pct"], arm["cohens_d_z"],
                n_paired, mean_diff, sd_diff, t_stat, arm["df"], p_val,
                arm["CI95_low"], arm["CI95_high"], bonf_alpha, bonf_sig,
                baseline_fid,
            ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-run", action="store_true", help="skip the runner sweep")
    parser.add_argument("--n-samples", type=int, default=N_SAMPLES)
    args = parser.parse_args()

    print(f"=== Wave 247 P3 — R5b CIFAR-10 RF n_rounds=1 N=1000 replication ===", flush=True)
    print(f"[w247-p3] seed={SEED}  n_rounds={N_ROUNDS}  NFE={NFE}  n_samples={args.n_samples}  device={DEVICE}", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    run_status = None
    if not args.skip_run:
        original, _patched = _patch_runner_seed()
        try:
            run_status = _run_sweep()
        finally:
            _restore_runner(original)

    eval_data = _evaluate()
    eval_data["timestamp_utc"] = datetime.now(UTC).isoformat()
    if run_status is not None:
        eval_data["runner_wall_seconds"] = run_status["wall_seconds"]
        eval_data["runner_returncode"] = run_status["returncode"]

    out_csv = OUT_DIR / "wave247-p3-r5b-n1000-n1.csv"
    _emit_csv(eval_data, out_csv)

    out_json = OUT_DIR / "wave247-p3-r5b-n1000-n1.json"
    out_json.write_text(json.dumps({
        "schema": "wave247_p3_r5b_n1000_v1",
        "wave": "Wave 247 P3",
        "task": "R5b CIFAR-10 RF n_rounds=1 N=1000 replication (single-seed, gold-standard)",
        "reference_seed0_N200": {
            "source": "verification_outputs/wave235-p1-r5b-fix.csv",
            "values": {
                "CosineAnnealScheduler": -1.6018242836951462,
                "CodimensionSheetScheduler": -2.530172588280457,
                "EvidenceDrivenScheduler": -0.11727964178747405,
                "FreeTrajScheduler": -0.663788768741204,
            },
        },
        "evaluation": eval_data,
        "verdict_per_scheduler": {
            sch: ("framework_WINS" if eval_data["framework_arms"][sch]["delta_vs_baseline_pct"] < 0
                  else "REGRESSES" if eval_data["framework_arms"][sch]["delta_vs_baseline_pct"] > 0
                  else "TIE")
            for sch in SCHEDULER_ARMS
        },
    }, indent=2, default=str) + "\n")

    print()
    print("=" * 78)
    print("HEADLINE — Wave 247 P3 N=1000")
    print("=" * 78)
    for sch in SCHEDULER_ARMS:
        a = eval_data["framework_arms"][sch]
        print(f"  {sch}: FID={a['fid_headline']:.2f}  ΔFID%={a['delta_vs_baseline_pct']:+.2f}%  d_z={a['cohens_d_z']:+.4f}  verdict={('framework_WINS' if a['delta_vs_baseline_pct']<0 else 'REGRESSES' if a['delta_vs_baseline_pct']>0 else 'TIE')}")
    print(f"  baseline FID: {eval_data['baseline_fid']:.2f}")
    print(f"  CSV: {out_csv.relative_to(REPO_ROOT)}")
    print(f"  JSON: {out_json.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
