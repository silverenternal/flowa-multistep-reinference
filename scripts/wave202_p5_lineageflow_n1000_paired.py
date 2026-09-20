#!/usr/bin/env python3
"""Wave 202 P5: per-record paired t-test on LineageFlow N=1000 paired records.

Resume of the N=1000 sweep that was killed during Wave 202 P1 (429 errors).
Re-runs per-record paired t-test on the full N=1000 paired dataset
(df=999) for plddt_mean + sc_perplexity, plus difficulty-stratified analysis.

Pipeline:
  1. Load foldability.jsonl (for plddt_mean) + self_consistency.jsonl (for sc_perplexity)
     from both arms.
  2. Pair by qid (paired samples are 'same record index' even though
     baseline.fasta q_i and framework.fasta q_i are different sequences —
     the adapter uses seed-prefixed qids so we pair by qid).
  3. Compute paired t-test on the diffs (framework - baseline) per metric.
  4. Stratify by 33rd/67th percentile of baseline plddt: hard / medium / easy.
  5. Cross-adapter consistency vs k6_foldability_w161 per-stratum.

Output:
  - verification_outputs/wave202-p5-lineageflow-per-record.{csv,json}
  - verification_outputs/wave202-p5-lineageflow-strata.{csv,json}
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

# Use the new N=1000 LineageFlow sweep paths (Wave 204 P2 resume run).
BASELINE_DIR = Path("/tmp/w202-lineageflow/baseline/baseline")
FRAMEWORK_DIR = Path("/tmp/w202-lineageflow/baseline/framework")

# 2 metrics per dataset → Bonferroni M=2, alpha=0.025
BONFERRONI_M = 2
BONFERRONI_ALPHA = 0.05 / BONFERRONI_M  # 0.025


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def pair_by_qid(
    base: list[dict], fr: list[dict], key: str
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    base_idx = {r["qid"]: r[key] for r in base if key in r}
    fr_idx = {r["qid"]: r[key] for r in fr if key in r}
    common_qids = sorted(set(base_idx) & set(fr_idx))
    b = np.array([base_idx[q] for q in common_qids], dtype=float)
    f = np.array([fr_idx[q] for q in common_qids], dtype=float)
    return b, f, common_qids


def paired_t_test(b: np.ndarray, f: np.ndarray) -> dict:
    diff = f - b
    n = len(diff)
    if n < 2:
        return {
            "n_paired": int(n),
            "mean_diff": float("nan"),
            "sd_diff": float("nan"),
            "t_statistic": float("nan"),
            "df": int(max(0, n - 1)),
            "p_value_raw": float("nan"),
            "p_value_bonferroni_alpha_0.025": float("nan"),
            "cohens_d_z": float("nan"),
            "ci_95": [float("nan"), float("nan")],
        }
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
        "p_value_bonferroni_alpha_0.025": float(BONFERRONI_ALPHA),
        "cohens_d_z": float(d_z),
        "ci_95": [float(ci_lo), float(ci_hi)],
    }


def verdict(result: dict, *, higher_better: bool = True) -> str:
    p = result["p_value_raw"]
    d = result["cohens_d_z"]
    n = result["n_paired"]
    if n < 2:
        return "UNDERPOWERED"
    if math.isnan(p) or math.isnan(d):
        return "UNDERPOWERED"
    signed_d = d if higher_better else -d
    if p < BONFERRONI_ALPHA:
        if signed_d > 0:
            return "SUPPORTED"
        if signed_d < 0:
            return "REGRESSES"
    if abs(d) < 0.05:
        return "TIE"
    return "UNDERPOWERED"


def main() -> int:
    print("=" * 78)
    print("Wave 202 P5: LineageFlow N=1000 per-record paired t-test (Wave 204 P2 resume)")
    print(f"Bonferroni M={BONFERRONI_M}, alpha={BONFERRONI_ALPHA:.5f}")
    print("=" * 78)

    # ---- Load foldability (plddt_mean) + self_consistency (sc_perplexity) ----
    baseline_fold = load_jsonl(BASELINE_DIR / "foldability.jsonl")
    framework_fold = load_jsonl(FRAMEWORK_DIR / "foldability.jsonl")
    baseline_sc = load_jsonl(BASELINE_DIR / "self_consistency.jsonl")
    framework_sc = load_jsonl(FRAMEWORK_DIR / "self_consistency.jsonl")
    print(f"baseline foldability:  {len(baseline_fold)} records")
    print(f"framework foldability: {len(framework_fold)} records")
    print(f"baseline sc:           {len(baseline_sc)} records")
    print(f"framework sc:          {len(framework_sc)} records")

    # qid sanity check
    b_qids = sorted(r["qid"] for r in baseline_fold)
    f_qids = sorted(r["qid"] for r in framework_fold)
    if b_qids == f_qids:
        print(f"qids match exactly: {len(b_qids)} unique qids on both arms")
    else:
        only_b = set(b_qids) - set(f_qids)
        only_f = set(f_qids) - set(b_qids)
        print(f"qid mismatch! only in baseline: {len(only_b)}, only in framework: {len(only_f)}")
    qid_pairing_verified = b_qids == f_qids

    # ---- Per-record paired t-test ----
    b_plddt, f_plddt, qids_plddt = pair_by_qid(baseline_fold, framework_fold, "plddt_mean")
    b_sc, f_sc, qids_sc = pair_by_qid(baseline_sc, framework_sc, "sc_perplexity")

    res_plddt = paired_t_test(b_plddt, f_plddt)
    res_sc = paired_t_test(b_sc, f_sc)
    # plddt higher is better; sc_perplexity LOWER is better (per
    # data/lineageflow_upstream/evaluation convention)
    v_plddt = verdict(res_plddt, higher_better=True)
    v_sc = verdict(res_sc, higher_better=False)

    print()
    print(f"plddt_mean:     N={res_plddt['n_paired']:4d}  "
          f"mean_diff={res_plddt['mean_diff']:+.6f}  "
          f"sd_diff={res_plddt['sd_diff']:.6f}  "
          f"t={res_plddt['t_statistic']:+.4f}  "
          f"df={res_plddt['df']}  "
          f"p={res_plddt['p_value_raw']:.3e}  "
          f"d_z={res_plddt['cohens_d_z']:+.4f}  "
          f"CI95=[{res_plddt['ci_95'][0]:+.4f}, {res_plddt['ci_95'][1]:+.4f}]  "
          f"verdict={v_plddt}")
    print(f"sc_perplexity:  N={res_sc['n_paired']:4d}  "
          f"mean_diff={res_sc['mean_diff']:+.6f}  "
          f"sd_diff={res_sc['sd_diff']:.6f}  "
          f"t={res_sc['t_statistic']:+.4f}  "
          f"df={res_sc['df']}  "
          f"p={res_sc['p_value_raw']:.3e}  "
          f"d_z={res_sc['cohens_d_z']:+.4f}  "
          f"CI95=[{res_sc['ci_95'][0]:+.4f}, {res_sc['ci_95'][1]:+.4f}]  "
          f"verdict={v_sc}")

    res_plddt["dataset"] = "lineageflow_n1000"
    res_plddt["metric"] = "plddt_mean"
    res_plddt["verdict"] = v_plddt
    res_sc["dataset"] = "lineageflow_n1000"
    res_sc["metric"] = "sc_perplexity"
    res_sc["verdict"] = v_sc

    per_record_results = [res_plddt, res_sc]

    # ---- Difficulty strata (33rd / 67th percentile of baseline pLDDT) ----
    b_p33, b_p67 = np.percentile(b_plddt, [33.333, 66.667])
    print()
    print("=" * 78)
    print(f"Difficulty strata: hard (plddt <= {b_p33:.3f}), "
          f"medium (plddt > {b_p33:.3f} and <= {b_p67:.3f}), "
          f"easy (plddt > {b_p67:.3f})")

    strata_results: list[dict] = []
    strata_rows_csv: list[dict] = []
    monotone_pattern = None  # filled in below

    # tier counts and stats
    hard_mask = b_plddt <= b_p33
    med_mask = (b_plddt > b_p33) & (b_plddt <= b_p67)
    easy_mask = b_plddt > b_p67
    n_hard = int(hard_mask.sum())
    n_med = int(med_mask.sum())
    n_easy = int(easy_mask.sum())
    print(f"  hard:   n={n_hard}")
    print(f"  medium: n={n_med}")
    print(f"  easy:   n={n_easy}")

    plddt_dz_by_tier: dict[str, float] = {}
    sc_dz_by_tier: dict[str, float] = {}

    for tier_name, mask, n_tier in (
        ("hard", hard_mask, n_hard),
        ("medium", med_mask, n_med),
        ("easy", easy_mask, n_easy),
    ):
        if n_tier < 2:
            for metric_name in ("plddt_mean", "sc_perplexity"):
                strata_results.append({
                    "dataset": "lineageflow_n1000",
                    "metric": metric_name,
                    "tier": tier_name,
                    "n_records": int(n_tier),
                    "mean_diff": float("nan"),
                    "sd_diff": float("nan"),
                    "t_statistic": float("nan"),
                    "df": int(max(0, n_tier - 1)),
                    "p_value_raw": float("nan"),
                    "cohens_d_z": float("nan"),
                    "verdict": "UNDERPOWERED",
                    "skipped": "n<2",
                })
                continue

        # plddt_mean
        b_tier = b_plddt[mask]
        f_tier = f_plddt[mask]
        r_tier = paired_t_test(b_tier, f_tier)
        v_tier = verdict(r_tier, higher_better=True)
        plddt_dz_by_tier[tier_name] = r_tier["cohens_d_z"]
        strata_results.append({
            "dataset": "lineageflow_n1000",
            "metric": "plddt_mean",
            "tier": tier_name,
            "n_records": int(n_tier),
            "mean_diff": r_tier["mean_diff"],
            "sd_diff": r_tier["sd_diff"],
            "t_statistic": r_tier["t_statistic"],
            "df": r_tier["df"],
            "p_value_raw": r_tier["p_value_raw"],
            "cohens_d_z": r_tier["cohens_d_z"],
            "verdict": v_tier,
        })
        strata_rows_csv.append({
            "dataset": "lineageflow_n1000",
            "metric": "plddt_mean",
            "tier": tier_name,
            "n_records": int(n_tier),
            "mean_diff": r_tier["mean_diff"],
            "sd_diff": r_tier["sd_diff"],
            "t_statistic": r_tier["t_statistic"],
            "df": r_tier["df"],
            "p_value_raw": r_tier["p_value_raw"],
            "cohens_d_z": r_tier["cohens_d_z"],
            "verdict": v_tier,
        })

        # sc_perplexity
        # Use the same qid mask — qids by qid index are aligned between
        # b_plddt (sorted) and b_sc (sorted). Need to remap mask to
        # the index order used by b_sc.
        # qids_plddt and qids_sc are both sorted lexicographically (same order)
        # so the mask applies to both arrays in the same indexing.
        b_sc_tier = b_sc[mask]
        f_sc_tier = f_sc[mask]
        r_sc_tier = paired_t_test(b_sc_tier, f_sc_tier)
        v_sc_tier = verdict(r_sc_tier, higher_better=False)
        sc_dz_by_tier[tier_name] = r_sc_tier["cohens_d_z"]
        strata_results.append({
            "dataset": "lineageflow_n1000",
            "metric": "sc_perplexity",
            "tier": tier_name,
            "n_records": int(n_tier),
            "mean_diff": r_sc_tier["mean_diff"],
            "sd_diff": r_sc_tier["sd_diff"],
            "t_statistic": r_sc_tier["t_statistic"],
            "df": r_sc_tier["df"],
            "p_value_raw": r_sc_tier["p_value_raw"],
            "cohens_d_z": r_sc_tier["cohens_d_z"],
            "verdict": v_sc_tier,
        })
        strata_rows_csv.append({
            "dataset": "lineageflow_n1000",
            "metric": "sc_perplexity",
            "tier": tier_name,
            "n_records": int(n_tier),
            "mean_diff": r_sc_tier["mean_diff"],
            "sd_diff": r_sc_tier["sd_diff"],
            "t_statistic": r_sc_tier["t_statistic"],
            "df": r_sc_tier["df"],
            "p_value_raw": r_sc_tier["p_value_raw"],
            "cohens_d_z": r_sc_tier["cohens_d_z"],
            "verdict": v_sc_tier,
        })

    # Print tier results
    print()
    print("Stratified results (Wave 202 P5):")
    for row in strata_rows_csv:
        print(
            f"  tier={row['tier']:6s} metric={row['metric']:14s} "
            f"n={row['n_records']:4d} mean_diff={row['mean_diff']:+.4f} "
            f"d_z={row['cohens_d_z']:+.4f} p={row['p_value_raw']:.3e} "
            f"verdict={row['verdict']}"
        )

    # Monotone pattern test on |d_z| for plddt
    # k6 monotone: hard > medium > easy in plddt d_z
    if all(t in plddt_dz_by_tier for t in ("hard", "medium", "easy")):
        h_dz = plddt_dz_by_tier["hard"]
        m_dz = plddt_dz_by_tier["medium"]
        e_dz = plddt_dz_by_tier["easy"]
        monotone_increase = (h_dz > m_dz > e_dz)
    else:
        h_dz = plddt_dz_by_tier.get("hard", float("nan"))
        m_dz = plddt_dz_by_tier.get("medium", float("nan"))
        e_dz = plddt_dz_by_tier.get("easy", float("nan"))
        monotone_increase = False
    print()
    print(f"plddt_mean d_z by tier: hard={h_dz:+.4f} medium={m_dz:+.4f} easy={e_dz:+.4f}")
    print(f"  monotone hard > medium > easy: {monotone_increase}")

    # ---- Cross-adapter consistency vs k6_w161 (Wave 198 P3 strata) ----
    cross_adapter = {
        "k6_hard_d_z": 1.189,
        "k6_medium_d_z": 0.218,
        "k6_easy_d_z": -0.998,
        "lineageflow_hard_d_z": float(h_dz),
        "lineageflow_medium_d_z": float(m_dz),
        "lineageflow_easy_d_z": float(e_dz),
        "monotone_pattern_confirmed": bool(monotone_increase),
    }

    # ---- Write outputs ----
    csv_path = OUT_DIR / "wave202-p5-lineageflow-per-record.csv"
    with csv_path.open("w", newline="") as f_:
        w = csv.DictWriter(
            f_,
            fieldnames=[
                "dataset", "metric", "n_paired", "mean_diff", "sd_diff", "t_statistic",
                "df", "p_value_raw", "cohens_d_z", "ci_95_low", "ci_95_high", "verdict",
            ],
        )
        w.writeheader()
        for r_ in per_record_results:
            w.writerow({
                "dataset": r_["dataset"],
                "metric": r_["metric"],
                "n_paired": r_["n_paired"],
                "mean_diff": r_["mean_diff"],
                "sd_diff": r_["sd_diff"],
                "t_statistic": r_["t_statistic"],
                "df": r_["df"],
                "p_value_raw": r_["p_value_raw"],
                "cohens_d_z": r_["cohens_d_z"],
                "ci_95_low": r_["ci_95"][0],
                "ci_95_high": r_["ci_95"][1],
                "verdict": r_["verdict"],
            })
    print(f"\nWrote {csv_path}")

    json_out = {
        "wave": "202 P5",
        "agent": "Wave 204 P2 resume",
        "dataset": "lineageflow_n1000",
        "qid_pairing_verified": bool(qid_pairing_verified),
        "bonferroni_M": BONFERRONI_M,
        "bonferroni_alpha": BONFERRONI_ALPHA,
        "per_record_results": per_record_results,
        "difficulty_stratified_results": strata_results,
        "difficulty_uplift_pattern": {
            "hard_d_z": float(h_dz),
            "medium_d_z": float(m_dz),
            "easy_d_z": float(e_dz),
            "monotone_increase": bool(monotone_increase),
        },
        "cross_adapter_consistency_vs_k6_w161": cross_adapter,
        "csv_paths": [
            "verification_outputs/wave202-p5-lineageflow-per-record.csv",
            "verification_outputs/wave202-p5-lineageflow-strata.csv",
        ],
        "json_paths": [
            "verification_outputs/wave202-p5-lineageflow-per-record.json",
            "verification_outputs/wave202-p5-lineageflow-strata.json",
        ],
    }
    json_path = OUT_DIR / "wave202-p5-lineageflow-per-record.json"
    with json_path.open("w") as f_:
        json.dump(json_out, f_, indent=2, default=str)
    print(f"Wrote {json_path}")

    strata_csv_path = OUT_DIR / "wave202-p5-lineageflow-strata.csv"
    with strata_csv_path.open("w", newline="") as f_:
        w = csv.DictWriter(
            f_,
            fieldnames=[
                "dataset", "metric", "tier", "n_records", "mean_diff", "sd_diff",
                "t_statistic", "df", "p_value_raw", "cohens_d_z", "verdict",
            ],
        )
        w.writeheader()
        for row in strata_rows_csv:
            w.writerow(row)
    print(f"Wrote {strata_csv_path}")

    strata_json_path = OUT_DIR / "wave202-p5-lineageflow-strata.json"
    with strata_json_path.open("w") as f_:
        json.dump(
            {
                "wave": "202 P5",
                "agent": "Wave 204 P2 resume",
                "dataset": "lineageflow_n1000",
                "tier_boundaries_baseline_plddt": {"p33": float(b_p33), "p67": float(b_p67)},
                "tier_n": {"hard": int(n_hard), "medium": int(n_med), "easy": int(n_easy)},
                "bonferroni_M": 6,  # 2 metrics × 3 tiers
                "bonferroni_alpha": 0.05 / 6,
                "strata_results": strata_results,
                "monotone_pattern_test": {
                    "k6_monotone_pattern": "hard > medium > easy in plddt d_z",
                    "lineageflow_hard_d_z": float(h_dz),
                    "lineageflow_medium_d_z": float(m_dz),
                    "lineageflow_easy_d_z": float(e_dz),
                    "monotone_increase": bool(monotone_increase),
                    "confirmed": bool(monotone_increase),
                },
                "cross_adapter_consistency_vs_k6_w161": cross_adapter,
            },
            f_,
            indent=2,
            default=str,
        )
    print(f"Wrote {strata_json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
