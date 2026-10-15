#!/usr/bin/env python3
"""GAP-37 — cross-cell statistical-power audit for the primary FlowA cells.

For each primary headline cell, the *replication unit* (seed / record / chunk /
cluster) determines the effective n, and therefore the power. This tool makes
the unit explicit and computes, per cell:

* the achieved **power** at the cell's reported effect size and replication
  count (two-sided normal approximation; Bonferroni-adjusted α where the cell
  belongs to a corrected family);
* the **n required** for 80 % power at the same effect size;
* a verdict ``adequate`` (power >= 0.8) / ``bounded_null`` (power < 0.8).

The point is honest bookkeeping: a "tiny" effect size (R2 d_z = 0.096) can be
adequately powered if the unit is the record (n = 1000), while a larger effect
size (R3 d_z = 0.40) is underpowered if the unit is the seed (n = 3).

CPU-only, numpy + scipy. Evidence: ``verification_outputs/gap37-power-audit/``.
Audit note: ``docs/audit/gap37-statistical-power.md``.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ALPHA = 0.05
TARGET_POWER = 0.80


@dataclass(frozen=True)
class PowerCell:
    """One primary cell's power inputs."""

    cell: str
    metric: str
    unit: str  # seed | record | chunk | cluster
    n: int
    effect_size: float  # d_z / Cohen's d at that unit
    alpha: float  # per-test alpha actually used (Bonferroni-corrected family α)
    source: str


#: Primary cells (R1..R6 + K-cells). ``alpha`` is the family-corrected level the
#: cell's verdict is actually judged at (R-level 0.05/7, R6 per-tier 0.05/6,
#: K-level 0.05/4). ``n`` is the replication count at ``unit``.
PRIMARY_CELLS: tuple[PowerCell, ...] = (
    PowerCell("R1", "HMMER hits", "record", 3000, 0.156, 0.05 / 7,
              "docs/audit/todo-history.md §5 (DL d_pooled=+0.156)"),
    PowerCell("R1", "HMMER hits (seed-pooled)", "seed", 3, 0.156, 0.05 / 7,
              "docs/audit/todo-history.md §5 (seed-pooled p_bonf=0.063)"),
    PowerCell("R2", "Kanzi RMSD", "record", 1000, 0.0956, 0.05 / 7,
              "verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj.json"),
    PowerCell("R2", "Kanzi RMSD (cluster-robust)", "cluster", 4, -0.879, 0.05 / 7,
              "verification_outputs/wave209-p2-cluster-robust-all-cells.csv"),
    PowerCell("R3", "FlowMol3 fg_dev (independent prior)", "seed", 3, -0.401, 0.05 / 7,
              "docs/audit/gap27-r3-power.md"),
    PowerCell("R3", "FlowMol3 fg_dev (shared prior)", "seed", 3, -1.089, 0.05 / 7,
              "verification_outputs/gap37-r3-shared-prior/wave338-p5-r3-n1000-paired.json"),
    PowerCell("R5a", "2D Two Moons W2", "seed", 3, 0.460, 0.05 / 7,
              "README 11-cell ledger (TIE)"),
    PowerCell("R5b", "CIFAR-10 FID", "chunk", 10, 2.70, 0.05 / 7,
              "README 11-cell ledger (chunk-level paired t)"),
    PowerCell("R5c", "MNIST FM FID", "chunk", 10, -13.18, 0.05 / 7,
              "docs/audit/gap35-cross-domain.md"),
    PowerCell("R6", "scPerp (cluster)", "cluster", 4, 4.019, 0.05 / 6,
              "docs/audit/todo-history.md §4"),
    PowerCell("R6", "pLDDT (cluster)", "cluster", 4, 0.333, 0.05 / 6,
              "docs/audit/todo-history.md §4"),
    PowerCell("K1", "RDKit validity", "seed", 3, 1.36, 0.05 / 4,
              "README 11-cell ledger (K1)"),
    PowerCell("K4", "HMMER length-bias", "cluster", 3, 0.84, 0.05 / 4,
              "docs/audit/todo-history.md §4 (K4)"),
    PowerCell("K5", "HMMER delta", "cluster", 3, 1.12, 0.05 / 4,
              "docs/audit/todo-history.md §4 (K5)"),
)


def achieved_power(effect_size: float, n: int, alpha: float) -> float:
    """Two-sided normal-approximation power for a one-sample/paired d_z."""
    if n <= 0 or not math.isfinite(effect_size):
        return float("nan")
    z_alpha = float(stats.norm.ppf(1.0 - alpha / 2.0))
    ncp = abs(effect_size) * math.sqrt(n)
    return float(stats.norm.sf(z_alpha - ncp) + stats.norm.cdf(-z_alpha - ncp))


def n_for_power(effect_size: float, alpha: float, target: float = TARGET_POWER) -> float:
    """Replication count for ``target`` power at ``effect_size`` (paired d_z)."""
    if effect_size == 0.0 or not math.isfinite(effect_size):
        return float("inf")
    z_alpha = float(stats.norm.ppf(1.0 - alpha / 2.0))
    z_beta = float(stats.norm.ppf(target))
    return ((z_alpha + z_beta) / abs(effect_size)) ** 2


def audit(cells=PRIMARY_CELLS) -> list[dict]:
    rows = []
    for c in cells:
        p = achieved_power(c.effect_size, c.n, c.alpha)
        rows.append({
            **asdict(c),
            "power": round(p, 4),
            "n_for_80pct": round(n_for_power(c.effect_size, c.alpha), 1),
            "verdict": "adequate" if (p == p and p >= TARGET_POWER) else "bounded_null",
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output-dir", type=Path,
                    default=REPO_ROOT / "verification_outputs" / "gap37-power-audit")
    args = ap.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows = audit()
    (args.output_dir / "power_audit.json").write_text(json.dumps(rows, indent=2))
    with (args.output_dir / "power_audit.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    for r in rows:
        print(f"{r['cell']:4s} {r['unit']:8s} n={r['n']:<5d} d={r['effect_size']:+.3f} "
              f"alpha={r['alpha']:.4f} power={r['power']:.3f} "
              f"n@80%={r['n_for_80pct']:>7.1f} -> {r['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
