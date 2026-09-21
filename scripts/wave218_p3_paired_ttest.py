#!/usr/bin/env python3
"""Wave 218 P3 — paired t-test analysis on Kanzi N=1000 framework vs baseline.

Reads:
  - framework: verification_outputs/wave218-p3-kanzi-framework-n1000/kanzi_n1000_framework_paper_metrics.json
  - baseline:  verification_outputs/wave218-p3-kanzi-baseline-n1000/kanzi_n1000_paper_metrics.json

Computes:
  - 12-col paired t-test audit row
  - 95% CI for mean diff
  - Cohen's d_z (paired)
  - p_bonferroni at family=7 cells (alpha=0.05/7=7.143e-3)

Writes:
  - verification_outputs/wave218-p3-kanzi-framework-wins.csv
  - verification_outputs/wave218-p3-kanzi-framework-wins.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def load_per_seq(path: Path) -> tuple[dict[str, float], dict]:
    """Load per_seq_rmsd_A dict + metadata."""
    d = json.loads(path.read_text())
    return d.get("per_seq_rmsd_A", {}), d


def paired_ttest(
    fw: np.ndarray,
    bw: np.ndarray,
    family_size: int = 7,
    alpha: float = 0.05,
) -> dict:
    """Compute paired t-test statistics on matched per-record arrays."""
    diff = fw - bw
    n = int(len(diff))
    df = n - 1
    mean_diff = float(np.mean(diff))
    sd_diff = float(np.std(diff, ddof=1))
    se_diff = sd_diff / np.sqrt(n)
    t_stat = mean_diff / se_diff if se_diff > 0 else float("nan")
    p_raw = float(2 * stats.t.sf(abs(t_stat), df)) if np.isfinite(t_stat) else float("nan")
    # Cohen's d_z (paired effect size)
    d_z = mean_diff / sd_diff if sd_diff > 0 else float("nan")
    # 95% CI for mean diff
    t_crit = stats.t.ppf(1 - alpha / 2, df)
    ci_low = mean_diff - t_crit * se_diff
    ci_high = mean_diff + t_crit * se_diff
    # Bonferroni
    p_bonf_alpha = alpha / family_size
    bonf_sig = p_raw < p_bonf_alpha if np.isfinite(p_raw) else False
    verdict = (
        "framework_wins"
        if mean_diff < 0 and bonf_sig
        else "baseline_wins"
        if mean_diff > 0 and bonf_sig
        else "tie"
    )
    return {
        "n_records": n,
        "framework_mean_A": float(np.mean(fw)),
        "baseline_mean_A": float(np.mean(bw)),
        "mean_diff_A": mean_diff,
        "sd_diff_A": sd_diff,
        "se_diff_A": float(se_diff),
        "t": float(t_stat),
        "df": int(df),
        "p_raw": p_raw,
        "ci95_low": float(ci_low),
        "ci95_high": float(ci_high),
        "d_z": float(d_z),
        "p_bonf_alpha": float(p_bonf_alpha),
        "bonf_sig": bool(bonf_sig),
        "verdict": verdict,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--framework", required=True, help="framework JSON path")
    parser.add_argument("--baseline", required=True, help="baseline JSON path")
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--family-size", type=int, default=7)
    args = parser.parse_args()

    fw_path = Path(args.framework)
    bw_path = Path(args.baseline)
    fw_dict, fw_meta = load_per_seq(fw_path)
    bw_dict, bw_meta = load_per_seq(bw_path)

    # Align by seq_idx
    common_keys = sorted(set(fw_dict.keys()) & set(bw_dict.keys()))
    if not common_keys:
        print("ERROR: no common per_seq keys", file=sys.stderr)
        return 1
    fw = np.array([fw_dict[k] for k in common_keys], dtype=np.float64)
    bw = np.array([bw_dict[k] for k in common_keys], dtype=np.float64)

    stats_dict = paired_ttest(fw, bw, family_size=args.family_size)
    stats_dict["framework_source"] = str(fw_path)
    stats_dict["baseline_source"] = str(bw_path)
    stats_dict["framework_n_records_in_file"] = fw_meta.get("n_records_processed")
    stats_dict["baseline_n_records_in_file"] = bw_meta.get("n_records_processed")
    stats_dict["paired_n_records"] = len(common_keys)
    stats_dict["framework_seed"] = fw_meta.get("seed")
    stats_dict["baseline_seed"] = bw_meta.get("seed")
    stats_dict["framework_sweep_wallclock_s"] = fw_meta.get("sweep_wallclock_s")
    stats_dict["baseline_sweep_wallclock_s"] = bw_meta.get("sweep_wallclock_s")

    # Write JSON
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(stats_dict, indent=2))

    # Write CSV (12-col audit row)
    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    csv_header = (
        "cell,metric,n_records,pairing,mean_diff,sd_diff,se_diff,ci_95_low,ci_95_high,"
        "t_statistic,df,p_raw,p_bonferroni_alpha,cohens_d_z,bonf_sig,verdict,"
        "framework_source,baseline_source\n"
    )
    csv_row = (
        f"R2_kanzi_inv_proj_rmsd_A,reconstruction_rmsd_Å,"
        f"{stats_dict['paired_n_records']},paired,"
        f"{stats_dict['mean_diff_A']:.6f},"
        f"{stats_dict['sd_diff_A']:.6f},"
        f"{stats_dict['se_diff_A']:.6f},"
        f"{stats_dict['ci95_low']:.6f},"
        f"{stats_dict['ci95_high']:.6f},"
        f"{stats_dict['t']:.4f},"
        f"{stats_dict['df']},"
        f"{stats_dict['p_raw']:.4e},"
        f"{stats_dict['p_bonf_alpha']:.4e},"
        f"{stats_dict['d_z']:.4f},"
        f"{stats_dict['bonf_sig']},"
        f"{stats_dict['verdict']},"
        f"{fw_path},{bw_path}\n"
    )
    if not out_csv.exists():
        out_csv.write_text(csv_header + csv_row)
    else:
        with out_csv.open("a") as f:
            f.write(csv_row)

    print(json.dumps(stats_dict, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())