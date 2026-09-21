#!/usr/bin/env python3
"""Wave 235 P4: 3-seed paired-t analysis (no fresh generation, analysis-only).

Reads existing wave235-p4-flowmol3-seed{N}-{baseline,framework}.json + sidecar
.smiles.txt files, computes per-seed fg_dev / per-record REOS diffs, and
the pooled paired-t summary. Also pulls in Wave 87 seed=42 reference.

Inputs expected:
  verification_outputs/wave235-p4-flowmol3-seed43-baseline.json + .smiles.txt
  verification_outputs/wave235-p4-flowmol3-seed43-framework.json + .smiles.txt
  verification_outputs/wave235-p4-flowmol3-seed44-baseline.json + .smiles.txt
  verification_outputs/wave235-p4-flowmol3-seed44-framework.json + .smiles.txt
  verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json  (seed 42 ref)

Outputs:
  verification_outputs/wave235-p4-flowmol3-3seed-per-record.csv
  verification_outputs/wave235-p4-flowmol3-3seed.csv
  verification_outputs/wave235-p4-flowmol3-3seed.json
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
import time
from pathlib import Path

REPO = Path("/home/hugo/codes/flowa-multistep-reinference")
OUT_DIR = REPO / "verification_outputs"

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
sys.path.insert(0, str(REPO))

import numpy as np
import scipy.stats

sys.path.insert(0, str(REPO / "scripts"))
import wave235_p4_flowmol3_3seed as w  # noqa: E402

NEW_SEEDS = [43, 44]


def _load_arm(seed: int, arm: str) -> tuple[dict, list]:
    base = OUT_DIR / f"wave235-p4-flowmol3-seed{seed}-{arm}"
    js = json.loads(base.with_suffix(".json").read_text())
    smi = base.with_suffix(".smiles.txt").read_text().splitlines()
    smi = [s for s in smi if s]
    return js, smi


def main() -> int:
    print("=" * 78, flush=True)
    print("Wave 235 P4: 3-seed pooled paired-t analysis (analysis-only)", flush=True)
    print("=" * 78, flush=True)

    per_seed_results: dict[int, dict] = {}
    for seed in NEW_SEEDS:
        per_seed_results[seed] = {}
        for arm in ("baseline", "framework"):
            js, smi = _load_arm(seed, arm)
            print(f"[seed={seed} {arm}] loaded n_sampled={js['n_sampled']} "
                  f"smiles_count={js.get('smiles_count', len(smi))} "
                  f"wallclock={js['wallclock_s']:.1f}s", flush=True)
            t_m = time.perf_counter()
            metrics = w._compute_paper_metrics(smi)
            print(f"[seed={seed} {arm}] metrics in {time.perf_counter()-t_m:.1f}s: "
                  f"fg_dev={metrics['fg_dev']:.4f}", flush=True)
            per_seed_results[seed][arm] = {
                "metrics": metrics,
                "smiles_list": smi,
                "raw": js,
            }

    # ---- Per-record REOS flags per seed (for per-record paired-t) ----
    print("\n--- Per-record REOS flags (for paired-t) ---", flush=True)
    per_record_rows: list[dict] = []
    for seed in NEW_SEEDS:
        for arm_name in ("baseline", "framework"):
            sl = per_seed_results[seed][arm_name]["smiles_list"]
            t_m = time.perf_counter()
            flags = w._per_record_reos_flags(sl)
            print(f"[seed={seed} {arm_name}] REOS flags in {time.perf_counter()-t_m:.1f}s", flush=True)
            per_seed_results[seed][arm_name]["reos_flags"] = flags
            for i, smi in enumerate(sl):
                per_record_rows.append({
                    "seed": int(seed),
                    "arm": arm_name,
                    "idx": int(i),
                    "smiles": smi,
                    "reos_flag": int(flags[i]),
                })

    per_record_csv = OUT_DIR / "wave235-p4-flowmol3-3seed-per-record.csv"
    with per_record_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["seed", "arm", "idx", "smiles", "reos_flag"],
        )
        writer.writeheader()
        writer.writerows(per_record_rows)
    print(f"Wrote {per_record_csv} ({len(per_record_rows)} rows)", flush=True)

    # ---- Per-seed aggregate summary ----
    per_seed_summaries: list[dict] = []
    for seed in NEW_SEEDS:
        s = w._per_seed_summary(
            seed,
            {"metrics": per_seed_results[seed]["baseline"]["metrics"],
             "n_sampled": per_seed_results[seed]["baseline"]["raw"]["n_sampled"]},
            {"metrics": per_seed_results[seed]["framework"]["metrics"],
             "n_sampled": per_seed_results[seed]["framework"]["raw"]["n_sampled"]},
        )
        per_seed_summaries.append(s)

    # ---- 2-seed pooled paired-t across per-seed mean_diffs ----
    diffs_per_seed = np.array([s["mean_diff"] for s in per_seed_summaries], dtype=np.float64)
    per_seed_paired = w._paired_t(diffs_per_seed)

    # ---- Pooled per-record paired-t (REOS flags diff) ----
    pooled_diffs: list[float] = []
    for seed in NEW_SEEDS:
        b_flags = np.array(per_seed_results[seed]["baseline"]["reos_flags"], dtype=np.int64)
        f_flags = np.array(per_seed_results[seed]["framework"]["reos_flags"], dtype=np.int64)
        n_min = min(len(b_flags), len(f_flags))
        diff = (f_flags[:n_min] - b_flags[:n_min]).astype(np.float64)
        pooled_diffs.extend(diff.tolist())
    pooled_diffs_arr = np.array(pooled_diffs, dtype=np.float64)
    per_record_paired = w._paired_t(pooled_diffs_arr)

    # ---- Wave 87 seed=42 reference ----
    w87 = json.loads((OUT_DIR / "flowmol3_n1000_sweep_wave87_q4_2026.json").read_text())
    w87_b_fg = float(w87["baseline"]["metrics"]["fg_dev"])
    w87_f_fg = float(w87["framework"]["metrics"]["fg_dev"])
    w87_diff = w87_f_fg - w87_b_fg
    w87_reos_d_z = -0.285
    w87_reos_mean_diff = -0.360

    direction_consistent = bool(per_record_paired["mean"] < 0)

    # ---- Verdict ----
    if math.isnan(per_record_paired["p_raw"]):
        verdict = "TIE"
    elif per_record_paired["p_raw"] < 0.05 / 7 and per_record_paired["mean"] < 0:
        verdict = "framework_WINS"
    elif per_record_paired["p_raw"] < 0.05 / 7 and per_record_paired["mean"] > 0:
        verdict = "REGRESSES"
    else:
        verdict = "UNDERPOWERED"

    row = {
        "wave": "235 P4",
        "model": "flowmol3",
        "cell": "R3_fg_dev",
        "metric": "reos_cum_dev_aggregate_AND_reos_flags_per_record",
        "n_total_per_arm": 500,
        "nfe": 100,
        "n_seeds_new": len(NEW_SEEDS),
        "seeds_new": ",".join(str(s) for s in NEW_SEEDS),
        "seed_42_reference_source": "flowmol3_n1000_sweep_wave87_q4_2026.json",
        "n_total_per_arm_seed_42": int(w87["n_total_per_arm"]),
        "nfe_seed_42": int(w87["nfe"]),
        "n_seeds_total": 1 + len(NEW_SEEDS),
        "n_seeds_blocked": 0,
        "block_reason": "",
        "fallback_used": "single_mol_partial_sweep_nfe100",
        "dgl_fix_attempted": True,
        "dgl_fix_succeeded": False,
        "per_seed_baseline_fg_dev": ",".join(f"{s['baseline_fg_dev']:.6f}" for s in per_seed_summaries),
        "per_seed_framework_fg_dev": ",".join(f"{s['framework_fg_dev']:.6f}" for s in per_seed_summaries),
        "per_seed_mean_diff": ",".join(f"{s['mean_diff']:+.6f}" for s in per_seed_summaries),
        "per_seed_paired_n": per_seed_paired["n"],
        "per_seed_paired_mean": per_seed_paired["mean"],
        "per_seed_paired_sd": per_seed_paired["sd"],
        "per_seed_paired_t": per_seed_paired["t_statistic"],
        "per_seed_paired_df": per_seed_paired["df"],
        "per_seed_paired_p_raw": per_seed_paired["p_raw"],
        "per_seed_paired_ci95_low": per_seed_paired["ci_95_low"],
        "per_seed_paired_ci95_high": per_seed_paired["ci_95_high"],
        "per_seed_paired_d_z": per_seed_paired["d_z"],
        "per_record_paired_n": per_record_paired["n"],
        "per_record_paired_mean": per_record_paired["mean"],
        "per_record_paired_sd": per_record_paired["sd"],
        "per_record_paired_t": per_record_paired["t_statistic"],
        "per_record_paired_df": per_record_paired["df"],
        "per_record_paired_p_raw": per_record_paired["p_raw"],
        "per_record_paired_ci95_low": per_record_paired["ci_95_low"],
        "per_record_paired_ci95_high": per_record_paired["ci_95_high"],
        "per_record_paired_d_z": per_record_paired["d_z"],
        "w87_seed_42_baseline_fg_dev": w87_b_fg,
        "w87_seed_42_framework_fg_dev": w87_f_fg,
        "w87_seed_42_mean_diff": w87_diff,
        "w87_seed_42_reos_d_z_1seed": w87_reos_d_z,
        "w87_seed_42_reos_mean_diff_1seed": w87_reos_mean_diff,
        "direction_consistent_with_1seed": direction_consistent,
        "alpha_bonferroni_7cells": 0.05 / 7,
        "bonf_sig_per_record": bool(
            not math.isnan(per_record_paired["p_raw"])
            and per_record_paired["p_raw"] < 0.05 / 7
            and per_record_paired["mean"] < 0
        ),
        "verdict": verdict,
    }

    csv_path = OUT_DIR / "wave235-p4-flowmol3-3seed.csv"
    with csv_path.open("w", newline="") as f:
        cw = csv.DictWriter(f, fieldnames=list(row.keys()))
        cw.writeheader()
        cw.writerow(row)
    print(f"Wrote {csv_path}", flush=True)

    json_path = OUT_DIR / "wave235-p4-flowmol3-3seed.json"
    json_path.write_text(json.dumps(row, indent=2, default=float), encoding="utf-8")
    print(f"Wrote {json_path}", flush=True)

    # ---- Print summary ----
    print("\n" + "=" * 78, flush=True)
    print("WAVE 235 P4 (3-seed expansion) SUMMARY", flush=True)
    print("=" * 78, flush=True)
    print(f"New seeds: {NEW_SEEDS}, nfe=100, n_per_arm=500", flush=True)
    print("Fallback: single-mol partial sweep (DGL 2.4.0 batched path broken)", flush=True)
    for s in per_seed_summaries:
        print(
            f"  Seed {s['seed']}: baseline fg_dev={s['baseline_fg_dev']:.4f} "
            f"framework fg_dev={s['framework_fg_dev']:.4f} "
            f"diff={s['mean_diff']:+.4f}",
            flush=True,
        )
    print(f"Per-seed paired-t (n_seeds={per_seed_paired['n']}, df={per_seed_paired['df']}): "
          f"mean={per_seed_paired['mean']:+.4f}, d_z={per_seed_paired['d_z']:+.3f}, "
          f"p_raw={per_seed_paired['p_raw']:.3e}", flush=True)
    print(f"Pooled per-record REOS diff (n={per_record_paired['n']}, df={per_record_paired['df']}): "
          f"mean={per_record_paired['mean']:+.4f}, d_z={per_record_paired['d_z']:+.3f}, "
          f"p_raw={per_record_paired['p_raw']:.3e}", flush=True)
    print(f"Direction consistent with 1-seed d_z=-0.285: {direction_consistent}", flush=True)
    print(f"Verdict: {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())