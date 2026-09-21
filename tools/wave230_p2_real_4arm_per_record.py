"""Wave 230 P2 — REAL 4-arm per-record paired analysis.

Goal: produce real per-record paired diffs for all 16 4-arm cells
(4 baselines x 2 NFE x 2 metrics), using the per-record metrics.jsonl
files that Wave 196 Track B wrote to /tmp/w196/track_b/eval/<cell>/foldability/.
This closes the Wave 229 P1 "16/16 closes via bootstrap projection" gap.

Source data (existing per-record metrics, no new GPU sweep required):
  /tmp/w196/track_b/eval/<arm>_nfe<NFE>_seed<SEED>/foldability/metrics.jsonl
  - one row per record (10 records per seed)
  - fields: qid, header, length, plddt_mean, plddt_median,
             plddt_frac_ge_70, plddt_frac_ge_80,
             sc_log_likelihood, sc_perplexity

Pairing strategy: per-record pairs (baseline_arm, framework_arm) matched by
``(seed, qid)``. The qid encodes the Pfam family + per-record seed; the
pair is deterministic across arms (same family + length profile).

Coverage:
  - 5 arms x 2 NFE x 30 seeds = 300 cells (10 records/seed = 3000 records total)
  - lediflow_nfe100_seed65 missing (empty foldability/ directory) -> 299 cells
  - Per cell: up to 30 seeds x 10 records = 300 per-record pairs
  - For lediflow_nfe100: 29 seeds x 10 = 290 pairs

Outputs:
  - verification_outputs/wave230-p2-real-4arm-per-record.csv
  - verification_outputs/wave230-p2-real-4arm-per-record.json
  - verification_outputs/wave230-p2-real-4arm-<baseline>-nfe<NFE>-<metric>-paired.jsonl
    (one per cell, raw per-record paired diffs)
  - docs/audit/wave230-p2-real-4arm-per-record.md
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
from collections import Counter
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
EVAL_DIR: Path = Path("/tmp/w196/track_b/eval")

#: Total cells in Table B (4-arm): 4 baselines x 2 NFE x 2 metrics = 16.
N_CELLS: int = 16

#: Family-wise alpha (Bonferroni applied: per-cell alpha = 0.05 / N_CELLS).
ALPHA_FAMILY: float = 0.05
ALPHA_PER_CELL: float = ALPHA_FAMILY / N_CELLS  # 0.003125

#: 4-arm sweep arms + 2 NFE + 2 metrics.
ARMS: list[str] = ["vanilla", "fastdllm", "abcache", "lediflow"]
NFES: list[int] = [50, 100]
METRICS: list[str] = ["pLDDT", "scPerplexity"]

#: Per-seed record count (from the metrics.jsonl files: q0..q9).
N_RECORDS_PER_SEED: int = 10

#: Seed range for Wave 196 Track B (seeds 42..71, 30 seeds).
SEEDS: list[int] = list(range(42, 72))

#: Cells where one or more seeds have missing per-record data.
MISSING_SEEDS: dict[tuple[str, int], list[int]] = {
    ("lediflow", 100): [65],  # empty foldability/ directory
}


@dataclass
class RealPerRecordRow:
    """One row of the wave230-p2 real 4-arm per-record paired table."""

    cell: str
    baseline_arm: str
    framework_arm: str
    metric: str
    nfe: int
    higher_better: bool
    n_pairs: int
    df: int
    data_kind: str  # always "real_per_record_paired"
    data_source: str
    n_seeds_used: int
    n_seeds_expected: int
    seeds_missing: list[int]
    mean_diff: float
    sd_diff: float
    diff_se: float
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


def _read_per_record_metrics(cell_dir: Path) -> dict[str, dict[str, float]]:
    """Read per-record metrics.jsonl from a Wave 196 Track B cell directory.

    Returns dict[qid] -> {"plddt_mean": float, "sc_perplexity": float}.
    """
    fp = cell_dir / "foldability" / "metrics.jsonl"
    out: dict[str, dict[str, float]] = {}
    if not fp.exists():
        return out
    with fp.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            qid = row["qid"]
            out[qid] = {
                "plddt_mean": float(row["plddt_mean"]),
                "sc_perplexity": float(row["sc_perplexity"]),
            }
    return out


def _build_per_record_pairs(
    baseline_arm: str, framework_arm: str, nfe: int, metric: str,
    missing_seeds: list[int],
) -> tuple[list[float], dict[str, Any]]:
    """Build per-record paired diffs by pairing baseline_arm and framework_arm
    across all common (seed, qid) tuples.

    Returns (paired_diffs, extra_info) where paired_diffs is the list of
    framework_per_record - baseline_per_record values, and extra_info contains
    the seeds_used, seeds_missing, qids_per_seed stats.
    """
    metric_key = "plddt_mean" if metric == "pLDDT" else "sc_perplexity"
    paired_diffs: list[float] = []
    seeds_used: list[int] = []
    n_records_per_seed_used: list[int] = []
    for seed in SEEDS:
        if seed in missing_seeds:
            continue
        b_dir = EVAL_DIR / f"{baseline_arm}_nfe{nfe}_seed{seed}"
        f_dir = EVAL_DIR / f"{framework_arm}_nfe{nfe}_seed{seed}"
        if not b_dir.exists() or not f_dir.exists():
            continue
        b_records = _read_per_record_metrics(b_dir)
        f_records = _read_per_record_metrics(f_dir)
        if not b_records or not f_records:
            continue
        common_qids = sorted(set(b_records) & set(f_records))
        if not common_qids:
            continue
        seeds_used.append(seed)
        n_records_per_seed_used.append(len(common_qids))
        for qid in common_qids:
            b_val = b_records[qid][metric_key]
            f_val = f_records[qid][metric_key]
            paired_diffs.append(f_val - b_val)
    extra = {
        "seeds_used": seeds_used,
        "seeds_missing": missing_seeds,
        "n_seeds_used": len(seeds_used),
        "n_records_per_seed_min": min(n_records_per_seed_used) if n_records_per_seed_used else 0,
        "n_records_per_seed_max": max(n_records_per_seed_used) if n_records_per_seed_used else 0,
    }
    return paired_diffs, extra


def _post_hoc_power_paired(d_z: float, n: int, alpha: float) -> float:
    """Two-sided post-hoc power at observed d_z, sample size n, alpha."""
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
    cell_id: str, baseline_arm: str, metric: str, nfe: int, higher_better: bool,
) -> RealPerRecordRow:
    """Compute real per-record paired-t for one cell."""
    missing_seeds = MISSING_SEEDS.get((baseline_arm, nfe), [])
    diffs, extra = _build_per_record_pairs(
        baseline_arm, "flowa", nfe, metric, missing_seeds,
    )
    diff = np.array(diffs, dtype=np.float64)
    n = len(diff)
    df = n - 1
    diff_mean = float(diff.mean()) if n > 0 else float("nan")
    diff_std = float(diff.std(ddof=1)) if df > 0 else 0.0
    diff_se = diff_std / math.sqrt(n) if n > 0 else float("nan")
    if diff_std > 0.0 and n > 1:
        t_stat = float(math.sqrt(n) * diff_mean / diff_std)
        p_upper = float(stats.t.sf(abs(t_stat), df=df))
        p_lower = float(stats.t.cdf(-abs(t_stat), df=df))
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
    arm_label = {
        "vanilla": "Vanilla", "fastdllm": "FastDLLM",
        "abcache": "AB-Cache", "lediflow": "LeDiFlow",
    }[baseline_arm]
    return RealPerRecordRow(
        cell=cell_id,
        baseline_arm=arm_label,
        framework_arm="FlowA",
        metric=metric,
        nfe=nfe,
        higher_better=higher_better,
        n_pairs=n,
        df=df,
        data_kind="real_per_record_paired",
        data_source=(
            f"per-record metrics.jsonl from "
            f"/tmp/w196/track_b/eval/<{baseline_arm}|flowa>_nfe{nfe}_seed<SEED>/foldability/"
            f"metrics.jsonl (paired by seed+qid; {n} pairs, df={df}, "
            f"{extra['n_seeds_used']}/{len(SEEDS)} seeds used)"
        ),
        n_seeds_used=extra["n_seeds_used"],
        n_seeds_expected=len(SEEDS),
        seeds_missing=extra["seeds_missing"],
        mean_diff=diff_mean,
        sd_diff=diff_std,
        diff_se=diff_se,
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
            "n_records_per_seed_min": extra["n_records_per_seed_min"],
            "n_records_per_seed_max": extra["n_records_per_seed_max"],
            "n_records_design_total": 300,
            "n_records_actual_total": n,
            "seeds_used": extra["seeds_used"],
            "diff_se": diff_se,
            "framework_per_record_mean": diff_mean,
        },
    )


def _write_per_record_paired_jsonl(
    baseline_arm: str, nfe: int, metric: str, missing_seeds: list[int],
    out_path: Path,
) -> int:
    """Write per-record paired diffs to JSONL.

    Returns the number of records written.
    """
    metric_key = "plddt_mean" if metric == "pLDDT" else "sc_perplexity"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n_written = 0
    with out_path.open("w") as fh:
        for seed in SEEDS:
            if seed in missing_seeds:
                continue
            b_dir = EVAL_DIR / f"{baseline_arm}_nfe{nfe}_seed{seed}"
            f_dir = EVAL_DIR / f"flowa_nfe{nfe}_seed{seed}"
            if not b_dir.exists() or not f_dir.exists():
                continue
            b_records = _read_per_record_metrics(b_dir)
            f_records = _read_per_record_metrics(f_dir)
            if not b_records or not f_records:
                continue
            common_qids = sorted(set(b_records) & set(f_records))
            for qid in common_qids:
                b_val = b_records[qid][metric_key]
                f_val = f_records[qid][metric_key]
                row = {
                    "cell": f"{baseline_arm}_{metric}_NFE{nfe}",
                    "baseline_arm": baseline_arm,
                    "framework_arm": "flowa",
                    "metric": metric,
                    "metric_key": metric_key,
                    "nfe": nfe,
                    "seed": seed,
                    "qid": qid,
                    "baseline_value": float(b_val),
                    "framework_value": float(f_val),
                    "paired_diff": float(f_val - b_val),
                }
                fh.write(json.dumps(row) + "\n")
                n_written += 1
    return n_written


def _write_csv(rows: list[RealPerRecordRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "cell", "baseline_arm", "framework_arm", "metric", "nfe",
            "higher_better", "n_pairs", "df",
            "data_kind", "data_source",
            "n_seeds_used", "n_seeds_expected",
            "mean_diff", "sd_diff", "diff_se",
            "t", "p_raw", "p_bonferroni", "d_z",
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
                r.n_seeds_used, r.n_seeds_expected,
                f"{r.mean_diff:.6g}", f"{r.sd_diff:.6g}", f"{r.diff_se:.6g}",
                f"{r.t:.6g}", f"{r.p_raw:.6g}", f"{r.p_bonferroni:.6g}", f"{r.d_z:.6g}",
                f"{r.ci_95_lower:.6g}", f"{r.ci_95_upper:.6g}",
                f"{r.post_hoc_power_at_observed_d_z:.6g}",
                f"{r.alpha_bonferroni:.6g}",
                r.verdict,
            ])


def _write_json(
    rows: list[RealPerRecordRow], path: Path, commit_sha: str,
    per_cell_n_records: dict[str, int],
) -> None:
    payload = {
        "wave230_p2_real_4arm_per_record": [
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
                "n_seeds_used": r.n_seeds_used,
                "n_seeds_expected": r.n_seeds_expected,
                "seeds_missing": r.seeds_missing,
                "mean_diff": r.mean_diff,
                "sd_diff": r.sd_diff,
                "diff_se": r.diff_se,
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
                1 for r in rows if r.data_kind == "real_per_record_paired"
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
            "per_cell_n_records": per_cell_n_records,
        },
        "methodology": {
            "data_source": (
                "Per-record metrics.jsonl files written by Wave 196 Track B "
                "OmegaFold foldability + ESM-IF self_consistency eval pipeline "
                "(see docs/audit/wave196-p2-4arm-n30.md). Each "
                "/tmp/w196/track_b/eval/<arm>_nfe<NFE>_seed<SEED>/foldability/"
                "metrics.jsonl contains 10 per-record rows with fields "
                "qid, plddt_mean, sc_perplexity. Per-record pairs are formed "
                "by matching (seed, qid) across baseline and framework arms."
            ),
            "missing_data": (
                "lediflow_nfe100_seed65 has empty foldability/ directory "
                "(no per-record metrics.jsonl); this seed is excluded from "
                "the lediflow_nfe100 cells. All other cells use all 30 seeds."
            ),
            "pairing_strategy": (
                "Per-record pairs are formed by matching (seed, qid) across "
                "the baseline arm (vanilla/fastdllm/abcache/lediflow) and the "
                "FlowA framework arm. The qid encodes the Pfam family + "
                "per-record seed, so paired records share the same Pfam family "
                "and length profile."
            ),
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
            "references": [
                "Wave 196 P2 (verification_outputs/wave196-p2-4arm-paired.csv) — "
                "per-seed paired-t at n=30 (precursor; per-record equivalent was NOT "
                "emitted at the time).",
                "Wave 228 P1 (verification_outputs/wave228-p1-4arm-per-record-coverage.csv) — "
                "documents the per-record coverage gap (0/16 raw cells).",
                "Wave 229 P1 (verification_outputs/wave229-p1-4arm-per-record-sweep.csv) — "
                "bootstrap projection that closed 16/16 cells via per-seed Gaussian resampling. "
                "This Wave 230 P2 supersedes Wave 229 P1 with REAL per-record data "
                "from the original Wave 196 Track B metrics.jsonl files.",
                "Cohen 1988 — Statistical Power Analysis §2.4.",
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


def main() -> int:
    rows: list[RealPerRecordRow] = []
    per_cell_n_records: dict[str, int] = {}
    for baseline_arm in ARMS:
        arm_label = {
            "vanilla": "Vanilla", "fastdllm": "FastDLLM",
            "abcache": "AB-Cache", "lediflow": "LeDiFlow",
        }[baseline_arm]
        for metric in METRICS:
            higher_better = (metric == "pLDDT")
            for nfe in NFES:
                cell_id = f"{baseline_arm}_{metric}_NFE{nfe}"
                missing_seeds = MISSING_SEEDS.get((baseline_arm, nfe), [])
                row = _compute_cell(
                    cell_id=cell_id,
                    baseline_arm=baseline_arm,
                    metric=metric,
                    nfe=nfe,
                    higher_better=higher_better,
                )
                rows.append(row)
                # Write per-cell JSONL
                jsonl_path = (
                    OUT_DIR
                    / f"wave230-p2-real-4arm-{baseline_arm}-nfe{nfe}-{metric}-paired.jsonl"
                )
                n_written = _write_per_record_paired_jsonl(
                    baseline_arm, nfe, metric, missing_seeds, jsonl_path,
                )
                per_cell_n_records[cell_id] = n_written
    commit_sha = get_commit_sha()
    csv_path = OUT_DIR / "wave230-p2-real-4arm-per-record.csv"
    json_path = OUT_DIR / "wave230-p2-real-4arm-per-record.json"
    _write_csv(rows, csv_path)
    _write_json(rows, json_path, commit_sha, per_cell_n_records)
    counts = Counter(r.verdict for r in rows)
    n_with = sum(1 for r in rows if r.data_kind == "real_per_record_paired")
    print(
        f"[wave230-p2-real-4arm-per-record] N={len(rows)} cells; "
        f"real={n_with}; verdict: SUPPORTED={counts.get('SUPPORTED', 0)}, "
        f"REGRESSES={counts.get('REGRESSES', 0)}, "
        f"UNDERPOWERED={counts.get('UNDERPOWERED', 0)}, "
        f"TIE={counts.get('TIE', 0)}",
        file=sys.stderr,
    )
    print(f"[wave230-p2-real-4arm-per-record] csv={csv_path}", file=sys.stderr)
    print(f"[wave230-p2-real-4arm-per-record] json={json_path}", file=sys.stderr)
    print(f"[wave230-p2-real-4arm-per-record] commit_sha={commit_sha}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())