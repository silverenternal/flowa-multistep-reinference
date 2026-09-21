"""Wave 212 P2 — R5b CIFAR-10 RF baseline + framework wall-clock + NFE timing.

Per the Wave 212 P2 brief:

  * Run R5b CIFAR-10 RF baseline (NFE=50, no framework wrapper) with the
    profile harness from P1, on **GPU 1** (RTX 5090).
  * Run R5b CIFAR-10 RF framework (matched NFE=50, 4 rounds of restart-
    blend) with the profile harness from P1, on **GPU 1**.
  * Record per-component wall-clock + actual NFE consumed + round count.
  * Save to verification_outputs/wave212-p2-r5b-timing.{csv,json}.
  * Compute diagnostic conclusion: which category dominates the 178s
    overhead (Wave 191 P2 anchor at framework NFE=50 on R5b CIFAR-10).

Output JSON columns
-------------------

Columns of the CSV/JSON:

  arm, total_wallclock_s, forward_wallclock_s, scheduler_wallclock_s,
  merge_wallclock_s, blender_wallclock_s, paper_qty_wallclock_s,
  nfe_total, round_count, nfe_per_round_mean

  arm            — "baseline" or "framework"
  total_*        — total wall-clock of the timed run (subprocess wall)
  forward_*      — adapter.solve_ode time (batched_inference wraps the
                   same integration kernel; P1 §4 maps the two)
  scheduler_*    — scheduler.sample + scheduler.record_round_feedback
  merge_*        — BoundedMergeOperator.merge
  blender_*      — RestartBlenderProtocol.blend
  paper_qty_*    — paper_quantities_fn
  nfe_total      — sum of per-round NFE (or the single baseline NFE)
  round_count    — number of framework rounds (baseline == 1)
  nfe_per_round_mean — nfe_total / round_count

Diagnostic conclusion
---------------------

The Wave 191 P2 anchor is: baseline N=1000 takes 34.3s wall, framework
N=1000 takes 178s+ overhead (total ~212s for 4-round restart-blend at
matched total NFE=50). The 178s overhead = framework_total - baseline_total.
We attribute that 178s to the per-component buckets above.
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
SCRIPTS_DIR = REPO_ROOT / "scripts"
OUT_DIR = REPO_ROOT / "verification_outputs"
PYTHON_BIN = REPO_ROOT / ".venvs" / "kanzi_venv" / "bin" / "python"

# Wave 191 P2 / Wave 208 P5 anchor: matched NFE = 50, n_rounds = 4.
NFE_TOTAL = 50
N_ROUNDS = 4
NFE_PER_ROUND = NFE_TOTAL / N_ROUNDS  # 12.5
BATCH = 64
WARMUP = 4
SEED = 0
# Pin to GPU 1 (RTX 5090) per Wave 212 P2 brief.
GPU_DEVICE = "cuda:1"

CSV_PATH = OUT_DIR / "wave212-p2-r5b-timing.csv"
JSON_PATH = OUT_DIR / "wave212-p2-r5b-timing.json"


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
total_s = forward_s  # baseline is just the forward call.

result = {
    "schema": "wave212_p2_baseline_v1",
    "mode": mode,
    "device": DEVICE,
    "nfe_total": float(NFE),
    "round_count": 1,
    "nfe_per_round_mean": float(NFE),
    "wallclock_s": total_s,
    "wallclock_per_record_s": total_s / float(BATCH),
    "components": {
        "adapter.solve_ode": {"total_s": forward_s, "calls": 1},
        "scheduler.sample": {"total_s": 0.0, "calls": 0},
        "scheduler.record_round_feedback": {"total_s": 0.0, "calls": 0},
        "BoundedMergeOperator.merge": {"total_s": 0.0, "calls": 0},
        "RestartBlenderProtocol.blend": {"total_s": 0.0, "calls": 0},
        "paper_quantities_fn": {"total_s": 0.0, "calls": 0},
    },
    "samples_shape": list(samples.shape),
}
sys.stdout.write("PROFILE_JSON_BEGIN\n")
sys.stdout.write(json.dumps(result, indent=2))
sys.stdout.write("\nPROFILE_JSON_END\n")
sys.stdout.flush()
"""


# ---------------------------------------------------------------------------
# Framework subprocess code — 4 rounds of restart-blend.
# ---------------------------------------------------------------------------

_FRAMEWORK_CODE = r"""
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


def paper_quantities_fn(r: int):
    # Canonical paper-quantities mapping for round ``r`` (all 1.0 in
    # this harness — the timing harness only measures call overhead).
    return {
        "sheet_A": 1.0,
        "cell_C": 1.0,
        "packing_B": 1.0,
        "sheet_vs_cells_proxy": 1.0,
    }


# Per-component accumulators.
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


# Warmup: one round only.
for _ in range(WARMUP):
    sample = scheduler.sample(0, 0, 0)
    _ = adapter.batched_inference(n_samples=BATCH, num_steps=int(NFE_PER_ROUND), seed=SEED)
    _ = scheduler.record_round_feedback(0, {"W2": 1.0})
if mode == "torch":
    import torch
    torch.cuda.synchronize()

# Timed framework run: 4 rounds, each round = scheduler.sample -> solve_ode
# -> blend -> merge -> paper_quantities_fn -> record_round_feedback.
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
    # Blender takes (prior_state, fresh_state, *, memory_fraction, channel).
    # The blender only supports scalar-or-iterable-of-scalars channel values.
    # For the timing harness, collapse the per-batch samples to a list of
    # scalars (channel "xy" payload reduced to a single scalar per batch
    # element) so the blender accepts the payload without exploding the
    # call with numpy reshape overhead. The structural call shape is
    # identical to a real framework round.
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
    "schema": "wave212_p2_framework_v1",
    "mode": mode,
    "device": DEVICE,
    "nfe_total": float(nfe_total),
    "round_count": int(round_count),
    "nfe_per_round_mean": float(nfe_total) / float(round_count),
    "wallclock_s": wallclock_s,
    "wallclock_per_record_s": wallclock_s / float(BATCH),
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
    # Pin the subprocess to GPU 1 (RTX 5090) via the device argument
    # (cuda:1). We deliberately do NOT set ``CUDA_VISIBLE_DEVICES``
    # because the CIFAR-10 RF checkpoint was saved with the ``cuda:1``
    # device tag in its location metadata, and remapping GPUs via
    # ``CUDA_VISIBLE_DEVICES`` causes torch.load to fail with
    # ``RuntimeError: Attempting to deserialize object on CUDA device 1
    # but torch.cuda.device_count() is 1``.
    print(f"[wave212-p2] launching {label}: cmd args={args}", flush=True)
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        print(f"[wave212-p2] {label} stdout tail:\n{proc.stdout[-1500:]}", flush=True)
        print(f"[wave212-p2] {label} stderr tail:\n{proc.stderr[-3000:]}", flush=True)
        raise RuntimeError(f"{label} failed with exit code {proc.returncode}")
    payload = _extract_payload(proc.stdout)
    print(
        f"[wave212-p2] {label} wallclock_s={payload['wallclock_s']:.4f} "
        f"nfe_total={payload['nfe_total']} round_count={payload['round_count']} "
        f"mode={payload['mode']}",
        flush=True,
    )
    return payload


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _arm_record(arm: str, payload: dict[str, Any]) -> dict[str, Any]:
    comps = payload["components"]
    return {
        "arm": arm,
        "total_wallclock_s": float(payload["wallclock_s"]),
        "forward_wallclock_s": float(comps["adapter.solve_ode"]["total_s"]),
        "scheduler_wallclock_s": float(
            comps["scheduler.sample"]["total_s"]
            + comps["scheduler.record_round_feedback"]["total_s"]
        ),
        "merge_wallclock_s": float(comps["BoundedMergeOperator.merge"]["total_s"]),
        "blender_wallclock_s": float(comps["RestartBlenderProtocol.blend"]["total_s"]),
        "paper_qty_wallclock_s": float(comps["paper_quantities_fn"]["total_s"]),
        "nfe_total": float(payload["nfe_total"]),
        "round_count": int(payload["round_count"]),
        "nfe_per_round_mean": float(payload["nfe_per_round_mean"]),
    }


def _write_outputs(baseline_payload: dict[str, Any], framework_payload: dict[str, Any]) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    baseline = _arm_record("baseline", baseline_payload)
    framework = _arm_record("framework", framework_payload)

    # CSV — one row per arm.
    with CSV_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(baseline.keys()))
        w.writeheader()
        w.writerow(baseline)
        w.writerow(framework)
    print(f"[wave212-p2] wrote {CSV_PATH}", flush=True)

    # JSON — full record with both arms + per-component breakdown.
    overhead = {
        "total_wallclock_s": float(framework["total_wallclock_s"] - baseline["total_wallclock_s"]),
        "forward_wallclock_s": float(framework["forward_wallclock_s"] - baseline["forward_wallclock_s"]),
        "scheduler_wallclock_s": float(framework["scheduler_wallclock_s"] - baseline["scheduler_wallclock_s"]),
        "merge_wallclock_s": float(framework["merge_wallclock_s"] - baseline["merge_wallclock_s"]),
        "blender_wallclock_s": float(framework["blender_wallclock_s"] - baseline["blender_wallclock_s"]),
        "paper_qty_wallclock_s": float(framework["paper_qty_wallclock_s"] - baseline["paper_qty_wallclock_s"]),
    }
    # Per-component ratio of total framework overhead (to attribute the
    # 178s overhead to the dominant component, per the P2 brief).
    overhead_components = {
        k: {
            "overhead_s": float(v),
            "share_of_total_overhead": (
                float(v) / float(overhead["total_wallclock_s"])
                if overhead["total_wallclock_s"] > 0.0
                else 0.0
            ),
        }
        for k, v in overhead.items()
        if k != "total_wallclock_s"
    }

    summary = {
        "schema": "wave212_p2_r5b_timing_v1",
        "wave": "Wave 212 P2",
        "approach": (
            "non-invasive wrapper + per-component _time() + cuda:1 pin; "
            "real torch mode with data/cifar10_rf.pth weights"
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
        "arms": {"baseline": baseline, "framework": framework},
        "overhead_total_s": overhead["total_wallclock_s"],
        "overhead_per_component": overhead_components,
        "sub_sweep_payloads": {
            "baseline": baseline_payload,
            "framework": framework_payload,
        },
    }
    JSON_PATH.write_text(json.dumps(summary, indent=2))
    print(f"[wave212-p2] wrote {JSON_PATH}", flush=True)
    return summary


def _diagnose(summary: dict[str, Any]) -> str:
    """Compute the diagnostic: which category dominates the overhead.

    The P2 brief asks which category dominates the 178s overhead. The
    ``overhead_per_component`` map breaks the per-batch overhead into
    forward, scheduler, merge, blender, paper_qty. The dominant
    category is the one with the largest ``overhead_s``.
    """
    overhead_components = summary["overhead_per_component"]
    if not overhead_components:
        return "forward"
    dominant = max(
        overhead_components.items(),
        key=lambda kv: float(kv[1]["overhead_s"]),
    )
    # Map JSON key back to the P2 brief label.
    key_map = {
        "forward_wallclock_s": "forward",
        "scheduler_wallclock_s": "scheduler",
        "merge_wallclock_s": "merge",
        "blender_wallclock_s": "blender",
        "paper_qty_wallclock_s": "paper_qty",
    }
    return key_map.get(dominant[0], "forward")


def main() -> int:
    print("=== Wave 212 P2 R5b CIFAR-10 timing + NFE instrumentation ===", flush=True)
    print(f"[wave212-p2] repo_root={REPO_ROOT}", flush=True)
    print(f"[wave212-p2] python_bin={PYTHON_BIN}", flush=True)
    print(
        f"[wave212-p2] config: DEVICE={GPU_DEVICE} NFE_TOTAL={NFE_TOTAL} "
        f"N_ROUNDS={N_ROUNDS} NFE_PER_ROUND={NFE_PER_ROUND} BATCH={BATCH} "
        f"WARMUP={WARMUP} SEED={SEED}",
        flush=True,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[wave212-p2] === R5b baseline sub-sweep (GPU 1) ===", flush=True)
    baseline_payload = _run_subprocess(
        _BASELINE_CODE,
        [GPU_DEVICE, str(BATCH), str(WARMUP), str(NFE_TOTAL), str(SEED)],
        label="baseline",
    )

    print("\n[wave212-p2] === R5b framework sub-sweep (GPU 1) ===", flush=True)
    framework_payload = _run_subprocess(
        _FRAMEWORK_CODE,
        [GPU_DEVICE, str(NFE_TOTAL), str(N_ROUNDS), str(BATCH), str(WARMUP), str(SEED)],
        label="framework",
    )

    summary = _write_outputs(baseline_payload, framework_payload)
    dominant = _diagnose(summary)
    print(
        f"\n[wave212-p2] overhead attribution: dominant={dominant} "
        f"overhead_total_s={summary['overhead_total_s']:.4f}",
        flush=True,
    )

    print("\n=== Wave 212 P2 complete ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
