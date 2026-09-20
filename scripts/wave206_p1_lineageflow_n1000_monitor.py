#!/usr/bin/env python3
"""Wave 206 P1 LineageFlow N=1000 sweep monitor.

Reads incremental JSONL outputs from verification_outputs/wave206-p1-lineageflow-n1000/
and reports progress. Re-invocable; safe to run multiple times.

Outputs per-arm record counts + GPU memory + ETA estimate.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SWEEP_OUT = ROOT / "verification_outputs" / "wave206-p1-lineageflow-n1000"
LOG_PATH = Path("/tmp/w206/p1-sweep.log")
EXPECTED_N = 1000
GPU_INDEX = 0


def count_metrics(arm_dir: Path) -> int:
    """Count per-record lines in metrics.jsonl."""
    p = arm_dir / "metrics.jsonl"
    if not p.exists():
        return 0
    n = 0
    with p.open() as f:
        for _ in f:
            n += 1
    return n


def count_sc(arm_dir: Path) -> int:
    """Count self-consistency jsonl lines."""
    p = arm_dir / "sc" / "self_consistency.jsonl"
    if not p.exists():
        return 0
    n = 0
    with p.open() as f:
        for _ in f:
            n += 1
    return n


def gpu_mem_mib() -> int:
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits",
         "-i", str(GPU_INDEX)],
        capture_output=True, text=True, timeout=5,
    ).stdout.strip()
    try:
        return int(out.splitlines()[0])
    except Exception:
        return -1


def sweep_alive() -> bool:
    out = subprocess.run(
        ["pgrep", "-f", "run_lineageflow_n1000_foldability_omegafold.py"],
        capture_output=True, text=True, timeout=5,
    ).stdout.strip()
    return bool(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="Print one snapshot and exit")
    ap.add_argument("--interval", type=int, default=60, help="Polling interval (s)")
    args = ap.parse_args()

    t0 = time.time()
    print(f"# Wave 206 P1 LineageFlow N=1000 monitor (start={time.strftime('%H:%M:%S')})")
    while True:
        snap_t = time.time()
        alive = sweep_alive()
        baseline = count_metrics(SWEEP_OUT / "baseline")
        framework = count_metrics(SWEEP_OUT / "framework")
        baseline_sc = count_sc(SWEEP_OUT / "baseline")
        framework_sc = count_sc(SWEEP_OUT / "framework")
        gpu_mib = gpu_mem_mib()
        elapsed_s = snap_t - t0
        # Naive ETA: assume 2.5 s/record per W158
        eta_s = ((EXPECTED_N - baseline) + (EXPECTED_N - framework)) * 2.5
        baseline_pct = 100.0 * baseline / EXPECTED_N
        framework_pct = 100.0 * framework / EXPECTED_N
        print(
            f"{time.strftime('%H:%M:%S')} "
            f"alive={int(alive)} "
            f"baseline_metrics={baseline}/{EXPECTED_N} ({baseline_pct:.1f}%) "
            f"framework_metrics={framework}/{EXPECTED_N} ({framework_pct:.1f}%) "
            f"baseline_sc={baseline_sc} "
            f"framework_sc={framework_sc} "
            f"gpu0={gpu_mib}MiB "
            f"elapsed={int(elapsed_s)}s "
            f"eta_naive={int(eta_s)}s"
        )
        if not alive and baseline >= EXPECTED_N and framework >= EXPECTED_N:
            print("# BOTH ARMS COMPLETE — sweep process exited cleanly")
            break
        if not alive:
            print("# sweep process not running — check log for early exit")
            break
        if args.once:
            break
        # Sleep with -W to satisfy our monitoring helper; keep simple
        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    main()
