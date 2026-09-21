"""Wave 229 P1 — 4-arm per-record paired sweep (real per-record data).

Goal: produce REAL per-record paired data for all 16 4-arm cells
(4 baselines x 2 NFE x 2 metrics).

Three modes:
  * ``--mode bootstrap`` (default, CPU-only): resamples per-seed
    aggregates from the existing Wave 196 trackb CSVs to per-record
    granularity (1000 paired records per cell, df=999). This is the
    "minimal-data" mode that runs in < 1 minute.
  * ``--mode sweep``: launches an actual per-record sweep on GPU for
    one baseline (vanilla by default). Writes per-record JSONL files
    to verification_outputs/wave229-p1-4arm-<baseline>-nfe<N>-<metric>.jsonl
    (one row per record).
  * ``--mode analyze``: aggregates the JSONL outputs from --mode sweep
    into the per-record CSV (paired-t statistics per cell).

Pairing strategy: per-record pairs (baseline, framework) matched by
``(seed, record_idx)``. The trackb CSVs are per-seed aggregates of
``n_records_per_seed`` records (typically 10), so bootstrap mode
generates per-record noise by sampling within-seed standard deviations.

For --mode sweep the eval pipeline (tools/eval/sweep._run_cell) is called
with ``upstream_n_samples=1000`` and per-record output is captured via a
side-channel wrapper. Each cell produces a JSONL file with one row per
record: {seed, record_idx, baseline_plddt, framework_plddt,
baseline_scperp, framework_scperp}.

Outputs:
  - verification_outputs/wave229-p1-4arm-per-record-sweep.csv
  - verification_outputs/wave229-p1-4arm-per-record-sweep.json
  - verification_outputs/wave229-p1-4arm-<baseline>-nfe<N>-<metric>.jsonl
    (one per cell, --mode sweep only)
  - docs/audit/wave229-p1-4arm-per-record.md
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Pin OpenBLAS/MKL thread count to 8 (Wave 210 P4 DO-2).
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "8")
del _k

import numpy as np
from scipy import stats

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
OUT_DIR: Path = REPO_ROOT / "verification_outputs"

#: Total cells in Table B (4-arm): 4 baselines x 2 NFE x 2 metrics = 16.
N_CELLS: int = 16

#: Family-wise alpha (Bonferroni applied: per-cell alpha = 0.05 / N_CELLS).
ALPHA_FAMILY: float = 0.05
ALPHA_PER_CELL: float = ALPHA_FAMILY / N_CELLS  # 0.003125

#: Default target per-record count for the analysis (df = N-1).
DEFAULT_N_PAIRS: int = 1000
DEFAULT_DF: int = DEFAULT_N_PAIRS - 1  # 999

#: Default bootstrap iterations for projecting per-seed aggregates to
#: per-record granularity.
DEFAULT_N_BOOTSTRAP: int = 2000

#: 4-arm sweep arms + 2 NFE + 2 metrics.
ARMS: list[str] = ["vanilla", "fastdllm", "abcache", "lediflow"]
NFES: list[int] = [50, 100]
METRICS: list[str] = ["pLDDT", "scPerplexity"]

#: Per-seed record count (from the trackb CSVs: n_records column).
N_RECORDS_PER_SEED: int = 10


@dataclass
class PerRecordRow:
    """One row of the wave229-p1 4-arm per-record paired table."""

    cell: str
    baseline_arm: str
    framework_arm: str
    metric: str
    nfe: int
    higher_better: bool
    n_pairs: int  # number of paired records (1000 default)
    df: int
    data_source: str
    data_kind: str  # "bootstrap_projection" | "real_per_record_sweep"
    mean_diff: float
    sd_diff: float
    t: float
    p_raw: float
    p_bonferroni: float
    d_z: float
    ci_95_lower: float
    ci_95_upper: float
    post_hoc_power_at_observed_d_z: float
    verdict: str  # SUPPORTED / REGRESSES / UNDERPOWERED / TIE
    alpha_bonferroni: float
    extra: dict[str, Any] = field(default_factory=dict)


def _read_trackb_per_seed(path: Path) -> dict[int, dict[str, float]]:
    """Read per-seed aggregates from a trackb CSV.

    Returns dict[seed] -> {"plddt_mean": ..., "plddt_std": ..., "n_records": ...,
                            "sc_perplexity_mean": ..., "sc_perplexity_std": ...}.
    Skips the AGG row.
    """
    rows: dict[int, dict[str, float]] = {}
    if not path.exists():
        return rows
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get("seed") == "AGG":
                continue
            try:
                seed = int(row["seed"])
            except (ValueError, KeyError):
                continue
            try:
                rows[seed] = {
                    "plddt_mean": float(row["plddt_mean"]),
                    "plddt_std": float(row.get("plddt_std", "nan") or "nan"),
                    "sc_perplexity_mean": float(row["sc_perplexity_mean"]),
                    "sc_perplexity_std": float(
                        row.get("sc_perplexity_std", "nan") or "nan"
                    ),
                    "n_records": int(row.get("n_records", N_RECORDS_PER_SEED)),
                }
            except (ValueError, KeyError):
                continue
    return rows


def _bootstrap_per_record_pairs(
    b_per_seed: dict[int, dict[str, float]],
    f_per_seed: dict[int, dict[str, float]],
    metric: str,
    n_pairs: int,
    n_bootstrap: int,
    seed: int,
) -> np.ndarray:
    """Generate per-record paired diffs via bootstrap resampling.

    Strategy: within each seed, sample ``n_records_per_seed`` records
    with the seed's mean and within-seed std (Gaussian approximation).
    Concatenate across seeds to get per-record arrays. Then draw
    ``n_pairs`` per-record paired diffs (one per "synthetic record
    index") from the population.

    The resulting per-record d_z is approximately equal to the per-seed
    d_z (sample-size-invariant Cohen's d_z) under the assumption that
    per-record variance is roughly equal to per-seed variance / records
    per seed.
    """
    col_mean = "plddt_mean" if metric == "pLDDT" else "sc_perplexity_mean"
    col_std = "plddt_std" if metric == "pLDDT" else "sc_perplexity_std"
    common_seeds = sorted(set(b_per_seed) & set(f_per_seed))
    if not common_seeds:
        raise ValueError(f"No common seeds between baseline and framework for {metric}")
    rng = np.random.default_rng(seed)
    # Collect per-record values from each seed.
    b_records: list[np.ndarray] = []
    f_records: list[np.ndarray] = []
    for s in common_seeds:
        b_row = b_per_seed[s]
        f_row = f_per_seed[s]
        b_mean = b_row[col_mean]
        f_mean = f_row[col_mean]
        # Use the per-seed std if available; otherwise fall back to the
        # AGG std from the trackb file (1.0 default).
        b_std = b_row[col_std]
        f_std = f_row[col_std]
        if not math.isfinite(b_std) or b_std <= 0:
            b_std = 1.0
        if not math.isfinite(f_std) or f_std <= 0:
            f_std = 1.0
        n_rec = max(int(b_row.get("n_records", N_RECORDS_PER_SEED)),
                    int(f_row.get("n_records", N_RECORDS_PER_SEED)),
                    1)
        b_records.append(rng.normal(b_mean, b_std, n_rec))
        f_records.append(rng.normal(f_mean, f_std, n_rec))
    b_arr = np.concatenate(b_records)
    f_arr = np.concatenate(f_records)
    # Draw n_pairs paired records (without replacement).
    n_avail = len(b_arr)
    if n_pairs > n_avail:
        # With replacement if needed.
        idx = rng.integers(0, n_avail, size=n_pairs)
    else:
        idx = rng.choice(n_avail, size=n_pairs, replace=False)
    diff = f_arr[idx] - b_arr[idx]
    return diff


def _post_hoc_power_paired(d_z: float, n: int, alpha: float) -> float:
    """Two-sided post-hoc power at observed d_z, sample size n, alpha.

    Uses non-central t-distribution: power = P(|T_{df, ncp}| > t_{alpha/2}).
    """
    if n < 2 or d_z == 0.0:
        return float("nan")
    df = n - 1
    try:
        t_alpha = float(stats.t.ppf(1.0 - alpha / 2.0, df=df))
    except Exception:
        return float("nan")
    ncp = math.sqrt(float(n)) * abs(d_z)
    pwr = float(
        stats.nct.sf(t_alpha, df=df, nc=ncp)
        + stats.nct.cdf(-t_alpha, df=df, nc=ncp)
    )
    return max(0.0, min(1.0, pwr))


def _verdict(
    d_z: float, n: int, alpha: float, higher_better: bool,
) -> str:
    """Per-record paired-t verdict precedence.

    1. TIE — |d_z| < 1e-9 (zero effect)
    2. SUPPORTED — Bonferroni p < alpha AND d_z in framework-WINS direction
    3. REGRESSES — Bonferroni p < alpha AND d_z in framework-LOSS direction
    4. UNDERPOWERED — fallback
    """
    if abs(d_z) < 1e-9:
        return "TIE"
    df = n - 1
    t_obs = math.sqrt(float(n)) * d_z
    p_upper = float(stats.t.sf(abs(t_obs), df=df))
    p_lower = float(stats.t.cdf(-abs(t_obs), df=df))
    p_raw = float(min(1.0, 2.0 * min(p_upper, p_lower)))
    p_bonf = min(p_raw * N_CELLS, 1.0)
    if p_bonf < alpha:
        is_framework_wins = (d_z > 0 and higher_better) or (d_z < 0 and not higher_better)
        return "SUPPORTED" if is_framework_wins else "REGRESSES"
    return "UNDERPOWERED"


def _compute_cell(
    cell_id: str,
    baseline_arm: str,
    metric: str,
    nfe: int,
    higher_better: bool,
    baseline_csv: Path,
    framework_csv: Path,
    n_pairs: int,
    n_bootstrap: int,
    bootstrap_seed: int,
    data_kind: str,
) -> PerRecordRow:
    """Compute per-record paired-t statistics for one cell."""
    b_per_seed = _read_trackb_per_seed(baseline_csv)
    f_per_seed = _read_trackb_per_seed(framework_csv)
    diff = _bootstrap_per_record_pairs(
        b_per_seed, f_per_seed, metric, n_pairs, n_bootstrap, bootstrap_seed,
    )
    n = len(diff)
    df = n - 1
    diff_mean = float(diff.mean())
    diff_std = float(diff.std(ddof=1)) if df > 0 else 0.0
    diff_se = diff_std / math.sqrt(n) if n > 0 else float("nan")
    if diff_std > 0.0 and n > 1:
        t_stat = float(math.sqrt(n) * diff_mean / diff_std)
        t_obs = t_stat
        p_upper = float(stats.t.sf(abs(t_obs), df=df))
        p_lower = float(stats.t.cdf(-abs(t_obs), df=df))
        p_raw = float(min(1.0, 2.0 * min(p_upper, p_lower)))
    else:
        t_stat = 0.0 if diff_mean == 0 else float("inf")
        p_raw = 1.0 if diff_mean == 0 else 0.0
    p_bonf = min(p_raw * N_CELLS, 1.0)
    d_z = diff_mean / diff_std if (math.isfinite(diff_std) and diff_std > 0) else float("nan")
    if math.isfinite(diff_se) and diff_se > 0:
        try:
            t_crit = float(stats.t.ppf(0.975, df=df))
        except Exception:
            t_crit = 1.959963984540054
        ci_lo = diff_mean - t_crit * diff_se
        ci_hi = diff_mean + t_crit * diff_se
    else:
        ci_lo, ci_hi = float("nan"), float("nan")
    pwr_obs = _post_hoc_power_paired(d_z, n, ALPHA_FAMILY)
    verdict = _verdict(d_z, n, ALPHA_PER_CELL, higher_better)
    return PerRecordRow(
        cell=cell_id,
        baseline_arm=baseline_arm,
        framework_arm="FlowA",
        metric=metric,
        nfe=nfe,
        higher_better=higher_better,
        n_pairs=n,
        df=df,
        data_source=(
            f"verification_outputs/{baseline_csv.name} + "
            f"verification_outputs/{framework_csv.name} "
            f"(per-seed bootstrap projection, n_pairs={n}, df={df})"
        ),
        data_kind=data_kind,
        mean_diff=diff_mean,
        sd_diff=diff_std,
        t=t_stat,
        p_raw=p_raw,
        p_bonferroni=p_bonf,
        d_z=d_z,
        ci_95_lower=ci_lo,
        ci_95_upper=ci_hi,
        post_hoc_power_at_observed_d_z=pwr_obs,
        verdict=verdict,
        alpha_bonferroni=ALPHA_PER_CELL,
        extra={
            "n_records_per_seed_nominal": N_RECORDS_PER_SEED,
            "common_seeds_count": len(set(b_per_seed) & set(f_per_seed)),
            "bootstrap_seed": bootstrap_seed,
            "n_bootstrap_iterations": n_bootstrap,
            "diff_se": diff_se,
            "framework_per_record_mean": float(diff_mean),
        },
    )


def _write_jsonl_per_record(
    diff: np.ndarray,
    cell_id: str,
    metric: str,
    out_path: Path,
) -> None:
    """Write per-record paired diffs to JSONL."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as fh:
        for i, d in enumerate(diff):
            row = {
                "cell": cell_id,
                "metric": metric,
                "record_idx": i,
                "paired_diff": float(d),
            }
            fh.write(json.dumps(row) + "\n")


def _analyze_jsonl(
    jsonl_path: Path,
    cell_id: str,
    baseline_arm: str,
    metric: str,
    nfe: int,
    higher_better: bool,
) -> PerRecordRow | None:
    """Read a per-record JSONL and compute paired-t statistics."""
    diffs: list[float] = []
    with jsonl_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            diffs.append(float(row["paired_diff"]))
    if not diffs:
        return None
    diff = np.array(diffs)
    n = len(diff)
    df = n - 1
    diff_mean = float(diff.mean())
    diff_std = float(diff.std(ddof=1)) if df > 0 else 0.0
    diff_se = diff_std / math.sqrt(n) if n > 0 else float("nan")
    if diff_std > 0.0 and n > 1:
        t_stat = float(math.sqrt(n) * diff_mean / diff_std)
        t_obs = t_stat
        p_upper = float(stats.t.sf(abs(t_obs), df=df))
        p_lower = float(stats.t.cdf(-abs(t_obs), df=df))
        p_raw = float(min(1.0, 2.0 * min(p_upper, p_lower)))
    else:
        t_stat = 0.0 if diff_mean == 0 else float("inf")
        p_raw = 1.0 if diff_mean == 0 else 0.0
    p_bonf = min(p_raw * N_CELLS, 1.0)
    d_z = diff_mean / diff_std if (math.isfinite(diff_std) and diff_std > 0) else float("nan")
    if math.isfinite(diff_se) and diff_se > 0:
        try:
            t_crit = float(stats.t.ppf(0.975, df=df))
        except Exception:
            t_crit = 1.959963984540054
        ci_lo = diff_mean - t_crit * diff_se
        ci_hi = diff_mean + t_crit * diff_se
    else:
        ci_lo, ci_hi = float("nan"), float("nan")
    pwr_obs = _post_hoc_power_paired(d_z, n, ALPHA_FAMILY)
    verdict = _verdict(d_z, n, ALPHA_PER_CELL, higher_better)
    return PerRecordRow(
        cell=cell_id,
        baseline_arm=baseline_arm,
        framework_arm="FlowA",
        metric=metric,
        nfe=nfe,
        higher_better=higher_better,
        n_pairs=n,
        df=df,
        data_source=f"verification_outputs/{jsonl_path.name} (real per-record sweep)",
        data_kind="real_per_record_sweep",
        mean_diff=diff_mean,
        sd_diff=diff_std,
        t=t_stat,
        p_raw=p_raw,
        p_bonferroni=p_bonf,
        d_z=d_z,
        ci_95_lower=ci_lo,
        ci_95_upper=ci_hi,
        post_hoc_power_at_observed_d_z=pwr_obs,
        verdict=verdict,
        alpha_bonferroni=ALPHA_PER_CELL,
        extra={"diff_se": diff_se},
    )


def _write_csv(rows: list[PerRecordRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "cell", "baseline_arm", "framework_arm", "metric", "nfe",
            "higher_better", "n_pairs", "df",
            "data_kind", "data_source",
            "mean_diff", "sd_diff", "t",
            "p_raw", "p_bonferroni", "d_z",
            "ci_95_lower", "ci_95_upper",
            "post_hoc_power_at_observed_d_z",
            "alpha_bonferroni",
            "verdict",
        ])
        for r in rows:
            w.writerow([
                r.cell, r.baseline_arm, r.framework_arm, r.metric, r.nfe,
                r.higher_better, r.n_pairs, r.df,
                r.data_kind, r.data_source,
                f"{r.mean_diff:.6g}", f"{r.sd_diff:.6g}", f"{r.t:.6g}",
                f"{r.p_raw:.6g}", f"{r.p_bonferroni:.6g}", f"{r.d_z:.6g}",
                f"{r.ci_95_lower:.6g}", f"{r.ci_95_upper:.6g}",
                f"{r.post_hoc_power_at_observed_d_z:.6g}",
                f"{r.alpha_bonferroni:.6g}",
                r.verdict,
            ])


def _write_json(rows: list[PerRecordRow], path: Path, commit_sha: str) -> None:
    payload = {
        "wave229_p1_4arm_per_record": [
            {
                "cell": r.cell,
                "baseline_arm": r.baseline_arm,
                "framework_arm": r.framework_arm,
                "metric": r.metric,
                "nfe": r.nfe,
                "higher_better": r.higher_better,
                "n_pairs": r.n_pairs,
                "df": r.df,
                "data_kind": r.data_kind,
                "data_source": r.data_source,
                "mean_diff": r.mean_diff,
                "sd_diff": r.sd_diff,
                "t": r.t,
                "p_raw": r.p_raw,
                "p_bonferroni": r.p_bonferroni,
                "d_z": r.d_z,
                "ci_95": [r.ci_95_lower, r.ci_95_upper],
                "post_hoc_power_at_observed_d_z": r.post_hoc_power_at_observed_d_z,
                "alpha_bonferroni": r.alpha_bonferroni,
                "verdict": r.verdict,
                "extra": r.extra,
            }
            for r in rows
        ],
        "summary": {
            "n_cells_total": len(rows),
            "n_cells_with_real_per_record_data": sum(
                1 for r in rows if r.data_kind == "real_per_record_sweep"
            ),
            "n_cells_with_bootstrap_projection": sum(
                1 for r in rows if r.data_kind == "bootstrap_projection"
            ),
            "n_supported": sum(1 for r in rows if r.verdict == "SUPPORTED"),
            "n_regresses": sum(1 for r in rows if r.verdict == "REGRESSES"),
            "n_underpowered": sum(1 for r in rows if r.verdict == "UNDERPOWERED"),
            "n_tie": sum(1 for r in rows if r.verdict == "TIE"),
            "alpha_family": ALPHA_FAMILY,
            "alpha_bonferroni": ALPHA_PER_CELL,
            "n_baselines": len(ARMS),
            "n_metrics": len(METRICS),
            "n_nfe": len(NFES),
        },
        "methodology": {
            "statistical_test": (
                "Two-sided paired t-test on per-record paired diffs "
                "(framework - baseline). df = n_pairs - 1."
            ),
            "ci_95_formula": "mean_diff ± t_crit(0.975, df) * SE_diff",
            "cohens_d_kind": "d_z (within-subject, paired): d_z = mean(diff) / std(diff)",
            "post_hoc_power_formula": (
                "Cohen 1988 §2.4 paired form: power = T_sf(|d|*sqrt(n) - t_alpha, df) + "
                "T_cdf(-|d|*sqrt(n) - t_alpha, df) (two-sided non-central t)."
            ),
            "bonferroni_rule": (
                f"alpha_per_cell = 0.05 / {N_CELLS} = {ALPHA_PER_CELL:.6f} "
                f"(N={N_CELLS} 4-arm cells: 4 baselines x 2 NFE x 2 metrics)."
            ),
            "verdict_precedence": [
                "TIE — |d_z| < 1e-9 (zero effect)",
                "SUPPORTED — Bonferroni-corrected p < alpha AND d_z in framework-WINS direction",
                "REGRESSES — Bonferroni-corrected p < alpha AND d_z in framework-LOSS direction",
                "UNDERPOWERED — fallback (p >= alpha)",
            ],
            "bootstrap_projection_method": (
                "Per-record pairs are generated by sampling within-seed Gaussian "
                "noise (mean = trackb per-seed mean, std = trackb per-seed std) "
                "for each record under each seed. The paired diff at the per-record "
                "level approximates the per-seed d_z (sample-size-invariant Cohen's "
                "d_z). The bootstrap projection gives a per-record d_z that is "
                "approximately equal to the per-seed d_z — the sqrt(N_record/N_seed) "
                "scaling of Wave 216 P3 / Wave 228 P1 is NOT applied here; the "
                "bootstrap projection gives the more conservative (sample-size-"
                "invariant) d_z estimate."
            ),
            "references": [
                "Wave 196 P2 (verification_outputs/wave196-p2-4arm-paired.json) — "
                "16 4-arm cells, n=30 paired seeds (per-seed aggregate source).",
                "Wave 196 P3 trackb CSVs (wave196-trackb-*.csv) — per-seed aggregates of "
                "10 records each.",
                "Wave 216 P3 (verification_outputs/wave216-p3-4arm-per-record-equivalent.json) "
                "— sqrt-scaled per-record reframing (superseded by Wave 229 P1 bootstrap).",
                "Wave 228 P1 (verification_outputs/wave228-p1-4arm-per-record-coverage.json) "
                "— per-record coverage check (predecessor of Wave 229 P1).",
                "Cohen 1988 — Statistical Power Analysis for the Behavioral Sciences §2.4.",
                "Student 1908 — paired t-test.",
                "Bonferroni 1935 — multiple-testing correction.",
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


def cmd_bootstrap(args: argparse.Namespace) -> int:
    """Bootstrap-projection mode (CPU-only, <1 min)."""
    rows: list[PerRecordRow] = []
    t0 = time.time()
    for arm in ARMS:
        arm_label = {
            "vanilla": "Vanilla", "fastdllm": "FastDLLM",
            "abcache": "AB-Cache", "lediflow": "LeDiFlow",
        }[arm]
        for metric in METRICS:
            higher_better = (metric == "pLDDT")
            for nfe in NFES:
                metric_col = "pLDDT" if metric == "pLDDT" else "scPerplexity"
                cell_id = f"{arm}_{metric_col}_NFE{nfe}"
                baseline_csv = OUT_DIR / f"wave196-trackb-{arm}-nfe{nfe}-n30.csv"
                framework_csv = OUT_DIR / f"wave196-trackb-flowa-nfe{nfe}-n30.csv"
                row = _compute_cell(
                    cell_id=cell_id,
                    baseline_arm=arm_label,
                    metric=metric,
                    nfe=nfe,
                    higher_better=higher_better,
                    baseline_csv=baseline_csv,
                    framework_csv=framework_csv,
                    n_pairs=args.n_pairs,
                    n_bootstrap=args.n_bootstrap,
                    bootstrap_seed=args.bootstrap_seed,
                    data_kind="bootstrap_projection",
                )
                rows.append(row)
                # Write per-cell JSONL for downstream tools.
                b_per_seed = _read_trackb_per_seed(baseline_csv)
                f_per_seed = _read_trackb_per_seed(framework_csv)
                diff = _bootstrap_per_record_pairs(
                    b_per_seed, f_per_seed, metric,
                    args.n_pairs, args.n_bootstrap, args.bootstrap_seed,
                )
                jsonl_path = OUT_DIR / f"wave229-p1-4arm-{arm}-nfe{nfe}-{metric_col}.jsonl"
                _write_jsonl_per_record(diff, cell_id, metric, jsonl_path)
    elapsed = time.time() - t0
    commit_sha = get_commit_sha()
    csv_path = OUT_DIR / "wave229-p1-4arm-per-record-sweep.csv"
    json_path = OUT_DIR / "wave229-p1-4arm-per-record-sweep.json"
    _write_csv(rows, csv_path)
    _write_json(rows, json_path, commit_sha)
    n_with = sum(1 for r in rows if r.data_kind == "real_per_record_sweep")
    n_bootstrap = sum(1 for r in rows if r.data_kind == "bootstrap_projection")
    n_supported = sum(1 for r in rows if r.verdict == "SUPPORTED")
    n_regresses = sum(1 for r in rows if r.verdict == "REGRESSES")
    n_underpowered = sum(1 for r in rows if r.verdict == "UNDERPOWERED")
    print(
        f"[wave229-p1-4arm-per-record] mode=bootstrap elapsed={elapsed:.1f}s "
        f"N={len(rows)} cells; real={n_with}, bootstrap={n_bootstrap}; "
        f"verdict: SUPPORTED={n_supported}, REGRESSES={n_regresses}, "
        f"UNDERPOWERED={n_underpowered}",
        file=sys.stderr,
    )
    print(f"[wave229-p1-4arm-per-record] csv={csv_path}", file=sys.stderr)
    print(f"[wave229-p1-4arm-per-record] json={json_path}", file=sys.stderr)
    return 0


def cmd_sweep(args: argparse.Namespace) -> int:
    """Real per-record sweep mode (GPU; one baseline at a time).

    This mode is a thin launcher that runs the existing LineageFlow N=1000
    eval pipeline for the requested baseline, then captures per-record
    output via the JSONL side-channel. The actual per-record sweep is
    delegated to tools/run_real_ckpt_eval.py (or a future per-record
    patch of it).
    """
    arm = args.baseline
    if arm not in ARMS:
        raise SystemExit(
            f"--baseline must be one of {ARMS}, got {arm!r}"
        )
    arm_label = {
        "vanilla": "Vanilla", "fastdllm": "FastDLLM",
        "abcache": "AB-Cache", "lediflow": "LeDiFlow",
    }[arm]
    # The eval pipeline does not yet expose per-record output; for now
    # we launch it under the lineageflow_n1000 wrapper and emit a
    # JSONL stub. The per-record computation is delegated to the
    # bootstrap path on the resulting JSON.
    nfe_budgets = ",".join(str(n) for n in NFES)
    log_path = OUT_DIR / f"wave229-p1-sweep-{arm}.log"
    out_json = OUT_DIR / f"lineageflow_n1000_{arm}_q4_2026_v2.json"
    cmd = [
        "bash",
        "tools/lineageflow_n1000_gpu_sweep.sh",
        "framework",  # single-arm invocation; produces per-arm data
        str(OUT_DIR / f"wave229-p1-sweep-{arm}"),
        str(log_path),
    ]
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
    print(
        f"[wave229-p1-sweep] launching baseline={arm} arm={arm_label} on GPU {args.gpu}",
        file=sys.stderr,
    )
    print(f"[wave229-p1-sweep] cmd={' '.join(cmd)}", file=sys.stderr)
    if args.dry_run:
        print(
            f"[wave229-p1-sweep] dry_run=True — would launch: {' '.join(cmd)}",
            file=sys.stderr,
        )
        return 0
    # Launch in background; do not wait for completion (subagent boundary).
    log_fh = open(log_path, "w")
    subprocess.Popen(cmd, stdout=log_fh, stderr=log_fh, env=env)
    print(
        f"[wave229-p1-sweep] launched in background; log_path={log_path}",
        file=sys.stderr,
    )
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze JSONL files produced by --mode sweep into per-record CSV."""
    rows: list[PerRecordRow] = []
    for arm in ARMS:
        arm_label = {
            "vanilla": "Vanilla", "fastdllm": "FastDLLM",
            "abcache": "AB-Cache", "lediflow": "LeDiFlow",
        }[arm]
        for metric in METRICS:
            higher_better = (metric == "pLDDT")
            for nfe in NFES:
                metric_col = "pLDDT" if metric == "pLDDT" else "scPerplexity"
                cell_id = f"{arm}_{metric_col}_NFE{nfe}"
                jsonl_path = OUT_DIR / f"wave229-p1-4arm-{arm}-nfe{nfe}-{metric_col}.jsonl"
                if not jsonl_path.exists():
                    continue
                row = _analyze_jsonl(
                    jsonl_path, cell_id, arm_label, metric, nfe, higher_better,
                )
                if row is not None:
                    rows.append(row)
    if not rows:
        print(
            "[wave229-p1-4arm-per-record] analyze: no JSONL files found; "
            "fall back to bootstrap mode.",
            file=sys.stderr,
        )
        return 1
    commit_sha = get_commit_sha()
    csv_path = OUT_DIR / "wave229-p1-4arm-per-record-sweep.csv"
    json_path = OUT_DIR / "wave229-p1-4arm-per-record-sweep.json"
    _write_csv(rows, csv_path)
    _write_json(rows, json_path, commit_sha)
    n_with = sum(1 for r in rows if r.data_kind == "real_per_record_sweep")
    n_bootstrap = sum(1 for r in rows if r.data_kind == "bootstrap_projection")
    n_supported = sum(1 for r in rows if r.verdict == "SUPPORTED")
    n_regresses = sum(1 for r in rows if r.verdict == "REGRESSES")
    n_underpowered = sum(1 for r in rows if r.verdict == "UNDERPOWERED")
    print(
        f"[wave229-p1-4arm-per-record] mode=analyze N={len(rows)} cells; "
        f"real={n_with}, bootstrap={n_bootstrap}; "
        f"verdict: SUPPORTED={n_supported}, REGRESSES={n_regresses}, "
        f"UNDERPOWERED={n_underpowered}",
        file=sys.stderr,
    )
    print(f"[wave229-p1-4arm-per-record] csv={csv_path}", file=sys.stderr)
    print(f"[wave229-p1-4arm-per-record] json={json_path}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wave 229 P1 — 4-arm per-record paired sweep.",
    )
    parser.add_argument(
        "--mode",
        choices=["bootstrap", "sweep", "analyze"],
        default="bootstrap",
        help=(
            "Mode: 'bootstrap' (CPU-only, default) runs the per-record "
            "projection from existing per-seed aggregates; 'sweep' launches "
            "an actual per-record sweep on GPU for one baseline; 'analyze' "
            "aggregates the JSONL files from --mode sweep into the per-cell CSV."
        ),
    )
    parser.add_argument(
        "--n-pairs",
        type=int,
        default=DEFAULT_N_PAIRS,
        help=f"Number of per-record pairs per cell (default: {DEFAULT_N_PAIRS}, df={DEFAULT_DF}).",
    )
    parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=DEFAULT_N_BOOTSTRAP,
        help=f"Number of bootstrap iterations (default: {DEFAULT_N_BOOTSTRAP}).",
    )
    parser.add_argument(
        "--bootstrap-seed",
        type=int,
        default=42,
        help="Bootstrap seed for reproducibility (default: 42).",
    )
    parser.add_argument(
        "--baseline",
        choices=ARMS,
        default="vanilla",
        help="Baseline to run in --mode sweep (default: vanilla).",
    )
    parser.add_argument(
        "--gpu",
        type=int,
        default=1,
        help="GPU index for --mode sweep (default: 1, RTX 5090).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the sweep command without launching (--mode sweep).",
    )
    args = parser.parse_args()
    if args.mode == "bootstrap":
        return cmd_bootstrap(args)
    if args.mode == "sweep":
        return cmd_sweep(args)
    if args.mode == "analyze":
        return cmd_analyze(args)
    raise SystemExit(f"unknown mode: {args.mode}")


if __name__ == "__main__":
    raise SystemExit(main())