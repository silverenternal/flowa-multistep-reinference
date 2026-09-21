#!/usr/bin/env python3
"""Wave 235 P1: R5b CIFAR-10 RF --no-final-restart counterfactual sweep.

DeepSeek's highest-priority suggestion after Wave 233 P5:
"try --no-final-restart flag OR n_rounds=1 to see if the 1-NFE forced restart
blending is the structural cause" of the R5b regression.

This script runs three new configurations:
  1. n_rounds=10 + --no-final-restart  (drop the last 1-NFE restart blending)
  2. n_rounds=1                          (no multi-round at all)
  3. n_rounds=1 + --no-final-restart     (combined)

For each configuration it computes:
  - Headline FID vs CIFAR-10 reference (numpy InceptionV3 TF-port)
  - Per-sample L2² paired t-test on squared L2 distance in feature space
  - Bonferroni-corrected p-values

Output:
  verification_outputs/wave235-p1-r5b-fix.csv     (combined table of all 3 runs)
  verification_outputs/wave235-p1-r5b-fix.json  (machine-readable report)

Per-config sample NPZ directories:
  verification_outputs/wave235-p1-r5b-no-final-restart-n200/
  verification_outputs/wave235-p1-r5b-rounds1-n200/
  verification_outputs/wave235-p1-r5b-nofr-rounds1-n200/

NOTE: This script does NOT re-run baseline or n_rounds=2 (those data exist in
wave225-p7-r5b-rounds2-n200/). For comparison the existing wave225-p7 results
are imported from wave225-p7-r5b-reduced-rounds.csv/json in the audit doc.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
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

# Per-run configuration
RUN_CONFIGURATIONS: list[dict[str, object]] = [
    {
        "label": "no_final_restart_n10",
        "out_dir": "wave235-p1-r5b-no-final-restart-n200",
        "csv_json_basename": "wave235-p1-r5b-no-final-restart",
        "n_rounds": 10,
        "no_final_restart": True,
        "description": "n_rounds=10 + --no-final-restart (last round skipped)",
        "match_nfe": "budget",
        "framework_max_num_steps": 50,
        "baseline_num_steps": 50,
        "framework_samples": 200,
        "n_samples": 200,
    },
    {
        "label": "rounds1",
        "out_dir": "wave235-p1-r5b-rounds1-n200",
        "csv_json_basename": "wave235-p1-r5b-rounds1",
        "n_rounds": 1,
        "no_final_restart": False,
        "description": "n_rounds=1 (no multi-round at all)",
        "match_nfe": "budget",
        "framework_max_num_steps": 50,
        "baseline_num_steps": 50,
        "framework_samples": 200,
        "n_samples": 200,
    },
    {
        "label": "nofr_rounds1",
        "out_dir": "wave235-p1-r5b-nofr-rounds1-n200",
        "csv_json_basename": "wave235-p1-r5b-nofr-rounds1",
        "n_rounds": 1,
        "no_final_restart": True,
        "description": "n_rounds=1 + --no-final-restart (combined)",
        "match_nfe": "budget",
        "framework_max_num_steps": 50,
        "baseline_num_steps": 50,
        "framework_samples": 200,
        "n_samples": 200,
    },
]

CANONICAL_NAMES = {
    "baseline": "baseline",
    "cosineanneal": "CosineAnnealScheduler",
    "codimensionsheet": "CodimensionSheetScheduler",
    "evidencedriven": "EvidenceDrivenScheduler",
    "freetraj": "FreeTrajScheduler",
}

ARM_FILE_NAMES = {
    "baseline": "baseline_samples.npz",
    "cosineanneal": "cosineanneal_samples.npz",
    "codimensionsheet": "codimensionsheet_samples.npz",
    "evidencedriven": "evidencedriven_samples.npz",
    "freetraj": "freetraj_samples.npz",
}


def _fid_numpy(feat_a: np.ndarray, feat_b: np.ndarray) -> float:
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
    fd = float(
        diff @ diff
        + np.trace(sigma_a)
        + np.trace(sigma_b)
        - 2 * np.trace(covmean)
    )
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
            batch = torch.from_numpy(
                np.asarray(samples[i : i + 32], dtype=np.float32)
            )
            x = (batch + 1.0) / 2.0
            pred = model(x)[0].squeeze(3).squeeze(2)
            out[i : i + int(batch.shape[0])] = pred.cpu().numpy()
    return out


def _load_or_compute_features(
    cache_dir: Path, arm_name: str, npz_path: Path
) -> np.ndarray | None:
    """Load cached features if present, else compute from NPZ."""
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


def _run_sota_cifar(
    cfg: dict[str, object], device: str, log_path: Path
) -> dict[str, object]:
    """Invoke the SOTA CIFAR tool with the given config; return wall metrics."""
    cmd = [
        str(PYTHON_BIN),
        "tools/run_sota_cifar_experiment.py",
        "--checkpoint",
        "data/rectified_flow_cifar10.pth",
        "--device",
        device,
        "--n-samples",
        str(int(cfg["n_samples"])),
        "--framework-samples",
        str(int(cfg["framework_samples"])),
        "--n-rounds",
        str(int(cfg["n_rounds"])),
        "--baseline-num-steps",
        str(int(cfg["baseline_num_steps"])),
        "--framework-max-num-steps",
        str(int(cfg["framework_max_num_steps"])),
        "--integrator",
        "euler",
        "--match-nfe",
        str(cfg["match_nfe"]),
        "--ref-npz",
        "data/cifar10_test_ref.npz",
        "--output-dir",
        f"verification_outputs/{cfg['out_dir']}",
    ]
    if bool(cfg["no_final_restart"]):
        cmd.append("--no-final-restart")

    print(
        f"\n[wave235-p1] === Running config: {cfg['label']} "
        f"(n_rounds={cfg['n_rounds']}, no_final_restart={cfg['no_final_restart']}) ===",
        flush=True,
    )
    print(f"[wave235-p1] CMD: {' '.join(cmd)}", flush=True)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with log_path.open("w") as log_f:
        proc = subprocess.run(
            cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=9000
        )
        log_f.write("STDOUT:\n")
        log_f.write(proc.stdout)
        log_f.write("\n\nSTDERR:\n")
        log_f.write(proc.stderr)
    wall = float(time.perf_counter() - started)
    if proc.returncode != 0:
        print(
            f"[wave235-p1] FAILED: tail of stderr:\n{proc.stderr[-2000:]}",
            flush=True,
        )
        raise RuntimeError(
            f"config {cfg['label']} failed with exit code {proc.returncode}"
        )
    print(
        f"[wave235-p1] config {cfg['label']} done in {wall:.1f}s; "
        f"log={log_path}",
        flush=True,
    )
    return {
        "wall_seconds": wall,
        "log_path": str(log_path.relative_to(REPO_ROOT)),
        "return_code": proc.returncode,
    }


def _evaluate_run(
    cfg: dict[str, object],
    ref_feats: np.ndarray,
) -> dict[str, object]:
    """Compute headline FIDs + per-sample L2² d_z for one configuration."""
    run_dir = OUT_DIR / str(cfg["out_dir"])
    cache_dir = run_dir / "inception_feats_cache"
    arm_feats: dict[str, np.ndarray] = {}
    for arm_name, file_name in ARM_FILE_NAMES.items():
        npz_path = run_dir / file_name
        feats = _load_or_compute_features(cache_dir, arm_name, npz_path)
        if feats is not None:
            arm_feats[arm_name] = feats
            print(
                f"  [{cfg['label']}/{arm_name}] features shape={feats.shape}",
                flush=True,
            )

    headline_fids: dict[str, float] = {}
    for arm_name, feats in arm_feats.items():
        headline_fids[arm_name] = _fid_numpy(feats, ref_feats)

    baseline_fid = headline_fids["baseline"]
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
        delta_pct = float(
            (headline_fids[arm_name] - baseline_fid) / baseline_fid * 100.0
        )
        bonf_alpha = 0.05 / max(1, len(framework_arms_present))
        bonf_p = float(
            min(p * len(framework_arms_present), 1.0)
            if not math.isnan(p)
            else float("nan")
        )
        framework_arms_out[arm_name] = {
            "fid_headline": float(headline_fids[arm_name]),
            "delta_vs_baseline_fid_units": float(
                headline_fids[arm_name] - baseline_fid
            ),
            "delta_vs_baseline_pct": delta_pct,
            "per_sample_l2_sq_distance_mean": mean_d,
            "per_sample_l2_sq_distance_std": sd_d,
            "p_value_raw": p,
            "p_value_bonferroni": bonf_p,
            "alpha_bonferroni": bonf_alpha,
            "bonferroni_significant": bool(bonf_p < 0.05)
            if not math.isnan(bonf_p)
            else False,
            "cohens_dz": dz,
            "t_stat": t,
            "df": int(n - 1),
            "n_paired": int(n),
        }

    return {
        "headline_fids": {k: float(v) for k, v in headline_fids.items()},
        "baseline_fid": float(baseline_fid) if not math.isnan(baseline_fid) else None,
        "framework_arms": framework_arms_out,
    }


def _emit_csv(
    *,
    all_results: dict[str, dict],
    out_path: Path,
) -> None:
    """Write a combined CSV with one row per (config, scheduler)."""
    bonf_k = 4  # 4 scheduler arms per run
    bonf_alpha = 0.05 / bonf_k
    with out_path.open("w", newline="") as f_:
        w = csv.writer(f_)
        w.writerow([
            "config", "config_label", "description",
            "n_rounds", "no_final_restart",
            "scheduler", "fid_headline",
            "delta_vs_baseline_pct", "cohens_d_z",
            "n_paired", "mean_diff", "sd_diff",
            "t_statistic", "df", "p_value_raw", "CI95_low", "CI95_high",
            "alpha_bonferroni", "bonf_sig",
        ])
        for cfg_label, eval_data in all_results.items():
            cfg = next(c for c in RUN_CONFIGURATIONS if c["label"] == cfg_label)
            for arm_name, arm_data in eval_data["framework_arms"].items():
                canonical = CANONICAL_NAMES.get(arm_name, arm_name)
                mean_diff = arm_data["per_sample_l2_sq_distance_mean"]
                sd_diff = arm_data["per_sample_l2_sq_distance_std"]
                n_paired = arm_data["n_paired"]
                se = sd_diff / math.sqrt(n_paired)
                ci_low = mean_diff - 1.96 * se
                ci_high = mean_diff + 1.96 * se
                w.writerow([
                    cfg_label,
                    cfg_label,
                    str(cfg["description"]),
                    int(cfg["n_rounds"]),
                    bool(cfg["no_final_restart"]),
                    canonical,
                    arm_data["fid_headline"],
                    arm_data["delta_vs_baseline_pct"],
                    arm_data["cohens_dz"],
                    n_paired,
                    mean_diff,
                    sd_diff,
                    arm_data["t_stat"],
                    arm_data["df"],
                    arm_data["p_value_raw"],
                    ci_low,
                    ci_high,
                    bonf_alpha,
                    arm_data["bonferroni_significant"],
                ])


def _import_wave225_p7_baseline() -> dict[str, object] | None:
    """Load the existing Wave 225 P7 n_rounds=2 results for comparison."""
    p7_csv = OUT_DIR / "wave225-p7-r5b-reduced-rounds.csv"
    p7_json = OUT_DIR / "wave225-p7-r5b-reduced-rounds.json"
    if not p7_json.exists():
        return None
    return {
        "csv": str(p7_csv.relative_to(REPO_ROOT)),
        "json": str(p7_json.relative_to(REPO_ROOT)),
        "report": json.loads(p7_json.read_text()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wave 235 P1 — R5b --no-final-restart counterfactual sweep"
    )
    parser.add_argument(
        "--device",
        default="cuda:1",
        help="Device string passed to the SOTA CIFAR tool (default cuda:1)",
    )
    parser.add_argument(
        "--skip-runs",
        action="store_true",
        help="Skip the GPU runs and only re-evaluate from existing artifacts",
    )
    args = parser.parse_args()

    print("=== Wave 235 P1 — R5b CIFAR --no-final-restart counterfactual sweep ===", flush=True)
    print(f"[wave235-p1] REPO_ROOT={REPO_ROOT}", flush=True)
    print(f"[wave235-p1] PYTHON_BIN={PYTHON_BIN}", flush=True)
    print(f"[wave235-p1] device={args.device}", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ref_feats = np.load(
        REPO_ROOT / "data" / "cifar10_inception_features.npz",
        allow_pickle=False,
    )["features"].astype(np.float64)
    print(f"[wave235-p1] ref features shape={ref_feats.shape}", flush=True)

    if not args.skip_runs:
        log_dir = OUT_DIR / "_wave235-p1-logs"
        for cfg in RUN_CONFIGURATIONS:
            log_path = log_dir / f"{cfg['csv_json_basename']}.log"
            wall = _run_sota_cifar(cfg, args.device, log_path)
            cfg["_wall_seconds"] = wall["wall_seconds"]
            cfg["_log_path"] = wall["log_path"]
    else:
        print("[wave235-p1] --skip-runs set; using existing artifacts", flush=True)

    all_results: dict[str, dict] = {}
    for cfg in RUN_CONFIGURATIONS:
        print(
            f"\n[wave235-p1] === Evaluating config: {cfg['label']} ===",
            flush=True,
        )
        eval_data = _evaluate_run(cfg, ref_feats)
        all_results[cfg["label"]] = eval_data
        for arm_name, arm_data in eval_data["framework_arms"].items():
            print(
                f"  [{cfg['label']}/{arm_name}] "
                f"ΔFID%={arm_data['delta_vs_baseline_pct']:+.2f}% "
                f"d_z={arm_data['cohens_dz']:+.4f}",
                flush=True,
            )

    report = {
        "schema": "wave235_p1_r5b_fix_v1",
        "wave": "Wave 235 P1",
        "task": (
            "R5b CIFAR-10 RF --no-final-restart counterfactual sweep "
            "(DeepSeek suggestion C: test if 1-NFE forced restart blending "
            "is the structural cause of the R5b regression)"
        ),
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "device": args.device,
        "configurations_tested": [
            {
                "label": cfg["label"],
                "description": cfg["description"],
                "n_rounds": int(cfg["n_rounds"]),
                "no_final_restart": bool(cfg["no_final_restart"]),
                "match_nfe": cfg["match_nfe"],
                "baseline_num_steps": int(cfg["baseline_num_steps"]),
                "framework_max_num_steps": int(cfg["framework_max_num_steps"]),
                "framework_samples": int(cfg["framework_samples"]),
                "n_samples": int(cfg["n_samples"]),
                "wall_seconds": cfg.get("_wall_seconds"),
                "log_path": cfg.get("_log_path"),
                "out_dir": str(cfg["out_dir"]),
                "evaluation": all_results[cfg["label"]],
            }
            for cfg in RUN_CONFIGURATIONS
        ],
        "wave225_p7_reference": _import_wave225_p7_baseline(),
        "statistical_test_note": (
            "Per-sample paired t-test on squared L2 distance in InceptionV3 "
            "feature space (NOT chunk-level Fréchet FID t-test, due to "
            "rank-deficient covariance at chunk_size=20 with 2048-D features). "
            "Cohen's d_z is on per-sample feature distance (matches Wave 225 P7 "
            "metric for apples-to-apples comparison)."
        ),
    }

    out_json = OUT_DIR / "wave235-p1-r5b-fix.json"
    out_json.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"\n[wave235-p1] wrote {out_json}", flush=True)

    out_csv = OUT_DIR / "wave235-p1-r5b-fix.csv"
    _emit_csv(all_results=all_results, out_path=out_csv)
    print(f"[wave235-p1] wrote {out_csv}", flush=True)

    # Headline summary
    print()
    print("=" * 78)
    print("HEADLINE — Wave 235 P1 sweep results")
    print("=" * 78)
    for cfg_label, eval_data in all_results.items():
        cfg = next(c for c in RUN_CONFIGURATIONS if c["label"] == cfg_label)
        primary_arm = "cosineanneal"
        if primary_arm in eval_data["framework_arms"]:
            arm_data = eval_data["framework_arms"][primary_arm]
            print(
                f"  [{cfg_label}] n_rounds={cfg['n_rounds']} "
                f"no_final_restart={cfg['no_final_restart']}: "
                f"CosineAnneal ΔFID%={arm_data['delta_vs_baseline_pct']:+.2f}% "
                f"d_z={arm_data['cohens_dz']:+.4f}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())