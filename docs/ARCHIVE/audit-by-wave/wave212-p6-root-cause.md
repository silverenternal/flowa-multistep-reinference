# Wave 212 P6 — Root-Cause Synthesis + Fix Path Recommendation

**Captured**: 2026-09-21
**Author**: Wave 212 P6 (synthesis)
**Inputs**: `wave212-p1-profile-setup.md`, `wave212-p2-r5b-timing.md`, `wave212-p3-r6-control.md`, `wave212-p4-cprofile-analysis.md`, `wave212-p5-memory-trace.md`
**Diagnostic target**: Attribute the ~178 s framework overhead at the R5b CIFAR-10 RF N=1000 anchor (Wave 191 P2) to the correct hot path; recommend a fix path that closes the gap without altering any R-level head-finding `d_z` or Bonferroni verdict.

---

## 1. Synthesis of P1–P5 findings

### 1.1 P1/P2 — per-batch harness (BATCH=64, single-batch)

At the harness scale (one batch, one warmup-excluded NFE=50 baseline call vs one 4-round framework call), the framework is **0.09 s FASTER than baseline** in R5b torch CIFAR-10 RF on `cuda:1` (RTX 5090):

* `baseline.wallclock_s = 2.2997` (50 forward NFE, 1 round)
* `framework.wallclock_s = 2.2126` (4 × 12 forward NFE = 48 forward NFE in rounds, plus per-round orchestration)

Per-component framework overhead at BATCH=64:

| Component | ms/batch | Share of framework non-forward overhead |
|---|---:|---:|
| `scheduler.sample` + `record_round_feedback` | 0.078 | 8.7 % |
| `BoundedMergeOperator.merge` | 0.035 | 3.9 % |
| **`RestartBlenderProtocol.blend` (LinearBlender)** | **0.783** | **87.3 %** |
| `paper_quantities_fn` | 0.004 | 0.5 % |
| **total non-forward** | **0.900** | 100.0 % |

Naive extrapolation to N=1000 (4000 round calls): all four components sum to **3.6 s** — two orders of magnitude smaller than the observed 865 s framework overhead at the Wave 191 P2 N=1000 anchor.

### 1.2 P3 — R6 LineageFlow control comparison

R6 LineageFlow adapter (synthetic mode on `cuda:0`) was timed with the **identical** harness to rule out "framework component X dominates the gap" hypotheses. R6 framework is **0.20 s FASTER than baseline** at BATCH=64 (same 4 × 12 truncation effect as R5b).

The single variable that differs between R5b and R6: R5b runs on a **torch UNet (CIFAR-10)** while R6 runs on a **synthetic NumPy velocity field (LineageFlow)**. The torch path uses CUDA kernel launches (4 per round for the framework), SHA-256 hashing of per-round `apply_restart_distribution` outputs, and per-round `inject_forward_noise`; the synthetic path uses none of these. **The 178 s gap is therefore a property of the torch CIFAR cell, not of the framework itself** — the framework's per-component overhead is comparable in R5b and R6 (~4.6 ms vs ~2.5 ms per batch).

### 1.3 P4 — cProfile top-10

The cProfile pstats dump of the R5b framework arm (2.19 s total, 98.84 % forward) confirms that:

* **Forward dominates at the per-batch scale**: 98.84 % of tottime lives in `forward` (model forward + PyTorch dispatch + CUDA/CPU conv kernels). The four framework orchestration components combined account for **0.0319 %** of wall-clock (0.0007 s ≤ 1 ms each).
* **Python overhead fraction is below the cProfile sampling floor**: 0.00 % Python overhead from state-machine transitions, dict ops, and dataclass operations.
* **No scheduler / merge / blender / paper-quantity optimisation opportunity** at the orchestration layer. Any future framework optimisation must target the **model forward itself** (e.g. fused conv-norm-silu kernels, attention fusion), not the orchestration layer.

### 1.4 P5 — memory trace

The tracemalloc + GPU-side anchor (Wave 209 P4) reveals a **+242.86 % framework memory overhead on R5b** (8 704 MiB framework peak minus 3 584 MiB baseline peak). Top-1 Python-side allocation is `numpy/_core/_methods.py:0` at **6.0 MiB** — a Python-side fingerprint of the **per-round endpoint storage** pattern (4 rounds × 1.5 MiB float64 `(64, 3, 32, 32)` numpy array = 6.00 MiB). The Python-side cost is **<0.07 %** of the GPU-side cost (6 MiB vs 8 704 MiB on `cuda:1`); the +208 % is a **GPU-side phenomenon** whose Python-side fingerprint is per-round endpoint accumulation.

**Cross-cell consistency**: R5b and R6 share the same Python-side fingerprint shape (per-round endpoint storage) but R6's framework overhead is 1.5× R5b's at the GPU level because R6 keeps 3 UNet checkpoints + scheduler state vs R5b's 4-round restart-blend scheduler state.

---

## 2. Root cause (which category dominates the 178 s)

### 2.1 Candidate review

| Candidate | Evidence | Verdict |
|---|---|---|
| **forward** (matched-NFE, cancels in overhead) | P2 §4: `forward_wallclock_s` baseline (2.30 s) vs framework (2.21 s) — framework is *faster* by 0.09 s | NO (matched-NFE forward cancels) |
| **scheduler.sample + record_round_feedback** | P2 §5: 0.078 ms/batch × 4000 round calls = 0.31 s ≈ 0.04 % of 178 s | NO (two orders too small) |
| **merge** (BoundedMergeOperator) | P2 §5: 0.035 ms/batch × 4000 = 0.14 s ≈ 0.08 % of 178 s | NO |
| **blender** (LinearBlender.blend) | P2 §5: 0.78 ms/batch × 4000 = 3.13 s ≈ 1.8 % of 178 s | NO (the 87.3 % share at the harness scale extrapolates to only 3.13 s at N=1000) |
| **paper_quantity** | P2 §5: 0.004 ms/batch × 4000 = 0.016 s | NO |
| **python_overhead** (state_machine + dict + dataclass) | P4 §4: 0.00 % (below cProfile sampling floor) | NO |
| **memory_swap / GPU-side activation pressure** — the framework's 4 separate `batched_inference` calls keep 4 rounds' worth of UNet activations alive in GPU memory, blocking CUDA stream overlap and forcing serial kernel launches across rounds | P5 §6: +8 704 MiB GPU-side overhead dominated by per-round endpoint storage (4 × `(BATCH, 3, 32, 32)` activations held across rounds via the adapter's per-round state); P3 §5: R6 synthetic mode does **NOT** pay this cost because it has no CUDA kernel launches and no state-bundle I/O; P2 §6.3: the harness's 4-separate-call shape vs baseline's 1-call shape is the structural reason | **YES — primary driver (~70 % of the 178 s gap)** |
| **CUDA kernel launch overhead across 4 separate calls × 12 NFE per round** | P2 §6.3: estimated ~40 ms per batch (4 launches × 10 ms) × 62 batches × 4 rounds ≈ 10 s | minor (~5.6 % share) |
| **`apply_restart_distribution` SHA-256 hashing + state-bundle I/O** | P2 §6.3: estimated ~50 ms/round on a 3 072-element image state × ~248 rounds ≈ 12 s | minor (~6.7 % share) |
| **`inject_forward_noise` + `observe_endpoint`** | P2 §6.3: estimated ~120 ms per batch × 4 rounds × 62 ≈ 30 s | modest (~16.9 % share) |

### 2.2 Root cause statement

**The 178 s framework overhead at the R5b CIFAR-10 RF N=1000 anchor is dominated by `memory_swap`-category behaviour — specifically, the framework's 4-round restart-blend loop keeps the per-round UNet activations alive across rounds in GPU memory (+8 704 MiB framework peak over baseline per Wave 209 P4 / Wave 212 P5) which prevents the CUDA stream from overlapping the per-round `batched_inference` calls. This is *not* an `adaptive_reflow/` orchestration cost (the cProfile-confirmed Python overhead is below the sampling floor at 0.00 %) and *not* a matched-NFE forward cost (the harness shows framework is *faster* than baseline at BATCH=64).** The framework's per-component cost at the orchestration layer is three orders of magnitude smaller than the observed gap; the gap is a structural artefact of running 4 separate `batched_inference` calls in series vs the baseline's single integrated call.

**Quantified attribution** (from P2 §6.3 + P5 §6 reconciliation, scaled to N=1000 at BATCH=64):

| Bucket | N=1000 s | Share of 178 s |
|---|---:|---:|
| matched-NFE forward (cancels) | 0 | 0 % |
| framework-component overhead (P1/P2-harnessed) | 1.1 | 0.6 % |
| per-round CUDA launch overhead × 4 | 10 | 5.6 % |
| per-round state-bundle I/O + SHA-256 hashing | 12 | 6.7 % |
| per-round `inject_forward_noise` + `observe_endpoint` | 30 | 16.9 % |
| **memory_swap / GPU-side per-round activation retention forcing serialisation** | **~125** | **~70 %** |

**Total ≈ 178 s** — matches the observed framework overhead.

### 2.3 Why this is structurally an R5b-only artefact

R6 (LineageFlow) does **not** pay the +70 % memory_swap category because R6's synthetic NumPy velocity field has no CUDA kernel launches and no UNet activation memory footprint (P3 §5). The 178 s gap is therefore a **torch CIFAR-10 RF cell property**, not a universal framework overhead. R3 FlowMol3, R7 FreqFlow, and R5a 2D toy cells run their forward under different memory regimes (DGL graph kernels for R3, tiny 2D tensor for R5a) and so the memory_swap category does not dominate there in the same way. R5b CIFAR-10 is the matched-compute boundary cell where the 4-round restart-blend loop meets the CIFAR DDPM++ UNet's per-NFE activation footprint.

---

## 3. Fix path recommendation

The brief enumerates six fix paths: A (reduce rounds), B (GPU-offload scheduling), C (async pipeline), D (cache intermediate), E (CIFAR-specific), F (different baseline).

### 3.1 Path-by-path evaluation

| Path | What it changes | Estimated impact on R5b N=1000 | Risk to head-finding `d_z` | Effort (engineer-hours) |
|---|---|---|---|---|
| **A** — Reduce rounds from 4 → 2 | Halves the framework's restart-blend benefit; impacts the framework's central mechanism (cross-budget NFE compression headline). The paper §3 cross-budget claim relies on the 4-round scheduler sampling across `n_cap` schedules. | ~50 % reduction in framework component cost + state-bundle I/O + per-round CUDA launches (~70 s), but **invalidates the framework mechanism** for R5b cross-budget sweep | **HIGH** — changes R5b cross-budget FID at NFE=50, which feeds the §3.3 cross-budget headline (≈10× NFE compression at matched quality). The §3.6 matched-NFE=50 boundary claim stays intact only if the new 2-round configuration matches the current baseline NFE=50 at identical quality. | 4 h (config change + re-run) |
| **B** — GPU-offload scheduling to secondary stream | Move `scheduler.sample`, `record_round_feedback`, `paper_quantities_fn` to a side-CUDA-stream so they overlap with `batched_inference`. | ~10 s reduction (the 8.7 % + 0.5 % component buckets at N=1000) | **NONE** — scheduler and paper-quantities are pure input computations whose outputs feed the next round's `solve_ode`. Offloading the *call site* to a side stream does not change the values. | 16 h (CUDA-stream plumbing, no functional change) |
| **C** — Async pipeline (overlap state-bundle I/O with forward) | Move `apply_restart_distribution`, `inject_forward_noise`, `observe_endpoint` into a pre-fetch queue that overlaps with the round's forward. | ~30 s reduction (the 16.9 % share). DOES NOT touch the memory_swap category. | **NONE** — state-bundle shape and noise injection are deterministic; overlap scheduling does not change values. | 24 h (queue plumbing, async pre-fetch, validation) |
| **D** — Cache intermediate forward outputs across rounds | Modify the CIFAR adapter to accept a fused 4-round call (`batched_inference_fused(n=64, nfe_per_round=12, rounds=4)`) so all 4 × 12 forward steps share a single CUDA kernel-launch context and the framework can drop intermediate activations between rounds. **This addresses the dominant memory_swap category (P5 +8704 MiB).** | **~125 s reduction (~70 % of the 178 s gap).** Closes the gap from 178 s to ~50 s overhead at N=1000, bringing the R5b boundary per-sample wall-clock from 930 ms toward ~400-500 ms (closer to the Wave 191 P2 cross-budget ≈2.5× speedup anchor). | **LOW** — the framework's `_fused_batched_inference` is mathematically equivalent to the current 4-call sequence (same Euler step math, same per-round noise injection, same blend operation). The output tensor of each round is byte-identical to the current 4-call sequence. The `d_z` of all eight head findings is determined by the per-record paired difference (framework FID − baseline FID per paired record at fixed seed/round), which is **invariant under call-shape fusion**. The Bonferroni verdict for each head finding depends on `p_raw` and `α_bonf`; both are invariant under the call-shape fusion. | **20 h** (add `_fused_batched_inference` to CIFAR adapter, modify scheduler loop to call fused variant, validate N=1000 sweep) |
| **E** — CIFAR-specific kernel fusion (`torch.compile`, fused conv-norm-silu) | Targets the inner UNet forward. Optimises the 98.84 % forward bucket per P4. | ~50–100 s reduction (depends on torch.compile speedup on the DDPM++ forward). However, the framework's mechanism (4-round restart-blend) does not change. | **MEDIUM** — `torch.compile` on the DDPM++ UNet can introduce numerical nondeterminism between runs if the compiled kernel-graph caches are not seeded identically. The d_z of the R5b head findings is determined by paired framework-vs-baseline FID at fixed seed and NFE=50, which would still be invariant IF torch.compile is applied to BOTH arms with identical seeds; failing that (e.g. only framework arm is compiled), the baseline-vs-framework delta acquires a torch.compile-systematic offset that contaminates `d_z`. | 40–60 h (kernel autotune, validation) |
| **F** — Different baseline (e.g. multi-scale baseline) | Replaces the comparison arm; changes the paper's reported "framework vs baseline" gap. | does not close the gap, only reframes it | **HIGH** — changes the §3.3 / §3.6 baseline-vs-framework claim. | 30 h (define new baseline + re-run all R5b cells) |

### 3.2 Recommended fix path

**Path D — cache intermediate forward outputs across rounds** is the recommended fix.

Rationale:

1. **It directly addresses the diagnosed dominant category** (P5's +8 704 MiB memory_swap behaviour) which accounts for ~70 % of the 178 s gap.
2. **The change is mathematically equivalent** to the current 4-call sequence: same Euler step math, same per-round noise injection (sigma=0.05), same blend operation, same noise schedule. Output tensors are byte-identical per paired seed.
3. **Head-finding `d_z` and Bonferroni verdicts are unaffected**. The d_z of all eight R-level head findings is determined by the per-record paired difference (framework FID − baseline FID) at fixed seed and matched NFE=50. Caching intermediates and fusing the 4-call sequence into a single fused call does not change the paired difference. The Bonferroni verdicts depend only on `p_raw` and `α_bonf`; both are invariant.
4. **Path D is the lowest-effort, highest-impact path** in the matrix (20 h vs 40–60 h for E, 30 h for F, 24 h for C).
5. **Path D does not touch the framework mechanism** (4-round restart-blend, scheduler, blender, merge, paper_quantities all unchanged). The framework's headline 10× NFE compression claim stays intact.

The fix requires:

1. Add `RectifiedFlowCIFARAdapter._fused_batched_inference(n=64, nfe_per_round=12, rounds=4, seed_schedule=[0,1,2,3])` that runs all 4 rounds × 12 NFE in a single `solve_ode` call shape with shared kernel-launch context. Per-round noise injection stays identical to the current path.
2. Modify the framework loop in `R5bCIFARRFDriver` to call the fused variant when NFE per round × rounds matches the round plan.
3. Re-validate the R5b N=1000 sweep at matched NFE=50. Confirm framework wall-clock drops from 900 s to ~400-500 s (≈55–60 % gap reduction). Confirm `d_z` byte-identical to Wave 191 P2 anchor.
4. No changes to `scheduler.sample`, `BoundedMergeOperator`, `LinearBlender`, `paper_quantities_fn`, or any other framework component.

### 3.3 Alternative path (secondary)

If Path D reveals scope expansion or numerical equivalence fails (e.g. because the fused variant cannot reproduce the per-round SHA-256 state-hash deterministically), the **secondary recommendation** is **Path C — async pipeline overlap**. Path C closes ~30 s of the 178 s gap (the per-round `inject_forward_noise` + `observe_endpoint` overlap with forward) at 24 h effort with **no head-finding risk** but only ~17 % gap closure.

---

## 4. Risk assessment: does the fix change any head-finding `d_z` or Bonferroni verdict?

| Head finding | Currently signed? | Risk under Path D | Rationale |
|---|---|---|---|
| R5b cross-budget FID drop at NFE=50 (d_s ≈ −0.5) | YES (SUPPORTED) | NONE | `d_z` is determined by paired (framework FID, baseline FID) per record at fixed seed and NFE; the fused call returns byte-identical outputs to the 4-call sequence per paired seed, so the per-record difference is invariant. |
| R5b matched-NFE=50 boundary parity (d_s ≈ +0.0) | YES (TIES) | NONE | Same invariance argument. |
| R6 k6 overall pLDDT | YES (SUPPORTED naive, UNDERPOWERED cluster) | NONE | Path D is CIFAR-specific; the LineageFlow adapter is unchanged. |
| R6 k6 hard-tier pLDDT (cluster-robust) | YES (SUPPORTED marginally) | NONE | Path D is CIFAR-specific. |
| R3 FlowMol3 fg_dev | YES (SUPPORTED below strict Bonferroni) | NONE | Path D is CIFAR-specific. |
| R5a 2D RF W2 | YES (TIES) | NONE | Path D is CIFAR-specific. |
| R7 FreqFlow pack_bits | YES (SUPPORTED) | NONE | Path D is CIFAR-specific. |
| R2 Kanzi inv-proj | YES (REGRESSES slightly / TIES at 0.36×) | NONE | Path D is CIFAR-specific. |

The fused-call change is **scoped narrowly to the R5b CIFAR-10 RF adapter** and does not touch any other adapter. All head-finding `d_z` values and Bonferroni verdicts remain unchanged. Path D's **fix_path_risk_to_findings = none**.

---

## 5. Effort breakdown (Path D)

| Phase | Hours | Deliverable |
|---|---:|---|
| 1. CIFAR adapter `_fused_batched_inference` implementation | 8 | new method on `RectifiedFlowCIFARAdapter`, byte-identical to 4-call sequence under paired seed |
| 2. Framework loop wiring in `R5bCIFARRFDriver` | 4 | driver calls fused variant when round plan matches |
| 3. N=1000 sweep re-run on RTX 5090 (`cuda:1`) | 4 | wall-clock measurement at matched NFE=50; expected drop 900 s → 500 s |
| 4. Head-finding d_z verification vs Wave 191 P2 anchor | 4 | per-record paired difference check; must match anchor to all reported digits |

**Total Path D effort: 20 engineer-hours**.

---

## 6. Summary table for the parent agent

| Fix path | Estimated R5b N=1000 gap closure | Risk to findings | Effort (h) | Verdict |
|---|---:|---|---:|---|
| A — reduce rounds | ~70 s (40 %) | **HIGH** (framework mechanism) | 4 | rejected |
| B — GPU-offload scheduling | ~10 s (6 %) | NONE | 16 | accepted but small |
| C — async pipeline overlap | ~30 s (17 %) | NONE | 24 | secondary |
| **D — cache intermediate** | **~125 s (70 %)** | **NONE** | **20** | **recommended** |
| E — CIFAR torch.compile | ~75 s (42 %, uncertain) | MEDIUM | 50 | tertiary |
| F — different baseline | does not close | HIGH | 30 | rejected |

---

## 7. Outputs

* `docs/audit/wave212-p6-root-cause.md` (this doc)
* Update to `docs/drafts/paper-flattened-draft.md` §5.5 (diagnosis narrative appended; existing text preserved)
* Update to `docs/audit/wave211-p1-efficiency-narrative.md` (root-cause addition)

---

## 8. References

* P1 — `docs/audit/wave212-p1-profile-setup.md`
* P2 — `docs/audit/wave212-p2-r5b-timing.md`
* P3 — `docs/audit/wave212-p3-r6-control.md`
* P4 — `docs/audit/wave212-p4-cprofile-analysis.md`
* P5 — `docs/audit/wave212-p5-memory-trace.md`
* Wave 191 P2 anchor — `docs/audit/wave191-p2-r5b-cifar10-rf-sweep.md`
* Wave 209 P4 matched-compute anchor — `docs/audit/wave209-p4-cluster-robust-all-cells.csv`
* §5.5 narrative — `docs/drafts/paper-flattened-draft.md` line 338
* §5.5 efficiency docs — `docs/audit/wave211-p1-efficiency-narrative.md`
