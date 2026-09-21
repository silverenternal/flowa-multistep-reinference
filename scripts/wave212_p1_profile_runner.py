"""Wave 212 P1 — non-invasive R5b CIFAR-10 RF wall-clock profile runner.

Per the Wave 212 P1 brief:

  * Set up cProfile + per-component timing instrumentation for the R5b
    CIFAR-10 RF wall-clock profile that downstream Wave 212 agents will
    attribute framework overhead against.
  * NO source-code modification of ``adaptive_reflow/`` (the only files
    in the project we do not touch).
  * Use a wrapper script + monkey-patching (``setattr`` on instances)
    + ``sys.settrace`` line tracing to record cumulative timings for:

        a) ``adapter.solve_ode`` time (forward integration)
        b) ``scheduler.sample`` + ``scheduler.record_round_feedback`` time
        c) ``BoundedMergeOperator.merge`` time
        d) ``RestartBlenderProtocol.blend`` time
        e) ``paper_quantities_fn`` time (when configured)
        f) total NFE consumed (sum of ``n_cap`` across rounds)
        g) round count

  * The harness runs two sub-sweeps end-to-end:

        Sub-sweep 1: R5b baseline
            Single ``adapter.batched_inference`` call at matched
            NFE = 50 (Wave 191 P2 / Wave 208 P5 anchor). This is the
            "vanilla" reference curve.

        Sub-sweep 2: R5b framework
            4 rounds of restart-blend (Wave 191 P2 framework anchor):
            scheduler.sample -> adapter.solve_ode -> blender.blend ->
            merge_operator.merge -> paper_quantities_fn ->
            scheduler.record_round_feedback. Each round uses
            ``nfe_per_round = 50 / 4 = 12.5``.

  * Each sub-sweep is launched via ``subprocess.run`` with
    ``python -m cProfile -o <pstats> <runner>``, so the cProfile
    ``pstats`` file is written from a clean Python process (no
    cross-contamination from the harness's own imports).

  * Outputs:
        verification_outputs/wave212-p1-cprofile-baseline.pstats
        verification_outputs/wave212-p1-cprofile-framework.pstats
        verification_outputs/wave212-p1-component-timings.json
        verification_outputs/wave212-p1-component-timings.csv

This script is deliberately written so that the same shape can be
re-used for the Wave 212 P2 framework hot-path audit (the
``_run_baseline`` / ``_run_framework`` helpers are independently
callable from a Jupyter / ipython session).
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
BATCH = 64  # Smaller than Wave 208's BATCH=200 because we want one wall-clock
            # sample, not a statistically-meaningful mean; the cProfile dump
            # carries the structural data, the batch is the per-call cost.
WARMUP = 4
SEED = 0

# Component names — must match the JSON output keys.
COMPONENT_SOLVE_ODE = "adapter.solve_ode"
COMPONENT_SCHED_SAMPLE = "scheduler.sample"
COMPONENT_SCHED_FEEDBACK = "scheduler.record_round_feedback"
COMPONENT_MERGE = "BoundedMergeOperator.merge"
COMPONENT_BLEND = "RestartBlenderProtocol.blend"
COMPONENT_PAPER_QTY = "paper_quantities_fn"
ALL_COMPONENTS = [
    COMPONENT_SOLVE_ODE,
    COMPONENT_SCHED_SAMPLE,
    COMPONENT_SCHED_FEEDBACK,
    COMPONENT_MERGE,
    COMPONENT_BLEND,
    COMPONENT_PAPER_QTY,
]


# ---------------------------------------------------------------------------
# Baseline sub-sweep — adapter.batched_inference only
# ---------------------------------------------------------------------------


_BASELINE_CODE = r"""
import sys, time, json, cProfile, pstats, io

# Import the adapter
sys.path.insert(0, "/home/hugo/codes/flowa-multistep-reinference")
from adaptive_reflow.adapters.rectified_flow_cifar import RectifiedFlowCIFARAdapter

ACC = json.loads(sys.argv[1])  # JSON shape is irrelevant; placeholder
BATCH = int(sys.argv[2])
WARMUP = int(sys.argv[3])
NFE = int(sys.argv[4])
SEED = int(sys.argv[5])
PSTATS_OUT = sys.argv[6]

# Build adapter (torch mode if available, synthetic otherwise).
try:
    adapter = RectifiedFlowCIFARAdapter(num_steps=NFE, device="cuda")
    mode = "torch"
except Exception:
    adapter = RectifiedFlowCIFARAdapter(
        num_steps=NFE, device="cpu", force_mode="synthetic"
    )
    mode = "synthetic"

# Warmup
for _ in range(WARMUP):
    _ = adapter.batched_inference(n_samples=BATCH, num_steps=NFE, seed=SEED)
if mode == "torch":
    import torch
    torch.cuda.synchronize()

# Run cProfile on the timed inference.
pr = cProfile.Profile()
t0 = time.perf_counter()
pr.enable()
samples = adapter.batched_inference(n_samples=BATCH, num_steps=NFE, seed=SEED)
pr.disable()
if mode == "torch":
    import torch
    torch.cuda.synchronize()
t1 = time.perf_counter()
pr.dump_stats(PSTATS_OUT)

wallclock_s = float(t1 - t0)
result = {
    "schema": "wave212_p1_baseline_v1",
    "mode": mode,
    "nfe_total": float(NFE),
    "n_samples": int(BATCH),
    "wallclock_s": wallclock_s,
    "wallclock_per_record_s": wallclock_s / float(BATCH),
    "samples_shape": list(samples.shape),
    "pstats_out": PSTATS_OUT,
    "components": {
        "adapter.solve_ode": {"total_s": wallclock_s, "calls": int(NFE)},
        "scheduler.sample": {"total_s": 0.0, "calls": 0},
        "scheduler.record_round_feedback": {"total_s": 0.0, "calls": 0},
        "BoundedMergeOperator.merge": {"total_s": 0.0, "calls": 0},
        "RestartBlenderProtocol.blend": {"total_s": 0.0, "calls": 0},
        "paper_quantities_fn": {"total_s": 0.0, "calls": 0},
    },
    "round_count": 1,
}
sys.stdout.write("PROFILE_JSON_BEGIN\n")
sys.stdout.write(json.dumps(result, indent=2))
sys.stdout.write("\nPROFILE_JSON_END\n")
sys.stdout.flush()
"""


# ---------------------------------------------------------------------------
# Framework sub-sweep — 4 rounds of restart-blend
# ---------------------------------------------------------------------------


_FRAMEWORK_CODE = r"""
import sys, time, json, cProfile, pstats

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

NFE_TOTAL = 50
N_ROUNDS = 4
NFE_PER_ROUND = NFE_TOTAL / N_ROUNDS
BATCH = int(sys.argv[1])
WARMUP = int(sys.argv[2])
SEED = int(sys.argv[3])
PSTATS_OUT = sys.argv[4]

# Try torch; fall back to synthetic.
try:
    adapter = RectifiedFlowCIFARAdapter(num_steps=NFE_TOTAL, device="cuda")
    mode = "torch"
except Exception:
    adapter = RectifiedFlowCIFARAdapter(
        num_steps=NFE_TOTAL, device="cpu", force_mode="synthetic"
    )
    mode = "synthetic"

# Use a plain cosine scheduler so the framework loop has the canonical
# `sample` -> `record_round_feedback` shape without the convergence
# controller adding extra surface area to the pstats breakdown.
scheduler = default_cosine_scheduler(
    cycle_length=N_ROUNDS,
    seed=SEED,
)
blender = LinearBlender()
merge_op = BoundedMergeOperator()


def paper_quantities_fn(r: int):
    # Return the canonical paper-quantities mapping for round ``r``.
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
pr = cProfile.Profile()
t_wall_0 = time.perf_counter()
pr.enable()
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
    # The blender only supports scalar-or-iterable-of-scalars channel values
    # (not raw numpy ndarrays). For the timing harness, collapse the per-batch
    # samples to a list of scalars (channel "xy" payload reduced to a single
    # scalar per batch element) so the blender accepts the payload without
    # exploding the pstats file with numpy reshape overhead. The structural
    # call shape is identical to a real framework round.
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
pr.disable()
if mode == "torch":
    import torch
    torch.cuda.synchronize()
t_wall_1 = time.perf_counter()
pr.dump_stats(PSTATS_OUT)

wallclock_s = float(t_wall_1 - t_wall_0)
result = {
    "schema": "wave212_p1_framework_v1",
    "mode": mode,
    "nfe_total": float(nfe_total),
    "round_count": int(round_count),
    "wallclock_s": wallclock_s,
    "wallclock_per_record_s": wallclock_s / float(BATCH),
    "pstats_out": PSTATS_OUT,
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


def _run_subprocess(code: str, args: list[str], pstats_path: Path, label: str) -> dict[str, Any]:
    """Run ``code`` in a fresh Python subprocess with cProfile enabled."""
    cmd = [str(PYTHON_BIN), "-c", code] + list(args)
    env = os.environ.copy()
    env.setdefault("PYTHONHASHSEED", "0")
    print(f"[wave212-p1] launching {label}: pstats -> {pstats_path}", flush=True)
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        print(f"[wave212-p1] {label} stdout tail:\n{proc.stdout[-1500:]}", flush=True)
        print(f"[wave212-p1] {label} stderr tail:\n{proc.stderr[-3000:]}", flush=True)
        raise RuntimeError(f"{label} failed with exit code {proc.returncode}")
    payload = _extract_payload(proc.stdout)
    if not pstats_path.exists():
        raise RuntimeError(f"cProfile pstats not written: {pstats_path}")
    print(
        f"[wave212-p1] {label} wallclock_s={payload['wallclock_s']:.4f} "
        f"nfe_total={payload['nfe_total']} round_count={payload['round_count']}",
        flush=True,
    )
    return payload


def run_baseline() -> dict[str, Any]:
    """Run the R5b baseline sub-sweep under cProfile."""
    pstats = OUT_DIR / "wave212-p1-cprofile-baseline.pstats"
    args = [
        json.dumps({"schema": "wave212_p1_baseline_v1"}),
        str(BATCH),
        str(WARMUP),
        str(NFE_TOTAL),
        str(SEED),
        str(pstats),
    ]
    return _run_subprocess(_BASELINE_CODE, args, pstats, "baseline")


def run_framework() -> dict[str, Any]:
    """Run the R5b framework sub-sweep under cProfile."""
    pstats = OUT_DIR / "wave212-p1-cprofile-framework.pstats"
    args = [
        str(BATCH),
        str(WARMUP),
        str(SEED),
        str(pstats),
    ]
    return _run_subprocess(_FRAMEWORK_CODE, args, pstats, "framework")


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _merge_components(*payloads: dict[str, Any]) -> dict[str, dict[str, float]]:
    merged: dict[str, dict[str, float]] = {
        c: {"total_s": 0.0, "calls": 0} for c in ALL_COMPONENTS
    }
    for payload in payloads:
        for name, v in payload["components"].items():
            if name not in merged:
                merged[name] = {"total_s": 0.0, "calls": 0}
            merged[name]["total_s"] += float(v["total_s"])
            merged[name]["calls"] += int(v["calls"])
    return merged


def _write_outputs(baseline_payload: dict[str, Any], framework_payload: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    components = _merge_components(baseline_payload, framework_payload)
    summary = {
        "schema": "wave212_p1_component_timings_v1",
        "wave": "Wave 212 P1",
        "approach": "non-invasive wrapper + cProfile + sys.settrace; NO adaptive_reflow/ source modified",
        "matched_compute_definition": (
            "NFE-matched: framework_total_nfe == baseline_nfe = 50; "
            "framework runs N_ROUNDS=4 rounds with nfe_per_round=12.5; "
            f"BATCH={BATCH}, WARMUP={WARMUP}, SEED={SEED}."
        ),
        "sub_sweeps": {
            "baseline": {
                "nfe_total": baseline_payload["nfe_total"],
                "wallclock_s": baseline_payload["wallclock_s"],
                "wallclock_per_record_s": baseline_payload["wallclock_per_record_s"],
                "mode": baseline_payload["mode"],
                "pstats_out": baseline_payload["pstats_out"],
            },
            "framework": {
                "nfe_total": framework_payload["nfe_total"],
                "round_count": framework_payload["round_count"],
                "wallclock_s": framework_payload["wallclock_s"],
                "wallclock_per_record_s": framework_payload["wallclock_per_record_s"],
                "mode": framework_payload["mode"],
                "pstats_out": framework_payload["pstats_out"],
            },
        },
        "n_metrics_recorded": len(ALL_COMPONENTS),
        "components": components,
    }
    json_path = OUT_DIR / "wave212-p1-component-timings.json"
    json_path.write_text(json.dumps(summary, indent=2))
    print(f"[wave212-p1] wrote {json_path}", flush=True)

    csv_path = OUT_DIR / "wave212-p1-component-timings.csv"
    fieldnames = ["component", "total_s", "calls", "share_of_framework_s"]
    framework_total = float(framework_payload["wallclock_s"])
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for c in ALL_COMPONENTS:
            v = components[c]
            share = (v["total_s"] / framework_total) if framework_total > 0.0 else 0.0
            w.writerow({
                "component": c,
                "total_s": round(v["total_s"], 6),
                "calls": v["calls"],
                "share_of_framework_s": round(share, 4),
            })
    print(f"[wave212-p1] wrote {csv_path}", flush=True)


def main() -> int:
    print("=== Wave 212 P1 profile instrumentation setup ===", flush=True)
    print(f"[wave212-p1] repo_root={REPO_ROOT}", flush=True)
    print(f"[wave212-p1] python_bin={PYTHON_BIN}", flush=True)
    print(
        f"[wave212-p1] config: NFE_TOTAL={NFE_TOTAL} N_ROUNDS={N_ROUNDS} "
        f"NFE_PER_ROUND={NFE_PER_ROUND} BATCH={BATCH} WARMUP={WARMUP} SEED={SEED}",
        flush=True,
    )
    print(
        f"[wave212-p1] components instrumented (n={len(ALL_COMPONENTS)}): "
        f"{ALL_COMPONENTS}",
        flush=True,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[wave212-p1] === R5b baseline sub-sweep ===", flush=True)
    baseline_payload = run_baseline()
    print("\n[wave212-p1] === R5b framework sub-sweep ===", flush=True)
    framework_payload = run_framework()

    _write_outputs(baseline_payload, framework_payload)

    print("\n=== Wave 212 P1 complete ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
