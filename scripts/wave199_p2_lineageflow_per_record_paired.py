#!/usr/bin/env python3
"""Wave 199 P2: per-record paired t-test on N=1000 paired records (lineageflow N=1000 sweep).

Reads per-record foldability.jsonl + self_consistency.jsonl from:
  - verification_outputs/wave199-p2-lineageflow-n1000/baseline/fold/foldability.jsonl
  - verification_outputs/wave199-p2-lineageflow-n1000/framework/fold/foldability.jsonl
  - verification_outputs/wave199-p2-lineageflow-n1000/baseline/sc/self_consistency.jsonl
  - verification_outputs/wave199-p2-lineageflow-n1000/framework/sc/self_consistency.jsonl

Computes paired t-test per metric (plddt_mean, sc_perplexity):
  - mean_diff = mean(framework - baseline)
  - sd_diff = std(framework - baseline, paired, ddof=1)
  - t_statistic = mean_diff / (sd_diff / sqrt(N))
  - df = N - 1
  - p_value = 2 * scipy.stats.t.sf(abs(t_statistic), df=df)
  - cohen_d_z = mean_diff / sd_diff
  - CI_95: mean_diff +/- 1.96 * SE_diff
  - Bonferroni alpha = 0.05 / 2 = 0.025
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
# Bonferroni M = number of metrics = 2 (plddt_mean, sc_perplexity)
BONFERRONI_M = 2
BONFERRONI_ALPHA = 0.05 / BONFERRONI_M  # 0.025


DATASET = {
    "dataset": "lineageflow_w199_p2_n1000",
    "baseline_fold": OUT_DIR / "wave199-p2-lineageflow-n1000/baseline/fold/foldability.jsonl",
    "framework_fold": OUT_DIR / "wave199-p2-lineageflow-n1000/framework/fold/foldability.jsonl",
    "baseline_sc": OUT_DIR / "wave199-p2-lineageflow-n1000/baseline/sc/self_consistency.jsonl",
    "framework_sc": OUT_DIR / "wave199-p2-lineageflow-n1000/framework/sc/self_consistency.jsonl",
}


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def pair_by_qid(base: list[dict], fr: list[dict], key: str) -> tuple[np.ndarray, np.ndarray]:
    base_idx = {r["qid"]: r[key] for r in base}
    fr_idx = {r["qid"]: r[key] for r in fr}
    common_qids = sorted(set(base_idx) & set(fr_idx))
    if len(common_qids) != len(base) or len(common_qids) != len(fr):
        print(
            f"  WARN: base={len(base)} fr={len(fr)} paired={len(common_qids)} qids "
            f"(dropped {len(set(base_idx) ^ set(fr_idx))})"
        )
    b = np.array([base_idx[q] for q in common_qids], dtype=float)
    f = np.array([fr_idx[q] for q in common_qids], dtype=float)
    return b, f


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
            "p_value_bonferroni_alpha_0.025": float("nan"),
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
        "p_value_bonferroni_alpha_0.025": float(BONFERRONI_ALPHA),
        "cohens_d_z": float(d_z),
        "ci_95": [float(ci_lo), float(ci_hi)],
    }


def verdict(result: dict) -> str:
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
    if abs(d) < 0.05:
        return "TIE"
    return "UNDERPOWERED"


def main() -> int:
    all_results = []
    rows_csv = []
    print("=" * 78)
    print("Wave 199 P2: per-record paired t-test on N=1000 lineageflow")
    print(f"Bonferroni M={BONFERRONI_M}, alpha={BONFERRONI_ALPHA:.5f}")
    print("=" * 78)

    print(f"\nDataset: {DATASET['dataset']}")
    base_fold = load_jsonl(DATASET["baseline_fold"])
    fr_fold = load_jsonl(DATASET["framework_fold"])
    base_sc = load_jsonl(DATASET["baseline_sc"])
    fr_sc = load_jsonl(DATASET["framework_sc"])
    print(f"  baseline_fold: {len(base_fold)} records")
    print(f"  framework_fold: {len(fr_fold)} records")
    print(f"  baseline_sc: {len(base_sc)} records")
    print(f"  framework_sc: {len(fr_sc)} records")

    for metric_name, base_arr, fr_arr in [
        ("plddt_mean", *pair_by_qid(base_fold, fr_fold, "plddt_mean")),
        ("sc_perplexity", *pair_by_qid(base_sc, fr_sc, "sc_perplexity")),
    ]:
        result = paired_t(base_arr, fr_arr)
        v = verdict(result)
        result["dataset"] = DATASET["dataset"]
        result["metric"] = metric_name
        result["verdict"] = v
        all_results.append(result)
        rows_csv.append({
            "dataset": result["dataset"],
            "metric": metric_name,
            "n_paired": result["n_paired"],
            "mean_diff": result["mean_diff"],
            "sd_diff": result["sd_diff"],
            "t_statistic": result["t_statistic"],
            "df": result["df"],
            "p_value_raw": result["p_value_raw"],
            "cohens_d_z": result["cohens_d_z"],
            "ci_95_low": result["ci_95"][0],
            "ci_95_high": result["ci_95"][1],
            "verdict": v,
        })
        print(f"\n  [{metric_name}] N={result['n_paired']} mean_diff={result['mean_diff']:+.4f} "
              f"sd_diff={result['sd_diff']:.4f} t={result['t_statistic']:+.4f} df={result['df']} "
              f"p={result['p_value_raw']:.3e} d_z={result['cohens_d_z']:+.4f} "
              f"CI95=[{result['ci_95'][0]:+.4f}, {result['ci_95'][1]:+.4f}] verdict={v}")

    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "wave199-p2-per-record-paired.csv"
    json_path = out_dir / "wave199-p2-per-record-paired.json"

    with csv_path.open("w", newline="") as f:
        if rows_csv:
            w = csv.DictWriter(f, fieldnames=list(rows_csv[0].keys()))
            w.writeheader()
            w.writerows(rows_csv)
    print(f"\nwrote {csv_path}")

    json_path.write_text(json.dumps({
        "per_record_results": all_results,
        "bonferroni_M": BONFERRONI_M,
        "bonferroni_alpha": BONFERRONI_ALPHA,
        "note": "Wave 199 P2: full N=1000 sweep on lineageflow (OmegaFold pLDDT + ESM-IF scPerplexity).",
        "csv_path": str(csv_path),
        "json_path": str(json_path),
    }, indent=2))
    print(f"wrote {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
