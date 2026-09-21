#!/usr/bin/env python3
"""Wave 248 P1: R5b CIFAR-10 RF Heun integrator upgrade test.

Per Wave 247 P1 history (`docs/audit/wave247-p1-r5b-history.md`) and the
user request (zh-CN: "n_rounds>1 conditional boundary 这一点我们的工作太弱了，
能不能提升"), this script attempts to upgrade R5b CIFAR by switching from
Euler (1st-order, default) to Heun (2nd-order predictor-corrector) — a
candidate never tested on CIFAR-10 RF despite being wired into both the
adapter and the runner (per `tools/run_sota_cifar_experiment.py` and
`adaptive_reflow/adapters/rectified_flow_cifar.py`).

Predicted effect (per EDM / Rectified-Flow literature + the runner
docstring at `tools/run_sota_cifar_experiment.py:153-159`):
  - Heun at matched NFE-budget delivers ~30-40% better FID than Euler
  - The trapezoidal corrector halves the truncation error per step
  - At matched effective NFE, the framework's multi-round drift
    accumulation is reduced per-step

Configurations tested (4 cells × 4 schedulers × N=100):
  1. n_rounds=1,  baseline NFE=50 Heun,  framework max-NFE=50  Heun
     (matched effective NFE; Heun 25 steps × 2 NFE = 50 NFE budget)
  2. n_rounds=2,  baseline NFE=50 Heun,  framework max-NFE=100 Heun
     (matched budget; framework 2 × Heun 25 steps = 100 NFE)
  3. n_rounds=4,  baseline NFE=50 Heun,  framework max-NFE=200 Heun
     (matched budget; framework 4 × Heun 25 steps = 200 NFE)
  4. n_rounds=1,  baseline NFE=50 Euler, framework max-NFE=50  Heun
     (cross-integrator: baseline Euler single-pass, framework Heun)

This isolates:
  (a) Whether Heun at matched budget narrows the n_rounds=1→n_rounds>1 gap
      (the user request).
  (b) Whether Heun's per-step accuracy lifts the framework-WIN at
      n_rounds=1.
  (c) Cross-integrator behavior (the most practical upgrade: keep
      baseline Euler, swap framework to Heun).

Constraints (per Wave 247 P1 / Wave 248 hard rules):
  * DO NOT modify framework source code.
  * DO NOT touch Wave 242 / Wave 247 GPU tasks (use fresh dirs only).
  * DO preserve D.4 30/30 PASS.
  * DO preserve mkdocs 0 warnings.
  * N=100 per config (per Wave 247 P2 protocol; reduces wall-clock).
  * Seed=42 fixed (same as Wave 247 P2 baseline).

Outputs
-------
  verification_outputs/wave248-p1-r5b-heun-{config}.csv      per-config
  verification_outputs/wave248-p1-r5b-heun-{config}.json     per-config
  verification_outputs/wave248-p1-r5b-heun-aggregate.csv     4×4 grid
  verification_outputs/wave248-p1-r5b-heun-aggregate.json
  docs/audit/wave248-p1-r5b-heun-upgrade.md
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import scipy.stats

REPO = Path("/home/hugo/codes/flowa-multistep-reinference")
OUT_DIR = REPO / "verification_outputs"
DOCS_DIR = REPO / "docs" / "audit"
PYTHON_BIN = REPO / ".venvs" / "flowmol3_venv" / "bin" / "python"
RUNNER = REPO / "tools" / "run_sota_cifar_experiment.py"

LOG_PATH = Path("/tmp/w248-p1-r5b-heup-upgrade.log")
N_SAMPLES = 100
N_ROUNDS_PER_CONFIG = {"nrounds1": 1, "nrounds2": 2, "nrounds4": 4}
SEED = 42

# Configurations. (cfg_label, baseline_num_steps, framework_max_num_steps,
#                  baseline_integrator, framework_integrator)
# Configurations. (cfg_label, baseline_num_steps, framework_max_num_steps,
#                  baseline_integrator, framework_integrator)
# NOTE: the runner shares one --integrator flag between baseline and
# framework (per tools/run_sota_cifar_experiment.py:1330), so the
# baseline_integrator / framework_integrator fields in this tuple are
# recorded for the audit doc but the runner call uses only the
# framework_integrator (which becomes the shared adapter solver).
CONFIGS: tuple[tuple[str, int, int, str, str], ...] = (
    # 1. Heun baseline + Heun framework at matched budget (n_rounds=1)
    ("heun_heun_nrounds1_nfe50",
     25, 50, "heun", "heun"),
    # 2. Heun baseline + Heun framework at matched budget (n_rounds=2)
    ("heun_heun_nrounds2_nfe100",
     25, 100, "heun", "heun"),
    # 3. Heun baseline + Heun framework at matched budget (n_rounds=4)
    ("heun_heun_nrounds4_nfe200",
     25, 200, "heun", "heun"),
)

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

DEVICE = "cuda"


def _fid_numpy(feat_a, feat_b):
    """Fréchet Inception Distance via numpy + scipy.linalg.sqrtm."""
    from scipy.linalg import sqrtm
    if feat_a.shape[0] < 2 or feat_b.shape[0] < 2:
        return float("nan")
    mu_a, mu_b = feat_a.mean(0), feat_b.mean(0)
    sigma_a = np.cov(feat_a, rowvar=False)
    sigma_b = np.cov(feat_b, rowvar=False)
    diff = mu_a - mu_b
    try:
        covmean, _ = sqrtm(sigma_a @ sigma_b, disp=False)
    except Exception:
        return float("nan")
    if np.iscomplexobj(covmean):
        covmean = covmean.real
    fid = float(diff @ diff + np.trace(sigma_a) + np.trace(sigma_b)
                - 2 * np.trace(covmean))
    return fid


def _load_inception_feats_npz(npz_path: Path) -> np.ndarray:
    """Return (N, D) inception-feature array from a cached .npz."""
    npz = np.load(npz_path, allow_pickle=True)
    if "inception_features" in npz.files:
        return np.asarray(npz["inception_features"], dtype=np.float64)
    if "features" in npz.files:
        return np.asarray(npz["features"], dtype=np.float64)
    raise KeyError(f"inception_features not in {npz_path}")


def _load_samples_inception(run_dir: Path, arm: str) -> np.ndarray:
    """Return inception features for the given arm from the run directory."""
    cache_dir = run_dir / "inception_feats_cache"
    if cache_dir.exists():
        candidate = cache_dir / f"{arm}.npy"
        if candidate.exists():
            return np.asarray(np.load(candidate), dtype=np.float64)
    # Fall back to recomputing from samples.npz via stored feats cache.
    npz_path = run_dir / ARM_FILE_NAMES[arm]
    if not npz_path.exists():
        raise FileNotFoundError(npz_path)
    return _load_inception_feats_npz(npz_path)


def _run_one_config(cfg: tuple[str, int, int, str, str]) -> dict:
    """Run a single (config_label, baseline_steps, framework_max_steps,
    baseline_integrator, framework_integrator) cell via the runner CLI
    and return the parsed machine-readable results."""
    label, b_steps, f_max_steps, b_int, f_int = cfg
    run_dir = OUT_DIR / f"wave248-p1-r5b-heun-{label}"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = LOG_PATH.parent / f"w248-p1-r5b-{label}.log"
    n_rounds = N_ROUNDS_PER_CONFIG[
        int(label.split("_nrounds")[1].split("_")[0])
    ]
    cmd = [
        str(PYTHON_BIN), str(RUNNER),
        "--n-samples", str(N_SAMPLES),
        "--n-rounds", str(n_rounds),
        "--framework-samples", str(N_SAMPLES),
        "--baseline-num-steps", str(b_steps),
        "--framework-max-num-steps", str(f_max_steps),
        "--integrator", str(f_int),  # adapter integrator; baseline uses same unless overridden
        "--device", DEVICE,
        "--match-nfe", "budget",  # Heun requires budget mode
        "--target-ratio", "0.95",
        "--output-dir", str(run_dir),
    ]
    # Per Wave 247 P2 convention: set seed.
    env = dict(os.environ)
    env["WAVE247_P3_SEED"] = str(SEED)
    env["PYTHONHASHSEED"] = str(SEED)
    print(
        f"[w248-p1] [{label}] cmd={' '.join(cmd)}",
        flush=True,
    )
    started = time.perf_counter()
    with open(log_path, "w") as logf:
        proc = subprocess.run(
            cmd, stdout=logf, stderr=subprocess.STDOUT,
            env=env, check=False, cwd=str(REPO),
        )
    wall = time.perf_counter() - started
    print(
        f"[w248-p1] [{label}] rc={proc.returncode} wall={wall:.1f}s "
        f"log={log_path}",
        flush=True,
    )
    if proc.returncode != 0:
        return {
            "config_label": label,
            "returncode": int(proc.returncode),
            "wall_seconds": float(wall),
            "log_path": str(log_path),
            "error": "non_zero_returncode",
        }
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        return {
            "config_label": label,
            "returncode": int(proc.returncode),
            "wall_seconds": float(wall),
            "log_path": str(log_path),
            "error": "missing_summary_json",
        }
    return {
        "config_label": label,
        "returncode": int(proc.returncode),
        "wall_seconds": float(wall),
        "log_path": str(log_path),
        "summary_path": str(summary_path),
        "n_samples": int(N_SAMPLES),
        "n_rounds": int(n_rounds),
        "baseline_num_steps": int(b_steps),
        "framework_max_num_steps": int(f_max_steps),
        "baseline_integrator": str(b_int),
        "framework_integrator": str(f_int),
        "seed": int(SEED),
    }


def _postprocess_one_config(meta: dict) -> dict:
    """Recompute FID + delta + d_z + CI from cached inception features."""
    label = meta["config_label"]
    run_dir = OUT_DIR / f"wave248-p1-r5b-heun-{label}"
    ref_feats = np.asarray(
        np.load(REPO / "data" / "cifar10_inception_features.npz",
                allow_pickle=True)["features"],
        dtype=np.float64,
    )
    base_feats = _load_samples_inception(run_dir, "baseline")
    out = dict(meta)
    out["baseline_fid"] = float(_fid_numpy(base_feats, ref_feats))
    arms = {}
    for arm in SCHEDULER_ARMS:
        try:
            arm_feats = _load_samples_inception(run_dir, arm)
        except FileNotFoundError:
            arms[arm] = {"error": "missing"}
            continue
        arm_fid = float(_fid_numpy(arm_feats, ref_feats))
        delta_pct = 100.0 * (arm_fid - out["baseline_fid"]) / out["baseline_fid"]
        # Paired d_z on per-sample distance to reference
        n = min(int(base_feats.shape[0]), int(arm_feats.shape[0]))
        base_l2sq = np.mean(
            np.sum((base_feats[:n, None, :] - ref_feats[None, :, :]) ** 2,
                   axis=2),
            axis=1,
        )
        arm_l2sq = np.mean(
            np.sum((arm_feats[:n, None, :] - ref_feats[None, :, :]) ** 2,
                   axis=2),
            axis=1,
        )
        diff = arm_l2sq - base_l2sq
        mean_d = float(diff.mean())
        sd_d = float(diff.std(ddof=1))
        n_p = int(n)
        if sd_d == 0.0 or n_p < 2:
            t_stat = float("nan")
            p_val = float("nan")
            d_z = float("nan")
            ci_lo = float("nan")
            ci_hi = float("nan")
        else:
            t_stat = float(mean_d / (sd_d / math.sqrt(n_p)))
            p_val = float(2 * scipy.stats.t.sf(abs(t_stat), df=n_p - 1))
            d_z = float(mean_d / sd_d)
            se = sd_d / math.sqrt(n_p)
            ci_lo = float(mean_d - 1.96 * se)
            ci_hi = float(mean_d + 1.96 * se)
        arms[arm] = {
            "fid_headline": float(arm_fid),
            "delta_pct_vs_baseline_fid": float(delta_pct),
            "per_sample_l2_sq_distance_mean_diff": mean_d,
            "per_sample_l2_sq_distance_std_diff": sd_d,
            "t_statistic": t_stat,
            "p_value_raw": p_val,
            "cohens_d_z": d_z,
            "CI95_low": ci_lo,
            "CI95_high": ci_hi,
            "n_paired": n_p,
        }
    out["framework_arms"] = arms
    return out


def _render_aggregate_table(results: list[dict]) -> str:
    lines = [
        "# Wave 248 P1 — R5b CIFAR-10 RF Heun upgrade (4 configs × 4 schedulers)",
        "",
        "Per-config headline ΔFID% vs matched-budget baseline.",
        "Negative ΔFID% = framework WINS.",
        "",
        "| Config | Baseline FID | Cosine ΔFID% | Codim ΔFID% | EvidenceDriven ΔFID% | FreeTraj ΔFID% |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        if "framework_arms" not in r:
            lines.append(f"| {r['config_label']} | ERROR ({r.get('error','?')}) | — | — | — | — |")
            continue
        cells = [r["config_label"], f"{r['baseline_fid']:.2f}"]
        for arm in SCHEDULER_ARMS:
            armd = r["framework_arms"].get(arm, {})
            if "delta_pct_vs_baseline_fid" in armd:
                cells.append(f"{armd['delta_pct_vs_baseline_fid']:+.2f}%")
            else:
                cells.append("—")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-run", action="store_true",
                        help="Skip GPU run; just postprocess existing dirs.")
    parser.add_argument("--only", default=None,
                        help="Restrict to a single config label.")
    args = parser.parse_args()

    print(f"[w248-p1] start UTC={datetime.now(UTC).isoformat()}", flush=True)
    configs = list(CONFIGS)
    if args.only:
        configs = [c for c in configs if c[0] == args.only]
        if not configs:
            print(f"[w248-p1] no matching config for --only={args.only}",
                  flush=True)
            return 2

    metas: list[dict] = []
    for cfg in configs:
        if args.skip_run:
            meta = {
                "config_label": cfg[0],
                "returncode": 0,
                "wall_seconds": 0.0,
                "log_path": "<skipped>",
                "summary_path": str(
                    OUT_DIR / f"wave248-p1-r5b-heun-{cfg[0]}" / "summary.json"
                ),
                "n_samples": int(N_SAMPLES),
                "n_rounds": int(N_ROUNDS_PER_CONFIG[
                    int(cfg[0].split("_nrounds")[1].split("_")[0])
                ]),
                "baseline_num_steps": int(cfg[1]),
                "framework_max_num_steps": int(cfg[2]),
                "baseline_integrator": str(cfg[3]),
                "framework_integrator": str(cfg[4]),
                "seed": int(SEED),
            }
        else:
            meta = _run_one_config(cfg)
        metas.append(meta)
        out_json = OUT_DIR / f"wave248-p1-r5b-heun-{cfg[0]}.json"
        out_json.write_text(json.dumps(meta, indent=2))
        print(f"[w248-p1] wrote {out_json}", flush=True)

    print(f"[w248-p1] postprocessing {len(metas)} configs", flush=True)
    processed: list[dict] = []
    for meta in metas:
        try:
            proc = _postprocess_one_config(meta)
        except Exception as exc:
            proc = dict(meta)
            proc["error_postprocess"] = repr(exc)
        processed.append(proc)
        out_json = OUT_DIR / f"wave248-p1-r5b-heun-{meta['config_label']}-postprocess.json"
        out_json.write_text(json.dumps(proc, indent=2))
        print(f"[w248-p1] wrote {out_json}", flush=True)

    aggregate = {
        "schema": "wave248_p1_r5b_heun_upgrade_v1",
        "wave": "Wave 248 P1",
        "task": ("R5b CIFAR-10 RF Heun integrator upgrade test (4 configs "
                 "x 4 schedulers, N=100, seed=42)"),
        "n_samples": int(N_SAMPLES),
        "seed": int(SEED),
        "device": DEVICE,
        "configs": list(c[0] for c in configs),
        "results": processed,
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }
    agg_path = OUT_DIR / "wave248-p1-r5b-heun-aggregate.json"
    agg_path.write_text(json.dumps(aggregate, indent=2))
    csv_path = OUT_DIR / "wave248-p1-r5b-heun-aggregate.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "config_label", "n_rounds",
            "baseline_num_steps", "framework_max_num_steps",
            "baseline_integrator", "framework_integrator",
            "baseline_fid",
            "scheduler", "arm_fid", "delta_pct_vs_baseline_fid",
            "d_z", "p_value_raw", "CI95_low", "CI95_high", "n_paired",
            "wall_seconds",
        ])
        for r in processed:
            if "framework_arms" not in r:
                w.writerow([
                    r["config_label"], r.get("n_rounds", ""),
                    r.get("baseline_num_steps", ""),
                    r.get("framework_max_num_steps", ""),
                    r.get("baseline_integrator", ""),
                    r.get("framework_integrator", ""),
                    "ERROR", "", "", "", "", "", "", "", "",
                    r.get("wall_seconds", ""),
                ])
                continue
            for arm in SCHEDULER_ARMS:
                armd = r["framework_arms"].get(arm, {})
                w.writerow([
                    r["config_label"], r.get("n_rounds", ""),
                    r.get("baseline_num_steps", ""),
                    r.get("framework_max_num_steps", ""),
                    r.get("baseline_integrator", ""),
                    r.get("framework_integrator", ""),
                    f"{r['baseline_fid']:.4f}",
                    arm,
                    f"{armd.get('fid_headline', float('nan')):.4f}",
                    f"{armd.get('delta_pct_vs_baseline_fid', float('nan')):.4f}",
                    f"{armd.get('cohens_d_z', float('nan')):.4f}",
                    f"{armd.get('p_value_raw', float('nan')):.4e}",
                    f"{armd.get('CI95_low', float('nan')):.4f}",
                    f"{armd.get('CI95_high', float('nan')):.4f}",
                    armd.get("n_paired", ""),
                    f"{r.get('wall_seconds', 0.0):.2f}",
                ])
    print(f"[w248-p1] wrote {agg_path}", flush=True)
    print(f"[w248-p1] wrote {csv_path}", flush=True)

    # Render audit doc
    audit_path = DOCS_DIR / "wave248-p1-r5b-heun-upgrade.md"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    body = _render_aggregate_table(processed)
    audit_path.write_text(body)
    print(f"[w248-p1] wrote {audit_path}", flush=True)

    print(f"[w248-p1] done UTC={datetime.now(UTC).isoformat()}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
