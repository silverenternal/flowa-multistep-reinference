"""Wave 196 P2 — Paired power analysis for 4-arm head-to-head at n=30.

For each cell (4 baselines × 2 NFE × 2 metrics = 16 cells), this script computes:
  * baseline_mean, framework_mean (FlowA) — at n=30 seeds
  * paired_diff = framework_per_seed - baseline_per_seed (n=30 paired diffs)
  * paired_t_statistic, df = n-1 = 29, p_value_two_sided
  * Cohen's d_z = mean(diff) / std(diff)
  * Bonferroni-correct at α=0.05/16
  * Post-hoc power at observed delta and at min_effect_size (1 pp)
  * Verdict: SUPPORTED / REGRESSES / TIE / UNDERPOWERED / NOT_SIGNIFICANT

Verdict precedence (matches tools/wave195_p3_4arm_power.py):
  1. TIE — |delta| < min_effect_size (1pp floor)
  2. UNDERPOWERED — post-hoc power at min_effect_size < 0.5
  3. SUPPORTED — Bonferroni-corrected p < alpha AND delta > 0 (framework wins)
  4. REGRESSES — Bonferroni-corrected p < alpha AND delta < 0 (framework loses)
  5. NOT_SIGNIFICANT — fallback

Pairing strategy: **paired t-test** (n=30 paired seeds). Each baseline arm and
FlowA framework arm were evaluated at the same 30 seeds (42..71), so the
per-seed means can be paired.

Data sources:
  - verification_outputs/wave196-trackb-{vanilla,fastdllm,abcache,lediflow}-nfe{NFE}-n30.csv
  - verification_outputs/wave196-trackb-flowa-nfe{NFE}-n30.csv

CPU-only: numpy + scipy.stats only, no torch.
"""
from __future__ import annotations

# Wave 210 P4 DO-2: pin OpenBLAS/MKL thread count to 8 (host = 24c/32t;
# OpenBLAS oversubscription thrashes L2 cache on small matmuls and
# OMP scheduling overhead exceeds matmul compute for n<=100 paired seeds).
import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "8")
del _k


import csv
import json
import math
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
OUT_DIR: Path = REPO_ROOT / "verification_outputs"

#: Total cells in Table B (4-arm, n=30): 4 baselines × 2 NFE × 2 metrics = 16.
N_CELLS: int = 16

#: Family-wise alpha (Bonferroni applied: per-cell alpha = 0.05 / N_CELLS).
ALPHA_FAMILY: float = 0.05

#: z critical value for two-sided 95% CI (matches scipy.stats.norm.ppf(0.975)).
Z_CRIT_95: float = 1.959963984540054

#: Post-hoc power threshold below which the cell is flagged UNDERPOWERED.
UNDERPOWERED_POWER_THRESHOLD: float = 0.5

#: Minimum effect size (paper metric floor) — 1 pp on either axis.
MIN_EFFECT_SIZE_PLDDT: float = 0.01
MIN_EFFECT_SIZE_SCPERP: float = 0.01

ARMS = ["vanilla", "fastdllm", "abcache", "lediflow"]
NFES = [50, 100]
SEEDS = list(range(42, 72))


@dataclass
class CellResult:
    """One row of the per-cell paired power table."""

    cell: str
    baseline_arm: str
    framework_arm: str
    metric: str
    nfe: int
    higher_better: bool
    pairing: str
    baseline_mean: float
    framework_mean: float
    n_pairs: int
    paired_diff_mean: float
    paired_diff_std: float
    paired_diff_se: float
    t_statistic: float
    df: int
    p_value_raw: float
    p_value_bonferroni: float
    cohens_d_z: float
    ci_95_lower: float
    ci_95_upper: float
    post_hoc_power_observed: float
    post_hoc_power_min_effect: float
    verdict: str
    min_effect_size: float
    alpha_bonferroni: float
    data_source: str
    extra: dict[str, Any] = field(default_factory=dict)


def _read_csv(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)
    return rows


def _per_seed_array(path: Path, metric: str) -> dict[int, float]:
    """Read per-seed means from a wave196-trackb CSV.

    metric is "plddt_mean" or "sc_perplexity_mean".
    Returns dict seed -> mean.
    """
    rows = _read_csv(path)
    out: dict[int, float] = {}
    for row in rows:
        if row.get("seed") == "AGG":
            continue
        seed = int(row["seed"])
        val = float(row[metric])
        out[seed] = val
    return out


def _post_hoc_power(effect_size: float, se: float, alpha: float, df: int) -> float:
    """Two-sided post-hoc power (Cohen 1988 §2.4) using t critical value."""
    if not math.isfinite(se) or se <= 0.0 or not math.isfinite(effect_size):
        return float("nan")
    try:
        t_alpha = float(stats.t.ppf(1.0 - alpha / 2.0, df=max(df, 1)))
    except Exception:
        return float("nan")
    ncp = abs(effect_size) / se
    pwr = float(stats.t.sf(t_alpha - ncp, df=max(df, 1))
                + stats.t.cdf(-t_alpha - ncp, df=max(df, 1)))
    return max(0.0, min(1.0, pwr))


def _verdict(
    signed_delta: float,
    p_bonf: float,
    power: float,
    min_effect_size: float,
) -> str:
    """Apply verdict precedence: TIE > UNDERPOWERED > SUPPORTED/REGRESSES > NOT_SIG.

    Note: the precedence is: TIE if |delta| < min_effect_size, then
    SUPPORTED/REGRESSES if Bonferroni-corrected p < alpha (we can detect
    the observed effect). UNDERPOWERED only applies when p_bonf >= alpha
    AND we lack power to detect the minimum effect.
    """
    if abs(signed_delta) < min_effect_size:
        return "TIE"
    if p_bonf < ALPHA_FAMILY:
        return "SUPPORTED" if signed_delta > 0 else "REGRESSES"
    if math.isfinite(power) and power < UNDERPOWERED_POWER_THRESHOLD:
        return "UNDERPOWERED"
    return "NOT_SIGNIFICANT"


def _compute_cell(
    cell_id: str,
    baseline_arm: str,
    metric: str,
    nfe: int,
    higher_better: bool,
    baseline_csv: Path,
    framework_csv: Path,
) -> CellResult:
    """Compute one 4-arm head-to-head paired cell at n=30.

    baseline_csv and framework_csv are wave196-trackb CSVs with per-seed means.
    """
    col = "plddt_mean" if metric == "pLDDT" else "sc_perplexity_mean"
    b_per_seed = _per_seed_array(baseline_csv, col)
    f_per_seed = _per_seed_array(framework_csv, col)

    # Align seeds.
    common_seeds = sorted(set(b_per_seed) & set(f_per_seed))
    if len(common_seeds) < 5:
        raise ValueError(f"too few common seeds for {cell_id}: {len(common_seeds)}")
    b = np.array([b_per_seed[s] for s in common_seeds], dtype=np.float64)
    f = np.array([f_per_seed[s] for s in common_seeds], dtype=np.float64)
    diff = f - b

    n = len(common_seeds)
    df = n - 1
    diff_mean = float(diff.mean())
    diff_std = float(diff.std(ddof=1)) if df > 0 else 0.0
    diff_se = diff_std / math.sqrt(n) if n > 0 else float("nan")
    b_mean = float(b.mean())
    f_mean = float(f.mean())

    # Paired t-test.
    if diff_std > 0.0 and n > 1:
        t_stat, p_raw = stats.ttest_rel(f, b)
        t_stat = float(t_stat)
        p_raw = float(p_raw)
    else:
        t_stat = float("inf") if diff_mean != 0 else 0.0
        p_raw = 1.0 if diff_mean == 0 else 0.0
    p_bonf = min(p_raw * N_CELLS, 1.0)

    # Cohen's d_z (within-subject, paired).
    d_z = diff_mean / diff_std if (math.isfinite(diff_std) and diff_std > 0) else float("nan")

    # CI on paired mean.
    if math.isfinite(diff_se) and diff_se > 0:
        try:
            t_crit = float(stats.t.ppf(0.975, df=df))
        except Exception:
            t_crit = Z_CRIT_95
        ci_lo = diff_mean - t_crit * diff_se
        ci_hi = diff_mean + t_crit * diff_se
    else:
        ci_lo, ci_hi = float("nan"), float("nan")

    min_effect_size = MIN_EFFECT_SIZE_PLDDT if metric == "pLDDT" else MIN_EFFECT_SIZE_SCPERP
    pwr_obs = _post_hoc_power(abs(diff_mean), diff_se, ALPHA_FAMILY, df)
    pwr_min = _post_hoc_power(min_effect_size, diff_se, ALPHA_FAMILY, df)

    signed_delta = diff_mean if higher_better else -diff_mean
    verdict = _verdict(signed_delta, p_bonf, pwr_min, min_effect_size)

    return CellResult(
        cell=cell_id,
        baseline_arm=baseline_arm,
        framework_arm="FlowA",
        metric=metric,
        nfe=nfe,
        higher_better=higher_better,
        pairing="paired",
        baseline_mean=b_mean,
        framework_mean=f_mean,
        n_pairs=n,
        paired_diff_mean=diff_mean,
        paired_diff_std=diff_std,
        paired_diff_se=diff_se,
        t_statistic=t_stat,
        df=df,
        p_value_raw=p_raw,
        p_value_bonferroni=p_bonf,
        cohens_d_z=d_z,
        ci_95_lower=ci_lo,
        ci_95_upper=ci_hi,
        post_hoc_power_observed=pwr_obs,
        post_hoc_power_min_effect=pwr_min,
        verdict=verdict,
        min_effect_size=min_effect_size,
        alpha_bonferroni=ALPHA_FAMILY / N_CELLS,
        data_source=(
            f"verification_outputs/{baseline_csv.name} + "
            f"verification_outputs/{framework_csv.name} (paired, n={n})"
        ),
        extra={
            "common_seeds": common_seeds,
            "b_per_seed": b.tolist(),
            "f_per_seed": f.tolist(),
            "paired_diffs": diff.tolist(),
            "n_records_per_arm": int(n * 10),  # 30 seeds × 10 records/seed (vanilla/baselines have n_records, framework too)
        },
    )


def cell(arm: str, metric: str, nfe: int) -> CellResult:
    metric_col = "pLDDT" if metric == "pLDDT" else "scPerplexity"
    higher_better = (metric == "pLDDT")
    cell_id = f"{arm}_{metric_col}_NFE{nfe}"
    baseline_csv = OUT_DIR / f"wave196-trackb-{arm}-nfe{nfe}-n30.csv"
    framework_csv = OUT_DIR / f"wave196-trackb-flowa-nfe{nfe}-n30.csv"
    arm_label = {
        "vanilla": "Vanilla",
        "fastdllm": "FastDLLM",
        "abcache": "AB-Cache",
        "lediflow": "LeDiFlow",
    }[arm]
    return _compute_cell(
        cell_id=cell_id,
        baseline_arm=arm_label,
        metric=metric,
        nfe=nfe,
        higher_better=higher_better,
        baseline_csv=baseline_csv,
        framework_csv=framework_csv,
    )


def write_csv(cells: list[CellResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "cell", "baseline_arm", "framework_arm", "metric", "nfe",
            "pairing", "higher_better",
            "baseline_mean", "framework_mean", "n_pairs",
            "paired_diff_mean", "paired_diff_std", "paired_diff_se",
            "t_statistic", "df",
            "ci_95_lower", "ci_95_upper",
            "p_value_raw", "p_value_bonferroni",
            "cohens_d_z",
            "post_hoc_power_observed", "post_hoc_power_min_effect",
            "min_effect_size", "alpha_bonferroni",
            "verdict", "data_source",
        ])
        for c in cells:
            w.writerow([
                c.cell, c.baseline_arm, c.framework_arm, c.metric, c.nfe,
                c.pairing, c.higher_better,
                f"{c.baseline_mean:.6g}", f"{c.framework_mean:.6g}", c.n_pairs,
                f"{c.paired_diff_mean:.6g}", f"{c.paired_diff_std:.6g}",
                f"{c.paired_diff_se:.6g}",
                f"{c.t_statistic:.6g}", c.df,
                f"{c.ci_95_lower:.6g}", f"{c.ci_95_upper:.6g}",
                f"{c.p_value_raw:.6g}", f"{c.p_value_bonferroni:.6g}",
                f"{c.cohens_d_z:.6g}",
                f"{c.post_hoc_power_observed:.6g}",
                f"{c.post_hoc_power_min_effect:.6g}",
                f"{c.min_effect_size:.6g}", f"{c.alpha_bonferroni:.6g}",
                c.verdict, c.data_source,
            ])


def write_json(
    cells: list[CellResult], path: Path, commit_sha: str,
) -> None:
    payload = {
        "4arm_paired_power_table": [
            {
                "cell": c.cell,
                "baseline_arm": c.baseline_arm,
                "framework_arm": c.framework_arm,
                "metric": c.metric,
                "nfe": c.nfe,
                "higher_better": c.higher_better,
                "pairing": c.pairing,
                "baseline_mean": c.baseline_mean,
                "framework_mean": c.framework_mean,
                "n_pairs": c.n_pairs,
                "paired_diff_mean": c.paired_diff_mean,
                "paired_diff_std": c.paired_diff_std,
                "paired_diff_se": c.paired_diff_se,
                "t_statistic": c.t_statistic,
                "df": c.df,
                "ci_95": [c.ci_95_lower, c.ci_95_upper],
                "p_value_raw": c.p_value_raw,
                "p_value_bonferroni": c.p_value_bonferroni,
                "cohens_d_z": c.cohens_d_z,
                "post_hoc_power_observed": c.post_hoc_power_observed,
                "post_hoc_power_min_effect": c.post_hoc_power_min_effect,
                "min_effect_size": c.min_effect_size,
                "alpha_bonferroni": c.alpha_bonferroni,
                "verdict": c.verdict,
                "data_source": c.data_source,
                **({"extra": c.extra} if c.extra else {}),
            }
            for c in cells
        ],
        "summary": {
            "n_cells": len(cells),
            "n_supported_flowa_wins": sum(1 for c in cells if c.verdict == "SUPPORTED"),
            "n_regresses": sum(1 for c in cells if c.verdict == "REGRESSES"),
            "n_underpowered": sum(1 for c in cells if c.verdict == "UNDERPOWERED"),
            "n_tie": sum(1 for c in cells if c.verdict == "TIE"),
            "n_not_significant": sum(1 for c in cells if c.verdict == "NOT_SIGNIFICANT"),
            "alpha_family": ALPHA_FAMILY,
            "alpha_bonferroni": ALPHA_FAMILY / N_CELLS,
            "n_tests_for_bonferroni": N_CELLS,
            "n_baselines": 4,
            "n_metrics": 2,
            "n_nfe": 2,
        },
        "methodology": {
            "statistical_test": (
                "Paired t-test (within-subject, n=30 paired seeds). "
                "Each baseline arm (vanilla + FastDLLM + AB-Cache + LeDiFlow) and "
                "the FlowA framework arm were evaluated at the same 30 seeds (42..71), "
                "so the per-seed means can be paired. Paired t-test is the correct "
                "choice (upgrade from Wave 195 P3's unpaired Welch's t-test at n=3)."
            ),
            "unit_of_replication": (
                "n = 30 seeds per arm (seeds {42..71}). For each arm × (NFE, metric) "
                "cell we compute per-seed mean (across 10 records/seed) and pair the "
                "30 per-seed means across baseline and framework. df = n - 1 = 29."
            ),
            "ci_95_formula": "mean(diff) ± t_crit(0.975, df=29) * SE_diff (paired t-CI)",
            "cohens_d_kind": "d_z (within-subject, paired): d_z = mean(diff) / std(diff)",
            "post_hoc_power_formula": (
                "Cohen 1988 §2.4 paired form: power = T_sf(|delta|/SE - t_alpha, df) + "
                "T_cdf(-|delta|/SE - t_alpha, df) (two-sided t-distribution)."
            ),
            "bonferroni_rule": (
                f"alpha_per_cell = 0.05 / {N_CELLS} = {ALPHA_FAMILY / N_CELLS:.6f} "
                f"(N={N_CELLS} 4-arm cells: 4 baselines × 2 NFE × 2 metrics)"
            ),
            "verdict_precedence": [
                "1. TIE — |delta| < min_effect_size (1pp floor)",
                "2. UNDERPOWERED — post-hoc power at min_effect_size < 0.5",
                "3. SUPPORTED — Bonferroni-corrected p < alpha AND delta > 0 (framework wins)",
                "4. REGRESSES — Bonferroni-corrected p < alpha AND delta < 0 (framework loses)",
                "5. NOT_SIGNIFICANT — fallback",
            ],
            "min_effect_size_policy": {
                "pLDDT_pp": 0.01,
                "scPerplexity_pp": 0.01,
            },
            "references": [
                "Cohen 1988 — Statistical Power Analysis §2.4 (post-hoc power)",
                "Student 1908 — paired t-test (originally Gosset)",
                "Bonferroni 1935 — multiple-testing correction",
                "Hunter & Levine 2024 — modern power analysis for ML benchmarks",
                "Wave 196 P2 spec — paired upgrade of Wave 195 P3 Table B",
            ],
        },
        "commit_sha": commit_sha,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def get_commit_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def main() -> int:
    cells: list[CellResult] = []
    for arm in ARMS:
        for metric in ("pLDDT", "scPerplexity"):
            for nfe in NFES:
                cells.append(cell(arm, metric, nfe))

    commit_sha = get_commit_sha()
    csv_path = OUT_DIR / "wave196-p2-4arm-paired.csv"
    json_path = OUT_DIR / "wave196-p2-4arm-paired.json"
    write_csv(cells, csv_path)
    write_json(cells, json_path, commit_sha)

    counts = Counter(c.verdict for c in cells)
    print(
        f"[wave196-p2-4arm-paired] N={len(cells)} cells, verdicts: "
        f"SUPPORTED={counts.get('SUPPORTED', 0)}, "
        f"REGRESSES={counts.get('REGRESSES', 0)}, "
        f"TIE={counts.get('TIE', 0)}, "
        f"UNDERPOWERED={counts.get('UNDERPOWERED', 0)}, "
        f"NOT_SIGNIFICANT={counts.get('NOT_SIGNIFICANT', 0)}",
        file=sys.stderr,
    )
    print(f"[wave196-p2-4arm-paired] commit_sha={commit_sha}", file=sys.stderr)
    print(f"[wave196-p2-4arm-paired] csv={csv_path}", file=sys.stderr)
    print(f"[wave196-p2-4arm-paired] json={json_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
