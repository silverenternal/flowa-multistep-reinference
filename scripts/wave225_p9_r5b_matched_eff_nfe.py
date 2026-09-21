#!/usr/bin/env python3
"""Wave 225 P9: matched-effective-NFE comparison.

Test if R5b matched-effective-NFE comparison (framework@NFE=100, rounds=2 vs
baseline@NFE=50) eliminates the R5b regression.

Setup:
- Framework: --baseline-num-steps 50 --framework-max-num-steps 100 --n-rounds 2
  --match-nfe budget
  - Cosine ramp cycle_length=2: round 0 n_cap=1.0 → 100 steps; round 1
    n_cap≈0.0 → 1 step.
  - Per-sample framework_total_nfe ≈ 101 (sum of per-round steps).
  - Per-sample EFFECTIVE NFE ≈ average(n_cap) * max_num_steps = 0.5 * 100 = 50.
- Baseline: 1 pass × 50 NFE → per-sample EFFECTIVE NFE = 50.

Both rows deliver ~50 effective NFE. If the R5b regression is a
definition-artifact (nominal vs effective NFE), this run should show
framework LOSING much less than at nominal-matched NFE=50.

Computes:
- Headline FID comparison (numpy InceptionV3 TF-port features against
  the 10000-image reference cached in
  data/cifar10_inception_features.npz).
- Per-sample paired t-test on squared L2 in InceptionV3 feature space
  (Wave 225 P7 §Method — same metric as the N=200 paired test, since
  the chunk-level FID t-test is numerically unstable at small N).
- Reports `matched_effective_nfe_d_z` (per-sample L2² d_z) and
  `matched_effective_nfe_p` (paired t-test p-value).

Output:
- verification_outputs/wave225-p9-r5b-matched-eff-nfe.csv
- verification_outputs/wave225-p9-r5b-matched-eff-nfe.json
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import scipy.stats

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "verification_outputs"
RUN_OUT_DIR = OUT_DIR / "wave225-p9-r5b-matched-eff-nfe-n200"
OUT_PATH_JSON = OUT_DIR / "wave225-p9-r5b-matched-eff-nfe.json"
OUT_PATH_CSV = OUT_DIR / "wave225-p9-r5b-matched-eff-nfe.csv"

ARM_FILE_NAMES = {
    "baseline": "baseline_samples.npz",
    "cosineannealscheduler": "cosineanneal_samples.npz",
    "codimensionsheetscheduler": "codimensionsheet_samples.npz",
    "evidencedrivenscheduler": "evidencedriven_samples.npz",
    "freetrajscheduler": "freetraj_samples.npz",
}

CANONICAL_NAMES = {
    "baseline": "baseline",
    "cosineannealscheduler": "CosineAnnealScheduler",
    "codimensionsheetscheduler": "CodimensionSheetScheduler",
    "evidencedrivenscheduler": "EvidenceDrivenScheduler",
    "freetrajscheduler": "FreeTrajScheduler",
}

R5B_BASELINE_D_Z: float = 2.7004
R5B_P7_PER_SAMPLE_D_Z: float = 5.444365365833261  # wave225-p7 N=200 per-sample L2² d_z

# Setup parameters
BASELINE_NOMINAL_NFE: int = 50
FRAMEWORK_NOMINAL_NFE: int = 100
FRAMEWORK_ROUNDS: int = 2
N_RECORDS: int = 200


def _fid_numpy(feat_a, feat_b):
    """Frechet distance with eigenclip fallback."""
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


def _inception_features(samples: np.ndarray) -> np.ndarray:
    """Compute InceptionV3 TF-port features for CIFAR-10 samples."""
    import torch
    from pytorch_fid.inception import InceptionV3

    block_idx = InceptionV3.BLOCK_INDEX_BY_DIM[2048]
    model = InceptionV3([block_idx])
    model.eval()

    n = int(samples.shape[0])
    out = np.empty((n, 2048), dtype=np.float32)
    with torch.no_grad():
        for i in range(0, n, 32):
            batch = torch.from_numpy(np.asarray(samples[i : i + 32], dtype=np.float32))
            x = (batch + 1.0) / 2.0
            pred = model(x)[0].squeeze(3).squeeze(2)
            out[i : i + int(batch.shape[0])] = pred.cpu().numpy()
    return out


def main():
    print("=== Wave 225 P9 matched-effective-NFE postprocess ===", flush=True)

    cache_dir = RUN_OUT_DIR / "inception_feats_cache"
    arm_feats: dict[str, np.ndarray] = {}

    # Available arms on disk
    available_files = {}
    for arm_name, file_name in ARM_FILE_NAMES.items():
        npz_path = RUN_OUT_DIR / file_name
        if npz_path.exists():
            available_files[arm_name] = npz_path

    if cache_dir.exists():
        for arm_name in available_files:
            cache_path = cache_dir / f"{arm_name}.npy"
            if cache_path.exists():
                arm_feats[arm_name] = np.load(cache_path).astype(np.float64)
                print(f"[{arm_name}] cached: {arm_feats[arm_name].shape}", flush=True)

    missing = [a for a in available_files if a not in arm_feats]
    if missing:
        # Compute from raw NPZ files
        cache_dir.mkdir(parents=True, exist_ok=True)
        for arm_name in missing:
            npz_path = available_files[arm_name]
            samples = np.load(npz_path)["samples"].astype(np.float64)
            feats = _inception_features(samples)
            np.save(cache_dir / f"{arm_name}.npy", feats)
            arm_feats[arm_name] = feats
            print(f"[{arm_name}] computed features: {feats.shape}", flush=True)

    # Note missing arms
    for arm_name in ARM_FILE_NAMES:
        if arm_name not in arm_feats:
            print(f"[{arm_name}] MISSING (not run)", flush=True)

    ref_feats = np.load(REPO_ROOT / "data" / "cifar10_inception_features.npz",
                        allow_pickle=False)["features"].astype(np.float64)
    print(f"[ref] shape: {ref_feats.shape}", flush=True)

    # Headline FIDs.
    headline_fids: dict[str, float] = {}
    for arm_name, feats in arm_feats.items():
        headline_fids[arm_name] = _fid_numpy(feats, ref_feats)
        print(f"[{arm_name}] headline FID = {headline_fids[arm_name]:.4f}", flush=True)

    baseline_fid = headline_fids["baseline"]

    # Per-sample paired t-test
    framework_arms_out: dict[str, dict] = {}
    framework_arms_present = [a for a in arm_feats if a != "baseline"]
    for arm_name in framework_arms_present:
        baseline_feats = arm_feats["baseline"]
        arm_feats_arr = arm_feats[arm_name]
        diff_sq = ((baseline_feats - arm_feats_arr) ** 2).sum(axis=1)
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
        bonf_alpha = 0.05 / max(1, len(framework_arms_present))
        bonf_p = float(min(p * len(framework_arms_present), 1.0)) if not math.isnan(p) else float("nan")
        framework_arms_out[arm_name] = {
            "fid_headline": float(headline_fids[arm_name]),
            "delta_vs_baseline_fid_units": float(headline_fids[arm_name] - baseline_fid),
            "delta_vs_baseline_pct": delta_pct,
            "per_sample_l2_sq_distance_mean": mean_d,
            "per_sample_l2_sq_distance_std": sd_d,
            "p_value_raw": p,
            "p_value_bonferroni": bonf_p,
            "alpha_bonferroni": bonf_alpha,
            "bonferroni_significant": bool(bonf_p < 0.05) if not math.isnan(bonf_p) else False,
            "cohens_dz": dz,
            "t_stat": t,
            "df": int(n - 1),
            "n_paired": int(n),
        }
        print(
            f"[{arm_name}] headline_FID={headline_fids[arm_name]:.4f} "
            f"ΔFID={headline_fids[arm_name] - baseline_fid:+.4f} "
            f"Δ%={delta_pct:+.2f}% "
            f"per-sample L2² dist mean={mean_d:.2f} d_z={dz:+.4f} p={p:.4g}",
            flush=True,
        )

    # Primary arm: cosineannealscheduler (R5b regression arm)
    primary_arm = "cosineannealscheduler"
    primary_d_z = framework_arms_out[primary_arm]["cohens_dz"]
    primary_p = framework_arms_out[primary_arm]["p_value_raw"]

    # Effective NFE calculation
    # Cosine ramp cycle_length=2: round 0 n_cap=1.0, round 1 n_cap≈0.0
    # Per-sample EFFECTIVE NFE = average(n_cap) * max_num_steps = 0.5 * 100 = 50
    # Baseline per-sample NFE = 50
    # So effective NFE matches at 50/50 (cosine halving = definition artifact)
    matched_effective_nfe_framework = 0.5 * float(FRAMEWORK_NOMINAL_NFE)
    matched_effective_nfe_baseline = float(BASELINE_NOMINAL_NFE)

    # Regression eliminated if the per-sample d_z (under matched-effective NFE)
    # is within tolerance of the P7 nominal-matched d_z AND headline ΔFID
    # is reduced substantially.
    # Definition: regression_eliminated = abs(ΔFID_pct) <= 5% AND d_z within P7 range
    primary_delta_pct = framework_arms_out[primary_arm]["delta_vs_baseline_pct"]
    primary_delta_fid = framework_arms_out[primary_arm]["delta_vs_baseline_fid_units"]
    eliminated = bool(
        abs(primary_delta_pct) <= 5.0
        and abs(primary_d_z) <= abs(R5B_P7_PER_SAMPLE_D_Z) * 0.5
    )

    report = {
        "wave": "225 P9",
        "task": "R5b matched-effective-NFE comparison — framework@NFE=100,rounds=2 vs baseline@NFE=50",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "n_records_per_arm": N_RECORDS,
        "n_rounds": FRAMEWORK_ROUNDS,
        "baseline_nominal_nfe": BASELINE_NOMINAL_NFE,
        "framework_nominal_nfe": FRAMEWORK_NOMINAL_NFE,
        "framework_effective_nfe_per_sample": matched_effective_nfe_framework,
        "baseline_effective_nfe_per_sample": matched_effective_nfe_baseline,
        "matched_definition": "effective NFE (avg n_cap * max_num_steps) — cosine ramp halves effective NFE",
        "device": "cuda",
        "primary_arm": primary_arm,
        "primary_arm_d_z": float(primary_d_z),
        "primary_arm_p_value": float(primary_p),
        "primary_arm_headline_fid": float(headline_fids[primary_arm]),
        "primary_arm_delta_fid_units": float(primary_delta_fid),
        "primary_arm_delta_fid_pct": float(primary_delta_pct),
        "baseline_headline_fid": float(baseline_fid),
        "r5b_nominal_matched_nfe_d_z_chunk_fid": R5B_BASELINE_D_Z,
        "r5b_p7_nominal_matched_nfe_d_z_per_sample": R5B_P7_PER_SAMPLE_D_Z,
        "r5b_p7_nominal_matched_delta_fid_pct": 9.77,
        "regression_eliminated_under_effective_nfe_match": eliminated,
        "headline_fids": {k: float(v) for k, v in headline_fids.items()},
        "framework_arms": framework_arms_out,
        "run_out_dir": str(RUN_OUT_DIR.relative_to(REPO_ROOT)),
        "audit_doc": "docs/audit/wave225-p9-r5b-matched-eff-nfe.md",
        "statistical_test_note": (
            "Per-sample paired t-test on squared L2 distance in InceptionV3 feature space "
            "(same metric as Wave 225 P7 for apples-to-apples comparison; the chunk-level "
            "Fréchet FID t-test is numerically unstable at N=200 with 2048-D features)."
        ),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH_JSON.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"\n[output] wrote {OUT_PATH_JSON}", flush=True)

    bonf_k = max(1, len(framework_arms_out))
    bonf_alpha = 0.05 / bonf_k
    with OUT_PATH_CSV.open("w", newline="") as f_:
        w = csv.writer(f_)
        w.writerow([
            "dataset", "model", "cell", "metric",
            "n_paired", "mean_diff", "sd_diff",
            "t_statistic", "df",
            "p_value_raw", "CI95_low", "CI95_high", "cohens_d_z",
            "test_type", "family", "alpha_bonferroni", "bonf_sig",
            "higher_better", "scheduler", "nfe_baseline", "nfe_framework_nominal",
            "nfe_framework_effective", "rounds", "delta_pct_vs_baseline",
        ])
        for arm_name, arm_data in framework_arms_out.items():
            canonical = CANONICAL_NAMES.get(arm_name, arm_name)
            mean_diff = arm_data["per_sample_l2_sq_distance_mean"]
            sd_diff = arm_data["per_sample_l2_sq_distance_std"]
            n_paired = arm_data["n_paired"]
            se = sd_diff / math.sqrt(n_paired)
            ci_low = mean_diff - 1.96 * se
            ci_high = mean_diff + 1.96 * se
            w.writerow([
                "cifar10_rf_v4_n200_eff_nfe_matched",
                "rectified_flow_cifar",
                f"R_cifar_v4_nfe_baseline{50}_fw_nominal100_eff50_{canonical}",
                "per_sample_l2_sq_dist",
                n_paired,
                mean_diff, sd_diff,
                arm_data["t_stat"], arm_data["df"],
                arm_data["p_value_raw"],
                ci_low, ci_high, arm_data["cohens_dz"],
                "paired_t_test_per_sample_l2",
                f"CIFAR_v4_eff_nfe_matched_k{bonf_k}",
                bonf_alpha, arm_data["bonferroni_significant"],
                False, canonical,
                BASELINE_NOMINAL_NFE, FRAMEWORK_NOMINAL_NFE,
                matched_effective_nfe_framework,
                FRAMEWORK_ROUNDS,
                arm_data["delta_vs_baseline_pct"],
            ])
    print(f"[output] wrote {OUT_PATH_CSV}", flush=True)

    print()
    print("=" * 78)
    print("PRIMARY RESULT — matched-effective-NFE comparison")
    print("=" * 78)
    print(
        f"  baseline @ NFE=50 (effective={matched_effective_nfe_baseline:.0f}): "
        f"headline FID = {baseline_fid:.4f}"
    )
    print(
        f"  framework @{primary_arm}, NFE=100, rounds=2 "
        f"(effective={matched_effective_nfe_framework:.0f}): "
        f"headline FID = {headline_fids[primary_arm]:.4f}"
    )
    print(
        f"  ΔFID (units, headline) = {primary_delta_fid:+.4f} "
        f"({primary_delta_pct:+.2f}%)"
    )
    print(
        f"  per-sample L2² d_z (matched-effective-NFE) = {primary_d_z:+.4f} "
        f"(p = {primary_p:.4g})"
    )
    print()
    print(
        f"  REFERENCE — Wave 225 P7 (nominal-matched NFE=50, effective=25): "
        f"ΔFID% = +9.77%, d_z = {R5B_P7_PER_SAMPLE_D_Z:+.4f}"
    )
    print(
        f"  REFERENCE — Wave 195 P2 (n_rounds=4, nominal-matched NFE=50): "
        f"chunk-FID d_z = {R5B_BASELINE_D_Z:+.4f}"
    )
    print()
    print(f"  regression_eliminated_under_effective_nfe_match = {eliminated}")


if __name__ == "__main__":
    main()
