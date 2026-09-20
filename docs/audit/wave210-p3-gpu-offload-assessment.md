# Wave 210 P3 — GPU Offload Opportunity Assessment

**Captured**: 2026-09-21 02:00 UTC
**Host**: `47.110.35.232` (single-node)
**Read-only audit**: no source code modified
**Verdict**: GPU offload is feasible for **3 eval-side hot paths** (W2 family + energy_distance) on **GPU 1**; the dominant CPU consumer (FreqFlow probe PID 3119617) is GPU-NOT-RECOMMENDED for byte-stability reasons.

---

## 0. Scope

This audit takes the 20 source-tree hot paths identified in
[Wave 210 P2](wave210-p2-source-hotpaths.md) and assesses each on
GPU-offload feasibility, estimated speedup, implementation cost,
risk to byte-stability, and final recommendation. It also addresses
the per-task questions in the Wave 210 P3 brief:

1. Top-20 hot-path assessment table.
2. FreqFlow probe deep dive (PID 3119617).
3. Paper-quantities explicit NO-GPU-PORT note (CLM-066).
4. Per-record statistics CPU-vs-GPU decision rule.
5. ODE solver status (no change).
6. FID computation status (already GPU via extractor).
7. pLDDT / scPerplexity / fg_dev assessment.
8. CSV sibling at `verification_outputs/wave210-p3-offload-assessment.csv`.

---

## 1. GPU state at audit time (2026-09-21 ~01:55 PT)

`nvidia-smi` snapshot captured at the start of this audit:

| GPU | Model | Util | Mem used | Process |
|---|---|---:|---:|---|
| 0 | RTX PRO 6000 | 45 % | 8127 / 97887 MiB | `omegafold` shard_00 (4056 MiB) + shard_01 (4080 MiB) |
| 1 | RTX 5090 | 45 % | 1660 / 32607 MiB | `.venvs/flowmol3_venv/bin/python` PID 3124542 (1650 MiB) — NFE scan one-liner |

**Conflict map**:

* **GPU 0 is OFF-LIMITS** to all new torch allocations. It is held by
  the Wave 206 P1 foldability sweep (`omegafold` shards) which must
  finish uninterrupted to deliver the LineageFlow N=1000 foldability
  result. Any torch allocation on GPU 0 would steal SM time and
  corrupt the sweep.
* **GPU 1 has ~30 GB headroom** today; the FlowMol3 NFE scan
  one-liner is ~transient. All recommended GPU offloads in this
  audit land on GPU 1 with `CUDA_VISIBLE_DEVICES=1`.

The user's directive ("GPU 1 is the target; check it is not in
conflict") was respected: at audit time GPU 1 is at 45 % util /
1660 MiB / 1 transient process — safe to co-tenant.

---

## 2. Top-20 hot-path assessment (per P2)

Sorted by P2 rank. **Speedup** is "vs current single-thread NumPy
path on CPU". **Risk** ranks medium if a port requires changing the
public interface, low if byte-stable, high if a port can affect
downstream determinism.

| # | File:line | Function | Wall/Call (ms) | Feasibility | Speedup | Cost (h) | Risk | Recommendation |
|---|---|---|---:|---|---:|---:|---|---|
| 1 | `adapters/freqflow.py:376` | `_synthetic_velocity_field` | 1500 | partial | 8× | 16 | high | **DEFER** |
| 2 | `adapters/freqflow.py:1151` | `FreqFlowAdapter.solve_ode` | 300 | partial | 7× | 12 | medium | **DEFER** |
| 3 | `scripts/wave206_p5_freqflow_n1000_audit.py:225` | `main` | 1500 | no | 1× | 0 | high | **DEFER** |
| 4 | `algorithm/dynamics.py:663` | `transition_probability_matrix` | 1 | yes | 5× | 4 | medium | **DEFER** |
| 5 | `eval/freq_l1.py:250` | `per_position_freq_l1` | 0.5 | yes | 4× | 2 | low | **DEFER** |
| 6 | `eval/w2.py:375` | `ProjectionFreeExactW2.estimate` | 15 | yes | 5× | 3 | low | **DO IT** |
| 7 | `eval/w2.py:483` | `KernelizedW2.estimate` | 40 | yes | 8× | 4 | medium | **DO IT** |
| 8 | `eval/fid_theorem_aligned.py:395` | `_fit_nu_g_grid_gaussian` | 8 | partial | 10× | 2 | medium | **DO IT** |
| 9 | `theory/paper_quantities.py:96` | `sheet_evidence_A` | 0.6 | partial | 10× | 3 | high | **NO** (cache only) |
| 10 | `theory/paper_quantities.py:178` | `root_cell_packing_B` | 0.6 | partial | 10× | 3 | high | **NO** (cache only) |
| 11 | `eval/fid.py:526` | `_frechet_distance_closed_form` | 5 | yes | 3× | 4 | medium | **DEFER** |
| 12 | `eval/fid.py:650` | `_sqrtm_with_eigenclip` | 3 | yes | 3× | 3 | medium | **DEFER** |
| 13 | `eval/twodim_fm_evaluator.py:272` | `coverage_score` | 2 | yes | 5× | 3 | medium | **DEFER** |
| 14 | `eval/twodim_fm_evaluator.py:313` | `energy_distance` | 3 | yes | 6× | 2 | low | **DO IT** |
| 15 | `eval/lipschitz_diagnostic.py:338` | `kernel_lipschitz_constant` | 8 | yes | 5× | 2 | low | **DEFER** |
| 16 | `eval/lipschitz_diagnostic.py:461` | `bounded_lipschitz_distance_2d` | 5 | yes | 3× | 2 | low | **DEFER** |
| 17 | `eval/posterior_selection_evaluator.py:1063` | `_generate_endpoints` | 500 | partial | 3× | 8 | medium | **DEFER** |
| 18 | `tools/eval/metrics.py:149` | `_compute_kanzi_real_metric` | 0 | no | 1× | 0 | low | **NO** |
| 19 | `tools/eval/metrics.py:1791` | `_compute_flowmol3_composite` | 0 | no | 1× | 0 | low | **NO** |
| 20 | `algorithm/perturbation/perturbation.py:509` | `_finite_difference_grad_log_p_qty` | 2 | no | 1.2× | 0 | low | **NO** |

**Tally**: 4 DO IT, 10 DEFER, 6 NO. (Paper-quantity items 9 + 10
count as NO; cache-on-GPU is a separate affordance.)

### 2.1 Why DO IT picks are safe

The three eval-side DO ITs are byte-stable-tolerant:

* `ProjectionFreeExactW2.estimate` — returns a real-valued scalar;
  downstream consumes it through Bonferroni t-test gating which
  already accepts O(ε) noise.
* `KernelizedW2.estimate` — same scalar surface; bandwidth median
  heuristic is ported together.
* `energy_distance` (called from `eval/coverage.py` →
  `energy_distance_with_ci` B=1000 bootstrap) — bootstrap resample
  loop is independent per iteration; GPU parallelises trivially; the
  result is a real-valued scalar + 95 % CI, not a discrete oracle.

### 2.2 Why the FreqFlow probe (PID 3119617) is **NOT** GPU-recommended

See §3 below for the deep dive.

### 2.3 Why paper-quantities are **NO** (but cache-on-GPU OK)

See §4 below.

---

## 3. FreqFlow probe deep dive (PID 3119617, 28 cores)

### 3.1 What it is computing

`scripts/wave206_p5_freqflow_n1000_audit.py --ckpt-probe` runs the
**Wave 206 P5 FreqFlow N=1000 paired-record 12-col audit** in
**synthetic mode** because FreqFlow's `nnet_ema.pth` ckpt is
**NOT publicly released** as of 2026-09-21 (re-probed this run:
`VERDICT: ckpt ABSENT — synthetic mode mandatory`). Per seed:

* `_solve_baseline(adapter, nfe=50, seed=s)` — 50 NFE steps, each
  calls `_synthetic_velocity_field` once → 50 × 2 matmuls
  (4096×256 and 256×4096) + 1 FFT.
* `_solve_framework(adapter, nfe=50, seed=s, n_rounds=3)` — 3 rounds
  of 50 NFE each → 150 × 2 matmuls + 3 FFTs.
* `_paired_metrics`, `_endpoint_latent` — small NumPy reductions.

Total per seed: **200 matmuls of 4096×256 + 200 matmuls of
256×4096 + 4 FFTs**. With 1000 seeds and the seed-loop fully
serialised inside the script, that is **400 000 matmuls** in float64.

Observed wall-clock ≈ 1.48 s/seed → estimated finish at seed 1000
≈ **~24 min total**. The script started 01:42, ETA ≈ 02:06.

### 3.2 Can it use GPU 1?

**Technically yes; contractually no.** Two reasons:

1. **Synthetic mode is intentional.** The script header states: *"This
   script therefore runs in synthetic mode only … the deterministic
   NumPy two-branch shim that backs the Protocol surface."* The whole
   point of the sweep is to exercise the Protocol surface
   (adapter / integrator / re-inference scheduling) against a
   deterministic NumPy field, not to test a real FM model. Moving
   `_synthetic_velocity_field` to a torch tensor would defeat the
   byte-determinism guarantee that the audit relies on.
2. **GPU 1 is technically free** (45 % util / 1660 MiB at audit
   time, 30 GB headroom). But porting the synthetic NumPy path to
   GPU on GPU 1 would change the per-record L2 / cosine scalars that
   downstream consumers (12-col audit, byte-stable regression suite)
   depend on. **No win.**

### 3.3 What would the speedup be?

* If ported *with* `no_grad` and a fused single-kernel matmul: **8×**
  per `_synthetic_velocity_field` call.
* If ported *and* batched across a new `n_molecules` axis (mirror
  FlowMol3): an additional **N×** wall-clock saving at the script
  level where N is the batch depth (N=10..100 typical).
* Combined: roughly **10-20× end-to-end** if both changes are made.

But the cost of those changes is:

* Add `n_molecules` to `FreqFlowAdapter.solve_ode` (mirror FlowMol3
  interface; ~4 h).
* Rewrite `_synthetic_velocity_field` as a single fused matmul
  kernel with `no_grad` and `(B, 4096) @ W1` reshape (B = batch) →
  `(B, 4096)` final (Wave 11-style refactor; ~16 h).
* Verify byte-stability against the synthetic NumPy path on N=10
  seeds before re-running the full sweep (~4 h).

Total: **~24 h** plus the regression test cost. Out of scope for
"default to GPU".

### 3.4 Implementation effort

| Phase | Task | Effort |
|---|---|---|
| (blocked) | Wait for FreqFlow ckpt release | external |
| (after ckpt lands) | Add `n_molecules` axis to `FreqFlowAdapter.solve_ode` | 4 h |
| (after ckpt lands) | Fuse `_synthetic_velocity_field` as torch matmul | 16 h |
| (after ckpt lands) | Byte-stability verify (N=10 seeds vs synthetic path) | 4 h |
| **Total** | | **24 h** |

Until the FreqFlow ckpt is released (today: ABSENT), this entire
effort is **DEFER**. The right CPU levers right now are drop
N=1000→500, drop NFE=50→25, or switch the synthetic field to
`np.float32` (per Wave 210 P1 §3.4).

### 3.5 What we should do *right now*

1. **Accept the 28-core CPU load** for the next ~24 minutes until
   the current Wave 206 P5 sweep finishes.
2. **Do NOT** interrupt PID 3119617 — the audit framework depends on
   deterministic NumPy output.
3. **For any future re-run** of the synthetic sweep, prefer the
   float32 lever (≈ 2× speedup, ~1× change in audit scalars) over
   a torch port (which would invalidate the synthetic-mode guarantee).
4. **GPU 1 is currently idle enough** to accept new torch
   allocations, but the only safe tenants are the eval-side DO ITs
   in §2.1 (W2 family + energy_distance).

---

## 4. Paper quantities (CLM-066 byte-stability constraint)

**Explicit verdict: NOT RECOMMENDED to port `adaptive_reflow/theory/paper_quantities.py` to GPU.**

### 4.1 Why NO

The module docstring at line 55 says:

> **Stdlib-only: no torch, no numpy, no other adaptive_reflow imports, no IO.**

This is a deliberate design contract. CLM-066 in
`docs/tpami_submission_checklist.md` (or equivalent claim registry)
requires that paper-quantity computations (`sheet_evidence_A`,
`root_cell_packing_B`, `per_cell_coefficient_C`, `exterior_gap_e_rho`)
be **byte-stable across hosts and Python builds**. The
`tests/test_theory/test_paper_quantities_byte_stability.py` (and the
W2 byte-stable regression suite D.4 33/33 PASS) verify this.

A torch port would:

1. Switch the implementation from `math.exp` / `math.sqrt` /
   composite trapezoidal in pure Python to a torch kernel whose
   math is *close to* but not identical to CPython `math`. Float64
   tensors on CUDA follow IEEE 754 but may use FMA fusion modes
   that differ from CPython's strict per-op evaluation.
2. Make the byte-stable regression suite fail or become flaky
   (the 12-col CSV audit would diverge from the
   `D.4 33/33 PASS` baseline).
3. Break the cross-host determinism guarantee that the TPAMI
   submission relies on for reviewer reproducibility.

### 4.2 Cache-on-GPU affordance (allowed)

Paper quantities MAY be **cached on GPU** for read-only scheduler
consumption. The flow:

1. Compute the paper quantity once on CPU (preserves byte-stability).
2. Pin the resulting float64 scalar or small tensor on GPU 1 in a
   pinned-memory buffer (no recomputation on GPU).
3. Scheduler reads from the pinned buffer without re-running the
   CPython math.

This pattern is **safe** because:

* The CPU computation is preserved (byte-stability intact).
* The GPU buffer is a *cache*, not a recomputation. The cached value
  is exactly the CPU-computed float64 (rounded on `to(cuda,
  dtype=torch.float64)` which preserves bit-exactness for the
  subset of IEEE 754 values that fit in a CUDA float64).
* The scheduler consumes the cache as a real-valued scalar;
  downstream t-tests on the cached values use the same CPU noise
  tolerance as the original CPython math.

Implementation cost: ~4 h. Status: **DEFER** (no current scheduler
hot path consumes paper quantities on the GPU critical loop).

---

## 5. Per-record statistics (paired t-test, bootstrap)

**Current implementation**: `scipy.stats.ttest_rel(f, b)` + 2*(1-cdf)
on CPU; `scipy.stats.t.sf(abs(t_stat), df=df)` for Bonferroni
correction (see `tools/wave196_p2_4arm_paired.py:198`,
`scripts/wave199_p3_lineageflow_difficulty_strata.py:33/116`).

### 5.1 Decision rule

* **N < 10000** — stay CPU. The t-test itself is < 1 ms; the
  scipy.stats C path is heavily optimised. GPU launch overhead
  exceeds the compute cost.
* **N >= 10000 + many bootstrap resamples (≥ 1000)** — port to
  GPU torch on device 1. The dominant cost is the bootstrap
  resampling loop (B=1000..10000) which is embarrassingly parallel.
  Use `torch.bernoulli` mask + indexed gather; aggregate with
  `torch.mean` + `torch.std`; CDF via `torch.distributions.normal.cdf`.
* **N >= 10000 but few bootstrap resamples** — stay CPU. The GPU
  port does not amortise the launch overhead for B < 100.

### 5.2 Decision per audit-time script

| Script | N records | Bootstrap B | Verdict |
|---|---:|---:|---|
| `scripts/wave196_p2_4arm_paired.py` | 30 | 0 | CPU |
| `scripts/wave199_p3_lineageflow_difficulty_strata.py` | 100..1000 | 0 | CPU |
| `scripts/wave203_p3_k6_cluster_robust.py` | 10..30 | 100 | CPU |
| `scripts/wave206_p1_lineageflow_n1000_monitor.py` | 1000 | 0 | CPU |
| `scripts/wave206_p2_kanzi_framework_n1000_audit.py` | 1000 | 0 | CPU |
| `scripts/wave206_p5_freqflow_n1000_audit.py` | 1000 | 0 | CPU |
| `tools/wave208_p1_4arm_power.py` | 30 (per MC rep) | 0 | CPU |

None of the audit-time scripts trigger the GPU threshold (N=10000
+ B≥100). The current scipy.stats path is correct.

---

## 6. ODE solver (`frame/engine.py` + adapter `solve_ode`)

**Status: already GPU**. The framework's solve_ode is
adapter-dispatched; the torch-mode adapters (`FlowMol3Adapter`,
`RectifiedFlowCIFARAdapter`, `KanziAdapter`, `LineageFlowAdapter`,
`ProtBfnAbBfnAdapter`, `HiDreamI1Adapter`, `LuminaImageAdapter`,
`Wan22VideoAdapter`, `FastDllmAdapter`, `AbCacheAdapter`, etc.)
all run the ODE integrate loop on whatever device the adapter is
constructed with (default `cuda`). No CPU offload candidate here.

**Action: NO CHANGE**.

---

## 7. FID computation (`eval/fid.py`, `eval/mnist_fid.py`)

### 7.1 InceptionV3 feature extractor

The single canonical extractor lives at
`tools/run_image_eval.py:load_inception_for_fid(device)`. It takes
a `device` argument and constructs:

```python
tvm.inception_v3(weights=IMAGENET1K_V1, aux_logits=True, transform_input=False)
model.fc = nn.Identity(); model.AuxLogits = None; model.eval()
```

When called with `device='cuda'`, the extractor is on GPU.
**Already optimal**.

### 7.2 Fréchet arithmetic (the math itself)

`_frechet_distance_closed_form` (`eval/fid.py:526`) and
`_sqrtm_with_eigenclip` (`eval/fid.py:650`) are pure NumPy +
`scipy.linalg.sqrtm`. These are FID items #11 and #12 in the
top-20 hot paths.

GPU port feasibility: yes (`torch.linalg.matrix_exp` on
half-log form), but:

* `d=2048` InceptionV3 regime: ~3× speedup, eigenclip retry differs
  in numeric ordering (medium risk).
* `d=128` MNIST Frechet-projection regime: GPU launch overhead
  eats the saving (1× speedup, no benefit).

**Recommendation: DEFER**. Only worth doing if a Wave-19-style
audit regenerates hundreds of FID values on the d=2048 path on
the user's host. Today the FID math is called per adapter round
(≤ 10 times per audit), not in a hot loop.

### 7.3 MNIST random-projection Fréchet (`mnist_fid.py`)

Pure NumPy + scipy.linalg.sqrtm. Same verdict as §7.2: DEFER.

---

## 8. pLDDT + scPerplexity (`eval/amino_acid_recovery.py`, `eval/coverage.py`)

### 8.1 `amino_acid_recovery.py`

* Per-region AAR over IMGT-numbered VH positions (128 positions, 7
  regions).
* Pure Python + Biopython optional FASTA reader; built-in fallback
  parser.
* Comparison is a straight position-by-position residue equality
  check after IMGT numbering.

**GPU feasibility**: **infeasible / not worth it**. The per-region
comparison is a scalar equality test on a length-128 vector;
GPU launch overhead would dominate the cost (~10 μs per call vs
~50 μs on CPU). Even if we batched across 1000 records, the
matmul throughput is negligible.

**Verdict: STAY CPU**.

### 8.2 `coverage.py`

* `weighted_coverage_score` — per-Voronoi-cell covered-area fraction.
  Per-call cost ~1 ms (np.linalg.norm on (n_grid, 2) +
  np.broadcast). Not a hot path.
* `energy_distance_with_ci` — 1000 bootstrap resamples of
  `energy_distance`. **THIS is the GPU win** — already covered by
  DO IT #14 in §2.1.

### 8.3 pLDDT / scPerplexity

These are not in this audit's scope (they live in
`tools/eval/metrics.py` and the LineageFlow foldability pipeline,
not in `adaptive_reflow/eval/`). The OmegaFold shards on GPU 0
already compute pLDDT on GPU; no CPU hot path here.

---

## 9. fg_dev (`eval/fg_deviation.py`, `eval/flowmol3_eq4_fg_deviation.py`)

### 9.1 What it does

Per-molecule functional-group occurrence / instance count via RDKit
SMARTS matching:

* `count_fg_hits(smiles_or_mol, smarts_list)` — per-FG hit count
  using `rdkit.Chem.Fragments.fr_<name>(mol)` for `fr_*` keys
  (the 85-element Bickerton QED SMARTS) and
  `mol.GetSubstructMatches(pat)` for arbitrary SMARTS.
* `fg_deviation_l1(gen, ref, smarts_list)` — L1 over
  frequency vectors.
* `flowmol3_eq4_fg_deviation` — paper-equivalent instance-count
  version.

### 9.2 GPU feasibility

**NO.** RDKit is fundamentally CPU-only. SMARTS matching uses
backtracking + atom-by-atom state-machine traversal; no GPU kernel
exists or is on the roadmap. The upstream Pat Walters rd_filters
library is also CPU.

### 9.3 What we could optimise on CPU

The `count_fg_hits` outer loop calls RDKit once per (mol × K) for
K≈85 SMARTS. A vectorisation across the K axis (cache fragments
per mol, then assemble the binary vector) is feasible on CPU but
yields only ~1.5× speedup (P2 estimate). Not worth the refactor.

**Verdict: STAY CPU**.

---

## 10. GPU contention summary

At audit time:

| GPU | State | Safe to co-tenant? | What we propose |
|---|---|---|---|
| 0 | OmegaFold shards (Wave 206 P1 foldability) | **NO** | (untouched) |
| 1 | FlowMol3 NFE scan one-liner (transient) | **YES** (after scan exits) | DO IT #6, #7, #8, #14 (W2 family + energy_distance + nu_g grid) |

**Implementation order if the user wants to land the DO ITs**:

1. Wait for the Wave 206 P5 sweep to finish (~24 min from 01:42 PT).
2. Wait for the FlowMol3 NFE scan on GPU 1 to finish (transient).
3. Port `ProjectionFreeExactW2.estimate` to torch with
   `CUDA_VISIBLE_DEVICES=1` and `torch.no_grad()`. Verify against
   NumPy reference on 5 fixed seeds; expect bit-exact match for the
   matmul + sort, ~ε noise for the quantile gather.
4. Port `KernelizedW2.estimate` and `_resolve_bandwidth` similarly.
5. Port `energy_distance` for the bootstrap path.
6. Port `_fit_nu_g_grid_gaussian` (low priority; only on the
   theorem-aligned FID reference build, called rarely).

Total: ~11 h across 4 functions. Byte-stable regression suite (D.4
33/33 PASS) MUST remain green — verify after each port.

---

## 11. Artefacts

* CSV: `verification_outputs/wave210-p3-offload-assessment.csv`
  (20 rows; columns `rank, file, line, function, wallclock_per_call_estimate_ms, gpu_offload_feasibility, est_gpu_speedup, implementation_cost_hours, byte_stability_risk, recommendation, notes`).
* This doc: `docs/audit/wave210-p3-gpu-offload-assessment.md`.

---

## 12. Reproducibility

* Audit time: 2026-09-21 ~02:00 UTC.
* `nvidia-smi` snapshot at audit start captured in §1.
* FreqFlow probe (PID 3119617) observed wall-clock and per-seed
  breakdown captured in §3.1.
* No source files were modified; only the audit doc + CSV were
  written.
* The CSV column ordering matches the column ordering consumed by
  downstream Wave 210 P4/P6 consumers (single source of truth so
  P2 + P3 + P4 stay in sync).