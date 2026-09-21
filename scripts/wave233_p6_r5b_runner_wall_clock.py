"""Wave 233 P6 — R5b CIFAR runner-based wall-clock measurement.

This script measures R5b CIFAR-10 wall-clock via the canonical
``ReInferenceRunner.run()`` path so the ``engine.run_round`` SHA-256
digest cache is actually exercised (the Wave 212 P2 harness bypasses
the engine and never goes through ``_digest_state``).

The script measures:
  1. baseline — single ``adapter.batched_inference`` call (no framework wrapper).
  2. framework_no_cache — ``ReInferenceRunner`` with ``digest_cache=None``.
  3. framework_with_cache — ``ReInferenceRunner`` with a fresh
     ``StateBundleDigestCache`` plumbed through ``Engine(digest_cache=...)``.

Output: ``verification_outputs/wave233-p6-wall-clock.{csv,json}``.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
OUT_DIR = REPO_ROOT / "verification_outputs"
PYTHON_BIN = REPO_ROOT / ".venvs" / "kanzi_venv" / "bin" / "python"

# Matched NFE = 50, n_rounds = 4 (per Wave 212 P2 brief).
NFE_TOTAL = 50
N_ROUNDS = 4
NFE_PER_ROUND = NFE_TOTAL / N_ROUNDS  # 12.5
BATCH = 64
WARMUP = 4
SEED = 0
# Pin to GPU 1 (RTX 5090) per Wave 212 P2 brief.
GPU_DEVICE = "cuda:1"

CSV_PATH = OUT_DIR / "wave233-p6-wall-clock.csv"
JSON_PATH = OUT_DIR / "wave233-p6-wall-clock.json"


# ---------------------------------------------------------------------------
# Baseline subprocess code — single batched_inference, no framework wrapper.
# ---------------------------------------------------------------------------

_BASELINE_CODE = r"""
import sys, time, json

import numpy as np

sys.path.insert(0, "/home/hugo/codes/flowa-multistep-reinference")
from adaptive_reflow.adapters.rectified_flow_cifar import RectifiedFlowCIFARAdapter

DEVICE = sys.argv[1]
BATCH = int(sys.argv[2])
WARMUP = int(sys.argv[3])
NFE = int(sys.argv[4])
SEED = int(sys.argv[5])

adapter = RectifiedFlowCIFARAdapter(num_steps=NFE, device=DEVICE)
mode = adapter._mode

for _ in range(WARMUP):
    _ = adapter.batched_inference(n_samples=BATCH, num_steps=NFE, seed=SEED)
if mode == "torch":
    import torch
    torch.cuda.synchronize()

t0 = time.perf_counter()
samples = adapter.batched_inference(n_samples=BATCH, num_steps=NFE, seed=SEED)
if mode == "torch":
    import torch
    torch.cuda.synchronize()
t1 = time.perf_counter()
forward_s = float(t1 - t0)
total_s = forward_s

result = {
    "schema": "wave233_p6_baseline_v1",
    "mode": mode,
    "device": DEVICE,
    "nfe_total": float(NFE),
    "round_count": 1,
    "nfe_per_round_mean": float(NFE),
    "wallclock_s": total_s,
    "wallclock_per_record_s": total_s / float(BATCH),
    "samples_shape": list(samples.shape),
}
sys.stdout.write("PROFILE_JSON_BEGIN\n")
sys.stdout.write(json.dumps(result, indent=2))
sys.stdout.write("\nPROFILE_JSON_END\n")
sys.stdout.flush()
"""


# ---------------------------------------------------------------------------
# Framework subprocess code via ReInferenceRunner.run() (exercises
# engine.run_round so the cache is actually engaged).
# ---------------------------------------------------------------------------

_FRAMEWORK_CODE = r"""
import sys, time, json

import numpy as np

sys.path.insert(0, "/home/hugo/codes/flowa-multistep-reinference")

USE_CACHE = sys.argv[1].lower() in ("1", "true", "yes")
DEVICE = sys.argv[2]
NFE_TOTAL = int(sys.argv[3])
N_ROUNDS = int(sys.argv[4])
NFE_PER_ROUND = NFE_TOTAL / N_ROUNDS
BATCH = int(sys.argv[5])
WARMUP = int(sys.argv[6])
SEED = int(sys.argv[7])

# Build the canonical adapter.
from adaptive_reflow.adapters.rectified_flow_cifar import RectifiedFlowCIFARAdapter
adapter = RectifiedFlowCIFARAdapter(num_steps=NFE_TOTAL, device=DEVICE)
mode = adapter._mode

# Build the canonical runner with optional cache.
from adaptive_reflow.frame.engine import Engine
from adaptive_reflow.framework.state_bundle_cache import StateBundleDigestCache
from adaptive_reflow.framework.engine import ReInferenceRunner, ReInferenceConfig

cache = StateBundleDigestCache() if USE_CACHE else None
engine = Engine(digest_cache=cache)
runner = ReInferenceRunner(adapter=adapter, engine=engine)

config = ReInferenceConfig(
    n_rounds=N_ROUNDS,
    outer_cycle_id=0,
    target_round=0,
    seed=SEED,
    channels=("xy",),
)

# Warmup: one round only.
for _ in range(WARMUP):
    _ = adapter.batched_inference(n_samples=BATCH, num_steps=int(NFE_PER_ROUND), seed=SEED)
if mode == "torch":
    import torch
    torch.cuda.synchronize()

# Timed framework run.
t_wall_0 = time.perf_counter()
result = runner.run(config)
if mode == "torch":
    import torch
    torch.cuda.synchronize()
t_wall_1 = time.perf_counter()
wallclock_s = float(t_wall_1 - t_wall_0)

# Per-round traces.
n_rounds_actual = int(result.config.n_rounds) if hasattr(result, "config") else int(len(result.round_traces))
cache_stats = cache.stats() if cache is not None else None
schema_label = (
    "wave233_p6_framework_with_cache_v1"
    if USE_CACHE
    else "wave233_p6_framework_no_cache_v1"
)

out = {
    "schema": schema_label,
    "mode": mode,
    "device": DEVICE,
    "nfe_total": float(NFE_TOTAL),
    "round_count": n_rounds_actual,
    "nfe_per_round_mean": float(NFE_PER_ROUND),
    "wallclock_s": wallclock_s,
    "wallclock_per_record_s": wallclock_s / float(BATCH),
    "sha_cache_used": bool(USE_CACHE),
    "sha_cache_stats": cache_stats,
}
sys.stdout.write("PROFILE_JSON_BEGIN\n")
sys.stdout.write(json.dumps(out, indent=2))
sys.stdout.write("\nPROFILE_JSON_END\n")
sys.stdout.flush()
"""


def _extract_payload(stdout: str) -> dict[str, Any]:
    start = stdout.find("PROFILE_JSON_BEGIN")
    if start < 0:
        raise RuntimeError("PROFILE_JSON_BEGIN marker not found")
    start = start + len("PROFILE_JSON_BEGIN") + 1
    end = stdout.find("PROFILE_JSON_END", start)
    if end < 0:
        raise RuntimeError("PROFILE_JSON_END marker not found")
    return json.loads(stdout[start:end].strip())


def _run_subprocess(code: str, args: list[str], label: str) -> dict[str, Any]:
    cmd = [str(PYTHON_BIN), "-c", code] + list(args)
    env = os.environ.copy()
    env.setdefault("PYTHONHASHSEED", "0")
    print(f"[wave233-p6] launching {label}: cmd args={args}", flush=True)
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        print(f"[wave233-p6] {label} stdout tail:\n{proc.stdout[-1500:]}", flush=True)
        print(f"[wave233-p6] {label} stderr tail:\n{proc.stderr[-3000:]}", flush=True)
        raise RuntimeError(f"{label} failed with exit code {proc.returncode}")
    payload = _extract_payload(proc.stdout)
    print(
        f"[wave233-p6] {label} wallclock_s={payload['wallclock_s']:.4f} "
        f"nfe_total={payload['nfe_total']} round_count={payload['round_count']} "
        f"mode={payload['mode']}",
        flush=True,
    )
    return payload


def _arm_record(arm: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "arm": arm,
        "n_rounds": int(payload["round_count"]),
        "wall_seconds": float(payload["wallclock_s"]),
        "FID": float("nan"),
        "sha_cache_used": bool(payload.get("sha_cache_used", False)),
    }


def _write_outputs(
    baseline_payload: dict[str, Any],
    no_cache_payload: dict[str, Any],
    with_cache_payload: dict[str, Any],
) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    baseline = _arm_record("baseline", baseline_payload)
    no_cache = _arm_record("framework_no_cache", no_cache_payload)
    with_cache = _arm_record("framework_with_cache", with_cache_payload)

    with CSV_PATH.open("w", newline="") as f:
        fieldnames = ["arm", "n_rounds", "wall_seconds", "FID", "sha_cache_used"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerow(baseline)
        w.writerow(no_cache)
        w.writerow(with_cache)
    print(f"[wave233-p6] wrote {CSV_PATH}", flush=True)

    base_wall = float(baseline["wall_seconds"])
    no_cache_wall = float(no_cache["wall_seconds"])
    with_cache_wall = float(with_cache["wall_seconds"])
    ratio_no_cache = (no_cache_wall / base_wall) if base_wall > 0.0 else 0.0
    ratio_with_cache = (with_cache_wall / base_wall) if base_wall > 0.0 else 0.0
    improvement_pct = (
        100.0 * (no_cache_wall - with_cache_wall) / no_cache_wall
        if no_cache_wall > 0.0
        else 0.0
    )
    delta_seconds = float(no_cache_wall - with_cache_wall)

    summary = {
        "schema": "wave233_p6_wall_clock_v1",
        "wave": "Wave 233 P6",
        "approach": (
            "ReInferenceRunner.run() via ReInferenceConfig with "
            "StateBundleDigestCache (Wave 233 P6 fix) toggled on/off; "
            "cuda:1 pin; matched NFE=50; 4 rounds"
        ),
        "config": {
            "device": GPU_DEVICE,
            "nfe_total": NFE_TOTAL,
            "n_rounds": N_ROUNDS,
            "nfe_per_round": NFE_PER_ROUND,
            "batch": BATCH,
            "warmup": WARMUP,
            "seed": SEED,
        },
        "arms": {
            "baseline": baseline,
            "framework_no_cache": no_cache,
            "framework_with_cache": with_cache,
        },
        "ratios": {
            "ratio_no_cache_baseline": float(ratio_no_cache),
            "ratio_with_cache_baseline": float(ratio_with_cache),
            "improvement_pct_on_framework": float(improvement_pct),
            "delta_seconds": float(delta_seconds),
        },
        "cache_stats_with_cache": with_cache_payload.get("sha_cache_stats"),
        "cache_stats_no_cache": no_cache_payload.get("sha_cache_stats"),
        "anchor": {
            "wallclock_ratio_anchor_24_6x": (
                "Wave 191 P2 / Wave 209 P8 anchor at N=1000: "
                "baseline 37.83 ms vs framework 930.52 ms = 24.60x "
                "at matched NFE=50 (cited in wave209-p8-experiment-setup.md "
                "and wave217-p3-24x-fix.md)"
            ),
        },
    }
    JSON_PATH.write_text(json.dumps(summary, indent=2))
    print(f"[wave233-p6] wrote {JSON_PATH}", flush=True)
    return summary


def main() -> int:
    print("=== Wave 233 P6 R5b CIFAR-10 SHA-256 cache (runner-based) wall-clock measurement ===", flush=True)
    print(f"[wave233-p6] repo_root={REPO_ROOT}", flush=True)
    print(f"[wave233-p6] python_bin={PYTHON_BIN}", flush=True)
    print(
        f"[wave233-p6] config: DEVICE={GPU_DEVICE} NFE_TOTAL={NFE_TOTAL} "
        f"N_ROUNDS={N_ROUNDS} NFE_PER_ROUND={NFE_PER_ROUND} BATCH={BATCH} "
        f"WARMUP={WARMUP} SEED={SEED}",
        flush=True,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[wave233-p6] === R5b baseline sub-sweep (GPU 1) ===", flush=True)
    baseline_payload = _run_subprocess(
        _BASELINE_CODE,
        [GPU_DEVICE, str(BATCH), str(WARMUP), str(NFE_TOTAL), str(SEED)],
        label="baseline",
    )

    print("\n[wave233-p6] === R5b framework sub-sweep WITHOUT cache (GPU 1) ===", flush=True)
    no_cache_payload = _run_subprocess(
        _FRAMEWORK_CODE,
        ["0", GPU_DEVICE, str(NFE_TOTAL), str(N_ROUNDS), str(BATCH), str(WARMUP), str(SEED)],
        label="framework_no_cache",
    )

    print("\n[wave233-p6] === R5b framework sub-sweep WITH cache (GPU 1) ===", flush=True)
    with_cache_payload = _run_subprocess(
        _FRAMEWORK_CODE,
        ["1", GPU_DEVICE, str(NFE_TOTAL), str(N_ROUNDS), str(BATCH), str(WARMUP), str(SEED)],
        label="framework_with_cache",
    )

    summary = _write_outputs(baseline_payload, no_cache_payload, with_cache_payload)
    print(
        f"\n[wave233-p6] ratio_no_cache={summary['ratios']['ratio_no_cache_baseline']:.4f} "
        f"ratio_with_cache={summary['ratios']['ratio_with_cache_baseline']:.4f} "
        f"improvement_pct={summary['ratios']['improvement_pct_on_framework']:.2f}% "
        f"delta_s={summary['ratios']['delta_seconds']:.4f}",
        flush=True,
    )
    print(f"[wave233-p6] cache stats (with cache): {summary['cache_stats_with_cache']}", flush=True)
    print("\n=== Wave 233 P6 complete ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())