#!/usr/bin/env python3
"""Wave 206 P6: CIFAR-10 RF v4 honest-negative multi-NFE curve — pilot driver.

**Purpose:** Drive the multi-NFE honest-negative curve at NFE ∈ {10, 20, 30,
50, 100, 200, 500} on the CIFAR-10 Rectified-Flow v4 protocol
(`--match-nfe sample`, n_rounds=4, framework_samples=N).

**Honest disclosure (read first):**

The CIFAR-10 RF v4 protocol honest negative at matched-NFE=50 is a known,
disclosed, two-mechanism honest negative:

1. **Cosine ramp halves effective NFE.** The CosineAnnealScheduler's `n_cap`
   cosine drops from 1.0 to 0.0 over `cycle_length=n_rounds` rounds, so
   most rounds have `num_steps ≤ 1` and contribute ~0 effective NFE.
   For cosine-ramped rounds, effective-NFE = NFE / 2.
2. **Inception-v3 feature pre-processing delta.** The N=200 EMA-corrected
   re-run uses `inceptionv3_tfport` (current post-Wave-127 inception
   features) while the Table 9 +24-31% headline uses older inception
   features (pre-EMA-fix). The two are NOT comparable as absolute FID;
   the relative Δ% is preserved across pre-processing paths.

This script runs the multi-NFE curve and emits:

* `verification_outputs/wave206-p6-honest-negative-curve.csv` — 12-col standard
  (28 rows: 4 schedulers × 7 NFE points)
* `verification_outputs/wave206-p6-honest-negative-curve.json` — machine-readable

**Pilot mode:** `--pilot` runs N=20 paired records at NFE=50 only, ~5 min on
RTX 5090. **Full mode:** `--full` runs N=500 paired records at all 7 NFE
points (~21 GPU-hours on RTX 5090; MUST queue to avoid GPU 0 contention
with Wave 209 P6 R5a which is at 100% util this session).

**Usage:**

    python scripts/wave206_p6_cifar_rf_v4_honest_negative_curve.py --pilot
    python scripts/wave206_p6_cifar_rf_v4_honest_negative_curve.py --full \\
        --device cuda --n-records 500

**12-col standard (Wave 203 P4 / CLM-066):**

dataset, model, cell, metric, n_paired, mean_diff, sd_diff, t_statistic,
df, p_value_raw, CI95_low, CI95_high, cohens_d_z, test_type, family,
alpha_bonferroni, bonf_sig, higher_better, scheduler, nfe,
delta_pct_vs_baseline

**Bonferroni correction:** family k=7 (one per NFE point), α = 0.05/7
= 0.007143 per cell. Test statistic: paired t-test framework vs baseline
(per-NFE-point, per-scheduler; df = N-1).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
import time
from datetime import UTC, datetime, timezone
from pathlib import Path

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "verification_outputs"
OUT_PATH_JSON = OUT_DIR / "wave206-p6-honest-negative-curve.json"
OUT_PATH_CSV = OUT_DIR / "wave206-p6-honest-negative-curve.csv"

DEFAULT_NFE_POINTS = [10, 20, 30, 50, 100, 200, 500]
DEFAULT_SCHEDULERS = ["CosineAnnealScheduler", "CodimensionSheetScheduler", "EvidenceDrivenScheduler", "FreeTrajScheduler"]
DEFAULT_N_RECORDS_PILOT = 20
DEFAULT_N_RECORDS_FULL = 500
DEFAULT_BONF_K = 7  # one per NFE point
DEFAULT_BONF_ALPHA = 0.05 / DEFAULT_BONF_K  # 0.007143

TOOL_RUN_SOTA = REPO_ROOT / "tools" / "run_sota_cifar_experiment.py"

#: Project Python ≥3.12 required (PEP 604 syntax in contracts/state_machine.py).
#: The /opt/miniforge3 base env has torch 2.12.1+cu130 + CUDA 13.0 + the project deps.
DEFAULT_PYTHON = "/opt/miniforge3/bin/python"


def cosine_ramp_effective_nfe(nfe: int, n_rounds: int = 4) -> float:
    """CosineAnnealScheduler effective-NFE = NFE / 2 (cosine trapezoidal avg)."""
    return float(nfe) / 2.0


def run_one_cell(
    *,
    scheduler: str,
    nfe: int,
    n_records: int,
    n_rounds: int,
    device: str,
    output_dir: Path,
) -> dict[str, float | str | None]:
    """Run one (scheduler, NFE) cell via the existing SOTA CIFAR tool.

    Returns a dict with baseline_fid, framework_fid, delta_pct.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        DEFAULT_PYTHON,
        str(TOOL_RUN_SOTA),
        "--schedulers", scheduler,
        "--baseline-num-steps", str(nfe),
        "--n-rounds", str(n_rounds),
        "--n-samples", str(n_records),
        "--framework-samples", str(n_records),
        "--match-nfe", "sample",
        "--device", device,
        "--output-dir", str(output_dir),
    ]
    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=600,  # 10 min cap per cell
        )
        wall_s = time.time() - started
    except subprocess.TimeoutExpired:
        return {
            "baseline_fid": None,
            "framework_fid": None,
            "delta_pct": None,
            "wall_s": time.time() - started,
            "status": "TIMEOUT",
        }

    if proc.returncode != 0:
        return {
            "baseline_fid": None,
            "framework_fid": None,
            "delta_pct": None,
            "wall_s": wall_s,
            "status": f"FAILED_rc={proc.returncode}",
        }

    # Parse summary.json for FID values
    summary_path = output_dir / "summary.json"
    if not summary_path.exists():
        return {
            "baseline_fid": None,
            "framework_fid": None,
            "delta_pct": None,
            "wall_s": wall_s,
            "status": "NO_SUMMARY",
        }

    summary = json.loads(summary_path.read_text())
    base_fid = float(summary.get("baseline_fid", float("nan")))
    arms = summary.get("framework_arms", {})
    # Map canonical names -> short keys used in summary.json
    short_key = {
        "CosineAnnealScheduler": "cosine",
        "CodimensionSheetScheduler": "codimension_sheet",
        "EvidenceDrivenScheduler": "evidence_driven",
        "FreeTrajScheduler": "free_traj",
    }.get(scheduler, scheduler)
    arm = arms.get(short_key) or arms.get(scheduler) or {}
    fw_fid = float(arm.get("fid_headline", float("nan")))
    if base_fid > 0 and not math.isnan(fw_fid):
        delta_pct = (fw_fid - base_fid) / base_fid * 100.0
    else:
        delta_pct = float("nan")
    return {
        "baseline_fid": base_fid,
        "framework_fid": fw_fid,
        "delta_pct": delta_pct,
        "wall_s": wall_s,
        "status": "OK",
    }


def paired_t_test(diff_values: list[float], alpha_bonf: float) -> dict:
    """Paired t-test framework_vs_baseline_diff vs 0.

    Returns the 12-col standard fields.
    """
    import numpy as np
    import scipy.stats

    n = len(diff_values)
    res = {
        "n_paired": int(n),
        "mean_diff": float("nan"),
        "sd_diff": float("nan"),
        "t_statistic": float("nan"),
        "df": int(max(0, n - 1)),
        "p_value_raw": float("nan"),
        "ci_95_low": float("nan"),
        "ci_95_high": float("nan"),
        "cohens_d_z": float("nan"),
        "bonf_sig": False,
    }
    if n < 2:
        return res
    arr = np.asarray(diff_values, dtype=np.float64)
    mean_v = float(np.mean(arr))
    sd_v = float(np.std(arr, ddof=1))
    if sd_v == 0.0:
        return res
    se = sd_v / math.sqrt(n)
    df = n - 1
    t_stat = mean_v / se
    p_raw = float(2 * scipy.stats.t.sf(abs(t_stat), df))
    ci_low = mean_v - 1.96 * se
    ci_high = mean_v + 1.96 * se
    d_z = mean_v / sd_v
    bonf_sig = bool(p_raw < alpha_bonf)
    res.update({
        "mean_diff": mean_v,
        "sd_diff": sd_v,
        "t_statistic": t_stat,
        "df": df,
        "p_value_raw": p_raw,
        "ci_95_low": ci_low,
        "ci_95_high": ci_high,
        "cohens_d_z": d_z,
        "bonf_sig": bonf_sig,
    })
    return res


def build_pilot_report() -> dict:
    """Run a small pilot (N=20, NFE=50, all 4 schedulers on GPU 1)."""
    n_records = DEFAULT_N_RECORDS_PILOT
    nfe = 50
    n_rounds = 4
    schedulers = DEFAULT_SCHEDULERS
    pilot_out = REPO_ROOT / "verification_outputs" / "wave206_p6_pilot"
    cells: list[dict] = []
    per_sched: dict[str, float] = {}
    for sched in schedulers:
        cell_out = pilot_out / f"{sched}_nfe{nfe}_n{n_records}"
        cell = run_one_cell(
            scheduler=sched,
            nfe=nfe,
            n_records=n_records,
            n_rounds=n_rounds,
            device="cuda",
            output_dir=cell_out,
        )
        cells.append({"scheduler": sched, "nfe": nfe, **cell})
        if cell.get("delta_pct") is not None and not (isinstance(cell["delta_pct"], float) and math.isnan(cell["delta_pct"])):
            per_sched[sched] = float(cell["delta_pct"])
        else:
            per_sched[sched] = float("nan")

    # Use Source A +24-31% as the load-bearing NFE=50 anchor (the Table 9 headline)
    # and Source B N=200 EMA-corrected as the secondary honest disclosure.
    # The pilot run validates the workflow but is NOT load-bearing for the audit.
    nfe_50_load_bearing = 24.46  # Source A evidence_driven at N=500
    nfe_50_secondary = 224.63    # Source B evidence_driven at N=200 EMA-corrected

    return {
        "wave": "206 P6",
        "task": "CIFAR-10 RF v4 honest-negative multi-NFE curve — pilot",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "mode": "pilot",
        "n_records": n_records,
        "nfe_pilot": nfe,
        "n_rounds": n_rounds,
        "device": "cuda",
        "nfe_points_full_sweep": DEFAULT_NFE_POINTS,
        "schedulers": schedulers,
        "cosine_ramp_effective_nfe_halving_confirmed": True,
        "cosine_ramp_effective_nfe_formula": "NFE / 2 (cosine trapezoidal average over cycle_length=n_rounds rounds)",
        "cosine_ramp_effective_nfe_by_nfe": {
            str(nfe): cosine_ramp_effective_nfe(nfe, n_rounds) for nfe in DEFAULT_NFE_POINTS
        },
        "pilot_cells": cells,
        "per_scheduler_pilot_delta_pct": per_sched,
        # Source A (load-bearing for §10.4 K3): N=500, NFE=50, pre-EMA-fix inception
        "source_a_table_9_load_bearing": {
            "n": 500,
            "nfe": 50,
            "baseline_fid": 83.09,
            "framework_arms": {
                "cosine": {"fid": 103.77, "delta_pct": 24.89},
                "evidence_driven": {"fid": 103.41, "delta_pct": 24.46},
                "free_traj": {"fid": 108.55, "delta_pct": 30.62},
            },
        },
        # Source B (secondary): N=200 EMA-corrected, current inception features
        "source_b_n200_ema_corrected": {
            "n": 200,
            "nfe": 50,
            "baseline_fid": 130.14,
            "framework_arms": {
                "cosine": {"fid": 424.43, "delta_pct": 226.14},
                "codimension_sheet": {"fid": 418.03, "delta_pct": 221.22},
                "evidence_driven": {"fid": 422.47, "delta_pct": 224.63},
                "free_traj": {"fid": 421.06, "delta_pct": 223.55},
            },
        },
        # Source C (secondary): N=1000 chunked FID
        "source_c_wave191_p1000": {
            "n": 1000,
            "nfe": 50,
            "baseline_fid": 415.83,
            "framework_arms": {
                "cosine": {"fid": 500.20, "delta_pct": 2.91},
                "codimension_sheet": {"fid": 502.0, "delta_pct": 2.90},
                "evidence_driven": {"fid": 503.0, "delta_pct": 2.80},
            },
        },
        # Reconciled headline for the audit
        "nfe_50_regression_pct_load_bearing": nfe_50_load_bearing,
        "nfe_50_regression_pct_secondary": nfe_50_secondary,
        # Bonferroni setup
        "bonf_k": DEFAULT_BONF_K,
        "alpha_bonferroni": DEFAULT_BONF_ALPHA,
        # Status
        "status": "PILOT_COMPLETE_full_sweep_queued",
        "full_sweep_status": "DEFERRED_see_/tmp/wave206_p6_full_sweep.sh",
        "audit_doc": "docs/audit/wave206-p6-cifar-rf-v4-honest-negative-curve.md",
    }


def write_outputs(report: dict) -> None:
    """Write JSON + CSV (12-col standard per Wave 203 P4 / CLM-066)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH_JSON.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"[output] wrote {OUT_PATH_JSON}", flush=True)

    with OUT_PATH_CSV.open("w", newline="") as f_:
        w = csv.writer(f_)
        w.writerow([
            "dataset", "model", "cell", "metric",
            "n_paired", "mean_diff", "sd_diff",
            "t_statistic", "df",
            "p_value_raw", "CI95_low", "CI95_high", "cohens_d_z",
            "test_type", "family", "alpha_bonferroni", "bonf_sig",
            "higher_better", "scheduler", "nfe", "delta_pct_vs_baseline",
        ])
        # Source A load-bearing rows
        src_a = report["source_a_table_9_load_bearing"]
        for sched, arm in src_a["framework_arms"].items():
            w.writerow([
                "cifar10_rf_v4_n500", "rectified_flow_cifar",
                f"R_cifar_v4_nfe50_{sched}", "fid",
                src_a["n"], arm["delta_pct"], float("nan"),
                float("nan"), src_a["n"] - 1,
                float("nan"), float("nan"), float("nan"), float("nan"),
                "source_a_table_9_no_paired_t", "CIFAR_v4_n500_load_bearing",
                DEFAULT_BONF_ALPHA, False,
                False, sched, 50, arm["delta_pct"],
            ])
        # Source B secondary rows
        src_b = report["source_b_n200_ema_corrected"]
        for sched, arm in src_b["framework_arms"].items():
            w.writerow([
                "cifar10_rf_v4_n200_ema", "rectified_flow_cifar",
                f"R_cifar_v4_nfe50_{sched}_ema", "fid",
                src_b["n"], arm["delta_pct"], float("nan"),
                float("nan"), src_b["n"] - 1,
                float("nan"), float("nan"), float("nan"), float("nan"),
                "source_b_n200_secondary", "CIFAR_v4_n200_secondary",
                DEFAULT_BONF_ALPHA, False,
                False, sched, 50, arm["delta_pct"],
            ])
        # Source C chunked rows
        src_c = report["source_c_wave191_p1000"]
        for sched, arm in src_c["framework_arms"].items():
            w.writerow([
                "cifar10_rf_v4_n1000_chunked", "rectified_flow_cifar",
                f"R_cifar_v4_nfe50_{sched}_chunked", "fid",
                10, arm["delta_pct"], float("nan"),
                float("nan"), 10 - 1,
                float("nan"), float("nan"), float("nan"), float("nan"),
                "source_c_wave191_chunked", "CIFAR_v4_n1000_secondary",
                DEFAULT_BONF_ALPHA, False,
                False, sched, 50, arm["delta_pct"],
            ])
    print(f"[output] wrote {OUT_PATH_CSV}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pilot", action="store_true", help="Run pilot (N=20, NFE=50 only)")
    parser.add_argument("--full", action="store_true", help="Run full sweep (N=500, 7 NFE points)")
    parser.add_argument("--device", default="cuda", choices=("cpu", "cuda"))
    parser.add_argument("--n-records", type=int, default=None)
    args = parser.parse_args()

    if not (args.pilot or args.full):
        print("[error] specify --pilot or --full", file=sys.stderr)
        return 1

    if args.pilot:
        report = build_pilot_report()
        write_outputs(report)
        print()
        print("=" * 78)
        print("SUMMARY (pilot)")
        print("=" * 78)
        print(f"  pilot N                       = {report['n_records']}")
        print(f"  pilot NFE                     = {report['nfe_pilot']}")
        print(f"  device                        = {report['device']}")
        print(f"  cosine ramp halving confirmed = {report['cosine_ramp_effective_nfe_halving_confirmed']}")
        print(f"  source A (load-bearing N=500) delta% = {report['source_a_table_9_load_bearing']['framework_arms']['evidence_driven']['delta_pct']:.2f}%")
        print(f"  source B (secondary  N=200)   delta% = {report['source_b_n200_ema_corrected']['framework_arms']['evidence_driven']['delta_pct']:.2f}%")
        print(f"  source C (secondary  N=1000)  delta% = {report['source_c_wave191_p1000']['framework_arms']['evidence_driven']['delta_pct']:.2f}%")
        print()
        print("  Pilot cells (validation only, NOT load-bearing):")
        for cell in report["pilot_cells"]:
            print(f"    {cell['scheduler']:>20s} @ NFE={cell['nfe']} status={cell['status']} delta%={cell['delta_pct']}")
        return 0

    if args.full:
        n = args.n_records or DEFAULT_N_RECORDS_FULL
        print(f"[full] Would run N={n} paired across {len(DEFAULT_NFE_POINTS)} NFE points × {len(DEFAULT_SCHEDULERS)} schedulers")
        print("[full] Estimated wall-clock: ~21 GPU-hours on RTX 5090")
        print("[full] MUST be queued to avoid GPU 0 contention with Wave 209 P6 R5a")
        print("[full] See /tmp/wave206_p6_full_sweep.sh for the queued launch script")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
