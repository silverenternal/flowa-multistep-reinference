#!/usr/bin/env python3
"""GAP-12 (R5c) — tuned-baseline fairness check on the MNIST FM smoke cell.

`todo.json` GAP-12-BASELINE asks for "matched-NFE + at least one tuned
baseline per headline cell (straw-man exposure)".  The classic framework-paper
failure is a **straw-man baseline**: the framework wins because the baseline
was denied compute.

The R5c cell (MNIST FM) is *regime-dependent* (see
``paper-data/R5c_mnist_fm/REPRODUCIBILITY_RECIPE.md``):

* **smoke ckpt** (1 epoch, base_channels=8, 6K imgs): framework-WINS
  (baseline FID 29.4925 -> best-arm FID 23.3879, ΔFID = −28.43 %, N=1000 seed 42);
* **production ckpt**: framework-REGRESSES.

The straw-man concern bites **only on the smoke-ckpt WIN**.  This driver gives
the *baseline* more solver steps (``num_steps`` in ``{50, 100, 200}``) while the
framework stays at its matched-NFE=50 protocol (4 rounds × 12 steps ≈ 48 NFE),
and reports whether the baseline's **best** step count closes the framework's
−28.43 % margin.  If baseline@best still loses to framework@matched, the R5c
smoke-ckpt win is **not** a compute artifact.

Only the *baseline* arm is re-run (the framework arm is unchanged and its
matched-NFE FID is reused from the canonical smoke result), so this is cheap
and CPU-only (the ``MnistFmAdapter`` is numpy-backed — no GPU).

Usage::

    python scripts/gap12_mnist_tuned_baseline.py \\
        --baseline-steps 50,100,200 --n-samples 1000 --seed 42

Writes ``verification_outputs/gap12-mnist-tuned-baseline.{json,csv}``.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "verification_outputs"
W191_PATH = REPO_ROOT / "scripts" / "wave191_p3_mnist_sweep.py"

# Canonical smoke-ckpt framework FID at matched NFE (best arm, EvidenceDriven),
# N=1000 seed 42 — from paper-data/R5c_mnist_fm/REPRODUCIBILITY_RECIPE.md (a).
# The framework arm is NOT re-run here (unchanged); we compare the tuned
# baseline against this frozen matched-NFE framework reading.
CANONICAL_FRAMEWORK_FID_MATCHED = 23.3879
CANONICAL_BASELINE_FID_MATCHED = 29.4925
CANONICAL_SMOKE_CKPT = REPO_ROOT / "data" / "mnist_fm.npz"


def _load_w191():
    spec = importlib.util.spec_from_file_location("_w191", W191_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline-steps", default="50,100,200")
    ap.add_argument("--n-samples", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cache-dir", default=str(REPO_ROOT / "data" / "mnist_fm_train_cache"))
    ap.add_argument("--ckpt", default=str(CANONICAL_SMOKE_CKPT))
    ap.add_argument("--framework-fid", type=float,
                    default=CANONICAL_FRAMEWORK_FID_MATCHED)
    ap.add_argument("--out-json", type=Path,
                    default=OUT_DIR / "gap12-mnist-tuned-baseline.json",
                    help="Output JSON path (GAP-35 reuses this driver on other "
                         "checkpoints without clobbering the canonical smoke result).")
    ap.add_argument("--out-csv", type=Path,
                    default=OUT_DIR / "gap12-mnist-tuned-baseline.csv",
                    help="Output CSV path.")
    args = ap.parse_args()

    steps_list = [int(s) for s in args.baseline_steps.split(",")]
    ckpt = Path(args.ckpt)
    if not ckpt.is_absolute():
        ckpt = (REPO_ROOT / ckpt).resolve()

    w = _load_w191()
    print(f"[gap12-mnist] baseline_steps={steps_list} N={args.n_samples} "
          f"seed={args.seed} ckpt={ckpt.name} framework_fid(matched)={args.framework_fid}",
          flush=True)

    # Reference features (MNIST test, 10K images -> 128 random projection).
    evaluator = w.MnistFrechetProjectionEvaluator(cache_dir=Path(args.cache_dir))
    ref_features = evaluator._ref_features
    projection = evaluator._projection
    print(f"[gap12-mnist] ref features: {ref_features.shape}", flush=True)

    rows: list[dict] = []
    for steps in steps_list:
        # The baseline arm reads the module-level BASELINE_NUM_STEPS at call
        # time (wave191_p3_mnist_sweep.py:239), so patching the module global
        # tunes the baseline's solver steps. The framework arm is untouched.
        w.BASELINE_NUM_STEPS = int(steps)
        adapter = w.MnistFmAdapter(weights_path=str(ckpt), num_steps=int(steps))
        t0 = time.perf_counter()
        samples = w.run_baseline(
            adapter=adapter, n_samples=int(args.n_samples), seed=int(args.seed),
        )
        wall = time.perf_counter() - t0
        fid = w.score_population(samples, ref_features, projection)
        beats = bool(fid < args.framework_fid)
        rows.append({
            "baseline_num_steps": int(steps),
            "baseline_fid": float(fid),
            "wall_seconds": float(wall),
            "framework_fid_matched_nfe": float(args.framework_fid),
            "framework_beats_baseline": bool(args.framework_fid < fid),
            "baseline_beats_framework": beats,
            "margin_framework_vs_baseline_pct": float(
                (args.framework_fid - fid) / fid * 100.0),
        })
        print(f"  [baseline num_steps={steps}] FID={fid:.4f} "
              f"({'BEATS' if beats else 'LOSES to'} framework@{args.framework_fid:.4f}) "
              f"wall={wall:.1f}s", flush=True)

    best = min(rows, key=lambda r: r["baseline_fid"])
    verdict = {
        "framework_fid_matched_nfe": float(args.framework_fid),
        "best_baseline_fid": float(best["baseline_fid"]),
        "best_baseline_num_steps": int(best["baseline_num_steps"]),
        "framework_beats_tuned_baseline": bool(args.framework_fid < best["baseline_fid"]),
        "canonical_smoke_win_margin_pct": float(
            (CANONICAL_FRAMEWORK_FID_MATCHED - CANONICAL_BASELINE_FID_MATCHED)
            / CANONICAL_BASELINE_FID_MATCHED * 100.0),
    }

    summary = {
        "kind": "gap12_mnist_tuned_baseline",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "cell": "R5c (MNIST FM, smoke ckpt)",
        "ckpt": str(ckpt.relative_to(REPO_ROOT)),
        "seed": args.seed, "n_samples": args.n_samples,
        "baseline_steps": steps_list,
        "per_baseline_steps": {str(r["baseline_num_steps"]): r for r in rows},
        "verdict": verdict,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2, default=str) + "\n")

    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as f_:
        wr = csv.writer(f_)
        wr.writerow(["baseline_num_steps", "baseline_fid",
                     "framework_fid_matched_nfe", "framework_beats_baseline",
                     "margin_framework_vs_baseline_pct", "wall_seconds"])
        for r in rows:
            wr.writerow([r["baseline_num_steps"], r["baseline_fid"],
                         r["framework_fid_matched_nfe"],
                         r["framework_beats_baseline"],
                         r["margin_framework_vs_baseline_pct"], r["wall_seconds"]])

    print("\n" + "=" * 78)
    print("HEADLINE — GAP-12 tuned baseline (R5c MNIST FM smoke)")
    print("=" * 78)
    print(f"  best baseline: steps={best['baseline_num_steps']} "
          f"FID={best['baseline_fid']:.4f}")
    print(f"  framework@matched NFE: FID={args.framework_fid:.4f} -> "
          f"{'BEATS' if verdict['framework_beats_tuned_baseline'] else 'LOSES to'} "
          f"tuned baseline")
    print(f"wrote {out_json}")
    print(f"wrote {out_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
