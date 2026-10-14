#!/usr/bin/env python3
"""GAP-35 — matched-architecture MNIST FM regime sweep (cross-domain coverage).

Motivation (paper §7.9 / §10.8).  The published R5c regime curve compares three
checkpoints that differ in **two** variables at once: the smoke checkpoint uses
``base_channels=8`` and 6 000 training images, whereas the intermediate
(``epochs2``) and production checkpoints use ``base_channels=16`` and 60 000
images.  §7.9 states explicitly that "the epochs = 1 -> 2 comparison is
confounded" and §10.8 asks for the missing control: *"vary epochs under one
architecture and training set"*.

This driver runs the canonical matched-NFE MNIST sweep
(``scripts/wave191_p3_mnist_sweep.py``) on a factorial set of checkpoints so the
**width** axis (8 vs 16 channels) and the **training-budget** axis (1 / 2 / 3
epochs at the full 60 K images) are separated:

    width=8  : smoke (1 ep, 6 K)  ,  w8e3 (3 ep, 60 K)
    width=16 : w16e1 (1 ep, 60 K) ,  w16e2 = epochs2 (2 ep, 60 K) ,
               w16e3 = production (3 ep, 60 K)

The GAP-35 acceptance is a **non-smoke** cell (``base_channels=16``) that is
framework-WINS vs the baseline.  ``w16e1`` is the decisive cell: if a
sixteen-channel checkpoint at the *lowest* training budget still wins, the
"framework value-add requires the tiny smoke width" hypothesis is refuted and
the win is a training-budget effect on a production-width model.

The GAP-12 tuned-baseline check (``scripts/gap12_mnist_tuned_baseline.py``) is a
separate follow-up on whichever checkpoint wins.

Usage::

    python tools/sweep_gap35_mnist_regime.py \
        --ckpts w16e1 --seeds 42 --out verification_outputs/gap35-mnist-regime

Writes ``<out>/<ckpt>/seed<NN>/sweep_summary.json`` (per run) and, when all
requested runs exist, ``<out>/aggregate.{json,csv}``.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parent
W191 = REPO_ROOT / "scripts" / "wave191_p3_mnist_sweep.py"

# name -> (relative ckpt path, base_channels, epochs, train_images)
# batch_size is 64 (the canonical recipe), so optimizer steps =
# epochs * (train_images // 64); this is the regime variable the sweep probes.
BATCH_SIZE = 64
CKPTS: dict[str, tuple[str, int, int, int]] = {
    "smoke_w8e1_6k": ("data/mnist_fm.npz", 8, 1, 6000),
    "w8e3_60k": ("data/mnist_fm/w8e3.ckpt.npz", 8, 3, 60000),
    "w16e1_5k": ("data/mnist_fm/w16e1_5k.ckpt.npz", 16, 1, 5000),
    "w16e1_10k": ("data/mnist_fm/w16e1_10k.ckpt.npz", 16, 1, 10000),
    "w16e1_60k": ("data/mnist_fm/w16e1.ckpt.npz", 16, 1, 60000),
    "w16e2_60k": ("data/mnist_fm/epochs2.ckpt.npz", 16, 2, 60000),
    "w16e3_60k": ("data/mnist_fm/production.ckpt.npz", 16, 3, 60000),
}


def _opt_steps(epochs: int, train_images: int) -> int:
    return int(epochs) * (int(train_images) // BATCH_SIZE)


ARM_LABELS = ("cosine", "codimension_sheet", "evidence_driven")


def _run_one(ckpt_name: str, seed: int, out_root: Path, n_samples: int) -> Path:
    """Invoke the canonical wave191 sweep for one (ckpt, seed). Returns the JSON path."""
    rel, _w, _e, _n = CKPTS[ckpt_name]
    ckpt_path = REPO_ROOT / rel
    if not ckpt_path.exists():
        raise SystemExit(f"checkpoint_missing:{ckpt_path}")
    seed_dir = out_root / ckpt_name / f"seed{seed}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    out_json = seed_dir / "sweep_summary.json"
    cmd = [
        sys.executable, str(W191),
        "--ckpt", str(ckpt_path),
        "--n-samples", str(int(n_samples)),
        "--seed", str(int(seed)),
        "--output-dir", str(seed_dir),
        "--output-json", str(out_json),
        "--quiet",
    ]
    print(f"[gap35] {ckpt_name} seed{seed}: {' '.join(cmd)}", flush=True)
    t0 = time.perf_counter()
    subprocess.run(cmd, check=True)
    print(f"[gap35] {ckpt_name} seed{seed}: done in {time.perf_counter() - t0:.1f}s", flush=True)
    return out_json


def _read_seed(ckpt_name: str, seed: int, out_root: Path) -> dict:
    d = json.loads((out_root / ckpt_name / f"seed{seed}" / "sweep_summary.json").read_text())
    arms = d["framework_arms"]
    best = min(arms, key=lambda k: arms[k]["fid_headline"])
    return {
        "seed": int(seed),
        "baseline_fid": float(d["baseline_fid"]),
        "best_arm": best,
        "best_arm_fid": float(arms[best]["fid_headline"]),
        "best_arm_delta_pct": float(arms[best]["delta_vs_baseline_pct"]),
        "best_arm_p_bonf": float(arms[best]["p_value_bonferroni"]),
        "best_arm_dz": float(arms[best]["cohens_dz"]),
        "verdict": d["verdict"],
        "wall_min": float(d["wall_min"]),
        "ckpt_is_smoke_by_size": bool(d.get("checkpoint_is_smoke_materialization")),
        "all_arms": {
            k: {
                "fid_headline": float(arms[k]["fid_headline"]),
                "delta_vs_baseline_pct": float(arms[k]["delta_vs_baseline_pct"]),
                "p_value_bonf": float(arms[k]["p_value_bonferroni"]),
                "cohens_dz": float(arms[k]["cohens_dz"]),
            }
            for k in ARM_LABELS
        },
    }


def _pooled(per_seed: list[dict]) -> dict:
    """Seed-level paired t-test on the (best_arm - baseline) chunk-mean delta."""
    deltas = np.asarray([d["best_arm_delta_pct"] for d in per_seed], dtype=np.float64)
    n = int(deltas.size)
    mean = float(deltas.mean())
    if n < 2:
        return {"n_seeds": n, "delta_pct_mean": mean, "sd": float("nan"),
                "t_stat": float("nan"), "df": 0, "p_value_raw": float("nan"),
                "cohens_dz": float("nan"), "bonf_sig": False}
    sd = float(deltas.std(ddof=1))
    se = sd / math.sqrt(n)
    t = mean / se if se > 0 else float("nan")
    df = n - 1
    p = float(2.0 * stats.t.sf(abs(t), df=df)) if t == t else float("nan")
    dz = mean / sd if sd > 0 else float("nan")
    return {
        "n_seeds": n,
        "delta_pct_mean": mean,
        "sd": sd,
        "se": se,
        "t_stat": t,
        "df": df,
        "p_value_raw": p,
        "p_value_bonferroni": min(p * len(ARM_LABELS), 1.0) if p == p else float("nan"),
        "cohens_dz": dz,
        "bonf_sig": bool(p == p and p * len(ARM_LABELS) < 0.05),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ckpts", nargs="+", default=["w16e1_60k"], choices=sorted(CKPTS))
    ap.add_argument("--seeds", nargs="+", type=int, default=[42])
    ap.add_argument("--n-samples", type=int, default=1000)
    ap.add_argument("--out", type=Path,
                    default=REPO_ROOT / "verification_outputs" / "gap35-mnist-regime")
    ap.add_argument("--aggregate-only", action="store_true")
    args = ap.parse_args(argv)

    out_root: Path = args.out
    out_root.mkdir(parents=True, exist_ok=True)

    if not args.aggregate_only:
        meta = {
            "kind": "gap35_mnist_regime_sweep",
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "device": "cpu (MnistFmAdapter is numpy-backed; no GPU)",
            "n_samples": int(args.n_samples),
            "ckpts": {c: {"path": CKPTS[c][0], "base_channels": CKPTS[c][1],
                          "epochs": CKPTS[c][2], "train_images": CKPTS[c][3]}
                      for c in args.ckpts},
            "seeds": [int(s) for s in args.seeds],
            "driver": "tools/sweep_gap35_mnist_regime.py",
            "inner_driver": "scripts/wave191_p3_mnist_sweep.py",
        }
        (out_root / "METADATA.json").write_text(json.dumps(meta, indent=2) + "\n")
        for ckpt_name in args.ckpts:
            for seed in args.seeds:
                _run_one(ckpt_name, int(seed), out_root, int(args.n_samples))

    # ---- aggregate over whatever (ckpt, seed) runs exist on disk ----
    table: dict[str, dict] = {}
    for ckpt_name, (rel, w, e, n_imgs) in CKPTS.items():
        ckpt_dir = out_root / ckpt_name
        if not ckpt_dir.exists():
            continue
        per_seed = []
        for seed in sorted(int(p.name[4:]) for p in ckpt_dir.glob("seed*")
                           if (p / "sweep_summary.json").exists()):
            per_seed.append(_read_seed(ckpt_name, seed, out_root))
        if not per_seed:
            continue
        table[ckpt_name] = {
            "ckpt": rel,
            "base_channels": w,
            "epochs": e,
            "train_images": n_imgs,
            "opt_steps": _opt_steps(e, n_imgs),
            "non_smoke_by_width": bool(w >= 16),
            "n_seeds": len(per_seed),
            "per_seed": per_seed,
            "pooled": _pooled(per_seed),
        }

    agg = {
        "schema_version": "gap35_mnist_regime_v1",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "n_samples": int(args.n_samples),
        "regime_table": table,
        "reading": (
            "non_smoke_by_width = base_channels>=16 (the production-width axis). "
            "A framework-WINS verdict on a non_smoke_by_width checkpoint with "
            "bonf_sig=True is the GAP-35 acceptance."
        ),
    }
    (out_root / "aggregate.json").write_text(json.dumps(agg, indent=2) + "\n")

    csv_path = out_root / "aggregate.csv"
    with csv_path.open("w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["ckpt", "base_channels", "epochs", "train_images",
                     "opt_steps", "non_smoke_by_width", "n_seeds", "baseline_fid_mean",
                     "best_arm_fid_mean", "delta_pct_mean", "cohens_dz",
                     "p_value_bonferroni", "bonf_sig", "verdict"])
        for name, row in table.items():
            ps = row["per_seed"]
            pooled = row["pooled"]
            verdict = "framework_wins" if pooled["delta_pct_mean"] < 0 else "baseline_wins"
            wr.writerow([
                name, row["base_channels"], row["epochs"], row["train_images"],
                row["opt_steps"],
                row["non_smoke_by_width"], row["n_seeds"],
                f"{np.mean([d['baseline_fid'] for d in ps]):.6f}",
                f"{np.mean([d['best_arm_fid'] for d in ps]):.6f}",
                f"{pooled['delta_pct_mean']:.6f}",
                f"{pooled['cohens_dz']:.6f}",
                f"{pooled.get('p_value_bonferroni', float('nan')):.6g}",
                pooled["bonf_sig"], verdict,
            ])
    print(f"[gap35] wrote {out_root / 'aggregate.json'}")
    print(f"[gap35] wrote {csv_path}")
    for name, row in table.items():
        p = row["pooled"]
        print(f"  {name:16s} w={row['base_channels']:2d} e={row['epochs']} "
              f"n={row['n_seeds']} Δ%={p['delta_pct_mean']:+.3f} "
              f"d_z={p['cohens_dz']:+.3f} bonf_sig={p['bonf_sig']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
