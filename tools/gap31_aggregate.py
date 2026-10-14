#!/usr/bin/env python3
"""GAP-31 R6 live-uplift aggregation.

Three live, non-counterfactual R6 measurements built on the GAP-28/30 sweeps:

  (a) the live **scPerplexity** axis: pair the framework arm's ESM-IF
      self-consistency perplexity against the seed-matched baseline arm's, by
      ``qid`` (lower scPerp = better, so a NEGATIVE paired ``d_z`` = framework
      WINS). Decomposed by the seed's own fresh-quantile difficulty tier.
  (b) the live **uniform -> as-designed** pLDDT tier-aware delta: the honest
      "before" (factor 1.0, no tier manipulation) vs "after" (factor 0.5).
  (c) the live **hard / medium tier** pLDDT anchors (arm-independent, since the
      wrapper touches only the easy tier).

Reads only committed/reused artifacts; writes ``gap31_summary.json``.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from adaptive_reflow.algorithm.scheduler.tier_aware import (
    DEFAULT_TIER_QUANTILES,
    _compute_tier_boundaries,
)
from tools.sweep_r6_tier_aware_live import REPO, _paired

GAP28 = REPO / "verification_outputs/gap28-r6-faithful"
GAP30_ASD = REPO / "verification_outputs/gap30-r6-fresh-tier/as-designed"
GAP31 = REPO / "verification_outputs/gap31-r6-live-uplift"


def _classify(v: float, low: float, high: float) -> str:
    if v <= low:
        return "hard"
    if v <= high:
        return "medium"
    return "easy"


def _load_plddt(path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        out[str(r["qid"])] = float(r["plddt_mean"])
    return out


def _load_sc(path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if "sc_perplexity" in r:
            out[str(r["qid"])] = float(r["sc_perplexity"])
    return out


def _tier_decompose(base: np.ndarray, fw: np.ndarray, tier_vals: np.ndarray) -> dict:
    low, high = _compute_tier_boundaries(tier_vals, DEFAULT_TIER_QUANTILES)
    out = {}
    for t in ("hard", "medium", "easy"):
        mask = np.array([_classify(v, low, high) == t for v in tier_vals])
        out[t] = _paired(base[mask], fw[mask])
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", type=Path, default=GAP31)
    p.add_argument("--seeds", type=str, default="42,43,44")
    args = p.parse_args()
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]

    # ---- (a) live scPerplexity ----
    sc_all_b, sc_all_f = [], []
    sc_tier_pool = {t: ([], []) for t in ("hard", "medium", "easy")}
    sc_per_seed: dict[str, dict] = {}
    for s in seeds:
        b = _load_sc(GAP31 / f"scperp/baseline/seed{s}/self_consistency.jsonl")
        f = _load_sc(GAP31 / f"scperp/as-designed/seed{s}/self_consistency.jsonl")
        base_plddt = _load_plddt(GAP28 / f"seed{s}/baseline/foldability/foldability.jsonl")
        qs = sorted(set(b) & set(f), key=lambda q: int(q[1:]))
        bv = np.array([b[q] for q in qs], dtype=float)
        fv = np.array([f[q] for q in qs], dtype=float)
        tv = np.array([base_plddt[q] for q in qs], dtype=float)
        res = _paired(bv, fv)
        res["seed"] = s
        res["per_tier"] = _tier_decompose(bv, fv, tv)
        sc_per_seed[str(s)] = res
        sc_all_b.extend(bv.tolist())
        sc_all_f.extend(fv.tolist())
        low, high = _compute_tier_boundaries(tv, DEFAULT_TIER_QUANTILES)
        for i, _q in enumerate(qs):
            t = _classify(tv[i], low, high)
            sc_tier_pool[t][0].append(bv[i])
            sc_tier_pool[t][1].append(fv[i])
    sc_pooled = _paired(np.array(sc_all_b), np.array(sc_all_f))
    sc_tier_pooled = {
        t: _paired(np.array(v[0]), np.array(v[1])) for t, v in sc_tier_pool.items()
    }

    # ---- (b) live uniform -> as-designed pLDDT ----
    plddt_per_seed: dict[str, dict] = {}
    uni_all, asd_all = [], []
    for s in seeds:
        base = _load_plddt(GAP28 / f"seed{s}/baseline/foldability/foldability.jsonl")
        uni = _load_plddt(GAP31 / f"uniform/seed{s}/framework/foldability/foldability.jsonl")
        asd = _load_plddt(GAP30_ASD / f"seed{s}/framework/foldability/foldability.jsonl")
        qs = sorted(set(base) & set(uni) & set(asd), key=lambda q: int(q[1:]))
        bv = np.array([base[q] for q in qs], dtype=float)
        uv = np.array([uni[q] for q in qs], dtype=float)
        av = np.array([asd[q] for q in qs], dtype=float)
        res = {
            "seed": s,
            "n": len(qs),
            "uniform_vs_baseline": _paired(bv, uv),
            "as_designed_vs_baseline": _paired(bv, av),
            "as_designed_vs_uniform": _paired(uv, av),
        }
        plddt_per_seed[str(s)] = res
        uni_all.extend((uv - bv).tolist())
        asd_all.extend((av - bv).tolist())

    summary = {
        "kind": "gap31_r6_live_uplift",
        "seeds": seeds,
        "scperplexity_live": {
            "note": "ESM-IF self-consistency perplexity, baseline vs as-designed "
                    "framework, paired by qid; NEGATIVE d_z = framework WINS "
                    "(lower scPerp is better)",
            "per_seed": sc_per_seed,
            "pooled": sc_pooled,
            "pooled_per_tier": sc_tier_pooled,
        },
        "plddt_live_uniform_to_as_designed": {
            "note": "uniform (factor 1.0, no tier manipulation) vs as-designed "
                    "(factor 0.5); both paired against the seed-matched baseline",
            "per_seed": plddt_per_seed,
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    out = args.outdir / "gap31_summary.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"scPerp pooled: n={sc_pooled['n']} mean_diff={sc_pooled['mean_diff']:+.4f} "
          f"d_z={sc_pooled['cohens_d_z']:+.4f}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
