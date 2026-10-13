#!/usr/bin/env python3
"""GAP-28 pooled aggregation over independently-run per-seed R6 faithful sweeps.

The faithful R6 sweep was executed as three concurrent single-seed
invocations of ``tools/sweep_r6_tier_aware_live.py`` (seeds are independent;
see ``verification_outputs/gap28-r6-faithful/METADATA.json``). Each invocation
wrote its own ``sweep_summary.json`` to the shared outdir, so the last writer
wins and the pooled block is not reliable. This tool re-derives the pooled
per-seed + pooled statistics from the per-seed foldability JSONLs, using the
*identical* paired math as the driver (``_paired`` / ``_load_jsonl`` /
``_read_fasta`` imported from ``tools.sweep_r6_tier_aware_live``).

Usage:
    .venvs/lineageflow_venv/bin/python tools/gap28_aggregate.py \
        --outdir verification_outputs/gap28-r6-faithful \
        --seeds 42,43,44
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from tools.sweep_r6_tier_aware_live import (
    FROZEN_BASELINE,
    FROZEN_BASELINE_FASTA,
    REPO,
    TIER_HIGH,
    TIER_LOW,
    _load_jsonl,
    _paired,
    _read_fasta,
)


def _seed_block(outdir: Path, seed: int) -> dict:
    sdir = outdir / f"seed{seed}"
    base_map = _load_jsonl(sdir / "baseline" / "foldability" / "foldability.jsonl")
    fw_map = _load_jsonl(sdir / "framework" / "foldability" / "foldability.jsonl")
    common = sorted(set(base_map) & set(fw_map), key=lambda q: int(q[1:]))
    b = np.array([base_map[q] for q in common], dtype=float)
    f = np.array([fw_map[q] for q in common], dtype=float)
    res = _paired(b, f)
    res["seed"] = seed
    # baseline byte-identity vs the frozen Wave 161 baseline
    new_base = _read_fasta(sdir / "fasta" / "baseline.fasta")
    frozen_base = _read_fasta(FROZEN_BASELINE_FASTA)
    res["baseline_byte_identical"] = bool(
        list(frozen_base.values()) == list(new_base.values())
    )
    res["baseline_source"] = "fresh seed-matched fold"
    res["n_framework_folded"] = int(len(fw_map))
    res["n_baseline_folded"] = int(len(base_map))
    res["n_common"] = int(len(common))
    tiers = {}
    for label, mask in (
        ("hard", b <= TIER_LOW),
        ("medium", (b > TIER_LOW) & (b <= TIER_HIGH)),
        ("easy", b > TIER_HIGH),
    ):
        tiers[label] = _paired(b[mask], f[mask])
    res["per_tier"] = tiers
    return res, common, base_map, fw_map


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", type=Path,
                   default=REPO / "verification_outputs/gap28-r6-faithful")
    p.add_argument("--seeds", type=str, default="42,43,44")
    p.add_argument("--tier-aware-n-cap", type=float, default=1.5)
    p.add_argument("--acceptance-bar", type=float, default=0.2235)
    p.add_argument("--as-designed-dz", type=float, default=0.1466)
    args = p.parse_args()

    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    outdir: Path = args.outdir

    per_seed: dict[str, dict] = {}
    all_b: list[float] = []
    all_f: list[float] = []
    for seed in seeds:
        res, common, base_map, fw_map = _seed_block(outdir, seed)
        per_seed[str(seed)] = res
        all_b.extend(base_map[q] for q in common)
        all_f.extend(fw_map[q] for q in common)
        print(f"[seed {seed}] n={res['n']} mean_diff={res['mean_diff']:+.4f} "
              f"d_z={res['cohens_d_z']:+.4f} "
              f"baseline_byte_identical={res['baseline_byte_identical']}")

    pooled = _paired(np.array(all_b), np.array(all_f))
    summary = {
        "kind": "gap28_r6_tier_aware_live_faithful_pooled",
        "seeds": seeds,
        "n_per_seed": per_seed[str(seeds[0])]["n"],
        "tier_aware_n_cap": float(args.tier_aware_n_cap),
        "gpu": "0",
        "pair_with": "fresh",
        "baseline_source": str(FROZEN_BASELINE.relative_to(REPO)),
        "acceptance_bar_pooled_dz": float(args.acceptance_bar),
        "as_designed_reference_pooled_dz": float(args.as_designed_dz),
        "acceptance_met": bool(pooled["cohens_d_z"] >= args.acceptance_bar),
        "per_seed": per_seed,
        "pooled": pooled,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    out = outdir / "sweep_summary.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"\npooled d_z = {pooled['cohens_d_z']:+.4f} "
          f"(n={pooled['n']}, mean_diff={pooled['mean_diff']:+.4f})")
    print(f"acceptance (>= {args.acceptance_bar}): {summary['acceptance_met']}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
