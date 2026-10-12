#!/usr/bin/env python3
"""GAP-12 (R5a) — tuned-baseline fairness check on the 2D Two-Moons cell.

`todo.json` GAP-12-BASELINE asks for "matched-NFE + at least one tuned
baseline per headline cell (straw-man exposure)".

The R5a cell (2D Two Moons rectified-flow ablation) reports a large
framework-WINS: baseline W2 = 2.85 -> framework W2 = 0.62 (Δ ≈ −78 %,
`docs/r4-survey/g1_deep_dive_q3_2026.json`, row ``twodim_fm_2d_ablation``).

The straw-man test: the *baseline* is a single-pass cosine solve whose only
compute knob is the adapter's ``num_steps`` (default ``TWODIM_FM_NUM_STEPS =
100``).  This driver gives the baseline MORE solver steps
(``num_steps in {100, 200, 400}``) and reports whether the baseline's best W2
still loses to the framework's 0.62.  If it does, the R5a win is **not** a
compute artifact.

CPU-only (the ``TwoDimFMAdapter`` is numpy-backed).  Reuses the canonical
runner's helpers (``tools.run_sota_2d_experiment``) so the metric
(``_wasserstein_2d`` → ``mean_w2_tail``) is identical to the headline.

Usage::

    python scripts/gap12_2d_tuned_baseline.py \\
        --steps 100,200,400 --target two_moons --seed 42

Writes ``verification_outputs/gap12-2d-tuned-baseline.{json,csv}``.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "verification_outputs"

# Canonical framework W2 for the R5a two-moons ablation (best scheduler,
# from docs/r4-survey/g1_deep_dive_q3_2026.json row twodim_fm_2d_ablation).
CANONICAL_FRAMEWORK_W2 = 0.62
CANONICAL_BASELINE_W2 = 2.85


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default="100,200,400")
    ap.add_argument("--target", default="two_moons")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--trajectories-per-round", type=int, default=50)
    ap.add_argument("--endpoints-per-trajectory", type=int, default=20)
    ap.add_argument("--framework-w2", type=float, default=CANONICAL_FRAMEWORK_W2)
    args = ap.parse_args()

    steps_list = [int(s) for s in args.steps.split(",")]

    # Import the canonical runner helpers (same metric path as the headline).
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from tools.run_sota_2d_experiment import (
        _aggregate,
        _build_cosine_scheduler,
        _drive_batched,
        _make_evaluator,
        _weights_path,
    )

    weights = _weights_path(args.target)
    if not weights.exists():
        raise SystemExit(f"weights_not_found:{weights}")

    print(f"[gap12-2d] target={args.target} steps={steps_list} seed={args.seed} "
          f"traj/round={args.trajectories_per_round} "
          f"endpoints/traj={args.endpoints_per_trajectory} "
          f"framework_w2={args.framework_w2}", flush=True)

    rows: list[dict] = []
    for steps in steps_list:
        adapter = TwoDimFMAdapter(
            weights_path=weights, target=args.target, num_steps=int(steps),
        )
        scheduler = _build_cosine_scheduler(rounds=1)
        evaluator = _make_evaluator(args.target)
        t0 = time.perf_counter()
        metrics, _endpoints, _wall = _drive_batched(
            adapter=adapter, scheduler=scheduler, seed=int(args.seed), rounds=1,
            trajectories_per_round=int(args.trajectories_per_round),
            endpoints_per_trajectory=int(args.endpoints_per_trajectory),
            selection_evaluator=evaluator,
        )
        wall = time.perf_counter() - t0
        agg = _aggregate(metrics)
        w2 = float(agg["mean_w2_tail"])
        beats = bool(w2 < args.framework_w2)
        rows.append({
            "baseline_num_steps": int(steps),
            "baseline_w2": w2,
            "wall_seconds": float(wall),
            "framework_w2": float(args.framework_w2),
            "baseline_beats_framework": beats,
        })
        print(f"  [baseline num_steps={steps}] W2={w2:.4f} "
              f"({'BEATS' if beats else 'LOSES to'} framework@{args.framework_w2:.4f}) "
              f"wall={wall:.1f}s", flush=True)

    best = min(rows, key=lambda r: r["baseline_w2"])
    verdict = {
        "framework_w2": float(args.framework_w2),
        "best_baseline_w2": float(best["baseline_w2"]),
        "best_baseline_num_steps": int(best["baseline_num_steps"]),
        "framework_beats_tuned_baseline": bool(args.framework_w2 < best["baseline_w2"]),
        "canonical_baseline_w2": float(CANONICAL_BASELINE_W2),
    }

    summary = {
        "kind": "gap12_2d_tuned_baseline",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "cell": "R5a (2D Two Moons RF ablation)",
        "target": args.target, "seed": args.seed,
        "steps": steps_list,
        "per_baseline_steps": {str(r["baseline_num_steps"]): r for r in rows},
        "verdict": verdict,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = OUT_DIR / "gap12-2d-tuned-baseline.json"
    out_json.write_text(json.dumps(summary, indent=2, default=str) + "\n")
    out_csv = OUT_DIR / "gap12-2d-tuned-baseline.csv"
    with out_csv.open("w", newline="") as f_:
        wr = csv.writer(f_)
        wr.writerow(["baseline_num_steps", "baseline_w2", "framework_w2",
                     "baseline_beats_framework", "wall_seconds"])
        for r in rows:
            wr.writerow([r["baseline_num_steps"], r["baseline_w2"],
                         r["framework_w2"], r["baseline_beats_framework"],
                         r["wall_seconds"]])

    print("\n" + "=" * 78)
    print("HEADLINE — GAP-12 tuned baseline (R5a 2D Two Moons)")
    print("=" * 78)
    print(f"  best baseline: steps={best['baseline_num_steps']} "
          f"W2={best['baseline_w2']:.4f}")
    print(f"  framework: W2={args.framework_w2:.4f} -> "
          f"{'BEATS' if verdict['framework_beats_tuned_baseline'] else 'LOSES to'} "
          f"tuned baseline")
    print(f"wrote {out_json}")
    print(f"wrote {out_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
