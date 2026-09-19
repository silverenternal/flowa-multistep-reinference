#!/usr/bin/env python3
"""Wave 197 P2 — Aggregate per-arm per-NFE summaries at n=100.

Reads eval outputs from /tmp/w197/track_b/eval/ and produces:
  - verification_outputs/wave197-p2-4arm-n100-summary.csv (per-arm x NFE rollup)
  - verification_outputs/wave197-p2-4arm-paired.csv (paired t-test, n=100)

Naming convention matches Wave 196 P2 outputs (wave197 prefix).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
EVAL_DIR: Path = Path("/tmp/w197/track_b/eval")
OUT_DIR: Path = REPO_ROOT / "verification_outputs"

#: Total cells in Table B (4-arm, n=100): 4 baselines × 2 NFE × 2 metrics = 16.
N_CELLS: int = 16
ALPHA_FAMILY: float = 0.05
Z_CRIT_95: float = 1.959963984540054
UNDERPOWERED_POWER_THRESHOLD: float = 0.5
MIN_EFFECT_SIZE_PLDDT: float = 0.01
MIN_EFFECT_SIZE_SCPERP: float = 0.01

ARMS = ["vanilla", "fastdllm", "abcache", "lediflow"]
NFES = [50, 100]
SEEDS = list(range(42, 72))


def collect_arm_seed_metrics(arm: str) -> dict:
    """Collect per-arm per-seed pLDDT and scPerplexity means from eval outputs."""
    rows = []
    for nfe in NFES:
        for seed in SEEDS:
            summary = EVAL_DIR / f"{arm}_nfe{nfe}_seed{seed}" / "summary.json"
            if not summary.exists():
                continue
            try:
                d = json.loads(summary.read_text())
                f = d.get("foldability", {})
                rows.append({
                    "nfe": nfe,
                    "seed": seed,
                    "n_records": f.get("n_total"),
                    "plddt_mean": f.get("plddt_mean_mean"),
                    "sc_perplexity_mean": f.get("sc_perplexity_mean"),
                })
            except Exception:
                continue
    return rows


def aggregate_per_arm_per_nfe(arm: str) -> dict:
    rows = collect_arm_seed_metrics(arm)
    out = {}
    for nfe in NFES:
        sub = [r for r in rows if r["nfe"] == nfe]
        if not sub:
            out[nfe] = None
            continue
        plddts = np.array([r["plddt_mean"] for r in sub if r["plddt_mean"] is not None], dtype=float)
        scps = np.array([r["sc_perplexity_mean"] for r in sub if r["sc_perplexity_mean"] is not None], dtype=float)
        out[nfe] = {
            "n_seeds": len(sub),
            "n_records_per_arm": int(np.sum([r["n_records"] for r in sub if r["n_records"]])) if sub else 0,
            "plddt_mean": float(np.mean(plddts)) if len(plddts) else float("nan"),
            "plddt_std": float(np.std(plddts, ddof=1)) if len(plddts) > 1 else float("nan"),
            "sc_perplexity_mean": float(np.mean(scps)) if len(scps) else float("nan"),
            "sc_perplexity_std": float(np.std(scps, ddof=1)) if len(scps) > 1 else float("nan"),
        }
    return out


def write_summary_csv(path: Path, all_arm_data: dict) -> None:
    """Write per-arm per-NFE rollup CSV (matches Wave 196 P2 format)."""
    fieldnames = [
        "arm", "nfe", "n_seeds", "n_records_per_arm",
        "plddt_mean", "plddt_std",
        "sc_perplexity_mean", "sc_perplexity_std",
        "baseline_plddt", "baseline_scperp",
        "delta_plddt_vs_baseline", "delta_scperp_vs_baseline",
    ]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for arm in ARMS:
            for nfe in NFES:
                d = all_arm_data.get(arm, {}).get(nfe)
                if d is None:
                    continue
                if arm == "vanilla":
                    w.writerow({
                        "arm": arm, "nfe": nfe,
                        "n_seeds": d["n_seeds"], "n_records_per_arm": d["n_records_per_arm"],
                        "plddt_mean": d["plddt_mean"], "plddt_std": d["plddt_std"],
                        "sc_perplexity_mean": d["sc_perplexity_mean"],
                        "sc_perplexity_std": d["sc_perplexity_std"],
                        "baseline_plddt": "nan", "baseline_scperp": "nan",
                        "delta_plddt_vs_baseline": "nan", "delta_scperp_vs_baseline": "nan",
                    })
                else:
                    base = all_arm_data.get("vanilla", {}).get(nfe)
                    if base is None:
                        base_plddt, base_sc = float("nan"), float("nan")
                        dplddt, dsc = float("nan"), float("nan")
                    else:
                        base_plddt, base_sc = base["plddt_mean"], base["sc_perplexity_mean"]
                        dplddt = d["plddt_mean"] - base_plddt
                        dsc = d["sc_perplexity_mean"] - base_sc
                    w.writerow({
                        "arm": arm, "nfe": nfe,
                        "n_seeds": d["n_seeds"], "n_records_per_arm": d["n_records_per_arm"],
                        "plddt_mean": d["plddt_mean"], "plddt_std": d["plddt_std"],
                        "sc_perplexity_mean": d["sc_perplexity_mean"],
                        "sc_perplexity_std": d["sc_perplexity_std"],
                        "baseline_plddt": base_plddt, "baseline_scperp": base_sc,
                        "delta_plddt_vs_baseline": dplddt, "delta_scperp_vs_baseline": dsc,
                    })


def run_paired_power(arm: str, nfe: int, metric: str) -> dict:
    """Compute paired t-test (n=100) for baseline_arm vs framework (FlowA) per cell.

    Returns dict with verdict, t-stat, p-value, etc.
    """
    base_rows = [r for r in collect_arm_seed_metrics(arm) if r["nfe"] == nfe]
    flowa_rows = [r for r in collect_arm_seed_metrics("flowa") if r["nfe"] == nfe]
    base_dict = {r["seed"]: r for r in base_rows}
    flowa_dict = {r["seed"]: r for r in flowa_rows}
    common_seeds = sorted(set(base_dict.keys()) & set(flowa_dict.keys()))
    if len(common_seeds) < 2:
        return {"verdict": "INSUFFICIENT_DATA", "n_pairs": len(common_seeds)}
    base_v = np.array([base_dict[s][metric] for s in common_seeds], dtype=float)
    flowa_v = np.array([flowa_dict[s][metric] for s in common_seeds], dtype=float)
    diff = flowa_v - base_v
    n = len(diff)
    if n < 3:
        return {"verdict": "INSUFFICIENT_DATA", "n_pairs": n}

    mean_diff = float(np.mean(diff))
    std_diff = float(np.std(diff, ddof=1))
    if std_diff == 0:
        return {"verdict": "TIE", "n_pairs": n}
    se_diff = std_diff / math.sqrt(n)
    t_stat = mean_diff / se_diff
    df = n - 1
    p_two_sided = float(2 * (1 - stats.t.cdf(abs(t_stat), df=df)))
    alpha_bonferroni = ALPHA_FAMILY / N_CELLS
    p_bonf = min(1.0, p_two_sided * N_CELLS)

    if metric == "plddt_mean":
        min_effect = MIN_EFFECT_SIZE_PLDDT
        higher_better = True
    else:
        min_effect = MIN_EFFECT_SIZE_SCPERP
        higher_better = False  # scPerplexity: lower is better

    # Cohen's d_z
    cohens_d_z = mean_diff / std_diff if std_diff > 0 else 0.0
    # 95% CI
    ci_lo = mean_diff - Z_CRIT_95 * se_diff
    ci_hi = mean_diff + Z_CRIT_95 * se_diff
    # Post-hoc power at observed effect
    def power_at(delta: float) -> float:
        if std_diff <= 0:
            return 1.0
        d = delta / std_diff
        ncp = abs(d) * math.sqrt(n)
        # two-sided
        return float(1 - stats.nct.cdf(stats.t.ppf(1 - alpha_bonferroni / 2, df), df, ncp) +
                          stats.nct.cdf(stats.t.ppf(alpha_bonferroni / 2, df), df, ncp))

    power_obs = power_at(abs(mean_diff))
    power_min = power_at(min_effect)

    # Verdict precedence (matches Wave 196 P2 / Wave 195 P3 ladder)
    if abs(mean_diff) < min_effect:
        verdict = "TIE"
    elif power_min < UNDERPOWERED_POWER_THRESHOLD:
        verdict = "UNDERPOWERED"
    elif p_bonf < alpha_bonferroni:
        # Significance check: framework wins if higher_better and mean_diff > 0, or !higher_better and mean_diff < 0
        if (higher_better and mean_diff > 0) or (not higher_better and mean_diff < 0):
            verdict = "SUPPORTED"
        else:
            verdict = "REGRESSES"
    else:
        verdict = "NOT_SIGNIFICANT"

    return {
        "verdict": verdict,
        "n_pairs": n,
        "baseline_mean": float(np.mean(base_v)),
        "framework_mean": float(np.mean(flowa_v)),
        "paired_diff_mean": mean_diff,
        "paired_diff_std": std_diff,
        "paired_diff_se": se_diff,
        "t_statistic": float(t_stat),
        "df": df,
        "ci_95_lower": float(ci_lo),
        "ci_95_upper": float(ci_hi),
        "p_value_raw": p_two_sided,
        "p_value_bonferroni": p_bonf,
        "cohens_d_z": float(cohens_d_z),
        "post_hoc_power_observed": power_obs,
        "post_hoc_power_min_effect": power_min,
        "min_effect_size": min_effect,
        "alpha_bonferroni": alpha_bonferroni,
    }


def write_paired_csv(path: Path, paired_results: list[dict]) -> None:
    fieldnames = [
        "cell", "baseline_arm", "framework_arm", "metric", "nfe",
        "pairing", "higher_better", "baseline_mean", "framework_mean",
        "n_pairs", "paired_diff_mean", "paired_diff_std", "paired_diff_se",
        "t_statistic", "df", "ci_95_lower", "ci_95_upper",
        "p_value_raw", "p_value_bonferroni", "cohens_d_z",
        "post_hoc_power_observed", "post_hoc_power_min_effect",
        "min_effect_size", "alpha_bonferroni", "verdict", "data_source",
    ]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in paired_results:
            higher = "True" if r["metric"] == "plddt_mean" else "False"
            row = {
                "cell": r["cell"],
                "baseline_arm": r["baseline_arm"],
                "framework_arm": "FlowA",
                "metric": "pLDDT" if r["metric"] == "plddt_mean" else "scPerplexity",
                "nfe": r["nfe"],
                "pairing": "paired",
                "higher_better": higher,
                "baseline_mean": r["baseline_mean"],
                "framework_mean": r["framework_mean"],
                "n_pairs": r["n_pairs"],
                "paired_diff_mean": r["paired_diff_mean"],
                "paired_diff_std": r["paired_diff_std"],
                "paired_diff_se": r["paired_diff_se"],
                "t_statistic": r["t_statistic"],
                "df": r["df"],
                "ci_95_lower": r["ci_95_lower"],
                "ci_95_upper": r["ci_95_upper"],
                "p_value_raw": r["p_value_raw"],
                "p_value_bonferroni": r["p_value_bonferroni"],
                "cohens_d_z": r["cohens_d_z"],
                "post_hoc_power_observed": r["post_hoc_power_observed"],
                "post_hoc_power_min_effect": r["post_hoc_power_min_effect"],
                "min_effect_size": r["min_effect_size"],
                "alpha_bonferroni": r["alpha_bonferroni"],
                "verdict": r["verdict"],
                "data_source": (
                    f"verification_outputs/wave197-trackb-{r['baseline_arm'].lower()}-nfe{r['nfe']}-n100.csv "
                    f"+ verification_outputs/wave197-trackb-flowa-nfe{r['nfe']}-n100.csv (paired, n={r['n_pairs']})"
                ),
            }
            w.writerow(row)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--eval-dir", type=Path, default=EVAL_DIR)
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = p.parse_args()

    global EVAL_DIR
    EVAL_DIR = args.eval_dir
    OUT_DIR = args.out_dir
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Eval dir: {EVAL_DIR}")
    print(f"Out dir: {OUT_DIR}")

    # Per-arm aggregation
    all_arm_data = {}
    for arm in ARMS + ["flowa"]:
        print(f"Aggregating {arm}...")
        all_arm_data[arm] = aggregate_per_arm_per_nfe(arm)
        for nfe in NFES:
            d = all_arm_data[arm][nfe]
            if d is None:
                print(f"  nfe={nfe}: NO DATA")
            else:
                print(f"  nfe={nfe}: n_seeds={d['n_seeds']} "
                      f"plddt={d['plddt_mean']:.3f}±{d['plddt_std']:.3f} "
                      f"scperp={d['sc_perplexity_mean']:.3f}±{d['sc_perplexity_std']:.3f}")

    summary_path = OUT_DIR / "wave197-p2-4arm-n100-summary.csv"
    write_summary_csv(summary_path, all_arm_data)
    print(f"\nWrote {summary_path}")

    # Paired power analysis
    paired_results = []
    print("\nRunning paired power analysis (FlowA framework)...")
    for arm in ARMS:
        for nfe in NFES:
            for metric in ["plddt_mean", "sc_perplexity_mean"]:
                cell = f"{arm}_{'pLDDT' if metric == 'plddt_mean' else 'scPerplexity'}_NFE{nfe}"
                print(f"  {cell}...", end=" ")
                r = run_paired_power(arm, nfe, metric)
                r["cell"] = cell
                r["baseline_arm"] = arm
                r["nfe"] = nfe
                r["metric"] = metric
                paired_results.append(r)
                print(f"verdict={r['verdict']} n_pairs={r['n_pairs']} "
                      f"diff={r.get('paired_diff_mean', float('nan')):.4f} "
                      f"p_bonf={r.get('p_value_bonferroni', float('nan')):.2e}")

    paired_path = OUT_DIR / "wave197-p2-4arm-paired.csv"
    write_paired_csv(paired_path, paired_results)
    print(f"Wrote {paired_path}")

    # Verdict distribution
    counts = Counter(r["verdict"] for r in paired_results)
    print(f"\nVerdict distribution: {dict(counts)}")
    return counts


if __name__ == "__main__":
    main()