#!/usr/bin/env python3
"""R1 (LineageFlow HMMER foldability) 3-seed paired-t + DerSimonian-Laird meta.

R1-REMEASURE-D004 driver. Consumes the per-seed HMMER ``--tblout`` files
produced by :mod:`tools.gen_lineageflow_n1000_fastas` + ``hmmscan`` and emits
the canonical per-seed paired-t + 3-seed random-effects meta summary used by
the R1 headline.

Inputs (per seed ``S`` under ``--root``)::

    seed<S>/baseline_hits.tbl
    seed<S>/framework_hits.tbl

A "hit" is any non-comment ``--tblout`` line. Per-record hit counts are keyed
by the ``seed<i>`` field embedded in the query name
(``<arm>_seed<i>|family=PF...``); records with zero hits are counted as 0.
The per-record paired diff is ``framework_hits_i - baseline_hits_i``.

Outputs ``--out/summary.json`` mirroring the pre-D-004 R1 3-seed schema so the
two runs are directly comparable. Statistics only; no plotting.

Methodology (unchanged from the canonical R1 3-seed run so the comparison is
apples-to-apples):

* per-seed paired-t on the ``n`` per-record diffs (``df = n - 1``);
* within-seed ``d_z = mean_diff / sd_diff`` with variance
  ``v_i = 1/n + d_z^2 / (2n)`` (Hedges small-sample form);
* seed-level pooled-t over the ``k`` total-diff values;
* DerSimonian-Laird random-effects meta on the per-seed ``d_z`` values.

Usage::

    python tools/r1_d004_analysis.py --root /tmp/r1_d004/n1000 \
        --out /tmp/r1_d004/n1000 --seeds 42 43 44 --n-per-seed 1000
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

Z_CRIT_95 = 1.959963984540054
ALPHA_RLEVEL_K7 = 0.05 / 7
ALPHA_RLEVEL_K16 = 0.05 / 16


def _record_hits(tbl: Path) -> dict[int, int]:
    """Per-record HMMER hit counts keyed by the ``seed<i>`` query index."""
    counts: dict[int, int] = defaultdict(int)
    with tbl.open() as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            if not line.strip():
                continue
            fields = line.split()
            if len(fields) < 3:
                continue
            query = fields[2]
            # query name shape: ``<arm>_seed<i>|family=PF...``
            head = query.split("|", 1)[0]
            idx_part = head.rsplit("_seed", 1)[-1]
            try:
                idx = int(idx_part)
            except ValueError:
                continue
            counts[idx] += 1
    return counts


def _paired_stats(diffs: np.ndarray) -> dict[str, float]:
    n = int(diffs.size)
    df = n - 1
    mean = float(np.mean(diffs))
    sd = float(np.std(diffs, ddof=1))
    d_z = mean / sd if sd > 0 else float("nan")
    t = mean / (sd / math.sqrt(n)) if sd > 0 else float("nan")
    p_raw = float(2 * stats.t.sf(abs(t), df=df)) if not math.isnan(t) else float("nan")
    dz_var = 1.0 / n + d_z**2 / (2.0 * n)
    return {
        "n_records": n,
        "mean_diff_per_record": mean,
        "sd_diff": sd,
        "t": t,
        "df": df,
        "p_raw": p_raw,
        "d_z": d_z,
        "dz_var": dz_var,
    }


def dersimonian_laird_d_z(
    per_seed_d_z: list[float], per_seed_var_d_z: list[float]
) -> dict[str, float]:
    """DerSimonian-Laird random-effects meta-analysis of per-seed d_z values."""
    di = np.array(per_seed_d_z, dtype=float)
    vi = np.array(per_seed_var_d_z, dtype=float)
    k = len(di)
    w_fe = 1.0 / vi
    d_fe = float(np.sum(w_fe * di) / np.sum(w_fe))
    Q = float(np.sum(w_fe * (di - d_fe) ** 2))
    c = float(np.sum(w_fe) - np.sum(w_fe**2) / np.sum(w_fe))
    tau2 = max(0.0, (Q - (k - 1)) / c)
    w_re = 1.0 / (vi + tau2)
    d_re = float(np.sum(w_re * di) / np.sum(w_re))
    se_re = math.sqrt(float(1.0 / np.sum(w_re)))
    z_re = d_re / se_re
    p_re = float(2 * (1 - stats.norm.cdf(abs(z_re))))
    I2 = max(0.0, (Q - (k - 1)) / Q) * 100 if Q > 0 else 0.0
    return {
        "k": k,
        "Q": Q,
        "C": c,
        "tau2": tau2,
        "I2_pct": I2,
        "d_pooled": d_re,
        "se_pooled": se_re,
        "z": z_re,
        "p_two_sided": p_re,
        "ci_95_lower": d_re - Z_CRIT_95 * se_re,
        "ci_95_upper": d_re + Z_CRIT_95 * se_re,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    ap.add_argument("--n-per-seed", type=int, default=1000)
    args = ap.parse_args()

    per_seed: list[dict[str, Any]] = []
    total_diffs: list[int] = []
    per_seed_d_z: list[float] = []
    per_seed_var: list[float] = []

    for seed in args.seeds:
        sdir = args.root / f"seed{seed}"
        base = _record_hits(sdir / "baseline_hits.tbl")
        fw = _record_hits(sdir / "framework_hits.tbl")
        diffs = np.array(
            [fw.get(i, 0) - base.get(i, 0) for i in range(args.n_per_seed)],
            dtype=float,
        )
        st = _paired_stats(diffs)
        b_total = int(sum(base.values()))
        f_total = int(sum(fw.values()))
        row = {
            "seed": seed,
            "baseline_total_hits": b_total,
            "framework_total_hits": f_total,
            "total_diff": f_total - b_total,
            "total_pct": (100.0 * (f_total - b_total) / b_total) if b_total else float("nan"),
            **st,
            "direction": "framework>baseline" if st["mean_diff_per_record"] > 0 else "baseline>framework",
        }
        per_seed.append(row)
        total_diffs.append(f_total - b_total)
        per_seed_d_z.append(st["d_z"])
        per_seed_var.append(st["dz_var"])

    td = np.array(total_diffs, dtype=float)
    pooled = {
        "diffs": total_diffs,
        "mean_diff": float(np.mean(td)),
        "sd": float(np.std(td, ddof=1)),
        "t": float(np.mean(td) / (np.std(td, ddof=1) / math.sqrt(td.size))),
        "df": int(td.size - 1),
        "p_two_sided": float(
            2 * stats.t.sf(abs(np.mean(td) / (np.std(td, ddof=1) / math.sqrt(td.size))), df=td.size - 1)
        ),
        "d_z": float(np.mean(td) / np.std(td, ddof=1)),
    }
    pooled["p_bonf_k7"] = min(pooled["p_two_sided"] * 7, 1.0)
    pooled["p_bonf_k16"] = min(pooled["p_two_sided"] * 16, 1.0)

    dl = dersimonian_laird_d_z(per_seed_d_z, per_seed_var)
    dl["p_bonf_k7"] = min(dl["p_two_sided"] * 7, 1.0)
    dl["p_bonf_k16"] = min(dl["p_two_sided"] * 16, 1.0)

    verdict = {
        "all_seeds_direction_consistent": len({r["direction"] for r in per_seed}) == 1,
        "alpha_rlevel_k7": ALPHA_RLEVEL_K7,
        "alpha_rlevel_k16": ALPHA_RLEVEL_K16,
        "seed_level_dz_gt_0.8": bool(pooled["d_z"] > 0.8),
        "seed_level_bonf_sig_k7": bool(pooled["p_bonf_k7"] < ALPHA_RLEVEL_K7),
        "dl_dz_gt_0.8": bool(dl["d_pooled"] > 0.8),
        "dl_bonf_sig_k7": bool(dl["p_bonf_k7"] < ALPHA_RLEVEL_K7),
    }

    out = {
        "seeds": {str(s): None for s in args.seeds},
        "per_seed": per_seed,
        "seed_level_pooled": pooled,
        "dl_meta": {
            "per_seed_dz": per_seed_d_z,
            **dl,
        },
        "verdict": verdict,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"per_seed": per_seed, "seed_level_pooled": pooled, "dl_meta": dl, "verdict": verdict}, indent=2))


if __name__ == "__main__":
    main()
