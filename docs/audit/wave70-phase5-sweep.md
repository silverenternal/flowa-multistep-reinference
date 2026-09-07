# Wave 70 Phase 5 — 9-cell FlowMol3 sweep on GPU + verdict

**Date:** 2026-09-08
**Wave:** 70, Agent 5
**Constraint:** Verification run. NO commit. NO push.

---

## 1. Goal

Run the 9-cell FlowMol3 sweep on GPU with `--force-mode real --metric-mode real
--composite-metric real`, after Wave 70 Phases 2–4 (upstream flowmol installed +
`export_sampled_molecules` added + caller wired `sampled_molecules` through
`_run_cell`). Verify that `chemistry_input` is populated and `composite > 0`.

**Result: FAIL.** All 9 cells still report `composite = 0.0`,
`composite_marker = "degraded_chemistry"`, and `chemistry_input_source =
"neutral_zero_stub_degraded"`. The root cause is GAP-1 from the Phase 1 audit —
**the `use_upstream=True` plumbing through `default_flowmol3adapter` was not
applied in Phases 2–4**, so the v2 adapter is constructed with `use_upstream=False`
and falls back to the partial-fidelity path. Without upstream weights, the
synthesized trajectories cannot be decoded to upstream `SampledMolecule`
objects, and `SampleAnalyzer.analyze` raises `AttributeError: 'Mol' object has no
attribute 'atom_types'`.

---

## 2. Step 1 — verify Phase 4 fix is in place

```text
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_tools/test_run_real_ckpt_eval.py -q --tb=line
33 passed, 3 warnings in 3.79s
```

Tool tests pass. The Phase 4 wire (`_run_cell` captures
`adapter.export_sampled_molecules(baseline_trace)` and threads
`sampled_molecules=sampled_molecules` into `_compute_flowmol3_composite`) is
present and tested. The capture block is at `tools/run_real_ckpt_eval.py:3615-3642`
and the composite call is at `tools/run_real_ckpt_eval.py:3749-3757`.

```text
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_d4_regression_vectors.py \
                                         tests/test_adapters/test_regression_vectors.py -q --tb=line
72 passed, 3 warnings in 41.30s
```

D.4 vectors byte-stable. **Phase 4 fix verified in place. No D.4 regression.**

---

## 3. Step 2 — run sweep on GPU

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=data/FlowMol3/repo \
  .venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
    --model flowmol3 \
    --force-mode real \
    --metric-mode real \
    --composite-metric real \
    --seeds 42,43,44 \
    --nfe-budgets 10,50,200 \
    --output verification_outputs/flowmol3_v3_q4_2026.json
```

GPU: NVIDIA RTX PRO 6000 Blackwell Workstation Edition (verified
`torch.cuda.is_available() == True`).
Venv: `.venvs/flowmol3_venv` with `flowmol` vendored at `data/FlowMol3/repo/`
injected via `PYTHONPATH`.
Output written: `verification_outputs/flowmol3_v3_q4_2026.json` (9 cells).

---

## 4. Step 3 — 9-cell result table

| seed | nfe | wallclock_baseline_s | wallclock_framework_s | composite | composite_marker | chemistry_input_source |
|------|-----|----------------------|-----------------------|-----------|------------------|------------------------|
| 42   | 10  | 0.5408               | 0.0029                | 0.0       | degraded_chemistry | neutral_zero_stub_degraded |
| 42   | 50  | 0.0046               | 0.0060                | 0.0       | degraded_chemistry | neutral_zero_stub_degraded |
| 42   | 200 | 0.0169               | 0.0190                | 0.0       | degraded_chemistry | neutral_zero_stub_degraded |
| 43   | 10  | 0.0010               | 0.0026                | 0.0       | degraded_chemistry | neutral_zero_stub_degraded |
| 43   | 50  | 0.0044               | 0.0058                | 0.0       | degraded_chemistry | neutral_zero_stub_degraded |
| 43   | 200 | 0.0165               | 0.0186                | 0.0       | degraded_chemistry | neutral_zero_stub_degraded |
| 44   | 10  | 0.0010               | 0.0025                | 0.0       | degraded_chemistry | neutral_zero_stub_degraded |
| 44   | 50  | 0.0044               | 0.0058                | 0.0       | degraded_chemistry | neutral_zero_stub_degraded |
| 44   | 200 | 0.0167               | 0.0188                | 0.0       | degraded_chemistry | neutral_zero_stub_degraded |

Aggregate metrics:

| metric | value |
|--------|-------|
| `wallclock_baseline_avg_s` | **0.0674** |
| `wallclock_framework_avg_s` | **0.0091** |
| `composite_avg` | **0.0** |
| `composite_min` | **0.0** |
| `composite_max` | **0.0** |
| `frac_valid_mols_avg` | **0.0** |
| `energy_js_div_avg` | **0.0** |
| `n_supported` | **0** |
| `n_tie` | **0** (all `verdict` = `None`) |
| `n_regression` | **0** |
| `n_blocked` | **0** (marker is `degraded_chemistry`, not `blocked`) |
| `chemistry_axis_populated` | **false** |

**Verdict: FAIL.** No cell reached `composite_marker = "computed"`. Every cell
falls into `degraded_chemistry` because the upstream `SampleAnalyzer.analyze`
raises `AttributeError: 'Mol' object has no attribute 'atom_types'`.

---

## 5. Step 4 — comparison vs Wave 69 sweep

| aspect | Wave 69 (flowmol3_v2_q4_2026) | Wave 70 Phase 5 (flowmol3_v3_q4_2026) | improved? |
|--------|--------------------------------|----------------------------------------|-----------|
| wallclock_baseline_avg_s | 0.5396 | 0.0674 | yes (-88%) but still << 5s |
| wallclock_framework_avg_s | 0.0028 | 0.0091 | no, slightly slower |
| composite_avg | 0.0 | 0.0 | no change |
| composite_min/max | 0.0 / 0.0 | 0.0 / 0.0 | no change |
| composite_marker | degraded_chemistry | degraded_chemistry | no change |
| chemistry_input_source | neutral_zero_stub_degraded | neutral_zero_stub_degraded | no change |
| baseline_marker | computed | computed | same |
| framework_marker | computed | computed | same |
| frac_valid_mols > 0 cells | 0/9 | 0/9 | no change |
| energy_js_div > 0 cells | 0/9 | 0/9 | no change |
| actual error | unknown | `AttributeError: 'Mol' object has no attribute 'atom_types'` | partial — root cause now visible |

**Net improvement vs Wave 69: NONE on the chemistry axes.** The Phase 4 wire is
capturing `sampled_molecules` correctly, but the molecules are not the
upstream `SampledMolecule` objects that `SampleAnalyzer.analyze` requires. The
wallclock is slightly faster (less overhead from the capture block on the empty
path), and the new error string identifies the exact root cause — but no
chemistry reading is computed.

---

## 6. Root cause — GAP-1 (Phase 1 audit §1.2 / §1.8) still open

Per Phase 1 audit §1.2 and §1.8, the FlowMol3 v2 adapter has a `use_upstream`
constructor flag. When `use_upstream=True`:
- the upstream `FlowMol.load_from_checkpoint(ckpt, ...)` path is taken
- real weights are loaded; `_solve_ode_upstream` runs the paper-correct sample
- `rdkit_mol_smiles` is cached on the entry
- `export_sampled_molecules` takes the SMILES shortcut via
  `flowmol3_metrics_upstream.sampled_mols_from_smiles(...)`, which returns
  upstream `SampledMolecule` objects

When `use_upstream=False` (the current factory default):
- the partial-fidelity fallback path is taken (lines 1754-1782 of
  `flowmol3_v2_adapter.py`)
- 444 GVP graph-conv tensors in the checkpoint are NOT applied
- trajectories are synthesized from random atom/bond labels
- `rdkit_mol_smiles` is NOT cached (no upstream sample)
- `export_sampled_molecules` falls through to the `(x, a, e)` reconstruction
  path, which returns plain `rdkit.Chem.Mol` objects (not upstream
  `SampledMolecule`)
- `compute_chemistry_metrics` → `compute_paper_metrics` → `SampleAnalyzer.analyze`
  raises `AttributeError: 'Mol' object has no attribute 'atom_types'`
- `chem_metrics = {}`, `composite_marker = "degraded_chemistry"`

The factory at `adaptive_reflow/adapters/flowmol3_v2_adapter.py:3922-3976`
currently does NOT thread `use_upstream=True`:

```python
return FlowMol3V2Adapter(
    backend=str(backend),
    num_steps=int(num_steps),
    weights_path=weights_path,
    device=str(device),
    ctmc_enabled=ctmc_enabled,
)  # <-- missing use_upstream=True when force_mode in {"real", "auto"}
```

The eval pipeline call at `tools/run_real_ckpt_eval.py:935-942` correctly
threads `force_mode="real"` and the v2 factory correctly maps
`force_mode="real"` → `backend="torch"`, but the `use_upstream=True` plumbing
from the Phase 1 audit Step 1 was never applied to the factory body.

---

## 7. What IS working

1. **Phase 4 wire (sampled_molecules capture)** — verified active:
   `_run_cell` calls `adapter.export_sampled_molecules(baseline_trace)` (per
   `composite_debug.chemistry_compute_error: AttributeError...` — proves the
   call ran and the molecules were passed to `compute_chemistry_metrics`).
2. **Phase 3 export_sampled_molecules** — verified returning molecules:
   `chem_metrics = {}` is reached AFTER `export_sampled_molecules` returns
   successfully; the failure happens in the `SampleAnalyzer.analyze` consumer,
   not in the export.
3. **Phase 2 upstream flowmol install** — verified importable from the
   `flowmol3_venv` (`is_upstream_available() == True`); the failure is in the
   *call chain* (which objects reach the SampleAnalyzer), not in the import
   surface.
4. **D.4 byte-stable** — 72/72 vectors pass after Phase 4 wire.

---

## 8. What is NOT working

1. **GAP-1 (`use_upstream=True` factory wiring)** — not applied.
2. **Real FlowMol3 ckpt forward** — never executed; the partial-fidelity path
   runs instead, producing synthesized trajectories.
3. **Chemistry axes** — `frac_valid_mols`, `frac_mols_stable_valence`,
   `energy_js_div`, `reos_cum_dev` all stay at the neutral-zero stub.
4. **Composite** — `composite_value = 0.0`, `composite_marker = "degraded_chemistry"`.
5. **Wallclock** — does NOT meet the > 5 s real-ckpt forward threshold
   (avg 0.07 s per cell — confirms partial-fidelity path).

---

## 9. Honest caveats (chemistry axes)

Per task constraint, listing the chemistry axes that would still return 0.0 even
after GAP-1 is applied:

| axis | populated by | expected after GAP-1 fix |
|------|--------------|---------------------------|
| `frac_valid_mols` | upstream `SampleAnalyzer.analyze` on `SampledMolecule` list | YES — should populate (real FlowMol3 typically 0.7–0.95 on GEOM-Drugs) |
| `avg_frag_frac` | same | YES |
| `avg_num_components` | same | YES |
| `frac_connected` | same | YES |
| `frac_atoms_stable` | same | YES |
| `frac_mols_stable_valence` | same | YES |
| `energy_js_div` | `SampleAnalyzer.analyze(energy_div=True)` | NO — requires `energy_dist.npz` in `processed_data_dir` (per Phase 2 §7 — file is not vendored). The Phase 2 fallback uses `run_energy_div=False` (default), so `energy_js_div` will stay 0.0 unless the user downloads the upstream reference distribution. |
| `reos_cum_dev` | `SampleAnalyzer.analyze(functional_validity=True)` | YES — `run_functional_validity=True` is already passed by the Phase 4 wire. |
| `neg_med_rmsd_after_xtb` (geometry axis) | xtb on `$PATH` | NO — xtb is not installed on the host. The geometry axis is correctly dropped and chemistry axes renormalized (per `tools/run_real_ckpt_eval.py:3235-3255`); `composite_debug.has_geometry = False`. |

---

## 10. Recommended next step (NOT executed — verification run only)

Apply Phase 1 audit Step 1: thread `use_upstream=True` through
`default_flowmol3adapter` when `force_mode in {"real", "auto"}`:

```python
# adaptive_reflow/adapters/flowmol3_v2_adapter.py:3975
return FlowMol3V2Adapter(
    backend=str(backend),
    num_steps=int(num_steps),
    weights_path=weights_path,
    device=str(device),
    ctmc_enabled=ctmc_enabled,
    use_upstream=(force_mode in {"real", "auto"}),  # NEW: Wave 70 Phase 6
)
```

Expected outcome: real `FlowMol.load_from_checkpoint(...)` runs → upstream
sample → `rdkit_mol_smiles` cached → `export_sampled_molecules` takes the
SMILES shortcut → upstream `SampledMolecule` list → `SampleAnalyzer.analyze`
returns `frac_valid_mols > 0` and the composite reads positive.

This fix is **NOT applied in Phase 5** because:
- The task constraint says "NO commit (verification run)"
- The Phase 1 audit documented GAP-1 as a fix that crosses the
  factory/eval-pipeline boundary; Phases 2–4 explicitly scoped around it (Phase
  2: upstream install; Phase 3: export method; Phase 4: caller wire) without
  touching the factory.
- Applying the fix belongs in a dedicated Phase 6 with its own audit + D.4
  regression check.

---

## 11. Summary JSON

```json
{
  "wallclock_baseline_avg_s": 0.0674,
  "wallclock_framework_avg_s": 0.0091,
  "composite_avg": 0.0,
  "composite_min": 0.0,
  "composite_max": 0.0,
  "frac_valid_mols_avg": 0.0,
  "energy_js_div_avg": 0.0,
  "n_supported": 0,
  "n_tie": 0,
  "n_regression": 0,
  "n_blocked": 0,
  "n_degraded_chemistry": 9,
  "chemistry_axis_populated": false,
  "verdict_overall": "FAIL — GAP-1 (factory use_upstream=True threading) blocks the Phase 4 wire; all 9 cells fall into degraded_chemistry",
  "improvement_vs_wave69_sweep": "none — same composite=0.0 / marker=degraded_chemistry / source=neutral_zero_stub_degraded / 0 of 9 chemistry axes populated",
  "files_written": [
    "verification_outputs/flowmol3_v3_q4_2026.json",
    "docs/audit/wave70-phase5-sweep.md"
  ],
  "root_cause": "Adaptive_reflow/adapters/flowmol3_v2_adapter.py:3922-3976 default_flowmol3adapter factory does not thread use_upstream=True when force_mode in {real, auto}. The v2 adapter is constructed with use_upstream=False (default), so the partial-fidelity path runs (no real FlowMol3 ckpt forward), the synthesized trajectory decodes to plain rdkit.Chem.Mol objects (not upstream SampledMolecule), and SampleAnalyzer.analyze raises AttributeError: 'Mol' object has no attribute 'atom_types'.",
  "next_phase": "Wave 70 Phase 6 — apply Phase 1 audit Step 1 (factory use_upstream=True threading) + re-run 9-cell sweep + verify composite > 0 + verify chemistry axes populated. NOT done in Phase 5 per verification-run constraint.",
  "honest_caveats": [
    "energy_js_div will stay 0.0 even after GAP-1 is applied (energy_dist.npz is not vendored).",
    "geometry axis (neg_med_rmsd_after_xtb) will stay None (xtb is not installed on the host).",
    "D.4 vectors remain byte-stable (72/72 pass).",
    "Phase 4 wire (sampled_molecules capture) is verified active — the failure is downstream in SampleAnalyzer, not in the capture.",
    "Phase 3 export_sampled_molecules is verified returning molecules — the failure is in the consumer, not in the export.",
    "Phase 2 upstream flowmol install is verified importable — is_upstream_available() returns True from flowmol3_venv."
  ]
}
```

---

**Phase 5 verification closed at:** 2026-09-08 (Wave 70 Agent 5)
**Status:** VERIFICATION FAIL. GAP-1 (factory `use_upstream=True` threading)
identified as the missing fix. Phase 6 plan documented in §10. NO commit.
NO push.
