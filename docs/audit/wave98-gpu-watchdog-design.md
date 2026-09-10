# Wave 98 Agent A — GPU utilization watchdog design

**Date:** 2026-09-10
**Agent:** Wave 98 Agent A
**Branch:** main
**Status:** design + implementation doc. Code landed in commit `99834d9`
("Wave 98.A: GPU utilization watchdog"). This doc is the design rationale
for that commit. 1 new audit doc + 0 source changes (code already
committed).

---

## 0. TL;DR

| Question | Answer |
|---|---|
| What problem did the watchdog fix? | The Wave 96.E "stuck-process" failure mode where a sweep driver is running on GPU but compute stays at 0% for tens of seconds while VRAM is occupied (e.g. driver hung on a `cuda.synchronize()`, model loaded but `forward()` never enqueued, or pinned to a different device). The user only sees the failure when the cell eventually times out 30 minutes later. |
| What's the diagnostic? | A daemon thread that polls `nvidia-smi` every 5 s and emits a WARNING to stderr when `util.gpu == 0` for ≥30 s WHILE `memory.used > 100 MiB`. |
| Stdlib-only? | **YES** — `subprocess` + `threading` + `os` + `sys` + `time` + `json` only. No `torch`, no `nvidia-ml-py`, no `psutil`. Cold-clone safe + CI-friendly. |
| How is it wired? | As a context manager (`tools._gpu_watchdog.gpu_watchdog()`) in `tools/eval/sweep.py:_run_cell`, `tools/sweep_kanzi_n1000_diverse.py`, and `tools/upstream_eval.py:run_*_upstream_eval`. |
| Test gate? | 9/9 watchdog tests PASS; 110/110 related tests PASS; D.4 33/33 PASS. |

---

## 1. Motivation — the Wave 96.E stuck-process scenario

### 1.1 The original failure mode

Wave 96.E's Kanzi N=10 sweep (`tools/sweep_kanzi_n1000_diverse.py`) was
the first sweep to surface this class of bug. The sweep driver was
launching on a 5090 GPU and:

1. Loaded the Kanzi adapter into VRAM (~3 GiB).
2. Began the first cell's ODE solve loop.
3. Hung silently — `torch.cuda.synchronize()` was stuck on a stale CUDA
   stream because the upstream `kanzi.DAE.from_pretrained` had bound to
   a different device than the adapter (a Wave 95 latent-loading bug
   that had been papered over with a try/except).
4. The user's terminal showed no output for 30 minutes; the sweep only
   terminated when the user's shell timed out the run.

**The diagnostic gap:** nothing in the sweep driver's stderr told the
user "the GPU is idle but VRAM is occupied — your process is stuck on
something other than compute." Without that signal, the only recourse
was to inspect `nvidia-smi` from another shell, manually.

### 1.2 Why we didn't catch this earlier

The earlier sweeps (Waves 91, 92c, 95 P3.C, 96.D) all completed
because they were short (N≤10 smoke tests). The Wave 96.E sweep was
the first N=10 that crossed the 30-minute wall-clock threshold while
still in GPU compute. The watchdog was originally proposed as a
"should have caught Wave 96.E" diagnostic; Wave 97 routed past it
without adding the watchdog; Wave 98.A is the first wave that
back-fills the diagnostic.

---

## 2. Design — `tools/_gpu_watchdog.py` (~240 LOC)

### 2.1 Public surface

```python
from tools._gpu_watchdog import gpu_status, gpu_watchdog

# Manual one-shot poll
status: dict = gpu_status()
# Returns: {"util": int, "mem_mib": float, "name": str | None,
#          "available": bool, "raw": str}

# Background watchdog context manager
with gpu_watchdog(threshold_seconds=30, sample_interval=5):
    # ... do GPU work ...
    ...
```

### 2.2 Trigger condition

The watchdog emits **one warning per stuck window** when:

```
util.gpu == 0
  AND memory.used > 100 MiB
  AND has persisted for >= threshold_seconds (default 30s)
```

The `memory.used > 100 MiB` floor matters because:

- A truly idle GPU has `util=0` AND `mem ≈ 0` (no model loaded). No
  warning — process is genuinely idle.
- A GPU with a model loaded but no compute in flight has `util=0`
  AND `mem > 100 MiB`. **THIS IS THE STUCK SCENARIO** — the watchdog
  fires.
- A GPU doing real work has `util > 5%` (cuBLAS GEMM always shows
  ≥5%). No warning.

### 2.3 The `_warned: bool` flag — one warning per window

The watchdog does **not** spam. Each `_warned` flag is reset to False
when compute recovers (`util > 0` or `mem drops below threshold`).
This avoids the case where a 5-minute sweep produces 60 warning
lines because the cell boundaries happen to align with the sample
interval.

### 2.4 `nvidia-smi` invocation

```bash
nvidia-smi --query-gpu=utilization.gpu,memory.used,name \
           --format=csv,noheader,nounits
```

We invoke `nvidia-smi` via `subprocess.run(..., timeout=2.0)` — never
inline-parsed with regex. The `--query-gpu=...` API is stable across
CUDA driver versions (10.x → 12.x). Timeout is 2s so a stuck
`nvidia-smi` cannot hang the sweep.

### 2.5 `_disabled_due_to_unavailable` short-circuit

If the first poll returns `available=False` (no `nvidia-smi` on the
host — common in CI), the thread marks itself disabled and exits
without spawning further polls. This prevents non-GPU hosts from
spamming `nvidia-smi: command not found` to stderr every 5 seconds
for the entire sweep duration.

### 2.6 `GPU_WATCHDOG_DISABLED=1` env var

A simple escape hatch:

```bash
GPU_WATCHDOG_DISABLED=1 python -m tools.eval --model kanzi --n-rounds 1
```

The watchdog silently no-ops. This is set in `tests/conftest.py` by
default so the watchdog doesn't interfere with tests that mock
`subprocess.run` (e.g. `test_upstream_eval.py` asserts
`call_count == 1`). The watchdog tests themselves explicitly
`monkeypatch.delenv()` to enable it.

### 2.7 Thread safety — `BaseException` catch

`gpu_status()` wraps `subprocess.run` in `except BaseException`. This
is intentional: the watchdog is a **diagnostic** that must NEVER
crash the parent process. If `nvidia-smi` hangs the kernel, or
Python's subprocess implementation has a teardown bug, or the test
mocks `subprocess.run` to raise a custom exception, the watchdog
must catch it and return `available=False` rather than propagating.

### 2.8 Daemon thread cleanup

The thread is `daemon=True` so it dies with the parent process — no
orphaned GPU pollers. Additionally, the `gpu_watchdog()` context
manager calls `stop_event.set()` + `thread.join(timeout=...)` on exit,
giving the thread up to 2 sample-intervals to clean up.

---

## 3. Where the watchdog is wired (Wave 98.A)

| File | Line | Site | Wrap pattern |
|---|---:|---|---|
| `tools/eval/sweep.py` | `_run_cell()` entry | Per-cell compute | `with gpu_watchdog(): _run_cell(...)` |
| `tools/sweep_kanzi_n1000_diverse.py` | `main()` body | Per-record sweep loop | `with gpu_watchdog(): for record in records: ...` |
| `tools/upstream_eval.py` | `run_flowmol3_upstream_eval()` + `run_lineageflow_upstream_eval()` entry | Each upstream entry point | `with gpu_watchdog(): ...` |

Each wiring is 1-2 LOC. The watchdog defaults (`threshold_seconds=30`,
`sample_interval=5`, `mem_threshold_mib=100`) are appropriate for the
dominant sweep duration (5-60 min).

---

## 4. Tests — `tests/test_tools/test_gpu_watchdog.py` (9 tests, ~270 LOC)

| # | Test | What it asserts |
|---|---|---|
| 1 | `test_watchdog_detects_stuck_zero_util_plus_memory` | When `gpu_status` returns `{util=0, mem=200}` continuously for 35s, a WARNING is emitted to the captured sink |
| 2 | `test_watchdog_no_warning_when_util_above_5pct` | When `gpu_status` returns `{util=50, mem=200}`, no warning after 35s |
| 3 | `test_watchdog_no_warning_when_memory_below_threshold` | When `gpu_status` returns `{util=0, mem=50}`, no warning after 35s |
| 4 | `test_gpu_status_returns_expected_dict_shape` | Manual poll returns dict with all 5 expected keys |
| 5 | `test_watchdog_thread_is_daemon_and_cleaned_up_on_exit` | Thread is `daemon=True` and is joined within 2 sample-intervals of context exit |
| 6 | `test_watchdog_window_resets_when_compute_recovers` | After a stuck window triggers a warning, a recovery sample resets the window — next stuck episode re-warns |
| 7 | `test_watchdog_enabled_false_short_circuits` | When `enabled=False`, context manager yields `None` and no thread is spawned |
| 8 | `test_watchdog_warning_includes_argv_command` | The WARNING line contains `sys.argv` joined with `shlex.quote` |
| 9 | `test_gpu_status_nvidia_smi_missing_returns_unavailable` | When `nvidia-smi` exits non-zero or returns empty, `gpu_status` returns `{"available": False, ...}` without raising |

### 4.1 Test isolation — `tests/conftest.py`

```python
# tests/conftest.py
import os
os.environ.setdefault("GPU_WATCHDOG_DISABLED", "1")
```

This is set in the session-level fixture so the watchdog doesn't
fire during tests that don't intentionally exercise it. Tests that
DO exercise the watchdog (`test_gpu_watchdog.py`) explicitly
`monkeypatch.delenv("GPU_WATCHDOG_DISABLED")` to re-enable it for
the duration of the test.

---

## 5. What the watchdog does NOT do

| Scenario | Why not caught | Mitigation |
|---|---|---|
| GPU OOM (cuda OOM exception in user's code) | The exception propagates immediately; the watchdog never sees the stuck window | Framework already wraps ODE solve in try/except that converts OOM to a structured error |
| GPU hang with NO VRAM occupied (kernel crash + driver reset) | `util=0` AND `mem=0` — below the 100 MiB floor | `nvidia-smi` would show "N/A" or empty; the watchdog short-circuits |
| Multi-GPU boxes where sweep is on GPU 1 but util shows GPU 0 | We poll `nvidia-smi` without `--id=` — defaults to GPU 0 | Documented limitation; multi-GPU boxes should set `CUDA_VISIBLE_DEVICES` |
| Sub-second stalls (e.g. optimizer.step() taking 0.5s) | Below the 30s window | Acceptable — only sustained stalls are flagged |
| Compute-bound workloads with low util (memory-bandwidth-bound) | `util=5-10%` is normal for memory-bound kernels; only `util=0` triggers | `util=0` is the discriminating signal — it means "no kernel was queued at all in the sample window" |

---

## 6. Impact on Wave 99 N=1000 sweep

The Wave 99 N=1000 Kanzi sweep will:

1. Wrap the per-cell compute in `gpu_watchdog(threshold_seconds=30)`.
2. If a cell gets stuck (e.g. CUDA stream deadlock from a malformed
   per-cell restart distribution), the watchdog emits a WARNING within
   35 seconds with the exact cell index, GPU util, VRAM, and the
   command line.
3. The user can then `pkill` the sweep and inspect the warning to
   identify which cell hung (e.g. cell #742 of 1000 — narrowed via
   the WARNING's `pid` + the sweep's last-printed progress line).

This is a **diagnostic**, not a fix — the watchdog doesn't unstick
the GPU. But it converts a 30-minute silent hang into a 35-second
loud warning, which is the difference between "I thought the sweep
was running fine" and "I know exactly which cell failed."

---

## 7. Cross-references

| Doc | What it covers |
|---|---|
| `tools/_gpu_watchdog.py` | The watchdog module (~240 LOC, stdlib-only) |
| `tests/test_tools/test_gpu_watchdog.py` | 9 unit tests |
| `docs/audit/wave98-sota-config-audit.md` | Wave 98.B — per-adapter SOTA alignment audit |
| `docs/audit/wave98-gpu-sota-final.md` | Wave 98.D — final consolidation |
| `docs/audit/wave96e-n1000-final.md` | Wave 96.E Kanzi N=10 sweep (the original stuck-process scenario) |
| `docs/audit/wave96-status-reality-check.md` | Wave 96 reality check (smoke-vs-N1000 + silent-hang diagnosis) |

Co-Authored-By: Claude Code <noreply@anthropic.com>
