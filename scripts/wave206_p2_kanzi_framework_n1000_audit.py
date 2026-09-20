#!/usr/bin/env python3
"""Wave 206 P2: Kanzi framework_inv_proj N=1000 paired-record audit.

Reads the framework arm from this Wave 206 P2 sweep
(verification_outputs/wave206-p2-kanzi-framework-n1000.partial.json)
OR the Wave 196 P3 framework arm if the sweep did not finish
(verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj-framework/).
The framework arm is byte-stable across sweeps (verified: my partial 96-record
checkpoint RMSDs match Wave 196's first-96 framework RMSDs to 4 decimals).

Compares to the Wave 88 N=1000 baseline arm aggregate
(mean=0.9020 Å, std=0.1375 Å, n=1000), which lacks per-record data.

For the paired-record comparison:
- The Wave 88 baseline JSON has only aggregate summary stats (mean, std, n),
  no per_seq_rmsd_A. We therefore cannot do a strict paired t-test against
  baseline. Instead we do a 1-sample t-test: are the framework per-record
  RMSDs different from baseline mean=0.9020 Å?
- We also cross-validate against the Wave 127 framework_inv_proj run
  (mean=0.8798 Å, byte-stable) and Wave 196 P3 (mean=1.558 Å, byte-stable).

Computes the 12-col audit-grade row per Wave 203 P4 / CLM-066:
  - n_paired, mean_diff, sd_diff, t, df, p_raw, CI95_low, CI95_high,
    Cohen's d_z, test_type, family, alpha_bonferroni, bonf_sig

Outputs:
  - verification_outputs/wave206-p2-kanzi-framework-n1000.csv
  - verification_outputs/wave206-p2-kanzi-framework-n1000.json
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import scipy.stats

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
OUT_DIR = REPO_ROOT / "verification_outputs"

# This Wave 206 P2 sweep output (may be partial)
W206_OUT = Path("/tmp/w206/p2-kanzi-framework")
W206_METRICS = W206_OUT / "kanzi_n1000_framework_paper_metrics.json"
W206_CKPT = W206_OUT / "checkpoint.json"

# Wave 88 baseline aggregate (no per-record data)
W88_BASELINE = OUT_DIR / "wave88_kanzi_n1000_baseline" / "kanzi_n1000_paper_metrics.json"

# Wave 196 P3 framework_inv_proj N=1000 (byte-stable fallback)
W196_FRAMEWORK = OUT_DIR / "wave196-p3-kanzi-n1000-framework-inv-proj-framework" / "kanzi_n1000_framework_paper_metrics.json"

# Wave 127 framework_inv_proj N=1000 (cross-check)
W127_FRAMEWORK = OUT_DIR / "kanzi_n1000_framework_inv_proj_seed42_wave127_q3_2026" / "kanzi_n1000_framework_paper_metrics.json"


def load_per_seq_rmsd(metrics_path: Path) -> dict[str, float]:
    if not metrics_path.exists():
        return {}
    with metrics_path.open() as f:
        d = json.load(f)
    return d.get("per_seq_rmsd_A", {}) or {}


def load_per_seq_rmsd_from_checkpoint(ckpt_path: Path) -> dict[str, float]:
    if not ckpt_path.exists():
        return {}
    with ckpt_path.open() as f:
        d = json.load(f)
    records = d.get("records", [])
    return {f"seq_{r['index']}": r["rmsd_A"] for r in records}


def one_sample_t_test(samples: np.ndarray, mu0: float, alpha: float) -> dict:
    n = len(samples)
    res = {
        "n_paired": int(n),
        "mean_diff": float("nan"),
        "sd_diff": float("nan"),
        "t_statistic": float("nan"),
        "df": int(max(0, n - 1)),
        "p_value_raw": float("nan"),
        "ci_95": [float("nan"), float("nan")],
        "cohens_d_z": float("nan"),
        "bonf_sig": False,
    }
    if n < 2:
        return res
    diff = samples - mu0
    mean_diff = float(np.mean(diff))
    sd_diff = float(np.std(samples, ddof=1))
    se = sd_diff / math.sqrt(n)
    df = n - 1
    if sd_diff == 0.0:
        t_stat = float("inf") if mean_diff > 0 else float("-inf") if mean_diff < 0 else 0.0
        p_raw = 0.0 if mean_diff != 0 else 1.0
        d_z = 0.0
    else:
        t_stat = mean_diff / se
        p_raw = float(2.0 * scipy.stats.t.sf(abs(t_stat), df=df))
        d_z = mean_diff / sd_diff
    ci_lo = mean_diff - 1.96 * se
    ci_hi = mean_diff + 1.96 * se
    res.update({
        "mean_diff": mean_diff,
        "sd_diff": sd_diff,
        "t_statistic": float(t_stat),
        "df": int(df),
        "p_value_raw": p_raw,
        "ci_95": [float(ci_lo), float(ci_hi)],
        "cohens_d_z": float(d_z),
        "bonf_sig": bool(p_raw < alpha),
    })
    return res


def main() -> int:
    print("=" * 78)
    print("Wave 206 P2: Kanzi framework_inv_proj N=1000 (re-run) 12-col audit")
    print("=" * 78)

    # ---- Load baseline aggregate ----
    with W88_BASELINE.open() as f:
        baseline = json.load(f)
    b_summary = baseline["reconstruction_kabsch_rmsd_A"]
    b_mean = float(b_summary["mean_rmsd_A"])
    b_std = float(b_summary["std_rmsd_A"])
    b_n = int(b_summary["n_seqs"])
    print(f"W88 baseline (aggregate only, no per_seq_rmsd_A): "
          f"mean={b_mean:.4f} std={b_std:.4f} n={b_n}")

    # ---- Load framework per-record from THIS sweep (partial) ----
    f_partial_from_ckpt = load_per_seq_rmsd_from_checkpoint(W206_CKPT)
    f_partial_from_metrics = load_per_seq_rmsd(W206_METRICS)
    if f_partial_from_metrics:
        f_partial = f_partial_from_metrics
        f_partial_source = "this_sweep_metrics_json"
    elif f_partial_from_ckpt:
        f_partial = f_partial_from_ckpt
        f_partial_source = "this_sweep_checkpoint_json"
    else:
        f_partial = {}
        f_partial_source = "none"

    n_partial = len(f_partial)
    print(f"THIS sweep framework per_record: n={n_partial} (source={f_partial_source})")

    # ---- Fallback: Wave 196 framework per-record (byte-stable) ----
    f_w196 = load_per_seq_rmsd(W196_FRAMEWORK)
    n_w196 = len(f_w196)
    print(f"W196 framework per_record: n={n_w196} (byte-stable fallback)")
    w127 = json.load(W127_FRAMEWORK.open()) if W127_FRAMEWORK.exists() else {}
    print(f"W127 framework aggregate: mean={w127.get('reconstruction_kabsch_rmsd_A',{}).get('mean_rmsd_A',float('nan')):.4f}")
    print(f"W196 framework aggregate: mean={json.load(W196_FRAMEWORK.open())['reconstruction_kabsch_rmsd_A']['mean_rmsd_A']:.4f}")

    # ---- Byte-stability check: compare partial to w196 first n_partial ----
    byte_stable = False
    if f_partial and f_w196:
        # Sort by seq index
        sorted_partial = sorted(f_partial.items(), key=lambda x: int(x[0].split("_")[1]))
        sorted_w196 = sorted(f_w196.items(), key=lambda x: int(x[0].split("_")[1]))
        n_check = min(len(sorted_partial), len(sorted_w196))
        diffs = [abs(p[1] - w[1]) for p, w in zip(sorted_partial[:n_check], sorted_w196[:n_check])]
        max_diff = max(diffs) if diffs else 0.0
        mean_diff = float(np.mean(diffs)) if diffs else 0.0
        byte_stable = max_diff < 1e-3
        print(f"Byte-stability check (partial vs W196 first {n_check}): "
              f"max_abs_diff={max_diff:.2e} mean_abs_diff={mean_diff:.2e} "
              f"byte_stable={byte_stable}")

    # ---- Use this sweep's partial data for primary analysis ----
    # If this sweep is partial (<1000), use W196 full data as the
    # byte-stable re-run result for the headline N=1000 paired comparison.
    if n_partial >= 1000:
        f_used = f_partial
        f_used_source = "this_sweep_n1000"
    elif f_w196:
        f_used = f_w196
        f_used_source = "W196_byte_stable_fallback"
    else:
        f_used = f_partial
        f_used_source = "this_sweep_partial"

    print(f"Using framework arm: source={f_used_source} n={len(f_used)}")

    # ---- One-sample t-test: framework per-record RMSDs vs baseline mean ----
    f_vals = np.array([v for _, v in sorted(f_used.items(),
                                            key=lambda x: int(x[0].split("_")[1]))],
                      dtype=float)
    alpha_bonf = 0.05  # Single-cell family (R2 Kanzi RMSD); Bonferroni alpha = 0.05/1 = 0.05
    test = one_sample_t_test(f_vals, mu0=b_mean, alpha=alpha_bonf)
    f_mean = float(np.mean(f_vals))
    f_std = float(np.std(f_vals, ddof=1))
    f_n = len(f_vals)

    diff = f_mean - b_mean
    verdict = ("framework_wins" if diff < 0
               else "ties" if abs(diff) < 0.005
               else "baseline_wins")
    print(f"Framework mean RMSD: {f_mean:.4f} +/- {f_std:.4f} Å (n={f_n})")
    print(f"Baseline mean RMSD:  {b_mean:.4f} +/- {b_std:.4f} Å (n={b_n})")
    print(f"Mean diff (framework - baseline): {diff:+.4f} Å")
    print(f"1-sample t-test vs baseline: t={test['t_statistic']:.3f}, "
          f"df={test['df']}, p={test['p_value_raw']:.3e}, "
          f"Cohen's d_z={test['cohens_d_z']:.3f}, "
          f"Bonferroni sig={test['bonf_sig']} (alpha={alpha_bonf})")
    print(f"Verdict: {verdict}")

    # ---- Wallclock (from THIS sweep) ----
    wc_hours = 5.77  # ~5h46m, killed at budget

    # ---- Compose output row ----
    row = {
        "cell": "R2_kanzi_reconstruction_rmsd_A",
        "test_type": "one_sample_t_vs_baseline_mean",
        "family": "R2_kanzi",
        "alpha_bonferroni": alpha_bonf,
        "n_paired": test["n_paired"],
        "baseline_mean_A": b_mean,
        "baseline_std_A": b_std,
        "baseline_n": b_n,
        "framework_mean_A": f_mean,
        "framework_std_A": f_std,
        "framework_n": f_n,
        "mean_diff": test["mean_diff"],
        "sd_diff": test["sd_diff"],
        "t_statistic": test["t_statistic"],
        "df": test["df"],
        "p_value_raw": test["p_value_raw"],
        "ci_95_low": test["ci_95"][0],
        "ci_95_high": test["ci_95"][1],
        "cohens_d_z": test["cohens_d_z"],
        "bonf_sig": test["bonf_sig"],
        "framework_source": f_used_source,
        "n_partial_this_sweep": n_partial,
        "byte_stable_vs_w196": byte_stable,
        "verdict": verdict,
        "wallclock_hours": wc_hours,
    }

    # ---- Write CSV + JSON ----
    csv_path = OUT_DIR / "wave206-p2-kanzi-framework-n1000.csv"
    json_path = OUT_DIR / "wave206-p2-kanzi-framework-n1000.json"

    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        w.writeheader()
        w.writerow(row)
    print(f"Wrote: {csv_path}")

    with json_path.open("w") as f:
        json.dump(row, f, indent=2, default=float)
    print(f"Wrote: {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
