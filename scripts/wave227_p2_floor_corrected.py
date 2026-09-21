#!/usr/bin/env python3
"""Wave 227 P2 — per-seed d_z floor CORRECT math.

Recompute d_z_floor = e^{A_g} · sqrt(2·d / n_seed) / sigma_record
for each of 16 cells in 4-arm Table B.

The "DeepSeek-flagged" incorrect Wave 226 P3 claim (per-seed d_z floor
2.21 scPerplexity / 0.53 pLDDT) appears to be a transcription error —
the Wave 226 P3 CSV (`wave226-p3-per-seed-variance-bound.csv`) and
audit doc actually report 3.7522 / 0.9051. This script reproduces
those values from the correct inputs.

Inputs (all from HEAD):
  - A_g = 0.8549457422, e^{A_g} = 2.3512468036 (wave226-p1-a-g-values.csv)
  - d = 512 (n_channels_decoder, wave226-p2-methods-paragraph.md)
  - sigma_record:
        pLDDT         = 15.17699 (wave202-p5-lineageflow-per-record.csv,
                                   LineageFlow n=574)
        scPerplexity  = 3.66097  (same)
  - per-cell d_z_observed, n_pairs (wave196-p2-4arm-paired.csv, 16 rows)

Output: verification_outputs/wave227-p2-floor-corrected.csv
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
W196 = REPO_ROOT / "verification_outputs" / "wave196-p2-4arm-paired.csv"
W226_P1 = REPO_ROOT / "verification_outputs" / "wave226-p1-a-g-values.csv"
W202 = REPO_ROOT / "verification_outputs" / "wave202-p5-lineageflow-per-record.csv"
OUT_CSV = REPO_ROOT / "verification_outputs" / "wave227-p2-floor-corrected.csv"
OUT_JSON = REPO_ROOT / "verification_outputs" / "wave227-p2-floor-corrected.json"


def _read_csv(path: Path) -> list[dict]:
    with path.open() as f:
        return list(csv.DictReader(f))


def main() -> None:
    # 1. Inputs
    a_g_rows = _read_csv(W226_P1)
    a_g = float(a_g_rows[0]["A_g"])
    exp_a_g = float(a_g_rows[0]["exp_A_g"])
    assert a_g == 0.8549457422, f"Unexpected A_g {a_g}"
    assert exp_a_g == 2.3512468036, f"Unexpected e^Ag {exp_a_g}"

    sigma_rows = _read_csv(W202)
    sigma_record = {}
    for row in sigma_rows:
        # rows are: dataset,metric,n_paired,...,sd_diff,...
        metric = row["metric"]
        sd_diff = float(row["sd_diff"])
        if metric == "plddt_mean":
            sigma_record["pLDDT"] = sd_diff
        elif metric == "sc_perplexity":
            sigma_record["scPerplexity"] = sd_diff
    assert sigma_record["pLDDT"] == 15.176988336372894
    assert sigma_record["scPerplexity"] == 3.660973910347937

    d = 512  # n_channels_decoder (wave226-p2-methods-paragraph.md)

    # 2. Per-cell recompute
    arms_4 = _read_csv(W196)
    out_rows = []
    scperp_floor_sum = 0.0
    scperp_floor_n = 0
    plddt_floor_sum = 0.0
    plddt_floor_n = 0

    for row in arms_4:
        cell = row["cell"]
        metric = row["metric"]
        n_seed = int(row["n_pairs"])
        d_z_obs = float(row["cohens_d_z"])
        verdict_per_seed = row["verdict"]  # SUPPORTED or UNDERPOWERED
        sigma_r = sigma_record[metric]

        # Correct formula per DeepSeek
        # d_z_floor = e^{A_g} · sqrt(2·d / n_seed) / sigma_record
        # Also: noise_floor_metric = e^{A_g} · sqrt(2·d / n_seed)
        noise_floor_metric = exp_a_g * math.sqrt(2.0 * d / n_seed)
        d_z_floor = noise_floor_metric / sigma_r

        abs_dz = abs(d_z_obs)

        # consistent = (|d_z_observed| < d_z_floor) AND (verdict_per_seed = UNDERPOWERED)
        below_floor = abs_dz < d_z_floor
        is_underpowered = verdict_per_seed == "UNDERPOWERED"
        consistent = below_floor and is_underpowered
        verdict_pair = f"{verdict_per_seed}+{'UNDERPOWERED' if below_floor else 'POWERED'}"

        out_rows.append({
            "cell": cell,
            "metric": metric,
            "n_seed": n_seed,
            "d_z_observed": f"{d_z_obs:.6f}",
            "d_z_abs": f"{abs_dz:.6f}",
            "sigma_record": f"{sigma_r:.3f}",
            "A_g": f"{a_g:.10f}",
            "exp_A_g": f"{exp_a_g:.4f}",
            "d": d,
            "noise_floor_metric": f"{noise_floor_metric:.4f}",
            "d_z_floor": f"{d_z_floor:.4f}",
            "verdict_per_seed": verdict_per_seed,
            "below_floor": "TRUE" if below_floor else "FALSE",
            "consistent_with_bound_corrected": "YES" if consistent else "NO",
            "verdict_pair": verdict_pair,
        })

        if metric == "scPerplexity":
            scperp_floor_sum += d_z_floor
            scperp_floor_n += 1
        else:  # pLDDT
            plddt_floor_sum += d_z_floor
            plddt_floor_n += 1

    # 3. Persist
    fieldnames = list(out_rows[0].keys())
    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    n_consistent = sum(1 for r in out_rows if r["consistent_with_bound_corrected"] == "YES")
    summary = {
        "n_cells_total": len(out_rows),
        "n_cells_floor_calculated": len(out_rows),
        "n_cells_consistent_with_bound_corrected": n_consistent,
        "scPerplexity_floor_mean": scperp_floor_sum / scperp_floor_n,
        "pLDDT_floor_mean": plddt_floor_sum / plddt_floor_n,
        "scPerplexity_floor_n30": exp_a_g * math.sqrt(2.0 * d / 30) / sigma_record["scPerplexity"],
        "scPerplexity_floor_n29": exp_a_g * math.sqrt(2.0 * d / 29) / sigma_record["scPerplexity"],
        "pLDDT_floor_n30": exp_a_g * math.sqrt(2.0 * d / 30) / sigma_record["pLDDT"],
        "pLDDT_floor_n29": exp_a_g * math.sqrt(2.0 * d / 29) / sigma_record["pLDDT"],
        "A_g": a_g,
        "exp_A_g": exp_a_g,
        "d": d,
        "sigma_record": sigma_record,
        "correct_formula": "d_z_floor = e^{A_g} · sqrt(2·d/n_seed) / sigma_record",
    }
    with OUT_JSON.open("w") as f:
        json.dump(summary, f, indent=2)

    # 4. Console report
    print(f"n_cells_total = {len(out_rows)}")
    print(f"n_cells_floor_calculated = {len(out_rows)}")
    print(f"n_cells_consistent_with_bound_corrected = {n_consistent}")
    print(f"scPerplexity_floor_mean = {scperp_floor_sum / scperp_floor_n:.4f}")
    print(f"pLDDT_floor_mean = {plddt_floor_sum / plddt_floor_n:.4f}")
    print()
    print("Per-cell:")
    for r in out_rows:
        marker = "OK" if r["consistent_with_bound_corrected"] == "YES" else "INCONSISTENT"
        print(f"  {r['cell']:35s} n={r['n_seed']:2d}  d_z_obs={r['d_z_observed']:>9s}  "
              f"d_z_floor={r['d_z_floor']:>6s}  {r['verdict_per_seed']:12s}  {marker}")


if __name__ == "__main__":
    main()
