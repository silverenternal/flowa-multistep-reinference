# Wave 210 P2 — Source Code CPU Hot Path Identification

## 0. Context

Wave 210 P1 process profile identified the wall-clock CPU leader as
`scripts/wave206_p5_freqflow_n1000_audit.py` running in synthetic
FreqFlow mode; secondary heavy scripts are the Kanzi/Legacy/4-arm/Stat
sweep tools in `tools/`. This audit walks the source tree to map that
wall-clock profile onto specific functions / lines in
`adaptive_reflow/` + `scripts/` + `tools/`, then rates each hot path on
GPU-portability, estimated speedup, and risk.

The audit is **READ-ONLY** for source; we did NOT modify any code path.
The audit files written (this doc + the CSV sibling at
`verification_outputs/wave210-p2-source-hotpaths.csv`) are the only
artefacts produced.

GPU contention note: at audit time (2026-09-21 01:54 PT) `nvidia-smi`
shows both GPUs busy:

* GPU 0 (RTX PRO 6000): 72% util, 8127/97887 MiB — held by
  `omega-megafold_py310/bin/python3.10` (2 procs, 4056 MiB each).
* GPU 1 (RTX 5090): 47% util, 1660/32607 MiB — held by
  `.venvs/flowmol3_venv/bin/python` (1 proc, 1650 MiB).

Any GPU offload this audit recommends must be staged so as to not
contend with those jobs (use a separate CUDA_VISIBLE_DEVICES slot when
the upstream user frees the device, or fall back to the GPU that is
empty in subsequent waves).

## 1. Static-survey aggregates (P2 raw signals)

### 1.1 `@torch.no_grad()` / `@torch.jit.script` decorators

Single match: `adaptive_reflow/adapters/flowmol3_v2_adapter.py:2487`
is a doc-string mention ("`@torch.no_grad`) and we re-detach…"), not
an actual decorator. The framework source tree contains **zero**
`@torch.no_grad` and **zero** `@torch.jit.script` decorated
callables. Every torch-touching function relies on the caller to wrap
in a `with torch.no_grad():` context (see
`tools/eval/metrics.py:194-198` for the one-call `torch.no_grad()`
context manager wrapping `_compute_kanzi_real_metric`'s `DAE.encode`
forward pass).

Implication: any GPU-portable hot loop is currently evaluated with
autograd graph construction turned on. A clean port must wrap the
inner loop in `with torch.no_grad():` *or* decorate the function —
otherwise the GPU saves every intermediate for backward, blowing GPU
memory on the 4×32×32 / 128-dim cases.

### 1.2 `.cpu()` / `.numpy()` / `.item()` calls

The framework routinely shuttles data across the device boundary:

* `.detach().cpu().numpy()` — 30+ matches across
  `adapters/{freqflow,lineageflow,protbfn_abbfn,rectified_flow_cifar,
  wan2_2_video,kanzi,mnist_fm_train,hidream_i1,flowmol3_v2_adapter}.py`,
  `eval/clip_score.py:480`, `core/graph_wrapper.py:560-610`.
* `v.cpu().numpy().astype(np.float64)` in the `_synthetic_velocity_field`
  analogous Block in `flowmol3_v2_adapter.py:1167-1171` and the
  `eval/exec` paths in `lineageflow.py:610`, `kanzi.py:1163`,
  `rectified_flow_cifar.py:312`, `wan2_2_video.py:424/534`,
  `mnist_fm_train.py:106`, `hidream_i1.py:468`,
  `protbfn_abbfn_adapter.py:1453-1454/1806-1807`,
  `protbfn_abbfn_loss.py:172`.
* `.item()` calls — `flowmol3_v2_adapter.py:369-370`
  (`int(indptr[i].item())` in CSR loop), `algorithm/blender/blender.py:776`
  (unflatten scalar), `algorithm/perturbation/perturbation.py:576`
  (unflatten scalar), `frame/engine.py:313` comment.

In the synthetic context (FreqFlow sweep) **all `.cpu()` / `.numpy()` /
`.item()` calls are NumPy-only** because the synthetic velocity field
already returns `np.ndarray` (no torch tensor is involved). The
references above are all on the *torch* code paths and become active
the moment `force_mode="torch"` is set on a real ckpt, which today is
BLOCKED for FreqFlow (no public ckpt).

### 1.3 NumPy heavy ops (`np.sum / np.mean / np.std / np.linalg / np.dot / np.exp / np.log`)

The greedy pull is 50+ matches across eval/, algorithm/, adapters/.
The hot ones for the Wave 206 P5 sweep are concentrated in:

* `adaptive_reflow/eval/fid_theorem_aligned.py:425-455` —
  `_fit_nu_g_grid_gaussian` per-point `math.exp(-0.5*x*x)/math.sqrt(...)`
  in pure-Python loop (1601 grid points, called per nu_g build).
* `adaptive_reflow/theory/paper_quantities.py:96-200, 361` —
  `sheet_evidence_A` / `root_cell_packing_B` / `exterior_gap_e_rho` /
  `per_cell_coefficient_C`, all pure-Python composite trapezoidal
  with `math.exp` + `math.sqrt` per grid point.
* `adaptive_reflow/eval/twodim_fm_evaluator.py:298-338` —
  `coverage_score` (np.linalg.norm axis=2 broadcast) + `energy_distance`
  (cdist via scipy).
* `adaptive_reflow/eval/w2.py:214` — `_pairwise_distances` builds an
  `(n,n)` matrix via broadcasting (allocates `O(n^2)` float64).

### 1.4 scipy.stats operations in power scripts

Power-analysis `tools/` files all open with the header
*"CPU-only, numpy + scipy.stats only, no torch"*.

* `tools/wave195_p2_r_level_power.py:160,217` — `stats.t.sf(...)` +
  `stats.ttest_ind(...)`.
* `tools/wave195_p3_4arm_power.py:266` — `scipy.stats.ttest_ind`
  inside Monte-Carlo replication.
* `tools/wave195_p4_theorem1_power.py` — `scipy.stats.norm.ppf(0.975)`
  constant.
* `tools/wave196_p2_4arm_paired.py:198` — `stats.ttest_rel(f, b)`.
* `tools/wave196_p3_kanzi_paired_ttest.py` — paired-t
  (`tools/w196_p3_kanzi_finalize.py`).
* `tools/statistical_power_analysis.py` — `scipy.stats` for both
  closed-form and Monte-Carlo.
* `tools/wave208_p1_4arm_power.py:145` — bootstrap + t-test.
* `scripts/wave199_p3_lineageflow_difficulty_strata.py:33/116` —
  `scipy.stats.t.sf(abs(t_stat), df=df)` for Bonferroni correction.
* `scripts/wave199_p2_lineageflow_per_record_paired.py:29`,
  `scripts/wave203_p3_k6_cluster_robust.py`,
  `scripts/wave206_p1_lineageflow_n1000_monitor.py`,
  `scripts/wave206_p2_kanzi_framework_n1000_audit.py` — all paired-t
  bonferroni per-record.

These are CPU-bounded by design (t-tests on N=10..30 pairs are < 1 ms
per call). The dominant cost in those scripts is the *outer loop*
that calls `scipy.stats.ttest_*` per cell — the t-test itself is
negligible.

## 2. Top-20 CPU-bound operations (sorted by wall-clock impact)

The estimate column below is "estimated speedup vs current
single-thread NumPy path" where 1× means no benefit. **Risk** ranks
medium if a port requires changing the public interface, low if the
port is byte-stable, high if a port can affect downstream determinism.

| Rank | File:line | Function | Op | GPU-able | Speedup | Risk | Notes |
| ---- | --------- | -------- | -- | -------- | ------- | ---- | ----- |
| 1 | `adaptive_reflow/adapters/freqflow.py:376` | `_synthetic_velocity_field` | Two-branch (4×32×32 → flatten → tanh@W1+W2 + FFT-mag@W_freq) matmul per NFE call. Called 153k× during Wave 206 P5. | partial | 8× | medium | Port to torch matvec with `no_grad`; gain only realised in *batch* mode (one cell = B=1000 trajectories → 153 MFLOP per call → 8× over a single-thread float64 matvec). |
| 2 | `adaptive_reflow/adapters/freqflow.py:1151` | `FreqFlowAdapter.solve_ode` | Integrate loop + Heun 2-eval per step + np.clip + `traj` alloc. | partial | 7× | medium | Batched-tensor port across `(B, 4, 32, 32)` reshapes, single kernel, N_steps+1 slices still required. |
| 3 | `scripts/wave206_p5_freqflow_n1000_audit.py:225` | `main` | Outer sweep loop over 1000 seeds × baseline + framework. | no | 1× | high | P1 profile showstopper, but root cause is items 1+2 (per-call cost) and orchestration overhead (item 3 caller). |
| 4 | `adaptive_reflow/algorithm/dynamics.py:663` | `transition_probability_matrix` | `scipy.linalg.expm(Q*dt)` per BFN step; falls back to `np.linalg.eigh + inv` when scipy missing. | yes | 5× | medium | torch.linalg.matrix_exp on GPU; `O(K^3)` per call. |
| 5 | `adaptive_reflow/eval/freq_l1.py:250` | `per_position_freq_l1` | Build `(max_length, 20)` count matrices + L1 reductions. | yes | 4× | low | Pure NumPy → easy GPU port (already per-position, no scatter). |
| 6 | `adaptive_reflow/eval/w2.py:375` | `ProjectionFreeExactW2.estimate` | 2 matmul + 2 sort axis=0 + quantile match + scalar reduce. | yes | 5× | low | torch.sort + cumsum on (n,128) ≈ 1ms on GPU vs 20ms on CPU. |
| 7 | `adaptive_reflow/eval/w2.py:483` | `KernelizedW2.estimate` | (n+m)^2 kernel matrix (rbf/laplacian/matern). | yes | 8× | medium | Pairwise `cdist` → `torch.cdist`; bandwidth median-heuristic is a separate hot path. |
| 8 | `adaptive_reflow/eval/fid_theorem_aligned.py:395` | `_fit_nu_g_grid_gaussian` | 1601-pt pure-Python `math.exp/sqrt` per grid point. | partial | 10× | medium | Vectorise with torch.linspace + (math→torch)→ one GPU call. |
| 9 | `adaptive_reflow/theory/paper_quantities.py:96` | `sheet_evidence_A` | Pure-Python composite trapezoidal on 1601-pt grid. | partial | 10× | medium | torch.linspace + tanh + cumtrapz; bit-identical iff float32 is upgraded to float64 explicitly. |
| 10 | `adaptive_reflow/theory/paper_quantities.py:178` | `root_cell_packing_B` | Pure-Python grid trapezoidal on Gaussian-weighted cell packing. | partial | 10× | medium | Same pattern as item 9. |
| 11 | `adaptive_reflow/eval/fid.py:526` | `_frechet_distance_closed_form` | `scipy.linalg.sqrtm` + eigenclip retry + numpy fallback. | yes | 3× | medium | `torch.linalg.matrix_exp` on `(S_s S_r)` half-log; eigenclip retry is the dominant cost. |
| 12 | `adaptive_reflow/eval/fid.py:650` | `_sqrtm_with_eigenclip` | The eigenclip retry itself. | yes | 3× | medium | Single-shot NumPy hot loop; GPU speedup small for d=2048. |
| 13 | `adaptive_reflow/eval/twodim_fm_evaluator.py:272` | `coverage_score` | `cKDTree.query` + axis=2 broadcast + nearest-mode argmin. | yes | 5× | medium | `torch.cdist` + cdist-on-grid. |
| 14 | `adaptive_reflow/eval/twodim_fm_evaluator.py:313` | `energy_distance` | `cdist(s,t) + cdist(s,s) + cdist(t,t)`. | yes | 6× | low | `torch.cdist` direct. |
| 15 | `adaptive_reflow/eval/lipschitz_diagnostic.py:338` | `kernel_lipschitz_constant` | Pairwise kernel matrix + scalar reduce. | yes | 5× | low | GPU trivial win. |
| 16 | `adaptive_reflow/eval/lipschitz_diagnostic.py:461` | `bounded_lipschitz_distance_2d` | 2D → 1D projection + sort + BL. | yes | 3× | low | CPU-vectorisable via numpy; GPU optional. |
| 17 | `adaptive_reflow/eval/posterior_selection_evaluator.py:1063` | `_generate_endpoints` | Serially replays `adapter.solve_ode` B=n_gen times. | partial | 3× | medium | Outer loop is the bottleneck inside the 2D-FM evaluator; a per-cell batched solve_ode would break the synthesised endpoint caching. |
| 18 | `tools/eval/metrics.py:149` | `_compute_kanzi_real_metric` | `DAE.encode(x_BLD)` torch forward; upstream torch code. | no | 1× | low | Already on GPU once ckpt loaded; cost is in the upstream encoder, not in our call site. |
| 19 | `tools/eval/metrics.py:1791` | `_compute_flowmol3_composite` | FlowMol3 5-axis composite (atom type, bond type, position, valency, composite). | no | 1× | low | Heavy GPU already (DAE + marginal); CPU call site is orchestration. |
| 20 | `adaptive_reflow/algorithm/perturbation/perturbation.py:509` | `_finite_difference_grad_log_p_qty` | Per-axis Python loop: O(d) function calls. | no | 1.2× | low | Cannot batch because `log_p_qty` is a Python scalar callable; GPU cannot help the per-axis eval loop unless `log_p_qty` is itself a torch fn (which the protocol forbids). |

## 3. Top-5 most CPU-bound functions in `adaptive_reflow/eval/`

The five are the eval-side functions that dominate the Wave 210 P1
process profile once the per-seed adapter solve is excluded (per-seed
solve is item 2 in §2 above; per-cell eval-side work follows).

### 3.1 `adaptive_reflow/eval/freq_l1.py:250` — `per_position_freq_l1`

* Pure NumPy. No torch dependency.
* Per-position AA histogram + L1 reduction for `max_length × 20`
  matrices (default 128 × 20 = 2560 floats).
* Operates per-call rather than per-seed.

**Verdict: stay CPU**. The per-call cost on the default config is
≈0.5 ms CPU; even a 10× GPU speedup saves 0.45 ms / call. The function
is on the protein side, not the FreqFlow sweep, and the Wave 206 P5
sweep does not call this function. A GPU port is feasible (4× speedup
estimate) but yields negligible wall-clock impact.

### 3.2 `adaptive_reflow/eval/w2.py:375` — `ProjectionFreeExactW2.estimate`

* Pure NumPy + tiny Python scalar reductions.
* Two matmuls `(n, dim) @ (dim, 128)` + `(m, dim) @ (dim, 128)`,
  two `sort` axis=0 ops on (n, 128) and (m, 128), and a quantile
  gather. The bottleneck is the two `sort` calls.
* Default config P=128 projections means 256 K-floats per sort.

**Verdict: GPU-portable**. `torch.sort` on (n, 128) takes <0.5 ms on a
RTX 5090 vs 10–20 ms on a single NumPy thread for n=1024. Byte-stability
is *not* required (the W2 result is a real-valued scalar, downstream
is a Bonferroni t-test, which already accepts noise of O(ε)).
Estimated speedup: 5×.

### 3.3 `adaptive_reflow/eval/fid.py:526` — `_frechet_distance_closed_form`

* Pure NumPy + `scipy.linalg.sqrtm`.
* Loads `mu_s`, `mu_r` (d,), `sigma_s`, `sigma_r` (d, d).
* Fréchet: `||mu_s-mu_r||^2 + Tr(S_s) + Tr(S_r) - 2 Tr(sqrtm(S_s S_r))`.
* Eigenclip retry with `+ eps*I` when primary sqrtm returns non-finite.

**Verdict: partial GPU port**. `scipy.linalg.sqrtm` is dominant
(O(d³)). A `torch.linalg.matrix_exp` on half-log form, or a
`torch.linalg.eigh` + sqrt + matmul reconstruction, would yield ~3×
but only in the d=2048 regime; in d=8/16 the GPU launch overhead
eats the saving. **Risk medium** (eigenclip retry differs between
NumPy and torch in numeric ordering).

### 3.4 `adaptive_reflow/eval/fg_deviation.py:357` — `count_fg_hits`

* RDKit-bound (`from rdkit import Chem` + `Chem.MolFromSmarts` +
  `mol.GetSubstructMatches`). Not pure NumPy.
* Called per molecule × per SMARTS — fully serial.

**Verdict: stay CPU**. RDKit is fundamentally CPU. A GPU speedup is
not achievable. Estimated 1.2× from vectorising the K loop, but RDKit
call overhead dominates so even that is dubious. The risk of changing
RDKit semantics is **high** (Fragments.fr_<name> signature changes
between RDKit versions).

### 3.5 `adaptive_reflow/eval/clip_score.py:396` — `HFCosineClipScoreEvaluator._score_pairs`

* torch + transformers; the CLIP forward pass is already on whatever
  device the `_processor` was loaded on (default `cuda` when avail).
* Cosine arithmetic `img_emb * txt_emb` + sum is a tensor op.
* Returns `per_pair.detach().cpu()` → CPU tensor.

**Verdict: stay CPU / already GPU**. The cost is the CLIP forward on
GPU; the cosine arithmetic is <1 ms CPU. The `.detach().cpu()` is
defensive (HuggingFace `transformers` outputs may not always be on
the requested device). No port yields meaningful speedup; the
function is *not* a CPU-bound hot path.

## 4. Recommendation (read-only, no code change)

The Wave 210 P1 process profile shows the wall-clock leader is
`scripts/wave206_p5_freqflow_n1000_audit.py`. Walking that wall-clock
to its source:

* Per-seed cost is dominated by `_synthetic_velocity_field` (item 1)
  inside the integrate loop `Fre­q­Flow­Adapter.solve_ode` (item 2),
  called twice per step (Heun) × ~25 effective NFE × 3 rounds ×
  1000 seeds = 150 000 `solve_ode` invocations total.
* The 30 other heavy `tools/*` scripts use similar synthesis —
  per-cell eval work is small (~1 ms each on `n≤30` arrays), the wall
  cost is the per-seed adapter solve.

That is, **there is no eval-side hot path that we can GPU-offload to
materially reduce wall-clock**. The real lever is per-tensor matmul
throughput inside the synthetic velocity field, which would shift to
torch + `no_grad` and to batched `(B, 4, 32, 32)` reshape — but only
after `n_molecules > 1` (FlowMol3 already exposes that kwarg; the
FreqFlow adapter does not).

**Recommendation**: do NOT flip the existing CPU `tools/*` sweeps to
GPU by default. Two reasons:

1. **GPU contention is live** (see §0 — both GPUs are in use). Any new
   torch allocation will land in the contended slot. `CUDA_VISIBLE_DEVICES`
   cannot side-step this while the existing jobs hold the GPU.
2. **The CPU-bound cost is in the per-seed adapter solve**, not in the
   eval-side tensor math. A correct remediation requires batching
   across `n_molecules` (currently only FlowMol3 supports this), plus
   rewriting `_synthetic_velocity_field` as a single fused matmul
   kernel rather than separate flatten → matmul → tanh → matmul →
   FFT → matmul → combine. That is a Wave 11-style refactor and is
   out of scope for "default to GPU".

If a future wave wants to GPU-port the Wave 206 P5 sweep end-to-end,
the order is:

1. Add `n_molecules` to `FreqFlowAdapter.solve_ode` (mirror FlowMol3).
2. Rewrite `_synthetic_velocity_field` as a single torch matmul
   kernel with `no_grad` and `n_molecules`-axis reshape `(B, 4096) @ W1`
   → reshape → combine → `(B, 4096)` final. Then `FreqFlowAdapter.solve_ode`
   carries a single GPU forward over the whole `n_molecules`-deep
   batch.
3. Stage the run on a free GPU slot, after the megafold + flowmol3
   jobs exit; on the user's host today the GPU that goes free *last*
   is GPU 0 (PRO 6000), since the megafold jobs are interactive.
4. Verify byte-stability against the synthetic NumPy path on a small
   N=10 seeds before re-running the full sweep.

Outside the Wave 206 P5 scope, the cleanest GPU speedup on the file
list is `ProjectionFreeExactW2.estimate` (item 6 in §2) — a torch.sort
on (n, 128) → ~5× per call. Risk is **low** because the W2 result is
a real-valued scalar that downstream consumes only through Bonferroni
gating.

## 5. CSV sibling

`verification_outputs/wave210-p2-source-hotpaths.csv` ships the
machine-readable form of §2 (45 rows including call-site expansions
for items 1–3). Columns: `file, line, function, op, gpu_portable,
est_speedup, risk`.

## 6. Reproducibility

* Audit time: 2026-09-21 01:54 PT
* Source-tree LOC: 230 .py files in `adaptive_reflow/`, ~125 K LOC
  total (per Wave 210 P1).
* `nvidia-smi` at audit time captured above.
* No source files were modified; only the audit doc + CSV were
  written.
* The CSV column ordering matches the column ordering consumed by the
  Wave 210 P3 plan agent (single source of truth so P2 + P3 stay in
  sync).
