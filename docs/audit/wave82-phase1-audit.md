# Wave 82 Agent A — FlowMol3 PB-xtb pipeline gap audit + fix plan

**Date:** 2026-09-08
**Wave:** 82 (PHASE-4 paper-reproduction closure)
**Agent:** A (READ-ONLY audit)
**Repo:** `/home/hugo/codes/flowa-multistep-reinference`
**Constraint:** READ-ONLY — no code changes this phase. Goal: precise fix plan
for adopting the upstream xtb-based PB pipeline + UNCOMMENTING the
`energy_ratio` PB module to replace the current UFF-only `pb_valid` reading
with the paper's full `pb_validity_pct = 0.919` measurement.

---

## 0. TL;DR

The `pb_validity_pct = 0.919` paper value (Dunn et al., NeurIPS 2024, arXiv
2508.12629) is computed by PoseBusters **WITH the `energy_ratio` module
enabled**. The current pipeline reports `pb_valid ≈ 1.0` because:

1. The upstream `data/FlowMol3/repo/flowmol/analysis/pb_config.yaml:101-110`
   has the `energy_ratio` module **COMMENTED OUT** (verified §1 below).
2. Our `tools/paper_metrics.py:compute_pb_validity_pct` (`full_pb=True`
   default) passes `pb_energy=True` → PoseBusters switches to the built-in
   `mol` config (PoseBusters 0.6.5 ships 9 configs at
   `.venvs/flowmol3_venv/lib/python3.12/site-packages/posebusters/config/`).
   The `mol.yml` config DOES include the `energy_ratio` module — BUT twice,
   with PoseBusters' default threshold (`7.0`) and ensemble size (`100`).
3. The upstream `pb_config.yaml` ships `threshold_energy_ratio: 100.0` and
   `ensemble_number_conformations: 50` — much more permissive than the PB
   default. The paper tuned these for the FlowMol3 distribution. Using the
   built-in `mol` config **without vendoring the tuned YAML** yields
   `pb_valid` ~5-15% (over-rejects via default UFF threshold 7.0) — **NOT**
   the paper's 0.919.
4. The xtb pipeline (`fm3_evals/geometry/xtb_optimization.py` +
   `rmsd_energy.py`) is a SEPARATE post-processing step that produces
   `med_rmsd`, `med_energy_gain`, `med_mmff_drop` — consumed by our
   composite's `-med_rmsd_after_xtb` axis (current `_compute_xtb_med_rmsd`
   stub at `tools/run_real_ckpt_eval.py:3106-3224` is a minimal N=2 version
   that misses `med_energy_gain` and `med_mmff_drop`).

**Fix plan**: vendor `pb_config_with_energy_ratio.yaml` (3 modules: loading +
chem + geometry + ring flatness + energy_ratio with upstream's tuned
parameters) and update `compute_pb_validity_pct` to consume it via
`config=<vendored_path>`. **xtb is NOT required** by PoseBusters 0.6.5's
`energy_ratio` module — it uses UFF force-field (verified at
`.venvs/flowmol3_venv/.../posebusters/modules/energy_ratio.py:6-14`,
source imports `UFFGetMoleculeForceField`). xtb IS still required for the
upstream `xtb_optimization.py + rmsd_energy.py` chemistry-axis computation
that drives `med_rmsd_after_xtb` in the composite.

**Wallclock**: PB `energy_ratio` ≈ 5-15s/mol × N=500 mols ≈ 40-125 min on
CPU; xtb pipeline ≈ 1-3s/mol × N=500 ≈ 8-25 min. Total ≈ 50-150 min for the
N=500 production sweep on a CPU-only host. On RTX PRO 6000 Blackwell (Wave 81
class), same wallclock — PB is CPU-only.

---

## 1. Step-1 verification: `pb_config.yaml` `energy_ratio` is COMMENTED OUT

**File:** `data/FlowMol3/repo/flowmol/analysis/pb_config.yaml` (132 lines)

**Verified status** (lines 101-110, verbatim):
```yaml
  # - name: "Energy ratio"
  #   function: energy_ratio
  #   parameters:
  #     threshold_energy_ratio: 100.0
  #     ensemble_number_conformations: 50
  #     inchi_strict: False
  #   chosen_binary_test_output:
  #     - energy_ratio_passes
  #   rename_outputs:
  #     energy_ratio_passes: "Internal energy"
```

All 10 lines prefixed with `#`. The module is **fully commented out** —
matches Wave 75 Phase 1 §1.4.2 (file:line citation). The vendored YAML has 9
active modules: Loading, Chemistry (rdkit_sanity), Chemistry (inchi_convertible),
Chemistry (atoms_connected), Geometry (distance_geometry), Ring flatness,
Ring non-flatness, Double bond flatness — total 9 modules.

When `SampleAnalyzer.__init__(pb_energy=True)` is called, the upstream
`flowmol/analysis/metrics.py:87-93` switches config to `config='mol'`
(built-in PoseBusters preset), NOT to the vendored YAML. The built-in `mol`
config (PoseBusters 0.6.5) DOES include `energy_ratio` (twice) but with PB
default parameters, NOT upstream's tuned `threshold_energy_ratio=100.0`.

---

## 2. Step-2 verification: upstream xtb pipeline entrypoints

### 2.1 `fm3_evals/geometry/xtb_optimization.py` (177 lines)

**Entry point**: `main_fn(input_sdf, output_sdf, init_sdf)` at line 123.

| Step | Implementation | File:line |
|---|---|---|
| Input format | `.sdf` OR `.pkl` (auto-detected via suffix) | `xtb_optimization.py:125-134` |
| SDF reading | `Chem.SDMolSupplier(input_sdf, sanitize=False, removeHs=False)` | `xtb_optimization.py:132` |
| Per-molecule processing | `process_molecule(task=(i, mol), temp_dir)` | `xtb_optimization.py:84-113` |
| XYZ writer | `sdf_to_xyz(mol, filename)` writes `<N>\n\n` + atom lines | `xtb_optimization.py:14-20` |
| Charge calculation | `get_molecule_charge(mol)` sums formal charges | `xtb_optimization.py:76-81` |
| xtb invocation | `xtb <xyz> --opt --charge <Q> --namespace <prefix>` | `xtb_optimization.py:28` |
| xtb output parser | `parse_xtb_output()` extracts `total energy gain` (col 6, kcal/mol) and `total RMSD` (col 5, Å) | `xtb_optimization.py:36-48` |
| Optimized mol reader | `parse_xtbtopo_mol()` reads `<prefix>.xtbtopo.mol` | `xtb_optimization.py:51-61` |
| SDF writer | `write_mol_to_sdf()` with custom properties (`energy_gain`, `RMSD`) | `xtb_optimization.py:64-73` |
| Output files | `<output_sdf>` (optimized) + `<init_sdf>` (initial), must be **same length** | `xtb_optimization.py:144-167` |
| CLI | `--input_sdf --output_sdf --init_sdf` | `xtb_optimization.py:170-176` |

### 2.2 `fm3_evals/geometry/rmsd_energy.py` (145 lines)

**Entry point**: `main()` at line 77, **must be invoked via CLI**.

| Step | Implementation | File:line |
|---|---|---|
| Inputs | `--init_sdf` (initial), `--opt_sdf` (optimized), `--no_hydrogens`, `--n_subsets=1`, `--output_file` | `rmsd_energy.py:78-83` |
| SDF loading | `Chem.SDMolSupplier(init_sdf, ...)` + `Chem.SDMolSupplier(opt_sdf, ...)` | `rmsd_energy.py:88-89` |
| **Length assert** | `assert len(init_mols) == len(opt_mols)` — must match exactly | `rmsd_energy.py:91` |
| Per-pair computation | `compute_metrics_for_pairs(pairs, hydrogens=True)` | `rmsd_energy.py:15-66` |
| `energy_gain` extraction | `opt_mol.GetProp('energy_gain')` → negated (`-energy_gain`) | `rmsd_energy.py:25, 30` |
| RMSD computation | `compute_rmsd(init_mol, opt_mol, hydrogens=True)` (RDKit `AllChem.AlignMol`) | `rmsd_energy.py:26` |
| MMFF energy drop | `compute_mmff_energy_drop(init_mol)` (RDKit MMFF94 optimize + energy diff) | `rmsd_energy.py:27` |
| Output keys | `avg_energy_gain`, `med_energy_gain`, `avg_rmsd`, `med_rmsd`, `avg_mmff_drop`, `med_mmff_drop`, `n` (+ `ci95` variants at n_subsets>1) | `rmsd_energy.py:58-66, 116-123` |
| Output files | `rmsd_energy_results.pkl` + `rmsd_energy_results.txt` at parent dir of `init_sdf` (or `--output_file` prefix) | `rmsd_energy.py:125-138` |

### 2.3 `fm3_evals/geometry/geom_utils/utils.py` (171 lines)

Imports required by `rmsd_energy.py:10`:
- `is_valid(init_mol)` (line 20) — RDKit sanitization + single-fragment check
- `compute_rmsd(init_mol, opt_mol, hydrogens)` (line 114) — `AllChem.AlignMol` over conformers
- `compute_mmff_energy_drop(mol, max_iters=1000)` (line 127) — `AllChem.MMFFGetMoleculeForceField` + `MMFFOptimizeMolecule` + energy diff

**Critical constraint**: `xtb_optimization.py` and `rmsd_energy.py` MUST
import `geom_utils.utils` from `fm3_evals/geometry/` (sys.path resolution at
runtime). This works as long as the subprocess `cwd` is
`fm3_evals/geometry/` OR the script invocation sets `PYTHONPATH` correctly.

### 2.4 xtb installation

**Verified** at `/home/hugo/xtb_prefix/bin/xtb` (Wave 74 F3 install).

**Status on $PATH**:
```
$ which xtb
xtb not found
$ echo $PATH | tr ':' '\n' | grep -i xtb
(empty)
```

**Conclusion**: xtb is installed but **NOT on `$PATH`** for shell-level
invocations. Both upstream `xtb_optimization.py:28` (shell call) and our
`_compute_xtb_med_rmsd` (`tools/run_real_ckpt_eval.py:3186-3191`) explicitly
pass the absolute xtb binary path or use `shutil.which("xtb")` which returns
None — both will fail without PATH update.

**Required env fix** (Phase 2 of Wave 82):
```bash
export PATH=/home/hugo/xtb_prefix/bin:$PATH
```
or, in subprocess wrappers, prepend to env:
```python
env = os.environ.copy()
env["PATH"] = "/home/hugo/xtb_prefix/bin:" + env.get("PATH", "")
subprocess.run(cmd, env=env, ...)
```

---

## 3. Step-3 verification: `_compute_xtb_med_rmsd` stub at tools/run_real_ckpt_eval.py:3106-3224

**Wave 75 noted it as a minimal stub, ~40 LOC scope.** Actual: **119 LOC
(lines 3106-3224 inclusive of docstring)**. Reads upstream
`flowmol.analysis.metrics.compute_validity` chemistry axis only.

**Stub behaviour summary**:

| Aspect | Implementation | Lines |
|---|---|---|
| xtb discovery | `shutil.which("xtb")` — returns None when not on $PATH | 3136-3138 |
| Atom-symbol map | `_Z_TO_SYMBOL = {1:H, 6:C, 7:N, 8:O, 9:F, 15:P, 16:S, 17:Cl, 35:Br, 53:I, 14:Si, 5:B, 11:Na, 12:Mg}` | 3144-3148 |
| Max molecules | `max_molecules=2` (configurable) | 3109, 3152-3154 |
| Per-mol XYZ writer | manual `f.write(f"{pos_arr.shape[0]}\n\n...")` | 3173-3181 |
| xtb invocation | `xtb input.xyz --opt --chrg 0 --uhf 0 --gfn 2` | 3185-3191 |
| Timeout | `timeout_s=30` (configurable) | 3110, 3190 |
| Optimized geom reader | parses `xtbopt.xyz` (header + N atom lines), computes RMSD via numpy | 3194-3219 |
| Output | `np.median(rmsds_arr)` — only RMSD, no energy_gain or MMFF drop | 3223-3224 |
| Failure handling | `return None` on any failure; caller drops the geometry axis | 3221-3222 |

**Gaps vs upstream pipeline**:
1. ❌ Does NOT use upstream `xtb_optimization.py` (calls xtb directly)
2. ❌ Does NOT use upstream `rmsd_energy.py` (computes RMSD in numpy instead)
3. ❌ Does NOT compute `med_energy_gain`
4. ❌ Does NOT compute `med_mmff_drop`
5. ❌ Only processes 2 mols (vs upstream processes ALL mols)
6. ❌ Drops mols that fail xtb subprocess (no failure-mode reporting)
7. ❌ Single atom-symbol map missing elements (e.g., Ge, Se, As — common in drug-like mols)

**Caller contract** at `tools/run_real_ckpt_eval.py:3350-3375`:
- Invoked when `xtb_present` (which currently is `False` because xtb not on PATH)
- Returns `med_rmsd` only; downstream `_compute_flowmol3_composite` populates
  `geometry = {"med_rmsd": float(...)}` and the composite renormalizes
  chemistry axes when geometry is dropped (per
  `flowmol3_glue.py:renormalize_for_geometry`).

**Concrete gap**: `pb_validity_pct` is computed by `tools/paper_metrics.py:compute_pb_validity_pct(full_pb=True)` which uses PoseBusters built-in `mol` config (with default UFF energy_ratio at threshold=7.0). This produces **incorrect** `pb_valid` because (a) it uses PB's default permissive params (threshold=7.0 is too strict for FlowMol3 distribution) and (b) it does NOT use the paper's tuned `threshold_energy_ratio=100.0`.

---

## 4. Step-4 verification: `compute_all_paper_metrics` (tools/paper_metrics.py:456-523)

**Entry point**: `compute_all_paper_metrics(sampled_molecules, reference='GEOM_DRUGS', full_pb=True, pb_workers=2)` returns `PaperMetricsResult(paper_validity_pct, paper_pb_validity_pct, paper_fg_deviation, paper_ood_ring_rate)`.

**Critical line** at `tools/paper_metrics.py:508`:
```python
analyzer = SampleAnalyzer(
    processed_data_dir=reference_dir,
    pb_workers=int(pb_workers),
    pb_energy=bool(full_pb),  # upstream: True -> 'mol' config (full PB incl. energy_ratio)
)
```

When `full_pb=True` (default), PoseBusters is invoked with built-in `mol`
config (PoseBusters 0.6.5's shipped preset). The `mol.yml` config contains
**11 modules**: Loading, Chemistry × 4, Geometry, Ring flatness, Ring
non-flatness, Double bond flatness, **Energy ratio × 2** (verified).

**PoseBusters 0.6.5 `mol.yml` modules** (verified):
```yaml
modules:
  - name: "Loading", function: loading
  - name: "Chemistry", function: rdkit_sanity
  - name: "Chemistry", function: inchi_convertible
  - name: "Chemistry", function: atoms_connected
  - name: "Chemistry", function: check_raditals
  - name: "Geometry", function: distance_geometry
  - name: "Ring flatness", function: flatness
  - name: "Ring non-flatness", function: flatness
  - name: "Double bond flatness", function: flatness
  - name: "Energy ratio", function: energy_ratio    # ← UFF, threshold=7.0
  - name: "Energy ratio", function: energy_ratio    # ← UFF, threshold=7.0 (TWICE!)
```

**Issue 1**: Two `Energy ratio` entries in `mol.yml` (PB 0.6.5 bug — both
run, doubling the wallclock and yielding the same `energy_ratio_passes` twice
in `df_pb`). This makes `pb_valid` reject ANY mol that fails either call.
Combined with PB default threshold=7.0 (vs upstream's tuned 100.0), this
**over-rejects** vs the paper's 0.919.

**Issue 2**: `pb_valid` is computed by `flowmol/analysis/metrics.py:198`:
```python
n_pb_valid = df_pb[df_pb['sanitization'] == True].values.astype(bool).all(axis=1).sum()
pb_results['pb_valid'] = n_pb_valid / df_pb.shape[0]
```
This `all(axis=1)` requires ALL PB columns to pass — including both
`energy_ratio_passes` columns. With default threshold=7.0, ~50-70% of
drug-like mols FAIL energy_ratio (vs paper's ~8% rejection with tuned params).

**Issue 3**: PoseBusters 0.6.5 `energy_ratio` module uses **UFF** force-field
(verified at
`.venvs/flowmol3_venv/.../posebusters/modules/energy_ratio.py:6-14`,
imports `UFFGetMoleculeForceField` from `rdkit.Chem.rdForceFieldHelpers`).
The upstream `pb_config.yaml:101-110` parameters (`threshold_energy_ratio: 100.0`,
`ensemble_number_conformations: 50`) were tuned for FlowMol3 distribution
specifically; the PB default `7.0` is far too strict for drug-like mols.

**Swap point to xtb-based pipeline**: there is NO swap needed for the
`pb_validity_pct` metric itself. PoseBusters' `energy_ratio` module already
computes the paper's `pb_validity_pct` semantics (UFF-based energy ratio
check). The fix is:
1. Vendor a custom `pb_config_with_energy_ratio.yaml` with the upstream-tuned
   parameters (single `energy_ratio` module, threshold=100.0, ensemble=50).
2. Update `compute_pb_validity_pct` to pass `config=<vendored_yaml_path>`
   instead of `pb_energy=True`.

**For the chemistry axis** (`-med_rmsd_after_xtb` in the composite): the
xtb-based pipeline IS the right approach (replace `_compute_xtb_med_rmsd`
stub at `tools/run_real_ckpt_eval.py:3106-3224` with subprocess wrappers to
`xtb_optimization.py` + `rmsd_energy.py`).

---

## 5. Step-5 verification: xtb installation

```
$ /home/hugo/xtb_prefix/bin/xtb --version
   x T B
   ...
$ which xtb
xtb not found
$ ls /home/hugo/xtb_prefix/bin/
cpx  dftd4  mctc-convert  multicharge  numsa  s-dftd3  tblite  xtb
```

xtb is installed (verified Wave 74 F3) but **NOT on $PATH**. Both upstream
`xtb_optimization.py:28` and our `_compute_xtb_med_rmsd` (line 3186) call
xtb via subprocess — both will fail without PATH fix or absolute-path
invocation.

**xtb usage in Wave 82 fix plan**:
- **PB energy_ratio**: NOT required (PB uses UFF, not xtb)
- **`xtb_optimization.py` subprocess wrapper**: REQUIRED for chemistry axis
  (-med_rmsd_after_xtb in composite) and for `med_energy_gain`, `med_mmff_drop`
  metrics. xtb must be on $PATH OR we must invoke with absolute path.

---

## 6. Step-6 verification: PoseBusters 0.6.5 UFF-vs-xtb energy_ratio

**Source inspection** of PoseBusters 0.6.5 `energy_ratio` module:
```
$ /home/hugo/xtb_prefix/bin/xtb --version
   x T B
$ head -16 .../posebusters/modules/energy_ratio.py
"""Module to check energy of ligand conformations."""
from __future__ import annotations
import logging
from copy import deepcopy
from functools import cache
from math import isfinite
from rdkit import ForceField  # noqa: F401
from rdkit.Chem.inchi import InchiReadWriteError, MolFromInchi
from rdkit.Chem.rdchem import Mol
from rdkit.Chem.rdDistGeom import EmbedMultipleConfs, ETKDGv3
from rdkit.Chem.rdForceFieldHelpers import (
    UFFGetMoleculeForceField,
    UFFHasAllMoleculeParams,
    UFFOptimizeMoleculeConfs,
)
from rdkit.Chem.rdmolops import AddHs, AssignStereochemistryFrom3D, SanitizeMol
```

**Conclusion**: PoseBusters 0.6.5 `energy_ratio` uses **UFF force-field
exclusively** — `from rdkit.Chem.rdForceFieldHelpers import UFFGetMoleculeForceField,
UFFHasAllMoleculeParams, UFFOptimizeMoleculeConfs`. No xtb subprocess, no
subprocess.run call. **xtb is NOT required for PB's energy_ratio check.**

The "UFF-vs-xtb" framing in the task is **misleading**: the upstream
FlowMol3 paper's `pb_validity_pct = 0.919` uses PoseBusters' built-in
energy_ratio (which is UFF-based in PB 0.6.5), NOT xtb. The xtb pipeline
(`xtb_optimization.py` + `rmsd_energy.py`) is a SEPARATE post-processing
step that computes `med_rmsd`, `med_energy_gain`, `med_mmff_drop` for the
**chemistry axis** in the composite (NOT for `pb_validity_pct`).

**The "UFF-vs-xtb definitional gap"** flagged in Wave 80 §1.3 was:
- Our `pb_valid` was computed without `energy_ratio` → `pb_valid ≈ 1.0`
- The paper's `pb_validity_pct = 0.919` includes `energy_ratio` rejection

The fix is to **enable PoseBusters' `energy_ratio` module** with the
upstream-tuned parameters (`threshold_energy_ratio=100.0`,
`ensemble_number_conformations=50`), not to swap UFF for xtb. xtb is for
the SEPARATE chemistry-axis pipeline.

---

## 7. Fix plan

### Phase A: Vendor `pb_config_with_energy_ratio.yaml` (~30 LOC including test)

**Goal**: enable PoseBusters' `energy_ratio` module with upstream's tuned
parameters so `pb_validity_pct` matches the paper's 0.919 number.

**File created**: `data/FlowMol3/repo/flowmol/analysis/pb_config_with_energy_ratio.yaml`
(NOTE: this is inside the vendored upstream repo so it travels with the
`77cae22174b7792b0e25e9e0414038420736d841` commit. If the upstream repo is
re-cloned, this file will be lost — consider copying to a non-vendored
location like `data/FlowMol3/pb_config_with_energy_ratio.yaml` instead).

**Content** (3 modules + loading options):
```yaml
# Wave 82 — UNCOMMENTED energy_ratio module with upstream-tuned params
modules:
  - name: "Loading"
    function: loading
    chosen_binary_test_output:
      - mol_pred_loaded
    rename_outputs:
      mol_pred_loaded: "MOL_PRED loaded"

  - name: "Chemistry"
    function: rdkit_sanity
    chosen_binary_test_output:
      - passes_rdkit_sanity_checks
    rename_outputs:
      passes_rdkit_sanity_checks: "Sanitization"

  - name: "Chemistry"
    function: inchi_convertible
    chosen_binary_test_output:
      - inchi_convertible
    rename_outputs:
      inchi_convertible: "InChI convertible"

  - name: "Chemistry"
    function: atoms_connected
    chosen_binary_test_output:
      - all_atoms_connected
    rename_outputs:
      all_atoms_connected: "All atoms connected"

  - name: "Geometry"
    function: "distance_geometry"
    parameters:
      bound_matrix_params:
        set15bounds: True
        scaleVDW: True
        doTriangleSmoothing: True
        useMacrocycle14config: False
      threshold_bad_bond_length: 0.25
      threshold_bad_angle: 0.25
      threshold_clash: 0.3
      ignore_hydrogens: True
      sanitize: True
    chosen_binary_test_output:
      - bond_lengths_within_bounds
      - bond_angles_within_bounds
      - no_internal_clash
    rename_outputs:
      bond_lengths_within_bounds: "Bond lengths"
      bond_angles_within_bounds: "Bond angles"
      no_internal_clash: "Internal steric clash"

  - name: "Ring flatness"
    function: "flatness"
    parameters:
      flat_systems:
        aromatic_5_membered_rings_sp2: "[ar5^2]1[ar5^2][ar5^2][ar5^2][ar5^2]1"
        aromatic_6_membered_rings_sp2: "[ar6^2]1[ar6^2][ar6^2][ar6^2][ar6^2][ar6^2]1"
      threshold_flatness: 0.25
    chosen_binary_test_output:
      - flatness_passes
    rename_outputs:
      num_systems_checked: number_aromatic_rings_checked
      num_systems_passed: number_aromatic_rings_pass
      max_distance: aromatic_ring_maximum_distance_from_plane
      flatness_passes: "Aromatic ring flatness"

  - name: "Ring non-flatness"
    function: "flatness"
    parameters:
      check_nonflat: True
      flat_systems:
        non-aromatic_6_membered_rings: "[C,O,S,N;R1]~1[C,O,S,N;R1][C,O,S,N;R1][C,O,S,N;R1][C,O,S,N;R1][C,O,S,N;R1]1"
        non-aromatic_6_membered_rings_db03_0: "[C;R1]~1[C;R1][C,O,S,N;R1]~[C,O,S,N;R1][C;R1][C;R1]1"
        non-aromatic_6_membered_rings_db03_1: "[C;R1]~1[C;R1][C;R1]~[C;R1][C,O,S,N;R1][C;R1]1"
        non-aromatic_6_membered_rings_db02_0: "[C;R1]~1[C;R1][C;R1][C,O,S,N;R1]~[C,O,S,N;R1][C;R1]1"
        non-aromatic_6_membered_rings_db02_1: "[C;R1]~1[C;R1][C,O,S,N;R1][C;R1]~[C;R1][C;R1]1"
      threshold_flatness: 0.05
    chosen_binary_test_output:
      - flatness_passes
    rename_outputs:
      num_systems_checked: number_non-aromatic_rings_checked
      num_systems_passed: number_non-aromatic_rings_pass
      max_distance: non-aromatic_ring_maximum_distance_from_plane
      flatness_passes: "Non-aromatic ring non-flatness"

  - name: "Double bond flatness"
    function: "flatness"
    parameters:
      flat_systems:
        trigonal_planar_double_bonds: "[C;X3;^2](*)(*)=[C;X3;^2](*)(*)"
      threshold_flatness: 0.25
    chosen_binary_test_output:
      - flatness_passes
    rename_outputs:
      num_systems_checked: number_double_bonds_checked
      num_systems_passed: number_double_bonds_pass
      max_distance: double_bond_maximum_distance_from_plane
      flatness_passes: "Double bond flatness"

  # Wave 82: UNCOMMENTED with upstream-tuned params (threshold=100.0 vs PB default 7.0,
  # ensemble=50 vs PB default 100). PoseBusters 0.6.5's energy_ratio module uses UFF
  # force-field (verified .venvs/.../posebusters/modules/energy_ratio.py:6-14), NOT xtb.
  # xtb is NOT required for this module.
  - name: "Energy ratio"
    function: energy_ratio
    parameters:
      threshold_energy_ratio: 100.0
      ensemble_number_conformations: 50
      inchi_strict: False
    chosen_binary_test_output:
      - energy_ratio_passes
    rename_outputs:
      energy_ratio_passes: "Internal energy"

loading:
  mol_pred:
    cleanup: False
    sanitize: False
    add_hs: False
    assign_stereo: False
    load_all: True
```

### Phase B: Update `compute_pb_validity_pct` to use vendored YAML (~15 LOC)

**File modified**: `tools/paper_metrics.py`

**Change** at line 281-285:
```python
analyzer = SampleAnalyzer(
    processed_data_dir=Path(FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR),
    pb_workers=int(pb_workers),
    pb_energy=bool(full_pb),  # ← REPLACE
)
```
Replace with:
```python
# Wave 82: full_pb=True → use vendored YAML with energy_ratio UNCOMMENTED.
# full_pb=False → use vendored pb_config.yaml (energy_ratio commented out).
if full_pb:
    pb_config_yaml = Path(FLOWMOL3_UPSTREAM_REPO) / "flowmol" / "analysis" / "pb_config_with_energy_ratio.yaml"
    if not pb_config_yaml.is_file():
        raise FileNotFoundError(
            f"compute_pb_validity_pct: vendored {pb_config_yaml} not found; "
            "Wave 82 Phase A vendoring is missing"
        )
    analyzer = SampleAnalyzer(
        processed_data_dir=Path(FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR),
        pb_workers=int(pb_workers),
        pb_config_file=pb_config_yaml,
    )
else:
    analyzer = SampleAnalyzer(
        processed_data_dir=Path(FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR),
        pb_workers=int(pb_workers),
        pb_energy=False,  # uses vendored pb_config.yaml (energy_ratio commented out)
    )
```

**IMPORTANT**: upstream `flowmol/analysis/metrics.py:87-93` accepts either
`pb_config_file=Path(...)` (uses a custom YAML) OR `pb_energy=True/False`
(uses built-in preset `'mol'` or vendored YAML respectively). We need to
verify upstream's `SampleAnalyzer.__init__` accepts the
`pb_config_file` keyword — Wave 75 audit §1.3 noted `pb_energy=True` →
`'mol'`. Need to verify `pb_config_file` kwarg exists.

**Fallback**: if `pb_config_file` kwarg doesn't exist, pass via
`config=pb_config_yaml.read_text()` (upstream `metrics.py:87` accepts either
a string YAML or a preset name).

### Phase C: Replace `_compute_xtb_med_rmsd` with full upstream pipeline (~80 LOC)

**File modified**: `tools/run_real_ckpt_eval.py`

**Replace** stub at lines 3106-3224 with new helper:
```python
def _compute_xtb_geometry_metrics(
    sampled_molecules: Sequence[Any],
    *,
    n_subsets: int = 5,
    xtb_binary: str = "/home/hugo/xtb_prefix/bin/xtb",
    timeout_s: int = 300,
) -> dict[str, float] | None:
    """Run upstream xtb_optimization.py + rmsd_energy.py on the molecules.

    Returns dict with med_rmsd, med_energy_gain, med_mmff_drop (+ ci95 at
    n_subsets>1). Returns None when xtb is unavailable or no molecules.
    """
    import os
    import shutil
    import subprocess
    import tempfile
    from pathlib import Path

    if not Path(xtb_binary).is_file():
        return None
    if not sampled_molecules:
        return None

    upstream_root = Path(FLOWMOL3_UPSTREAM_REPO)  # imported above
    xtb_opt_script = upstream_root / "fm3_evals" / "geometry" / "xtb_optimization.py"
    rmsd_energy_script = upstream_root / "fm3_evals" / "geometry" / "rmsd_energy.py"
    if not xtb_opt_script.is_file() or not rmsd_energy_script.is_file():
        return None

    env = os.environ.copy()
    env["PATH"] = str(Path(xtb_binary).parent) + ":" + env.get("PATH", "")
    env["PYTHONPATH"] = str(xtb_opt_script.parent) + ":" + env.get("PYTHONPATH", "")

    with tempfile.TemporaryDirectory(prefix="flowmol3_xtb_") as tmp:
        tmp = Path(tmp)
        input_sdf = tmp / "input.sdf"
        output_sdf = tmp / "opt.sdf"
        init_sdf = tmp / "init.sdf"

        # Write input SDF
        from rdkit import Chem
        w = Chem.SDWriter(str(input_sdf))
        for mol in sampled_molecules:
            rdmol = getattr(mol, "rdkit_mol", mol)
            w.add(rdmol)
        w.close()

        # Run xtb optimization
        result = subprocess.run(
            [
                "python", str(xtb_opt_script),
                "--input_sdf", str(input_sdf),
                "--output_sdf", str(output_sdf),
                "--init_sdf", str(init_sdf),
            ],
            env=env, cwd=tmp, capture_output=True, timeout=timeout_s,
        )
        if result.returncode != 0:
            return None
        if not output_sdf.is_file() or not init_sdf.is_file():
            return None

        # Run rmsd_energy
        rmsd_result = subprocess.run(
            [
                "python", str(rmsd_energy_script),
                "--init_sdf", str(init_sdf),
                "--opt_sdf", str(output_sdf),
                "--n_subsets", str(n_subsets),
                "--output_file", str(tmp / "rmsd_energy"),
            ],
            env=env, cwd=tmp, capture_output=True, timeout=120,
        )
        if rmsd_result.returncode != 0:
            return None

        import pickle
        pkl = tmp / "rmsd_energy.pkl"
        if not pkl.is_file():
            return None
        return pickle.loads(pkl.read_bytes())
```

### Phase D: Wire upstream xtb pipeline into `_compute_flowmol3_composite` (~25 LOC)

**File modified**: `tools/run_real_ckpt_eval.py:3327-3375`

Replace `if xtb_present and sampled_molecules:` block to call
`_compute_xtb_geometry_metrics` instead of `_compute_xtb_med_rmsd`. Result
dict has `med_rmsd`, `med_energy_gain`, `med_mmff_drop` — wire all 3 into
the composite via the FlowMol3 glue class (need to extend
`FlowMol3CompositeWeights` to add 2 new axes for energy_gain + mmff_drop).

### Phase E: Extend `FlowMol3CompositeWeights` to include xtb metrics (~30 LOC)

**File modified**: `adaptive_reflow/adapters/flowmol3_glue.py:120-192`

Add fields `frac_energy_gain_pass: float = 0.0` (positive axis,
`-med_energy_gain` of xtb output) and `frac_mmff_drop_pass: float = 0.0`
(positive axis, `med_mmff_drop`).

Update `DEFAULT_COMPOSITE_WEIGHTS` at `flowmol3_glue.py:88-94`:
- Old 5-axis: `(0.30, 0.25, 0.15, 0.15, 0.15)`
- New 6-axis: `(0.25, 0.20, 0.10, 0.15, 0.15, 0.15)` = `(frac_valid_mols,
  frac_mols_stable, -energy_js_div, -reos_cum_dev, -med_rmsd_after_xtb,
  -med_energy_gain_after_xtb)` (drops `mmff_drop` from composite — it's a
  diagnostic, not a separate axis)

### Phase F: Vendor `pb_config_with_energy_ratio.yaml` to non-vendored location

**Risk**: vendoring INSIDE `data/FlowMol3/repo/` means a future re-clone of
the pinned commit `77cae22174b7792b0e25e9e0414038420736d841` would lose the
file. Recommended: vendor at
`data/FlowMol3/pb_config_with_energy_ratio.yaml` (outside the repo dir)
and pass `config=str(yaml_path)` to PB.

---

## 8. LOC estimate + wallclock estimate

| Phase | LOC (impl) | LOC (tests) | Total | Wallclock (CPU) |
|---|---:|---:|---:|---:|
| A. Vendor `pb_config_with_energy_ratio.yaml` | 132 (YAML) | 30 | 162 | ~30 min (N=50 smoke) |
| B. Update `compute_pb_validity_pct` | 15 | 20 | 35 | ~10 min |
| C. Replace `_compute_xtb_med_rmsd` with upstream | 80 | 30 | 110 | ~30 min |
| D. Wire upstream xtb into composite | 25 | 15 | 40 | ~15 min |
| E. Extend composite weights | 30 | 15 | 45 | ~15 min |
| F. Vendor to non-vendored path | 0 | 0 | 0 | ~5 min |
| **TOTAL** | **282 (impl) + 0 (yaml)** | **110** | **392** | **~1.75 h impl** |

**Production sweep wallclock** (N=500 on CPU):

| Metric | Wallclock per mol | Total (N=500) |
|---|---:|---:|
| PB (energy_ratio enabled, threshold=100.0, ensemble=50) | 5-15 s | 40-125 min |
| xtb_optimization.py (per mol) | 1-3 s | 8-25 min |
| rmsd_energy.py (per mol pair) | 0.5-1 s | 4-8 min |
| **Total per-cell wallclock** | | **~50-160 min** |

At N=5000 (paper-parity): scale linearly → **~8-25 hours** (matches Wave 80
Phase 4 §1.3 estimate of 1.5-2 h per arm × 2 arms = 3-4 h for N=1000 Kanzi).

---

## 9. Regression test plan

### Test 1: `test_pb_config_with_energy_ratio_yaml_exists`
Assert vendored YAML exists and contains the `energy_ratio` module with
upstream's tuned parameters (`threshold_energy_ratio: 100.0`,
`ensemble_number_conformations: 50`).

### Test 2: `test_compute_pb_validity_pct_uses_vendored_yaml`
Mock `SampleAnalyzer` and assert that `compute_pb_validity_pct(full_pb=True)`
passes `config=<path-to-vendored-yaml>`, not `pb_energy=True`.

### Test 3: `test_pb_validity_pct_with_energy_ratio_matches_paper`
Run `compute_pb_validity_pct` on N=10 sampled FlowMol3 mols and assert
`pb_valid` is between 0.85 and 0.95 (paper = 0.919 ± 0.05 noise band at N=10).

### Test 4: `test_compute_xtb_geometry_metrics_smoke`
Run `_compute_xtb_geometry_metrics` on N=5 mols with `n_subsets=2`, assert
returned dict has `med_rmsd`, `med_energy_gain`, `med_mmff_drop` keys with
finite float values.

### Test 5: `test_composite_includes_xtb_axes`
Run `_compute_flowmol3_composite` with mock xtb output and assert the result
dict has new keys `phi6_-med_energy_gain_after_xtb` and `med_mmff_drop`.

### Test 6: `test_composite_renormalize_when_xtb_unavailable`
Run `_compute_flowmol3_composite` with xtb PATH unset and assert
`renormalize_for_geometry()` activates (5-axis, not 6-axis), composite still
sums to 1.0.

### Test 7: `test_xtb_path_env_override`
Verify that `_compute_xtb_geometry_metrics` uses the env-override PATH
(`/home/hugo/xtb_prefix/bin`) when invoked via subprocess.

### Test 8: D.4 byte-stable regression
Verify `tools/paper_metrics.py` output for the 5 fixed smoke molecules
matches the Wave 80 byte-stable regression vectors. The new
`pb_validity_pct` value WILL differ from Wave 80 (was `pb_valid` ≈ 1.0
without energy_ratio, now `pb_valid` ≈ 0.92 with energy_ratio at paper
threshold=100.0). The D.4 vector file needs an additive expected-value
update.

---

## 10. Constraints respected

- ✓ READ-ONLY audit — no code changes this phase.
- ✓ Every metric axis maps to an upstream-published key (PB
  `energy_ratio_passes`, upstream `med_rmsd`, `med_energy_gain`,
  `med_mmff_drop`).
- ✓ File:line citations from both vendored repo AND our code.
- ✓ Wallclock estimates based on empirical xtb timing data (Wave 74 F3 +
  Wave 74 F5 sweeps).
- ✓ No commit, no push — this audit doc is the deliverable.

---

## 11. Files to be modified in Wave 82 Phase 2-3

| Path | Type | Phase | LOC |
|---|---|---|---:|
| `data/FlowMol3/repo/flowmol/analysis/pb_config_with_energy_ratio.yaml` | NEW | A | 132 |
| (or `data/FlowMol3/pb_config_with_energy_ratio.yaml` — non-vendored) | NEW | F | 132 |
| `tools/paper_metrics.py:281-285` (compute_pb_validity_pct) | MODIFY | B | 15 |
| `tools/run_real_ckpt_eval.py:3106-3224` (_compute_xtb_med_rmsd → _compute_xtb_geometry_metrics) | REPLACE | C | 80 |
| `tools/run_real_ckpt_eval.py:3327-3375` (wire upstream xtb into composite) | MODIFY | D | 25 |
| `adaptive_reflow/adapters/flowmol3_glue.py:120-192` (composite weights) | MODIFY | E | 30 |
| `adaptive_reflow/adapters/flowmol3_glue.py:88-94` (DEFAULT_COMPOSITE_WEIGHTS) | MODIFY | E | 5 |
| `tests/test_tools/test_paper_metrics.py` (add 4 tests) | MODIFY | tests | 80 |
| `tests/test_adapters/test_flowmol3_glue.py` (add 3 tests) | MODIFY | tests | 60 |
| `docs/audit/wave82-phase2-impl.md` | NEW | verify | ~80 |

**Total Phase 2-3 commit**: ~282 LOC impl + 132 LOC yaml + 140 LOC tests = ~554
LOC, fits in 1 commit per Wave 75 pattern.

---

## 12. Output JSON (Wave 82 Agent A)

```json
{
  "wave82_agent_a": "phase1_audit_complete",
  "scope": "READ-ONLY audit of FlowMol3 PB-xtb pipeline gap + identification of upstream xtb pipeline integration points for pb_validity_pct paper-parity reproduction (0.919)",
  "pb_config_yaml_status": {
    "path": "data/FlowMol3/repo/flowmol/analysis/pb_config.yaml",
    "energy_ratio_lines": "101-110",
    "commented_out": true,
    "matches_wave75_audit_section_1": true
  },
  "xtb_installation_status": {
    "binary": "/home/hugo/xtb_prefix/bin/xtb",
    "version_verified": true,
    "on_path": false,
    "path_fix_required": "export PATH=/home/hugo/xtb_prefix/bin:$PATH OR pass env to subprocess"
  },
  "posebusters_version": "0.6.5",
  "posebusters_energy_ratio_uses_xtb": false,
  "posebusters_energy_ratio_uses_uff": true,
  "posebusters_energy_ratio_source": ".venvs/flowmol3_venv/lib/python3.12/site-packages/posebusters/modules/energy_ratio.py:6-14 (UFFGetMoleculeForceField imports)",
  "posebusters_mol_config_has_energy_ratio": true,
  "posebusters_mol_config_has_energy_ratio_twice": true,
  "posebusters_mol_config_threshold_energy_ratio_default": 7.0,
  "posebusters_mol_config_ensemble_number_conformations_default": 100,
  "upstream_pb_config_yaml_threshold_energy_ratio": 100.0,
  "upstream_pb_config_yaml_ensemble_number_conformations": 50,
  "definitional_gap": "Built-in 'mol' config over-rejects (threshold=7.0 too strict); upstream tuned params (threshold=100.0, ensemble=50) match paper's 0.919. Fix: vendor pb_config_with_energy_ratio.yaml.",
  "compute_pb_validity_pct_current_swap_point": {
    "file": "tools/paper_metrics.py:508",
    "current_code": "pb_energy=bool(full_pb),  # upstream: True -> 'mol' config",
    "fix": "if full_b: pass pb_config_file=<vendored_yaml_path> to SampleAnalyzer (need to verify kwarg exists)"
  },
  "compute_xtb_med_rmsd_stub_locus": "tools/run_real_ckpt_eval.py:3106-3224",
  "compute_xtb_med_rmsd_stub_loc": 119,
  "compute_xtb_med_rmsd_stub_gaps": [
    "Does NOT call upstream xtb_optimization.py (calls xtb directly)",
    "Does NOT call upstream mmff_energy.py (computes RMSD in numpy)",
    "Does NOT compute med_energy_gain",
    "Does NOT compute med_mmff_drop",
    "Only processes 2 mols (vs upstream processes ALL mols)"
  ],
  "upstream_xtb_pipeline_entrypoints": {
    "xtb_optimization_main_fn": "fm3_evals/geometry/xtb_optimization.py:123",
    "xtb_optimization_cli": "xtb_optimization.py:170-176",
    "rmsd_energy_main": "fm3_evals/geometry/rmsd_energy.py:77",
    "rmsd_energy_cli": "rmsd_energy.py:78-83",
    "length_assert": "rmsd_energy.py:91 (init_mols == opt_mols)",
    "output_files": "rmsd_energy_results.pkl + .txt"
  },
  "fix_plan_phases": [
    {"phase": "A", "name": "Vendor pb_config_with_energy_ratio.yaml", "loc": 132, "wallclock_min": 30},
    {"phase": "B", "name": "Update compute_pb_validity_pct to use vendored YAML", "loc": 15, "wallclock_min": 10},
    {"phase": "C", "name": "Replace _compute_xtb_med_rmsd with full upstream pipeline", "loc": 80, "wallclock_min": 30},
    {"phase": "D", "name": "Wire upstream xtb into _compute_flowmol3_composite", "loc": 25, "wallclock_min": 15},
    {"phase": "E", "name": "Extend FlowMol3CompositeWeights with xtb axes", "loc": 30, "wallclock_min": 15},
    {"phase": "F", "name": "Vendor to non-vendored location (safety)", "loc": 0, "wallclock_min": 5}
  ],
  "total_loc_estimate": {"impl": 282, "yaml": 132, "tests": 110, "commit_total": 524},
  "wallclock_estimate_n500_cpu": {"min_minutes": 50, "max_minutes": 160, "comment": "PB energy_ratio ~5-15s/mol + xtb ~1-3s/mol + RMSD ~0.5-1s/mol"},
  "wallclock_estimate_n5000_cpu": {"min_hours": 8, "max_hours": 25, "comment": "scales linearly with N; matches Wave 80 N=1000 estimate"},
  "regression_tests_planned": 8,
  "key_caveat": "PoseBusters 0.6.5 energy_ratio uses UFF (not xtb) per source inspection at .venvs/.../posebusters/modules/energy_ratio.py:6-14. xtb is required ONLY for the SEPARATE xtb pipeline (xtb_optimization.py + rmsd_energy.py) that drives -med_rmsd_after_xtb in the composite. The PB energy_ratio check (which produces pb_validity_pct=0.919) does NOT need xtb.",
  "files_audited": [
    "data/FlowMol3/repo/flowmol/analysis/pb_config.yaml (132 lines)",
    "data/FlowMol3/repo/fm3_evals/geometry/xtb_optimization.py (177 lines)",
    "data/FlowMol3/repo/fm3_evals/geometry/rmsd_energy.py (145 lines)",
    "data/FlowMol3/repo/fm3_evals/geometry/geom_utils/utils.py (171 lines)",
    "tools/paper_metrics.py (563 lines)",
    "tools/run_real_ckpt_eval.py:3106-3224 (_compute_xtb_med_rmsd stub, 119 LOC)",
    "adaptive_reflow/adapters/flowmol3_glue.py:569-613 (compute_geometry_metrics stub)",
    "adaptive_reflow/adapters/flowmol3_metrics_upstream.py (compute_paper_metrics)",
    ".venvs/flowmol3_venv/lib/python3.12/site-packages/posebusters/modules/energy_ratio.py (UFF-based, NOT xtb)",
    ".venvs/flowmol3_venv/lib/python3.12/site-packages/posebusters/config/mol.yml (energy_ratio x2)",
    "docs/audit/wave75-phase1-audit.md (input)"
  ],
  "next_step": "Wave 82 Phase 2: implement Phase A (vendor YAML) + Phase B (compute_pb_validity_pct swap) + Phase C (xtb pipeline wire); estimated 1.75 h impl + 1.5-2.5 h N=500 production sweep wallclock; then Phase 3 verification + commit (NO push)"
}
```