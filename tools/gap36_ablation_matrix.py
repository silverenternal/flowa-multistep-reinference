#!/usr/bin/env python3
"""GAP-36 — consolidated rounds x schedulers x checkpoints ablation matrix.

GAP-36 asks for **one** consolidated ablation table crossing the three axes that
the generative headline cells were swept along — **rounds**, **schedulers**, and
**checkpoints** — with matched-NFE controls, assembled from existing runs (no new
experiments).

Sources (both already committed):

* ``verification_outputs/gap04-r5b-rounds-multiseed.json`` — R5b (CIFAR-10 FM),
  rounds {1, 2, 3} x 4 schedulers x 3 seeds, N=200, matched NFE=50. Cohen's
  d_z is at the **per-sample feature-distance** level (see
  ``scripts/gap04_r5b_rounds_multiseed.py``).
* ``verification_outputs/gap35-mnist-regime/aggregate.json`` — R5c (MNIST FM),
  4 checkpoints x 3 schedulers x 3 seeds, N=1000, matched NFE=50. Cohen's d_z
  is at the **paired-chunk** level (see ``docs/audit/gap35-cross-domain.md``).

The two d_z columns are therefore **not** on a common unit; the ``stat_unit``
column records which is which. Verdicts use ``mean_delta_pct`` sign + a
0.5 % tie band + Bonferroni significance of the best seed (``min_p_bonf``).

Outputs ``ablation_matrix.{json,csv,md}`` under ``verification_outputs/
gap36-ablation-matrix/``. Audit note: ``docs/audit/gap36-ablation-matrix.md``.
CPU-only, stdlib + json.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VO = REPO_ROOT / "verification_outputs"

#: Matched-NFE labels for the two generative cells.
ROUNDS_SCHED_SRC = VO / "gap04-r5b-rounds-multiseed.json"
CKPT_SCHED_SRC = VO / "gap35-mnist-regime" / "aggregate.json"


def _verdict(delta_pct: float, min_p_bonf: float, alpha: float = 0.05,
             tie_band: float = 0.5) -> str:
    """Three-way verdict: wins require the sign to clear the tie band AND the
    best seed to be Bonferroni-significant; otherwise ``n.s.`` (beyond band but
    not significant) or ``tie`` (within band)."""
    if abs(delta_pct) < tie_band:
        return "tie"
    if min_p_bonf >= alpha:
        return "n.s."
    return "framework_wins" if delta_pct < 0 else "baseline_wins"


def _from_rounds_schedulers() -> list[dict]:
    """R5b: rounds x schedulers (one checkpoint)."""
    d = json.loads(ROUNDS_SCHED_SRC.read_text())
    nfe, n_samples = d["nfe"], d["n_samples"]
    seeds = d["seeds"]
    rows: list[dict] = []
    for rounds in d["n_rounds"]:
        for sched in ("CosineAnnealScheduler", "CodimensionSheetScheduler",
                      "EvidenceDrivenScheduler", "FreeTrajScheduler"):
            deltas, dzs, pbonfs, base_fids = [], [], [], []
            for seed in seeds:
                cell = d["per_cell"].get(f"r{rounds}_s{seed}")
                if cell is None:
                    continue
                arm = cell["framework_arms"].get(sched)
                if arm is None:
                    continue
                deltas.append(float(arm["delta_vs_baseline_pct"]))
                dzs.append(float(arm["cohens_dz"]))
                pbonfs.append(float(arm["p_value_bonferroni"]))
                base_fids.append(float(cell["baseline_fid"]))
            if not deltas:
                continue
            m = sum(deltas) / len(deltas)
            rows.append({
                "cell": "R5b",
                "model": "cifar10_fm",
                "checkpoint": "cifar10 smoke (epochs=1, ch=8)",
                "ckpt_opt_steps": None,
                "rounds": int(rounds),
                "scheduler": sched,
                "nfe": int(nfe),
                "n_samples": int(n_samples),
                "n_seeds": len(deltas),
                "stat_unit": "per_sample_feature_distance",
                "baseline_metric": round(sum(base_fids) / len(base_fids), 4),
                "mean_delta_pct": round(m, 4),
                "mean_dz": round(sum(dzs) / len(dzs), 4),
                "min_p_bonf": round(min(pbonfs), 6),
                "verdict": _verdict(m, min(pbonfs)),
                "source": ROUNDS_SCHED_SRC.name,
            })
    return rows


def _from_checkpoints_schedulers() -> list[dict]:
    """R5c: checkpoints x schedulers (framework default rounds)."""
    d = json.loads(CKPT_SCHED_SRC.read_text())
    n_samples = d["n_samples"]
    rows: list[dict] = []
    for ck, cell in d["regime_table"].items():
        arms = sorted({a for ps in cell["per_seed"] for a in ps["all_arms"]})
        for sched in arms:
            deltas, dzs, pbonfs, base_fids = [], [], [], []
            for ps in cell["per_seed"]:
                arm = ps["all_arms"].get(sched)
                if arm is None:
                    continue
                deltas.append(float(arm["delta_vs_baseline_pct"]))
                dzs.append(float(arm["cohens_dz"]))
                pbonfs.append(float(arm["p_value_bonf"]))
                base_fids.append(float(ps["baseline_fid"]))
            if not deltas:
                continue
            m = sum(deltas) / len(deltas)
            rows.append({
                "cell": "R5c",
                "model": "mnist_fm",
                "checkpoint": ck,
                "ckpt_opt_steps": cell.get("opt_steps"),
                "rounds": 4,  # framework default (restart_from_round=1, 4 rounds)
                "scheduler": sched,
                "nfe": 50,
                "n_samples": int(n_samples),
                "n_seeds": len(deltas),
                "stat_unit": "paired_chunk",
                "baseline_metric": round(sum(base_fids) / len(base_fids), 4),
                "mean_delta_pct": round(m, 4),
                "mean_dz": round(sum(dzs) / len(dzs), 4),
                "min_p_bonf": round(min(pbonfs), 6),
                "verdict": _verdict(m, min(pbonfs)),
                "source": CKPT_SCHED_SRC.parent.name + "/" + CKPT_SCHED_SRC.name,
            })
    return rows


def build() -> list[dict]:
    return _from_rounds_schedulers() + _from_checkpoints_schedulers()


def _md_table(rows: list[dict]) -> str:
    cols = ["cell", "checkpoint", "rounds", "scheduler", "nfe", "n_samples",
            "n_seeds", "stat_unit", "baseline_metric", "mean_delta_pct",
            "mean_dz", "min_p_bonf", "verdict"]
    head = "| " + " | ".join(cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    lines = [head, sep]
    for r in rows:
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--outdir", type=Path,
                    default=VO / "gap36-ablation-matrix")
    args = ap.parse_args(argv)
    args.outdir.mkdir(parents=True, exist_ok=True)

    rows = build()
    (args.outdir / "ablation_matrix.json").write_text(json.dumps(rows, indent=2))
    with (args.outdir / "ablation_matrix.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (args.outdir / "ablation_matrix.md").write_text(_md_table(rows) + "\n")

    print(f"rows: {len(rows)}")
    print(_md_table(rows))
    print(f"\nwrote {args.outdir}/ablation_matrix.{{json,csv,md}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
