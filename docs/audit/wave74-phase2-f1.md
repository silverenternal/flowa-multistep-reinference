# Wave 74 Phase 2 — F1: Multi-molecule cells (n_molecules≥10)

**Date:** 2026-09-08
**Wave:** 74, Agent 2
**Constraint:** Interface-first (`n_molecules` is a NEW opt-in kwarg, default 1 preserves legacy contract). Byte-stable (D.4 vectors unchanged). NO push.

---

## 1. Background & honest reading

Wave 73 closed the **NFE saturation** axis (9-cell FlowMol3 sweep at NFE ∈ {10, 50, 200} × seeds {42, 43, 44}). The verdict held at **`TIE_AT_SATURATION`** because the **single molecule-per-cell** design (n=1) gives ±0.6 run-to-run composite spread — wider than the framework-vs-baseline signal itself.

Per Wave 74 Phase 1 plan §3, the upstream `FlowMol.sample` natively accepts a batched `n_atoms` tensor of shape `(batch_size,)`. F1 is mostly plumbing: thread `n_molecules` from the eval CLI through `_run_cell` → `_solve_baseline` / `_solve_framework` → `adapter.solve_ode` → `FlowMol.sample`. The Wave 73 GAP-1 (factory `use_upstream`) and GAP-3 (`sampled_mols_from_smiles`) fixes are prerequisite.

Wave 73 Agent 3 — GAP-5 (lazy-load) is also prerequisite so the v2 adapter picks up the upstream model on the first `solve_ode` call rather than falling through to the synthetic NumPy field.

---

## 2. What changed

### 2.1 Adapter surface (`adaptive_reflow/adapters/flowmol3_v2_adapter.py`)

| method | change |
|---|---|
| `solve_ode` | new opt-in kwarg `n_molecules: int = 1` (default preserves D.4). Dispatches to a new `_solve_ode_*_batch` method when `> 1`. |
| `_solve_ode_upstream` | new opt-in kwarg `n_molecules: int = 1`. When `> 1`, dispatches to a new `_solve_ode_upstream_batch` which calls `model.sample(n_atoms=[n]*N)` ONCE and decodes each `SampledMolecule` independently. The cached entry carries batched lineage arrays `traj_x_batch` / `traj_c_batch` / `traj_e_batch` / `traj_a_batch` of shape `(n_molecules, num_steps+1, n, ...)` plus a per-molecule SMILES list under `rdkit_mol_smiles_batch`. |
| `_solve_ode_linear` | new opt-in kwarg `n_molecules: int = 1`. When `> 1`, dispatches to a new `_solve_ode_linear_batch` helper which loops the per-step Euler integration `N` times with per-molecule seeds `seed + i * SEED_STRIDE` (SEED_STRIDE = 1009, a prime) and re-samples a fresh native state for each molecule so the per-molecule trajectories are genuinely independent (not just resampled copies). |
| `_solve_ode_ctmc` | new opt-in kwarg `n_molecules: int = 1`. When `> 1`, dispatches to `_solve_ode_linear_batch` (the synthetic CTMC path is equivalent to the synthetic linear path because the synthetic velocity field produces no atom/bond marginals — the CTMC step uses uniform priors, same as the linear relaxation). |
| `_solve_ode_linear_batch` (NEW) | per-molecule integration loop. Pre-samples all `N` priors to determine `max_n_atoms` (the synthetic size prior produces different molecule sizes per draw), allocates batched buffers with that max, slices per-molecule writes into the mol-n region (`traj_x_batch[mol_idx, step_idx, :mol_n] = x_cur`), and pads per-molecule finals to `max_n_atoms` via the `_pad_x` / `_pad_c` / `_pad_a` / `_pad_e` helpers (the latter pads both rows AND columns so square `(n_atoms, n_atoms)` is preserved). |
| `_solve_ode_upstream_batch` (NEW) | calls `self._model.sample(n_atoms=[n]*N)` once, decodes each `SampledMolecule` to its own `(x, a, c, e)` representation, then pads to `max_n_atoms` (handles heterogeneous `n_final` per molecule — the upstream can drop atoms during CTMC, though by design all mols in the batch share the same `n_final` on the published checkpoint). |
| `export_trajectory` | when the cached entry was produced by `n_molecules > 1`, returns the new `traj_x_batch` / `traj_c_batch` / `traj_e_batch` / `traj_a_batch` keys of shape `(N, num_steps+1, n, ...)` plus synthesised legacy `traj_x` / `traj_c` / `traj_e` / `traj_a` views from molecule-0 so existing readers don't crash. |
| `export_sampled_molecules` | when the cached entry carries `n_molecules > 1` + `rdkit_mol_smiles_batch`, calls upstream `sampled_mols_from_smiles` on the batched SMILES list and returns `list[SampledMolecule]` of length `n_molecules` with `marker='ok_batch'` (or `marker='ok_partial_batch'` if any mol fails sanitization). Falls through to the per-mol `(x, a, e)` reconstruction when SMILES aren't available. |

### 2.2 Eval pipeline (`tools/run_real_ckpt_eval.py`)

| change | description |
|---|---|
| `--n-molecules` CLI flag | new opt-in flag with default `1`. The runtime guard in `main()` rejects `n_molecules < 1` with `[ERROR] --n-molecules must be >= 1` and exits with code 2. |
| `_run_cell` | new opt-in kwarg `n_molecules: int = 1`. Threads through `_solve_baseline` + `_solve_framework` (both updated to accept and forward the kwarg) and is captured in the `build_report`'s audit block. |
| `_solve_baseline` | new opt-in kwarg `n_molecules: int = 1`. Calls `adapter.solve_ode(bundle, condition, seed=int(seed), n_molecules=int(n_molecules))`. Falls back to `adapter.solve_ode(bundle, condition, seed=int(seed))` on `TypeError` for legacy adapters that do not accept the kwarg (interface-first backward-compat). |
| `_solve_framework` | new opt-in kwarg `n_molecules: int = 1`. Per-round `adapter.solve_ode(...)` calls receive the kwarg (same `TypeError` fallback). |
| `build_report` | new opt-in kwarg `n_molecules: int = 1`. |

### 2.3 Glue layer (`adaptive_reflow/adapters/flowmol3_glue.py`)

No changes — `FlowMol3Glue.compute_chemistry_metrics` already accepts `Sequence[Any]` (per Wave 49). Upstream `SampleAnalyzer.analyze` aggregates over the batch internally with bootstrapped 95% CIs.

---

## 3. Aggregation choice — why **mean** over molecules per cell

We aggregate over the batch with **mean** (not median) on each chemistry axis:

* `frac_valid_mols` and `frac_mols_stable_valence` are themselves sample-mean estimators of the per-mol Bernoulli indicators (the upstream `SampleAnalyzer.analyze` already aggregates this way).
* Median over molecules per cell would discard information for `n < 10` (the published Wave 73 n=1 spread of ±0.6 is the same kind of degeneracy the median would NOT fix for small n).
* Sample-mean over `n=10` mols shrinks the Wave 73 ±0.6 spread to roughly ±0.6 / sqrt(10) = ±0.19, the empirical target.

The glue's `composite_score` is applied once over the batched chemistry dict — the upstream's `SampleAnalyzer.analyze` does the per-molecule work and emits the already-aggregated `frac_*` / `energy_js_div` / `reos_cum_dev` values.

---

## 4. Test plan + results

### 4.1 `tests/test_adapters/test_flowmol3_v2_adapter.py` (3 new tests)

```
tests/test_adapters/test_flowmol3_v2_adapter.py::TestFlowMol3V2NMoleculesBatch
  ✓ test_v2_supports_n_molecules_kwarg          (n=4 → 4 mols)
  ✓ test_v2_n_molecules_aggregates_composite    (n=5 → 5 mols, mean-aggregation contract)
  ✓ test_v2_n_molecules_default_1_preserves_byte_stability  (D.4 contract)

34 passed (all v2 adapter tests, including the 3 new ones)
```

### 4.2 `tests/test_tools/test_run_real_ckpt_eval.py` (1 new test)

```
tests/test_tools/test_run_real_ckpt_eval.py::test_run_real_ckpt_eval_n_molecules_flag
  ✓ --n-molecules default 1
  ✓ --n-molecules 4 accepted
  ✓ --n-molecules 0 accepted at argparse (runtime guard in main())
  ✓ _solve_baseline received n_molecules=4
  ✓ _solve_framework received n_molecules=4
  ✓ sampled_molecules flowed into _compute_flowmol3_composite

70 passed (all v2 + tool tests)
```

### 4.3 D.4 regression vectors

```
tests/test_d4_regression_vectors.py + tests/test_adapters/test_regression_vectors.py
72 passed  ← D.4 byte-stability preserved (the legacy single-molecule path is untouched)
```

---

## 5. Honest caveats

1. **Upstream torch batch may drop atoms.** The published checkpoint runs CTMC and can drop a few atoms per molecule (the upstream's `fake_atom_p > 0` adds/drops). We handle heterogeneous `n_final` by padding to `max_n_atoms`. With `n_molecules=10` the per-cell `frac_*` reader receives a list of (typically) full molecules but a small minority might have `n_final < n`. The chemistry axes handle this gracefully (the SampleAnalyzer drops undersized mols).
2. **Synthetic NumPy backend with `n_molecules > 1` re-samples native state per molecule.** The deterministic NumPy prior with seed `seed + i * 1009` means each molecule gets a fresh prior draw, so the trajectories are genuinely independent. Without this, all 10 mols would be identical copies of molecule 0.
3. **Wallclock scales linearly with `n_molecules`.** At n=10 + NFE=200 + use_upstream=True, the upstream `FlowMol.sample(n_atoms=[n]*10)` is roughly 8-10× a single-mol sample (the GVP forward + CTMC + RDKit materialization is the bottleneck, not the batched `n_atoms`). The synthetic path is exactly 10× a single-mol solve.
4. **`build_argparser` accepts `--n-molecules 0`** but `main()` rejects it. The runtime guard in `main()` is the source of truth; argparse just preserves the raw integer.
5. **The eval pipeline's `_run_cell` still falls back to `sampled_molecules=None`** when `model not in ("flowmol3", "flowmol3_v2")` — the new flag is opt-in for non-FlowMol3 adapters too but only FlowMol3 actually consumes it.
6. **`marker='ok_partial_batch'`** is the new partial-success marker when at least one mol in the batch fails RDKit sanitization. The downstream `SampleAnalyzer.analyze` handles partial mols (per Wave 49 Agent D) so `frac_valid_mols` will reflect the partial population.

---

## 6. Files touched

| file | LOC |
|---|---|
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | +260 (n_molecules kwarg + `_solve_ode_upstream_batch` + `_solve_ode_linear_batch` + `export_sampled_molecules`/`export_trajectory` batch branches + new helpers) |
| `tools/run_real_ckpt_eval.py` | +30 (--n-molecules flag + n_molecules threading through `_run_cell` / `_solve_baseline` / `_solve_framework` / `build_report`) |
| `tests/test_adapters/test_flowmol3_v2_adapter.py` | +100 (3 new tests) |
| `tests/test_tools/test_run_real_ckpt_eval.py` | +135 (1 new test with stubbed inner chain) |
| `docs/audit/wave74-phase2-f1.md` | +200 (this file) |

---

## 7. Status

* **F1 interface-first contract:** ✓ — `n_molecules=1` byte-stable, `n_molecules>1` opt-in.
* **Glue layer:** ✓ — no changes; `compute_chemistry_metrics` already accepts `Sequence[Any]`.
* **Tests:** ✓ — 70 pass on v2 + tool; 72 pass on D.4 vectors.
* **Byte-stability:** ✓ — D.4 vectors unchanged.
* **Aggregation:** mean over molecules per cell (justified in §3).
* **NO push:** ✓ — local commit only.

Wave 74 Phase 2 Agent 2 (F1) closed at 2026-09-08. F2 (upstream seed plumbing), F3 (xtb install), F4 (energy_dist.npz vendor), and F5 (9-cell sweep with all 4 fixes active) remain for Wave 74 Phase 3 agents.