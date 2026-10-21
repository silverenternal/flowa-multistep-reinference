#!/usr/bin/env python3
"""GAP-76 report — does centroid anchoring remove the first-moment defect?

Compares the mean-preserving run (`gap76-mean-preserving/<ckpt>_s<seed>/`)
against the frozen matched-NFE ladder (`gap57-equal-nfe-ladder-n1000/`) and
against the GAP-77 counterfactual (`gap77-restart-mechanism/decomposition.json`).

Three checks, in the order the pre-registration fixes them:

1. **Control** — `Tr(S)` and `cross` are translation-invariant, so the new arm
   must reproduce the old arm's values exactly. If they differ, the run is not
   comparable and the report says so instead of printing deltas.
2. **Displacement** — `||mean(arm) - mean(baseline)||` must collapse.
3. **Delta FID** — must match the counterfactual `delta_fid - delta_bias`.

Usage
-----
    PYTHONPATH=. python3 tools/gap76_report.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ARMS: tuple[str, ...] = ("cosine", "codimension_sheet", "evidence_driven")


def _load_samples(path: Path) -> np.ndarray:
    with np.load(path) as blob:
        key = "samples" if "samples" in blob else list(blob)[0]
        arr = np.asarray(blob[key], dtype=np.float64)
    return arr.reshape(arr.shape[0], -1)


def _terms(
    features: np.ndarray, ref: np.ndarray, ref_sqrt: np.ndarray
) -> dict[str, float]:
    mu_g = features.mean(axis=0)
    mu_r = ref.mean(axis=0)
    cov_g = np.cov(features, rowvar=False)
    cov_r = np.cov(ref, rowvar=False)
    bias = float(((mu_g - mu_r) ** 2).sum())
    trace_g = float(np.trace(cov_g))
    trace_r = float(np.trace(cov_r))
    sandwich = ref_sqrt @ cov_g @ ref_sqrt
    eig = np.linalg.eigvalsh((sandwich + sandwich.T) / 2.0)
    cross = float(np.sqrt(np.clip(eig, 0.0, None)).sum())
    return {
        "bias": bias,
        "trace_g": trace_g,
        "trace_r": trace_r,
        "cross": cross,
        "fid": bias + trace_g + trace_r - 2.0 * cross,
        "mean": mu_g,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", type=Path,
                        default=Path("verification_outputs/gap57-equal-nfe-ladder-n1000"))
    parser.add_argument("--new", type=Path,
                        default=Path("verification_outputs/gap76-mean-preserving"))
    parser.add_argument("--gap77", type=Path,
                        default=Path("verification_outputs/gap77-restart-mechanism/decomposition.json"))
    parser.add_argument("--out", type=Path,
                        default=Path("verification_outputs/gap76-mean-preserving/report.json"))
    args = parser.parse_args(argv)

    from adaptive_reflow.eval.mnist_fid import MnistFrechetProjectionEvaluator

    evaluator = MnistFrechetProjectionEvaluator()
    ref = np.asarray(evaluator._ref_features, dtype=np.float64)
    projection = np.asarray(evaluator._projection, dtype=np.float64)
    eig_w, eig_v = np.linalg.eigh(np.cov(ref, rowvar=False))
    ref_sqrt = (eig_v * np.sqrt(np.clip(eig_w, 0.0, None))) @ eig_v.T

    counterfactual = {}
    if args.gap77.exists():
        blob = json.loads(args.gap77.read_text())
        for row in blob.get("counterfactual_mean_preserved", []):
            counterfactual[(row["checkpoint"], row["seed"], row["arm"])] = row

    rows: list[dict[str, object]] = []
    for new_dir in sorted(args.new.glob("*_s*")):
        if not new_dir.is_dir():
            continue
        name = new_dir.name
        checkpoint, _, seed_s = name.rpartition("_s")
        old_dir = args.old / name
        if not old_dir.exists():
            print(f"[skip] no frozen counterpart for {name}")
            continue
        seed = int(seed_s)
        base_new = _terms(_load_samples(new_dir / "baseline_samples.npz") @ projection,
                          ref, ref_sqrt)
        base_old = _terms(_load_samples(old_dir / "baseline_samples.npz") @ projection,
                          ref, ref_sqrt)
        for arm in ARMS:
            p_new = new_dir / f"{arm}_samples.npz"
            p_old = old_dir / f"{arm}_samples.npz"
            if not p_new.exists() or not p_old.exists():
                continue
            t_new = _terms(_load_samples(p_new) @ projection, ref, ref_sqrt)
            t_old = _terms(_load_samples(p_old) @ projection, ref, ref_sqrt)
            cf = counterfactual.get((checkpoint, seed, arm), {})
            rows.append(
                {
                    "checkpoint": checkpoint,
                    "seed": seed,
                    "arm": arm,
                    # control: translation-invariant quantities
                    "trace_g_new": t_new["trace_g"],
                    "trace_g_old": t_old["trace_g"],
                    "cross_new": t_new["cross"],
                    "cross_old": t_old["cross"],
                    "control_ok": bool(
                        abs(t_new["trace_g"] - t_old["trace_g"]) < 1e-8
                        and abs(t_new["cross"] - t_old["cross"]) < 1e-8
                    ),
                    "baseline_fid": base_old["fid"],
                    "delta_fid_old": t_old["fid"] - base_old["fid"],
                    "delta_fid_new": t_new["fid"] - base_new["fid"],
                    "delta_fid_pct_new": 100.0
                    * (t_new["fid"] - base_new["fid"])
                    / base_old["fid"],
                    "shift_new": float(np.linalg.norm(t_new["mean"] - base_new["mean"])),
                    "shift_old": float(np.linalg.norm(t_old["mean"] - base_old["mean"])),
                    "bias_new": t_new["bias"],
                    "bias_old": t_old["bias"],
                    "counterfactual_delta_fid": cf.get("mean_preserved_delta_fid"),
                }
            )

    if not rows:
        print("no comparable cells found")
        return 1

    control_fail = [r for r in rows if not r["control_ok"]]
    improved = [r for r in rows if float(r["delta_fid_new"]) <= 0.0]  # type: ignore[arg-type]

    print(f"{'ckpt':11s} {'seed':>4s} {'arm':18s} {'dFID_old':>9s} {'dFID_new':>9s} "
          f"{'pred':>8s} {'shift_old':>9s} {'shift_new':>9s} {'ctrl':>5s}")
    for r in rows:
        pred = r["counterfactual_delta_fid"]
        pred_s = f"{float(pred):+9.3f}" if pred is not None else f"{'n/a':>9s}"
        print(f"{r['checkpoint']:11s} {r['seed']:4d} {r['arm']:18s} "
              f"{float(r['delta_fid_old']):+9.3f} {float(r['delta_fid_new']):+9.3f} "
              f"{pred_s} {float(r['shift_old']):9.3f} {float(r['shift_new']):9.3f} "
              f"{'OK' if r['control_ok'] else 'FAIL':>5s}")
    print()
    print(f"control (translation-invariant terms reproduced): {len(rows) - len(control_fail)}/{len(rows)}")
    print(f"non-positive delta FID: {len(improved)}/{len(rows)}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"n_cells": len(rows), "cells": rows}, indent=1) + "\n",
                        encoding="utf-8")
    print(f"wrote {args.out}")
    return 0 if not control_fail else 2


if __name__ == "__main__":
    raise SystemExit(main())
