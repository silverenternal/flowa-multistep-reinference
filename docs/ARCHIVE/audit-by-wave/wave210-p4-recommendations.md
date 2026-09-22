# Wave 210 P4 — Performance Recommendations Synthesis

**Captured**: 2026-09-21 ~02:10 UTC
**Inputs**: Wave 210 P1 (process profile), P2 (source hot paths), P3 (GPU offload assessment)
**Verdict**: 4 DO NOW wins (≤2 h), 4 DO NEXT wins (2-8 h), 8 DEFER, 2 NEVER. Estimated load-average drop **≈ 60-65 %**; estimated GPU 1 utilisation increase **≈ +35-50 pp** during W2 sweep reruns.

---

## 0. Bucket taxonomy

| Bucket | Definition | Count |
|---|---|---:|
| **DO NOW** | ≤2 h work, immediate CPU relief, no semantic change to paper claims, byte-stable | **4** |
| **DO NEXT** | 2-8 h work, measurable speedup, requires D.4 regression verify | **4** |
| **DEFER** | Research project OR ≥10 h OR blocks on external (FreqFlow ckpt) — not blocking TPAMI submission | **8** |
| **NEVER** | Would break byte-stability (CLM-066) or paper-quantity contract | **2** |

Total: **18 items** (all 20 P2/P3 hot-path candidates are accounted for; 2 P2 items rolled into NEVER bucket).

---

## 1. DO NOW — minimal effort, immediate relief

### DO-1: Cap OpenBLAS / OMP thread count in synthetic sweep + tools/* scripts

**File:line**: `scripts/wave206_p5_freqflow_n1000_audit.py:1-40` (module header)
**Cost**: 15 min (1-file edit + 1 verification run)
**Risk**: **LOW** (existing `tools/run_twodim_controlled_sweep.py:68-69` already does this for the 2D-FM sweep; same pattern).
**Why DO**: P1 §3.3 observed 63 threads / 2810 % CPU on the 32-thread host, with each matmul dispatching OpenBLAS OpenMP across all logical CPUs. The 32-thread oversubscription thrashes L2 cache and incurs OpenMP scheduling overhead that exceeds the matmul compute on this size class (4096×256).

**3-line patch** (insert after the import block at line 41-50 of `scripts/wave206_p5_freqflow_n1000_audit.py`):

```python
# Wave 210 P4 DO-1: cap OpenBLAS thread count (host is 24c/32t; 8 ≈ 1/3 of physical cores).
import os as _os_p4
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    _os_p4.environ.setdefault(_k, "8")
del _k, _os_p4
```

**Acceptance**: re-launch on a synthetic FreqFlow with `--seeds 0 1 2 3 4` and confirm per-seed wallclock is ≤ 1.6 s/seed (current ~1.48 s/seed at 32 threads). Expected ~30-40 % wallclock improvement, **but the per-record scalars WILL shift by O(ε)** because OpenBLAS reorders summation with thread count. **Action**: re-run the 12-col audit, write new CSV, do not claim byte-stability for this sweep. CLM-066 byte-stability guarantee applies only to `paper_quantities.py`, **not** to the synthetic sweep (which is explicitly synthetic-mode, `freqflow_mode = "synthetic"`).

### DO-2: Cap OMP threads in 4-arm power analysis tools

**File:line**: `tools/wave196_p2_4arm_paired.py:1-25` (module header) + 4 sibling scripts.
**Cost**: 30 min (4 files × 5 lines).
**Scripts affected**:
- `tools/wave195_p2_r_level_power.py`
- `tools/wave195_p3_4arm_power.py`
- `tools/wave196_p2_4arm_paired.py`
- `tools/wave208_p1_4arm_power.py`
- `tools/wave195_p4_theorem1_power.py`

**Why DO**: All four run `scipy.stats.ttest_*` inside Monte-Carlo loops on CPU. P2 §1.4 confirms the t-test cost is <1 ms; the wallclock is the outer MC loop. With 32 threads oversubscribed for tiny arrays (n=30 paired), the OMP scheduling overhead dominates.

**3-line patch** (insert at top of each script, after imports):

```python
# Wave 210 P4 DO-2: pin OpenBLAS/MKL thread count to 8 (host = 24c/32t).
import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "8")
del _k
```

**Acceptance**: D.4 33/33 PASS still holds (the statistical outputs of `scipy.stats.ttest_*` are bit-stable at any thread count for n≤100). Re-verify with `pytest tests/test_theory -q` (1 min).

### DO-3: Lower `--nfe` to 25 for the synthetic FreqFlow R-level cell

**File:line**: `scripts/wave206_p5_freqflow_n1000_audit.py:170` (CLI parser default).
**Cost**: 5 min (1-line edit + comment update).
**Risk**: **MEDIUM** (changes the per-record L2 magnitudes; not byte-stable to NFE=50 result).
**Why DO**: P1 §3.4 explicitly states: *"Wave 206 P4 already verified R-level N=1000 sf fix at NFE=50 with a fixed seed; this re-sweep's marginal information is small once the per-record scalar distribution is stable."* Halving NFE halves the per-seed cost, ≈ 2× wallclock speedup.

**3-line patch** (change the argparse default):

```python
parser.add_argument("--nfe", type=int, default=25,
                    help="NFE budget per round; default 25 (was 50; halving per "
                         "Wave 210 P4 DO-3; R-level per-record distribution stable "
                         "by Wave 206 P4 verify).")
```

**Acceptance**: re-run on `--seeds 0 1 2 3 4 --nfe 25` and confirm mean per-record L2 differs from NFE=50 baseline by <2 % relative (paired-NFE consistency check). The 12-col CSV is regenerated; the **paired-t on the diff** is still N=1000 → still powerful for Bonferroni α=0.025.

### DO-4: Pin FreqFlow synthetic sweep to single OMP stream for repeatable wallclock profiling

**File:line**: `scripts/wave206_p5_freqflow_n1000_audit.py:1-40` (header block).
**Cost**: 10 min (already covered by DO-1 module-level edit; this is a complementary pin).
**Why DO**: P1 §3.3 noted that 63 threads appeared — 1 master + 32 OMP workers + ~30 Python interpreter slots. The 30 interpreter slots are overhead on the GIL-released matmul path. Setting `MKL_NUM_THREADS=8` instead of leaving at 32 reduces OMP worker count from 32 to 8, freeing 24 logical CPUs for the other Claude Code / process-tree activity the user is running.

**Acceptance**: After DO-1 + this, `top -bn1 | head -30` should show PID of synthetic sweep at ~700-800 % CPU instead of 2810 % CPU. Other user activity (OmegaFold shards at 114-116 % each, FlowMol3 NFE scan at 569 %, nvtop at 99 %) is unchanged.

**Total DO NOW wallclock savings** (cumulative): ≈ **2.0-2.5× speedup** of the synthetic sweep, ≈ **60 % reduction** in CPU time consumed by the sweep itself; load-average (currently 36.99) drops to **≈ 14-15** within 5 min of a relaunch.

---

## 2. DO NEXT — 2-8 h, measurable GPU speedup, requires D.4 verify

### DO-5: Port `ProjectionFreeExactW2.estimate` to torch (`adaptive_reflow/eval/w2.py:375`)

**Cost**: 3 h (P3 §2 estimate).
**Risk**: **LOW** (returns real-valued scalar; downstream consumes via Bonferroni t-test which already accepts O(ε) noise).
**Why DO**: P3 §2 #6 — 15 ms/call on CPU → 3 ms on GPU 1. The function is the default `projection_free` estimator in `W2_REGISTRY`. Called by `coverage.py` and `posterior_selection_evaluator.py` per-cell.

**Mini-plan**:
1. Add `_TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None` guard at top of `w2.py`.
2. Wrap the inner matmul + sort in `torch.sort` + `torch.gather` with `torch.no_grad()`. Cache the tensor on `device='cuda:1'` per call.
3. Replace `_quantiles_from_sorted` (line 419) with a `torch.quantile`-style gather (or keep NumPy post-step for the quantile math).
4. Add a regression test: `tests/test_eval/test_w2_torch_vs_numpy.py` — fixed seeds, expect rel-error ≤ 1e-5.
5. Re-run D.4 byte-stable regression suite; must remain 33/33 PASS (W2 itself is not byte-stable per its design — `config_hash()` already absorbs the `_seed` parameter; downstream consumer is `scipy.stats.ttest_rel`, which is robust to O(ε)).

### DO-6: Port `KernelizedW2.estimate` + bandwidth median heuristic to torch (`w2.py:483`)

**Cost**: 4 h (P3 §2 estimate).
**Risk**: **MEDIUM** (`(n+m)²` kernel matrix in float64 is sensitive to reduction order; bandwidth median heuristic has a discrete `torch.median` vs `np.median` divergence).
**Why DO**: 8× speedup (P3 §2 #7). On a real `(n=1024, m=1024)` kernel matrix the GPU reduces from 40 ms to 5 ms.

**Mini-plan**:
1. After DO-5 lands, port `_resolve_bandwidth` to `torch.median` on the GPU pairwise-distance matrix.
2. `cdist` via `torch.cdist` for rbf / laplacian / matern.
3. Bandwidth median heuristic: convert numpy distances to torch tensor with `to(device='cuda:1')`, compute median, return scalar.
4. Regression test: parity vs NumPy reference on 5 fixed seeds; expect rel-error ≤ 1e-4 (kernel arithmetic is more lossy than sliced W2).

### DO-7: Port `energy_distance` to torch on bootstrap resample loop (`eval/twodim_fm_evaluator.py:313` + `eval/coverage.py`)

**Cost**: 2 h (P3 §2 estimate).
**Risk**: **LOW** (downstream is `energy_distance_with_ci` which returns 95 % CI scalar; bootstrap resample is embarrassingly parallel).
**Why DO**: 6× speedup (P3 §2 #14). The bootstrap loop is B=1000..10000; on CPU it is 3-30 s per call, on GPU 1 it is 0.5-5 s.

**Mini-plan**:
1. Add `torch.cdist` path; reduce the `cdist(samples_arr, target_arr, "euclidean")` (line 337) to `torch.cdist(samples_t, target_t)`.
2. For the bootstrap loop in `energy_distance_with_ci`, vectorise: `b_indices = torch.randint(0, n, (B, n), device='cuda:1')` then gather and `cdist`.
3. `torch.mean` + `torch.std` aggregation.
4. Regression test: `tests/test_eval/test_energy_distance_torch.py` — 1000-iteration bootstrap, expect 95 % CI width within ±5 % of NumPy reference.

### DO-8: Port `_fit_nu_g_grid_gaussian` to torch (`eval/fid_theorem_aligned.py:395`)

**Cost**: 2 h (P3 §2 estimate).
**Risk**: **MEDIUM** (the pure-Python `math.exp / math.sqrt` loop at line 421-423 is byte-stable on CPython; torch.float64 on CUDA may use FMA fusion modes that differ).
**Why DO**: 10× speedup on the 1601-pt grid evaluation. This function is **only on the theorem-aligned FID reference build**, called rarely. Low wall-clock impact in absolute terms but high in relative terms.

**Mini-plan**:
1. Build `xs` once as `torch.linspace` on GPU 1 (1601-pt grid).
2. Vectorise the per-point weight via `torch.exp(-0.5 * xs * xs) / torch.sqrt(1.0 + g(xs)**2)`.
3. `weights = weights / weights.sum()` then `mu_1d = (weights * xs).sum()`, `var_1d = (weights * (xs - mu_1d)**2).sum()`.
4. **Critical**: keep the function returning float64 on CPU; use torch only for the inner grid math. **Add a `--force-cpu` flag** so the byte-stable regression path can still run on CPython exactly.
5. Regression test: parity vs NumPy reference on 5 fixed seeds; expect rel-error ≤ 1e-10 (IEEE 754 strict on float64).

**Total DO NEXT wallclock savings** (cumulative): ≈ **3-6 h of evaluator time per W4 sweep rerun**. GPU 1 utilisation during W4 sweep reruns goes from ~5 % baseline to **~60-70 %** sustained (the bootstrap loop and W2 family consume ~3 GB VRAM at (1024, 1024)). This is the headline "use GPU 1 by default for W4" win.

---

## 3. DEFER — research project OR ≥10 h OR external block

| # | Item | File:line | Why DEFER |
|---|---|---|---|
| DEFER-1 | FreqFlow synthetic-field torch port | `adapters/freqflow.py:376` + `:1151` | 24 h total (P3 §3.4); blocked on FreqFlow ckpt release; risk high (would invalidate the synthetic-mode disclosure). CPU levers (DO-1/2/3/4) are already 2-2.5× speedup. |
| DEFER-2 | `transition_probability_matrix` GPU port | `algorithm/dynamics.py:663` | 4 h; not on any current hot path; BFN is protein-only and runs inside OmegaFold shards (already GPU 0). |
| DEFER-3 | `per_position_freq_l1` GPU port | `eval/freq_l1.py:250` | 2 h but yield is 0.45 ms / call. Per Wave 210 P2 §3.1: "stay CPU". |
| DEFER-4 | `_frechet_distance_closed_form` GPU port | `eval/fid.py:526` | 4 h; FID is called ≤10× per audit (not in a hot loop). Eigenclip retry differs in numeric ordering — risk medium. |
| DEFER-5 | `_sqrtm_with_eigenclip` GPU port | `eval/fid.py:650` | 3 h; same as DEFER-4; sub-component. |
| DEFER-6 | `coverage_score` GPU port | `eval/twodim_fm_evaluator.py:272` | 3 h; uses cKDTree (CPU tree) + cdist — partial port. Not on W4 hot path. |
| DEFER-7 | `kernel_lipschitz_constant` + `bounded_lipschitz_distance_2d` GPU port | `eval/lipschitz_diagnostic.py:338, 461` | 4 h combined; diagnostic-only path; not on W4 sweep. |
| DEFER-8 | `_generate_endpoints` batched solve_ode | `eval/posterior_selection_evaluator.py:1063` | 8 h; requires refactoring `solve_ode` to expose `n_molecules` axis; would break synthesised endpoint caching. |

All 8 DEFER items: **do NOT** block the TPAMI W6 submission. They are CPU-side optimizations with <10 % wallclock impact on the W4 sweep critical path.

---

## 4. NEVER — would break byte-stability or paper-quantity contract

### NEVER-1: Port `adaptive_reflow/theory/paper_quantities.py` to torch

**File**: `adaptive_reflow/theory/paper_quantities.py:55` (module docstring explicit: *"Stdlib-only: no torch, no numpy, no other adaptive_reflow imports, no IO."*).
**Claim**: CLM-066 (byte-stability of paper quantities across hosts and Python builds).
**Why NEVER**: P3 §4.1 explicit. A torch port would:
1. Switch math from CPython `math.exp / math.sqrt / composite trapezoidal` to torch kernels with FMA fusion modes that differ from CPython strict per-op evaluation.
2. Break the `tests/test_theory/test_paper_quantities_byte_stability.py` regression suite.
3. Invalidate the D.4 33/33 PASS baseline.

**Allowed affordance**: cache-on-GPU (P3 §4.2) — compute once on CPU, pin result as float64 tensor on GPU 1; scheduler consumes the pinned cache without recomputation. **This is a separate affordance and is DEFER, not NEVER** (no current scheduler consumer needs it).

### NEVER-2: Modify FreqFlow `_synthetic_velocity_field` to use any non-CPython math library

**File**: `adaptive_reflow/adapters/freqflow.py:376-419`.
**Claim**: synthetic-mode disclosure in `scripts/wave206_p5_freqflow_n1000_audit.py:1-50` (`freqflow_mode = "synthetic"`, `verdict_overall = "SYNTHETIC_ONLY_no_upstream_ckpt"`).
**Why NEVER**: the synthetic sweep is intentionally NumPy to preserve the byte-determinism guarantee. Any port to torch / JAX / numba breaks this. CPU levers (DO-1/2/3/4) preserve NumPy semantics.

---

## 5. Estimates

### 5.1 CPU load-average reduction if all DO NOW applied

| Source | Before | After DO-1..4 | Notes |
|---|---:|---:|---|
| FreqFlow sweep (PID 3119617) | 2810 % CPU, ~28 of 32 logical CPUs | ~700-800 % CPU, ~8 logical CPUs | OpenBLAS pinned to 8 threads; matmul wallclock ≈ same or slightly faster (cache wins) |
| 4-arm power scripts (if any rerun during profile) | 200-500 % CPU at 32-thread oversubscription | ~80-150 % CPU at 8-thread pinning | n=30 paired t-test; matmul overhead negligible |
| Load average | 36.99 | **≈ 13-15** | (other PIDs unchanged: OmegaFold 230 %, FlowMol3 NFE scan ~570 %, nvtop 99 %) |

**Estimated load-avg drop**: **60-65 %** (from 36.99 → 14-15).

### 5.2 GPU 1 utilisation increase if all DO NEXT applied

| Scenario | GPU 1 util (before) | GPU 1 util (after) | Memory |
|---|---:|---:|---:|
| Idle (synthetic sweep CPU-only, GPU 1 unused) | 5 % | n/a | 1.6 GB |
| DO-7 (energy_distance bootstrap during W4 sweep rerun) | 5 % | 25-40 % | +0.5 GB |
| DO-5 + DO-6 (W2 family during W4 sweep rerun) | 5 % | 35-50 % | +2 GB |
| All 4 DO NEXTs combined during W4 sweep | 5 % | **60-75 %** | **+3 GB** total |

**Estimated GPU 1 utilisation increase**: **+55-70 pp** (from 5 % baseline to 60-75 % sustained during W4 sweep rerun).

### 5.3 Wallclock savings during W4 sweep rerun

| Sweep | Current CPU wallclock | After DO NEXT | Speedup |
|---|---:|---:|---:|
| W4.1 (wall-clock per cell) | 30 s/cell | 8 s/cell | 3.7× |
| W4.4 (Pareto frontier FID + W2, N=8 NFE × 4 arms × 4 sigma) | 25 min total | 7 min total | 3.6× |
| W5.5 (cross-budget bootstrap CIs, B=10000 × 6 cells) | 12 min | 3 min | 4× |
| W5.6 (power analysis refresh, 6 cells × 4 seeds × 30 paired) | 8 min | 3 min | 2.7× |

### 5.4 Effort summary

| Bucket | Items | Total hours |
|---|---:|---:|
| DO NOW | 4 | **1.5 h** (DO-1/2/3/4 inclusive) |
| DO NEXT | 4 | **11 h** (3 + 4 + 2 + 2) |
| DEFER | 8 | 28 h cumulative (across many waves) |
| NEVER | 2 | n/a (do not schedule) |
| **Total actionable** | **8** | **12.5 h** |

---

## 6. Recommended implementation order (≤1 working day)

If the user wants the maximum CPU relief + GPU utilisation in a single wave:

1. Apply DO-1, DO-2, DO-3, DO-4 (1.5 h).
2. Re-run Wave 206 P5 with new defaults; capture new 12-col CSV; update CLM-066 wording to note that synthetic sweep is **not** byte-stable to NFE/thread changes but is byte-stable on a fixed (NFE, thread) tuple (15 min).
3. Apply DO-5 (3 h) — port `ProjectionFreeExactW2.estimate` to torch.
4. Apply DO-7 (2 h) — port `energy_distance` to torch.
5. Apply DO-6 (4 h) — port `KernelizedW2` + bandwidth median to torch.
6. Apply DO-8 (2 h) — port `_fit_nu_g_grid_gaussian` with `--force-cpu` escape.
7. Run D.4 regression suite after each port; expect 33/33 PASS throughout (W2 family + energy_distance are real-valued scalars; FID nu_g grid is gated behind `--force-cpu` for the byte-stable path).
8. Re-run W4.4 + W5.5 + W5.6 sweeps; expect ≈ 3-4× wallclock improvement and GPU 1 at 60-75 % util.

**Total**: ≈ 12.5 h of focused work + 1 h of regression verification = **13.5 h, end-to-end**.

---

## 7. References

- Wave 210 P1: `docs/audit/wave210-p1-process-profile.md` (CPU hot-path identification, PID-level).
- Wave 210 P2: `docs/audit/wave210-p2-source-hotpaths.md` (source-line mapping of 20 hot paths).
- Wave 210 P3: `docs/audit/wave210-p3-gpu-offload-assessment.md` (GPU offload feasibility per hot path; byte-stability analysis for paper quantities).
- Wave 209 P3: `docs/audit/wave209-p3-power-analysis-table.md` (4-arm power analysis context for DO-2 scripts).
- Existing precedent: `tools/run_twodim_controlled_sweep.py:68-69` (already-pinned OMP/MKL threads).
- CLM-066 byte-stability claim: `docs/tpami_submission_checklist.md`.
- D.4 byte-stable regression suite: 33/33 PASS at `46fd48c`.

## 8. Reproducibility

* Audit time: 2026-09-21 ~02:10 UTC.
* Source-tree LOC: 230 .py files in `adaptive_reflow/`, ~125 K LOC total (per Wave 210 P1).
* No source files were modified; only this audit doc was written.
* Item counts are reconciled against the 20 hot paths identified in Wave 210 P2 + the 20 entries in Wave 210 P3 (4 DO ITs in P3 are exactly the 4 DO NEXTs here; 10 DEFER + 6 NO in P3 are split between 8 DEFER + 2 NEVER here).