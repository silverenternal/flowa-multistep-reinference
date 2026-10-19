"""GAP-52 — apply the pre-registered dev-screen selection rule.

Reads the four dev arms produced by ``/tmp/run_gap52_dev.sh`` (C0, C1, C2,
C3), computes the paired ``fg_dev`` delta per seed, and applies
§4 of ``docs/audit/gap52-charge-channel-preregistration.md``:

  1. compute the paired mean delta for each arm;
  2. drop any arm whose mean delta is not below C0's mean delta;
  3. among survivors, pick the lowest mean delta;
  4. if no arm beats C0, return ``null`` (stop; no confirmatory run).

The confirmatory decision rule lives in the same pre-registration and is
applied by ``--confirm`` once the winner has been run on seeds 2000..2490.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gap43_blend_positive_analysis import (  # noqa: E402
    _load_arm,
    bootstrap_dz_ci,
    paired_stats,
)

ARMS = ("C0_continuous_flat", "C1_categorical_flat",
        "C2_categorical_perchannel", "C3_continuous_perchannel")
REFERENCE = "C0_continuous_flat"


def _seeds(directory: Path) -> list[int]:
    seeds = []
    for path in sorted(directory.glob("flowmol3_n1000_framework_wave338_p5_seed*.json")):
        seeds.append(int(path.stem.rsplit("seed", 1)[1]))
    return seeds


def _deltas(directory: Path, seeds: list[int], metric: str) -> tuple[np.ndarray, list[int]]:
    values = []
    used = []
    for seed in seeds:
        bl = _load_arm(directory, "baseline", seed)
        fw = _load_arm(directory, "framework", seed)
        if bl is None or fw is None:
            continue
        values.append(float(fw[metric]) - float(bl[metric]))
        used.append(seed)
    return np.asarray(values, dtype=np.float64), used


def screen(dev_dir: Path) -> dict[str, Any]:
    seeds = _seeds(dev_dir / REFERENCE)
    if len(seeds) != 10:
        raise SystemExit(f"expected 10 dev seeds under {REFERENCE}, got {len(seeds)}")
    rows: dict[str, Any] = {}
    for arm in ARMS:
        deltas, used = _deltas(dev_dir / arm, seeds, "fg_dev")
        if len(used) != len(seeds):
            raise SystemExit(f"{arm}: missing runs ({len(used)}/{len(seeds)})")
        stats = paired_stats(deltas)
        stats["dz_bootstrap_ci95"] = list(bootstrap_dz_ci(deltas))
        stats["seeds"] = used
        stats["mean_pb_validity_delta"] = float(
            _deltas(dev_dir / arm, seeds, "pb_validity_pct")[0].mean()
        )
        rows[arm] = stats
    reference_mean = float(rows[REFERENCE]["mean"])
    survivors = [
        arm for arm in ARMS
        if arm != REFERENCE and float(rows[arm]["mean"]) < reference_mean
    ]
    winner = min(survivors, key=lambda a: float(rows[a]["mean"])) if survivors else None
    return {
        "kind": "gap52_dev_screen",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "dev_seeds": seeds,
        "reference_arm": REFERENCE,
        "reference_mean_delta": reference_mean,
        "arms": rows,
        "survivors": survivors,
        "winner": winner,
        "proceed_to_confirm": winner is not None,
    }


def confirm(confirm_dir: Path, winner_arm: str) -> dict[str, Any]:
    """Apply §6 of the pre-registration to the 50-seed confirmatory block."""
    winner_dir = confirm_dir / winner_arm
    reference_dir = confirm_dir / REFERENCE
    seeds = _seeds(winner_dir)
    if len(seeds) != 50:
        raise SystemExit(f"expected 50 confirm seeds under {winner_arm}, got {len(seeds)}")

    winner_deltas, used = _deltas(winner_dir, seeds, "fg_dev")
    ref_deltas, _ = _deltas(reference_dir, seeds, "fg_dev")
    if len(used) != 50:
        raise SystemExit(f"{winner_arm}: missing runs ({len(used)}/50)")

    stats = paired_stats(winner_deltas, alpha=0.05)
    stats["dz_bootstrap_ci95"] = list(bootstrap_dz_ci(winner_deltas))
    ref_stats = paired_stats(ref_deltas, alpha=0.05)

    # Tuned gate: 10 seeds, framework NFE=250 vs best-of baseline 250/1000.
    # Each seed lives in its own directory (the driver writes one
    # baseline file per run, so the two budgets cannot share a dir).
    tuned_dir = confirm_dir / "tuned_gate"
    tuned = []
    for seed_dir in sorted(tuned_dir.glob("seed*")):
        seed = int(seed_dir.name.removeprefix("seed"))
        fw = _load_arm(seed_dir, "framework", seed)
        bl250 = _load_arm(seed_dir, "baseline", seed)
        bl1000_dir = seed_dir / "baseline_nfe1000"
        bl1000 = _load_arm(bl1000_dir, "baseline", seed)
        if fw is None or bl250 is None or bl1000 is None:
            continue
        best = min(float(bl250["fg_dev"]), float(bl1000["fg_dev"]))
        tuned.append(float(fw["fg_dev"]) - best)
    tuned_arr = np.asarray(tuned, dtype=np.float64)
    gate_mean = float(tuned_arr.mean()) if tuned_arr.size else float("nan")
    gate_passes = bool(tuned_arr.size == 10 and gate_mean < 0.0)

    mean = float(stats["mean"])
    p = float(stats["p_value"])
    dz = float(stats["cohens_dz"])
    beats_reference = mean < float(ref_stats["mean"])
    conditions = {
        "mean_negative": mean < 0.0,
        "p_below_0.05": p < 0.05,
        "dz_at_floor": abs(dz) >= 0.5,
        "tuned_gate_passes": gate_passes,
        "beats_as_wired": beats_reference,
    }
    if all(conditions.values()):
        verdict = "POSITIVE"
    elif stats["dz_bootstrap_ci95"][1] < -0.5:
        verdict = "BOUNDED NEGATIVE"
    else:
        verdict = "INCONCLUSIVE"

    return {
        "kind": "gap52_confirm",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "winner_arm": winner_arm,
        "seeds": used,
        "primary": stats,
        "reference": ref_stats,
        "tuned_gate": {
            "n": int(tuned_arr.size),
            "mean_delta_tuned": gate_mean,
            "passes": gate_passes,
        },
        "conditions": conditions,
        "verdict": verdict,
        "exploratory_pb_validity": paired_stats(
            _deltas(winner_dir, seeds, "pb_validity_pct")[0], alpha=0.05
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dev-dir", type=Path,
                    default=REPO_ROOT / "verification_outputs/gap52-charge-channel/dev")
    ap.add_argument("--confirm-dir", type=Path, default=None)
    ap.add_argument("--winner", default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    if args.confirm_dir is not None:
        if args.winner is None:
            raise SystemExit("--winner is required with --confirm-dir")
        summary = confirm(args.confirm_dir, args.winner)
        out = args.out or (args.confirm_dir / "summary.json")
    else:
        summary = screen(args.dev_dir)
        out = args.out or (args.dev_dir / "summary.json")

    out.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "arms"}, indent=2))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
