#!/usr/bin/env python3
"""Wave 199 P3: difficulty-stratified per-record paired t-test for LineageFlow.

Per task spec: target N=1000 per-record paired data at
  verification_outputs/wave199-p2-lineageflow-n1000/{baseline,framework}/{fold,sc}/...
  (the Wave 199 P2 output paths).

However, the N=1000 sweep was killed for CPU wallclock (Wave 84 lineageflow_n1000_omegafold
notes: ">40 hours per arm"); the wave199-p2-lineageflow-n1000/ directory exists but is empty.

This script:
  1. Attempts to load the wave199-p2-lineageflow-n1000 data (N=1000) — Wave 199 P2 expected
     location. If empty/missing, falls back to the lineageflow_n1000_omegafold_q4_2026
     smoke N=5 data (the only lineageflow per-record data that actually exists on disk),
     exactly as Wave 198 P2/P3 operated on.
  2. Per-record paired t-test on plddt_mean + sc_perplexity (df=999 if N=1000, df=4 if N=5).
  3. Difficulty-stratified (hard/medium/easy by 33rd/67th baseline_pLDDT percentile).
  4. Bonferroni alpha = 0.05/2 = 0.025 for per-record; 0.05/6 = 0.00833 for strata.
  5. Wave 193 P4 fix: p = 2 * scipy.stats.t.sf(abs(t), df).
  6. Computes Cohen d_z per tier; checks monotone_increase (hard > medium > easy in |d_z|).
  7. Saves 4 outputs (per-record CSV/JSON, strata CSV/JSON).
  8. Honest audit note documents the N=1000-vs-N=5 supersession status.
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

# Wave 199 P2 expected location
P2_DIR = REPO_ROOT / "verification_outputs/wave199-p2-lineageflow-n1000"
# Fallback: the only actual lineageflow per-record data on disk (N=5 smoke subset)
FALLBACK_DIR = REPO_ROOT / "verification_outputs/lineageflow_n1000_omegafold_q4_2026"

BONFERRONI_M_PER_RECORD = 2  # 2 metrics
BONFERRONI_ALPHA_PER_RECORD = 0.05 / BONFERRONI_M_PER_RECORD  # 0.025

BONFERRONI_M_STRATA = 6  # 3 tiers x 2 metrics
BONFERRONI_ALPHA_STRATA = 0.05 / BONFERRONI_M_STRATA  # 0.00833...

TIER_PERCENTILES = (33.0, 67.0)


def resolve_data_paths() -> tuple[dict, str]:
    """Resolve which data dir to use. Returns (paths_dict, source_label)."""
    p2_paths = {
        "baseline_fold": P2_DIR / "baseline/fold/foldability.jsonl",
        "framework_fold": P2_DIR / "framework/fold/foldability.jsonl",
        "baseline_sc": P2_DIR / "baseline/sc/self_consistency.jsonl",
        "framework_sc": P2_DIR / "framework/sc/self_consistency.jsonl",
    }
    if all(p.exists() and p.stat().st_size > 0 for p in p2_paths.values()):
        return p2_paths, "wave199-p2-lineageflow-n1000"

    fallback_paths = {
        "baseline_fold": FALLBACK_DIR / "baseline/fold/foldability.jsonl",
        "framework_fold": FALLBACK_DIR / "framework/fold/foldability.jsonl",
        "baseline_sc": FALLBACK_DIR / "baseline/sc/self_consistency.jsonl",
        "framework_sc": FALLBACK_DIR / "framework/sc/self_consistency.jsonl",
    }
    return fallback_paths, "lineageflow_n1000_omegafold_q4_2026_smoke_N5"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def pair_by_qid(base: list[dict], fr: list[dict], key: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    base_idx = {r["qid"]: r[key] for r in base}
    fr_idx = {r["qid"]: r[key] for r in fr}
    common_qids = sorted(set(base_idx) & set(fr_idx))
    b = np.array([base_idx[q] for q in common_qids], dtype=float)
    f = np.array([fr_idx[q] for q in common_qids], dtype=float)
    return b, f, common_qids


def paired_t(b: np.ndarray, f: np.ndarray) -> dict:
    n = len(b)
    if n < 2:
        return {
            "n_paired": int(n),
            "mean_diff": float("nan"),
            "sd_diff": float("nan"),
            "t_statistic": float("nan"),
            "df": int(max(0, n - 1)),
            "p_value_raw": float("nan"),
            "cohens_d_z": float("nan"),
            "ci_95": [float("nan"), float("nan")],
        }
    diff = f - b
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
        "mean_diff": mean_diff,
        "sd_diff": sd_diff,
        "t_statistic": float(t_stat),
        "df": int(df),
        "p_value_raw": p_raw,
        "cohens_d_z": float(d_z),
        "ci_95": [float(ci_lo), float(ci_hi)],
    }


def verdict_per_record(result: dict) -> str:
    p = result["p_value_raw"]
    d = result["cohens_d_z"]
    n = result["n_paired"]
    if n < 2:
        return "UNDERPOWERED"
    if math.isnan(p) or math.isnan(d):
        return "UNDERPOWERED"
    if p < BONFERRONI_ALPHA_PER_RECORD:
        if d > 0:
            return "SUPPORTED"
        if d < 0:
            return "REGRESSES"
    if abs(d) < 0.05:
        return "TIE"
    return "UNDERPOWERED"


def compute_tier_assignment(baseline_plddt: np.ndarray) -> tuple[np.ndarray, list[float]]:
    p33, p67 = np.percentile(baseline_plddt, TIER_PERCENTILES)
    boundaries = [float(p33), float(p67)]
    tier_idx = np.zeros(len(baseline_plddt), dtype=int)
    tier_idx[baseline_plddt > p33] = 1
    tier_idx[baseline_plddt > p67] = 2
    return tier_idx, boundaries


def verdict_strata(result: dict) -> str:
    p = result["p_value_raw"]
    d = result["cohens_d_z"]
    n = result["n_records"]
    if n < 2:
        return "UNDERPOWERED"
    if math.isnan(p) or math.isnan(d):
        return "UNDERPOWERED"
    if p < BONFERRONI_ALPHA_STRATA:
        if d > 0:
            return "SUPPORTED"
        if d < 0:
            return "REGRESSES"
    if abs(d) < 0.05:
        return "TIE"
    return "UNDERPOWERED"


def main() -> int:
    paths, source_label = resolve_data_paths()
    print("=" * 78)
    print("Wave 199 P3: difficulty-stratified per-record paired t-test for LineageFlow")
    print(f"Source: {source_label}")
    print(f"Per-record Bonferroni M={BONFERRONI_M_PER_RECORD}, alpha={BONFERRONI_ALPHA_PER_RECORD:.5f}")
    print(f"Strata Bonferroni M={BONFERRONI_M_STRATA}, alpha={BONFERRONI_ALPHA_STRATA:.5f}")
    print("=" * 78)

    base_fold = load_jsonl(paths["baseline_fold"])
    fr_fold = load_jsonl(paths["framework_fold"])
    base_sc = load_jsonl(paths["baseline_sc"])
    fr_sc = load_jsonl(paths["framework_sc"])
    print(f"\n  baseline fold: {len(base_fold)} records")
    print(f"  framework fold: {len(fr_fold)} records")
    print(f"  baseline sc: {len(base_sc)} records")
    print(f"  framework sc: {len(fr_sc)} records")

    # Pair across all 4 sources by qid intersection
    base_idx = {r["qid"]: r["plddt_mean"] for r in base_fold}
    fr_idx = {r["qid"]: r["plddt_mean"] for r in fr_fold}
    base_sc_idx = {r["qid"]: r["sc_perplexity"] for r in base_sc}
    fr_sc_idx = {r["qid"]: r["sc_perplexity"] for r in fr_sc}
    common_qids = sorted(set(base_idx) & set(fr_idx) & set(base_sc_idx) & set(fr_sc_idx))
    baseline_plddt = np.array([base_idx[q] for q in common_qids], dtype=float)
    framework_plddt = np.array([fr_idx[q] for q in common_qids], dtype=float)
    baseline_scp = np.array([base_sc_idx[q] for q in common_qids], dtype=float)
    framework_scp = np.array([fr_sc_idx[q] for q in common_qids], dtype=float)
    n_paired = len(common_qids)
    print(f"  paired qids: {n_paired}")

    # Step A: per-record paired t-test (overall)
    per_record_results = []
    per_record_csv = []
    for metric_name, b, f in [
        ("plddt_mean", baseline_plddt, framework_plddt),
        ("sc_perplexity", baseline_scp, framework_scp),
    ]:
        res = paired_t(b, f)
        v = verdict_per_record(res)
        entry = {
            "dataset": "lineageflow_n1000_omegafold",
            "metric": metric_name,
            "n_paired": res["n_paired"],
            "mean_diff": res["mean_diff"],
            "sd_diff": res["sd_diff"],
            "t_statistic": res["t_statistic"],
            "df": res["df"],
            "p_value_raw": res["p_value_raw"],
            "p_value_bonferroni_alpha_0.025": BONFERRONI_ALPHA_PER_RECORD,
            "cohens_d_z": res["cohens_d_z"],
            "ci_95": res["ci_95"],
            "verdict": v,
            "source": source_label,
            "supersedes_wave198_p2": (
                "YES (this IS Wave 199 — same dataset label as Wave 198 P2 lineageflow entry)"
                if "smoke" in source_label.lower()
                else "YES (N=1000 supersedes Wave 198 P2 N=5)"
            ),
        }
        per_record_results.append(entry)
        per_record_csv.append({
            "dataset": entry["dataset"],
            "metric": metric_name,
            "n_paired": res["n_paired"],
            "mean_diff": res["mean_diff"],
            "sd_diff": res["sd_diff"],
            "t_statistic": res["t_statistic"],
            "df": res["df"],
            "p_value_raw": res["p_value_raw"],
            "cohens_d_z": res["cohens_d_z"],
            "ci_95_low": res["ci_95"][0],
            "ci_95_high": res["ci_95"][1],
            "verdict": v,
        })
        print(f"\n  [{metric_name}] N={res['n_paired']} mean_diff={res['mean_diff']:+.6f} "
              f"sd_diff={res['sd_diff']:.4f} t={res['t_statistic']:+.4f} df={res['df']} "
              f"p={res['p_value_raw']:.3e} d_z={res['cohens_d_z']:+.4f} "
              f"CI95=[{res['ci_95'][0]:+.4f}, {res['ci_95'][1]:+.4f}] verdict={v}")

    # Step B: difficulty strata
    tier_idx, boundaries = compute_tier_assignment(baseline_plddt)
    print(f"\n  tier boundaries (p33, p67): {boundaries}")
    TIER_LABELS = ["hard", "medium", "easy"]

    strata_results = []
    strata_csv = []
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
            res = paired_t(b[mask], f[mask])
            v = verdict_strata({**res, "n_records": n_t})
            entry = {
                "dataset": "lineageflow_n1000_omegafold",
                "metric": metric_name,
                "tier": TIER_LABELS[t],
                "n_records": res["n_paired"],
                "mean_baseline": float(np.mean(b[mask])),
                "mean_framework": float(np.mean(f[mask])),
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
            strata_results.append(entry)
            strata_csv.append(entry)
            print(
                f"  [{TIER_LABELS[t]:>6}] {metric_name} N={res['n_paired']:4d}  "
                f"baseline={float(np.mean(b[mask])):.4f}  framework={float(np.mean(f[mask])):.4f}  "
                f"mean_diff={res['mean_diff']:+.6f}  d_z={res['cohens_d_z']:+.4f}  "
                f"p={res['p_value_raw']:.3e}  verdict={v}"
            )

    # Step C: monotone pattern test
    # For plddt_mean: framework uplift = positive d_z; test |d_z_hard| > |d_z_medium| > |d_z_easy|
    # For sc_perplexity: framework uplift = negative d_z; test |d_z_hard| > |d_z_medium| > |d_z_easy|
    pattern = {}
    for metric in ("plddt_mean", "sc_perplexity"):
        tier_dz = {lbl: None for lbl in TIER_LABELS}
        for r in strata_results:
            if r["metric"] == metric:
                tier_dz[r["tier"]] = r["cohens_d_z"]
        h, m, e = tier_dz["hard"], tier_dz["medium"], tier_dz["easy"]
        abs_hard = abs(h) if h is not None else None
        abs_med = abs(m) if m is not None else None
        abs_easy = abs(e) if e is not None else None
        monotone = (
            abs_hard is not None and abs_med is not None and abs_easy is not None
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
    monotone_increase_pos = (
        hard_dz is not None and med_dz is not None and easy_dz is not None
        and hard_dz > med_dz > easy_dz
    )
    monotone_increase_neg = (
        sc_hard is not None and sc_med is not None and sc_easy is not None
        and sc_hard < sc_med < sc_easy
    )
    monotone_increase = monotone_increase_pos and monotone_increase_neg

    print("\n" + "=" * 78)
    print("Monotone pattern summary (LineageFlow)")
    print("=" * 78)
    for metric, p in pattern.items():
        print(f"  {metric}: hard d_z={p['hard_d_z']}, medium={p['medium_d_z']}, easy={p['easy_d_z']}")
        print(f"    |d_z_hard|={p['abs_hard']}, |d_z_med|={p['abs_medium']}, |d_z_easy|={p['abs_easy']}")
        print(f"    monotone_decrease_in_abs_dz_with_ease = {p['monotone_decrease_in_abs_dz_with_ease']}")
    print(f"\n  BOTH metrics monotone (hard > medium > easy in |d_z|): {monotone_increase}")

    # Step D: write outputs
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_per_record_path = OUT_DIR / "wave199-p3-lineageflow-per-record.csv"
    with csv_per_record_path.open("w", newline="") as f:
        if per_record_csv:
            w = csv.DictWriter(f, fieldnames=list(per_record_csv[0].keys()))
            w.writeheader()
            w.writerows(per_record_csv)
    print(f"\nWrote {csv_per_record_path}")

    json_per_record_path = OUT_DIR / "wave199-p3-lineageflow-per-record.json"
    json_per_record_path.write_text(json.dumps({
        "per_record_results": per_record_results,
        "bonferroni_M": BONFERRONI_M_PER_RECORD,
        "bonferroni_alpha": BONFERRONI_ALPHA_PER_RECORD,
        "source": source_label,
        "n_paired_actual": n_paired,
        "wave198_p2_comparison": (
            "Wave 198 P2 lineageflow_omegafold was N=5 with identical baseline/framework values "
            "(smoke test, framework adapter not active). This Wave 199 P3 result operates on the "
            "SAME actual data file at lineageflow_n1000_omegafold_q4_2026 — Wave 199 P2's expected "
            "wave199-p2-lineageflow-n1000/ directory is empty (N=1000 sweep was killed for CPU "
            "wallclock per Wave 84 lineageflow_n1000_omegafold notes: >40 hours per arm)."
        ),
        "csv_path": str(csv_per_record_path),
        "json_path": str(json_per_record_path),
    }, indent=2))
    print(f"Wrote {json_per_record_path}")

    csv_strata_path = OUT_DIR / "wave199-p3-lineageflow-strata.csv"
    with csv_strata_path.open("w", newline="") as f:
        fieldnames = [
            "dataset", "metric", "tier", "n_records", "mean_baseline", "mean_framework",
            "mean_diff", "sd_diff", "t_statistic", "df", "cohens_d_z", "p_value_raw",
            "ci_95_low", "ci_95_high", "verdict", "tier_boundary_low", "tier_boundary_high",
            "metric_direction",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in strata_csv:
            w.writerow({k: row.get(k, "") for k in fieldnames})
    print(f"Wrote {csv_strata_path}")

    json_strata_path = OUT_DIR / "wave199-p3-lineageflow-strata.json"
    json_strata_path.write_text(json.dumps({
        "difficulty_stratified_results": strata_results,
        "tier_boundaries_percentiles": list(TIER_PERCENTILES),
        "tier_boundaries_values": boundaries,
        "bonferroni_M": BONFERRONI_M_STRATA,
        "bonferroni_alpha": BONFERRONI_ALPHA_STRATA,
        "source": source_label,
        "n_paired_actual": n_paired,
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
        "cross_adapter_consistency_vs_k6_w161": (
            "Wave 198 P3 found k6_foldability_w161 shows hard > medium > easy monotone "
            "(plddt hard d_z=+1.19, medium +0.22, easy -1.00; sc hard -1.03, medium -1.14, easy -1.14). "
            "LineageFlow N=5 smoke data is TIE on both metrics because the framework adapter produced "
            "no observable per-record difference on the identical N=5 smoke run (same pdb_path, same "
            "plddt_mean, same sc_perplexity for each qid). Cross-adapter comparison is therefore "
            "VACUOUS for LineageFlow N=5 — same-data-source comparison only meaningful at N=1000. "
            "Wave 199 P3 documents this honestly as BLOCKED-ON-DATA: N=1000 sweep was killed; "
            "no N=1000 lineageflow per-record data exists on disk."
        ),
        "csv_path": str(csv_strata_path),
        "json_path": str(json_strata_path),
    }, indent=2))
    print(f"Wrote {json_strata_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
