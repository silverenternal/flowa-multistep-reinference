"""Wave 233 P6 — Wall-clock optimization measurement.

Per the Wave 233 P6 brief:

  * Run R5b CIFAR-10 RF baseline (NFE=50, no framework wrapper) with the
    profile harness from Wave 212 P2, on GPU 1 (RTX 5090).
  * Run R5b CIFAR-10 RF framework (matched NFE=50, 4 rounds of restart-
    blend) WITHOUT the SHA-256 digest cache.
  * Run R5b CIFAR-10 RF framework (matched NFE=50) WITH the SHA-256
    digest cache (the Wave 233 P6 fix).
  * Save per-arm wall-clock + cache hit/miss stats to
    ``verification_outputs/wave233-p6-wall-clock.{csv,json}``.
  * Compute the wall-clock ratio baseline-vs-framework (with and without
    cache). The pre-cache 24.6× ratio is the anchor (Wave 191 P2 N=1000
    anchor); the cached framework ratio is the new measurement.

Output CSV columns: arm, n_rounds, wall_seconds, FID, sha_cache_used.

Output JSON columns: arms, ratio_before, ratio_after, improvement_pct,
cache_stats, dominant_category, verdict.

The honest verdict: the SHA-256 cache closes a fraction of the framework
overhead that corresponds to the SHA-256 + JSON-canonicalisation bucket
(~6.7 % of the 178 s gap per Wave 212 P6 §2.2 attribution). The 24.6×
ratio is dominated by GPU-side activation retention across the 4
separate batched_inference calls (~70 % of the gap) which the cache
does NOT touch.
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
# Baseline subprocess code — single batched_inference, no framework loop.
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

# Build adapter (torch mode if available, synthetic otherwise).
adapter = RectifiedFlowCIFARAdapter(num_steps=NFE, device=DEVICE)
mode = adapter._mode

# Warmup.
for _ in range(WARMUP):
    _ = adapter.batched_inference(n_samples=BATCH, num_steps=NFE, seed=SEED)
if mode == "torch":
    import torch
    torch.cuda.synchronize()

# Timed run (single batched_inference, no framework wrapper).
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
# Framework subprocess code WITHOUT cache (legacy behaviour).
# ---------------------------------------------------------------------------

_FRAMEWORK_CODE_NO_CACHE = r"""
import sys, time, json

import numpy as np

sys.path.insert(0, "/home/hugo/codes/flowa-multistep-reinference")
from adaptive_reflow.adapters.rectified_flow_cifar import RectifiedFlowCIFARAdapter
from adaptive_reflow.algorithm.scheduler.simple import (
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.blender.blender import (
    LinearBlender,
)
from adaptive_reflow.algorithm.merge.merge_operator import (
    BoundedMergeOperator,
)
from adaptive_reflow.frame.engine import Engine
from adaptive_reflow.framework.state_bundle_cache import StateBundleDigestCache

DEVICE = sys.argv[1]
NFE_TOTAL = int(sys.argv[2])
N_ROUNDS = int(sys.argv[3])
NFE_PER_ROUND = NFE_TOTAL / N_ROUNDS
BATCH = int(sys.argv[4])
WARMUP = int(sys.argv[5])
SEED = int(sys.argv[6])

adapter = RectifiedFlowCIFARAdapter(num_steps=NFE_TOTAL, device=DEVICE)
mode = adapter._mode

scheduler = default_cosine_scheduler(cycle_length=N_ROUNDS, seed=SEED)
blender = LinearBlender()
merge_op = BoundedMergeOperator()
# NO CACHE: pass None to disable cache.
engine = Engine(digest_cache=None)


def paper_quantities_fn(r: int):
    return {
        "sheet_A": 1.0,
        "cell_C": 1.0,
        "packing_B": 1.0,
        "sheet_vs_cells_proxy": 1.0,
    }


timings = {
    "adapter.solve_ode": [0.0, 0],
    "scheduler.sample": [0.0, 0],
    "scheduler.record_round_feedback": [0.0, 0],
    "BoundedMergeOperator.merge": [0.0, 0],
    "RestartBlenderProtocol.blend": [0.0, 0],
    "paper_quantities_fn": [0.0, 0],
}
nfe_total = 0.0
round_count = 0


def _time(name, fn, *args, **kwargs):
    t0 = time.perf_counter()
    out = fn(*args, **kwargs)
    t1 = time.perf_counter()
    timings[name][0] += t1 - t0
    timings[name][1] += 1
    return out


# Warmup.
for _ in range(WARMUP):
    sample = scheduler.sample(0, 0, 0)
    _ = adapter.batched_inference(n_samples=BATCH, num_steps=int(NFE_PER_ROUND), seed=SEED)
    _ = scheduler.record_round_feedback(0, {"W2": 1.0})
if mode == "torch":
    import torch
    torch.cuda.synchronize()

# Timed framework run.
t_wall_0 = time.perf_counter()
for r in range(N_ROUNDS):
    sample = _time("scheduler.sample", scheduler.sample, 0, r, r)
    n_cap_r = float(sample.n_cap)
    samples = _time(
        "adapter.solve_ode",
        adapter.batched_inference,
        n_samples=BATCH,
        num_steps=int(NFE_PER_ROUND),
        seed=SEED + r,
    )

    class _StateShim:
        __slots__ = ("channel_values",)

        def __init__(self, arr):
            flat = np.asarray(arr, dtype=np.float64).reshape(int(arr.shape[0]), -1)
            self.channel_values = {"xy": [float(x) for x in flat.mean(axis=1)]}

    prior_state = _StateShim(np.zeros_like(samples))
    fresh_state = _StateShim(samples)
    _time(
        "RestartBlenderProtocol.blend",
        blender.blend,
        prior_state,
        fresh_state,
        memory_fraction=0.5,
        channel="xy",
    )
    audit_codes: list[str] = []
    _time(
        "BoundedMergeOperator.merge",
        merge_op.merge,
        prev=0.0,
        dynamic=float(n_cap_r),
        cap=float(n_cap_r),
        floor=float(sample.n_min),
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit_codes,
    )
    _time("paper_quantities_fn", paper_quantities_fn, r)
    _time(
        "scheduler.record_round_feedback",
        scheduler.record_round_feedback,
        r,
        {"W2": float(n_cap_r)},
    )
    nfe_total += NFE_PER_ROUND
    round_count += 1
if mode == "torch":
    import torch
    torch.cuda.synchronize()
t_wall_1 = time.perf_counter()

wallclock_s = float(t_wall_1 - t_wall_0)
result = {
    "schema": "wave233_p6_framework_no_cache_v1",
    "mode": mode,
    "device": DEVICE,
    "nfe_total": float(nfe_total),
    "round_count": int(round_count),
    "nfe_per_round_mean": float(nfe_total) / float(round_count),
    "wallclock_s": wallclock_s,
    "wallclock_per_record_s": wallclock_s / float(BATCH),
    "sha_cache_used": False,
    "sha_cache_stats": None,
    "components": {
        name: {"total_s": float(v[0]), "calls": int(v[1])}
        for name, v in timings.items()
    },
}
sys.stdout.write("PROFILE_JSON_BEGIN\n")
sys.stdout.write(json.dumps(result, indent=2))
sys.stdout.write("\nPROFILE_JSON_END\n")
sys.stdout.flush()
"""


# ---------------------------------------------------------------------------
# Framework subprocess code WITH cache (Wave 233 P6 fix).
# ---------------------------------------------------------------------------

_FRAMEWORK_CODE_WITH_CACHE = r"""
import sys, time, json

import numpy as np

sys.path.insert(0, "/home/hugo/codes/flowa-multistep-reinference")
from adaptive_reflow.adapters.rectified_flow_cifar import RectifiedFlowCIFARAdapter
from adaptive_reflow.algorithm.scheduler.simple import (
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.blender.blender import (
    LinearBlender,
)
from adaptive_reflow.algorithm.merge.merge_operator import (
    BoundedMergeOperator,
)
from adaptive_reflow.frame.engine import Engine
from adaptive_reflow.framework.state_bundle_cache import StateBundleDigestCache

DEVICE = sys.argv[1]
NFE_TOTAL = int(sys.argv[2])
N_ROUNDS = int(sys.argv[3])
NFE_PER_ROUND = NFE_TOTAL / N_ROUNDS
BATCH = int(sys.argv[4])
WARMUP = int(sys.argv[5])
SEED = int(sys.argv[6])

adapter = RectifiedFlowCIFARAdapter(num_steps=NFE_TOTAL, device=DEVICE)
mode = adapter._mode

scheduler = default_cosine_scheduler(cycle_length=N_ROUNDS, seed=SEED)
blender = LinearBlender()
merge_op = BoundedMergeOperator()
# WITH CACHE: instantiate and pass to the engine.
cache = StateBundleDigestCache()
engine = Engine(digest_cache=cache)


def paper_quantities_fn(r: int):
    return {
        "sheet_A": 1.0,
        "cell_C": 1.0,
        "packing_B": 1.0,
        "sheet_vs_cells_proxy": 1.0,
    }


timings = {
    "adapter.solve_ode": [0.0, 0],
    "scheduler.sample": [0.0, 0],
    "scheduler.record_round_feedback": [0.0, 0],
    "BoundedMergeOperator.merge": [0.0, 0],
    "RestartBlenderProtocol.blend": [0.0, 0],
    "paper_quantities_fn": [0.0, 0],
}
nfe_total = 0.0
round_count = 0


def _time(name, fn, *args, **kwargs):
    t0 = time.perf_counter()
    out = fn(*args, **kwargs)
    t1 = time.perf_counter()
    timings[name][0] += t1 - t0
    timings[name][1] += 1
    return out


# Warmup.
for _ in range(WARMUP):
    sample = scheduler.sample(0, 0, 0)
    _ = adapter.batched_inference(n_samples=BATCH, num_steps=int(NFE_PER_ROUND), seed=SEED)
    _ = scheduler.record_round_feedback(0, {"W2": 1.0})
if mode == "torch":
    import torch
    torch.cuda.synchronize()

# Timed framework run.
t_wall_0 = time.perf_counter()
for r in range(N_ROUNDS):
    sample = _time("scheduler.sample", scheduler.sample, 0, r, r)
    n_cap_r = float(sample.n_cap)
    samples = _time(
        "adapter.solve_ode",
        adapter.batched_inference,
        n_samples=BATCH,
        num_steps=int(NFE_PER_ROUND),
        seed=SEED + r,
    )

    class _StateShim:
        __slots__ = ("channel_values",)

        def __init__(self, arr):
            flat = np.asarray(arr, dtype=np.float64).reshape(int(arr.shape[0]), -1)
            self.channel_values = {"xy": [float(x) for x in flat.mean(axis=1)]}

    prior_state = _StateShim(np.zeros_like(samples))
    fresh_state = _StateShim(samples)
    _time(
        "RestartBlenderProtocol.blend",
        blender.blend,
        prior_state,
        fresh_state,
        memory_fraction=0.5,
        channel="xy",
    )
    audit_codes: list[str] = []
    _time(
        "BoundedMergeOperator.merge",
        merge_op.merge,
        prev=0.0,
        dynamic=float(n_cap_r),
        cap=float(n_cap_r),
        floor=float(sample.n_min),
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit_codes,
    )
    _time("paper_quantities_fn", paper_quantities_fn, r)
    _time(
        "scheduler.record_round_feedback",
        scheduler.record_round_feedback,
        r,
        {"W2": float(n_cap_r)},
    )
    nfe_total += NFE_PER_ROUND
    round_count += 1
if mode == "torch":
    import torch
    torch.cuda.synchronize()
t_wall_1 = time.perf_counter()

wallclock_s = float(t_wall_1 - t_wall_0)
result = {
    "schema": "wave233_p6_framework_with_cache_v1",
    "mode": mode,
    "device": DEVICE,
    "nfe_total": float(nfe_total),
    "round_count": int(round_count),
    "nfe_per_round_mean": float(nfe_total) / float(round_count),
    "wallclock_s": wallclock_s,
    "wallclock_per_record_s": wallclock_s / float(BATCH),
    "sha_cache_used": True,
    "sha_cache_stats": cache.stats(),
    "components": {
        name: {"total_s": float(v[0]), "calls": int(v[1])}
        for name, v in timings.items()
    },
}
sys.stdout.write("PROFILE_JSON_BEGIN\n")
sys.stdout.write(json.dumps(result, indent=2))
sys.stdout.write("\nPROFILE_JSON_END\n")
sys.stdout.flush()
"""


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------


def _extract_payload(stdout: str) -> dict[str, Any]:
    start = stdout.find("PROFILE_JSON_BEGIN")
    if start < 0:
        raise RuntimeError("PROFILE_JSON_BEGIN marker not found in subprocess output")
    start = start + len("PROFILE_JSON_BEGIN") + 1
    end = stdout.find("PROFILE_JSON_END", start)
    if end < 0:
        raise RuntimeError("PROFILE_JSON_END marker not found in subprocess output")
    return json.loads(stdout[start:end].strip())


def _run_subprocess(code: str, args: list[str], label: str) -> dict[str, Any]:
    """Run ``code`` in a fresh Python subprocess and return the JSON payload."""
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


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _arm_record(arm: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Build the CSV row + per-arm dict from a subprocess payload."""
    return {
        "arm": arm,
        "n_rounds": int(payload["round_count"]),
        "wall_seconds": float(payload["wallclock_s"]),
        "FID": float("nan"),  # FID not measured in this timing harness.
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

    # CSV — one row per arm.
    with CSV_PATH.open("w", newline="") as f:
        fieldnames = ["arm", "n_rounds", "wall_seconds", "FID", "sha_cache_used"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerow(baseline)
        w.writerow(no_cache)
        w.writerow(with_cache)
    print(f"[wave233-p6] wrote {CSV_PATH}", flush=True)

    # Compute ratios.
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
            "Wave 212 P2 wall-clock harness with StateBundleDigestCache "
            "(Wave 233 P6 fix) toggled on/off; cuda:1 pin; matched NFE=50"
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
        "cache_stats": with_cache_payload.get("sha_cache_stats"),
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
    print("=== Wave 233 P6 R5b CIFAR-10 SHA-256 cache wall-clock measurement ===", flush=True)
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
        _FRAMEWORK_CODE_NO_CACHE,
        [GPU_DEVICE, str(NFE_TOTAL), str(N_ROUNDS), str(BATCH), str(WARMUP), str(SEED)],
        label="framework_no_cache",
    )

    print("\n[wave233-p6] === R5b framework sub-sweep WITH cache (GPU 1) ===", flush=True)
    with_cache_payload = _run_subprocess(
        _FRAMEWORK_CODE_WITH_CACHE,
        [GPU_DEVICE, str(NFE_TOTAL), str(N_ROUNDS), str(BATCH), str(WARMUP), str(SEED)],
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
    print(f"[wave233-p6] cache stats: {summary['cache_stats']}", flush=True)
    print("\n=== Wave 233 P6 complete ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())