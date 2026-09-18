"""Wave 195 P2 — Per-cell power analysis for the 6 R-level headline claims (R1-R6).

For each cell (R1 lineageflow HMMER, R2 kanzi inv_proj, R3 flowmol3 fg_dev,
R5a Two Moons W2, R5b CIFAR-10 RF FID, R5c MNIST FM FID, R6 lineageflow
foldability + scPerplexity), this script computes:

  * baseline_mean, framework_mean, n_b, n_f
  * delta = framework - baseline
  * delta_se  (paired: sd(diff) / sqrt(n_pairs); unpaired: sqrt(var_b/n + var_f/n))
  * 95% CI on delta (delta ± 1.96 * SE)
  * p_value_raw  (two-sided)
  * p_value_bonferroni  (× N_tests = 7)
  * Cohen's d_z  (within-subject if paired; Cohen's d_s if unpaired)
  * Post-hoc power to detect observed delta AND 1pp (or 0.01 absolute)
  * Verdict: SUPPORTED / REGRESSES / TIE / UNDERPOWERED / NOT_SIGNIFICANT

Verdict precedence (matches tools/statistical_power_analysis.py + Wave 195 P1 spec):

  1. TIE         — |delta| < min_effect_size
  2. UNDERPOWERED — post-hoc power at min_effect_size < 0.5
  3. SUPPORTED   — Bonferroni-corrected p < alpha AND delta > 0
  4. REGRESSES   — Bonferroni-corrected p < alpha AND delta < 0
  5. NOT_SIGNIFICANT — fallback

Statistical references (Cohen 1988 §2.4; Welch 1947; Bonferroni 1935; Hunter
& Levine 2024) are all already documented in the Wave 195 P1 spec.

Constraint: **CPU-only**, **numpy + scipy.stats only**, no torch.
"""
from __future__ import annotations

import csv
import json
import math
import os
import statistics
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
OUT_DIR: Path = REPO_ROOT / "verification_outputs"

#: Total cells in Table A (R-level) for Bonferroni correction.
N_CELLS: int = 7

#: Family-wise alpha (Bonferroni applied: per-cell alpha = 0.05 / N_CELLS).
ALPHA_FAMILY: float = 0.05

#: z critical value for two-sided 95% CI (matches scipy.stats.norm.ppf(0.975)).
Z_CRIT_95: float = 1.959963984540054

#: Post-hoc power threshold below which the cell is flagged UNDERPOWERED.
UNDERPOWERED_POWER_THRESHOLD: float = 0.5

# ---------------------------------------------------------------------------
# Cell-result dataclass + verdict machinery
# ---------------------------------------------------------------------------


@dataclass
class CellResult:
    """One row of the per-cell power table."""

    cell: str
    pairing: str  # "paired" or "unpaired"
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
    cohens_d_kind: str  # "d_z" (within-subject) or "d_s" (between-subject)
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
# Per-cell compute functions
# ---------------------------------------------------------------------------


def _paired_result(
    cell: str,
    baseline: np.ndarray,
    framework: np.ndarray,
    *,
    min_effect_size: float,
    data_source: str,
    higher_better: bool = True,
) -> CellResult:
    """Paired (within-subject) cell — paired t-test on within-pair diffs."""
    diff = framework - baseline
    n_pairs = len(diff)
    delta = float(diff.mean())
    sd_diff = float(diff.std(ddof=1)) if n_pairs > 1 else float("nan")
    delta_se = sd_diff / math.sqrt(n_pairs) if sd_diff > 0.0 else float("nan")
    ci_lo, ci_hi = _ci_95(delta, delta_se)
    if math.isfinite(delta_se) and delta_se > 0.0:
        t_stat = delta / delta_se
        p_raw = float(2.0 * (1.0 - stats.t.cdf(abs(t_stat), df=n_pairs - 1)))
    else:
        p_raw = 1.0 if abs(delta) > 0.0 else 0.0  # diff exactly 0 → p=1.0
    p_bonf = _bonferroni(p_raw, N_CELLS)
    d_z = float(delta / sd_diff) if sd_diff > 0.0 else float("inf") * (1.0 if delta > 0 else -1.0)
    pwr_obs = _post_hoc_power(abs(delta), delta_se, ALPHA_FAMILY)
    pwr_min = _post_hoc_power(min_effect_size, delta_se, ALPHA_FAMILY)
    # Direction: if metric is "lower better" (e.g. FID, W2, fg_dev), framework winning
    # means delta < 0. We invert sign of verdict so SUPPORTED always means framework wins.
    signed_delta = delta if higher_better else -delta
    verdict = _verdict(signed_delta, p_bonf, pwr_min, ALPHA_FAMILY, min_effect_size)
    return CellResult(
        cell=cell,
        pairing="paired",
        baseline_mean=float(baseline.mean()),
        framework_mean=float(framework.mean()),
        n_b=n_pairs,
        n_f=n_pairs,
        delta=delta,
        delta_se=delta_se,
        ci_95_lower=ci_lo,
        ci_95_upper=ci_hi,
        p_value_raw=min(p_raw, 1.0),
        p_value_bonferroni=p_bonf,
        cohens_d=d_z,
        cohens_d_kind="d_z",
        post_hoc_power_observed=pwr_obs,
        post_hoc_power_min_effect=pwr_min,
        verdict=verdict,
        min_effect_size=min_effect_size,
        alpha_bonferroni=ALPHA_FAMILY / N_CELLS,
        data_source=data_source,
        extra={"t_stat": float(delta / delta_se) if delta_se > 0 else float("nan"),
               "sd_diff": sd_diff, "n_pairs": n_pairs, "higher_better": higher_better},
    )


def _unpaired_result(
    cell: str,
    baseline: np.ndarray,
    framework: np.ndarray,
    *,
    min_effect_size: float,
    data_source: str,
    higher_better: bool = True,
) -> CellResult:
    """Unpaired (Welch's two-sample) cell — Welch's t-test."""
    n_b = len(baseline)
    n_f = len(framework)
    b_mean = float(baseline.mean())
    f_mean = float(framework.mean())
    b_var = float(baseline.var(ddof=1)) if n_b > 1 else 0.0
    f_var = float(framework.var(ddof=1)) if n_f > 1 else 0.0
    delta = f_mean - b_mean
    delta_se = math.sqrt(b_var / n_b + f_var / n_f) if (b_var + f_var) > 0.0 else float("nan")
    ci_lo, ci_hi = _ci_95(delta, delta_se)
    if math.isfinite(delta_se) and delta_se > 0.0:
        t_stat, p_raw = stats.ttest_ind(framework, baseline, equal_var=False)
        p_raw = float(p_raw)
    else:
        # Degenerate (both var = 0).
        t_stat = float("inf") if delta != 0 else 0.0
        p_raw = 1.0 if delta == 0 else 0.0
    p_bonf = _bonferroni(p_raw, N_CELLS)
    # Cohen's d_s (between-subject, pooled SD).
    pooled_sd = math.sqrt((b_var + f_var) / 2.0) if (b_var + f_var) > 0.0 else float("nan")
    d_s = delta / pooled_sd if (pooled_sd and pooled_sd > 0.0) else float("nan")
    pwr_obs = _post_hoc_power(abs(delta), delta_se, ALPHA_FAMILY)
    pwr_min = _post_hoc_power(min_effect_size, delta_se, ALPHA_FAMILY)
    signed_delta = delta if higher_better else -delta
    verdict = _verdict(signed_delta, p_bonf, pwr_min, ALPHA_FAMILY, min_effect_size)
    return CellResult(
        cell=cell,
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
        data_source=data_source,
        extra={"t_stat": float(t_stat), "b_var": b_var, "f_var": f_var,
               "pooled_sd": pooled_sd, "higher_better": higher_better},
    )


# ---------------------------------------------------------------------------
# Per-cell data loaders
# ---------------------------------------------------------------------------


def cell_R1_lineageflow_hmmer() -> CellResult:
    """R1: lineageflow HMMER Pfam hits (baseline vs framework; unpaired Welch).

    The P1 spec defines min_effect_size = 1 hit (total count across N=1000 seqs).
    In per-sequence units, this is 1/N = 0.001 hits/seq. We use that as the
    floor so the delta (0.184 hits/seq) is well above the noise floor.
    """
    base = REPO_ROOT / "verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/baseline_hits.tbl"
    fw = REPO_ROOT / "verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/framework_hits.tbl"
    n_seqs = 1000

    def per_seq_counts(path: Path) -> np.ndarray:
        """Return per-sequence hit counts (length n_seqs)."""
        counts: Counter[str] = Counter()
        with path.open() as fh:
            for line in fh:
                if line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) < 4:
                    continue
                counts[parts[2]] += 1
        arr = np.zeros(n_seqs, dtype=np.int64)
        vals = list(counts.values())
        for i, v in enumerate(vals[:n_seqs]):
            arr[i] = v
        return arr.astype(np.float64)

    b = per_seq_counts(base)
    f = per_seq_counts(fw)
    assert int(b.sum()) == 158, f"baseline hits mismatch: {int(b.sum())} != 158"
    assert int(f.sum()) == 342, f"framework hits mismatch: {int(f.sum())} != 342"
    # min_effect_size in per-seq units = 1 hit / N_seqs = 0.001.
    return _unpaired_result(
        "R1_lineageflow_hmmer",
        b, f,
        min_effect_size=1.0 / n_seqs,  # 1 hit total / 1000 seqs
        data_source="verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/{baseline,framework}_hits.tbl",
        higher_better=True,
    )


def cell_R2_kanzi_inv_proj() -> CellResult:
    """R2: kanzi framework_inv_proj (composite byte-stable σ=0)."""
    base = REPO_ROOT / "verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json"
    fw = REPO_ROOT / "verification_outputs/kanzi_n1000_framework_paper_metrics_inv_proj/kanzi_n1000_framework_paper_metrics.json"

    b_data = json.loads(base.read_text())
    f_data = json.loads(fw.read_text())
    b_rmsd = b_data["reconstruction_kabsch_rmsd_A"]
    f_rmsd = f_data["reconstruction_kabsch_rmsd_A"]
    n_b = int(b_rmsd["n_seqs"])
    n_f = int(f_rmsd["n_seqs"])
    b_mean = float(b_rmsd["mean_rmsd_A"])
    b_std = float(b_rmsd["std_rmsd_A"])
    f_mean = float(f_rmsd["mean_rmsd_A"])
    f_std = float(f_rmsd["std_rmsd_A"])

    # Framework is byte-stable σ=0 across 1000 records. The "paired" view is exact
    # because each record was reproduced identically; the mean diff = f - b is
    # exact and SE comes from baseline sd (which is the dominant noise source).
    # We treat as paired with sd_diff = b_std (framework contributes zero noise).
    delta = f_mean - b_mean
    # Lower better (Å RMSD). We flip signed_delta inside _paired_result via
    # higher_better=False.
    delta_se = b_std / math.sqrt(n_b) if b_std > 0.0 else float("nan")
    ci_lo, ci_hi = _ci_95(delta, delta_se)
    if math.isfinite(delta_se) and delta_se > 0.0:
        z = delta / delta_se
        # For paired with σ_diff ≈ b_std and large df, use normal approximation.
        p_raw = float(2.0 * (1.0 - stats.norm.cdf(abs(z))))
    else:
        p_raw = 0.0
    p_bonf = _bonferroni(p_raw, N_CELLS)
    d_z = delta / b_std if b_std > 0.0 else float("nan")
    pwr_obs = _post_hoc_power(abs(delta), delta_se, ALPHA_FAMILY)
    pwr_min = _post_hoc_power(0.01, delta_se, ALPHA_FAMILY)
    signed_delta = -delta  # lower better
    verdict = _verdict(signed_delta, p_bonf, pwr_min, ALPHA_FAMILY, 0.01)
    return CellResult(
        cell="R2_kanzi_inv_proj",
        pairing="paired",
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
        cohens_d=d_z,
        cohens_d_kind="d_z",
        post_hoc_power_observed=pwr_obs,
        post_hoc_power_min_effect=pwr_min,
        verdict=verdict,
        min_effect_size=0.01,
        alpha_bonferroni=ALPHA_FAMILY / N_CELLS,
        data_source=(
            "verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json + "
            "verification_outputs/kanzi_n1000_framework_paper_metrics_inv_proj/"
            "kanzi_n1000_framework_paper_metrics.json"
        ),
        extra={
            "b_std": b_std, "f_std": f_std, "lower_better": True,
            "note": "framework byte-stable σ=0; baseline σ=0.137 Å; Δ is exact across 1000 records",
        },
    )


def cell_R3_flowmol3_fg_dev() -> CellResult:
    """R3: FlowMol3 fg_dev (lower better; aggregate from sweep)."""
    sweep = json.loads(
        (REPO_ROOT / "verification_outputs/flowmol3_n1000_sweep_q4_2026.json").read_text()
    )
    b_mean = float(sweep["baseline"]["metrics"]["fg_dev"])
    f_mean = float(sweep["framework"]["metrics"]["fg_dev"])
    n_b = int(sweep["baseline"]["n_sampled"])
    n_f = int(sweep["framework"]["n_sampled"])
    # Use the pre-computed SEM from statistical_power_at_n1000 (per-arm SEM at N=1000).
    sem = float(sweep["statistical_power_at_n1000"]["fg_dev_sem"])
    delta_se = math.sqrt(2.0) * sem  # unpaired SE for delta with equal SEM per arm
    delta = f_mean - b_mean
    ci_lo, ci_hi = _ci_95(delta, delta_se)
    # For unpaired test: t = delta / SE, df approximated by Welch-Satterthwaite.
    # Without per-sequence variance, use normal approximation (large N).
    z = delta / delta_se
    p_raw = float(2.0 * (1.0 - stats.norm.cdf(abs(z))))
    p_bonf = _bonferroni(p_raw, N_CELLS)
    # Cohen's d_s: per-arm SD = SEM * sqrt(N); pooled SD = avg of two.
    b_sd = sem * math.sqrt(n_b)
    f_sd = sem * math.sqrt(n_f)
    pooled_sd = math.sqrt((b_sd ** 2 + f_sd ** 2) / 2.0)
    d_s = delta / pooled_sd if pooled_sd > 0.0 else float("nan")
    pwr_obs = _post_hoc_power(abs(delta), delta_se, ALPHA_FAMILY)
    pwr_min = _post_hoc_power(0.01, delta_se, ALPHA_FAMILY)
    signed_delta = -delta  # lower better
    verdict = _verdict(signed_delta, p_bonf, pwr_min, ALPHA_FAMILY, 0.01)
    return CellResult(
        cell="R3_flowmol3_fg_dev",
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
        min_effect_size=0.01,
        alpha_bonferroni=ALPHA_FAMILY / N_CELLS,
        data_source="verification_outputs/flowmol3_n1000_sweep_q4_2026.json",
        extra={
            "sem": sem, "b_sd": b_sd, "f_sd": f_sd, "lower_better": True,
            "note": "Per-arm SEM from sweep statistical_power_at_n1000.fg_dev_sem; unpaired since arms are independent sweeps",
        },
    )


def cell_R5a_two_moons_W2() -> CellResult:
    """R5a: 2D Two Moons W2 (per-seed aggregates; unpaired Welch on n=3 seeds)."""
    combined = json.loads(
        (REPO_ROOT / "verification_outputs/wave189-p2-post-cd70821-combined.json").read_text()
    )
    tm = combined["two_moons"]
    b = np.array(tm["baseline_per_seed_w2"], dtype=np.float64)
    f = np.array(tm["framework_per_seed_w2_tail5"], dtype=np.float64)
    return _unpaired_result(
        "R5a_2D_two_moons_W2",
        b, f,
        min_effect_size=0.01,
        data_source="verification_outputs/wave189-p2-post-cd70821-combined.json#two_moons",
        higher_better=False,
    )


def cell_R5b_cifar10rf_fid() -> CellResult:
    """R5b: CIFAR-10 RF matched-NFE=50 FID (chunk-level paired, df=9; baseline_wins).

    Source: wave191-p2-cifar10-n1000.json (chunk-level paired t-test). The headline
    FID shows framework REGRESSES at matched NFE=50: baseline 415.83 vs best framework
    arm evidence_driven 499.83 (delta=+20.21%, framework-WORSE on FID). This is the
    documented honest-negative cell per Wave 191 P2 r5_implication.
    """
    w = json.loads((REPO_ROOT / "verification_outputs/wave191-p2-cifar10-n1000.json").read_text())
    arm = w["framework_arms"]["evidence_driven"]
    n_chunks = int(arm["n_chunks"])
    fw_std = float(arm["fid_chunks_std"])
    fw_mean = float(arm["fid_chunks_mean"])
    fw_headline = float(arm["fid_headline"])
    b_fid = float(w["baseline_fid"])
    # Use the pre-computed p_value, cohens_dz, t_stat directly from the source JSON.
    p_raw = float(arm["p_value_raw"])
    d_z = float(arm["cohens_dz"])
    t_stat = float(arm["t_stat"])
    df = int(arm["df"])
    # Reconstruct delta from the source-reported values: chunks_mean - baseline.
    delta = fw_mean - b_fid  # +90.045 (framework WORSE on FID; REGRESSES)
    # SE_delta from paired test: SE = delta / t_stat
    se = abs(delta / t_stat) if t_stat != 0.0 else float("nan")
    ci_lo, ci_hi = _ci_95(delta, se)
    p_bonf = _bonferroni(p_raw, N_CELLS)
    pwr_obs = _post_hoc_power(abs(delta), se, ALPHA_FAMILY)
    pwr_min = _post_hoc_power(1.0, se, ALPHA_FAMILY)  # 1 FID unit floor
    signed_delta = -delta  # FID lower better
    verdict = _verdict(signed_delta, p_bonf, pwr_min, ALPHA_FAMILY, 1.0)
    return CellResult(
        cell="R5b_cifar10rf_matched_NFE50_FID",
        pairing="paired",
        baseline_mean=b_fid,
        framework_mean=fw_headline,  # headline (full N=1000) for paper claim
        n_b=int(w["n_records"]),
        n_f=int(w["n_records"]),
        delta=delta,
        delta_se=se,
        ci_95_lower=ci_lo,
        ci_95_upper=ci_hi,
        p_value_raw=min(p_raw, 1.0),
        p_value_bonferroni=p_bonf,
        cohens_d=d_z,
        cohens_d_kind="d_z",
        post_hoc_power_observed=pwr_obs,
        post_hoc_power_min_effect=pwr_min,
        verdict=verdict,
        min_effect_size=1.0,  # 1 FID unit (paper convention)
        alpha_bonferroni=ALPHA_FAMILY / N_CELLS,
        data_source="verification_outputs/wave191-p2-cifar10-n1000.json (chunk-level paired t-test, df=9)",
        extra={
            "t_stat": t_stat, "df": df, "n_chunks": n_chunks,
            "fw_chunks_mean": fw_mean, "fw_chunks_std": fw_std,
            "fw_headline_fid": fw_headline, "b_fid": b_fid,
            "lower_better": True,
            "note": "Framework REGRESSES at matched NFE=50 (FID higher by 20.21%). Pre-computed p_value_raw/cohens_dz/t_stat from Wave 191 P2 chunk-level paired t-test (df=9).",
        },
    )


def cell_R5c_mnist_fm_fid() -> CellResult:
    """R5c: MNIST FM matched-NFE=50 FID (chunk-level paired, df=9; framework_wins).

    Source: wave191-p3-mnist-n1000.json (chunk-level paired t-test). The headline
    FID shows framework WINS at matched NFE=50: baseline 29.49 vs best framework
    arm evidence_driven 23.39 (delta=-28.43%, framework-BETTER on FID).
    """
    w = json.loads((REPO_ROOT / "verification_outputs/wave191-p3-mnist-n1000.json").read_text())
    arm = w["framework_arms"]["evidence_driven"]
    n_chunks = int(arm["n_chunks"])
    fw_std = float(arm["fid_chunks_std"])
    fw_mean = float(arm["fid_chunks_mean"])
    fw_headline = float(arm["fid_headline"])
    b_fid = float(w["baseline_fid"])
    p_raw = float(arm["p_value_raw"])
    d_z = float(arm["cohens_dz"])
    t_stat = float(arm["t_stat"])
    df = int(arm["df"])
    # Use the headline-level delta (the paper claim is on the headline FID).
    delta = fw_headline - b_fid  # -6.10
    se = abs(delta / t_stat) if t_stat != 0.0 else float("nan")
    ci_lo, ci_hi = _ci_95(delta, se)
    p_bonf = _bonferroni(p_raw, N_CELLS)
    pwr_obs = _post_hoc_power(abs(delta), se, ALPHA_FAMILY)
    pwr_min = _post_hoc_power(0.1, se, ALPHA_FAMILY)  # 0.1 FID units floor
    signed_delta = -delta  # FID lower better
    verdict = _verdict(signed_delta, p_bonf, pwr_min, ALPHA_FAMILY, 0.1)
    return CellResult(
        cell="R5c_mnist_fm_matched_NFE50_FID",
        pairing="paired",
        baseline_mean=b_fid,
        framework_mean=fw_headline,  # headline (full N=1000) for paper claim
        n_b=int(w["n_records"]),
        n_f=int(w["n_records"]),
        delta=delta,
        delta_se=se,
        ci_95_lower=ci_lo,
        ci_95_upper=ci_hi,
        p_value_raw=min(p_raw, 1.0),
        p_value_bonferroni=p_bonf,
        cohens_d=d_z,
        cohens_d_kind="d_z",
        post_hoc_power_observed=pwr_obs,
        post_hoc_power_min_effect=pwr_min,
        verdict=verdict,
        min_effect_size=0.1,  # 0.1 FID units (small but consistent scale)
        alpha_bonferroni=ALPHA_FAMILY / N_CELLS,
        data_source="verification_outputs/wave191-p3-mnist-n1000.json (chunk-level paired t-test, df=9)",
        extra={
            "t_stat": t_stat, "df": df, "n_chunks": n_chunks,
            "fw_chunks_mean": fw_mean, "fw_chunks_std": fw_std,
            "fw_headline_fid": fw_headline, "b_fid": b_fid,
            "lower_better": True,
            "note": "Framework WINS at matched NFE=50 (FID lower by 28.43%). Pre-computed p_value_raw/cohens_dz/t_stat from Wave 191 P3 chunk-level paired t-test (df=9). Smoke ckpt per honest_disclosure.",
        },
    )


def cell_R6_lineageflow_foldability() -> CellResult:
    """R6: LineageFlow foldability (paired on qid, n=1000)."""
    base_dir = REPO_ROOT / "verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability"
    fw_dir = REPO_ROOT / "verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability"

    def load_plddt(d: Path) -> np.ndarray:
        out = []
        with d.joinpath("foldability.jsonl").open() as fh:
            for line in fh:
                rec = json.loads(line)
                out.append(float(rec["plddt_mean"]))
        return np.array(out, dtype=np.float64)

    def load_sc(d: Path) -> np.ndarray:
        out = []
        with d.joinpath("self_consistency.jsonl").open() as fh:
            for line in fh:
                rec = json.loads(line)
                out.append(float(rec["sc_perplexity"]))
        return np.array(out, dtype=np.float64)

    b_p = load_plddt(base_dir)
    f_p = load_plddt(fw_dir)
    b_s = load_sc(base_dir)
    f_s = load_sc(fw_dir)

    # pLDDT (higher better)
    plddt = _paired_result(
        "R6_lineageflow_foldability_pLDDT",
        b_p, f_p,
        min_effect_size=0.5,  # 0.5 pLDDT pp (N=1000 paired SEM is ~0.5)
        data_source="verification_outputs/k6_foldability_n1000_w161_q3_2026/{baseline,framework}/foldability/foldability.jsonl",
        higher_better=True,
    )
    # scPerplexity (lower better)
    sc = _paired_result(
        "R6_lineageflow_scPerplexity",
        b_s, f_s,
        min_effect_size=0.1,  # 0.1 scPerplexity units (paired SEM is ~0.115)
        data_source="verification_outputs/k6_foldability_n1000_w161_q3_2026/{baseline,framework}/foldability/self_consistency.jsonl",
        higher_better=False,
    )
    return [plddt, sc]


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def write_csv(cells: list[CellResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "cell", "pairing", "baseline_mean", "framework_mean", "n_b", "n_f",
            "delta", "delta_se", "ci_95_lower", "ci_95_upper",
            "p_value_raw", "p_value_bonferroni",
            "cohens_d", "cohens_d_kind",
            "post_hoc_power_observed", "post_hoc_power_min_effect",
            "min_effect_size", "alpha_bonferroni",
            "verdict", "data_source",
        ])
        for c in cells:
            w.writerow([
                c.cell, c.pairing,
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
        "r_level_power_table": [
            {
                "cell": c.cell,
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
                "cohens_d": c.cohens_d,
                "cohens_d_kind": c.cohens_d_kind,
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
            "n_supported": sum(1 for c in cells if c.verdict == "SUPPORTED"),
            "n_regresses": sum(1 for c in cells if c.verdict == "REGRESSES"),
            "n_underpowered": sum(1 for c in cells if c.verdict == "UNDERPOWERED"),
            "n_tie": sum(1 for c in cells if c.verdict == "TIE"),
            "n_not_significant": sum(1 for c in cells if c.verdict == "NOT_SIGNIFICANT"),
            "alpha_family": ALPHA_FAMILY,
            "alpha_bonferroni": ALPHA_FAMILY / N_CELLS,
            "n_tests_for_bonferroni": N_CELLS,
        },
        "methodology": {
            "statistical_test": (
                "Paired t-test on within-pair diffs (paired cells); "
                "Welch's t-test (unequal-variance) for unpaired cells. "
                "Cohen's d_z = mean(diff)/sd(diff) for paired; "
                "Cohen's d_s = (mean_F - mean_B) / sqrt((var_B + var_F)/2) for unpaired."
            ),
            "ci_95_formula": "delta ± 1.96 * SE_delta (normal approximation; df large)",
            "post_hoc_power_formula": "Cohen 1988 §2.4: power = Phi(|delta|/SE - z_alpha/2) + Phi(-|delta|/SE - z_alpha/2)",
            "bonferroni_rule": "alpha_per_cell = 0.05 / 7 = 0.007143 (N=7 R-level cells: R1, R2, R3, R5a, R5b, R5c, R6)",
            "verdict_precedence": [
                "1. TIE — |delta| < min_effect_size",
                "2. UNDERPOWERED — post-hoc power at min_effect_size < 0.5",
                "3. SUPPORTED — Bonferroni-corrected p < alpha AND delta > 0 (framework wins)",
                "4. REGRESSES — Bonferroni-corrected p < alpha AND delta < 0 (framework loses)",
                "5. NOT_SIGNIFICANT — fallback",
            ],
            "min_effect_size_policy": {
                "r1_hmmer_hits_int_count": 1,
                "r2_kanzi_rmsd_A_pp": 0.01,
                "r3_flowmol3_fg_dev_pp": 0.01,
                "r5a_2d_two_moons_W2_pp": 0.01,
                "r5b_cifar10_rf_FID_unit": 1.0,
                "r5c_mnist_fm_FID_unit": 0.1,
                "r6_lineageflow_pLDDT_pp": 0.5,
                "r6_lineageflow_scPerplexity_pp": 0.1,
            },
            "references": [
                "Cohen 1988 — Statistical Power Analysis §2.4 (post-hoc power)",
                "Welch 1947 — unequal-variance t-test",
                "Bonferroni 1935 — multiple-testing correction",
                "Hunter & Levine 2024 — modern power analysis for ML benchmarks",
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
    import subprocess

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
    cells.append(cell_R1_lineageflow_hmmer())
    cells.append(cell_R2_kanzi_inv_proj())
    cells.append(cell_R3_flowmol3_fg_dev())
    cells.append(cell_R5a_two_moons_W2())
    cells.append(cell_R5b_cifar10rf_fid())
    cells.append(cell_R5c_mnist_fm_fid())
    cells.extend(cell_R6_lineageflow_foldability())

    commit_sha = get_commit_sha()
    csv_path = OUT_DIR / "wave195-p2-r-level-power.csv"
    json_path = OUT_DIR / "wave195-p2-r-level-power.json"
    write_csv(cells, csv_path)
    write_json(cells, json_path, commit_sha)

    # Summary line for stderr.
    counts = Counter(c.verdict for c in cells)
    print(
        f"[wave195-p2-r-level-power] N={len(cells)} cells, verdicts: "
        f"SUPPORTED={counts.get('SUPPORTED', 0)}, "
        f"REGRESSES={counts.get('REGRESSES', 0)}, "
        f"TIE={counts.get('TIE', 0)}, "
        f"UNDERPOWERED={counts.get('UNDERPOWERED', 0)}, "
        f"NOT_SIGNIFICANT={counts.get('NOT_SIGNIFICANT', 0)}",
        file=__import__("sys").stderr,
    )
    print(f"[wave195-p2-r-level-power] commit_sha={commit_sha}", file=__import__("sys").stderr)
    print(f"[wave195-p2-r-level-power] csv={csv_path}", file=__import__("sys").stderr)
    print(f"[wave195-p2-r-level-power] json={json_path}", file=__import__("sys").stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
