#!/usr/bin/env python3
"""R1 D-004B-ATTRIBUTION — init-only control vs baseline vs framework.

Consumes the per-seed HMMER ``--tblout`` files for three arms:

* **baseline** — bare-RNG family-biased draw (the R1 baseline arm).
* **init-only** — one ``solve_ode`` pass from a per-record random-simplex
  initial state (``tools/r1_d004b_attribution.py``), no restart / no blend.
* **framework** — the D-004b multi-round restart-blend arm.

and reports the per-seed paired comparisons ``init-only − baseline`` (B−A) and
``init-only − framework`` (B−C), plus the seed-level pooled t on the 3 totals.
The question: is the D-004b R1 win the *per-record random initial state* (a
single pass suffices → B ≈ C) or the *multi-round restart-blend* (B ≈ A)?

Usage::

    python tools/r1_d004b_attribution_analysis.py \
        --attrib-root /tmp/r1_d004b/attrib \
        --d004b-root verification_outputs/r1_3seed_d004b_q4_2026 \
        --out verification_outputs/r1_d004b_attribution_q4_2026 \
        --seeds 42 43 44 --n-per-seed 1000
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

from tools.r1_d004_analysis import _paired_stats


def _record_hits(tbl: Path) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    with tbl.open() as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            fields = line.split()
            if len(fields) < 3:
                continue
            head = fields[2].split("|", 1)[0]
            idx_part = head.rsplit("_seed", 1)[-1]
            try:
                counts[int(idx_part)] += 1
            except ValueError:
                continue
    return counts


def _totals(counts: dict[int, int]) -> int:
    return int(sum(counts.values()))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--attrib-root", required=True, type=Path)
    ap.add_argument("--d004b-root", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    ap.add_argument("--n-per-seed", type=int, default=1000)
    args = ap.parse_args()

    per_seed = []
    for seed in args.seeds:
        a = _record_hits(args.d004b_root / f"seed{seed}" / "baseline_hits.tbl")
        b = _record_hits(args.attrib_root / f"seed{seed}" / "init_only_hits.tbl")
        c = _record_hits(args.d004b_root / f"seed{seed}" / "framework_hits.tbl")
        idx = range(args.n_per_seed)
        a_arr = np.array([a.get(i, 0) for i in idx], dtype=float)
        b_arr = np.array([b.get(i, 0) for i in idx], dtype=float)
        c_arr = np.array([c.get(i, 0) for i in idx], dtype=float)
        ba = _paired_stats(b_arr - a_arr)
        bc = _paired_stats(b_arr - c_arr)
        ca = _paired_stats(c_arr - a_arr)
        per_seed.append({
            "seed": seed,
            "baseline_total": _totals(a),
            "init_only_total": _totals(b),
            "framework_total": _totals(c),
            "init_minus_baseline": ba,
            "init_minus_framework": bc,
            "framework_minus_baseline": ca,
        })
        print(f"seed {seed}: A(baseline)={_totals(a)} "
              f"B(init-only)={_totals(b)} C(framework)={_totals(c)} | "
              f"B-A mean={ba['mean_diff_per_record']:+.4f} d_z={ba['d_z']:+.4f} | "
              f"B-C mean={bc['mean_diff_per_record']:+.4f} d_z={bc['d_z']:+.4f}")

    # seed-level pooled t on the 3 totals
    def _pooled(vals: list[int]) -> dict[str, float]:
        arr = np.array(vals, dtype=float)
        m = float(np.mean(arr))
        sd = float(np.std(arr, ddof=1))
        t = m / (sd / math.sqrt(arr.size))
        return {
            "values": vals,
            "mean": m,
            "sd": sd,
            "t": t,
            "df": int(arr.size - 1),
            "p_two_sided": float(2 * stats.t.sf(abs(t), df=arr.size - 1)),
            "d_z": m / sd if sd > 0 else float("nan"),
        }

    ba_tot = [r["init_only_total"] - r["baseline_total"] for r in per_seed]
    bc_tot = [r["init_only_total"] - r["framework_total"] for r in per_seed]
    ca_tot = [r["framework_total"] - r["baseline_total"] for r in per_seed]

    out = {
        "kind": "r1_d004b_attribution",
        "seeds": args.seeds,
        "n_per_seed": args.n_per_seed,
        "arms": {"A": "baseline", "B": "init_only", "C": "framework"},
        "per_seed": per_seed,
        "seed_level_pooled": {
            "init_minus_baseline": _pooled(ba_tot),
            "init_minus_framework": _pooled(bc_tot),
            "framework_minus_baseline": _pooled(ca_tot),
        },
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "attribution_summary.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nseed-level pooled: B-A={_pooled(ba_tot)['mean']:+.1f} "
          f"B-C={_pooled(bc_tot)['mean']:+.1f} C-A={_pooled(ca_tot)['mean']:+.1f}")
    print(f"wrote {args.out / 'attribution_summary.json'}")


if __name__ == "__main__":
    main()
