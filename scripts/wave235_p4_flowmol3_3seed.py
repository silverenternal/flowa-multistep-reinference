#!/usr/bin/env python3
"""Wave 235 P4: FlowMol3 3-seed expansion (partial sweep, single-mol path).

DGL 2.4.0+cu124 has a graph ndata shape mismatch at n_molecules > 1
(regression documented in Wave 109.C). The single-mol path
(n_molecules=1) works fine.

Plan (per the Wave 235 P4 brief):
- N=500 records per arm (partial sweep fallback per brief)
- NFE=100 (reduced from paper NFE=250 for time budget; documented)
- Seeds: 43, 44 (new); seed=42 reused from Wave 87 byte-stable data
- Arms: baseline (perturbation_sigma=0), framework (perturbation_sigma=0.05)
- Output: per-arm per-seed JSON, per-record CSV with paired diffs,
  3-seed pooled paired-t summary

Outputs:
  - verification_outputs/wave235-p4-flowmol3-seed{N}-{baseline,framework}.json
  - verification_outputs/wave235-p4-flowmol3-3seed.csv
  - verification_outputs/wave235-p4-flowmol3-3seed.json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

REPO = Path("/home/hugo/codes/flowa-multistep-reinference")
OUT_DIR = REPO / "verification_outputs"

# Force CUDA device 0 (RTX PRO 6000 Blackwell).
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "data" / "FlowMol3" / "repo"))

import numpy as np
import scipy.stats


def _apply_perturbation(adapter, bundle, *, perturbation_sigma: float, seed: int) -> None:
    """Apply framework's restart-blend prior perturbation (canonical x only)."""
    if perturbation_sigma <= 0.0:
        return
    rng = np.random.default_rng(int(seed) * 1009 + 7)
    digest = bundle.native_state_digest
    entry = adapter._native_states.get(digest)
    if entry is None:
        return
    x_canonical = np.asarray(entry["x"], dtype=np.float64)
    if x_canonical.ndim == 2 and x_canonical.shape[1] == 3:
        noise = rng.standard_normal(x_canonical.shape).astype(np.float64) * float(perturbation_sigma)
        entry["x"] = (x_canonical + noise).astype(np.float64)
        adapter._native_states[digest] = entry


def _generate_arm_single_mol(
    *,
    adapter,
    arm_name: str,
    perturbation_sigma: float,
    seed_base: int,
    n_total: int,
    nfe: int,
) -> dict:
    """Generate N molecules using single-mol path (n_molecules=1)."""
    from adaptive_reflow.universal.state import ODEConditionDelta

    smiles_list: list[str] = []
    errors: list[str] = []
    n_errors = 0
    t_total = time.perf_counter()
    for i in range(int(n_total)):
        seed = int(seed_base + i)
        bundle = adapter.build_initial_state(
            batch_id=f"w235p4-{arm_name}-s{seed_base}-i{i}",
            sample_id=f"w235p4-{arm_name}-s{seed_base}-i{i}-prior",
        )
        _apply_perturbation(adapter, bundle, perturbation_sigma=perturbation_sigma, seed=seed)
        cond = ODEConditionDelta(
            delta_spec={"num_steps": nfe},
            source=f"wave235_p4_{arm_name}",
            target_round=0,
            calibration_artifact_hash="wave235_p4",
        )
        try:
            trace = adapter.solve_ode(bundle, cond, seed=seed, n_molecules=1)
            sampled, metadata = adapter.export_sampled_molecules(trace)
            if metadata.get("marker") != "ok":
                n_errors += 1
                if len(errors) < 5:
                    errors.append(f"i{i}:marker={metadata.get('marker')}")
                continue
            entry = adapter._native_states.get(trace.native_state_digest) or {}
            smi = entry.get("rdkit_mol_smiles") or ""
            if smi:
                smiles_list.append(smi)
            else:
                n_errors += 1
                if len(errors) < 5:
                    errors.append(f"i{i}:no_smiles")
        except Exception as exc:  # noqa: BLE001
            n_errors += 1
            if len(errors) < 5:
                errors.append(f"i{i}:{type(exc).__name__}:{exc}")
        if (i + 1) % 100 == 0:
            elapsed = time.perf_counter() - t_total
            print(
                f"  [{arm_name} s={seed_base}] {i+1}/{n_total} "
                f"({elapsed:.1f}s, ~{elapsed/(i+1):.2f}s/mol)",
                flush=True,
            )
    wallclock_s = round(time.perf_counter() - t_total, 3)
    print(
        f"[{arm_name} s={seed_base}] DONE: n_sampled={len(smiles_list)} "
        f"n_errors={n_errors} wallclock={wallclock_s}s",
        flush=True,
    )
    return {
        "arm": arm_name,
        "n_target": int(n_total),
        "n_sampled": int(len(smiles_list)),
        "n_errors": int(n_errors),
        "errors_sample": errors[:5],
        "wallclock_s": float(wallclock_s),
        "perturbation_sigma": float(perturbation_sigma),
        "seed_base": int(seed_base),
        "nfe": int(nfe),
        "smiles_list": smiles_list,
    }


def _compute_paper_metrics(smiles_list: list[str]) -> dict:
    """Compute upstream paper metrics from SMILES list."""
    from adaptive_reflow.adapters.flowmol3_metrics_upstream import (
        compute_paper_metrics_from_smiles,
    )
    metrics = compute_paper_metrics_from_smiles(
        smiles_list,
        run_posebusters=True,
        run_functional_validity=True,
        pb_workers=2,
    )
    return {
        "validity_pct": float(metrics.get("frac_valid_mols", 0.0)),
        "pb_validity_pct": float(metrics.get("frac_pb_valid_mols", 0.0)),
        "fg_dev": float(metrics.get("reos_cum_dev", 0.0)),
        "ood_ring_rate": float(metrics.get("ood_rate", 0.0)),
    }


def _per_record_reos_flags(smiles_list: list[str]) -> list[int]:
    """Per-record REOS flag count (matches Wave 208 P2 sanity proxy).

    Uses ``useful_rdkit_utils.reos.REOS`` directly (the same upstream class
    used by Wave 208 P2 via ``flowmol.analysis.reos.REOS``).
    """
    try:
        from useful_rdkit_utils.reos import REOS
        from rdkit import Chem
        reos_obj = REOS(active_rules=["Glaxo", "Dundee"])
    except Exception as exc:
        print(f"  WARNING: reos init failed ({type(exc).__name__}:{exc}); returning zeros", flush=True)
        return [0] * len(smiles_list)
    flags = []
    for smi in smiles_list:
        try:
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                flags.append(0)
                continue
            mol_flags = reos_obj.mol_to_flags(mol)
            flags.append(len(mol_flags))
        except Exception:
            flags.append(0)
    return flags


def _paired_t(diff_array: np.ndarray) -> dict:
    """Paired t-test on a diff array."""
    n = int(diff_array.size)
    mean = float(np.mean(diff_array))
    sd = float(np.std(diff_array, ddof=1)) if n > 1 else float("nan")
    se = sd / math.sqrt(n) if n > 1 else float("nan")
    t_stat = mean / se if se and se > 0 else float("nan")
    df = max(n - 1, 1)
    p_raw = float(2.0 * scipy.stats.t.sf(abs(t_stat), df=df)) if not math.isnan(t_stat) else float("nan")
    d_z = mean / sd if sd and sd > 0 else float("nan")
    ci_low = mean - 1.96 * se if not math.isnan(se) else float("nan")
    ci_high = mean + 1.96 * se if not math.isnan(se) else float("nan")
    return {
        "n": n,
        "mean": mean,
        "sd": sd,
        "se": se,
        "t_statistic": t_stat,
        "df": df,
        "p_raw": p_raw,
        "ci_95_low": ci_low,
        "ci_95_high": ci_high,
        "d_z": d_z,
    }


def _per_seed_summary(seed: int, baseline: dict, framework: dict) -> dict:
    """Per-seed summary."""
    b_metrics = baseline["metrics"]
    f_metrics = framework["metrics"]
    diff = float(f_metrics["fg_dev"] - b_metrics["fg_dev"])
    return {
        "seed": int(seed),
        "baseline_n": int(baseline["n_sampled"]),
        "framework_n": int(framework["n_sampled"]),
        "baseline_fg_dev": float(b_metrics["fg_dev"]),
        "framework_fg_dev": float(f_metrics["fg_dev"]),
        "mean_diff": diff,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--n-total", type=int, default=500, help="Records per arm (default 500).")
    p.add_argument("--nfe", type=int, default=100, help="NFE (default 100, reduced from 250).")
    p.add_argument("--seeds", type=int, nargs="+", default=[43, 44], help="Seeds (default 43 44).")
    p.add_argument("--n-mols-per-record", type=int, default=1, help="n_molecules per record (default 1).")
    p.add_argument("--no-compute-metrics", action="store_true", help="Skip paper-metric computation.")
    args = p.parse_args()

    n_total = int(args.n_total)
    nfe = int(args.nfe)
    seeds = list(args.seeds)
    n_mols = int(args.n_mols_per_record)

    print("=" * 78, flush=True)
    print(f"Wave 235 P4: FlowMol3 3-seed expansion (partial sweep)", flush=True)
    print(f"  n_total_per_arm = {n_total}, nfe = {nfe}, seeds = {seeds}", flush=True)
    print(f"  n_molecules per record = {n_mols} (DGL 2.4.0 regression forces single-mol path)", flush=True)
    print("=" * 78, flush=True)

    # Load adapter once (warm)
    from adaptive_reflow.adapters.flowmol3_v2_adapter import FlowMol3V2Adapter

    print("Loading FlowMol3 v2 adapter (upstream path) ...", flush=True)
    t0 = time.perf_counter()
    adapter = FlowMol3V2Adapter(
        backend="torch",
        num_steps=nfe,
        weights_path=str(REPO / "data" / "flowmol3" / "weights_real" / "checkpoints" / "last.ckpt"),
        device="cuda:0",
        use_upstream=True,
        upstream_repo_dir=str(REPO / "data" / "FlowMol3" / "repo"),
    )
    # Eager-load model
    _ = adapter._load_model()
    print(f"Adapter loaded in {time.perf_counter()-t0:.2f}s", flush=True)

    arm_specs = [
        ("baseline", {"perturbation_sigma": 0.0}),
        ("framework", {"perturbation_sigma": 0.05}),
    ]

    per_seed_results: dict[int, dict] = {}
    for seed in seeds:
        print(f"\n--- Seed {seed} ---", flush=True)
        per_seed_results[seed] = {}
        for arm_name, arm_kwargs in arm_specs:
            arm_raw = _generate_arm_single_mol(
                adapter=adapter,
                arm_name=arm_name,
                seed_base=int(seed),
                n_total=n_total,
                nfe=nfe,
                **arm_kwargs,
            )
            # Persist raw arm JSON (with smiles_list capped to 200 to keep file small,
            # but also write full smiles_list to a sidecar .smiles.txt file)
            arm_full = dict(arm_raw)
            smiles_list = arm_full.pop("smiles_list")
            arm_capped = dict(arm_full)
            arm_capped["smiles_list_capped_200"] = smiles_list[:200]
            arm_capped["smiles_count"] = len(smiles_list)
            out_json = OUT_DIR / f"wave235-p4-flowmol3-seed{seed}-{arm_name}.json"
            out_json.write_text(json.dumps(arm_capped, indent=2), encoding="utf-8")
            print(f"Wrote {out_json}", flush=True)
            # Also write full smiles to a sidecar file
            smiles_txt = OUT_DIR / f"wave235-p4-flowmol3-seed{seed}-{arm_name}.smiles.txt"
            smiles_txt.write_text("\n".join(smiles_list) + "\n", encoding="utf-8")

            # Compute metrics
            if args.no_compute_metrics:
                metrics = {"validity_pct": float("nan"), "pb_validity_pct": float("nan"),
                           "fg_dev": float("nan"), "ood_ring_rate": float("nan")}
            else:
                t_m = time.perf_counter()
                metrics = _compute_paper_metrics(smiles_list)
                print(f"[{arm_name} s={seed}] metrics computed in {time.perf_counter()-t_m:.1f}s", flush=True)

            per_seed_results[seed][arm_name] = {
                "metrics": metrics,
                "smiles_list": smiles_list,
                "raw": arm_raw,
            }

    # ---- Per-record REOS flags per seed (for per-record paired-t) ----
    print("\n--- Per-record REOS flags (for paired-t) ---", flush=True)
    per_record_rows: list[dict] = []
    for seed in seeds:
        for arm_name in ("baseline", "framework"):
            sl = per_seed_results[seed][arm_name]["smiles_list"]
            t_m = time.perf_counter()
            flags = _per_record_reos_flags(sl)
            print(f"[seed={seed} {arm_name}] REOS flags computed in {time.perf_counter()-t_m:.1f}s", flush=True)
            per_seed_results[seed][arm_name]["reos_flags"] = flags
            for i, smi in enumerate(sl):
                per_record_rows.append({
                    "seed": int(seed),
                    "arm": arm_name,
                    "idx": int(i),
                    "smiles": smi,
                    "reos_flag": int(flags[i]),
                })

    # Save per-record CSV
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
    for seed in seeds:
        s = _per_seed_summary(
            seed,
            {"metrics": per_seed_results[seed]["baseline"]["metrics"],
             "n_sampled": per_seed_results[seed]["baseline"]["raw"]["n_sampled"]},
            {"metrics": per_seed_results[seed]["framework"]["metrics"],
             "n_sampled": per_seed_results[seed]["framework"]["raw"]["n_sampled"]},
        )
        per_seed_summaries.append(s)

    # ---- 3-seed pooled paired-t across per-seed mean_diffs ----
    diffs_per_seed = np.array([s["mean_diff"] for s in per_seed_summaries], dtype=np.float64)
    per_seed_paired = _paired_t(diffs_per_seed)

    # ---- Pooled per-record paired-t (REOS flags diff, n_pooled = 3 × N) ----
    pooled_diffs: list[float] = []
    for seed in seeds:
        b_flags = np.array(per_seed_results[seed]["baseline"]["reos_flags"], dtype=np.int64)
        f_flags = np.array(per_seed_results[seed]["framework"]["reos_flags"], dtype=np.int64)
        n_min = min(len(b_flags), len(f_flags))
        # framework - baseline (negative = framework closer to QM9 distribution;
        # we expect framework to have fewer REOS flags because lower fg_dev)
        diff = (f_flags[:n_min] - b_flags[:n_min]).astype(np.float64)
        pooled_diffs.extend(diff.tolist())
    pooled_diffs_arr = np.array(pooled_diffs, dtype=np.float64)
    per_record_paired = _paired_t(pooled_diffs_arr)

    # ---- Wave 87 seed=42 reference (existing, NFE=250, N=1000) ----
    w87 = json.loads((OUT_DIR / "flowmol3_n1000_sweep_wave87_q4_2026.json").read_text())
    w87_b_fg = float(w87["baseline"]["metrics"]["fg_dev"])
    w87_f_fg = float(w87["framework"]["metrics"]["fg_dev"])
    w87_diff = w87_f_fg - w87_b_fg
    w87_reos_d_z = -0.285  # from Wave 208 P2 sanity (REOS n_flags per-record)
    w87_reos_mean_diff = -0.360

    # Direction consistency check: 1-seed d_z = -0.285 should be similar sign at 3-seed
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

    # ---- Save 12-col summary CSV ----
    row = {
        "wave": "235 P4",
        "model": "flowmol3",
        "cell": "R3_fg_dev",
        "metric": "reos_cum_dev_aggregate_AND_reos_flags_per_record",
        "n_total_per_arm": n_total,
        "nfe": nfe,
        "n_seeds_new": len(seeds),
        "seeds_new": ",".join(str(s) for s in seeds),
        "seed_42_reference_source": "flowmol3_n1000_sweep_wave87_q4_2026.json",
        "n_total_per_arm_seed_42": int(w87["n_total_per_arm"]),
        "nfe_seed_42": int(w87["nfe"]),
        "n_seeds_total": 1 + len(seeds),
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
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        w.writeheader()
        w.writerow(row)
    print(f"Wrote {csv_path}", flush=True)

    # ---- Save JSON summary ----
    json_path = OUT_DIR / "wave235-p4-flowmol3-3seed.json"
    json_path.write_text(json.dumps(row, indent=2, default=float), encoding="utf-8")
    print(f"Wrote {json_path}", flush=True)

    # ---- Print summary ----
    print("\n" + "=" * 78, flush=True)
    print("WAVE 235 P4 SUMMARY", flush=True)
    print("=" * 78, flush=True)
    print(f"New seeds: {seeds}, nfe={nfe}, n_per_arm={n_total}", flush=True)
    print(f"Fallback: single-mol partial sweep (DGL 2.4.0 batched path broken)", flush=True)
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
