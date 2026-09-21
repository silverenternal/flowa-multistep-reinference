"""Wave 233 P4 — R5a Two Moons seed expansion (n=10 -> n=30).

Run two_moons baseline + 4 schedulers for seeds {10, 11, ..., 29} (20 new
seeds, expanding the existing n=10 set to n=30). Mirrors the wave216
P2 R5a runner setup (1000 samples/round, 5 rounds, 50 traj, 20 endpoints).

Writes per-(scheduler, seed) CSVs to docs/r4-survey/.

Reads via wave233_p4_r5a_extended.py (separate aggregation step) which
loads both the existing /tmp/wave209_p6_r5a/ + /tmp/wave216_p2_r5a/ data
and the new docs/r4-survey/ files.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools"))

OUT_DIR = REPO_ROOT / "docs" / "r4-survey"
NEW_SEEDS = list(range(10, 30))  # seeds 10..29 inclusive = 20 new seeds

N_SAMPLES = 1000
N_ROUNDS = 5
TRAJECTORIES_PER_ROUND = 50
ENDPOINTS_PER_TRAJECTORY = 20
TARGET = "two_moons"


def main() -> int:
    """Run two_moons baseline + 4 schedulers for seeds 10..29."""
    import run_sota_2d_experiment as rse  # type: ignore[import-not-found]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(
        f"[wave233_p4_r5a_expansion] === seeds={NEW_SEEDS} target={TARGET} "
        f"n_rounds={N_ROUNDS} n_samples={N_SAMPLES} ===",
        flush=True,
    )

    started = time.perf_counter()
    run = rse._per_target_runs(
        target=TARGET,
        seeds=NEW_SEEDS,
        n_rounds=N_ROUNDS,
        n_samples=N_SAMPLES,
        trajectories_per_round=TRAJECTORIES_PER_ROUND,
        endpoints_per_trajectory=ENDPOINTS_PER_TRAJECTORY,
        output_dir=OUT_DIR,
    )
    wall = float(time.perf_counter() - started)

    baseline_seed_mean = float(run["baseline"]["seed_mean_w2"])
    print(
        f"[wave233_p4_r5a_expansion] baseline seed_mean_W2 = {baseline_seed_mean:.5f} "
        f"(wall={wall:.1f}s)",
        flush=True,
    )
    for name in rse.SCHEDULER_NAMES:
        sched = run["scheduler_runs"][name]
        print(
            f"[wave233_p4_r5a_expansion] {name}: seed_mean_W2 = "
            f"{float(sched['seed_mean_w2']):.5f} ± "
            f"{float(sched['seed_std_w2']):.5f}",
            flush=True,
        )

    print(f"[wave233_p4_r5a_expansion] Wrote per-(scheduler, seed) CSVs to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())