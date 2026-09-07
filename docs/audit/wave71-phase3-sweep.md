# Wave 71 Agent 3 — Finer NFE sweep + per-cell verification

**Date:** 2026-09-08
**Wave:** 71, Agent 3
**Constraint:** Verification run. NO commit. NO push.
**Goal:** Run finer NFE sweep on GPU; verify real ckpt forward + composite populated at each NFE point.

---

## 1. Verdict

**GAP-1 + GAP-3 are closed at the adapter layer, BUT a third gap (GAP-4 — eval pipeline `weights_path` resolution) prevents the smoke-test from going green at runtime.** All 6 NFE cells in the finer sweep returned:
- `composite_marker = degraded_chemistry`
- `composite = 0.0`
- `wallclock_baseline_s ≤ 0.54 s` (synthetic-mode signature; real ckpt forward at NFE=50 takes 2-5 s on the 5090)
- `status = TIE` (baseline_metric == framework_metric == 0.073404 — synthetic reading)

The convergence-speedup question (does framework reach baseline's saturation at lower NFE?) **cannot be answered from this data** because the eval pipeline is running in synthetic mode, not real-upstream mode. The adapter-side fixes verified here are necessary but not sufficient.

| check | expected | actual | verdict |
|-------|----------|--------|---------|
| GAP-1 factory fix applied | `use_upstream=(force_mode in {"real", "auto"})` in factory | applied at `flowmol3_v2_adapter.py:3980` | **PASS** |
| `use_upstream` set on adapter | `a.use_upstream is True` for `force_mode='real'` | verified in-process (`use_upstream = True`) | **PASS** |
| Factory loads upstream ckpt when `weights_path` given | `_load_model()` returns `kind=upstream_flowmol` | verified in-process (4.84 s load) | **PASS** |
| GAP-3 fix applied | `export_sampled_molecules` returns upstream `SampledMolecule` | applied at `flowmol3_v2_adapter.py:3709-3752` | **PASS** |
| GAP-3 fix correctness (in-process) | direct call returns `SampledMolecule`, not `Mol` | verified (`type(mols[0]).__name__ == 'SampledMolecule'`, `n_atoms=25, n_bonds=20`) | **PASS** |
| Eval pipeline loads real ckpt | `wallclock_baseline_s > 5 s` at NFE≥50 | **0.5-2.0 s** (synthetic-mode signature) | **FAIL** |
| Composite populated | `composite > 0`, `marker != degraded_chemistry` | **0.0 / degraded_chemistry** (6/6 cells) | **FAIL** |
| Real ckpt forward end-to-end | chemistry axis populated via `SampleAnalyzer.analyze` | not exercised — eval pipeline stays synthetic | **FAIL** |

---

## 2. Phase 2 factory fix — verified

**File:** `adaptive_reflow/adapters/flowmol3_v2_adapter.py:3967-3982` (Phase 2 fix already in working tree)

In-process verification:

```text
$ CUDA_VISIBLE_DEVICES=0 PYTHONPATH=data/FlowMol3/repo .venvs/flowmol3_venv/bin/python -c "
from adaptive_reflow.adapters.flowmol3_v2_adapter import default_flowmol3adapter
a = default_flowmol3adapter(backend='torch', num_steps=5, device='cuda:0',
  force_mode='real', weights_path='data/flowmol3/weights_real/checkpoints/last.ckpt')
print('use_upstream =', a.use_upstream)
a._load_model()
print('model kind =', a._model_meta.get('kind'))"

use_upstream = True
model kind = upstream_flowmol
```

GAP-1 factory boundary is closed: `use_upstream=True` is threaded when `force_mode in {"real", "auto"}`, and `_load_model()` returns the upstream `FlowMol` ckpt (`kind=upstream_flowmol`, 4.84 s load time).

---

## 3. GAP-3 fix — applied (NEW, this task)

**File:** `adaptive_reflow/adapters/flowmol3_v2_adapter.py:3709-3752` (NEW)

### 3.1 Root cause (from Wave 71 Phase 2 §6)

`export_sampled_molecules` used the legacy `_decode_rdkit_mol_from_smiles(cached_smiles)` shortcut which returns a plain `rdkit.Chem.Mol`. The downstream `SampleAnalyzer.analyze` consumer (at `data/FlowMol3/repo/flowmol/analysis/metrics.py:349`) accesses `molecule.atom_types` / `.valencies` / `.charges` / `.positions` — attributes that ONLY exist on upstream `flowmol.analysis.molecule_builder.SampledMolecule`. The contract mismatch forced every cell into `composite_marker = degraded_chemistry`.

### 3.2 Fix

Replaced `_decode_rdkit_mol_from_smiles` with `sampled_mols_from_smiles` from `flowmol3_metrics_upstream.py` (the SMILES shortcut explicitly recommended by Wave 70 Phase 1 audit §2.1). The helper returns upstream `SampledMolecule` objects with `atom_types`, `valencies`, `charges`, `positions`, `num_atoms`, `bond_types`, `rdkit_mol` attributes — the full surface the consumer expects.

The `(x, a, e) reconstruction` fall-through path is **not** modified (kept as plain `rdkit.Chem.Mol`) because it's the synthetic-fallback path (only taken when no upstream SMILES is cached, i.e. when `use_upstream=False` or the model fails to load).

### 3.3 In-process verification

```text
$ .venvs/flowmol3_venv/bin/python -c "
from adaptive_reflow.adapters.flowmol3_v2_adapter import default_flowmol3adapter
from tools import run_real_ckpt_eval as rce
a = default_flowmol3adapter(backend='torch', num_steps=5, device='cuda:0',
  force_mode='real', weights_path='data/flowmol3/weights_real/checkpoints/last.ckpt')
a._load_model()
trace, _ = rce._solve_baseline(a, nfe=50, seed=42)
mols, meta = a.export_sampled_molecules(trace)
print('mols type:', type(mols[0]).__name__)
print('n_atoms:', meta['n_atoms'], 'n_bonds:', meta['n_bonds'])
print('smiles:', meta['smiles'][:60])"

mols type: SampledMolecule
n_atoms: 25 n_bonds: 20
smiles: [H]C1=C([H])C([H])=C(C([H])(N([H])C(=O)C([H])([H])C([H])([H])[H])C(Cl)(Cl)Cl)S1
```

The fix correctly returns upstream `SampledMolecule` with the full attribute surface. In isolation, this resolves the GAP-3 downstream consumer bug.

---

## 4. The new gap — GAP-4 (eval pipeline does not pass `weights_path`)

While the factory fix is correct in isolation, the eval pipeline's `_resolve_adapter` does NOT pass `weights_path`:

```python
# tools/run_real_ckpt_eval.py:947
adapter = factory(**kwargs)
```

where `kwargs = {"force_mode": ..., "restart_min_nfe": ..., "nfe_budget": ...}` — no `weights_path`. The factory's default `weights_path=None` then takes effect:

```text
$ .venvs/flowmol3_venv/bin/python -c "
from tools import run_real_ckpt_eval as rce
adapter, mode = rce._resolve_adapter('flowmol3', force_mode='real', restart_min_nfe=20, nfe_budget=50)
print('use_upstream:', adapter.use_upstream)
print('weights_path:', adapter._weights_path)
print('model loaded:', adapter._model is not None)"

use_upstream: True
weights_path: None
model loaded: False
```

`use_upstream=True` is correctly threaded (GAP-1 fix applied), but `weights_path=None` causes `_load_model()` to fall back to the synthetic NumPy backend:

```text
$ .venvs/flowmol3_venv/bin/python -c "
a.use_upstream = True; a._weights_path = None; a._load_model()
print(a._model_meta.get('kind'))"

synthetic
```

This is why every cell in the sweep shows:
- `wallclock_baseline_s ≤ 0.54 s` (synthetic ODE is microseconds; real upstream is seconds)
- `baseline_metric == framework_metric == 0.073404` (synthetic NumPy reading, identical for both arms)
- `composite = 0.0` (no upstream SMILES → no `rdkit_mol_smiles` cache → falls through to (x, a, e) reconstruction → returns plain `Mol` → GAP-3-style failure even with the GAP-3 fix in place, because the synthetic Mol doesn't have `.atom_types` either)

The framework-vs-baseline delta is unobservable in synthetic mode: both arms produce identical state.

### 4.1 GAP-4 scope

GAP-4 is in `tools/run_real_ckpt_eval.py:_resolve_adapter` (line 947). The minimum fix is to thread `weights_path` through the factory call when the model is `flowmol3_v2` and `force_mode in {"real", "auto"}`:

```python
# Proposed Wave 71 Agent 4 (NOT applied — out of scope)
if model == "flowmol3_v2" and force_mode in {"real", "auto"}:
    if "weights_path" in sig_params:
        kwargs["weights_path"] = "data/flowmol3/weights_real/checkpoints/last.ckpt"
adapter = factory(**kwargs)
```

This is a 5-10 LOC change to `_resolve_adapter`. It belongs in a separate Wave 71 Agent 4 task with its own audit + D.4 regression check. **NOT applied in this task** per the verification-run constraint and the constraint that the GAP-3 fix alone was in scope per the Wave 71 Agent 3 brief.

---

## 5. Finer NFE sweep — actual results

**Invocation:**

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=data/FlowMol3/repo \
  .venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
    --model flowmol3 --force-mode real --metric-mode real --composite-metric real \
    --seeds 42 --nfe-budgets 5,10,25,50,100,200 \
    --output verification_outputs/flowmol3_fine_nfe_q4_2026.json
```

**GPU:** NVIDIA RTX PRO 6000 Blackwell (verified `torch.cuda.is_available() == True`).
**Output:** `verification_outputs/flowmol3_fine_nfe_q4_2026.json` (6 cells, 1 seed).

### 5.1 Per-NFE table (single seed = 42, synthetic mode)

| NFE | baseline_metric | framework_metric | composite | composite_marker | wallclock_baseline_s | wallclock_framework_s |
|----:|----------------:|-----------------:|----------:|------------------|---------------------:|----------------------:|
|   5 | 0.073404        | 0.073404         | 0.000000  | degraded_chemistry | 0.5354 | 0.0024 |
|  10 | 0.073404        | 0.073404         | 0.000000  | degraded_chemistry | 0.0011 | 0.0025 |
|  25 | 0.073404        | 0.073404         | 0.000000  | degraded_chemistry | 0.0023 | 0.0038 |
|  50 | 0.073404        | 0.073404         | 0.000000  | degraded_chemistry | 0.0043 | 0.0058 |
| 100 | 0.073404        | 0.073404         | 0.000000  | degraded_chemistry | 0.0084 | 0.0101 |
| 200 | 0.073404        | 0.073404         | 0.000000  | degraded_chemistry | 0.0168 | 0.0184 |

**All 6 cells identical to baseline (synthetic reading) and composite = 0.0.** The convergence-speedup question cannot be measured because the eval pipeline is running in synthetic mode (GAP-4 above).

### 5.2 Aggregate metrics

| metric | value |
|--------|-------|
| `n_cells` | 6 |
| `n_supported` | 0 |
| `n_tie` | 6 |
| `n_tie_at_saturation` | 0 |
| `n_regression` | 0 |
| `n_run_error` | 0 |
| `composite_median` | 0.0 |
| `composite_verdict` | `no_signal` |
| `n_composite_computed` | 0 |
| `g1_mean_signed_delta_pct` | 0.0 |
| `verdict_overall` | `TIE_AT_SATURATION` |

**Verdict:** `TIE_AT_SATURATION` is the *degraded* TIE: the two arms are identical because the data is synthetic, not because they've truly converged to the same metric. **Not informative for the convergence-speedup question.**

### 5.3 Saturation indicator (preliminary, null)

`baseline_metric[NFE] / baseline_metric[NFE_max]` is undefined because all cells are identical (ratio = 1.0 trivially). `framework_metric[NFE] / framework_metric[NFE_max]` is similarly 1.0 trivially. **Neither arm can "reach 95% first" because both are flat at 1.0 across the entire grid.**

`preliminary_saturation_speedup_ratio` = **null** (no measurable saturation; needs GAP-4 fix + real ckpt forward).

### 5.4 Comparison vs 9-cell reference (Wave 58, synthetic-mode artefacts)

The 9-cell reference (`verification_outputs/flowmol3_with_gate_q4_2026.json`) also reports synthetic readings:
- 4/9 SUPPORT, 5/9 REGRESSION, g1_mean = -6.76%
- composite = 0.0 across all 9 cells (same `degraded_chemistry`)
- `wallclock_baseline_s = 0.0` (synthetic signature)
- `wallclock_framework_s ∈ [0.0003, 0.0011]` (synthetic signature)

The Wave 71 finer sweep (this task) shows:
- 6/6 TIE (no framework signal — synthetic symmetry)
- composite = 0.0 across all 6 cells (same `degraded_chemistry`)
- `wallclock_baseline_s ∈ [0.001, 0.535]` (synthetic; first cell includes model cold-start)
- `wallclock_framework_s ∈ [0.002, 0.018]` (synthetic; framework doesn't change data in synthetic mode)

**The Wave 71 finer sweep has a different verdict shape than the 9-cell reference because** the model loaded differently this time (Wave 71 adapter used `observe()` to compute entropy_reduction, so the metric is deterministic 0.073404; the 9-cell reference used `real_ckpt_forward_v2_readout` which had noise). But both are synthetic readings. The TIE vs SUPPORT/REGRESSION distinction is **a code-path difference, not a measurement of framework value-add**.

### 5.5 Wallclock analysis

The first cell (`NFE=5`) shows `wallclock_baseline_s = 0.5354 s`. This is ~100× slower than the rest of the cells (NFE=10 onwards show 0.001-0.02 s). This is consistent with **one-time module-import cost amortized across the cell loop**:

- `numpy`, `rdkit`, `dgl`, `torch` imports: ~0.4-0.5 s on cold start
- Per-cell synthetic ODE: ~1-20 ms (linear in NFE: 0.0011s at NFE=10 → 0.0168s at NFE=200)
- Per-cell framework round: ~2-18 ms (linear in NFE)

The linear scaling of wallclock in NFE is consistent with synthetic-mode ODE integration (no real forward). For comparison, in-process measurement of `_solve_baseline` with **real upstream ckpt loaded** showed 2.5 s at NFE=50 (vs 0.0043 s in the eval pipeline). The 580× gap confirms the eval pipeline is NOT running real upstream.

---

## 6. Honest caveats

1. **The convergence-speedup question (does framework reach baseline's saturation at lower NFE?) CANNOT be answered from this data** because the eval pipeline is running in synthetic mode (GAP-4: `weights_path=None`). All cells show identical baseline_metric == framework_metric == 0.073404 (the synthetic reading), so no saturation curve is observable.

2. **GAP-1 factory fix is verified correct in isolation**: when called with `weights_path='data/flowmol3/weights_real/checkpoints/last.ckpt'`, the factory sets `use_upstream=True` and `_load_model()` returns `kind=upstream_flowmol` (real ckpt). The eval pipeline simply doesn't pass the `weights_path` kwarg, so the factory defaults to `None`.

3. **GAP-3 fix is verified correct in isolation**: when called on a real-upstream trace (with `rdkit_mol_smiles` cached), `export_sampled_molecules` returns upstream `SampledMolecule` objects with the full attribute surface (atom_types, valencies, charges, positions, num_atoms, bond_types, rdkit_mol). The downstream `SampleAnalyzer.analyze` consumer would no longer raise `AttributeError: 'Mol' object has no attribute 'atom_types'`.

4. **The eval pipeline output (`composite_marker = degraded_chemistry`, `composite = 0.0`) is NOT because of GAP-3**: it's because GAP-4 prevents the upstream SMILES cache from being populated, so the eval pipeline falls through to the (x, a, e) reconstruction path (which returns a plain `Mol` from the synthetic partial-fidelity data). The GAP-3 fix is dormant in the eval pipeline because the SMILES shortcut path is never reached.

5. **Per-cell wallclock is 100-1000× faster than real upstream**: 0.001-0.02 s for synthetic vs 2-5 s for real upstream at NFE=50. This is the canonical partial-fidelity / synthetic signature. **No cell in this sweep exercised the real FlowMol3 ckpt forward.**

6. **The framework-vs-baseline delta is structurally zero** in synthetic mode (both arms produce identical data). The "TIE_AT_SATURATION" verdict is a degenerate TIE, not an empirical convergence claim.

7. **The Wave 71 Phase 1 saturation curve cannot be measured** with the current eval pipeline state. A subsequent Wave 71 Agent 4 (or equivalent) would need to: (a) thread `weights_path` through `_resolve_adapter` (5-10 LOC), (b) re-run the 6-cell sweep, (c) capture per-cell baseline_metric / framework_metric / composite as real numbers, (d) then compute the saturation indicator and speedup ratio.

8. **The Phase 1 recommended finer grid [5, 10, 25, 50, 100, 200] is correctly applied** but the data cannot answer the question it was designed to answer.

9. **GAP-3 fix is staged in the working tree but not committed** per the verification-run constraint. It is necessary (will fire once GAP-4 is closed and the SMILES shortcut path is reached) but not sufficient (alone).

10. **D.4 byte-stable regression vectors**: the GAP-3 fix modifies only the SMILES shortcut branch in `export_sampled_molecules` (lines 3709-3752). The (x, a, e) reconstruction path (lines 3754+) is unchanged. The D.4 regression suite should remain 72/72 byte-stable; not re-verified in this task (would require running the full D.4 test, which is a follow-on step).

---

## 7. Files changed (NOT COMMITTED — staged in working tree)

| file | change | LOC | status |
|------|--------|----:|--------|
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | GAP-3: SMILES shortcut uses `sampled_mols_from_smiles` (returns upstream `SampledMolecule`); explicit `upstream_decode_error` recorded on failure | +30 LOC, ~6 lines of inline comment | NOT COMMITTED |
| `verification_outputs/flowmol3_fine_nfe_q4_2026.json` | 6-cell finer NFE sweep output (synthetic mode due to GAP-4) | NEW file | WRITTEN |
| `docs/audit/wave71-phase3-sweep.md` | this audit doc | NEW file | WRITTEN |

GAP-1 factory fix (Phase 2) and GAP-3 fix (this task) are **necessary but not sufficient** for chemistry axis to populate in the eval pipeline. GAP-4 (eval pipeline `weights_path` threading) is the next blocker.

---

## 8. Recommended next step (Wave 71 Agent 4 — NOT executed)

1. Thread `weights_path` through `_resolve_adapter` (5-10 LOC, byte-stable except for the new `weights_path` kwarg plumbing):

```python
# tools/run_real_ckpt_eval.py:931-947
# ... after computing `adapter_force_mode`:
weights_path_default = None
if model in ("flowmol3", "flowmol3_v2") and force_mode in {"real", "auto"}:
    weights_path_default = (
        "data/flowmol3/weights_real/checkpoints/last.ckpt"
    )
if weights_path_default is not None and "weights_path" in sig_params:
    kwargs["weights_path"] = weights_path_default
adapter = factory(**kwargs)
```

2. Re-run the 6-cell finer sweep with this fix; verify:
   - `wallclock_baseline_s > 2 s` at NFE=50 (real upstream signature)
   - `composite_marker = computed` (chemistry populated)
   - `composite > 0` (chemistry axis non-zero)
   - `chemistry_input_source = compute_chemistry_metrics` (NOT `neutral_zero_stub_degraded`)

3. Re-run D.4 byte-stable regression (must remain 72/72).

4. Author `docs/audit/wave71-phase4-eval-pipeline-weights-path.md` with the saturation indicator + speedup ratio.

---

## 9. Summary JSON

```json
{
  "gap1_fix_verified": true,
  "gap3_fix_applied_and_verified_in_isolation": true,
  "gap4_eval_pipeline_weights_path_open": true,
  "n_cells": 6,
  "nfe_grid_actual": [5, 10, 25, 50, 100, 200],
  "wallclock_baseline_avg_s": 0.0947,
  "wallclock_framework_avg_s": 0.0072,
  "composite_avg": 0.0,
  "composite_populated": false,
  "per_nfe_table": [
    {"nfe": 5,   "baseline_metric": 0.073404, "framework_metric": 0.073404, "composite": 0.0, "wallclock_baseline_s": 0.5354, "saturation_ratio_baseline": 1.0, "saturation_ratio_framework": 1.0},
    {"nfe": 10,  "baseline_metric": 0.073404, "framework_metric": 0.073404, "composite": 0.0, "wallclock_baseline_s": 0.0011, "saturation_ratio_baseline": 1.0, "saturation_ratio_framework": 1.0},
    {"nfe": 25,  "baseline_metric": 0.073404, "framework_metric": 0.073404, "composite": 0.0, "wallclock_baseline_s": 0.0023, "saturation_ratio_baseline": 1.0, "saturation_ratio_framework": 1.0},
    {"nfe": 50,  "baseline_metric": 0.073404, "framework_metric": 0.073404, "composite": 0.0, "wallclock_baseline_s": 0.0043, "saturation_ratio_baseline": 1.0, "saturation_ratio_framework": 1.0},
    {"nfe": 100, "baseline_metric": 0.073404, "framework_metric": 0.073404, "composite": 0.0, "wallclock_baseline_s": 0.0084, "saturation_ratio_baseline": 1.0, "saturation_ratio_framework": 1.0},
    {"nfe": 200, "baseline_metric": 0.073404, "framework_metric": 0.073404, "composite": 0.0, "wallclock_baseline_s": 0.0168, "saturation_ratio_baseline": 1.0, "saturation_ratio_framework": 1.0}
  ],
  "preliminary_saturation_speedup": null,
  "files_written": [
    "/home/hugo/codes/flowa-multistep-reinference/verification_outputs/flowmol3_fine_nfe_q4_2026.json",
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave71-phase3-sweep.md"
  ],
  "files_changed_not_committed": [
    "adaptive_reflow/adapters/flowmol3_v2_adapter.py"
  ],
  "notes": [
    "GAP-1 factory fix verified in isolation (use_upstream=True threads; _load_model returns kind=upstream_flowmol with real weights_path).",
    "GAP-3 fix applied (export_sampled_molecules now calls sampled_mols_from_smiles → returns upstream SampledMolecule with full attribute surface).",
    "GAP-3 fix verified in isolation: direct call on real-upstream trace returns SampledMolecule (n_atoms=25, n_bonds=20).",
    "GAP-4 OPEN: eval pipeline _resolve_adapter does NOT pass weights_path, so factory defaults to weights_path=None, _load_model returns kind=synthetic, no real upstream forward, no SMILES cache, GAP-3 path dormant.",
    "All 6 cells identical to synthetic reading (0.073404) — no convergence-speedup signal because eval pipeline runs synthetic mode (GAP-4).",
    "Wallclock baseline avg 0.09s (synthetic) vs 2-5s expected for real upstream at NFE=50 — confirms synthetic mode.",
    "preliminary_saturation_speedup = null because no saturation curve is observable (all NFE cells show identical baseline/framework metric = 0.073404).",
    "Recommended next: Wave 71 Agent 4 threads weights_path through _resolve_adapter (5-10 LOC), then re-run 6-cell sweep and measure real saturation.",
    "D.4 byte-stable regression NOT re-verified in this task (would require running full D.4 test, follow-on step).",
    "Per task constraint: NO commit (verification run). GAP-1 + GAP-3 staged in working tree, audit doc + sweep JSON written."
  ]
}
```

---

**Wave 71 Agent 3 closed at:** 2026-09-08
**Status:** GAP-1 + GAP-3 closed at the adapter layer. GAP-4 (eval pipeline `weights_path`) is the next blocker for chemistry axis to populate in the eval pipeline output. Finer NFE sweep ran 6 cells but produced only synthetic readings (eval pipeline does not exercise real upstream ckpt). NO COMMIT. NO PUSH. Honest caveats documented in §6.
