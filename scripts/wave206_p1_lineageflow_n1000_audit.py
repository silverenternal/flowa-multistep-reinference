#!/usr/bin/env python3
"""Wave 206 P1: 12-col audit-grade per-cell stats for LineageFlow N=1000 paired sweep.

Reads R1 HMMER (baseline_hits.tbl, framework_hits.tbl) + R6 foldability
(foldability.jsonl) + R6 self_consistency (self_consistency.jsonl) from
verification_outputs/wave206-p1-lineageflow-n1000/.

Computes paired-record per-cell stats (12-col format per Wave 203 P4 / CLM-066):
  - n_paired, mean_diff, sd_diff, t, df, p_raw, CI95_low, CI95_high,
    Cohen's d_z, test_type, family, alpha_bonferroni, bonf_sig
for three cells: R1 HMMER, R6 pLDDT, R6 scPerplexity.

Bonferroni families:
  - R1 HMMER: 1 cell (alpha=0.05/1=0.05)
  - R6 foldability: 2 cells (plddt_mean + sc_perplexity; alpha=0.05/2=0.025)
  - Wave 203 P4 / CLM-066 standardizes the 12-col format.

Outputs:
  - verification_outputs/wave206-p1-lineageflow-n1000.csv
  - verification_outputs/wave206-p1-lineageflow-n1000.json
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import scipy.stats

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
OUT_DIR = REPO_ROOT / "verification_outputs"
WAVE_OUT = OUT_DIR / "wave206-p1-lineageflow-n1000"

# R1 HMMER paths (pre-computed Wave 158 Pfam DB sweep, complete on disk)
HMMER_DIR = OUT_DIR / "lineageflow_hmmer_real_n1000_w158_q3_2026"
R1_BASELINE_HITS = HMMER_DIR / "baseline_hits.tbl"
R1_FRAMEWORK_HITS = HMMER_DIR / "framework_hits.tbl"

# R6 foldability + sc paths come from Wave 206 P1 sweep
R6_BASELINE_DIR = WAVE_OUT / "baseline"
R6_FRAMEWORK_DIR = WAVE_OUT / "framework"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def parse_hmmscan_total_hits(tbl_path: Path) -> dict[int, int]:
    """Parse hmmscan --tblout output: count hits per query SEED index.

    The fasta headers are `baseline_seedN|family=...` and
    `framework_seedN|family=...` (N = seed 0..999). The HMMER tbl preserves
    these headers as the query_name field. We extract N as integer seed
    (paired-record index across baseline and framework arms).

    Returns: dict seed_index -> hit count.
    Filters only non-comment lines; each line is one Pfam domain hit.
    """
    seed_hits: dict[int, int] = {}
    if not tbl_path.exists():
        return seed_hits
    pat_seed = re.compile(r"_seed(\d+)\|")
    with tbl_path.open() as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            qname = parts[2]
            m = pat_seed.search(qname)
            if not m:
                continue
            seed = int(m.group(1))
            seed_hits[seed] = seed_hits.get(seed, 0) + 1
    return seed_hits


def paired_t_test(b: np.ndarray, f: np.ndarray, alpha: float) -> dict:
    diff = f - b
    n = len(diff)
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
    mean_diff = float(np.mean(diff))
    sd_diff = float(np.std(diff, ddof=1))
    se = sd_diff / math.sqrt(n)
    df = n - 1
    if sd_diff == 0.0:
        if mean_diff > 0:
            t_stat = float("inf")
            p_raw = 0.0
        elif mean_diff < 0:
            t_stat = float("-inf")
            p_raw = 0.0
        else:
            t_stat = 0.0
            p_raw = 1.0
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
    print("Wave 206 P1: LineageFlow N=1000 paired-record 12-col audit")
    print("=" * 78)

    # ---- R1 HMMER (pre-computed, pair by seed index 0-999) ----
    base_hits = parse_hmmscan_total_hits(R1_BASELINE_HITS)
    fr_hits = parse_hmmscan_total_hits(R1_FRAMEWORK_HITS)
    all_seeds = list(range(1000))
    b_r1 = np.array([base_hits.get(s, 0) for s in all_seeds], dtype=float)
    f_r1 = np.array([fr_hits.get(s, 0) for s in all_seeds], dtype=float)
    n_paired_r1 = int(((b_r1 + f_r1) >= 0).sum())  # everyone is paired
    n_r1 = n_paired_r1
    n_zerozero = int(((b_r1 == 0) & (f_r1 == 0)).sum())
    print(
        f"R1 HMMER: baseline={len(base_hits)}/1000 seeds with hits, "
        f"framework={len(fr_hits)}/1000 seeds with hits, "
        f"paired by seed 0..999 (zero-zero: {n_zerozero}/{n_r1})"
    )

    # ---- R6 foldability + sc from current Wave 206 P1 sweep ----
    baseline_fold = load_jsonl(R6_BASELINE_DIR / "fold" / "foldability.jsonl")
    framework_fold = load_jsonl(R6_FRAMEWORK_DIR / "fold" / "foldability.jsonl")
    baseline_sc = load_jsonl(R6_BASELINE_DIR / "sc" / "self_consistency.jsonl")
    framework_sc = load_jsonl(R6_FRAMEWORK_DIR / "sc" / "self_consistency.jsonl")

    # filter sc entries with actual scores (drop error rows)
    def plddt_map(rows):
        return {r["qid"]: r["plddt_mean"] for r in rows if "plddt_mean" in r}

    def sc_map(rows):
        return {r["qid"]: r["sc_perplexity"] for r in rows if "sc_perplexity" in r and r.get("sc_perplexity") is not None}

    b_plddt_m = plddt_map(baseline_fold)
    f_plddt_m = plddt_map(framework_fold)
    b_sc_m = sc_map(baseline_sc)
    f_sc_m = sc_map(framework_sc)

    common_qids_plddt = sorted(set(b_plddt_m) & set(f_plddt_m))
    common_qids_sc = sorted(set(b_sc_m) & set(f_sc_m))
    b_plddt = np.array([b_plddt_m[q] for q in common_qids_plddt], dtype=float)
    f_plddt = np.array([f_plddt_m[q] for q in common_qids_plddt], dtype=float)
    b_sc = np.array([b_sc_m[q] for q in common_qids_sc], dtype=float)
    f_sc = np.array([f_sc_m[q] for q in common_qids_sc], dtype=float)

    print(f"R6 pLDDT: common={len(common_qids_plddt)} (baseline={len(baseline_fold)}, framework={len(framework_fold)})")
    print(f"R6 scPerp: common={len(common_qids_sc)} (baseline={len(baseline_sc)}, framework={len(framework_sc)})")

    # ---- Per-cell stats (12-col) ----
    rows: list[dict] = []

    # R1 HMMER: 1 cell, alpha=0.05/1=0.05; higher_better (more hits is better)
    r1 = paired_t_test(b_r1, f_r1, alpha=0.05)
    r1.update({
        "dataset": "lineageflow_n1000",
        "model": "lineageflow",
        "cell": "R1_HMMER",
        "metric": "hmmscan_total_hits",
        "test_type": "paired_t_test",
        "family": "R1_only",
        "alpha_bonferroni": 0.05,
        "higher_better": True,
    })
    rows.append(r1)

    # R6 pLDDT: alpha=0.05/2=0.025; higher_better
    r6_p = paired_t_test(b_plddt, f_plddt, alpha=0.025)
    r6_p.update({
        "dataset": "lineageflow_n1000",
        "model": "lineageflow",
        "cell": "R6_pLDDT",
        "metric": "plddt_mean",
        "test_type": "paired_t_test",
        "family": "R6_foldability",
        "alpha_bonferroni": 0.025,
        "higher_better": True,
    })
    rows.append(r6_p)

    # R6 scPerplexity: alpha=0.05/2=0.025; LOWER better
    r6_s = paired_t_test(b_sc, f_sc, alpha=0.025)
    r6_s.update({
        "dataset": "lineageflow_n1000",
        "model": "lineageflow",
        "cell": "R6_scPerplexity",
        "metric": "sc_perplexity",
        "test_type": "paired_t_test",
        "family": "R6_foldability",
        "alpha_bonferroni": 0.025,
        "higher_better": False,
    })
    rows.append(r6_s)

    # ---- Print + write outputs ----
    print()
    print(f"{'cell':<18} {'n_paired':>8} {'mean_diff':>12} {'sd_diff':>10} {'t':>10} {'p_raw':>12} {'d_z':>8} {'CI95':>20} {'bonf':>6}")
    for r in rows:
        ci_lo, ci_hi = r["ci_95"]
        bonf = "YES" if r["bonf_sig"] else "no"
        print(
            f"{r['cell']:<18} {r['n_paired']:>8d} "
            f"{r['mean_diff']:>+12.4f} {r['sd_diff']:>10.4f} "
            f"{r['t_statistic']:>+10.3f} "
            f"{r['p_value_raw']:>12.3e} {r['cohens_d_z']:>+8.4f} "
            f"[{ci_lo:>+.4f},{ci_hi:>+.4f}] {bonf:>6}"
        )

    # CSV (12-col standard)
    csv_path = OUT_DIR / "wave206-p1-lineageflow-n1000.csv"
    with csv_path.open("w", newline="") as f_:
        w = csv.writer(f_)
        w.writerow([
            "dataset", "model", "cell", "metric",
            "n_paired", "mean_diff", "sd_diff", "t_statistic", "df",
            "p_value_raw", "CI95_low", "CI95_high", "cohens_d_z",
            "test_type", "family", "alpha_bonferroni", "bonf_sig",
            "higher_better",
        ])
        for r in rows:
            ci_lo, ci_hi = r["ci_95"]
            w.writerow([
                r["dataset"], r["model"], r["cell"], r["metric"],
                r["n_paired"], r["mean_diff"], r["sd_diff"], r["t_statistic"], r["df"],
                r["p_value_raw"], ci_lo, ci_hi, r["cohens_d_z"],
                r["test_type"], r["family"], r["alpha_bonferroni"], r["bonf_sig"],
                r["higher_better"],
            ])
    print(f"\nWrote {csv_path}")

    # JSON (full)
    json_path = OUT_DIR / "wave206-p1-lineageflow-n1000.json"
    json.dump(
        {
            "wave": "206 P1",
            "agent": "Wave 206 P1 LineageFlow N=1000 audit",
            "dataset": "lineageflow_n1000",
            "model": "lineageflow",
            "omega_fold_env": "omegafold_py310",
            "r1_hmmer": {
                "data_source": str(R1_BASELINE_HITS.parent),
                "n_paired": int(r1["n_paired"]),
                "baseline_hits_count": int(sum(base_hits.values())),
                "framework_hits_count": int(sum(fr_hits.values())),
            },
            "r6_foldability": {
                "data_source": str(WAVE_OUT),
                "plddt_n_paired": int(r6_p["n_paired"]),
                "sc_n_paired": int(r6_s["n_paired"]),
            },
            "per_cell_stats": [
                {
                    "dataset": r["dataset"],
                    "model": r["model"],
                    "cell": r["cell"],
                    "metric": r["metric"],
                    "n_paired": r["n_paired"],
                    "mean_diff": r["mean_diff"],
                    "sd_diff": r["sd_diff"],
                    "t_statistic": r["t_statistic"],
                    "df": r["df"],
                    "p_value_raw": r["p_value_raw"],
                    "ci_95_low": r["ci_95"][0],
                    "ci_95_high": r["ci_95"][1],
                    "cohens_d_z": r["cohens_d_z"],
                    "test_type": r["test_type"],
                    "family": r["family"],
                    "alpha_bonferroni": r["alpha_bonferroni"],
                    "bonf_sig": r["bonf_sig"],
                    "higher_better": r["higher_better"],
                }
                for r in rows
            ],
            "csv_path": "verification_outputs/wave206-p1-lineageflow-n1000.csv",
        },
        json_path.open("w"),
        indent=2,
        default=str,
    )
    print(f"Wrote {json_path}")

    # Return r1_dict + summary
    print()
    print("SUMMARY:")
    print(f"  R1 HMMER:      Δ={r1['mean_diff']:+.2f} hits, d_z={r1['cohens_d_z']:+.3f}, p={r1['p_value_raw']:.3e}, N={r1['n_paired']}")
    print(f"  R6 pLDDT:      Δ={r6_p['mean_diff']:+.4f}, d_z={r6_p['cohens_d_z']:+.4f}, p={r6_p['p_value_raw']:.3e}, N={r6_p['n_paired']}")
    print(f"  R6 scPerp:     Δ={r6_s['mean_diff']:+.4f}, d_z={r6_s['cohens_d_z']:+.4f}, p={r6_s['p_value_raw']:.3e}, N={r6_s['n_paired']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
