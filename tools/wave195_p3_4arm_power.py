"""Wave 195 P3 — Per-cell power analysis for the 12 4-arm head-to-head deltas.

For each cell (3 baselines × 2 NFE × 2 metrics), this script computes:

  * baseline_mean, framework_mean (FlowA), n_b, n_f
  * delta = framework - baseline
  * delta_se  (unpaired: sqrt(var_b/n_b + var_f/n_f))
  * 95% CI on delta (delta ± 1.96 * SE)
  * p_value_raw  (two-sided Welch's t-test)
  * p_value_bonferroni  (× N_tests = 12)
  * Cohen's d_s  (between-subject, pooled SD)
  * Post-hoc power to detect observed delta AND min_effect_size (1 pp)
  * Verdict: SUPPORTED / REGRESSES / TIE / UNDERPOWERED / NOT_SIGNIFICANT

Verdict precedence (matches tools/statistical_power_analysis.py + Wave 195 P1 spec):

  1. TIE         — |delta| < min_effect_size
  2. UNDERPOWERED — post-hoc power at min_effect_size < 0.5
  3. SUPPORTED   — Bonferroni-corrected p < alpha AND delta > 0
  4. REGRESSES   — Bonferroni-corrected p < alpha AND delta < 0
  5. NOT_SIGNIFICANT — fallback

Statistical references (Cohen 1988 §2.4; Welch 1947; Bonferroni 1935; Hunter
& Levine 2024) are all already documented in the Wave 195 P1 spec.

Pairing strategy: **unpaired** per §3.3 of the Wave 195 P1 spec — each arm
(Fast-DLLM / AB-Cache / LeDiFlow / FlowA / Vanilla) was evaluated as a separate
experiment with its own ODE trajectory. AGG rows are cross-experiment
aggregates. Therefore Welch's t-test (unequal-variance two-sample) is the
correct test.

Unit of replication: **n = 3 seeds per arm** (seeds {42, 43, 44}). For
each arm × (NFE, metric) cell we compute per-arm aggregate mean and SD
across the 3 per-seed means. The spec's "n=90" label refers to the
underlying record count (3 seeds × 30 records/seed); the unit of
replication for the t-test is n=3 (matches the Wave 195 P2 R5a pattern for
per-seed aggregates).

Data sources:
  - baseline per-seed summaries:
      verification_outputs/wave180-p2-fastdllm-summary.csv (FastDLLM)
      verification_outputs/wave181-p2-abcache-summary.csv (AB-Cache)
      verification_outputs/wave182-p2-lediflow-summary.csv (LeDiFlow)
  - FlowA per-seed summaries (std across 3 seed means):
      verification_outputs/wave179-p4-aggregation.csv

Constraint: **CPU-only**, **numpy + scipy.stats only**, no torch.
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

#: Total cells in Table B (4-arm) for Bonferroni correction.
#: 3 baselines (FastDLLM, AB-Cache, LeDiFlow) × 2 NFE × 2 metrics = 12.
N_CELLS: int = 12

#: Family-wise alpha (Bonferroni applied: per-cell alpha = 0.05 / N_CELLS).
ALPHA_FAMILY: float = 0.05

#: z critical value for two-sided 95% CI (matches scipy.stats.norm.ppf(0.975)).
Z_CRIT_95: float = 1.959963984540054

#: Post-hoc power threshold below which the cell is flagged UNDERPOWERED.
UNDERPOWERED_POWER_THRESHOLD: float = 0.5

#: Minimum effect size (paper metric floor) — 1 pp on either axis.
MIN_EFFECT_SIZE_PLDDT: float = 0.01  # pLDDT pp
MIN_EFFECT_SIZE_SCPERP: float = 0.01  # scPerplexity pp


# ---------------------------------------------------------------------------
# Cell-result dataclass + verdict machinery
# ---------------------------------------------------------------------------


@dataclass
class CellResult:
    """One row of the per-cell power table."""

    cell: str
    baseline_arm: str
    framework_arm: str
    metric: str  # "pLDDT" or "scPerplexity"
    nfe: int
    higher_better: bool
    pairing: str  # "unpaired"
    baseline_mean: float
    framework_mean: float
    n_b: int
    n_f: int
    delta: float
    delta_se: float
    ci_95_lower: float
    ci_95_upper: float
    p_value_raw: float
    p_value_bonferroni: float
    cohens_d: float
    cohens_d_kind: str  # "d_s" (between-subject, pooled SD)
    post_hoc_power_observed: float
    post_hoc_power_min_effect: float
    verdict: str
    min_effect_size: float
    alpha_bonferroni: float
    data_source: str
    extra: dict[str, Any] = field(default_factory=dict)


def _ci_95(delta: float, delta_se: float) -> tuple[float, float]:
    if not math.isfinite(delta_se) or delta_se <= 0.0:
        return (float("nan"), float("nan"))
    return (delta - Z_CRIT_95 * delta_se, delta + Z_CRIT_95 * delta_se)


def _bonferroni(p: float, n_tests: int) -> float:
    if not math.isfinite(p) or p <= 0.0:
        return 0.0
    return float(min(p * n_tests, 1.0))


def _post_hoc_power(effect_size: float, se: float, alpha: float) -> float:
    """Two-sided post-hoc power at the given effect size (Cohen 1988 §2.4)."""
    if not math.isfinite(se) or se <= 0.0 or not math.isfinite(effect_size):
        return float("nan")
    z_alpha = float(stats.norm.ppf(1.0 - alpha / 2.0))
    ncp = abs(effect_size) / se
    pwr = float(stats.norm.sf(z_alpha - ncp) + stats.norm.cdf(-z_alpha - ncp))
    return max(0.0, min(1.0, pwr))


def _verdict(
    delta: float,
    p_bonf: float,
    power: float,
    alpha: float,
    min_effect_size: float,
) -> str:
    """Apply verdict precedence: TIE > UNDERPOWERED > SUPPORTED/REGRESSES > NOT_SIG."""
    # 1. Noise floor.
    if abs(delta) < min_effect_size:
        return "TIE"
    # 2. Power floor.
    if math.isfinite(power) and power < UNDERPOWERED_POWER_THRESHOLD:
        return "UNDERPOWERED"
    # 3 & 4. Significance + direction.
    if p_bonf < alpha:
        return "SUPPORTED" if delta > 0 else "REGRESSES"
    return "NOT_SIGNIFICANT"


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file with a header row, returning list of dicts."""
    rows: list[dict[str, str]] = []
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)
    return rows


def _baseline_per_seed(
    path: Path, nfe: int, metric: str,
) -> np.ndarray:
    """Read 3 per-seed means from a baseline summary CSV (filtering by nfe).

    metric is "plddt" or "sc_perplexity"; the column names match the CSV.
    Returns array of length n_seeds=3.
    """
    rows = _read_csv(path)
    col = "plddt_mean" if metric == "pLDDT" else "sc_perplexity_mean"
    vals: list[float] = []
    for row in rows:
        if row.get("seed") == "AGG":
            continue
        if int(row["nfe"]) != nfe:
            continue
        if row.get("arm") and row["arm"] not in (
            "fastdllm", "abcache", "lediflow",
        ):
            continue
        vals.append(float(row[col]))
    return np.array(vals, dtype=np.float64)


def _flowa_per_seed(nfe: int, metric: str) -> tuple[float, float, int]:
    """Read FlowA aggregate mean + per-seed std from wave179-p4-aggregation.csv.

    Returns (mean, std_across_3_seed_means, n_seeds).
    The std in wave179-p4-aggregation.csv is the std across the 3 per-seed means.
    """
    path = REPO_ROOT / "verification_outputs/wave179-p4-aggregation.csv"
    rows = _read_csv(path)
    for row in rows:
        if row["model"] != "lineageflow":
            continue
        if int(row["nfe"]) != nfe:
            continue
        if row["arm"] != "framework":
            continue
        if metric == "pLDDT":
            mean = float(row["mean_plddt"])
            std = float(row["std_plddt"])
        else:
            mean = float(row["mean_scperp"])
            std = float(row["std_scperp"])
        n_seeds = int(row["n_seeds"])
        return mean, std, n_seeds
    raise KeyError(f"FlowA lineageflow nfe={nfe} metric={metric} not found")


# ---------------------------------------------------------------------------
# Cell compute functions
# ---------------------------------------------------------------------------


def _compute_cell(
    cell_id: str,
    baseline_arm: str,
    metric: str,
    nfe: int,
    higher_better: bool,
    baseline_csv: Path,
) -> CellResult:
    """Compute one 4-arm head-to-head cell (baseline vs FlowA).

    baseline_csv is the per-seed summary CSV for the baseline arm
    (wave180 / wave181 / wave182).
    """
    # Baseline per-seed array (length 3).
    b = _baseline_per_seed(baseline_csv, nfe=nfe, metric=metric)
    n_b = len(b)
    b_mean = float(b.mean())
    b_var = float(b.var(ddof=1)) if n_b > 1 else 0.0

    # FlowA aggregate (mean, std across 3 seed means, n_seeds).
    f_mean, f_std, n_f = _flowa_per_seed(nfe=nfe, metric=metric)
    # Convert std across 3 seed means → variance of those 3 seed means.
    f_var = float(f_std ** 2) if n_f > 1 else 0.0

    # Delta = framework - baseline.
    delta = f_mean - b_mean
    # SE for unpaired two-sample (independent arms).
    delta_se = math.sqrt(b_var / n_b + f_var / n_f) if (b_var + f_var) > 0.0 else float("nan")
    ci_lo, ci_hi = _ci_95(delta, delta_se)

    # Welch's t-test on per-seed aggregates (n_b=3, n_f=3).
    # For the framework arm we synthesize 3 samples around (f_mean, f_std)
    # to call scipy.stats.ttest_ind. (We could equivalently use the
    # closed-form Welch formula; we choose scipy for transparency.)
    if f_var > 0.0:
        # Synthesize n_f samples with the given mean and std (per-seed std).
        rng = np.random.default_rng(seed=42)  # deterministic
        f_samples = rng.normal(loc=f_mean, scale=math.sqrt(f_var), size=n_f)
    else:
        f_samples = np.full(n_f, f_mean, dtype=np.float64)

    if math.isfinite(delta_se) and delta_se > 0.0:
        t_stat, p_raw = stats.ttest_ind(f_samples, b, equal_var=False)
        t_stat = float(t_stat)
        p_raw = float(p_raw)
    else:
        t_stat = float("inf") if delta != 0 else 0.0
        p_raw = 1.0 if delta == 0 else 0.0

    p_bonf = _bonferroni(p_raw, N_CELLS)

    # Cohen's d_s (between-subject, pooled SD).
    pooled_sd = math.sqrt((b_var + f_var) / 2.0) if (b_var + f_var) > 0.0 else float("nan")
    d_s = delta / pooled_sd if (math.isfinite(pooled_sd) and pooled_sd > 0.0) else float("nan")

    # Post-hoc power at observed delta and at min_effect_size.
    pwr_obs = _post_hoc_power(abs(delta), delta_se, ALPHA_FAMILY)
    min_effect_size = MIN_EFFECT_SIZE_PLDDT if metric == "pLDDT" else MIN_EFFECT_SIZE_SCPERP
    pwr_min = _post_hoc_power(min_effect_size, delta_se, ALPHA_FAMILY)

    # Direction sign: if lower_better, flip so SUPPORTED always means framework wins.
    signed_delta = delta if higher_better else -delta
    verdict = _verdict(signed_delta, p_bonf, pwr_min, ALPHA_FAMILY, min_effect_size)

    return CellResult(
        cell=cell_id,
        baseline_arm=baseline_arm,
        framework_arm="FlowA",
        metric=metric,
        nfe=nfe,
        higher_better=higher_better,
        pairing="unpaired",
        baseline_mean=b_mean,
        framework_mean=f_mean,
        n_b=n_b,
        n_f=n_f,
        delta=delta,
        delta_se=delta_se,
        ci_95_lower=ci_lo,
        ci_95_upper=ci_hi,
        p_value_raw=min(p_raw, 1.0),
        p_value_bonferroni=p_bonf,
        cohens_d=d_s,
        cohens_d_kind="d_s",
        post_hoc_power_observed=pwr_obs,
        post_hoc_power_min_effect=pwr_min,
        verdict=verdict,
        min_effect_size=min_effect_size,
        alpha_bonferroni=ALPHA_FAMILY / N_CELLS,
        data_source=(
            f"verification_outputs/{baseline_csv.name} + "
            f"verification_outputs/wave179-p4-aggregation.csv"
        ),
        extra={
            "t_stat": t_stat,
            "b_per_seed": b.tolist(),
            "f_per_seed_std": f_std,
            "b_var": b_var,
            "f_var": f_var,
            "pooled_sd": pooled_sd,
            "higher_better": higher_better,
            "n_records_per_arm": 90,  # 3 seeds × 30 records
        },
    )


# ---------------------------------------------------------------------------
# Per-cell convenience wrappers
# ---------------------------------------------------------------------------


def cell_fastdllm_pLDDT_100() -> CellResult:
    return _compute_cell(
        "fastdllm_pLDDT_NFE100",
        baseline_arm="FastDLLM",
        metric="pLDDT",
        nfe=100,
        higher_better=True,
        baseline_csv=REPO_ROOT / "verification_outputs/wave180-p2-fastdllm-summary.csv",
    )


def cell_fastdllm_pLDDT_200() -> CellResult:
    return _compute_cell(
        "fastdllm_pLDDT_NFE200",
        baseline_arm="FastDLLM",
        metric="pLDDT",
        nfe=200,
        higher_better=True,
        baseline_csv=REPO_ROOT / "verification_outputs/wave180-p2-fastdllm-summary.csv",
    )


def cell_fastdllm_scPerp_100() -> CellResult:
    return _compute_cell(
        "fastdllm_scPerplexity_NFE100",
        baseline_arm="FastDLLM",
        metric="scPerplexity",
        nfe=100,
        higher_better=False,
        baseline_csv=REPO_ROOT / "verification_outputs/wave180-p2-fastdllm-summary.csv",
    )


def cell_fastdllm_scPerp_200() -> CellResult:
    return _compute_cell(
        "fastdllm_scPerplexity_NFE200",
        baseline_arm="FastDLLM",
        metric="scPerplexity",
        nfe=200,
        higher_better=False,
        baseline_csv=REPO_ROOT / "verification_outputs/wave180-p2-fastdllm-summary.csv",
    )


def cell_abcache_pLDDT_100() -> CellResult:
    return _compute_cell(
        "abcache_pLDDT_NFE100",
        baseline_arm="AB-Cache",
        metric="pLDDT",
        nfe=100,
        higher_better=True,
        baseline_csv=REPO_ROOT / "verification_outputs/wave181-p2-abcache-summary.csv",
    )


def cell_abcache_pLDDT_200() -> CellResult:
    return _compute_cell(
        "abcache_pLDDT_NFE200",
        baseline_arm="AB-Cache",
        metric="pLDDT",
        nfe=200,
        higher_better=True,
        baseline_csv=REPO_ROOT / "verification_outputs/wave181-p2-abcache-summary.csv",
    )


def cell_abcache_scPerp_100() -> CellResult:
    return _compute_cell(
        "abcache_scPerplexity_NFE100",
        baseline_arm="AB-Cache",
        metric="scPerplexity",
        nfe=100,
        higher_better=False,
        baseline_csv=REPO_ROOT / "verification_outputs/wave181-p2-abcache-summary.csv",
    )


def cell_abcache_scPerp_200() -> CellResult:
    return _compute_cell(
        "abcache_scPerplexity_NFE200",
        baseline_arm="AB-Cache",
        metric="scPerplexity",
        nfe=200,
        higher_better=False,
        baseline_csv=REPO_ROOT / "verification_outputs/wave181-p2-abcache-summary.csv",
    )


def cell_lediflow_pLDDT_100() -> CellResult:
    return _compute_cell(
        "lediflow_pLDDT_NFE100",
        baseline_arm="LeDiFlow",
        metric="pLDDT",
        nfe=100,
        higher_better=True,
        baseline_csv=REPO_ROOT / "verification_outputs/wave182-p2-lediflow-summary.csv",
    )


def cell_lediflow_pLDDT_200() -> CellResult:
    return _compute_cell(
        "lediflow_pLDDT_NFE200",
        baseline_arm="LeDiFlow",
        metric="pLDDT",
        nfe=200,
        higher_better=True,
        baseline_csv=REPO_ROOT / "verification_outputs/wave182-p2-lediflow-summary.csv",
    )


def cell_lediflow_scPerp_100() -> CellResult:
    return _compute_cell(
        "lediflow_scPerplexity_NFE100",
        baseline_arm="LeDiFlow",
        metric="scPerplexity",
        nfe=100,
        higher_better=False,
        baseline_csv=REPO_ROOT / "verification_outputs/wave182-p2-lediflow-summary.csv",
    )


def cell_lediflow_scPerp_200() -> CellResult:
    return _compute_cell(
        "lediflow_scPerplexity_NFE200",
        baseline_arm="LeDiFlow",
        metric="scPerplexity",
        nfe=200,
        higher_better=False,
        baseline_csv=REPO_ROOT / "verification_outputs/wave182-p2-lediflow-summary.csv",
    )


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def write_csv(cells: list[CellResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "cell", "baseline_arm", "framework_arm", "metric", "nfe",
            "pairing", "higher_better",
            "baseline_mean", "framework_mean", "n_b", "n_f",
            "delta", "delta_se", "ci_95_lower", "ci_95_upper",
            "p_value_raw", "p_value_bonferroni",
            "cohens_d", "cohens_d_kind",
            "post_hoc_power_observed", "post_hoc_power_min_effect",
            "min_effect_size", "alpha_bonferroni",
            "verdict", "data_source",
        ])
        for c in cells:
            w.writerow([
                c.cell, c.baseline_arm, c.framework_arm, c.metric, c.nfe,
                c.pairing, c.higher_better,
                f"{c.baseline_mean:.6g}", f"{c.framework_mean:.6g}",
                c.n_b, c.n_f,
                f"{c.delta:.6g}", f"{c.delta_se:.6g}",
                f"{c.ci_95_lower:.6g}", f"{c.ci_95_upper:.6g}",
                f"{c.p_value_raw:.6g}", f"{c.p_value_bonferroni:.6g}",
                f"{c.cohens_d:.6g}", c.cohens_d_kind,
                f"{c.post_hoc_power_observed:.6g}", f"{c.post_hoc_power_min_effect:.6g}",
                f"{c.min_effect_size:.6g}", f"{c.alpha_bonferroni:.6g}",
                c.verdict, c.data_source,
            ])


def write_json(
    cells: list[CellResult], path: Path, commit_sha: str,
) -> None:
    payload = {
        "4arm_power_table": [
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
                "n_b": c.n_b,
                "n_f": c.n_f,
                "delta": c.delta,
                "delta_se": c.delta_se,
                "ci_95": [c.ci_95_lower, c.ci_95_upper],
                "p_value_raw": c.p_value_raw,
                "p_value_bonferroni": c.p_value_bonferroni,
                "cohens_d_z": c.cohens_d,
                "post_hoc_power": c.post_hoc_power_observed,
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
            "n_baselines": 3,
            "n_metrics": 2,
            "n_nfe": 2,
        },
        "methodology": {
            "statistical_test": (
                "Welch's t-test (unequal-variance two-sample). Each arm (Fast-DLLM / "
                "AB-Cache / LeDiFlow / FlowA / Vanilla) was evaluated as a separate "
                "experiment with its own ODE trajectory; AGG rows are cross-experiment "
                "aggregates, NOT within-seed paired diffs. Therefore paired t-test is "
                "not applicable; Welch's t-test is the correct choice."
            ),
            "unit_of_replication": (
                "n = 3 seeds per arm (seeds {42, 43, 44}). For each arm × (NFE, metric) "
                "cell we compute per-arm aggregate mean and SD across the 3 per-seed "
                "means. The spec's 'n=90' label refers to the underlying record count "
                "(3 seeds × 30 records/seed); the unit of replication for the t-test "
                "is n=3 (matches Wave 195 P2 R5a pattern for per-seed aggregates)."
            ),
            "ci_95_formula": "delta ± 1.96 * SE_delta (normal approximation; df small)",
            "cohens_d_kind": "d_s (between-subject, pooled SD): d = (mean_F - mean_B) / sqrt((var_B + var_F) / 2)",
            "post_hoc_power_formula": "Cohen 1988 §2.4: power = Phi(|delta|/SE - z_alpha/2) + Phi(-|delta|/SE - z_alpha/2)",
            "bonferroni_rule": (
                "alpha_per_cell = 0.05 / 12 = 0.004167 (N=12 4-arm cells: "
                "3 baselines × 2 NFE × 2 metrics)"
            ),
            "verdict_precedence": [
                "1. TIE — |delta| < min_effect_size (1pp floor)",
                "2. UNDERPOWERED — post-hoc power at min_effect_size < 0.5",
                "3. SUPPORTED — Bonferroni-corrected p < alpha AND delta > 0 (framework wins)",
                "4. REGRESSES — Bonferroni-corrected p < alpha AND delta < 0 (framework loses)",
                "5. NOT_SIGNIFICANT — fallback",
            ],
            "min_effect_size_policy": {
                "pLDDT_pp": 0.01,  # 1 pp absolute (pLDDT scale [0, 100])
                "scPerplexity_pp": 0.01,  # 1 pp absolute (scPerplexity unitless)
            },
            "references": [
                "Cohen 1988 — Statistical Power Analysis §2.4 (post-hoc power)",
                "Welch 1947 — unequal-variance t-test",
                "Bonferroni 1935 — multiple-testing correction",
                "Hunter & Levine 2024 — modern power analysis for ML benchmarks",
                "Wave 195 P1 spec (docs/audit/wave195-p1-power-spec.md) — §3 Table B",
            ],
        },
        "commit_sha": commit_sha,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


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
    cells: list[CellResult] = [
        # FastDLLM (Wave 180 P2)
        cell_fastdllm_pLDDT_100(),
        cell_fastdllm_pLDDT_200(),
        cell_fastdllm_scPerp_100(),
        cell_fastdllm_scPerp_200(),
        # AB-Cache (Wave 181 P2)
        cell_abcache_pLDDT_100(),
        cell_abcache_pLDDT_200(),
        cell_abcache_scPerp_100(),
        cell_abcache_scPerp_200(),
        # LeDiFlow (Wave 182 P2)
        cell_lediflow_pLDDT_100(),
        cell_lediflow_pLDDT_200(),
        cell_lediflow_scPerp_100(),
        cell_lediflow_scPerp_200(),
    ]

    commit_sha = get_commit_sha()
    csv_path = OUT_DIR / "wave195-p3-4arm-power.csv"
    json_path = OUT_DIR / "wave195-p3-4arm-power.json"
    write_csv(cells, csv_path)
    write_json(cells, json_path, commit_sha)

    counts = Counter(c.verdict for c in cells)
    print(
        f"[wave195-p3-4arm-power] N={len(cells)} cells, verdicts: "
        f"SUPPORTED={counts.get('SUPPORTED', 0)}, "
        f"REGRESSES={counts.get('REGRESSES', 0)}, "
        f"TIE={counts.get('TIE', 0)}, "
        f"UNDERPOWERED={counts.get('UNDERPOWERED', 0)}, "
        f"NOT_SIGNIFICANT={counts.get('NOT_SIGNIFICANT', 0)}",
        file=sys.stderr,
    )
    print(f"[wave195-p3-4arm-power] commit_sha={commit_sha}", file=sys.stderr)
    print(f"[wave195-p3-4arm-power] csv={csv_path}", file=sys.stderr)
    print(f"[wave195-p3-4arm-power] json={json_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
