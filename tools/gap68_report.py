#!/usr/bin/env python3
"""GAP-68 report — does the topology lock beat the all-channels-free restart?

Reads ``verification_outputs/gap68-flowmol3-channels/<arm>/seed<seed>/`` and
applies the pre-registered rules from ``docs/audit/gap68-flowmol3-channels.md``
§0.5, in order:

1. **pairing check** — the baseline arm must be byte-identical across arms for a
   given seed (the driver rebuilds it inside every call; under ``--shared-prior``
   the prior key is arm-independent). If it is not, the A/B is not paired and
   nothing below counts.
2. **rule 1** — ``mean(dA2) - mean(dA1) <= -0.5 * sd(dA2 - dA1)``.
3. **rule 2** — pooled A2 CI (95 %, t, df=2) excludes 0 and ``p < 0.00714``.

Usage
-----
    PYTHONPATH=. python3 tools/gap68_report.py
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import scipy.stats

ARMS: tuple[str, ...] = ("a1", "a2", "a3")
BONFERRONI_ALPHA = 0.05 / 7.0
METRICS: tuple[str, ...] = ("fg_dev", "pb_validity_pct")


def _read_cell(path: Path) -> dict[str, float]:
    base = json.loads(
        (path / f"flowmol3_n1000_baseline_wave338_p5_seed{_seed(path)}.json").read_text()
    )
    fw = json.loads(
        (path / f"flowmol3_n1000_framework_wave338_p5_seed{_seed(path)}.json").read_text()
    )
    out: dict[str, float] = {}
    for m in METRICS:
        b = float(base["metrics"][m])
        f = float(fw["metrics"][m])
        out[f"{m}_baseline"] = b
        out[f"{m}_framework"] = f
        out[f"{m}_delta"] = f - b
    out["n_sampled"] = float(fw["n_sampled"])
    out["validity_pct"] = float(fw["metrics"]["validity_pct"])
    # Diversity guard: the arm JSON stores the first 200 canonical SMILES.
    # A topology lock that improves fg_dev by collapsing every molecule onto
    # the prior's topology is not a fix, so the unique fraction is recorded.
    for tag, payload in (("baseline", base), ("framework", fw)):
        smiles = [s for s in (payload.get("smiles_list") or []) if s]
        out[f"{tag}_n_smiles"] = float(len(smiles))
        out[f"{tag}_n_unique"] = float(len(set(smiles)))
    return out


def _seed(path: Path) -> int:
    return int(path.name.removeprefix("seed"))


def _pooled(deltas: list[float]) -> dict[str, float]:
    arr = np.asarray(deltas, dtype=np.float64)
    n = int(arr.size)
    mean = float(arr.mean())
    if n < 2:
        return {
            "n": n,
            "mean": mean,
            "sd": float("nan"),
            "se": float("nan"),
            "t": float("nan"),
            "p": float("nan"),
            "ci_low": float("nan"),
            "ci_high": float("nan"),
            "d_z": float("nan"),
        }
    sd = float(arr.std(ddof=1))
    se = sd / math.sqrt(n)
    t = mean / se if se > 0 else float("nan")
    p = float(2.0 * scipy.stats.t.sf(abs(t), df=n - 1))
    crit = float(scipy.stats.t.ppf(0.975, df=n - 1))
    return {
        "n": n,
        "mean": mean,
        "sd": sd,
        "se": se,
        "t": float(t),
        "p": p,
        "ci_low": mean - crit * se,
        "ci_high": mean + crit * se,
        "d_z": mean / sd if sd > 0 else float("nan"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("verification_outputs/gap68-flowmol3-channels"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("verification_outputs/gap68-flowmol3-channels/report.json"),
    )
    args = parser.parse_args(argv)

    cells: dict[str, dict[int, dict[str, float]]] = {}
    for arm in ARMS:
        arm_dir = args.root / arm
        if not arm_dir.exists():
            continue
        rows: dict[int, dict[str, float]] = {}
        for seed_dir in sorted(arm_dir.glob("seed*")):
            if not seed_dir.is_dir():
                continue
            try:
                rows[_seed(seed_dir)] = _read_cell(seed_dir)
            except FileNotFoundError:
                continue
        if rows:
            cells[arm] = rows

    if "a1" not in cells or "a2" not in cells:
        print("need both a1 and a2 to run the pre-registered comparison")
        return 1

    shared = sorted(set(cells["a1"]) & set(cells["a2"]))
    print(f"{'arm':4s} {'seed':>4s} {'fg_base':>8s} {'fg_fw':>8s} {'fg_d':>8s} "
          f"{'pb_base':>8s} {'pb_fw':>8s} {'pb_d':>8s} {'uniq_b':>7s} {'uniq_fw':>7s}")
    for arm in ("a1", "a2", "a3"):
        for seed in sorted(cells.get(arm, {})):
            r = cells[arm][seed]
            print(f"{arm:4s} {seed:4d} {r['fg_dev_baseline']:8.4f} "
                  f"{r['fg_dev_framework']:8.4f} {r['fg_dev_delta']:+8.4f} "
                  f"{r['pb_validity_pct_baseline']:8.4f} "
                  f"{r['pb_validity_pct_framework']:8.4f} "
                  f"{r['pb_validity_pct_delta']:+8.4f} "
                  f"{r['baseline_n_unique']:7.0f} {r['framework_n_unique']:7.0f}")

    # --- 1. pairing check ------------------------------------------------
    mismatches = [
        (arm, seed)
        for arm in cells
        for seed in cells[arm]
        if seed in cells["a1"]
        and abs(
            cells[arm][seed]["fg_dev_baseline"] - cells["a1"][seed]["fg_dev_baseline"]
        )
        > 1e-12
    ]
    print()
    print(f"pairing check (baseline identical across arms): "
          f"{'OK' if not mismatches else f'FAIL {mismatches}'}")

    summary: dict[str, object] = {
        "cells": {arm: {str(k): v for k, v in rows.items()} for arm, rows in cells.items()},
        "shared_seeds": shared,
        "pairing_ok": not mismatches,
    }

    if mismatches:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
        print("pairing failed — no verdict computed")
        return 2

    # --- 2/3. pooled + rules --------------------------------------------
    pooled = {
        arm: _pooled([cells[arm][s]["fg_dev_delta"] for s in shared])
        for arm in ("a1", "a2")
    }
    pooled_pb = {
        arm: _pooled([cells[arm][s]["pb_validity_pct_delta"] for s in shared])
        for arm in ("a1", "a2")
    }
    print()
    print(f"{'arm':4s} {'n':>2s} {'mean d':>8s} {'sd':>7s} {'d_z':>7s} "
          f"{'CI95':>19s} {'p':>8s}")
    for arm in ("a1", "a2"):
        s = pooled[arm]
        print(f"{arm:4s} {s['n']:2d} {s['mean']:+8.4f} {s['sd']:7.4f} "
              f"{s['d_z']:+7.3f} [{s['ci_low']:+7.4f},{s['ci_high']:+7.4f}] "
              f"{s['p']:8.4f}")
    print()
    for arm in ("a1", "a2"):
        s = pooled_pb[arm]
        print(f"{arm:4s} pb_validity mean {s['mean']:+.4f}  d_z {s['d_z']:+.3f}  "
              f"p {s['p']:.4f}")

    diff = np.asarray(
        [cells["a2"][s]["fg_dev_delta"] - cells["a1"][s]["fg_dev_delta"] for s in shared],
        dtype=np.float64,
    )
    diff_mean = float(diff.mean())
    diff_sd = float(diff.std(ddof=1)) if diff.size > 1 else float("nan")
    rule1 = bool(diff.size > 1 and diff_mean <= -0.5 * diff_sd)
    a2 = pooled["a2"]
    rule2 = bool(
        a2["ci_high"] < 0.0 or a2["ci_low"] > 0.0
    ) and bool(a2["p"] < BONFERRONI_ALPHA)
    if rule1 and rule2:
        verdict = "SUPPORTED"
    elif rule1:
        verdict = "DIRECTIONAL_UNDERPOWERED"
    else:
        verdict = "CHANNEL_GEOMETRY_NOT_THE_BOTTLENECK"

    print()
    print(f"rule 1  mean(dA2 - dA1) = {diff_mean:+.4f}  sd = {diff_sd:.4f}  "
          f"bar = {-0.5 * diff_sd:+.4f}  -> {'PASS' if rule1 else 'FAIL'}")
    print(f"rule 2  A2 CI excludes 0 and p < {BONFERRONI_ALPHA:.5f}  -> "
          f"{'PASS' if rule2 else 'FAIL'}")
    print(f"verdict: {verdict}")

    summary.update(
        {
            "pooled_fg_dev": pooled,
            "pooled_pb_validity": pooled_pb,
            "rule1": {
                "diff_mean": diff_mean,
                "diff_sd": diff_sd,
                "bar": -0.5 * diff_sd,
                "pass": rule1,
            },
            "rule2": {"pass": rule2, "alpha": BONFERRONI_ALPHA},
            "verdict": verdict,
        }
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
