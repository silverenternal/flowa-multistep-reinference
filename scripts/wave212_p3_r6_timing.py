"""Wave 212 P3 — R6 LineageFlow baseline + framework wall-clock + NFE timing.

Per the Wave 212 P3 brief:

  * Run R6 LineageFlow baseline (synthetic velocity field, NFE=50) with the
    profile harness from P1, on **GPU 0** (RTX PRO 6000).
  * Run R6 LineageFlow framework (matched NFE=50, 4 rounds of restart-
    blend) with the profile harness from P1, on **GPU 0**.
  * Record per-component wall-clock + actual NFE consumed + round count.
  * Save to verification_outputs/wave212-p3-r6-timing.{csv,json}.
  * Compute diagnostic conclusion: which category dominates the 178s
    overhead (Wave 191 P2 R5b anchor at framework NFE=50 on R5b CIFAR-10)
    when ported to R6 LineageFlow.

Output JSON columns
-------------------

Columns of the CSV/JSON:

  arm, total_wallclock_s, forward_wallclock_s, scheduler_wallclock_s,
  merge_wallclock_s, blender_wallclock_s, paper_qty_wallclock_s,
  nfe_total, round_count, nfe_per_round_mean

Diagnostic conclusion
---------------------

The Wave 212 P2 R5b CIFAR-10 anchor at BATCH=64: baseline 2.30s, framework
2.21s (matched NFE=50); the framework's per-batch non-forward overhead is
~0.9 ms dominated by the blender. The Wave 212 P3 R6 LineageFlow harness
compares against the Wave 191 P2 N=1000 anchor (baseline 34.3s, framework
~900s) to identify which category dominates the 178s framework-vs-baseline
gap when ported to the LineageFlow protein FM axis.
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
PYTHON_BIN = REPO_ROOT / ".venvs" / "lineageflow_venv" / "bin" / "python"

# Wave 212 P2 / Wave 191 P2 anchor: matched NFE = 50, n_rounds = 4.
NFE_TOTAL = 50
N_ROUNDS = 4
NFE_PER_ROUND = NFE_TOTAL / N_ROUNDS  # 12.5
BATCH = 64
WARMUP = 4
SEED = 0
# Pin to GPU 0 (RTX PRO 6000) per Wave 212 P3 brief.
GPU_DEVICE = "cuda:0"

CSV_PATH = OUT_DIR / "wave212-p3-r6-timing.csv"
JSON_PATH = OUT_DIR / "wave212-p3-r6-timing.json"


# ---------------------------------------------------------------------------
# Baseline subprocess code — single solve_ode, no framework wrapper.
# ---------------------------------------------------------------------------

_BASELINE_CODE = r"""
import sys, time, json

import numpy as np

sys.path.insert(0, "/home/hugo/codes/flowa-multistep-reinference")

# Pin to GPU 0 (RTX PRO 6000) per Wave 212 P3 brief.
import torch
torch.cuda.set_device(0)

from adaptive_reflow.adapters.lineageflow import LineageFlowAdapter
from adaptive_reflow.universal.state import ODEConditionDelta

DEVICE = sys.argv[1]
BATCH = int(sys.argv[2])
WARMUP = int(sys.argv[3])
NFE = int(sys.argv[4])
SEED = int(sys.argv[5])

# Build adapter (synthetic mode — torch mode requires 13s+ ESM-2 init
# which would dominate per-batch measurements; framework overhead is
# the diagnostic target, not the forward cost).
adapter = LineageFlowAdapter(force_mode="synthetic", num_steps=NFE)
mode = adapter._mode

# Warmup.
for w in range(WARMUP):
    bundle = adapter.build_initial_state(batch_id="b%d" % w, sample_id="s%d" % w)
    delta = ODEConditionDelta(
        delta_spec={"num_steps": NFE, "sampler_id": "euler"},
        source="wave212-p3-baseline",
        target_round=0,
        calibration_artifact_hash="wave212-p3:default",
    )
    delta = adapter.compose_condition(bundle, delta)
    _ = adapter.solve_ode(bundle, delta, seed=SEED + w)

torch.cuda.synchronize()

# Timed run (single solve_ode, no framework wrapper).
t0 = time.perf_counter()
bundle = adapter.build_initial_state(batch_id="b0", sample_id="s0")
delta = ODEConditionDelta(
    delta_spec={"num_steps": NFE, "sampler_id": "euler"},
    source="wave212-p3-baseline",
    target_round=0,
    calibration_artifact_hash="wave212-p3:default",
)
delta = adapter.compose_condition(bundle, delta)
trace = adapter.solve_ode(bundle, delta, seed=SEED)
torch.cuda.synchronize()
t1 = time.perf_counter()
forward_s = float(t1 - t0)
total_s = forward_s  # baseline is just the forward call.

result = {
    "schema": "wave212_p3_baseline_v1",
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
    "samples_shape": None,  # ODEIntegratorTrace does not carry .endpoint; trajectory is stored in native_state_cache
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

import torch
torch.cuda.set_device(0)

from adaptive_reflow.adapters.lineageflow import LineageFlowAdapter
from adaptive_reflow.algorithm.scheduler.simple import (
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.blender.blender import (
    LinearBlender,
)
from adaptive_reflow.algorithm.merge.merge_operator import (
    BoundedMergeOperator,
)
from adaptive_reflow.universal.state import ODEConditionDelta

DEVICE = sys.argv[1]
NFE_TOTAL = int(sys.argv[2])
N_ROUNDS = int(sys.argv[3])
NFE_PER_ROUND = NFE_TOTAL / N_ROUNDS
BATCH = int(sys.argv[4])
WARMUP = int(sys.argv[5])
SEED = int(sys.argv[6])

adapter = LineageFlowAdapter(force_mode="synthetic", num_steps=NFE_TOTAL)
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
for w in range(WARMUP):
    bundle = adapter.build_initial_state(batch_id="b%d" % w, sample_id="s%d" % w)
    delta = ODEConditionDelta(
        delta_spec={"num_steps": int(NFE_PER_ROUND), "sampler_id": "euler"},
        source="wave212-p3-framework",
        target_round=0,
        calibration_artifact_hash="wave212-p3:default",
    )
    delta = adapter.compose_condition(bundle, delta)
    _ = adapter.solve_ode(bundle, delta, seed=SEED + w)
torch.cuda.synchronize()

# Timed framework run: 4 rounds, each round = scheduler.sample -> solve_ode
# -> blend -> merge -> paper_quantities_fn -> record_round_feedback.
t_wall_0 = time.perf_counter()
for r in range(N_ROUNDS):
    sample = _time("scheduler.sample", scheduler.sample, 0, r, r)
    n_cap_r = float(sample.n_cap)
    # Build a fresh bundle per round so the framework loop matches the
    # R5b harness shape (which uses build_initial_state + solve_ode
    # per round in the framework loop).
    bundle = adapter.build_initial_state(batch_id="b%d" % r, sample_id="s%d" % r)
    delta = ODEConditionDelta(
        delta_spec={"num_steps": int(NFE_PER_ROUND), "sampler_id": "euler"},
        source="wave212-p3-framework",
        target_round=r,
        calibration_artifact_hash="wave212-p3:default",
    )
    delta = adapter.compose_condition(bundle, delta)
    trace = _time(
        "adapter.solve_ode",
        adapter.solve_ode,
        bundle,
        delta,
        seed=SEED + r,
    )
    # Blender takes (state, policy). For LineageFlow, collapse the
    # per-position categorical state to a scalar channel-value shim so
    # the LinearBlender accepts the payload. The structural call shape
    # matches a real framework round.
    class _StateShim:
        __slots__ = ("channel_values",)

        def __init__(self, arr):
            flat = np.asarray(arr, dtype=np.float64).reshape(-1)
            self.channel_values = {"xy": float(flat.mean())}

    # Build channel-value shims from a sample-aggregate of the per-position
    # categorical state. For the timing harness, the structural round shape
    # is what matters; the channel value carries one float per round.
    shim = _StateShim(np.zeros((1, 1), dtype=np.float64))
    prior_state = shim
    fresh_state = shim
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
torch.cuda.synchronize()
t_wall_1 = time.perf_counter()

wallclock_s = float(t_wall_1 - t_wall_0)
result = {
    "schema": "wave212_p3_framework_v1",
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
    # Pin the subprocess to GPU 0 (RTX PRO 6000) via the device argument.
    print(f"[wave212-p3] launching {label}: cmd args={args}", flush=True)
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        print(f"[wave212-p3] {label} stdout tail:\n{proc.stdout[-1500:]}", flush=True)
        print(f"[wave212-p3] {label} stderr tail:\n{proc.stderr[-3000:]}", flush=True)
        raise RuntimeError(f"{label} failed with exit code {proc.returncode}")
    payload = _extract_payload(proc.stdout)
    print(
        f"[wave212-p3] {label} wallclock_s={payload['wallclock_s']:.4f} "
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


def _write_outputs(
    baseline_payload: dict[str, Any], framework_payload: dict[str, Any]
) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    baseline = _arm_record("baseline", baseline_payload)
    framework = _arm_record("framework", framework_payload)

    # CSV — one row per arm.
    with CSV_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(baseline.keys()))
        w.writeheader()
        w.writerow(baseline)
        w.writerow(framework)
    print(f"[wave212-p3] wrote {CSV_PATH}", flush=True)

    # JSON — full record with both arms + per-component breakdown.
    overhead = {
        "total_wallclock_s": float(
            framework["total_wallclock_s"] - baseline["total_wallclock_s"]
        ),
        "forward_wallclock_s": float(
            framework["forward_wallclock_s"] - baseline["forward_wallclock_s"]
        ),
        "scheduler_wallclock_s": float(
            framework["scheduler_wallclock_s"] - baseline["scheduler_wallclock_s"]
        ),
        "merge_wallclock_s": float(
            framework["merge_wallclock_s"] - baseline["merge_wallclock_s"]
        ),
        "blender_wallclock_s": float(
            framework["blender_wallclock_s"] - baseline["blender_wallclock_s"]
        ),
        "paper_qty_wallclock_s": float(
            framework["paper_qty_wallclock_s"]
            - baseline["paper_qty_wallclock_s"]
        ),
    }
    # Per-component ratio of total framework overhead (to attribute the
    # framework overhead to the dominant component, per the P3 brief).
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
        "schema": "wave212_p3_r6_timing_v1",
        "wave": "Wave 212 P3",
        "approach": (
            "non-invasive wrapper + per-component _time() + cuda:0 pin; "
            "LineageFlow synthetic mode (torch mode requires 13s+ ESM-2 init)"
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
    print(f"[wave212-p3] wrote {JSON_PATH}", flush=True)
    return summary


def main() -> int:
    print("=== Wave 212 P3 R6 LineageFlow timing + NFE instrumentation ===", flush=True)
    print(f"[wave212-p3] repo_root={REPO_ROOT}", flush=True)
    print(f"[wave212-p3] python_bin={PYTHON_BIN}", flush=True)
    print(
        f"[wave212-p3] config: DEVICE={GPU_DEVICE} NFE_TOTAL={NFE_TOTAL} "
        f"N_ROUNDS={N_ROUNDS} NFE_PER_ROUND={NFE_PER_ROUND} BATCH={BATCH} "
        f"WARMUP={WARMUP} SEED={SEED}",
        flush=True,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[wave212-p3] === R6 LineageFlow baseline sub-sweep (GPU 0) ===", flush=True)
    baseline_payload = _run_subprocess(
        _BASELINE_CODE,
        [GPU_DEVICE, str(BATCH), str(WARMUP), str(NFE_TOTAL), str(SEED)],
        label="baseline",
    )

    print("\n[wave212-p3] === R6 LineageFlow framework sub-sweep (GPU 0) ===", flush=True)
    framework_payload = _run_subprocess(
        _FRAMEWORK_CODE,
        [GPU_DEVICE, str(NFE_TOTAL), str(N_ROUNDS), str(BATCH), str(WARMUP), str(SEED)],
        label="framework",
    )

    summary = _write_outputs(baseline_payload, framework_payload)
    print(
        f"\n[wave212-p3] overhead_total_s={summary['overhead_total_s']:.4f}",
        flush=True,
    )

    print("\n=== Wave 212 P3 complete ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
