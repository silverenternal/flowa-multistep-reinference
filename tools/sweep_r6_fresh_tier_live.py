#!/usr/bin/env python3
"""GAP-30 R6 fresh-tier live sweep (tier source = each seed's own baseline).

GAP-28 exposed that the R6 tier-aware wrapper classified records from the
**frozen** Wave 161 metrics while the live pairing uses each seed's **fresh**
baseline. For seeds 43/44 the fresh baseline is uncorrelated with the frozen
one (Pearson +0.03 / -0.01), so the "easy tier" the wrapper damps is only the
true easy tier on seed 42. This driver re-runs the framework arm with
``--tier-aware-baseline-metrics-jsonl`` pointed at the seed's OWN fresh baseline
fold, so the tier is the record's actual baseline quality.

The baseline arm is bare-RNG and seed-deterministic, so its FASTA + fold are
reused verbatim from the GAP-28 increment (``--baseline-root``); only the
framework arm is regenerated and re-folded. The regenerated baseline FASTA is
verified byte-identical to the reused one.

Per seed:
  1. Generate the framework FASTA with the fresh baseline metrics as the tier
     source (``--tier-aware-n-cap <factor>``).
  2. Verify the regenerated baseline arm is byte-identical to the reused one.
  3. Fold the framework arm on cuda:0 (``--skip-sc``).
  4. Pair the fresh framework pLDDT against the seed-matched fresh baseline
     pLDDT by ``qid``; decompose by BOTH the frozen and the fresh tier. Tier
     assignment uses the wrapper's own rule (quantile boundaries
     ``DEFAULT_TIER_QUANTILES`` computed from the reference baseline), so the
     "fresh" group is exactly the record set the wrapper actually damps.

HARD CONSTRAINT: cuda:0 ONLY (the recorded R6 directive).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from adaptive_reflow.algorithm.scheduler.tier_aware import (
    DEFAULT_TIER_QUANTILES,
    _compute_tier_boundaries,
)
from tools.sweep_r6_tier_aware_live import (
    FROZEN_BASELINE,
    GEN,
    LIN_VENV,
    OMEGAFOLD_BIN,
    OMEGAFOLD_PY,
    REPO,
    RUN_FOLD,
    _load_jsonl,
    _paired,
    _read_fasta,
    _run,
)

DEFAULT_BASELINE_ROOT = REPO / "verification_outputs/gap28-r6-faithful"


def _classify(v: float, low: float, high: float) -> str:
    if v <= low:
        return "hard"
    if v <= high:
        return "medium"
    return "easy"


def _decompose(base_map: dict, fw_map: dict, tier_ref: dict) -> dict:
    qs = sorted(set(base_map) & set(fw_map), key=lambda q: int(q[1:]))
    b = np.array([base_map[q] for q in qs], dtype=float)
    f = np.array([fw_map[q] for q in qs], dtype=float)
    out: dict = {}
    for label, key in (("frozen", tier_ref), ("fresh", base_map)):
        vals = np.array([key[q] for q in qs], dtype=float)
        low, high = _compute_tier_boundaries(vals, DEFAULT_TIER_QUANTILES)
        tiers = {}
        for t in ("hard", "medium", "easy"):
            mask = np.array([_classify(v, low, high) == t for v in vals])
            tiers[t] = _paired(b[mask], f[mask])
        out[label] = tiers
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", type=Path, required=True)
    p.add_argument("--baseline-root", type=Path, default=DEFAULT_BASELINE_ROOT)
    p.add_argument("--seeds", type=str, default="42,43,44")
    p.add_argument("--n", type=int, default=1000)
    p.add_argument("--tier-aware-n-cap", type=float, required=True)
    p.add_argument("--gpu", type=str, default="0")
    p.add_argument("--skip-generate", action="store_true")
    p.add_argument("--skip-fold", action="store_true")
    args = p.parse_args()

    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    outdir: Path = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    baseline_root: Path = args.baseline_root

    frozen = _load_jsonl(FROZEN_BASELINE)

    env = dict(os.environ)
    env["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
    env["PYTHONPATH"] = str(REPO)

    results: dict[str, dict] = {}
    for seed in seeds:
        sdir = outdir / f"seed{seed}"
        sdir.mkdir(parents=True, exist_ok=True)
        log = sdir / "sweep.log"

        bs_root = baseline_root / f"seed{seed}"
        fresh_baseline_jsonl = bs_root / "baseline/foldability/foldability.jsonl"
        fresh_baseline_fasta = bs_root / "fasta/baseline.fasta"
        if not fresh_baseline_jsonl.exists():
            print(f"[seed {seed}] missing fresh baseline {fresh_baseline_jsonl}")
            return 1

        # ---- 1. generate (both arms) with the FRESH tier source ----
        if not args.skip_generate:
            cmd = [
                str(LIN_VENV), str(GEN),
                "--outdir", str(sdir / "fasta"),
                "--n", str(args.n), "--seed", str(seed),
                "--upstream-eval-len-bias", "short",
                "--nfe", "10", "--n-rounds", "3", "--temperature", "1.0",
                "--tier-aware-n-cap", str(args.tier_aware_n_cap),
                "--tier-aware-baseline-metrics-jsonl", str(fresh_baseline_jsonl),
            ]
            if _run(cmd, env=env, log=log) != 0:
                print(f"[seed {seed}] generation failed")
                return 1

        # ---- 2. verify the regenerated baseline is byte-identical ----
        new_base = _read_fasta(sdir / "fasta" / "baseline.fasta")
        reused_base = _read_fasta(fresh_baseline_fasta)
        base_identical = list(new_base.values()) == list(reused_base.values())
        print(f"[seed {seed}] baseline byte-identical to reused fresh: {base_identical}")

        # reuse the seed-matched fresh baseline fold (deterministic)
        base_fold_dir = sdir / "baseline" / "foldability"
        base_fold_dir.mkdir(parents=True, exist_ok=True)
        if not (base_fold_dir / "foldability.jsonl").exists():
            shutil.copy2(fresh_baseline_jsonl, base_fold_dir / "foldability.jsonl")

        # ---- 3. fold the framework arm ----
        fw_fold_dir = sdir / "framework" / "foldability"
        if not args.skip_fold and not (fw_fold_dir / "foldability.jsonl").exists():
            cmd = [
                str(OMEGAFOLD_PY), str(RUN_FOLD),
                "--fasta", str(sdir / "fasta" / "framework.fasta"),
                "--outdir", str(fw_fold_dir),
                "--omegafold-bin", OMEGAFOLD_BIN,
                "--fold-gpus", str(args.gpu), "--sc-gpus", str(args.gpu),
                "--max-seqs", str(args.n),
                "--skip-sc", "--no-plots", "--log-every", "60",
            ]
            if _run(cmd, env=env, log=log) != 0:
                print(f"[seed {seed}] fold failed")
                return 1

        base_map = _load_jsonl(base_fold_dir / "foldability.jsonl")
        fw_map = _load_jsonl(fw_fold_dir / "foldability.jsonl")
        common = sorted(set(base_map) & set(fw_map), key=lambda q: int(q[1:]))
        res = _paired(
            np.array([base_map[q] for q in common], dtype=float),
            np.array([fw_map[q] for q in common], dtype=float),
        )
        res["seed"] = seed
        res["baseline_byte_identical"] = bool(base_identical)
        res["baseline_source"] = "reused seed-matched fresh fold (GAP-28)"
        res["tier_source"] = "fresh (this seed's own baseline fold)"
        res["tier_aware_n_cap"] = float(args.tier_aware_n_cap)
        res["n_framework_folded"] = int(len(fw_map))
        res["per_tier"] = _decompose(base_map, fw_map, frozen)
        results[str(seed)] = res
        print(f"[seed {seed}] d_z={res['cohens_d_z']:+.4f} "
              f"mean_diff={res['mean_diff']:+.4f} n={res['n']}")

    # ---- pooled (tier assignment is per-seed quantile, matching the wrapper) ----
    all_b, all_f = [], []
    frozen_pool = {t: ([], []) for t in ("hard", "medium", "easy")}
    fresh_pool = {t: ([], []) for t in ("hard", "medium", "easy")}
    for seed in seeds:
        sdir = outdir / f"seed{seed}"
        base_map = _load_jsonl(sdir / "baseline" / "foldability" / "foldability.jsonl")
        fw_map = _load_jsonl(sdir / "framework" / "foldability" / "foldability.jsonl")
        qs = sorted(set(base_map) & set(fw_map), key=lambda x: int(x[1:]))
        frozen_vals = np.array([frozen[q] for q in qs], dtype=float)
        fresh_vals = np.array([base_map[q] for q in qs], dtype=float)
        fz_low, fz_high = _compute_tier_boundaries(frozen_vals, DEFAULT_TIER_QUANTILES)
        fr_low, fr_high = _compute_tier_boundaries(fresh_vals, DEFAULT_TIER_QUANTILES)
        for i, q in enumerate(qs):
            all_b.append(base_map[q])
            all_f.append(fw_map[q])
            ft = _classify(frozen_vals[i], fz_low, fz_high)
            rt = _classify(fresh_vals[i], fr_low, fr_high)
            frozen_pool[ft][0].append(base_map[q])
            frozen_pool[ft][1].append(fw_map[q])
            fresh_pool[rt][0].append(base_map[q])
            fresh_pool[rt][1].append(fw_map[q])
    pooled = _paired(np.array(all_b), np.array(all_f))
    per_tier = {
        label: {
            t: _paired(np.array(v[0]), np.array(v[1]))
            for t, v in pool.items()
        }
        for label, pool in (("frozen", frozen_pool), ("fresh", fresh_pool))
    }

    summary = {
        "kind": "gap30_r6_fresh_tier_live",
        "seeds": seeds,
        "n_per_seed": int(args.n),
        "tier_aware_n_cap": float(args.tier_aware_n_cap),
        "gpu": str(args.gpu),
        "baseline_root": (
            str(baseline_root.resolve().relative_to(REPO))
            if REPO in baseline_root.resolve().parents
            else str(baseline_root)
        ),
        "tier_source": "fresh (each seed's own baseline fold)",
        "per_seed": results,
        "pooled": pooled,
        "pooled_per_tier": per_tier,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (outdir / "sweep_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\npooled d_z = {pooled['cohens_d_z']:+.4f} "
          f"(n={pooled['n']}, mean_diff={pooled['mean_diff']:+.4f})")
    print(f"wrote {outdir / 'sweep_summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
