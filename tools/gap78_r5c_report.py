#!/usr/bin/env python3
"""GAP-78 — the R5c 3-seed report, read against the GAP-84 win definition.

Input: a directory of cells named ``<ckpt>_beta<beta>_s<seed>``, each holding a
``sweep_summary.json`` from ``scripts/wave191_p3_mnist_sweep.py``.

The ledger metric is the **headline** projection-FID delta (GAP-76's
"+7.75 % → −3.34 %" is the headline, verified by recomputing that mean from its
12 cell means). The chunk-level paired delta is reported alongside because the
two disagree in sign on at least one checkpoint (GAP-67 §2.2, GAP-78 §9); the
chunk number never decides a verdict here.

Two margins are computed on the same rows, because GAP-84 §0.5 originally
specified a universal 1 % *relative* margin and the ledger's own per-cell floor
for this metric is 1 *FID unit* absolute (GAP-76 §1.2, CLM-060 min_effect_size).
On these baselines the two differ by 4x-9x, so both verdicts are printed:

* **relative** (the pre-registered rule) — ``CI95_high(delta_pct) <= +1 %``
* **floor** (the ledger rule) — ``CI95_high(delta_units) <= +floor``

and a strict gain is ``CI95_high < 0`` (relative) or ``CI95_high <= -floor``
(floor — the symmetric "95 % confident it beats the floor" rule, which is
stricter than GAP-76's point-mean census). R5c WINs only if weak dominance holds at
every (checkpoint, arm) cell **and** at least one cell carries a strict gain.

There is no override, no "within noise" clause and no best-arm selection: the
verdict is read off all twelve cells.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

MARGIN = 0.01  # 1 % relative, GAP-84 §0.5 (pre-registered)
FLOOR_UNITS = 1.0  # 1 FID unit absolute, the ledger's MNIST-FID effect floor
CELL_RE = re.compile(r"^(?P<ckpt>.+)_beta(?P<beta>[0-9.]+)_s(?P<seed>\d+)$")


def _t_ci(values: list[float]) -> tuple[float, float]:
    arr = np.asarray(values, dtype=np.float64)
    n = arr.size
    if n < 2:
        return float("nan"), float("nan")
    half = stats.t.ppf(0.975, n - 1) * arr.std(ddof=1) / np.sqrt(n)
    mean = float(arr.mean())
    return mean - float(half), mean + float(half)


def collect(root: Path) -> dict[str, dict[str, list[dict[str, float]]]]:
    """``{ckpt: {arm: [row per seed]}}`` with the seed recorded on each row."""
    out: dict[str, dict[str, list[dict[str, float]]]] = {}
    for cell in sorted(p for p in root.iterdir() if p.is_dir()):
        m = CELL_RE.match(cell.name)
        summary = cell / "sweep_summary.json"
        if m is None or not summary.exists():
            continue
        d = json.loads(summary.read_text())
        base = float(d["baseline_fid"])
        ckpt = m.group("ckpt")
        seed = int(m.group("seed"))
        for arm, payload in d["framework_arms"].items():
            out.setdefault(ckpt, {}).setdefault(arm, []).append({
                "seed": seed,
                "baseline": base,
                "headline_delta": (float(payload["fid_headline"]) - base) / base * 100.0,
                "headline_delta_units": float(payload["fid_headline"]) - base,
                "chunk_delta": float(payload.get("delta_vs_baseline_pct", float("nan"))),
            })
    return out


def report(root: Path, *, margin: float = MARGIN,
           floor_units: float = FLOOR_UNITS) -> dict[str, Any]:
    data = collect(root)
    if not data:
        raise SystemExit(f"no '<ckpt>_beta<b>_s<seed>' cells with sweep_summary.json under {root}")

    rows: list[dict[str, Any]] = []
    for ckpt in sorted(data):
        for arm in sorted(data[ckpt]):
            seeds = sorted(data[ckpt][arm], key=lambda r: r["seed"])
            head = [r["headline_delta"] for r in seeds]
            units = [r["headline_delta_units"] for r in seeds]
            chunk = [r["chunk_delta"] for r in seeds]
            lo, hi = _t_ci(head)
            ulo, uhi = _t_ci(units)
            rows.append({
                "ckpt": ckpt,
                "arm": arm,
                "n_seeds": len(seeds),
                "seeds": [r["seed"] for r in seeds],
                "baseline_fid": seeds[0]["baseline"],
                "headline_delta": head,
                "headline_mean": float(np.mean(head)),
                "headline_sd": float(np.std(head, ddof=1)) if len(head) > 1 else float("nan"),
                "headline_ci95": [lo, hi],
                "delta_units_mean": float(np.mean(units)),
                "delta_units_ci95": [ulo, uhi],
                "chunk_mean": float(np.mean(chunk)),
                "weak_dominance": bool(np.isfinite(hi) and hi <= margin * 100.0),
                "strict_gain": bool(np.isfinite(hi) and hi < 0.0),
                "weak_dominance_floor": bool(np.isfinite(uhi) and uhi <= floor_units),
                "strict_gain_floor": bool(np.isfinite(uhi) and uhi <= -floor_units),
            })

    def _verdict(key_weak: str, key_gain: str) -> str:
        if any(r["n_seeds"] < 2 for r in rows):
            return "INCOMPLETE"
        if not all(r[key_weak] for r in rows):
            return "LOSS"
        return "WIN" if any(r[key_gain] for r in rows) else "TIE"

    n_cells = len(rows)
    n_weak = sum(r["weak_dominance"] for r in rows)
    gains = [r for r in rows if r["strict_gain"]]
    per_ckpt: dict[str, Any] = {}
    for ckpt in sorted(data):
        sub = [r for r in rows if r["ckpt"] == ckpt]
        per_ckpt[ckpt] = {
            "mean_headline": float(np.mean([r["headline_mean"] for r in sub])),
            "mean_units": float(np.mean([r["delta_units_mean"] for r in sub])),
            "weak_dominance_all_arms": all(r["weak_dominance"] for r in sub),
            "weak_dominance_floor_all_arms": all(r["weak_dominance_floor"] for r in sub),
            "strict_gain_arms": [r["arm"] for r in sub if r["strict_gain"]],
            "strict_gain_floor_arms": [r["arm"] for r in sub if r["strict_gain_floor"]],
        }

    return {
        "schema": "gap78_r5c_report_v2",
        "root": str(root),
        "margin_pct": margin * 100.0,
        "floor_units": floor_units,
        "n_cells": n_cells,
        "n_seeds_per_cell": sorted({r["n_seeds"] for r in rows}),
        "rows": rows,
        "per_checkpoint": per_ckpt,
        "n_weak_dominance": n_weak,
        "n_strict_gain": len(gains),
        "n_weak_dominance_floor": sum(r["weak_dominance_floor"] for r in rows),
        "n_strict_gain_floor": sum(r["strict_gain_floor"] for r in rows),
        "verdict_relative": _verdict("weak_dominance", "strict_gain"),
        "verdict_floor": _verdict("weak_dominance_floor", "strict_gain_floor"),
        "caveat": (
            "Headline metric decides. The chunk delta is printed for disclosure "
            "only; on w16e1_60k it disagrees with the headline in sign (GAP-78 §9). "
            "A verdict computed on 1 seed has no interval and cannot be quoted."
        ),
    }


def render(rep: dict[str, Any]) -> str:
    lines = [
        f"R5c report — {rep['n_cells']} cells, seeds/cell {rep['n_seeds_per_cell']}",
        f"relative margin ±{rep['margin_pct']:.1f} %   floor ±{rep['floor_units']:.1f} FID units",
        "",
        "| ckpt | arm | n | headline % (per seed) | mean % | CI95 % | ΔFID | CI95 units "
        "| chunk | weak | gain | weakF | gainF |",
        "|---|---|---:|---|---:|---|---:|---:|---:|:--:|:--:|:--:|:--:|",
    ]
    for r in rep["rows"]:
        per = " / ".join(f"{v:+.2f}" for v in r["headline_delta"])
        lo, hi = r["headline_ci95"]
        ulo, uhi = r["delta_units_ci95"]
        ci = "—" if not np.isfinite(lo) else f"[{lo:+.2f}, {hi:+.2f}]"
        uci = "—" if not np.isfinite(ulo) else f"[{ulo:+.3f}, {uhi:+.3f}]"
        lines.append(
            f"| {r['ckpt']} | {r['arm']} | {r['n_seeds']} | {per} | "
            f"{r['headline_mean']:+.2f} | {ci} | {r['delta_units_mean']:+.3f} | {uci} | "
            f"{r['chunk_mean']:+.2f} | "
            f"{'y' if r['weak_dominance'] else 'N'} | "
            f"{'y' if r['strict_gain'] else 'n'} | "
            f"{'y' if r['weak_dominance_floor'] else 'N'} | "
            f"{'y' if r['strict_gain_floor'] else 'n'} |"
        )
    lines += [
        "",
        f"relative rule: weak dominance {rep['n_weak_dominance']}/{rep['n_cells']}, "
        f"strict gains {rep['n_strict_gain']} → **{rep['verdict_relative']}**",
        f"floor rule:    weak dominance {rep['n_weak_dominance_floor']}/{rep['n_cells']}, "
        f"strict gains {rep['n_strict_gain_floor']} → **{rep['verdict_floor']}**",
        "",
        f"Caveat: {rep['caveat']}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--margin", type=float, default=MARGIN)
    ap.add_argument("--floor-units", type=float, default=FLOOR_UNITS,
                    help="absolute effect floor in metric units (MNIST projection-FID: 1.0)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    rep = report(args.root, margin=args.margin, floor_units=args.floor_units)
    print(render(rep))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rep, indent=1) + "\n")
        print(f"\nwrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
