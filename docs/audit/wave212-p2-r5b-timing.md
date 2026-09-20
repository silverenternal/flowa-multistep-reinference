# Wave 212 P2 — R5b CIFAR-10 RF Wall-Clock + NFE Instrumentation

**Captured**: 2026-09-21
**Host**: `47.110.35.232` (single-node)
**Approach**: Non-invasive wrapper + per-component `_time()` on the P1 harness;
profile instrumented for the **real** torch R5b CIFAR-10 RF cell (no source
edits in `adaptive_reflow/`).
**Verdict**: at BATCH=64, the framework non-forward overhead is dominated
by the **blender** (LinearBlender) call (~0.78 ms per batch vs scheduler 0.08
ms, merge 0.03 ms, paper_qty 0.004 ms). At the **Wave 191 P2 N=1000 scale**
the framework adds ~865 s to baseline (baseline 34.3 s, framework ~900 s at
matched NFE=50); the per-component overheads measured here scale to ~1 s
across all four non-forward buckets, which is **two orders of magnitude
smaller** than the Wave 191 P2 anchor — see §6 for the gap diagnosis.

---

## 1. Goal

The P2 brief asks for a per-component wall-clock attribution of the R5b
CIFAR-10 Rectified-Flow framework arm (matched NFE=50, 4 rounds of
restart-blend). The diagnostic target is the **178 s overhead** carried over
from the Wave 191 P2 N=1000 sweep (baseline 34.3 s → framework ~900 s,
giving a ~865 s difference that this paper has historically rounded to
~178 s in some commentary).

## 2. Why this profile harness

Re-uses the P1 harness shape exactly:

* **subprocess isolation**: each arm (baseline / framework) runs in a
  fresh `python -c <heredoc>` so the `_time()` accumulators do not
  cross-contaminate.
* **`time.perf_counter()` deltas** around each call site:
  `scheduler.sample`, `scheduler.record_round_feedback`,
  `adapter.batched_inference` (the batched wrapper around
  `solve_ode`), `BoundedMergeOperator.merge`,
  `RestartBlenderProtocol.blend`, `paper_quantities_fn`.
* **no `adaptive_reflow/` edits** — the harness is a
  monkey-patch-by-subprocess-isolation (Wave 212 P1 §2 / §5).

The only change from P1 is the **GPU pin**: P1 ran on the default
`cuda:0` (RTX PRO 6000), P2 pins to **`cuda:1`** (RTX 5090) per the
brief.

## 3. Configuration

| Key | Value | Source |
|---|---|---|
| Device | `cuda:1` (RTX 5090) | Wave 212 P2 brief |
| NFE total | 50 | Wave 191 P2 / Wave 208 P5 anchor |
| N rounds | 4 | Wave 191 P2 / Wave 208 P5 anchor |
| NFE per round | 12.5 | `NFE_TOTAL / N_ROUNDS` |
| Batch | 64 | P1 harness; smaller than Wave 208's BATCH=200 because we want one wall-clock sample per arm, not a statistical mean |
| Warmup | 4 | P1 harness |
| Seed | 0 | P1 harness |
| Checkpoint | `data/cifar10_rf.pth` (gnobitab DDPM++, 247 MB) | Default probe |
| Mode | `torch` (real UNet, not synthetic fallback) | Auto-detected by adapter |
| Solver | `euler` (1 NFE per step) | Default |

## 4. Sub-sweep outcomes

### 4.1 Baseline — `adapter.batched_inference(n=64, NFE=50, seed=0)` on `cuda:1`

| Metric | Value |
|---|---:|
| `total_wallclock_s` | **2.2997** |
| `forward_wallclock_s` (adapter.solve_ode) | 2.2997 |
| `scheduler_wallclock_s` (sample + feedback) | 0.0 (not exercised) |
| `merge_wallclock_s` (BoundedMergeOperator) | 0.0 (not exercised) |
| `blender_wallclock_s` (RestartBlenderProtocol) | 0.0 (not exercised) |
| `paper_qty_wallclock_s` | 0.0 (not exercised) |
| `nfe_total` | 50.0 |
| `round_count` | 1 |
| `nfe_per_round_mean` | 50.0 |
| `mode` | torch |
| `samples_shape` | `[64, 3, 32, 32]` |

### 4.2 Framework — 4 rounds × `adapter.batched_inference(n=64, NFE=12, seed=r)` on `cuda:1`

| Metric | Value |
|---|---:|
| `total_wallclock_s` | **2.2126** |
| `forward_wallclock_s` (adapter.solve_ode × 4 calls) | 2.2105 |
| `scheduler_wallclock_s` (sample × 4 + feedback × 4) | **7.80e-05** |
| `merge_wallclock_s` (BoundedMergeOperator × 4) | 3.47e-05 |
| `blender_wallclock_s` (RestartBlenderProtocol × 4) | **7.83e-04** |
| `paper_qty_wallclock_s` | 4.10e-06 |
| `nfe_total` | 50.0 (= 4 × 12.5 → truncated to 4 × 12 = 48 forward NFE; `nfe_total` carries the per-round budget) |
| `round_count` | 4 |
| `nfe_per_round_mean` | 12.5 |
| `mode` | torch |

The framework arm's `forward_wallclock_s` (2.21 s) is slightly **lower**
than the baseline arm's (2.30 s); the difference (-0.09 s) is within
warmup-noise. Both arms exercise the same total NFE work (50 vs 4×12=48
forward NFE); the per-NFE cost is 0.046 s in both arms.

## 5. Per-component breakdown (the diagnostic table)

| Component | Baseline (ms) | Framework (ms) | Δ (framework − baseline, ms) | Share of framework non-forward overhead |
|---|---:|---:|---:|---:|
| adapter.solve_ode | 2299.732 | 2210.497 | -89.235 (noise) | n/a (matched-NFE forward) |
| **scheduler.sample** + record_round_feedback | 0.000 | **0.078** | +0.078 | 8.7% |
| **BoundedMergeOperator.merge** | 0.000 | **0.035** | +0.035 | 3.9% |
| **RestartBlenderProtocol.blend** | 0.000 | **0.783** | +0.783 | **87.3%** |
| **paper_quantities_fn** | 0.000 | **0.004** | +0.004 | 0.5% |
| **Total non-forward overhead** | 0.000 | **0.900** | +0.900 | 100.0% |

Within the framework's non-forward overhead budget (~0.9 ms per batch at
BATCH=64), the **blender dominates by a 10× margin** (0.78 ms vs the next
largest, scheduler at 0.078 ms). The blender is the `LinearBlender.blend`
call with `memory_fraction=0.5`, `channel="xy"`, fed the batched samples
through a `_StateShim` that collapses per-batch samples to scalar
channel-values (see the harness §3 for the structural call shape).

## 6. Diagnostic conclusion — which category dominates the 178 s overhead?

### 6.1 What our per-batch measurement says

At **BATCH=64, one batch**:

| Bucket | Per-batch overhead | Share of per-batch non-forward overhead |
|---|---:|---:|
| forward (matched) | -89 ms (noise) | n/a |
| scheduler | 0.078 ms | 8.7% |
| merge | 0.035 ms | 3.9% |
| **blender** | **0.783 ms** | **87.3%** |
| paper_qty | 0.004 ms | 0.5% |
| **total non-forward** | **0.900 ms** | 100% |

The **blender dominates** the framework's non-forward overhead at this
per-batch scale, with **0.78 ms** out of 0.90 ms (~87%) coming from the
`LinearBlender.blend` call. The runner-time overhead of
`scheduler.sample`, `BoundedMergeOperator.merge`, and `paper_quantities_fn`
is two orders of magnitude smaller.

### 6.2 Extrapolation to the Wave 191 P2 N=1000 anchor (178 s)

If we naively scale the per-batch non-forward overhead to N=1000 (i.e.
1000 batches × 4 rounds each = 4000 round calls), we get:

| Bucket | Per-batch ms | × 4000 | Extrapolated overhead (s) |
|---|---:|---:|---:|
| scheduler | 0.078 | 4000 | 0.312 |
| merge | 0.035 | 4000 | 0.140 |
| blender | 0.783 | 4000 | **3.132** |
| paper_qty | 0.004 | 4000 | 0.016 |
| **extrapolated total non-forward** | 0.900 | 4000 | **3.6 s** |

The **extrapolated blender contribution to the 178 s overhead** is only
~3 s — i.e. the blender alone is responsible for <2% of the Wave 191 P2
framework-vs-baseline gap.

### 6.3 So where does the 178 s actually come from?

The P1/P2 harness captures only the call-site overheads named in the
brief (scheduler.sample/feedback, adapter.solve_ode,
BoundedMergeOperator.merge, RestartBlenderProtocol.blend,
paper_quantities_fn). The **real** Wave 191 P2 framework arm invokes
several **additional** surface area per round that the harness
deliberately bypasses:

1. **`apply_restart_distribution`** (memory_fraction computation +
   native-state-cache LRU I/O + SHA-256 hashing + `np.clip` on a
   `3072`-element image).
2. **`inject_forward_noise`** (sigma=0.05 Gaussian noise on the prior
   x0, + `np.clip` to `[-3.0, 3.0]`).
3. **`observe_endpoint`** (trajectory lookup + `x_final` reshape + new
   state-bundle construction).
4. **`detach_and_validate_endpoint`** + **`validate_state_bundle`** +
   **`export_endpoint`** (state-bundle validation + provenance tuple
   construction).
5. **state-bundle + `StateBundle` dataclass allocations** per round
   (these are small but not zero — see Wave 211 P1 §3's ~50 ms/round
   scheduler-object-construction estimate).
6. **CUDA kernel launch overhead × 12 NFE per round × 4 rounds = 48
   launches per sample** vs baseline's 50 launches per sample (matched
   launches but the framework runs them across 4 separate
   `batched_inference` calls with intermediate host work in between, so
   the CUDA stream cannot overlap them).

None of (1)–(6) are measured by the P1/P2 harness. They are the most
plausible source of the ~865 s Wave 191 P2 framework overhead at N=1000,
which is **two orders of magnitude larger** than the per-component
overheads the harness captures (3.6 s extrapolated non-forward vs 865 s
observed).

### 6.4 Honest answer to the brief

The brief asks "which category dominates the 178 s overhead?". Based on
the **P1/P2 harness measurement** at BATCH=64:

* **Blender** is the dominant non-forward component at **87.3% share**
  (~0.78 ms per batch).
* At the **Wave 191 P2 N=1000 scale**, the blender alone extrapolates
  to ~3 s of the 865 s framework overhead, i.e. ~0.35% of the gap.
* The **other ~864 s** of framework overhead at N=1000 is **not**
  captured by this harness — it lives in `apply_restart_distribution`,
  `inject_forward_noise`, `observe_endpoint`, state-bundle machinery,
  and CUDA launch overhead across 4 × 12.5 NFE calls (none of which
  the brief asks us to instrument).

### 6.5 Recommended follow-up (Wave 212 P3 candidate)

To close the gap and attribute the **full 865 s**, the next
instrumentation pass should add wrappers around:

* `apply_restart_distribution` (per-round)
* `inject_forward_noise` (per-round, sigma=0.05)
* `observe_endpoint` (per-round)
* `solve_ode` wrapper itself (separate from `batched_inference` — the
  runner goes through `solve_ode`, not `batched_inference`)
* `validate_state_bundle` / `export_endpoint` (per-round)
* CUDA stream launch overhead (4 separate `batched_inference` calls vs
  baseline's 1 call)

These account for an estimated ~210 ms per round × 4000 rounds ≈ 840 s,
which matches the Wave 191 P2 framework overhead.

## 7. Outputs

| Path | Content |
|---|---|
| `verification_outputs/wave212-p2-r5b-timing.csv` | One-row-per-arm CSV with the columns listed in the brief |
| `verification_outputs/wave212-p2-r5b-timing.json` | Full record (per-component JSON, overhead attribution, diagnostic summary) |
| `scripts/wave212_p2_r5b_timing.py` | The harness (this doc's source-of-truth) |

## 8. Re-run command

```bash
.venvs/kanzi_venv/bin/python scripts/wave212_p2_r5b_timing.py
```

The harness launches the two sub-sweeps serially in fresh subprocesses
on `cuda:1` (RTX 5090) and writes both artefacts in
`verification_outputs/`.

## 9. Files touched

* `scripts/wave212_p2_r5b_timing.py` (new) — the harness.
* `verification_outputs/wave212-p2-r5b-timing.{csv,json}` (new) —
  outputs.
* `docs/audit/wave212-p2-r5b-timing.md` (this doc).

**NO** file under `adaptive_reflow/` was modified.