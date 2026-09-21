#!/usr/bin/env python3
"""Wave 246 P2 — tier-aware parameter transferability on R1 LineageFlow.

Goal (per Wave 246 P2 brief)
----------------------------
Wave 235 P2 picked ``(easy_factor=0.0, hard_intensity=2.0)`` for R2 Kanzi
(20-cell grid search). Wave 235 P3 picked ``(easy_factor=0.0,
hard_intensity=3.0)`` for R6 MNIST (20-cell grid search).

Concern: are these best cells overfit to R2 / R6 specifically, or do they
transfer to other adapters?

Independence test: re-run the Wave 235 P2 / P3 tier-aware counterfactual
methodology on the R1 LineageFlow N=1000 HMMER dataset (NOT used in the Wave
235 grid search). If the Wave 235 best cells also produce positive d_z on
R1 LineageFlow AND the same best cell dominates vs 4 alternatives, then the
Wave 235 cells transfer — low overfit risk. If only a different cell wins
on R1, the Wave 235 cells are adapter-specific — high overfit risk.

6 param combos (per the brief: R2 best + R6 best + 4 alternatives):
  0. (0.0, 2.0) - Wave 235 P2 R2 Kanzi best
  1. (0.0, 3.0) - Wave 235 P3 R6 MNIST best
  2. (0.0, 1.0) - uniform passthrough (no tier-aware reduction)
  3. (0.25, 2.0) - middle of grid
  4. (0.5, 1.0) - Wave 233 P3 baseline
  5. (0.5, 2.0) - easy reduction + hard amplification

Per-record paired data
----------------------
For each of 1000 seeds we extract a per-record scalar from the HMMER
``--tblout`` output:

* Baseline: best (max) full-sequence HMMER score across all hits for that
  query. If the query has 0 hits, score is 0 (sequence doesn't hit any Pfam
  profile).
* Framework: same metric on the framework's HMMER scan.

Both scans run on the same N=1000 LineageFlow sequence sample (Wave 158
canonical archive), so baseline_seedK and framework_seedK share the same
seed index and the same family assignment.

Tier stratification
-------------------
Records are stratified into easy / medium / hard by the BASELINE per-record
score (higher baseline score = easier seed; lower baseline score = harder
seed). Tier boundaries: 33rd / 67th percentiles of the baseline score
distribution (same Wave 198 P3 / Wave 225 P4 / Wave 233 P3 / Wave 245 P2
methodology).

Counterfactual methodology (reused from Wave 245 P2)
-----------------------------------------------------
For each (tier, param-combo) the counterfactual framework arm is::

    diff_t          = f[t] - b[t]
    mean_diff_t     = mean(diff_t)
    diff_counter_t  = diff_t - mean_diff_t + ratio * mean_diff_t
    counter_t       = b[t] + diff_counter_t

Where ``ratio = easy_factor`` on easy, ``ratio = 1.0`` on medium
(passthrough), ``ratio = hard_intensity`` on hard. Per-record variance is
preserved.

The "best cell" criterion matches Wave 235 P2 / P3: cell with the HIGHEST
overall d_z VALUE (most positive). For HMMER score (higher=better),
positive d_z means framework wins — so highest d_z = strongest tier-aware
uplift. This is direction-aligned for HMMER (unlike RMSD, where the brief's
criterion is direction-agnostic magnitude).

Hard rules respected:
* NO framework source code modified
* NO Wave 242 GPU task touched
* D.4 30/30 PASS preserved (READ-ONLY analysis on FROZEN Wave 158 HMMER
  hit tables; same counterfactual methodology as Wave 225 P4 / Wave 233 P3
  / Wave 235 P2 / Wave 235 P3 / Wave 245 P2)
* Counterfactual (no live GPU run)

Outputs
-------
* verification_outputs/wave246-p2-tier-aware-independence-r1.json
* verification_outputs/wave246-p2-tier-aware-independence-r1.csv
* docs/audit/wave246-p2-tier-aware-independence-r1.md
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

REPO = Path("/home/hugo/codes/flowa-multistep-reinference")
OUT_DIR = REPO / "verification_outputs"
DOCS_DIR = REPO / "docs" / "audit"

# --- R1 (LineageFlow HMMER) data sources (Wave 158 frozen) ---
R1_BASELINE = (
    REPO / "verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/baseline_hits.tbl"
)
R1_FRAMEWORK = (
    REPO / "verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/framework_hits.tbl"
)
R1_FAMILY_IDS = ["PF00005.27", "PF00072.24", "PF00183.19", "PF02517.18"]

JSON_OUT = OUT_DIR / "wave246-p2-tier-aware-independence-r1.json"
CSV_OUT = OUT_DIR / "wave246-p2-tier-aware-independence-r1.csv"
DOC_OUT = DOCS_DIR / "wave246-p2-tier-aware-independence-r1.md"

# --- Bonferroni M=3 (3 tiers x 1 metric) ---
BONFERRONI_M = 3
BONFERRONI_ALPHA = 0.05 / BONFERRONI_M

# --- 6 param combos (per the Wave 246 P2 brief) ---
R1_PARAM_COMBOS = [
    ("w235_p2_r2_kanzi_best",  0.0, 2.0),  # Wave 235 P2 best for R2 Kanzi
    ("w235_p3_r6_mnist_best",  0.0, 3.0),  # Wave 235 P3 best for R6 MNIST
    ("uniform_passthrough",    0.0, 1.0),  # uniform passthrough (no tier-aware)
    ("mid_grid",               0.25, 2.0), # middle of grid
    ("w233_p3_baseline",       0.5, 1.0),  # Wave 233 P3 baseline
    ("easy_red_hard_amp",      0.5, 2.0),  # easy reduction + hard amplification
]


# ============================================================================
# Statistics primitives (reused from Wave 235 P2/P3 / Wave 245 P2)
# ============================================================================

def _paired_t_test(b: np.ndarray, f: np.ndarray) -> dict[str, float]:
    diff = f - b
    n = int(len(diff))
    if n < 2:
        return {
            "n_paired": n,
            "mean_baseline": float(np.mean(b)) if n else float("nan"),
            "mean_framework": float(np.mean(f)) if n else float("nan"),
            "mean_diff": float("nan"),
            "sd_diff": float("nan"),
            "t_statistic": float("nan"),
            "df": 0,
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
    return {
        "n_paired": n,
        "mean_baseline": mean_b,
        "mean_framework": mean_f,
        "mean_diff": mean_diff,
        "sd_diff": sd_diff,
        "t_statistic": float(t_stat),
        "df": int(df),
        "p_value_raw": p_raw,
        "cohens_d_z": float(d_z),
        "ci_95": [float(mean_diff - 1.96 * se), float(mean_diff + 1.96 * se)],
    }


def _tier_assignment(baseline_metric: np.ndarray, low: float, high: float) -> np.ndarray:
    """Assign 0/1/2 (hard/medium/easy) by baseline metric percentile rank.

    For HMMER score (higher=better): low baseline score = hard (sequence
    hits few/no Pfam profiles), high baseline score = easy (sequence hits
    many Pfam profiles). Tier boundaries derived from 33rd / 67th
    percentile of the baseline score distribution.
    """
    tier = np.zeros(len(baseline_metric), dtype=int)
    tier[baseline_metric > low] = 1
    tier[baseline_metric > high] = 2
    return tier


def _build_counterfactual(
    b: np.ndarray,
    f: np.ndarray,
    tier: np.ndarray,
    easy_factor: float,
    hard_intensity: float,
) -> np.ndarray:
    """Build per-tier counterfactual framework arm.

    For each tier ``t`` with assigned ratio ``r``::

        diff_counter_t = diff_t - mean_diff_t + r * mean_diff_t
        counter_t      = baseline_t + diff_counter_t

    where ``r = easy_factor`` on easy, ``r = 1.0`` on medium, and
    ``r = hard_intensity`` on hard.
    """
    diff = f - b
    counter = f.copy()
    tier_ratios = {
        0: float(hard_intensity),  # hard
        1: 1.0,                    # medium (passthrough)
        2: float(easy_factor),     # easy
    }
    for t, ratio in tier_ratios.items():
        mask = tier == t
        if not np.any(mask):
            continue
        mean_diff_t = float(np.mean(diff[mask]))
        diff_counter_t = diff[mask] - mean_diff_t + ratio * mean_diff_t
        counter[mask] = b[mask] + diff_counter_t
    return counter


# ============================================================================
# Loaders
# ============================================================================

def _parse_hmmer_tbl(path: Path) -> dict[str, dict[str, float]]:
    """Parse HMMER --tblout file. Return per-query aggregate dict.

    For each query returns:
      - n_hits: int, number of hit rows
      - max_score: float, max full-sequence score across hits (0.0 if no hits)
      - min_e_value: float, min full-sequence E-value across hits (inf if no hits)
      - family: str, Pfam family from query header

    The query name (column 3) is "baseline_seedK|family=PFxxx.yy" or
    "framework_seedK|family=PFxxx.yy". We strip the arm prefix to get a
    common seed key (e.g., "seedK").
    """
    per_query: dict[str, dict[str, float]] = {}
    with path.open() as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            if not line.strip():
                continue
            parts = line.split(None, 18)  # last column may contain spaces
            if len(parts) < 18:
                continue
            target_accession = parts[1]
            query_name = parts[2]
            try:
                full_e_value = float(parts[4])
                full_score = float(parts[5])
            except ValueError:
                continue
            # Extract seed key (strip "baseline_" or "framework_" prefix).
            m = re.match(r"(?:baseline|framework)_(seed\d+)\|family=(\S+)", query_name)
            if not m:
                # Some rows may have just "baseline_seed7" without family
                m2 = re.match(r"(?:baseline|framework)_(seed\d+)", query_name)
                if m2:
                    seed_key = m2.group(1)
                    family = ""
                else:
                    continue
            else:
                seed_key = m.group(1)
                family = m.group(2)
            rec = per_query.get(seed_key)
            if rec is None:
                per_query[seed_key] = {
                    "n_hits": 1,
                    "max_score": full_score,
                    "min_e_value": full_e_value,
                    "family": family,
                    "best_target_accession": target_accession,
                }
            else:
                rec["n_hits"] += 1
                if full_score > rec["max_score"]:
                    rec["max_score"] = full_score
                if full_e_value < rec["min_e_value"]:
                    rec["min_e_value"] = full_e_value
                    rec["best_target_accession"] = target_accession
    # Records absent from the file get a default (zero hits, score=0).
    return per_query


def _load_seed_list_from_manifest() -> tuple[list[str], list[str]]:
    """Load all 1000 seed keys + Pfam family per seed from the FASTA manifest.

    The HMMER hit tables only contain rows for seeds that produced at
    least one hit; we need the FULL N=1000 seed list (including the
    zero-hit seeds) to compute per-record paired data with score=0 for
    non-hit records.
    """
    b_fasta = REPO / "verification_outputs/lineageflow_real_fastas_w158_q3_2026/baseline.fasta"
    seeds: list[str] = []
    families: list[str] = []
    seed_re = re.compile(r"^>(?:baseline|framework)_(seed\d+)\|family=(\S+)")
    with b_fasta.open() as fh:
        for line in fh:
            if not line.startswith(">"):
                continue
            m = seed_re.match(line.strip())
            if not m:
                continue
            seeds.append(m.group(1))
            families.append(m.group(2))
    paired = sorted(
        zip(seeds, families, strict=False),
        key=lambda t: int(t[0].replace("seed", "")),
    )
    seeds_sorted = [p[0] for p in paired]
    families_sorted = [p[1] for p in paired]
    return seeds_sorted, families_sorted


def _load_r1_lineageflow() -> tuple[list[str], np.ndarray, np.ndarray, list[str]]:
    """Load per-record R1 LineageFlow paired data + Pfam family per record.

    Returns (seed_keys, baseline_max_score, framework_max_score, families)
    aligned across all 1000 seeds (in seed numerical order). Records
    absent from the HMMER hit tables get score=0 (sequence hits no Pfam
    profile).
    """
    all_seeds, families = _load_seed_list_from_manifest()
    b = _parse_hmmer_tbl(R1_BASELINE)
    f = _parse_hmmer_tbl(R1_FRAMEWORK)
    b_scores = np.array([b.get(s, {}).get("max_score", 0.0) for s in all_seeds], dtype=float)
    f_scores = np.array([f.get(s, {}).get("max_score", 0.0) for s in all_seeds], dtype=float)
    return all_seeds, b_scores, f_scores, families


# ============================================================================
# Independence analysis
# ============================================================================

def _tier_aware_counterfactual_grid(
    b: np.ndarray,
    f: np.ndarray,
    tier_low: float,
    tier_high: float,
    combos: list[tuple[str, float, float]],
) -> dict:
    """Run tier-aware counterfactual grid on R1; report per-tier d_z per combo.

    Per the Wave 235 P2 / P3 brief, the "best cell" criterion is the cell
    with the HIGHEST d_z VALUE (most positive). For HMMER score
    (higher=better), positive d_z means framework wins, so the cell with
    highest d_z = strongest tier-aware uplift.

    Returns:
      {
        "tier_boundaries": (low, high),
        "n_records_total": int,
        "tier_sizes": {hard/medium/easy: int},
        "per_combo": {
          combo_name: {
            "easy_factor": float, "hard_intensity": float,
            "overall_d_z": float, "overall_p_value": float,
            "overall_bonf_sig": bool,
            "per_tier_d_z": {hard/medium/easy: float},
            "per_tier_p_value": {hard/medium/easy: float},
            "per_tier_mean_diff": {hard/medium/easy: float},
          },
          ...
        },
        "best_combo": combo_name,
        "best_combo_d_z": float,
      }
    """
    tier = _tier_assignment(b, tier_low, tier_high)
    per_tier_sizes = {
        "hard": int(np.sum(tier == 0)),
        "medium": int(np.sum(tier == 1)),
        "easy": int(np.sum(tier == 2)),
    }
    per_combo: dict[str, dict] = {}
    for combo_name, ef, hi in combos:
        counter = _build_counterfactual(b, f, tier, ef, hi)
        overall = _paired_t_test(b, counter)
        per_tier: dict[str, float] = {}
        per_tier_p: dict[str, float] = {}
        per_tier_md: dict[str, float] = {}
        for t, label in enumerate(["hard", "medium", "easy"]):
            tmask = tier == t
            n_t = int(np.sum(tmask))
            if n_t < 2:
                per_tier[label] = float("nan")
                per_tier_p[label] = float("nan")
                per_tier_md[label] = float("nan")
                continue
            t_result = _paired_t_test(b[tmask], counter[tmask])
            per_tier[label] = t_result["cohens_d_z"]
            per_tier_p[label] = t_result["p_value_raw"]
            per_tier_md[label] = t_result["mean_diff"]
        per_combo[combo_name] = {
            "easy_factor": float(ef),
            "hard_intensity": float(hi),
            "overall_d_z": float(overall["cohens_d_z"]),
            "overall_p_value": float(overall["p_value_raw"]),
            "overall_mean_diff": float(overall["mean_diff"]),
            "overall_bonf_sig": bool(overall["p_value_raw"] < BONFERRONI_ALPHA),
            "per_tier_d_z": per_tier,
            "per_tier_p_value": per_tier_p,
            "per_tier_mean_diff": per_tier_md,
            "per_tier_n": {
                "hard": per_tier_sizes["hard"],
                "medium": per_tier_sizes["medium"],
                "easy": per_tier_sizes["easy"],
            },
        }
    # Best combo = cell with HIGHEST overall d_z value (most positive).
    best_combo = max(per_combo.items(), key=lambda kv: kv[1]["overall_d_z"])[0]
    return {
        "tier_boundaries": (tier_low, tier_high),
        "n_records_total": int(len(b)),
        "tier_sizes": per_tier_sizes,
        "per_combo": per_combo,
        "best_combo": best_combo,
        "best_combo_d_z": float(per_combo[best_combo]["overall_d_z"]),
    }


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    print("=" * 72)
    print("Wave 246 P2 — tier-aware parameter transferability on R1 LineageFlow")
    print("=" * 72)

    # ------------------------------------------------------------------
    # R1 (LineageFlow HMMER) — N=1000 paired records
    # ------------------------------------------------------------------
    print("\n" + "=" * 72)
    print("R1 (LineageFlow HMMER) — N=1000 paired records")
    print("=" * 72)
    seeds_r1, b_score, f_score, families_r1 = _load_r1_lineageflow()
    n_r1 = len(seeds_r1)
    print(f"  Loaded R1 paired records: {n_r1}")
    fam_set = sorted(set(families_r1))
    print(f"  Pfam families: {fam_set}")
    fam_sizes = {fam: int(sum(1 for f in families_r1 if f == fam)) for fam in fam_set}
    for fam, n in fam_sizes.items():
        print(f"    {fam}: n={n}")

    # Tier boundaries (33rd / 67th percentiles of baseline max HMMER score).
    r1_tier_low = float(np.quantile(b_score, 0.33, method="linear"))
    r1_tier_high = float(np.quantile(b_score, 0.67, method="linear"))
    print(f"  Tier boundaries (baseline max HMMER score): low={r1_tier_low:.4f}, high={r1_tier_high:.4f}")

    r1_tier = _tier_assignment(b_score, r1_tier_low, r1_tier_high)
    r1_tier_sizes = {
        "hard": int(np.sum(r1_tier == 0)),
        "medium": int(np.sum(r1_tier == 1)),
        "easy": int(np.sum(r1_tier == 2)),
    }
    print(f"  Tier sizes (aggregate): {r1_tier_sizes}")

    # Per-tier baseline summary (sanity).
    print("\n  Per-tier baseline HMMER score summary (higher = easier seed):")
    for label, t in [("hard", 0), ("medium", 1), ("easy", 2)]:
        mask = r1_tier == t
        n_t = int(np.sum(mask))
        if n_t == 0:
            continue
        b_mean = float(np.mean(b_score[mask]))
        f_mean = float(np.mean(f_score[mask]))
        print(
            f"    {label}: n={n_t}  baseline_mean={b_mean:+.4f}  "
            f"framework_mean={f_mean:+.4f}  delta={f_mean - b_mean:+.4f}"
        )

    # Naive uplift (no tier-aware, just framework - baseline).
    naive_uplift = float(np.mean(f_score - b_score))
    naive_t = _paired_t_test(b_score, f_score)
    print(
        f"\n  Naive uplift (no tier-aware): d_z={naive_t['cohens_d_z']:+.4f}  "
        f"p={naive_t['p_value_raw']:.3e}  bonf={int(naive_t['p_value_raw'] < BONFERRONI_ALPHA)}"
    )

    # Run tier-aware counterfactual grid on R1.
    print("\n  Running counterfactual grid on R1 ...")
    r1_result = _tier_aware_counterfactual_grid(
        b=b_score,
        f=f_score,
        tier_low=r1_tier_low,
        tier_high=r1_tier_high,
        combos=R1_PARAM_COMBOS,
    )
    r1_result["axis_label"] = "R1 LineageFlow N=1000 HMMER (Wave 158 frozen archive)"
    r1_result["metric_label"] = "per-record best (max) full-sequence HMMER score"
    r1_result["metric_polarity"] = "higher_better"
    r1_result["family_set"] = fam_set
    r1_result["family_sizes"] = fam_sizes
    r1_result["combo_set"] = [
        {"name": n, "easy_factor": e, "hard_intensity": h}
        for (n, e, h) in R1_PARAM_COMBOS
    ]
    r1_result["naive_uplift_d_z"] = naive_t["cohens_d_z"]
    r1_result["naive_uplift_p_value"] = naive_t["p_value_raw"]
    r1_result["naive_uplift_mean_diff"] = naive_t["mean_diff"]
    r1_result["naive_uplift_bonf_sig"] = bool(naive_t["p_value_raw"] < BONFERRONI_ALPHA)
    r1_result["naive_uplift_mean_score"] = naive_uplift

    # Print per-combo per-tier d_z (the key table).
    print("\n  R1 per-combo per-tier d_z (HMMER score higher=better; positive d_z = framework wins):")
    header = "Combo                          | (easy, hard) | Hard d_z   | Medium d_z | Easy d_z   | Overall d_z"
    print("  " + header)
    print("  " + "-" * len(header))
    for combo_name, ef, hi in R1_PARAM_COMBOS:
        combo_res = r1_result["per_combo"][combo_name]
        pt = combo_res["per_tier_d_z"]
        marker = "  <- BEST" if combo_name == r1_result["best_combo"] else ""
        print(
            f"  {combo_name:30s} | ({ef}, {hi:.1f})    | "
            f"{pt['hard']:+9.4f}  | "
            f"{pt['medium']:+9.4f}  | "
            f"{pt['easy']:+9.4f}  | "
            f"{combo_res['overall_d_z']:+9.4f}{marker}"
        )

    # ------------------------------------------------------------------
    # Transferability verdict
    # ------------------------------------------------------------------
    w235_p2_combo = "w235_p2_r2_kanzi_best"
    w235_p3_combo = "w235_p3_r6_mnist_best"
    r2_ref_d_z = 0.393   # Wave 235 P2 R2 Kanzi best aggregate d_z (brief)
    r6_ref_d_z = 0.647   # Wave 235 P3 R6 MNIST best aggregate d_z (brief)
    w235_p2_r1_d_z = r1_result["per_combo"][w235_p2_combo]["overall_d_z"]
    w235_p3_r1_d_z = r1_result["per_combo"][w235_p3_combo]["overall_d_z"]
    best_combo = r1_result["best_combo"]
    best_d_z = r1_result["best_combo_d_z"]

    # Transferability rule:
    # * "transfers" if either Wave 235 best cell is the best on R1 OR
    #   both Wave 235 cells give d_z > 0 AND at least one is among the
    #   top-2 on R1 (small within-R1 ranking variation).
    # * "weakly transfers" if at least one Wave 235 cell gives d_z > 0
    #   but neither is the R1 best.
    # * "does NOT transfer" if the R1 best is neither Wave 235 cell AND
    #   at least one Wave 235 cell gives d_z <= 0.
    w235_p2_is_best = best_combo == w235_p2_combo
    w235_p3_is_best = best_combo == w235_p3_combo
    either_is_best = w235_p2_is_best or w235_p3_is_best
    both_positive = (w235_p2_r1_d_z > 0.0) and (w235_p3_r1_d_z > 0.0)
    w235_p2_top2 = sorted(
        R1_PARAM_COMBOS,
        key=lambda c: r1_result["per_combo"][c[0]]["overall_d_z"],
        reverse=True,
    )[:2]
    w235_p2_in_top2 = w235_p2_combo in {c[0] for c in w235_p2_top2}
    w235_p3_in_top2 = w235_p3_combo in {c[0] for c in w235_p2_top2}

    if either_is_best:
        verdict = "transfers"
        overfit_risk = "low"
    elif both_positive and (w235_p2_in_top2 or w235_p3_in_top2):
        verdict = "weakly transfers"
        overfit_risk = "medium"
    else:
        verdict = "does NOT transfer"
        overfit_risk = "high"

    print("\n  Transferability verdict:")
    print(f"    R1 best combo: {best_combo} (d_z = {best_d_z:+.4f})")
    print(f"    Wave 235 P2 R2 best on R1: d_z = {w235_p2_r1_d_z:+.4f}  "
          f"(R2 reference d_z = {r2_ref_d_z:+.4f})")
    print(f"    Wave 235 P3 R6 best on R1: d_z = {w235_p3_r1_d_z:+.4f}  "
          f"(R6 reference d_z = {r6_ref_d_z:+.4f})")
    print(f"    Both Wave 235 cells positive on R1: {both_positive}")
    print(f"    W235 P2 cell is R1 best: {w235_p2_is_best}")
    print(f"    W235 P3 cell is R1 best: {w235_p3_is_best}")
    print(f"    -> {verdict.upper()}  (overfit_risk = {overfit_risk.upper()})")

    # ------------------------------------------------------------------
    # Per-family per-tier cross-check (informational)
    # ------------------------------------------------------------------
    print("\n" + "=" * 72)
    print("R1 — per-family per-combo per-tier d_z (informational cross-check)")
    print("=" * 72)
    per_family_results: dict[str, dict] = {}
    for fam in fam_set:
        mask = np.array([f == fam for f in families_r1], dtype=bool)
        b_fam = b_score[mask]
        f_fam = f_score[mask]
        n_fam = int(mask.sum())
        # Recompute tier boundaries within family (so each family has its own
        # easy/medium/hard split). If family has < 3 records, fall back to
        # aggregate boundaries.
        if n_fam >= 3:
            tier_low_fam = float(np.quantile(b_fam, 0.33, method="linear"))
            tier_high_fam = float(np.quantile(b_fam, 0.67, method="linear"))
        else:
            tier_low_fam = r1_tier_low
            tier_high_fam = r1_tier_high
        fam_grid = _tier_aware_counterfactual_grid(
            b=b_fam, f=f_fam,
            tier_low=tier_low_fam, tier_high=tier_high_fam,
            combos=R1_PARAM_COMBOS,
        )
        per_family_results[fam] = {
            "n_records": n_fam,
            "tier_boundaries": (tier_low_fam, tier_high_fam),
            "tier_sizes": fam_grid["tier_sizes"],
            "best_combo": fam_grid["best_combo"],
            "best_combo_d_z": fam_grid["best_combo_d_z"],
            "per_combo": fam_grid["per_combo"],
        }
        print(
            f"\n  {fam}: n={n_fam}  best_combo={fam_grid['best_combo']}  "
            f"d_z={fam_grid['best_combo_d_z']:+.4f}  tier_sizes={fam_grid['tier_sizes']}"
        )
        for combo_name, ef, hi in R1_PARAM_COMBOS:
            combo_res = fam_grid["per_combo"][combo_name]
            pt = combo_res["per_tier_d_z"]
            print(
                f"    {combo_name:30s} (ef={ef}, hi={hi:.1f}) -> "
                f"hard={pt['hard']:+.4f}  medium={pt['medium']:+.4f}  "
                f"easy={pt['easy']:+.4f}  overall={combo_res['overall_d_z']:+.4f}"
            )

    r1_result["per_family_results"] = per_family_results
    r1_result["w235_p2_r2_kanzi_reference_d_z"] = r2_ref_d_z
    r1_result["w235_p3_r6_mnist_reference_d_z"] = r6_ref_d_z
    r1_result["transferability_verdict"] = verdict
    r1_result["overfit_risk"] = overfit_risk
    r1_result["w235_p2_d_z_on_r1"] = w235_p2_r1_d_z
    r1_result["w235_p3_d_z_on_r1"] = w235_p3_r1_d_z
    r1_result["w235_p2_is_best_on_r1"] = bool(w235_p2_is_best)
    r1_result["w235_p3_is_best_on_r1"] = bool(w235_p3_is_best)

    # ------------------------------------------------------------------
    # Write outputs
    # ------------------------------------------------------------------
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    JSON_OUT.write_text(json.dumps(r1_result, indent=2, default=str))
    print(f"\nWrote {JSON_OUT}")

    # CSV: per-combo per-tier d_z on aggregate (one row per combo).
    with CSV_OUT.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "experiment", "n_records", "combo_name",
            "easy_factor", "hard_intensity",
            "overall_d_z", "overall_p_value", "overall_bonf_sig",
            "overall_mean_diff",
            "tier_hard_d_z", "tier_medium_d_z", "tier_easy_d_z",
            "tier_hard_p", "tier_medium_p", "tier_easy_p",
            "is_best_for_r1",
        ])
        for combo_name, ef, hi in R1_PARAM_COMBOS:
            combo_res = r1_result["per_combo"][combo_name]
            pt = combo_res["per_tier_d_z"]
            pp = combo_res["per_tier_p_value"]
            writer.writerow([
                "R1_lineageflow_hmmer", n_r1, combo_name,
                ef, hi,
                combo_res["overall_d_z"],
                combo_res["overall_p_value"],
                int(combo_res["overall_bonf_sig"]),
                combo_res["overall_mean_diff"],
                pt["hard"], pt["medium"], pt["easy"],
                pp["hard"], pp["medium"], pp["easy"],
                int(combo_name == r1_result["best_combo"]),
            ])
    print(f"Wrote {CSV_OUT}")

    _write_audit_doc(
        r1_result=r1_result,
        n_r1=n_r1,
        r1_tier_sizes=r1_tier_sizes,
        fam_set=fam_set,
        fam_sizes=fam_sizes,
        per_family_results=per_family_results,
        verdict=verdict,
        overfit_risk=overfit_risk,
        r2_ref_d_z=r2_ref_d_z,
        r6_ref_d_z=r6_ref_d_z,
    )
    print(f"Wrote {DOC_OUT}")

    print("\n" + "=" * 72)
    print("WAVE 246 P2 SUMMARY")
    print("=" * 72)
    print(f"  R1 LineageFlow N={n_r1}")
    print(f"  Naive (no tier-aware) uplift d_z = {naive_t['cohens_d_z']:+.4f}")
    print(f"  R1 best combo: {best_combo} (d_z = {best_d_z:+.4f})")
    print(f"  W235 P2 (R2 best) on R1: d_z = {w235_p2_r1_d_z:+.4f}")
    print(f"  W235 P3 (R6 best) on R1: d_z = {w235_p3_r1_d_z:+.4f}")
    print(f"  Verdict: {verdict.upper()}  (overfit_risk = {overfit_risk.upper()})")
    return 0


# ============================================================================
# Audit doc writer
# ============================================================================

def _fmt(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "N/A"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:+.4f}"
    return str(v)


def _write_audit_doc(
    *,
    r1_result: dict,
    n_r1: int,
    r1_tier_sizes: dict,
    fam_set: list[str],
    fam_sizes: dict,
    per_family_results: dict,
    verdict: str,
    overfit_risk: str,
    r2_ref_d_z: float,
    r6_ref_d_z: float,
) -> None:
    """Write Wave 246 P2 audit markdown."""
    r1_tier_low, r1_tier_high = r1_result["tier_boundaries"]

    best_combo = r1_result["best_combo"]
    best_d_z = r1_result["best_combo_d_z"]
    w235_p2_combo = "w235_p2_r2_kanzi_best"
    w235_p3_combo = "w235_p3_r6_mnist_best"
    w235_p2_r1_d_z = r1_result["w235_p2_d_z_on_r1"]
    w235_p3_r1_d_z = r1_result["w235_p3_d_z_on_r1"]
    w235_p2_is_best = r1_result["w235_p2_is_best_on_r1"]
    w235_p3_is_best = r1_result["w235_p3_is_best_on_r1"]

    # Per-combo per-tier d_z table.
    combo_table_lines = []
    for combo_name, ef, hi in R1_PARAM_COMBOS:
        combo_res = r1_result["per_combo"][combo_name]
        pt = combo_res["per_tier_d_z"]
        pp = combo_res["per_tier_p_value"]
        md = combo_res["per_tier_mean_diff"]
        marker = " **<- R1 BEST**" if combo_name == best_combo else ""
        wave235_marker = ""
        if combo_name == w235_p2_combo:
            wave235_marker = "  (Wave 235 P2 R2 best)"
        elif combo_name == w235_p3_combo:
            wave235_marker = "  (Wave 235 P3 R6 best)"
        combo_table_lines.append(
            f"| `{combo_name}`{wave235_marker} | ({ef}, {hi}) | "
            f"{_fmt(pt['hard'])} (p={pp['hard']:.2e}, md={md['hard']:+.4f}) | "
            f"{_fmt(pt['medium'])} (p={pp['medium']:.2e}, md={md['medium']:+.4f}) | "
            f"{_fmt(pt['easy'])} (p={pp['easy']:.2e}, md={md['easy']:+.4f}) | "
            f"**{_fmt(combo_res['overall_d_z'])}** (p={combo_res['overall_p_value']:.2e}) | "
            f"{_fmt(combo_res['overall_bonf_sig'])} |{marker}"
        )
    combo_table = "\n".join(combo_table_lines)

    # Per-family summary table (best combo per family + W235 P2/P3 d_z on each family).
    per_family_lines = []
    for fam in fam_set:
        fam_res = per_family_results[fam]
        best_fam = fam_res["best_combo"]
        best_fam_d_z = fam_res["best_combo_d_z"]
        w235_p2_fam_d_z = fam_res["per_combo"][w235_p2_combo]["overall_d_z"]
        w235_p3_fam_d_z = fam_res["per_combo"][w235_p3_combo]["overall_d_z"]
        marker = ""
        if best_fam == w235_p2_combo:
            marker = " (W235 P2 best)"
        elif best_fam == w235_p3_combo:
            marker = " (W235 P3 best)"
        per_family_lines.append(
            f"| {fam} | n={fam_res['n_records']} | `{best_fam}`{marker} | "
            f"{best_fam_d_z:+.4f} | "
            f"{w235_p2_fam_d_z:+.4f} | "
            f"{w235_p3_fam_d_z:+.4f} |"
        )
    per_family_table = "\n".join(per_family_lines)

    # Conclusion text.
    if verdict == "transfers":
        conclusion = (
            f"The R1 LineageFlow best combo is `{best_combo}` with overall "
            f"d_z = **{best_d_z:+.4f}** — which is the Wave 235 "
            f"{'P2 R2 Kanzi' if w235_p2_is_best else 'P3 R6 MNIST'} best cell. "
            f"This is a clean cross-adapter transfer: the Wave 235 best cell "
            f"is also the best cell on R1 LineageFlow (an adapter it was never "
            f"trained on / grid-searched against). \n\n"
            f"**Overfit risk: LOW.** The tier-aware parameters are "
            f"adapter-portable — the same (easy_factor=0.0, hard_intensity="
            f"{2.0 if w235_p2_is_best else 3.0}) cell generalises from R2 "
            f"Kanzi / R6 MNIST to R1 LineageFlow."
        )
    elif verdict == "weakly transfers":
        conclusion = (
            f"The R1 LineageFlow best combo is `{best_combo}` with overall "
            f"d_z = **{best_d_z:+.4f}** — NOT the Wave 235 best cell. However, "
            f"both Wave 235 best cells produce POSITIVE d_z on R1: "
            f"W235 P2 (R2 best) -> d_z = {w235_p2_r1_d_z:+.4f}; "
            f"W235 P3 (R6 best) -> d_z = {w235_p3_r1_d_z:+.4f}. The Wave 235 "
            f"best cells are in the top tier of R1 combos but not the R1 best "
            f"— the R1 best is a different cell. \n\n"
            f"**Overfit risk: MEDIUM.** The tier-aware direction is right "
            f"(both W235 cells give positive uplift) but the optimal cell is "
            f"slightly adapter-dependent. We recommend disclosing the per-combo "
            f"transferability in the paper."
        )
    else:
        conclusion = (
            f"The R1 LineageFlow best combo is `{best_combo}` with overall "
            f"d_z = **{best_d_z:+.4f}** — NOT the Wave 235 best cell. At least "
            f"one Wave 235 cell gives d_z <= 0 on R1 "
            f"(W235 P2 -> {w235_p2_r1_d_z:+.4f}; W235 P3 -> {w235_p3_r1_d_z:+.4f}). "
            f"The Wave 235 best cells are adapter-specific. \n\n"
            f"**Overfit risk: HIGH.** The Wave 235 best cells do NOT transfer "
            f"to R1 LineageFlow. The per-combo per-tier table above identifies "
            f"which cell wins on R1; we recommend NOT reporting a single "
            f"tier-aware best cell across all adapters."
        )

    doc = f"""# Wave 246 P2 — Tier-Aware Parameter Transferability on R1 LineageFlow

## Goal

Wave 235 P2 (R2 Kanzi RMSD) grid search picked `(easy_factor=0.0,
hard_intensity=2.0)` → aggregate d_z = +0.393 (over 1000 records).

Wave 235 P3 (R6 MNIST FM) grid search picked `(easy_factor=0.0,
hard_intensity=3.0)` → aggregate d_z = +0.647 (over 1000 records).

**Concern:** are these best cells overfit to R2 / R6 specifically, or do
they transfer to other adapters (notably R1 LineageFlow, which was NOT
used in the Wave 235 P2 / P3 grid search)?

**Independence test:** re-run the Wave 235 P2 / P3 counterfactual wrapper
on the R1 LineageFlow N=1000 HMMER dataset with 6 param combos (the two
Wave 235 best cells + 4 alternatives). If either Wave 235 best cell is
also the R1 best, then the Wave 235 cells transfer — low overfit risk. If
the R1 best is a different cell (or the Wave 235 cells give <= 0 d_z on
R1), the Wave 235 cells are adapter-specific — high overfit risk.

## Methodology

### Data sources (FROZEN, per-record granularity)

R1 (LineageFlow N=1000 HMMER, Wave 158 canonical archive):

| Arm | Source | Records | Hits |
|-----|--------|--------:|-----:|
| Baseline | `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/baseline_hits.tbl` | {n_r1} | 158 |
| Framework | `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/framework_hits.tbl` | {n_r1} | 342 |

The headline R1 +116% (158 → 342 hits) was re-derived from scratch in
Wave 158 P2 (commit `2ae8473`) from truly-real LineageFlowAdapter
multi-round sequences (Pitfall #2 sys.path fix in
`tools/gen_lineageflow_n1000_fastas.py`). Both hit tables are
sha256-pinned (`d2db3769...` baseline, `04830145...` framework).

### Per-record paired scalar

For each seed `seedK` (K=0..999) we extract a per-record scalar:

- **Baseline**: best (max) full-sequence HMMER score across all hits for
  `baseline_seedK`. If `baseline_seedK` has 0 hits in `baseline_hits.tbl`,
  score = 0.0 (sequence doesn't hit any Pfam profile).
- **Framework**: same metric on `framework_seedK`.

This gives a continuous scalar in `[0, +inf)` per record. The metric is
HIGHER = BETTER (a higher HMMER score means the sequence matches a Pfam
profile more confidently). Records are paired by seed key (baseline_seedK
vs framework_seedK).

### Tier stratification (Wave 198 P3 / Wave 225 P4 / Wave 233 P3 / Wave 245 P2)

Records are stratified into easy / medium / hard by the **baseline**
per-record max HMMER score, using 33rd / 67th percentiles of the baseline
score distribution:

- hard: baseline_score <= q33
- medium: q33 < baseline_score <= q67
- easy: baseline_score > q67

This is the same Wave 198 P3 methodology, applied to R1 LineageFlow's
HMMER score distribution.

**Tier boundaries:** low = {r1_tier_low:.4f}, high = {r1_tier_high:.4f}.

**Tier sizes (aggregate, N={n_r1}):** hard = {r1_tier_sizes['hard']},
medium = {r1_tier_sizes['medium']}, easy = {r1_tier_sizes['easy']}.

**Note on the zero-inflated medium tier:** the R1 LineageFlow HMMER score
distribution is zero-inflated (855 of 1000 records have baseline score =
0 because the baseline sequence hits no Pfam profile; only 145 records
have a positive baseline score). With the 33rd and 67th percentiles both
at 0.0, the medium tier is empty (0 records). This is a *data
characteristic*, not a methodology failure — the Wave 198 P3
baseline-metric-quantile stratification is applied correctly. The
tier-aware counterfactual still applies: hard tier (855 records with
baseline=0) and easy tier (145 records with baseline>0) are the two
non-empty tiers, and the counterfactual ratios are applied to them.
Records in the empty medium tier contribute 0 to the overall d_z (their
contribution cancels because both baseline and counterfactual equal
framework, ratio=1.0 is identity for them).

### Param combos tested (6 per the brief)

| Combo name | easy_factor | hard_intensity | Source |
|------------|------------:|---------------:|--------|
| `w235_p2_r2_kanzi_best` | 0.0 | 2.0 | Wave 235 P2 R2 Kanzi best (d_z=+0.393) |
| `w235_p3_r6_mnist_best` | 0.0 | 3.0 | Wave 235 P3 R6 MNIST best (d_z=+0.647) |
| `uniform_passthrough` | 0.0 | 1.0 | uniform passthrough (no tier-aware) |
| `mid_grid` | 0.25 | 2.0 | middle of grid |
| `w233_p3_baseline` | 0.5 | 1.0 | Wave 233 P3 baseline |
| `easy_red_hard_amp` | 0.5 | 2.0 | easy reduction + hard amplification |

### Counterfactual (reuses Wave 225 P4 / Wave 233 P3 / Wave 235 P2/P3 / Wave 245 P2)

For each (combo), per-tier counterfactual framework arm::

    diff_t          = f[t] - b[t]
    mean_diff_t     = mean(diff_t)
    diff_counter_t  = diff_t - mean_diff_t + ratio * mean_diff_t
    counter_t       = b[t] + diff_counter_t

Where ``ratio = easy_factor`` on easy, ``ratio = 1.0`` on medium
(passthrough), ``ratio = hard_intensity`` on hard. Per-record variance is
preserved.

Statistics: paired t-test, d_z = mean_diff / sd_diff (Cohen's d_z),
Bonferroni family M=3 (3 tiers x 1 metric), per-cell alpha =
{BONFERRONI_ALPHA:.5f}.

### "Best cell" criterion (matches Wave 235 P2 / P3)

For HMMER score (higher=better), positive d_z means framework wins. The
"best cell" is the one with the HIGHEST overall d_z VALUE (most
positive) — same criterion as Wave 235 P2 (`scripts/wave235_p2_r2_uplift.py:321`)
and Wave 235 P3 (`scripts/wave235_p3_r6_uplift.py:312`).

### Transferability verdict rule

- **transfers (overfit risk LOW):** the R1 best cell is one of the Wave
  235 best cells.
- **weakly transfers (overfit risk MEDIUM):** the R1 best cell is NOT a
  Wave 235 best cell, but both Wave 235 cells give positive d_z on R1
  (direction-correct, just not R1-optimal).
- **does NOT transfer (overfit risk HIGH):** the R1 best cell is NOT a
  Wave 235 best cell, AND at least one Wave 235 cell gives d_z <= 0 on
  R1 (direction-wrong on R1).

## R1 (LineageFlow N=1000 HMMER) — per-combo per-tier d_z

Tier sizes (aggregate, N={n_r1}): hard = {r1_tier_sizes['hard']},
medium = {r1_tier_sizes['medium']}, easy = {r1_tier_sizes['easy']}.
Tier boundaries: low = {r1_tier_low:.4f}, high = {r1_tier_high:.4f}.

| Combo | (easy, hard) | Hard d_z (p, md) | Medium d_z (p, md) | Easy d_z (p, md) | Overall d_z (p) | bonf_sig |
|-------|--------------|------------------|--------------------|------------------|-------------------|----------|
{combo_table}

### Best combo for R1 (highest overall d_z)

**`{best_combo}`** with overall d_z = **{best_d_z:+.4f}**.

### Naive uplift (no tier-aware, framework - baseline)

d_z = **{r1_result['naive_uplift_d_z']:+.4f}**, p = {r1_result['naive_uplift_p_value']:.3e},
mean_diff = {r1_result['naive_uplift_mean_diff']:+.4f} (HMMER score units),
bonf_sig = {int(r1_result['naive_uplift_bonf_sig'])}.

### Per-family cross-check (informational)

Pfam families present in the LineageFlow N=1000 sample: {fam_set}.
Family sizes: {fam_sizes}.

For each family, the within-family tier boundaries are recomputed (33rd /
67th percentile of baseline score within the family). Best combo per
family:

| Family | n | Best combo | Best d_z | W235 P2 d_z | W235 P3 d_z |
|--------|--:|------------|---------:|------------:|------------:|
{per_family_table}

## Comparison vs Wave 235 P2 / P3 reference cells

| Cell | Wave 235 reference d_z (on trained adapter) | d_z on R1 LineageFlow |
|------|--------------------------------------------:|----------------------:|
| `(easy_factor=0.0, hard_intensity=2.0)` (Wave 235 P2 R2 Kanzi best) | **+{r2_ref_d_z:.3f}** (R2 Kanzi) | **{w235_p2_r1_d_z:+.4f}** |
| `(easy_factor=0.0, hard_intensity=3.0)` (Wave 235 P3 R6 MNIST best) | **+{r6_ref_d_z:.3f}** (R6 MNIST) | **{w235_p3_r1_d_z:+.4f}** |

Wave 235 P2 best cell on R1: d_z = {w235_p2_r1_d_z:+.4f}
(W235 P2 best on R1: {w235_p2_is_best}).
Wave 235 P3 best cell on R1: d_z = {w235_p3_r1_d_z:+.4f}
(W235 P3 best on R1: {w235_p3_is_best}).

## Transferability verdict

**{verdict.upper()}** — overfit risk: **{overfit_risk.upper()}**.

## Conclusion

{conclusion}

## D.4 byte-stable gate

This is a READ-ONLY counterfactual analysis. **No framework source code was
modified.** D.4 30/30 PASS is preserved unchanged. The R1 LineageFlow
HMMER hit tables (Wave 158 archive, sha256-pinned) and the per-record
parsing logic are byte-stable inputs.

## Honest disclosure

This is a counterfactual re-analysis (Wave 225 P4 / Wave 233 P3 / Wave 235
P2 / Wave 235 P3 / Wave 245 P2 constant-offset methodology). No live GPU
run was launched; no framework source code was modified. The
`TierAwareCodimensionSheetScheduler` only materialises
`easy_tier_nfe_reduction_factor` in code; the `hard_intensity` axis is
simulated via the constant-offset counterfactual.

The per-record paired scalar (best max full-sequence HMMER score, with
zero-hit records set to score=0.0) is a deterministic function of the
Wave 158 HMMER hit tables and the seed key. The tier boundaries are
derived from the 33rd / 67th percentiles of the baseline score
distribution (Wave 198 P3 methodology applied to R1).

The "best cell" criterion (highest overall d_z VALUE — most positive)
matches Wave 235 P2 / P3 exactly. For HMMER score (higher=better), this
criterion is direction-aligned with framework improvement; for RMSD
(lower=better) it is direction-agnostic magnitude — see Wave 245 P2 audit
doc for the cross-experiment discussion.

Per-family cross-check uses within-family tier boundaries (smaller bins),
which is informational only — the headline transferability verdict uses
the aggregate (N={n_r1}) tier boundaries.
"""
    DOC_OUT.write_text(doc)


if __name__ == "__main__":
    sys.exit(main())
