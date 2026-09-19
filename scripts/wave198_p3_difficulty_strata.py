#!/usr/bin/env python3
"""Wave 198 P3: difficulty-stratified per-record paired t-test.

Loads per-record foldability.jsonl + self_consistency.jsonl from two datasets
  - k6_foldability_n1000_w161_q3_2026 (N=1000, paired by qid)
  - lineageflow_n1000_omegafold_q4_2026 (N=5 smoke subset, paired by qid)

For each dataset:
  1. Compute baseline_pLDDT percentile rank (per-record).
  2. Stratify into 3 tiers: hard (<=33rd pct), medium (33-67), easy (>67).
  3. Per tier: paired t-test framework vs baseline on plddt_mean + sc_perplexity.
  4. Compute Cohen d_z per tier.
  5. Verdict per tier.

Specifically test: does framework_uplift (Cohen d_z) monotonically INCREASE with
seed difficulty? Theory: restart-blend helps difficult records more (framework
value-add lives at the difficult-seed level).
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

# Wave 193 P4 verdict precedence: TIE > UNDERPOWERED > SUPPORTED/REGRESSES > NOT_SIG
# Bonferroni M = 6 tests per dataset (3 tiers x 2 metrics) to control for tier stratification
BONFERRONI_M = 6  # 3 tiers x 2 metrics
BONFERRONI_ALPHA = 0.05 / BONFERRONI_M  # 0.00833...

TIER_PERCENTILES = (33.0, 67.0)  # hard <=33, medium 33-67, easy >67


DATASETS = [
    {
        "dataset": "k6_foldability_w161",
        "baseline_fold": REPO_ROOT / "verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl",
        "framework_fold": REPO_ROOT / "verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability/foldability.jsonl",
        "baseline_sc": REPO_ROOT / "verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/self_consistency.jsonl",
        "framework_sc": REPO_ROOT / "verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability/self_consistency.jsonl",
    },
    {
        "dataset": "lineageflow_omegafold",
        "baseline_fold": REPO_ROOT / "verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/fold/foldability.jsonl",
        "framework_fold": REPO_ROOT / "verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/fold/foldability.jsonl",
        "baseline_sc": REPO_ROOT / "verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/sc/self_consistency.jsonl",
        "framework_sc": REPO_ROOT / "verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/sc/self_consistency.jsonl",
    },
]


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def compute_tier_assignment(baseline_plddt: np.ndarray) -> tuple[np.ndarray, list[int]]:
    """Assign tiers based on baseline_pLDDT percentile rank.

    Returns:
        tier_idx: array of length N (0=hard, 1=medium, 2=easy)
        boundaries: list of percentile boundary values used
    """
    p33, p67 = np.percentile(baseline_plddt, TIER_PERCENTILES)
    boundaries = [float(p33), float(p67)]
    tier_idx = np.zeros(len(baseline_plddt), dtype=int)
    tier_idx[baseline_plddt > p33] = 1
    tier_idx[baseline_plddt > p67] = 2
    return tier_idx, boundaries


def paired_t_test(b: np.ndarray, f: np.ndarray) -> dict:
    diff = f - b
    n = len(diff)
    if n < 2:
        return {
            "n_paired": int(n),
            "mean_baseline": float(np.mean(b)) if n > 0 else float("nan"),
            "mean_framework": float(np.mean(f)) if n > 0 else float("nan"),
            "mean_diff": float("nan"),
            "sd_diff": float("nan"),
            "t_statistic": float("nan"),
            "df": int(max(0, n - 1)),
            "p_value_raw": float("nan"),
            "cohens_d_z": float("nan"),
            "ci_95": [float("nan"), float("nan")],
        }
    mean_b = float(np.mean(b))
    mean_f = float(np.mean(f))
    mean_diff = float(np.mean(diff))
    sd_diff = float(np.std(diff, ddof=1))
    se = sd_diff / math.sqrt(n)
    df = n - 1
    if sd_diff == 0.0:
        t_stat = float("inf") if mean_diff > 0 else (float("-inf") if mean_diff < 0 else 0.0)
        p_raw = 0.0 if mean_diff != 0 else 1.0
        d_z = 0.0
    else:
        t_stat = mean_diff / se
        p_raw = float(2.0 * scipy.stats.t.sf(abs(t_stat), df=df))
        d_z = mean_diff / sd_diff
    ci_lo = mean_diff - 1.96 * se
    ci_hi = mean_diff + 1.96 * se
    return {
        "n_paired": int(n),
        "mean_baseline": mean_b,
        "mean_framework": mean_f,
        "mean_diff": mean_diff,
        "sd_diff": sd_diff,
        "t_statistic": float(t_stat),
        "df": int(df),
        "p_value_raw": p_raw,
        "cohens_d_z": float(d_z),
        "ci_95": [float(ci_lo), float(ci_hi)],
    }


def verdict(result: dict, lower_is_better_metric: bool = False) -> str:
    """Apply Wave 193 P4 verdict precedence.

    lower_is_better_metric=True for sc_perplexity (lower = better fit, so
    negative d_z = framework-WINS, but verdict string follows t-sign).
    """
    p = result["p_value_raw"]
    d = result["cohens_d_z"]
    n = result["n_paired"]
    if n < 2:
        return "UNDERPOWERED"
    if math.isnan(p) or math.isnan(d):
        return "UNDERPOWERED"
    if p < BONFERRONI_ALPHA:
        if d > 0:
            return "SUPPORTED"
        if d < 0:
            return "REGRESSES"
    # TIE precedence over UNDERPOWERED per Wave 193 P4
    if abs(d) < 0.05:
        return "TIE"
    return "UNDERPOWERED"


def main() -> int:
    all_results = []
    rows_csv = []
    print("=" * 78)
    print("Wave 198 P3: difficulty-stratified per-record paired t-test")
    print(f"Bonferroni M={BONFERRONI_M} (3 tiers x 2 metrics), alpha={BONFERRONI_ALPHA:.5f}")
    print("=" * 78)

    TIER_LABELS = ["hard", "medium", "easy"]

    for ds in DATASETS:
        print(f"\nDataset: {ds['dataset']}")
        b_fold = load_jsonl(ds["baseline_fold"])
        f_fold = load_jsonl(ds["framework_fold"])
        b_sc = load_jsonl(ds["baseline_sc"])
        f_sc = load_jsonl(ds["framework_sc"])
        print(f"  baseline foldability: {len(b_fold)} records")
        print(f"  framework foldability: {len(f_fold)} records")
        print(f"  baseline sc: {len(b_sc)} records")
        print(f"  framework sc: {len(f_sc)} records")

        # Build paired arrays by qid for each metric.
        # Get baseline plddt first (this drives tier assignment).
        base_idx = {r["qid"]: r["plddt_mean"] for r in b_fold}
        fr_fold_idx = {r["qid"]: r["plddt_mean"] for r in f_fold}
        base_sc_idx = {r["qid"]: r["sc_perplexity"] for r in b_sc}
        fr_sc_idx = {r["qid"]: r["sc_perplexity"] for r in f_sc}
        common_qids = sorted(set(base_idx) & set(fr_fold_idx) & set(base_sc_idx) & set(fr_sc_idx))
        print(f"  paired qids: {len(common_qids)}")

        baseline_plddt = np.array([base_idx[q] for q in common_qids], dtype=float)
        framework_plddt = np.array([fr_fold_idx[q] for q in common_qids], dtype=float)
        baseline_scp = np.array([base_sc_idx[q] for q in common_qids], dtype=float)
        framework_scp = np.array([fr_sc_idx[q] for q in common_qids], dtype=float)

        tier_idx, boundaries = compute_tier_assignment(baseline_plddt)
        print(f"  tier boundaries (p33, p67): {boundaries}")
        for t in range(3):
            mask = tier_idx == t
            n_t = int(np.sum(mask))
            plddt_min = float(np.min(baseline_plddt[mask])) if n_t > 0 else float("nan")
            plddt_max = float(np.max(baseline_plddt[mask])) if n_t > 0 else float("nan")
            print(f"  tier {TIER_LABELS[t]}: n={n_t} baseline_plddt_range=[{plddt_min:.2f}, {plddt_max:.2f}]")

        # Per-tier paired t-test for both metrics
        for t in range(3):
            mask = tier_idx == t
            n_t = int(np.sum(mask))
            if n_t < 2:
                print(f"  tier {TIER_LABELS[t]}: SKIP (n={n_t} < 2)")
                continue

            # plddt_mean in this tier
            res_plddt = paired_t_test(baseline_plddt[mask], framework_plddt[mask])
            v_plddt = verdict(res_plddt)
            print(
                f"  [{TIER_LABELS[t]:>6}] plddt_mean  N={res_plddt['n_paired']:4d}  "
                f"baseline={res_plddt['mean_baseline']:.4f}  framework={res_plddt['mean_framework']:.4f}  "
                f"mean_diff={res_plddt['mean_diff']:+.6f}  d_z={res_plddt['cohens_d_z']:+.4f}  "
                f"p={res_plddt['p_value_raw']:.3e}  verdict={v_plddt}"
            )
            entry = {
                "dataset": ds["dataset"],
                "metric": "plddt_mean",
                "tier": TIER_LABELS[t],
                "n_records": res_plddt["n_paired"],
                "mean_baseline": res_plddt["mean_baseline"],
                "mean_framework": res_plddt["mean_framework"],
                "mean_diff": res_plddt["mean_diff"],
                "sd_diff": res_plddt["sd_diff"],
                "t_statistic": res_plddt["t_statistic"],
                "df": res_plddt["df"],
                "cohens_d_z": res_plddt["cohens_d_z"],
                "p_value_raw": res_plddt["p_value_raw"],
                "ci_95_low": res_plddt["ci_95"][0],
                "ci_95_high": res_plddt["ci_95"][1],
                "verdict": v_plddt,
                "tier_boundary_low": boundaries[0],
                "tier_boundary_high": boundaries[1],
                "metric_direction": "higher_is_better",
            }
            all_results.append(entry)
            rows_csv.append(entry)

            # sc_perplexity in this tier
            res_sc = paired_t_test(baseline_scp[mask], framework_scp[mask])
            v_sc = verdict(res_sc, lower_is_better_metric=True)
            print(
                f"  [{TIER_LABELS[t]:>6}] sc_perplex  N={res_sc['n_paired']:4d}  "
                f"baseline={res_sc['mean_baseline']:.4f}  framework={res_sc['mean_framework']:.4f}  "
                f"mean_diff={res_sc['mean_diff']:+.6f}  d_z={res_sc['cohens_d_z']:+.4f}  "
                f"p={res_sc['p_value_raw']:.3e}  verdict={v_sc}"
            )
            entry = {
                "dataset": ds["dataset"],
                "metric": "sc_perplexity",
                "tier": TIER_LABELS[t],
                "n_records": res_sc["n_paired"],
                "mean_baseline": res_sc["mean_baseline"],
                "mean_framework": res_sc["mean_framework"],
                "mean_diff": res_sc["mean_diff"],
                "sd_diff": res_sc["sd_diff"],
                "t_statistic": res_sc["t_statistic"],
                "df": res_sc["df"],
                "cohens_d_z": res_sc["cohens_d_z"],
                "p_value_raw": res_sc["p_value_raw"],
                "ci_95_low": res_sc["ci_95"][0],
                "ci_95_high": res_sc["ci_95"][1],
                "verdict": v_sc,
                "tier_boundary_low": boundaries[0],
                "tier_boundary_high": boundaries[1],
                "metric_direction": "lower_is_better",
            }
            all_results.append(entry)
            rows_csv.append(entry)

    # Determine monotone_increase pattern (hard > medium > easy) for each dataset+metric
    # For plddt_mean: positive d_z is framework improvement, so hard > medium > easy in d_z
    # For sc_perplexity: negative d_z is framework improvement (lower=better), so hard < medium < easy in d_z (i.e., more negative)
    # We test: does |d_z| increase with difficulty? (theory: framework uplift increases with difficulty)
    pattern_results = {}
    for ds in DATASETS:
        for metric in ("plddt_mean", "sc_perplexity"):
            tier_dz = {t: None for t in TIER_LABELS}
            for r in all_results:
                if r["dataset"] == ds["dataset"] and r["metric"] == metric:
                    tier_dz[r["tier"]] = r["cohens_d_z"]
            hard_d = tier_dz["hard"]
            med_d = tier_dz["medium"]
            easy_d = tier_dz["easy"]
            # For plddt_mean: framework uplift is positive d_z; expect |d_z_hard| > |d_z_easy|
            # For sc_perplexity: framework uplift is negative d_z; expect |d_z_hard| > |d_z_easy| (more negative = bigger uplift)
            # We test: does |d_z| monotonically decrease as tier gets easier?
            abs_diffs = [abs(d) if d is not None else None for d in (hard_d, med_d, easy_d)]
            monotone_decrease = (
                abs_diffs[0] is not None
                and abs_diffs[1] is not None
                and abs_diffs[2] is not None
                and abs_diffs[0] > abs_diffs[1] > abs_diffs[2]
            )
            pattern_results[f"{ds['dataset']}|{metric}"] = {
                "hard_d_z": hard_d,
                "medium_d_z": med_d,
                "easy_d_z": easy_d,
                "abs_hard": abs_diffs[0],
                "abs_medium": abs_diffs[1],
                "abs_easy": abs_diffs[2],
                "monotone_decrease_in_abs_dz_with_ease": monotone_decrease,
            }

    # Determine global monotone pattern per dataset using plddt_mean (the cleaner signal)
    global_pattern = {}
    for ds in DATASETS:
        ds_label = ds["dataset"]
        ds_patterns = {k: v for k, v in pattern_results.items() if k.startswith(ds_label)}
        hard_dz = ds_patterns.get(f"{ds_label}|plddt_mean", {}).get("hard_d_z")
        med_dz = ds_patterns.get(f"{ds_label}|plddt_mean", {}).get("medium_d_z")
        easy_dz = ds_patterns.get(f"{ds_label}|plddt_mean", {}).get("easy_d_z")
        # For plddt_mean, framework uplift = positive d_z; check if d_z_hard > d_z_medium > d_z_easy
        monotone_increase_positive = (
            hard_dz is not None
            and med_dz is not None
            and easy_dz is not None
            and hard_dz > med_dz > easy_dz
        )
        sc_pattern = ds_patterns.get(f"{ds_label}|sc_perplexity", {})
        hard_dz_sc = sc_pattern.get("hard_d_z")
        med_dz_sc = sc_pattern.get("medium_d_z")
        easy_dz_sc = sc_pattern.get("easy_d_z")
        # For sc_perplexity, framework uplift = negative d_z; check if d_z_hard < d_z_medium < d_z_easy
        monotone_increase_negative = (
            hard_dz_sc is not None
            and med_dz_sc is not None
            and easy_dz_sc is not None
            and hard_dz_sc < med_dz_sc < easy_dz_sc
        )
        global_pattern[ds_label] = {
            "plddt_hard_d_z": hard_dz,
            "plddt_medium_d_z": med_dz,
            "plddt_easy_d_z": easy_dz,
            "plddt_monotone_increase": monotone_increase_positive,
            "sc_hard_d_z": hard_dz_sc,
            "sc_medium_d_z": med_dz_sc,
            "sc_easy_d_z": easy_dz_sc,
            "sc_monotone_increase": monotone_increase_negative,
            "both_metrics_monotone": monotone_increase_positive and monotone_increase_negative,
        }

    # Write CSV
    csv_path = OUT_DIR / "wave198-p3-difficulty-strata.csv"
    fieldnames = [
        "dataset", "metric", "tier", "n_records", "mean_baseline", "mean_framework",
        "mean_diff", "sd_diff", "t_statistic", "df", "cohens_d_z", "p_value_raw",
        "ci_95_low", "ci_95_high", "verdict", "tier_boundary_low", "tier_boundary_high",
        "metric_direction",
    ]
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows_csv:
            w.writerow(row)
    print(f"\nWrote {csv_path}")

    # Write JSON
    json_out = {
        "difficulty_stratified_results": all_results,
        "tier_boundaries_percentiles": TIER_PERCENTILES,
        "bonferroni_M": BONFERRONI_M,
        "bonferroni_alpha": BONFERRONI_ALPHA,
        "method": (
            "Per-record difficulty stratification: assign each record to hard/medium/easy tier "
            "based on baseline_pLDDT percentile (33rd and 67th percentiles). "
            "Per tier, run paired t-test (framework vs baseline) on plddt_mean and sc_perplexity. "
            "Bonferroni alpha = 0.05 / 6 = 0.00833 (3 tiers x 2 metrics per dataset)."
        ),
        "monotone_pattern_per_dataset_metric": pattern_results,
        "monotone_pattern_summary_per_dataset": global_pattern,
        "wave198_p2_context": {
            "k6_foldability_w161": {
                "plddt_mean_overall": {"mean_diff": 1.123, "d_z": 0.071, "verdict": "UNDERPOWERED"},
                "sc_perplexity_overall": {"mean_diff": -3.917, "d_z": -1.077, "verdict": "REGRESSES (lower=better, framework wins)"},
            },
            "lineageflow_omegafold": {
                "plddt_mean_overall": {"mean_diff": 0.0, "d_z": 0.0, "verdict": "TIE"},
                "sc_perplexity_overall": {"mean_diff": 0.0, "d_z": 0.0, "verdict": "TIE"},
            },
        },
        "theory_test": (
            "Theory: restart-blend helps difficult records more (framework value-add lives at "
            "difficult-seed level). Predicted pattern: framework_uplift (|d_z|) INCREASES with "
            "seed difficulty, i.e., |d_z_hard| > |d_z_medium| > |d_z_easy|. "
            "If monotone_increase holds for both metrics, this confirms Wave 197 P3 honest "
            "finding that framework value-add lives at the difficult-seed level."
        ),
        "csv_path": "verification_outputs/wave198-p3-difficulty-strata.csv",
        "json_path": "verification_outputs/wave198-p3-difficulty-strata.json",
    }
    json_path = OUT_DIR / "wave198-p3-difficulty-strata.json"
    with json_path.open("w") as f:
        json.dump(json_out, f, indent=2, default=str)
    print(f"Wrote {json_path}")

    # Print summary
    print("\n" + "=" * 78)
    print("Summary: monotone pattern per dataset")
    print("=" * 78)
    for ds_label, pat in global_pattern.items():
        print(f"\n{ds_label}:")
        h = pat['plddt_hard_d_z']
        m = pat['plddt_medium_d_z']
        e = pat['plddt_easy_d_z']
        h_str = f"{h:+.4f}" if h is not None else "  N/A  "
        m_str = f"{m:+.4f}" if m is not None else "  N/A  "
        e_str = f"{e:+.4f}" if e is not None else "  N/A  "
        print(f"  plddt_mean:    hard d_z={h_str}  medium={m_str}  easy={e_str}  monotone_increase={pat['plddt_monotone_increase']}")
        h = pat['sc_hard_d_z']
        m = pat['sc_medium_d_z']
        e = pat['sc_easy_d_z']
        h_str = f"{h:+.4f}" if h is not None else "  N/A  "
        m_str = f"{m:+.4f}" if m is not None else "  N/A  "
        e_str = f"{e:+.4f}" if e is not None else "  N/A  "
        print(f"  sc_perplexity: hard d_z={h_str}  medium={m_str}  easy={e_str}  monotone_increase={pat['sc_monotone_increase']}")
        print(f"  both metrics monotone: {pat['both_metrics_monotone']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
