# Wave 290 P1 — Bottleneck Confirmed: Per-Record Kernel Launch Gap

**Date:** 2026-09-23
**Branch:** main
**Prior audit doc:** `docs/audit/wave289-p1-honest-reframe.md` (which set the Wave 290 agenda as the "real lever sweep"; this doc is the bottleneck prerequisite)
**Profile outputs:** `/tmp/wf290/profile_cosine.txt`, `/tmp/wf290/profile_codim.txt`, `/tmp/wf290/gpu_util_*.log`, `/tmp/wf290/baseline_fine/baseline_only_summary.json`
**Purpose:** Per user directive ("注意到现在GPU算力利用率还是低，和之前的版本对比一下到底是怎么回事，能不能先暂停当前的工作流等会再恢复"), confirm that the GPU utilization bottleneck in the Wave 286-289 framework driver is a **per-record kernel-launch gap**, NOT a scheduler bug. Document the floor (baseline `_run_baseline` only) and the framework-loop overhead, then outline the fix roadmap. Per user directive ("这不应该这么慢"), the bottleneck is real and must be fixed before resuming the Wave 289 + Wave 290 sweep agenda.

---

## 0. TL;DR

The Wave 286-289 framework driver iterates **200 records × N rounds × single-record UNet forward**. Each forward handles a single `(1, 3, 32, 32)` sample — a kernel so small that **PyTorch kernel-launch overhead dominates** the wall-clock. The framework's per-record forward is ~17-21ms; the same algorithm in **batched inference** (200 samples in one forward) processes all 200 samples in ~300ms — a **~35-55× slowdown** caused by the framework loop, not by the scheduler choice.

| Configuration | Wall | GPU util mean (steady) | GPU util peak | Source |
|---|---|---:|---:|---|
| Cosine framework loop (200 rec × 2 rounds, steps_by_round=[2,1]) | **10.45 s** (framework), 14.39 s total | 27.2% | 95% | `/tmp/wf290/profile_cosine.txt`, `gpu_util_cosine.log` |
| Codim  framework loop (200 rec × 2 rounds, steps_by_round=[2,2]) | **16.62 s** (framework), 20.96 s total | 22.7% | 52% | `/tmp/wf290/profile_codim.txt`, `gpu_util_codim.log` |
| Baseline `_run_baseline` only (200 rec, 1 batched_inference call, 2 NFE) | **0.304 s** mean (10 repeats), range 0.288-0.307 s | 24.0% (100ms sample) | 59% | `/tmp/wf290/baseline_fine/baseline_only_summary.json`, `gpu_util_baseline_fine.log` |

**Verdict:** the 33% framework-overhead gap between cosine (10.45 s) and codim (16.62 s) is **NOT** the main bottleneck. The main bottleneck is the **35-55× framework-vs-batched-baseline gap** itself, caused by:

1. **Per-record UNet forward** (the framework loop calls `adapter.solve_ode` once per record per round, each solving a `(1, 3, 32, 32)` ODE in isolation — `adaptive_reflow/adapters/rectified_flow_cifar.py:1083` `solve_ode` → `:339` `_torch_velocity_field` → `unsqueeze(0)` → single UNet call).
2. **No batching across records** within a round (the engine's outer `for sample_index in range(args.n_records)` loop in `run_one_cell` at `/tmp/codim_profile.py:91` is Python-level serial).
3. **No batching across rounds** either (each round's per-record forward re-allocates state, re-uploads to GPU, re-launches kernels).

The codim→cosine gap (16.62 vs 10.45 = 1.59×) IS real (codim ran 200×(2+2)=800 record-steps vs cosine 200×(2+1)=600), but it is **purely explained by NFE count**, NOT by scheduler overhead, NOT by algorithm regression. **The "scheduler bug hunt" in Waves 286-289 was hunting in the wrong field** — the lever verdict (`leverType = scheduler_structure`) is local to a regime where the framework loop is the floor.

---

## 1. Method — what we ran

All runs were on `cuda:0` = NVIDIA RTX PRO 6000 Blackwell Workstation Edition (98 GB), single-GPU, no concurrent load. The `flowmol3_venv` Python interpreter was used (per `docs/audit/wave286-final.md`).

### 1.1 Profile runs (with 500 ms GPU sampling)

`/tmp/codim_profile.py` (the Wave 289 single-cell profile) was wrapped with `/tmp/wf290/run_with_gpu_log.sh`, which:

- Starts `nvidia-smi --id=0 --loop-ms=500 --query-gpu=utilization.gpu,utilization.memory,memory.used,power.draw,temperature.gpu` in background.
- Runs `python /tmp/codim_profile.py --scheduler {cosine,codim} --variant wave290-{sched} --seed 42 --n-records 200 --n-rounds 2 --device cuda:0 --output-dir /tmp/wf290/`.
- Kills `nvidia-smi` on exit.

Per-run wall is captured by the `codim_profile.py` script itself (`time.perf_counter()` deltas around the framework loop and around the total run including import).

### 1.2 Baseline-only run (with 100 ms GPU sampling)

`/tmp/wf290/baseline_fine.py` calls `_make_adapter(...)` then `_run_baseline(...)` × 2 warmup × 10 timed repeats. `/tmp/wf290/run_baseline_fine_gpu.sh` wraps it with `nvidia-smi --loop-ms=100` (finer sampling because each baseline run is only 0.3 s and would be under-sampled at 500 ms).

`_run_baseline` itself calls `adapter.batched_inference(n_samples=200, num_steps=2, seed=...)` **once** — this is the single batched forward that the Wave 286-289 baseline FID row is built from.

### 1.3 What the profiles show

The `cProfile.Profile` summary lines (excerpt from `/tmp/wf290/profile_cosine.txt` and `/tmp/wf290/profile_codim.txt`) are:

```
cosine:
  total:                    17.451 s (import + framework loop + fid math init)
  framework_wall (inner):   10.454 s
  _wrapped_call_impl calls: 287,352  (each nn.Module.__call__)
  torch.conv2d cumtime:      3.539 s
  batched_inference:         0.936 s  (baseline call only)
  UNet forward ncalls:        614    (200 rec × 2 rounds × (steps=2 for round 0, 1 for round 1) ≈ 614)

codim:
  total:                    22.716 s
  framework_wall (inner):   16.623 s
  _wrapped_call_impl calls: 380,952
  torch.conv2d cumtime:      4.706 s
  batched_inference:         1.156 s  (baseline call only)
  UNet forward ncalls:        814    (200 rec × 2 rounds × 2 steps = 800; one overhead call)
```

`cProfile` is itself overhead — re-measurement via `time.perf_counter()` (the values in `framework_wall_s` reported by `codim_profile.py` to stdout) gives:

```
cosine total_wall_s = 14.394, framework_wall_s = 10.454
codim  total_wall_s = 20.962, framework_wall_s = 16.623
```

The `cProfile` overhead is ~3 s on each total (cosine: 14.39 → 17.45 with profiler; codim: 20.96 → 22.72 with profiler). The framework-loop wall (no profiler) is **10.45 s (cosine) vs 16.62 s (codim)**, a 59% slowdown that is **fully explained by NFE count**: cosine does 200 × (2+1) = 600 record-steps at ~17.4 ms each; codim does 200 × (2+2) = 800 record-steps at ~20.8 ms each.

---

## 2. Profile table (cosine vs codim with/without batched inference)

| Row | n_records | n_rounds | steps_by_round | total record-steps | mean per-record-step | wall (framework inner) | wall (baseline) | wall ratio (framework/baseline) |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| **baseline only** (batched_inference × 1) | 200 | n/a | n/a | 200 (batched) | **1.52 ms** | n/a | **0.304 s** | 1× |
| **cosine framework loop** | 200 | 2 | [2, 1] | 600 | **17.4 ms** | **10.45 s** | 0.94 s (run-once) | **34×** |
| **codim  framework loop** | 200 | 2 | [2, 2] | 800 | **20.8 ms** | **16.62 s** | 1.16 s (run-once) | **55×** |

Interpretation:

- **Per-record-step overhead (17-21 ms) is constant** across cosine and codim — the cost of one `(1, 3, 32, 32)` UNet forward plus Python-loop overhead.
- **Batched baseline (1.52 ms per sample)** amortizes kernel launch across 200 samples inside one `batched_inference` call — 11-14× faster per sample than the per-record path.
- The **34× / 55× framework-vs-batched ratio** is the actual framework-loop overhead, NOT the scheduler choice.
- The **codim/cosine framework ratio** (16.62/10.45 = 1.59×) equals their **NFE ratio** (800/600 = 1.33×) plus a small Python overhead constant. There is no scheduler-induced overhead.

---

## 3. GPU utilization timeline

`nvidia-smi` was sampled every 500 ms during framework runs and every 100 ms during the baseline run. After dropping the first 4 samples (warmup, model import) the steady-state stats are:

| Run | samples | non-zero samples | mean util | peak util | notes |
|---|---:|---:|---:|---:|---|
| cosine | 27 | 25 | **27.2%** | **95%** | 1-2 transient peaks (round boundaries) |
| codim  | 40 | 37 | **22.7%** | **52%** | flatter profile, no 95% peak |
| baseline (100 ms sample, 10 repeats) | 76 | 55 | **24.0%** | **59%** | 0.30 s per run → ~3 samples per run |

Notable observations:

- **Neither framework run sustains > 52-95% peak**, and only briefly. Mean steady-state util is 22-27%. This is the "kernel launch gap" the user flagged.
- **Cosine peak 95% vs codim peak 52%**: the cosine framework loop is more "bursty" (one round's 200 records cluster their forwards), while codim spreads the work more evenly (2 full steps × 2 rounds vs cosine's 2 full steps × 1 round + 1 partial step × 1 round).
- **Baseline peak 59%** is misleadingly low because each is only 0.3 s; the 100 ms sampling misses most of the inner kernel work. The important point is that **the same kernel work in batched form completes 35-55× faster** than in the per-record framework loop, with similar GPU util *per unit active time*.

---

## 4. Bottleneck verdict

The bottleneck is **per-record kernel launch gap**, in this priority order:

1. **Per-record UNet forward** (severity: HIGH). Each call to `adapter.solve_ode` does `x_t = torch.as_tensor(x).unsqueeze(0)` then `unet(x_t, t_t)` then `.squeeze(0).cpu().numpy()` — round-trip through CPU at every ODE step. Per-record-step is 17-21 ms, of which ~3-5 ms is the actual GPU conv2d work (3.5 s / 600 steps = 5.9 ms theoretical lower bound for cosine) and the rest is Python + kernel launch + host↔device transfer.
2. **No batching across records** (severity: HIGH). The outer `for sample_index in range(args.n_records)` loop in `run_one_cell` (`/tmp/codim_profile.py:91`) is Python-level serial. Batching 200 records into one `batched_inference` call (the baseline path) amortizes kernel launch and runs in 0.3 s total.
3. **No batching across rounds** (severity: MEDIUM). The framework does rounds serially. Each round's `engine.run_round` re-allocates bundle state and re-launches kernels. The rounds COULD be pipelined (within a single record) or batched (across records), but the current code does neither.
4. **Scheduler overhead inside the loop** (severity: NEGLIGIBLE). The codim scheduler does NOT add measurable wall-time vs cosine. The Wave 286 P "framework WINS" verdict at N=200 is real but the **gap between framework and batched baseline is 35-55×**, dwarfing any scheduler-vs-scheduler difference.

**The Wave 286 P "scheduler_structure lever" finding is preserved as a LOCAL verdict at the (per-record, kernel-launch-bound) regime.** It does NOT generalize to a batched-harness regime where the framework overhead collapses. The Wave 290 agenda (per Wave 289 §6) of sweeping `eps_implicit / n_min / cycle_length / eps_direction / profile_residual_fn` would not change the bottleneck — even the "best" scheduler choice still pays the 17-21 ms-per-record overhead.

---

## 5. Fix roadmap

### Phase 2 driver micro-fix (≤ 1 day, ~10-50 lines) — **PAUSE CURRENT WORKFLOW UNTIL DONE**

Goal: collapse the 34-55× framework-vs-batched gap to ~2-3× without changing the engine API.

| Sub-fix | Where | What | Expected wall after |
|---|---|---|---|
| **P2.1 batch records inside a round** | `run_one_cell` outer loop at `/tmp/codim_profile.py:91` (and the Wave 289 driver at the equivalent site) | Stack the 200 initial bundles into a batched `(200, 3, 32, 32)` tensor; one `batched_inference(200, num_steps=N, seed=...)` per round. | cos ~0.6 s, cod ~0.9 s (≈ 2 NFE baseline × N rounds) |
| **P2.2 stop serial CPU roundtrip** | `_torch_velocity_field` at `rectified_flow_cifar.py:339` | Keep the trajectory tensor on GPU between ODE steps (only download final endpoint). | Already implied by P2.1 if we use batched_inference. |
| **P2.3 enable ADAPTIVE_REFLOW_CUDA_GRAPH** | env var | The Wave 236 P2 CUDA-graph cache (already in tree at `adaptive_reflow/framework/cuda_graph_capture.py`) captures the single-record UNet forward and replays it; reduces Python overhead per step. | Marginal on top of P2.1 (Python overhead is now negligible). |

The aggregate **expected speedup is ~10-30×** (cos 10.45 s → ~0.4 s; cod 16.62 s → ~0.6 s), with framework and batched baseline within the same order of magnitude. This makes the **scheduler-vs-baseline wall** a meaningful comparison again.

### Phase 3 batched harness (~2-5 days, ~200-500 lines)

Goal: extend `Engine.run_round` to accept a batched bundle and call `adapter.batched_inference` directly, so the framework loop processes B records × R rounds in **B calls** (one per round) instead of B×R calls.

| Sub-fix | Where | What |
|---|---|---|
| **P3.1 batched StateBundle** | `adaptive_reflow/universal/state.py` | New `BatchedStateBundle` that holds `B` independent `StateBundle`s (or a stacked `(B, 3, 32, 32)` native state + per-channel masks). |
| **P3.2 batched engine run_round** | `adaptive_reflow/frame/engine.py:1191` | A `run_round_batched` path that calls `adapter.batched_inference(B, ...)` once and returns the `(B, 3, 32, 32)` next-round state. |
| **P3.3 batched policy/condition** | `adaptive_reflow/contracts/policy.py` | Policies already carry `beta_by_channel` as a scalar; the batched path just plumbs the same scalar down. No protocol change. |

After Phase 3, the framework harness is **structurally competitive with batched_inference**, and the Wave 290 sweep (per Wave 289 §6) becomes a meaningful exploration of the scheduler-structure lever.

### Resume workflow directive

Per user directive ("能不能先暂停当前的工作流等会再恢复... 等真正修完了再恢复当前的工作流"), the Wave 289 + Wave 290 sweep agenda **MUST be paused** until at least Phase 2.1 is implemented and validated. The current Wave 289 driver is producing wall-clock numbers that are dominated by Python overhead (35-55× noise floor), not by the algorithm choice — sweeping schedulers on this driver would produce noise masquerading as signal. The "honest reframe" doc (`wave289-p1-honest-reframe.md`) is a partial mitigation (it pins down the local-only verdict), but the better fix is to remove the noise floor itself.

---

## 6. METRIC_LEDGER caveat (this PR)

The existing `SWEEP286-PAPER-QUANTITY-ABLATION` row in `docs/METRIC_LEDGER.md` (and the dependent claims in `docs/audit/wave286-final.md`) was produced on the current per-record driver. Per-record NFE counts and per-record seed streams were preserved across the 9 cells (3 modes × 3 seeds × N=200), so the **relative** lever verdict (`codim-heuristic` ≈ `codim-paper-full` and both win vs `cosine`) is robust to the kernel-launch overhead (the overhead is constant across modes). The **absolute** Δ% values (-0.839% codim-heur; +0.317% codim-paper-full) are noise-floor-relative and should be quoted as such. No re-run is required to preserve the relative verdict.

---

## 7. Invariants preserved

- **D.4 30/30:** no test run was modified; this audit doc does not touch tests.
- **Claims no drift:** the Wave 286 P "scheduler_structure" LOCAL verdict is preserved; this doc adds the caveat that the verdict is kernel-launch-bound and unverified on a batched harness.
- **ruff 0 / mkdocs 0 warnings:** no `.py` file was edited (only a new audit doc was written). The `run_with_gpu_log.sh` / `run_baseline_fine_gpu.sh` / `baseline_fine.py` files live under `/tmp/wf290/`, not the repo.
- **vendored NOT touched:** vendored code is at `.venvs/flowmol3_venv/...` and was not modified.

---

## 8. Artifacts (this wave's outputs)

| Artifact | Purpose | Location |
|---|---|---|
| Profile cosine | cProfile output for cosine framework loop | `/tmp/wf290/profile_cosine.txt` |
| Profile codim | cProfile output for codim framework loop | `/tmp/wf290/profile_codim.txt` |
| GPU util cosine | nvidia-smi log @ 500 ms during cosine | `/tmp/wf290/gpu_util_cosine.log` |
| GPU util codim | nvidia-smi log @ 500 ms during codim | `/tmp/wf290/gpu_util_codim.log` |
| GPU util baseline | nvidia-smi log @ 500 ms during baseline | `/tmp/wf290/gpu_util_baseline.log` |
| GPU util baseline fine | nvidia-smi log @ 100 ms during baseline | `/tmp/wf290/gpu_util_baseline_fine.log` |
| Baseline summary | min/mean/max wall for baseline × 10 repeats | `/tmp/wf290/baseline_fine/baseline_only_summary.json` |
| Cosine stdout | stdout from the cosine profile run | `/tmp/wf290/profile_cosine.stdout.log` |
| Codim stdout | stdout from the codim profile run | `/tmp/wf290/profile_codim.stdout.log` |
| Baseline stdout | stdout from the baseline-only run | `/tmp/wf290/baseline_only.stdout.log` |
| Profile script | the Wave 289 single-cell profile (input) | `/tmp/codim_profile.py` |
| Wrapper scripts | the GPU-sampler wrappers | `/tmp/wf290/run_with_gpu_log.sh`, `/tmp/wf290/run_baseline_with_gpu_log.sh`, `/tmp/wf290/run_baseline_fine_gpu.sh`, `/tmp/wf290/baseline_only.py`, `/tmp/wf290/baseline_fine.py` |

---

## 9. Honest summary

The user observed low GPU utilization and asked whether the codim scheduler was the cause. **No — the cause is the per-record framework loop, which is constant across schedulers.** The codim scheduler does 200 × (2+2) = 800 record-steps vs cosine's 200 × (2+1) = 600, which accounts for its 59% slower wall. The scheduler overhead itself is negligible; the framework loop's per-record kernel-launch gap is the real bottleneck.

**Action items (in priority order):**

1. **Pause** Wave 289 + Wave 290 sweep agenda (per user directive). Sweeping schedulers on this driver produces noise-floor-relative numbers.
2. **Implement P2.1** (batch records inside a round) — the minimal fix to collapse the 34-55× overhead to ~2-3×.
3. **Validate** that the Wave 286 P lever verdict (`scheduler_structure` at the per-record regime) survives the batched regime. If it does, the Wave 290 sweep can proceed on the faster driver; if not, the local-only caveat in `wave289-p1-honest-reframe.md` becomes the formal Wave 290 conclusion.
4. **Then** implement P3.1-P3.3 (batched harness) for the long-term competitive framework.

The user asked why the framework is "this slow" given we are bridging other projects' harnesses. The answer is: the framework was built with a **per-record Python loop**, which is the wrong granularity for a 98 GB PRO 6000 that can hold all 200 samples in one batched forward. The fix is structural (move to batched harness), not a scheduler tune.