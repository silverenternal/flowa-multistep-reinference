"""Wave 236 P2 — R5b CIFAR-10 RF CUDA-graph wall-clock measurement.

Mirrors :mod:`scripts.wave233_p6_r5b_runner_wall_clock` but toggles
the ``ADAPTIVE_REFLOW_CUDA_GRAPH`` env var so the framework run
exercises the new graph-capture path.

The script measures five arms on the matched-NFE=50 / BATCH=64
harness:

  1. baseline_eager            — single batched_inference, graph OFF
  2. baseline_graph            — single batched_inference, graph ON
  3. framework_eager           — 4-round restart-blend runner, graph OFF
  4. framework_graph           — 4-round restart-blend runner, graph ON
  5. framework_graph_with_cache — runner + StateBundleDigestCache + graph

Output: ``verification_outputs/wave236-p2-cuda-graph-wall-clock.{csv,json}``.
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

CSV_PATH = OUT_DIR / "wave236-p2-cuda-graph-wall-clock.csv"
JSON_PATH = OUT_DIR / "wave236-p2-cuda-graph-wall-clock.json"


# ---------------------------------------------------------------------------
# Baseline subprocess code — single batched_inference, no framework wrapper.
# ---------------------------------------------------------------------------

_BASELINE_CODE = r"""
import sys, time, json

import numpy as np

sys.path.insert(0, "/home/hugo/codes/flowa-multistep-reinference")
from adaptive_reflow.adapters.rectified_flow_cifar import RectifiedFlowCIFARAdapter
from adaptive_reflow.framework.cuda_graph_capture import (
    default_cache, is_cuda_graph_capture_enabled,
)

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
    "schema": "wave236_p2_baseline_v1",
    "mode": mode,
    "device": DEVICE,
    "nfe_total": float(NFE),
    "round_count": 1,
    "nfe_per_round_mean": float(NFE),
    "wallclock_s": total_s,
    "wallclock_per_record_s": total_s / float(BATCH),
    "samples_shape": list(samples.shape),
    "cuda_graph_enabled": bool(is_cuda_graph_capture_enabled()),
    "cuda_graph_stats": default_cache().stats(),
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
from adaptive_reflow.framework.cuda_graph_capture import (
    default_cache, is_cuda_graph_capture_enabled,
)

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
sha_cache_stats = cache.stats() if cache is not None else None
cuda_graph_stats = default_cache().stats()

out = {
    "schema": (
        "wave236_p2_framework_with_cache_v1"
        if USE_CACHE
        else "wave236_p2_framework_no_cache_v1"
    ),
    "mode": mode,
    "device": DEVICE,
    "nfe_total": float(NFE_TOTAL),
    "round_count": n_rounds_actual,
    "nfe_per_round_mean": float(NFE_PER_ROUND),
    "wallclock_s": wallclock_s,
    "wallclock_per_record_s": wallclock_s / float(BATCH),
    "sha_cache_used": bool(USE_CACHE),
    "sha_cache_stats": sha_cache_stats,
    "cuda_graph_enabled": bool(is_cuda_graph_capture_enabled()),
    "cuda_graph_stats": cuda_graph_stats,
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


def _run_subprocess(
    code: str,
    args: list[str],
    label: str,
    *,
    env_override: dict[str, str] | None = None,
) -> dict[str, Any]:
    cmd = [str(PYTHON_BIN), "-c", code] + list(args)
    env = os.environ.copy()
    env.setdefault("PYTHONHASHSEED", "0")
    if env_override:
        env.update(env_override)
    print(f"[wave236-p2] launching {label}: cmd args={args}", flush=True)
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        print(f"[wave236-p2] {label} stdout tail:\n{proc.stdout[-1500:]}", flush=True)
        print(f"[wave236-p2] {label} stderr tail:\n{proc.stderr[-3000:]}", flush=True)
        raise RuntimeError(f"{label} failed with exit code {proc.returncode}")
    payload = _extract_payload(proc.stdout)
    print(
        f"[wave236-p2] {label} wallclock_s={payload['wallclock_s']:.4f} "
        f"nfe_total={payload['nfe_total']} round_count={payload['round_count']} "
        f"mode={payload['mode']} cuda_graph_enabled={payload.get('cuda_graph_enabled')}",
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
        "cuda_graph_enabled": bool(payload.get("cuda_graph_enabled", False)),
    }


def _write_outputs(
    baseline_eager: dict[str, Any],
    baseline_graph: dict[str, Any],
    framework_eager: dict[str, Any],
    framework_graph: dict[str, Any],
    framework_graph_with_cache: dict[str, Any],
) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    arms = {
        "baseline_eager": _arm_record("baseline_eager", baseline_eager),
        "baseline_graph": _arm_record("baseline_graph", baseline_graph),
        "framework_eager": _arm_record("framework_eager", framework_eager),
        "framework_graph": _arm_record("framework_graph", framework_graph),
        "framework_graph_with_cache": _arm_record(
            "framework_graph_with_cache", framework_graph_with_cache
        ),
    }

    with CSV_PATH.open("w", newline="") as f:
        fieldnames = [
            "arm",
            "n_rounds",
            "wall_seconds",
            "FID",
            "sha_cache_used",
            "cuda_graph_enabled",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for arm in arms.values():
            w.writerow(arm)
    print(f"[wave236-p2] wrote {CSV_PATH}", flush=True)

    base_eager_per_record = float(baseline_eager["wallclock_per_record_s"])
    base_graph_per_record = float(baseline_graph["wallclock_per_record_s"])
    framework_eager_per_record = float(framework_eager["wallclock_per_record_s"])
    framework_graph_per_record = float(framework_graph["wallclock_per_record_s"])
    framework_graph_with_cache_per_record = float(
        framework_graph_with_cache["wallclock_per_record_s"]
    )

    ratio_baseline = (
        base_graph_per_record / base_eager_per_record
        if base_eager_per_record > 0
        else 0.0
    )
    ratio_framework_eager = (
        framework_eager_per_record / base_eager_per_record
        if base_eager_per_record > 0
        else 0.0
    )
    ratio_framework_graph = (
        framework_graph_per_record / base_graph_per_record
        if base_graph_per_record > 0
        else 0.0
    )
    speedup_eager = (
        framework_eager_per_record / framework_graph_per_record
        if framework_graph_per_record > 0
        else 0.0
    )
    improvement_pct = (
        100.0
        * (framework_eager_per_record - framework_graph_per_record)
        / framework_eager_per_record
        if framework_eager_per_record > 0
        else 0.0
    )

    summary = {
        "schema": "wave236_p2_cuda_graph_wall_clock_v1",
        "wave": "Wave 236 P2",
        "approach": (
            "ReInferenceRunner.run() via ReInferenceConfig with "
            "StateBundleDigestCache (Wave 233 P6) and CUDA-graph "
            "capture (Wave 236 P2) toggled on/off; cuda:1 pin; "
            "matched NFE=50; 4 rounds"
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
        "arms": arms,
        "per_record_seconds": {
            "baseline_eager": base_eager_per_record,
            "baseline_graph": base_graph_per_record,
            "framework_eager": framework_eager_per_record,
            "framework_graph": framework_graph_per_record,
            "framework_graph_with_cache": framework_graph_with_cache_per_record,
        },
        "ratios": {
            "baseline_graph_vs_eager": float(ratio_baseline),
            "framework_eager_vs_baseline_eager": float(ratio_framework_eager),
            "framework_graph_vs_baseline_graph": float(ratio_framework_graph),
            "framework_speedup_graph_vs_eager": float(speedup_eager),
            "improvement_pct_on_framework": float(improvement_pct),
        },
        "cuda_graph_stats": {
            "baseline_graph": baseline_graph.get("cuda_graph_stats"),
            "framework_eager": framework_eager.get("cuda_graph_stats"),
            "framework_graph": framework_graph.get("cuda_graph_stats"),
            "framework_graph_with_cache": framework_graph_with_cache.get(
                "cuda_graph_stats"
            ),
        },
        "anchor": {
            "wallclock_ratio_anchor_24_6x": (
                "Wave 209 P8 anchor at N=1000: baseline 37.83 ms vs "
                "framework 930.52 ms = 24.60x at matched NFE=50."
            ),
        },
    }
    JSON_PATH.write_text(json.dumps(summary, indent=2))
    print(f"[wave236-p2] wrote {JSON_PATH}", flush=True)
    return summary


def main() -> int:
    print(
        "=== Wave 236 P2 R5b CIFAR-10 CUDA-graph wall-clock measurement ===",
        flush=True,
    )
    print(f"[wave236-p2] repo_root={REPO_ROOT}", flush=True)
    print(f"[wave236-p2] python_bin={PYTHON_BIN}", flush=True)
    print(
        f"[wave236-p2] config: DEVICE={GPU_DEVICE} NFE_TOTAL={NFE_TOTAL} "
        f"N_ROUNDS={N_ROUNDS} NFE_PER_ROUND={NFE_PER_ROUND} BATCH={BATCH} "
        f"WARMUP={WARMUP} SEED={SEED}",
        flush=True,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[wave236-p2] === R5b baseline sub-sweep (graph OFF) ===", flush=True)
    baseline_eager = _run_subprocess(
        _BASELINE_CODE,
        [GPU_DEVICE, str(BATCH), str(WARMUP), str(NFE_TOTAL), str(SEED)],
        label="baseline_eager",
        env_override={"ADAPTIVE_REFLOW_CUDA_GRAPH": ""},
    )

    print("\n[wave236-p2] === R5b baseline sub-sweep (graph ON) ===", flush=True)
    baseline_graph = _run_subprocess(
        _BASELINE_CODE,
        [GPU_DEVICE, str(BATCH), str(WARMUP), str(NFE_TOTAL), str(SEED)],
        label="baseline_graph",
        env_override={"ADAPTIVE_REFLOW_CUDA_GRAPH": "1"},
    )

    print("\n[wave236-p2] === R5b framework sub-sweep (no cache, graph OFF) ===", flush=True)
    framework_eager = _run_subprocess(
        _FRAMEWORK_CODE,
        ["0", GPU_DEVICE, str(NFE_TOTAL), str(N_ROUNDS), str(BATCH), str(WARMUP), str(SEED)],
        label="framework_eager",
        env_override={"ADAPTIVE_REFLOW_CUDA_GRAPH": ""},
    )

    print("\n[wave236-p2] === R5b framework sub-sweep (no cache, graph ON) ===", flush=True)
    framework_graph = _run_subprocess(
        _FRAMEWORK_CODE,
        ["0", GPU_DEVICE, str(NFE_TOTAL), str(N_ROUNDS), str(BATCH), str(WARMUP), str(SEED)],
        label="framework_graph",
        env_override={"ADAPTIVE_REFLOW_CUDA_GRAPH": "1"},
    )

    print(
        "\n[wave236-p2] === R5b framework sub-sweep (sha cache + graph ON) ===",
        flush=True,
    )
    framework_graph_with_cache = _run_subprocess(
        _FRAMEWORK_CODE,
        ["1", GPU_DEVICE, str(NFE_TOTAL), str(N_ROUNDS), str(BATCH), str(WARMUP), str(SEED)],
        label="framework_graph_with_cache",
        env_override={"ADAPTIVE_REFLOW_CUDA_GRAPH": "1"},
    )

    summary = _write_outputs(
        baseline_eager,
        baseline_graph,
        framework_eager,
        framework_graph,
        framework_graph_with_cache,
    )
    print(
        f"\n[wave236-p2] per_record: baseline_eager="
        f"{summary['per_record_seconds']['baseline_eager']*1000:.2f}ms "
        f"baseline_graph={summary['per_record_seconds']['baseline_graph']*1000:.2f}ms "
        f"framework_eager={summary['per_record_seconds']['framework_eager']*1000:.2f}ms "
        f"framework_graph={summary['per_record_seconds']['framework_graph']*1000:.2f}ms",
        flush=True,
    )
    print(
        f"[wave236-p2] speedup_graph_on_framework="
        f"{summary['ratios']['framework_speedup_graph_vs_eager']:.2f}x "
        f"new_ratio={summary['ratios']['framework_graph_vs_baseline_graph']:.2f}x "
        f"(was 24.60x anchor)",
        flush=True,
    )
    print("\n=== Wave 236 P2 complete ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
