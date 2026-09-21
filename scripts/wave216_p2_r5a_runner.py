"""Wave 216 P2 — Run two_moons for seeds {43, 44, 45} via run_sota_2d_experiment.

Imports :mod:`tools.run_sota_2d_experiment` and calls its :func:`_per_target_runs`
helper with the explicit seed list, writing CSVs to ``/tmp/wave216_p2_r5a/``.

This is a one-shot driver for the R5a seed-extension; it does NOT modify
the existing r4-survey/ tree or the wave195_p2 / wave209_p6 R-level power
tables.
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

OUT_DIR = Path("/tmp/wave216_p2_r5a")
NEW_SEEDS = [43, 44, 45]

# Match Wave 209 P6 setup: 1000 samples/round, 5 multi-round rounds (faster than
# the canonical 20 to fit time budget; tail-5 still applies for 5-round runs).
N_SAMPLES = 1000
N_ROUNDS = 5
TRAJECTORIES_PER_ROUND = 50
ENDPOINTS_PER_TRAJECTORY = 20
TARGET = "two_moons"


def main() -> int:
    """Run two_moons baseline + 4 schedulers for seeds 43, 44, 45."""
    import run_sota_2d_experiment as rse  # type: ignore[import-not-found]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(
        f"[wave216_p2_r5a_runner] === seeds={NEW_SEEDS} target={TARGET} "
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
        f"[wave216_p2_r5a_runner] baseline seed_mean_W2 = {baseline_seed_mean:.5f} "
        f"(wall={wall:.1f}s)",
        flush=True,
    )
    for name in rse.SCHEDULER_NAMES:
        sched = run["scheduler_runs"][name]
        print(
            f"[wave216_p2_r5a_runner] {name}: seed_mean_W2 = "
            f"{float(sched['seed_mean_w2']):.5f} ± "
            f"{float(sched['seed_std_w2']):.5f}",
            flush=True,
        )

    print(f"[wave216_p2_r5a_runner] Wrote per-(scheduler, seed) CSVs to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())