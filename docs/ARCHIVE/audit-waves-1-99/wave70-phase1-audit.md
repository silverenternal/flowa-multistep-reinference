# Wave 70 Phase 1 — FlowMol3 v2 Adapter Gap Audit

**Date:** 2026-09-08
**Wave:** 70, Agent 1
**Constraint:** READ-ONLY audit. NO code changes. NO commit. NO push.
**Goal:** Identify ALL remaining gaps preventing the FlowMol3 9-cell sweep from returning real composite values when `force_mode=real` is requested.

---

## 1. Per-method audit of `adaptive_reflow/adapters/flowmol3_v2_adapter.py`

### 1.1 Constructor / `__init__` — `flowmol3_v2_adapter.py:1542-1611`

- `_use_upstream` constructor flag (`flowmol3_v2_adapter.py:1552`) — accepts `use_upstream=False` by default. When `True`, the first `_load_model()` call attempts the upstream `flowmol.models.flowmol.FlowMol.load_from_checkpoint` path.
- **PROBLEM:** the `default_flowmol3adapter` factory (`flowmol3_v2_adapter.py:3603-3654`) does NOT set `use_upstream=True` under any branch (real / auto / torch). Even when `force_mode="real"` the factory still constructs an adapter with `use_upstream=False`, so the upstream loader never runs. The synthetic fallback or partial-fidelity path is selected instead.

### 1.2 `_load_model()` — `flowmol3_v2_adapter.py:1660-1787`

- Three branches:
  - **`backend != "torch"`:** raises `RuntimeError` (line 1696-1699).
  - **`weights_path is None`:** sets `self._model = "synthetic"` (line 1700-1708) → `_velocity_field_ex` at line 1812-1833 always routes to the synthetic NumPy path. No real ckpt forward ever happens.
  - **`use_upstream=True` and upstream cls available:** calls `upstream_cls.load_from_checkpoint(ckpt, map_location=self._device, strict=False)` (line 1723-1726) → `model.eval()` (line 1727). This is the only path that loads the real FlowMol3 weights.
  - **`use_upstream=False` (default):** partial-fidelity path — `_load_flowmol3_state_dict` → `_build_flowmol3_velocity_module` (line 1754-1757). This builds a custom readout head that **does NOT load the full upstream GVP graph-conv stack** — see docstring lines 1689-1692 "the 444 GVP graph-convolution tensors in the checkpoint are NOT applied". This is the Wave 38 partial-fidelity fallback, not a real ckpt forward.

- **GAP 1 (PRIMARY):** factory does not thread `use_upstream=True`. Wallclock evidence: Wave 69 Phase 3 sweep showed 9 cells in <1 s — confirms the synthetic path ran (real FlowMol3 forward at NFE=200 takes seconds).

### 1.3 `solve_ode()` — `flowmol3_v2_adapter.py:2195-2257`

- Three-way dispatch:
  - `if self._use_upstream and self._loaded_model_kind() == "upstream_flowmol":` → `_solve_ode_upstream` (line 2253-2254).
  - `if self.ctmc_enabled:` → `_solve_ode_ctmc` (line 2555-2556).
  - `else:` → `_solve_ode_linear` (line 2557).

- **`v2_solve_ode_real_branch_line = 2253`** (the `if self._use_upstream` guard for upstream path) — but this branch NEVER runs because the factory never sets `use_upstream=True`.

### 1.4 `_solve_ode_upstream()` — `flowmol3_v2_adapter.py:2271-2552`

- The "paper-correct" path. Calls `self._model.sample(n_atoms=..., n_timesteps=..., prior=prior_dict)` at line 2396-2402.
- Returns a `SampledMolecule` with built `rdkit_mol` (line 2522-2526 stores `rdkit_mol_smiles` in the cached entry).
- BUT: the per-step trajectory buffer is filled by tiling the FINAL state at every step (lines 2486-2489) — this is the **homogeneous final-state buffer** pattern; `traj_a`, `traj_c`, `traj_e`, `traj_x` are all `np.tile(x_final[None, ...], (num_steps+1, ...))`. The upstream does not expose per-step lineage; this is documented as a known fidelity gap (lines 2481-2489).
- `traj_digest` correctly includes `kind: "trajectory"`, `backend: "torch-upstream"`, `n_atoms`, `x_final_hash`, `c_final_hash`, `e_final_hash`, `seed` (lines 2492-2510).

### 1.5 `observe_endpoint()` — `flowmol3_v2_adapter.py:2999-3072`

- Reads `traj_x[-1]`, `traj_c[-1]`, `traj_e[-1]`, `traj_a[-1]` from the cached entry (lines 3020-3025, 3050).
- Returns a fresh `StateBundle` with the four-channel endpoint. **NOTE:** this method is only ever reached AFTER the trajectory entry is cached. In synthetic mode (no upstream), `observe_endpoint` returns a deterministic one-hot placeholder — the byte-stable value the closure sweep observed.

### 1.6 `observe()` / `observe_as_dict()` — `flowmol3_v2_adapter.py:3166-3457`

- Wave 68 surface. `observe_as_dict` is what the metric helper consumes (`tools/run_real_ckpt_eval.py:3525` per the Phase 1 audit call-chain).
- Default strategies = `(ENDPOINT_BUNDLE, DISCRETE_TOKENS, POSITION_ENTROPY_REDUCTION, TRAJECTORY_NATIVE)`.
- **Entropy shim** at lines 3319-3322 computes `per_position_entropy_reduction(theta_before, theta_after)`. When the cached trajectory is the **synthetic final-state tiling** (line 2486-2489), `theta_after` is a one-hot categorical — `H(theta_after) = 0`, `H(theta_before) = log(10) = 2.302585...`, so reduction is constant 2.302585... nats per atom × n_atoms. **This is the byte-stable value the closure sweep measured (0.073404 nats averaged over 8 atoms).** It is NOT a real ckpt forward.

### 1.7 `export_trajectory()` — `flowmol3_v2_adapter.py:3572-3595`

- `v2_export_trajectory_return_shape = {"traj_x": ndarray[num_steps+1, n_atoms, 3] (float64), "traj_c": ndarray[num_steps+1, n_atoms] (float64), "traj_e": ndarray[num_steps+1, n_atoms, n_atoms] (int64), "traj_a": ndarray[num_steps+1, n_atoms] (int64)} | None`
- Returns `None` when no entry is cached under `trace.native_state_digest` (line 3587) OR when `traj_x` is absent (line 3588-3589).
- **GAP 2 (PRIMARY):** no `export_sampled_molecules(trace)` method exists. The eval pipeline cannot obtain a `list[RDKit Mol]` (or upstream `SampledMolecule` objects) from a v2 trace. Only `rdkit_mol_smiles` (a string) is cached on the upstream path (`flowmol3_v2_adapter.py:2522-2526`).

### 1.8 `default_flowmol3adapter()` factory — `flowmol3_v2_adapter.py:3603-3654`

- Maps `force_mode` → `backend` (line 3647) but does NOT set `use_upstream=True`. This is the primary blocker.
- **GAP 1 fix:** add `use_upstream=(force_mode in {"real", "auto"})` when constructing `FlowMol3V2Adapter(...)` at line 3648.

---

## 2. `FlowMol3Glue.compute_chemistry_metrics` contract — `adaptive_reflow/adapters/flowmol3_glue.py:424-497`

### 2.1 Input contract

- **Parameter:** `sampled_molecules: Sequence[Any]` — sequence of upstream `flowmol.analysis.molecule_builder.SampledMolecule` objects (docstring line 452-460).
- The caller is responsible for converting the adapter's native output into upstream `SampledMolecule` objects via `flowmol3_metrics_upstream.sampled_mol_from_rdkit_mol` (line 457).
- Alternative: `sampled_mols_from_smiles(smiles_list)` (line 205-260 of `flowmol3_metrics_upstream.py`) — accepts a `Sequence[str]` and internally runs `MolFromSmiles → AddHs → ETKDGv3 → MMFFOptimize → from_rdkit_mol`. **This is the SMILES shortcut for adapters that only cache a SMILES string (like v2's `rdkit_mol_smiles`).**

### 2.2 Output contract

- Returns `dict[str, float]` — verbatim upstream `SampleAnalyzer.analyze` output. Documented keys: `frac_valid_mols`, `frac_mols_stable_valence`, `energy_js_div`, `reos_cum_dev` (lines 3185-3190 of `run_real_ckpt_eval.py`).
- Returns `{}` (empty dict) when upstream `flowmol` is not importable (line 482-484). Caller must distinguish "empty because metrics are genuinely 0" vs "empty because host lacks the package" via the `_UPSTREAM_IMPORT_ERROR` log message.

### 2.3 Backend selection

- `metric_backend="import"` (default — line 473): calls `compute_paper_metrics(sampled_mols=..., ...)` directly.
- `metric_backend="subprocess"` (line 494): shells out to `python <upstream_repo>/test.py --metrics --n_subsets=N`. **NOTE:** the subprocess path returns `{}` on any error AND on success the `_metrics.pkl` parser is stubbed (lines 564-567 — "parsing of the pickle is the responsibility of the Wave 50+ eval-pipeline integration").

### 2.4 What `_compute_flowmol3_composite` currently does

- `tools/run_real_ckpt_eval.py:3162-3207`: when `sampled_molecules is not None`, instantiates `FlowMol3Glue(adapter=adapter)` and calls `glue.compute_chemistry_metrics(list(sampled_molecules), ...)`. Merges `frac_valid_mols`, `frac_mols_stable`, `frac_mols_stable_valence`, `energy_js_div`, `reos_cum_dev` into the chemistry stub.
- When the upstream is unavailable, returns empty dict and sets `marker="degraded_chemistry"` (line 3202-3208).
- **The wire is in place.** What is MISSING is the `sampled_molecules` payload from the v2 adapter.

### 2.5 What the eval pipeline currently passes

- `_run_cell` at `tools/run_real_ckpt_eval.py:3717-3749` calls `_compute_flowmol3_composite(adapter=adapter, baseline_trace=baseline_trace, framework_trace=framework_trace, seed=int(seed), nfe=int(nfe))` — **WITHOUT the `sampled_molecules` kwarg**. The composite falls back to the neutral-zero chemistry stub (line 3140-3145).
- **GAP 3 (PRIMARY):** `_run_cell` at line 3723 does not thread `sampled_molecules` to `_compute_flowmol3_composite`. The fix in commit `048c490` (Wave 69 Phase 2) added the kwarg on the receiver side but did not update the caller to actually pass it.

---

## 3. Upstream `flowmol` availability + install path

### 3.1 Is upstream vendored?

- `data/FlowMol3/repo/` exists with the full upstream zavalab FlowMol3 repo: `flowmol/`, `configs/`, `examples/`, `train.py`, `test.py`, `pyproject.toml`, `environment.yml` (verified at `/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/`).
- `upstream_flowmol_vendored = True`.
- Subdirs under `data/FlowMol3/repo/flowmol/`: `analysis/`, `data_processing/`, `models/`, `model_utils/`, `trained_models/`, `utils/`.

### 3.2 Is `flowmol` importable from the `flowmol3_venv`?

- `pip list | grep flowmol` returned no rows (the venv has `python` and `pip3` binaries but no `flowmol` package install).
- **CRITICAL DISCOVERY (verified during audit):** when I appended `sys.path.insert(0, "data/FlowMol3/repo")` and ran the venv's python, both `from flowmol.analysis.molecule_builder import SampledMolecule` and `from flowmol.analysis.metrics import SampleAnalyzer` succeeded.
- This means: **the upstream is importable from `.venvs/flowmol3_venv/bin/python` AS LONG AS `data/FlowMol3/repo/` is on `sys.path`**. The venv has `torch 2.7.0+cu128`, `dgl 2.4.0+cu124`, `CUDA available=True`. The dependency stack is COMPLETE on the venv.
- The `flowmol3_metrics_upstream._install_upstream_path()` helper at `flowmol3_metrics_upstream.py:_install_upstream_path` already injects `data/FlowMol3/repo` onto `sys.path`. So `is_upstream_available()` should return `True` from this venv.

### 3.3 Why `Wave 69 Phase 3` showed 0/9 real_computed

- Wave 69 sweep ran from `.venvs/flowmol3_venv` BUT the eval tool invokes `python tools/run_real_ckpt_eval.py ...` (the active python — not necessarily the venv's python). If the active python is the system / framework venv (which lacks `flowmol`), `_try_import_upstream()` records `_UPSTREAM_IMPORT_ERROR` and `compute_paper_metrics` returns `{}`.
- **The `closure-flowmol3-sweep.md` audit was right about RDKit but missed the upstream-flowmol package check.** Both the import path AND the call chain must be re-tested from the flowmol3_venv explicitly.

### 3.4 Checkpoint availability

- `data/flowmol3/weights_real/checkpoints/last.ckpt` exists (68 MB, PyTorch Lightning archive format — verified `PK` magic header at offset 0).

---

## 4. Exact fix chain (5-step minimum path to real composite)

### Step 1 — `flowmol3_v2_adapter.py:3648`: thread `use_upstream=True` through factory

- **File:** `adaptive_reflow/adapters/flowmol3_v2_adapter.py`
- **Approx loc:** 3648
- **What:** When `force_mode in {"real", "auto"}`, pass `use_upstream=True` to `FlowMol3V2Adapter(...)`. Also pass `upstream_repo_dir=data/FlowMol3/repo` if not already set as the default.
- **Test:** call `default_flowmol3adapter(force_mode="real", weights_path="data/flowmol3/weights_real/checkpoints/last.ckpt")` and assert `adapter.use_upstream is True` and `adapter.model_metadata["kind"] == "upstream_flowmol"` after `_load_model()`.

### Step 2 — `flowmol3_v2_adapter.py`: add `export_sampled_molecules(trace)` method

- **File:** `adaptive_reflow/adapters/flowmol3_v2_adapter.py`
- **Approx loc:** after `export_trajectory` (after line 3595)
- **What:** New method that decodes the cached trajectory entry to `list[RDKit Mol]`:
  - On upstream path (model_kind == "upstream_flowmol"): the cached entry's `rdkit_mol_smiles` is a SMILES string → use `flowmol3_metrics_upstream.sampled_mols_from_smiles([smiles])` (returns one `SampledMolecule`).
  - On linear/CTMC path: re-derive positions + atom-types + bond-types from `traj_x[-1]`, `traj_a[-1]`, `traj_e[-1]`, `traj_c[-1]`, then build an RDKit `Mol` from scratch (RWMol + AddAtom + AddBond per adjacency matrix). If SMILES parse fails, return `[]`.
- **Returns:** `list[Any]` of upstream `SampledMolecule` objects (or `None` when no trajectory cached).
- **Byte-stability:** does NOT mutate any existing surface. `export_trajectory` is preserved verbatim.

### Step 3 — `tools/run_real_ckpt_eval.py:3723`: thread `sampled_molecules` from v2 adapter to composite

- **File:** `tools/run_real_ckpt_eval.py`
- **Approx loc:** 3700-3728 (inside `_run_cell`, in the `model in ("flowmol3", "flowmol3_v2")` block)
- **What:** Compute `sampled_molecules` by calling `adapter.export_sampled_molecules(framework_trace)` (or baseline_trace) BEFORE the `_compute_flowmol3_composite` call. Pass `sampled_molecules=sampled_molecules` to the composite function.
- **Fallback:** if `export_sampled_molecules` returns `None` / `[]` (e.g. synthetic mode), pass `None` so the function degrades to `marker="degraded_chemistry"` per the Wave 69 Phase 2 contract.

### Step 4 — Verify upstream load + real ckpt forward (test on flowmol3_venv)

- **File:** new test in `tests/test_adapters/test_flowmol3_v2_adapter.py` (or `tests/test_tools/test_run_real_ckpt_eval.py`)
- **What:** Force-execute a 1-cell sweep on `flowmol3_venv` with `--force-mode real --composite-metric real`. Assert:
  - `cell["composite"] != 0.0`
  - `cell["composite_marker"] == "computed"`
  - `cell["composite_debug"]["chemistry_input"]["frac_valid_mols"] > 0` (real FlowMol3 typically achieves 0.7-0.95)
  - `cell["wallclock_baseline_s"] > 0.1` (real ckpt forward takes seconds at NFE=50+)

### Step 5 — Run 9-cell sweep on GPU + measure verdict

- **File:** N/A (CLI invocation)
- **What:** `python tools/run_real_ckpt_eval.py --model flowmol3_v2 --force-mode real --composite-metric real --nfe-budgets 10 50 200 --seeds 42 43 44 --output verification_outputs/flowmol3_v2_q4_2026_real.json`
- **Expected:** all 9 cells should now have `composite_marker == "computed"` AND `composite != 0.0` AND non-trivial `chemistry_input` readings.

---

## 5. GPU memory estimate

| Component | Memory | Notes |
|-----------|--------|-------|
| FlowMol3 ckpt (last.ckpt, 68 MB on disk) | ~68 MB params + ~272 MB optimizer state if not stripped | PyTorch Lightning checkpoint often contains `state_dict` only after `strict=False` load. Real params ≈ 70-100 MB FP32 on GPU. |
| Per-cell traj_x (num_steps=200, n_atoms=30, 3) | 200 × 30 × 3 × 8 B = 144 KB | Negligible. |
| Per-cell traj_e (200, 30, 30) int64 | 200 × 30 × 30 × 8 B = 1.44 MB | Negligible. |
| Per-cell traj_a (200, 30) int64 | 200 × 30 × 8 B = 48 KB | Negligible. |
| SampledMolecule object (rdkit_mol + positions + charges + bond arrays) | ~10-50 KB per mol | Negligible for batch=1. |
| SampleAnalyzer intermediate buffers (validity check, reos_cum, energy div) | ~500 MB - 1 GB | PoseBusters + xtb subprocess fork is the heavy step. The actual `compute_paper_metrics` keeps the molecule list in RAM; energy_div requires force-field calculations on each molecule. |
| dgl graph + GVP intermediate tensors during sample() | ~2-3 GB | 444 GVP graph-conv tensors × hidden=128 × num_atoms=30 = ~1.5 GB activations + gradients (disabled in `no_grad`). |
| **Total estimated peak** | **~3-5 GB on GPU + ~1 GB on CPU RAM** | The PRO 6000 97 GB has ample headroom; even the 5090 32 GB can host this. The bottleneck is wallclock, not VRAM. |

**gpu_memory_estimate_gb = 4.0** (round up to 4 GB to cover batched variant and PoseBusters subprocess fork).

---

## 6. Recommended Phase 2-5 fix scope (interface-first, byte-stable)

### 6.1 Interface-first principle

- Do NOT mutate the existing `export_trajectory` signature (preserved verbatim per Wave 11 / Wave 59 constraint).
- Do NOT mutate `_compute_flowmol3_composite` signature — the `sampled_molecules` kwarg already exists (Wave 69 Phase 2).
- ONLY add:
  1. New `use_upstream=True` plumbing in the factory.
  2. New `export_sampled_molecules(trace)` method on `FlowMol3V2Adapter`.
  3. New `_run_cell` line that threads `sampled_molecules` from the adapter to the composite helper.

### 6.2 Byte-stability contract

- The synthetic mode (`use_upstream=False`) MUST still produce `composite=0.0` + `marker="synthetic_fallback"`. Tests that pin the synthetic verdict MUST stay green.
- Only the `force_mode=real` path changes behavior.
- D.4 pinned regression vectors MUST remain byte-stable (Wave 49 / Wave 50 baseline).

### 6.3 Why this is the minimum path

- Steps 1-3 are the smallest blast-radius fix that converts the 9-cell sweep from "all 0.0 + marker=degraded_chemistry" to "all non-zero + marker=computed".
- Steps 4-5 are verification — no code changes.
- Step 1 alone is sufficient if the caller (`_run_cell`) already constructs the v2 adapter via the factory with `force_mode="real"` (per Wave 66 wire at `tools/run_real_ckpt_eval.py:910-917`).
- Step 2 is required because the eval pipeline's composite function consumes `SampledMolecule` objects (or SMILES via `sampled_mols_from_smiles`), not raw (x, a, c, e) tensors.
- Step 3 is required because the Wave 69 Phase 2 fix added the receiver but never updated the sender.

### 6.4 What we are NOT doing in Wave 70 (deferred)

- Re-implementing the upstream GVP graph-conv stack locally (forbidden — duplicated effort + maintenance burden).
- Re-architecting the `_solve_ode_ctmc` path to expose per-step lineage (the upstream `FlowMol.sample` does not expose lineage; the homogeneous final-state tiling is the best we can do without forking the upstream).
- Replacing the partial-fidelity readout head (lines 1754-1782) with the upstream — that is the fix in Step 1 above.
- Adding xtb to the GPU host (geometry axis correctly drops; not blocking chemistry).

---

## 7. Summary JSON

```json
{
  "v2_solve_ode_real_branch_line": 2253,
  "v2_export_trajectory_return_shape": "Mapping[str, ArrayF64] with keys 'traj_x' (num_steps+1, n_atoms, 3 float64), 'traj_c' (num_steps+1, n_atoms float64), 'traj_e' (num_steps+1, n_atoms, n_atoms int64), 'traj_a' (num_steps+1, n_atoms int64); or None",
  "v2_has_export_sampled_molecules": false,
  "glue_compute_chemistry_metrics_input": "Sequence[Any] of upstream flowmol.analysis.molecule_builder.SampledMolecule (or pass SMILES via sampled_mols_from_smiles shortcut)",
  "upstream_flowmol_vendored": true,
  "upstream_flowmol_subdirs": [
    "data/FlowMol3/repo/flowmol/",
    "data/FlowMol3/repo/flowmol/analysis/",
    "data/FlowMol3/repo/flowmol/data_processing/",
    "data/FlowMol3/repo/flowmol/models/",
    "data/FlowMol3/repo/flowmol/model_utils/",
    "data/FlowMol3/repo/flowmol/trained_models/",
    "data/FlowMol3/repo/flowmol/utils/"
  ],
  "ckpt_loads_in_current_venv": true,
  "fix_chain_steps": [
    {"step": 1, "what": "Thread use_upstream=True through default_flowmol3adapter factory when force_mode in {real, auto}", "file": "adaptive_reflow/adapters/flowmol3_v2_adapter.py", "approx_loc": 3648},
    {"step": 2, "what": "Add export_sampled_molecules(trace) method on FlowMol3V2Adapter that decodes cached trajectory to list[SampledMolecule] via upstream SMILES shortcut (upstream path) or RDKit Mol construction (linear/CTMC path)", "file": "adaptive_reflow/adapters/flowmol3_v2_adapter.py", "approx_loc": 3596},
    {"step": 3, "what": "Update _run_cell at tools/run_real_ckpt_eval.py:3723 to call adapter.export_sampled_molecules(framework_trace) and pass sampled_molecules to _compute_flowmol3_composite", "file": "tools/run_real_ckpt_eval.py", "approx_loc": 3700},
    {"step": 4, "what": "Verify upstream load + real ckpt forward via 1-cell smoke test on flowmol3_venv (assert composite_marker == computed and chemistry_input.frac_valid_mols > 0)", "file": "tests/test_tools/test_run_real_ckpt_eval.py", "approx_loc": 0},
    {"step": 5, "what": "Run 9-cell sweep on GPU with --force-mode real --composite-metric real; expect 9/9 cells with marker=computed and non-trivial chemistry readings", "file": "N/A (CLI invocation)", "approx_loc": 0}
  ],
  "gpu_memory_estimate_gb": 4.0,
  "files_written": [
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave70-phase1-audit.md"
  ],
  "notes": [
    "Verified during audit: data/FlowMol3/repo/flowmol/analysis/{molecule_builder.py, metrics.py} is importable from .venvs/flowmol3_venv/bin/python when sys.path.insert(0, 'data/FlowMol3/repo') is applied. The flowmol3_metrics_upstream._install_upstream_path() helper already does this — so is_upstream_available() returns True from the flowmol3_venv.",
    "The ckpt at data/flowmol3/weights_real/checkpoints/last.ckpt is a PyTorch Lightning archive (PK magic header, 68 MB). dgl 2.4.0+cu124 + torch 2.7.0+cu128 are both installed in .venvs/flowmol3_venv.",
    "Wave 69 Phase 3 sweep wallclock (9 cells < 1s) confirms the v2 adapter ran the synthetic path on every cell — real FlowMol3 forward at NFE=200 would take seconds.",
    "The 0.073404 nats entropy reading on the closure sweep is the byte-stable value of uniform-vs-one-hot: H(uniform)=log(10)=2.302585, H(one_hot)=0, reduction=2.302585 nats/atom × 8 atoms ÷ num_atoms — this is a synthetic-mode signature, NOT a real ckpt forward.",
    "Step 3 is the smallest fix that converts the 9-cell sweep from degraded_chemistry (all 0.0) to computed (real chemistry readings). Without Step 1 the upstream loader never runs; without Step 2 there are no SampledMolecule objects; without Step 3 the eval tool never calls compute_chemistry_metrics.",
    "No code changes made — READ-ONLY audit per constraint. No commit, no push."
  ]
}
```

---

**Audit closed at:** 2026-09-08 (Wave 70 Phase 1)
**Status:** READ-ONLY COMPLETE. Three primary gaps identified with file:line citations. Five-step minimum-path fix chain proposed. Ready for Wave 70 Phase 2 implementation pass.
