#!/usr/bin/env python3
"""Wave 202 P5: difficulty-stratified per-record paired t-test on LineageFlow.

Per task spec: target N=1000 per-record paired data at the Wave 202 P3 expected
output paths.

However, the N=1000 lineageflow sweep is BLOCKED-ON-DATA per Wave 200 P2 commit
2bdd905. This script operates on the N=5 smoke subset (the only LineageFlow
per-record data on disk) exactly as Wave 198 P3 and Wave 199 P3 lineageflow
analyses did.

This script:
  1. Resolves the data source (Wave 202 P3 N=1000 path if it exists, else fallback
     to the lineageflow_n1000_omegafold_q4_2026 smoke N=5 data).
  2. Difficulty stratification: hard (baseline_pLDDT <= 33rd pct), medium
     (33rd-67th pct), easy (> 67th pct).
  3. Per-tier paired t-test on plddt_mean + sc_perplexity.
  4. Cohen d_z per tier.
  5. Monotone pattern test (hard > medium > easy in |d_z|).
  6. Bonferroni alpha = 0.05 / 6 = 0.00833 (3 tiers x 2 metrics).
  7. Cross-adapter consistency check vs k6_foldability_w161 (Wave 198 P3):
     - k6 hard d_z = +1.189 (plddt_mean), -1.033 (sc_perplexity)
     - k6 medium d_z = +0.218 (plddt_mean), -1.138 (sc_perplexity)
     - k6 easy d_z = -0.998 (plddt_mean), -1.138 (sc_perplexity)
  8. Saves 2 outputs (CSV + JSON) at wave202-p5-lineageflow-strata.{csv,json}.
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

P3_DIR = REPO_ROOT / "verification_outputs/wave202-p3-lineageflow-n1000"
FALLBACK_DIR = REPO_ROOT / "verification_outputs/lineageflow_n1000_omegafold_q4_2026"

# Bonferroni M = 6 tests per dataset (3 tiers x 2 metrics)
BONFERRONI_M = 6
BONFERRONI_ALPHA = 0.05 / BONFERRONI_M  # 0.00833...

TIER_PERCENTILES = (33.0, 67.0)


def resolve_data_paths() -> tuple[dict, str, str]:
    """Resolve which data dir to use. Returns (paths_dict, source_label, dataset_label)."""
    p3_paths = {
        "baseline_fold": P3_DIR / "baseline/fold/foldability.jsonl",
        "framework_fold": P3_DIR / "framework/fold/foldability.jsonl",
        "baseline_sc": P3_DIR / "baseline/sc/self_consistency.jsonl",
        "framework_sc": P3_DIR / "framework/sc/self_consistency.jsonl",
    }
    if all(p.exists() and p.stat().st_size > 0 for p in p3_paths.values()):
        return p3_paths, "wave202-p3-lineageflow-n1000", "lineageflow_n1000"

    fallback_paths = {
        "baseline_fold": FALLBACK_DIR / "baseline/fold/foldability.jsonl",
        "framework_fold": FALLBACK_DIR / "framework/fold/foldability.jsonl",
        "baseline_sc": FALLBACK_DIR / "baseline/sc/self_consistency.jsonl",
        "framework_sc": FALLBACK_DIR / "framework/sc/self_consistency.jsonl",
    }
    return fallback_paths, "lineageflow_n1000_omegafold_q4_2026_smoke_N5", "lineageflow_n1000"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def compute_tier_assignment(baseline_plddt: np.ndarray) -> tuple[np.ndarray, list[float]]:
    p33, p67 = np.percentile(baseline_plddt, TIER_PERCENTILES)
    boundaries = [float(p33), float(p67)]
    tier_idx = np.zeros(len(baseline_plddt), dtype=int)
    tier_idx[baseline_plddt > p33] = 1
    tier_idx[baseline_plddt > p67] = 2
    return tier_idx, boundaries


def paired_t_test(b: np.ndarray, f: np.ndarray) -> dict:
    n = len(b)
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
    diff = f - b
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


def verdict(result: dict) -> str:
    """Apply Wave 193 P4 verdict precedence: TIE > UNDERPOWERED > SUPPORTED/REGRESSES."""
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
    paths, source_label, dataset_label = resolve_data_paths()
    print("=" * 78)
    print("Wave 202 P5: difficulty-stratified per-record paired t-test on LineageFlow")
    print(f"Source: {source_label}")
    print(f"Bonferroni M={BONFERRONI_M} (3 tiers x 2 metrics), alpha={BONFERRONI_ALPHA:.5f}")
    print("=" * 78)

    base_fold = load_jsonl(paths["baseline_fold"])
    fr_fold = load_jsonl(paths["framework_fold"])
    base_sc = load_jsonl(paths["baseline_sc"])
    fr_sc = load_jsonl(paths["framework_sc"])
    print(f"\n  baseline fold: {len(base_fold)} records")
    print(f"  framework fold: {len(fr_fold)} records")
    print(f"  baseline sc: {len(base_sc)} records")
    print(f"  framework sc: {len(fr_sc)} records")

    # Pair across all 4 sources by qid intersection.
    base_idx = {r["qid"]: r["plddt_mean"] for r in base_fold}
    fr_idx = {r["qid"]: r["plddt_mean"] for r in fr_fold}
    base_sc_idx = {r["qid"]: r["sc_perplexity"] for r in base_sc}
    fr_sc_idx = {r["qid"]: r["sc_perplexity"] for r in fr_sc}
    common_qids = sorted(set(base_idx) & set(fr_idx) & set(base_sc_idx) & set(fr_sc_idx))
    n_paired = len(common_qids)
    print(f"  paired qids: {n_paired}")

    baseline_plddt = np.array([base_idx[q] for q in common_qids], dtype=float)
    framework_plddt = np.array([fr_idx[q] for q in common_qids], dtype=float)
    baseline_scp = np.array([base_sc_idx[q] for q in common_qids], dtype=float)
    framework_scp = np.array([fr_sc_idx[q] for q in common_qids], dtype=float)

    tier_idx, boundaries = compute_tier_assignment(baseline_plddt)
    TIER_LABELS = ["hard", "medium", "easy"]
    print(f"\n  tier boundaries (p33, p67): {boundaries}")
    for t in range(3):
        mask = tier_idx == t
        n_t = int(np.sum(mask))
        if n_t > 0:
            print(
                f"  tier {TIER_LABELS[t]}: n={n_t}  "
                f"baseline_plddt_range=[{float(np.min(baseline_plddt[mask])):.2f}, "
                f"{float(np.max(baseline_plddt[mask])):.2f}]"
            )
        else:
            print(f"  tier {TIER_LABELS[t]}: n=0 (no records)")

    all_results = []
    rows_csv = []

    for t in range(3):
        mask = tier_idx == t
        n_t = int(np.sum(mask))
        if n_t < 2:
            print(f"  tier {TIER_LABELS[t]}: SKIP (n={n_t} < 2)")
            continue

        for metric_name, b, f, direction in [
            ("plddt_mean", baseline_plddt, framework_plddt, "higher_is_better"),
            ("sc_perplexity", baseline_scp, framework_scp, "lower_is_better"),
        ]:
            res = paired_t_test(b[mask], f[mask])
            v = verdict(res)
            print(
                f"  [{TIER_LABELS[t]:>6}] {metric_name} N={res['n_paired']:4d}  "
                f"baseline={res['mean_baseline']:.4f}  framework={res['mean_framework']:.4f}  "
                f"mean_diff={res['mean_diff']:+.6f}  d_z={res['cohens_d_z']:+.4f}  "
                f"p={res['p_value_raw']:.3e}  verdict={v}"
            )
            entry = {
                "dataset": dataset_label,
                "metric": metric_name,
                "tier": TIER_LABELS[t],
                "n_records": res["n_paired"],
                "mean_baseline": res["mean_baseline"],
                "mean_framework": res["mean_framework"],
                "mean_diff": res["mean_diff"],
                "sd_diff": res["sd_diff"],
                "t_statistic": res["t_statistic"],
                "df": res["df"],
                "cohens_d_z": res["cohens_d_z"],
                "p_value_raw": res["p_value_raw"],
                "ci_95_low": res["ci_95"][0],
                "ci_95_high": res["ci_95"][1],
                "verdict": v,
                "tier_boundary_low": boundaries[0],
                "tier_boundary_high": boundaries[1],
                "metric_direction": direction,
                "source": source_label,
            }
            all_results.append(entry)
            rows_csv.append(entry)

    # Monotone pattern test (per metric).
    # For plddt_mean: framework uplift = positive d_z; test |d_z_hard| > |d_z_medium| > |d_z_easy|.
    # For sc_perplexity: framework uplift = negative d_z (lower=better); test |d_z_hard| > |d_z_medium| > |d_z_easy|.
    pattern = {}
    for metric in ("plddt_mean", "sc_perplexity"):
        tier_dz = {lbl: None for lbl in TIER_LABELS}
        for r in all_results:
            if r["metric"] == metric:
                tier_dz[r["tier"]] = r["cohens_d_z"]
        h, m, e = tier_dz["hard"], tier_dz["medium"], tier_dz["easy"]
        abs_hard = abs(h) if h is not None else None
        abs_med = abs(m) if m is not None else None
        abs_easy = abs(e) if e is not None else None
        monotone = (
            abs_hard is not None
            and abs_med is not None
            and abs_easy is not None
            and abs_hard > abs_med > abs_easy
        )
        pattern[metric] = {
            "hard_d_z": h,
            "medium_d_z": m,
            "easy_d_z": e,
            "abs_hard": abs_hard,
            "abs_medium": abs_med,
            "abs_easy": abs_easy,
            "monotone_decrease_in_abs_dz_with_ease": monotone,
        }

    hard_dz = pattern["plddt_mean"]["hard_d_z"]
    med_dz = pattern["plddt_mean"]["medium_d_z"]
    easy_dz = pattern["plddt_mean"]["easy_d_z"]
    sc_hard = pattern["sc_perplexity"]["hard_d_z"]
    sc_med = pattern["sc_perplexity"]["medium_d_z"]
    sc_easy = pattern["sc_perplexity"]["easy_d_z"]

    # For plddt_mean, framework uplift = positive d_z; check d_z_hard > d_z_medium > d_z_easy.
    monotone_increase_pos = (
        hard_dz is not None
        and med_dz is not None
        and easy_dz is not None
        and hard_dz > med_dz > easy_dz
    )
    # For sc_perplexity, framework uplift = negative d_z; check d_z_hard < d_z_medium < d_z_easy.
    monotone_increase_neg = (
        sc_hard is not None
        and sc_med is not None
        and sc_easy is not None
        and sc_hard < sc_med < sc_easy
    )
    monotone_increase = monotone_increase_pos and monotone_increase_neg

    # Reference: k6_foldability_w161 from Wave 198 P3.
    k6_w198_p3 = {
        "plddt_mean": {
            "hard_d_z": 1.1889349923927075,
            "medium_d_z": 0.2181142515180313,
            "easy_d_z": -0.998239425515868,
            "monotone_increase": True,
        },
        "sc_perplexity": {
            "hard_d_z": -1.0332592299564876,
            "medium_d_z": -1.1379913712528409,
            "easy_d_z": -1.1378411040984453,
            "monotone_increase": False,
        },
    }

    print("\n" + "=" * 78)
    print("Monotone pattern summary (LineageFlow)")
    print("=" * 78)
    for metric, p in pattern.items():
        print(
            f"  {metric}: hard d_z={p['hard_d_z']}, medium={p['medium_d_z']}, easy={p['easy_d_z']}"
        )
        print(
            f"    |d_z_hard|={p['abs_hard']}, |d_z_med|={p['abs_medium']}, |d_z_easy|={p['abs_easy']}"
        )
        print(
            f"    monotone_decrease_in_abs_dz_with_ease = {p['monotone_decrease_in_abs_dz_with_ease']}"
        )
    print(f"\n  BOTH metrics monotone (hard > medium > easy in |d_z|): {monotone_increase}")

    # Cross-adapter consistency: per task spec, compare to k6 hard/medium/easy d_z
    # 1.189 / 0.218 / -0.998 (plddt_mean).
    cross_adapter = {
        "k6_hard_d_z": 1.189,
        "k6_medium_d_z": 0.218,
        "k6_easy_d_z": -0.998,
        "lineageflow_hard_d_z": hard_dz if hard_dz is not None else None,
        "lineageflow_medium_d_z": med_dz if med_dz is not None else None,
        "lineageflow_easy_d_z": easy_dz if easy_dz is not None else None,
        "monotone_pattern_confirmed": monotone_increase_pos,
        "hard_d_z_positive": (hard_dz is not None and not math.isnan(hard_dz) and hard_dz > 0),
        "comparison_status": (
            "VACUOUS — LineageFlow N=5 smoke data has identical baseline/framework values; "
            "monotone pattern not testable at N=5"
            if (hard_dz == 0.0 and med_dz in (0.0, None) and easy_dz in (0.0, None))
            else "TESTABLE"
        ),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = OUT_DIR / "wave202-p5-lineageflow-strata.csv"
    fieldnames = [
        "dataset",
        "metric",
        "tier",
        "n_records",
        "mean_baseline",
        "mean_framework",
        "mean_diff",
        "sd_diff",
        "t_statistic",
        "df",
        "cohens_d_z",
        "p_value_raw",
        "ci_95_low",
        "ci_95_high",
        "verdict",
        "tier_boundary_low",
        "tier_boundary_high",
        "metric_direction",
    ]
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows_csv:
            w.writerow({k: row.get(k, "") for k in fieldnames})
    print(f"\nWrote {csv_path}")

    json_path = OUT_DIR / "wave202-p5-lineageflow-strata.json"
    json_path.write_text(
        json.dumps(
            {
                "difficulty_stratified_results": all_results,
                "tier_boundaries_percentiles": list(TIER_PERCENTILES),
                "tier_boundaries_values": boundaries,
                "bonferroni_M": BONFERRONI_M,
                "bonferroni_alpha": BONFERRONI_ALPHA,
                "method": (
                    "Per-record difficulty stratification: assign each record to hard/medium/easy tier "
                    "based on baseline_pLDDT percentile (33rd and 67th percentiles). "
                    "Per tier, run paired t-test (framework vs baseline) on plddt_mean and sc_perplexity. "
                    "Bonferroni alpha = 0.05 / 6 = 0.00833 (3 tiers x 2 metrics per dataset)."
                ),
                "monotone_pattern_per_metric": pattern,
                "monotone_pattern_global": {
                    "plddt_hard_d_z": hard_dz,
                    "plddt_medium_d_z": med_dz,
                    "plddt_easy_d_z": easy_dz,
                    "plddt_monotone_increase": monotone_increase_pos,
                    "sc_hard_d_z": sc_hard,
                    "sc_medium_d_z": sc_med,
                    "sc_easy_d_z": sc_easy,
                    "sc_monotone_increase": monotone_increase_neg,
                    "both_metrics_monotone": monotone_increase,
                },
                "difficulty_uplift_pattern": {
                    "hard_d_z": hard_dz,
                    "medium_d_z": med_dz,
                    "easy_d_z": easy_dz,
                    "monotone_increase": monotone_increase,
                },
                "cross_adapter_consistency_vs_k6_w161": cross_adapter,
                "k6_foldability_w161_wave198_p3_reference": k6_w198_p3,
                "source": source_label,
                "n_paired_actual": n_paired,
                "wave198_p3_lineageflow_reference": {
                    "plddt_hard_d_z": 0.0,
                    "plddt_medium_d_z": None,
                    "plddt_easy_d_z": 0.0,
                    "sc_hard_d_z": 0.0,
                    "sc_medium_d_z": None,
                    "sc_easy_d_z": 0.0,
                    "verdict": "TIE on hard and easy, medium tier SKIP (n=1)",
                },
                "wave199_p3_lineageflow_reference": {
                    "plddt_hard_d_z": 0.0,
                    "plddt_medium_d_z": None,
                    "plddt_easy_d_z": 0.0,
                    "sc_hard_d_z": 0.0,
                    "sc_medium_d_z": None,
                    "sc_easy_d_z": 0.0,
                    "verdict": "TIE on hard and easy, medium tier SKIP (n=1)",
                },
                "blocked_on_data_note": (
                    "LineageFlow N=1000 sweep was BLOCKED-ON-DATA on GPU per Wave 200 P2 commit "
                    "(2bdd905: torch 1.13.1 vs Blackwell sm_120). Wave 202 P2 smoke test PASS on "
                    "Blackwell sm_120 (40c70a7) confirmed the pipeline works, but the full N=1000 "
                    "sweep was not re-run after the GPU environment fix. The N=5 smoke data is the "
                    "only LineageFlow per-record paired data on disk. This Wave 202 P5 strata result "
                    "therefore operates on N=5 (df=4) smoke data, identical to Wave 198 P3 and Wave 199 "
                    "P3 lineageflow entries: hard n=2, medium n=1 (SKIP), easy n=2. Cross-adapter "
                    "consistency check vs k6_foldability_w161 is therefore VACUOUS."
                ),
                "csv_path": str(csv_path),
                "json_path": str(json_path),
            },
            indent=2,
            default=str,
        )
    )
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
