#!/usr/bin/env python3
"""Wave 235 P1: Simple postprocess - compute FID + per-sample d_z for 3 sweeps."""
from __future__ import annotations

import csv
import json
import math
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import scipy.stats

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
sys.path.insert(0, str(REPO_ROOT))
OUT_DIR = REPO_ROOT / "verification_outputs"

# Limit threads to avoid contention / hang in numpy BLAS
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

CONFIGS = [
    ("no_final_restart_n10", "wave235-p1-r5b-no-final-restart-n200", 10, True),
    ("rounds1", "wave235-p1-r5b-rounds1-n200", 1, False),
    ("nofr_rounds1", "wave235-p1-r5b-nofr-rounds1-n200", 1, True),
]
ARM_FILE_NAMES = {
    "baseline": "baseline_samples.npz",
    "cosineanneal": "cosineanneal_samples.npz",
    "codimensionsheet": "codimensionsheet_samples.npz",
    "evidencedriven": "evidencedriven_samples.npz",
    "freetraj": "freetraj_samples.npz",
}
CANONICAL_NAMES = {
    "baseline": "baseline",
    "cosineanneal": "CosineAnnealScheduler",
    "codimensionsheet": "CodimensionSheetScheduler",
    "evidencedriven": "EvidenceDrivenScheduler",
    "freetraj": "FreeTrajScheduler",
}


def fid_numpy(feat_a, feat_b):
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


def inception_feats(samples):
    import torch
    from pytorch_fid.inception import InceptionV3
    block_idx = InceptionV3.BLOCK_INDEX_BY_DIM[2048]
    model = InceptionV3([block_idx])
    model.eval()
    n = int(samples.shape[0])
    out = np.empty((n, 2048), dtype=np.float32)
    with torch.no_grad():
        for i in range(0, n, 32):
            batch = torch.from_numpy(np.asarray(samples[i:i+32], dtype=np.float32))
            x = (batch + 1.0) / 2.0
            pred = model(x)[0].squeeze(3).squeeze(2)
            out[i:i+int(batch.shape[0])] = pred.cpu().numpy()
    return out


def evaluate(label, out_dir_name, ref_feats, no_final_restart, n_rounds):
    run_dir = OUT_DIR / out_dir_name
    cache_dir = run_dir / "inception_feats_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    arm_feats = {}
    for arm, fname in ARM_FILE_NAMES.items():
        npz_path = run_dir / fname
        if not npz_path.exists():
            continue
        cache_path = cache_dir / f"{arm}.npy"
        if cache_path.exists():
            arm_feats[arm] = np.load(cache_path).astype(np.float64)
        else:
            samples = np.load(npz_path)["samples"].astype(np.float64)
            f = inception_feats(samples)
            np.save(cache_path, f)
            arm_feats[arm] = f.astype(np.float64)
        print(f"  [{label}/{arm}] features shape={arm_feats[arm].shape}", flush=True)

    fids = {}
    for arm, f in arm_feats.items():
        print(f"  [{label}/{arm}] computing FID...", flush=True)
        t0 = time.perf_counter()
        fids[arm] = fid_numpy(f, ref_feats)
        print(f"  [{label}/{arm}] FID = {fids[arm]:.4f} (took {time.perf_counter()-t0:.1f}s)", flush=True)

    base_fid = fids["baseline"]
    results = {}
    for arm in arm_feats:
        if arm == "baseline":
            continue
        diff_sq = ((arm_feats["baseline"] - arm_feats[arm]) ** 2).sum(axis=1)
        n = diff_sq.shape[0]
        mean_d = float(diff_sq.mean())
        sd_d = float(diff_sq.std(ddof=1))
        if sd_d > 0:
            t = mean_d / (sd_d / np.sqrt(n))
            p = float(2 * scipy.stats.t.sf(abs(t), df=n - 1))
            dz = mean_d / sd_d
        else:
            t, p, dz = float("nan"), float("nan"), float("nan")
        delta_pct = float((fids[arm] - base_fid) / base_fid * 100.0)
        results[arm] = {
            "fid_headline": fids[arm],
            "delta_pct": delta_pct,
            "d_z": dz,
            "mean": mean_d,
            "sd": sd_d,
            "p": p,
            "t": t,
            "n": n,
            "n_rounds": n_rounds,
            "no_final_restart": no_final_restart,
        }
        print(f"  [{label}/{arm}] FID={fids[arm]:.4f} dFID%={delta_pct:+.2f}% d_z={dz:+.4f} p={p:.4g}", flush=True)
    return base_fid, results


def main():
    print("=== Wave 235 P1 postprocess (simple) ===", flush=True)
    print(f"[postprocess] OPENBLAS_NUM_THREADS={os.environ.get('OPENBLAS_NUM_THREADS')}", flush=True)
    ref_feats = np.load(
        REPO_ROOT / "data" / "cifar10_inception_features.npz",
        allow_pickle=False,
    )["features"].astype(np.float64)
    print(f"[postprocess] ref features shape={ref_feats.shape}", flush=True)

    all_results = {}
    for label, out_dir_name, n_rounds, no_final_restart in CONFIGS:
        print(f"\n[postprocess] === {label} (n_rounds={n_rounds}, no_final_restart={no_final_restart}) ===", flush=True)
        base_fid, results = evaluate(label, out_dir_name, ref_feats, no_final_restart, n_rounds)
        all_results[label] = {
            "config_label": label,
            "n_rounds": n_rounds,
            "no_final_restart": no_final_restart,
            "out_dir": out_dir_name,
            "baseline_fid": base_fid,
            "results": results,
        }

    # Write JSON
    out_json = OUT_DIR / "wave235-p1-r5b-fix.json"
    out_json.write_text(json.dumps(all_results, indent=2, default=str) + "\n")
    print(f"\n[postprocess] wrote {out_json}", flush=True)

    # Write CSV
    out_csv = OUT_DIR / "wave235-p1-r5b-fix.csv"
    bonf_k = 4
    bonf_alpha = 0.05 / bonf_k
    with out_csv.open("w", newline="") as f_:
        w = csv.writer(f_)
        w.writerow([
            "config", "config_label", "n_rounds", "no_final_restart",
            "scheduler", "fid_headline", "delta_pct", "cohens_d_z",
            "n_paired", "mean_diff", "sd_diff",
            "t_statistic", "df", "p_value_raw", "CI95_low", "CI95_high",
            "alpha_bonferroni", "bonf_sig",
        ])
        for label, data in all_results.items():
            for arm, r in data["results"].items():
                canonical = CANONICAL_NAMES.get(arm, arm)
                n_paired = r["n"]
                mean_d = r["mean"]
                sd_d = r["sd"]
                se = sd_d / math.sqrt(n_paired) if sd_d > 0 else float("nan")
                ci_low = mean_d - 1.96 * se
                ci_high = mean_d + 1.96 * se
                bonf_p = min(r["p"] * bonf_k, 1.0) if not math.isnan(r["p"]) else float("nan")
                w.writerow([
                    label, label, data["n_rounds"], data["no_final_restart"],
                    canonical, r["fid_headline"], r["delta_pct"], r["d_z"],
                    n_paired, mean_d, sd_d,
                    r["t"], n_paired - 1, r["p"], ci_low, ci_high,
                    bonf_alpha, bonf_p < 0.05 if not math.isnan(bonf_p) else False,
                ])
    print(f"[postprocess] wrote {out_csv}", flush=True)


if __name__ == "__main__":
    main()