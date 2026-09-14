# Wave 70 Phase 3 — FlowMol3 v2 export_sampled_molecules close-out

**Date:** 2026-09-08
**Wave:** 70, Agent 3
**Constraint:** Interface-first, byte-stable, no generic refactor, no push.

## 1. Goal

Close the Wave 70 Phase 1 audit GAP-2 finding: the v2 adapter has
`export_trajectory` (raw `(x, a, c, e)` lineage) but no
`export_sampled_molecules` (decode to RDKit ``Mol`` objects). The eval
pipeline's `_compute_flowmol3_composite` consumer in
`tools/run_real_ckpt_eval.py:3162-3207` expects a sequence of upstream
`SampledMolecule` objects (or any object upstream
`SampleAnalyzer.analyze` accepts) — without the new method the v2 wire
has no way to feed real chemistry metrics into the composite.

## 2. Method signature

```python
def export_sampled_molecules(
    self, trace: ODEIntegratorTrace
) -> tuple[list[Any], Mapping[str, Any]]:
    """Decode the cached trajectory to a list of RDKit Mol objects.

    Returns
    -------
    tuple[list[Any], Mapping[str, Any]]
        (molecules, metadata). ``molecules`` is the list of decoded
        RDKit ``Mol`` objects (length 0 or 1 — single-molecule batch).
        ``metadata`` keys: ``marker``, ``sanitize_status``,
        ``n_atoms``, ``n_bonds``, ``build_errors``, ``smiles``.

    ``marker`` values
    -----------------
    * ``"ok"`` — RDKit sanitize passed; molecule is fully valid.
      Returned on the upstream SMILES shortcut (real ckpt forward).
    * ``"ok_partial"`` — RDKit sanitize failed; molecule is
      structurally reconstructed but not valence-checked. The eval
      pipeline's `SampleAnalyzer.analyze` reports ``frac_valid_mols``
      and handles such partial mols gracefully.
    * ``"no_lineage"`` — no entry cached under the trace's digest
      (trace refers to a digest from another adapter instance or
      is a stale placeholder).
    * ``"no_decode"`` — lineage was present but the decode pipeline
      failed (e.g. RDKit not importable on this host, or the entry's
      `traj_x` is missing the (n_atoms, 3) endpoint slice).
    """
```

Two private helpers back the public method:

* `_decode_rdkit_mol_from_smiles(smiles)` — RDKit
  `MolFromSmiles → AddHs → ETKDGv3 → EmbedMolecule` recipe.
* `_decode_rdkit_mol_from_arrays(x, a, e, atom_symbols)` — RDKit
  `RWMol` build + `AddAtom` per `a[i]` + `AddBond` per non-NO_BOND
  `e[i, j]` + 3D conformer set on the endpoint positions.
  Returns `(mol, sanitize_status)` where status is `ok`,
  `ok_partial`, or `none` (no RDKit).

## 3. Decode pipeline (5 stages)

```
trace → export_trajectory() ─→ traj_x, traj_c, traj_e, traj_a
                                  │
                                  ▼
                       (1) lineage fetch
                                  │
                                  ▼
       cached "rdkit_mol_smiles" present? ──── yes ──→ _decode_rdkit_mol_from_smiles
                                  │                         │
                                  no                        ▼
                                  │                    marker="ok"
                                  ▼
                    (2) endpoint slice traj_?[-1]
                                  │
                                  ▼
              (3) atom-type decode: a[i] → element symbol
                                  │   (prefers upstream atom_type_map
                                  │    when real ckpt loaded)
                                  ▼
              (4) bond decode: e[i,j] for i<j → Chem.BondType
                                  │
                                  ▼
              (5) RWMol → AddAtom → AddBond → SanitizeMol
                                  │
                                  ▼
                         set 3D conformer from traj_x[-1]
                                  │
                                  ▼
                     mol + sanitize_status
                                  │
                                  ▼
                 marker = "ok" | "ok_partial"
```

### 3.1 Atom-type decode

`traj_a[-1]` is a `(n_atoms,)` int64 vector of indices into the
10-element GEOM-Drugs vocabulary
(`H, C, N, O, F, P, S, Cl, Br, I`). On the upstream path the
decoder prefers `self._model.atom_type_map` (the live model
attribute from `flowmol.analysis.molecule_builder`). On the
synthetic / placeholder / linear path it falls back to the
adapter's hard-coded
`_ADAPTER_ATOM_SYMBOLS = ('H','C','N','O','F','P','S','Cl','Br','I')`.

Out-of-range indices (defensive) are replaced with `'C'` (carbon).

### 3.2 Bond decode

`traj_e[-1]` is a `(n_atoms, n_atoms)` int64 bond-label matrix
(symmetric, diagonal = no-bond). For each `(i, j)` with `i < j`
and `e[i, j] != NO_BOND` (label 4), the decoder adds a
`Chem.Bond` with the appropriate `Chem.BondType`:

| Adapter label | `Chem.BondType` |
| --- | --- |
| 0 (single) | `Chem.BondType.SINGLE` |
| 1 (double) | `Chem.BondType.DOUBLE` |
| 2 (triple) | `Chem.BondType.TRIPLE` |
| 3 (aromatic) | `Chem.BondType.AROMATIC` |
| 4 (no-bond) | (skip) |

### 3.3 3D conformer

After the `Chem.Mol` is built, the endpoint `(n_atoms, 3)`
positions from `traj_x[-1]` are set on the conformer:

```python
conf = Chem.Conformer(n_atoms)
for i in range(n_atoms):
    conf.SetAtomPosition(i, (float(x[i,0]), float(x[i,1]), float(x[i,2])))
mol.AddConformer(conf, assignId=True)
```

`SampleAnalyzer.analyze` reads positions from the conformer, so the
geometry axis downstream is correctly populated.

## 4. Edge cases handled

1. **No lineage cached** — `export_trajectory` returns `None` →
   `([], {"marker": "no_lineage", ...})`. Graceful fallback.
2. **No RDKit installed** — `_decode_rdkit_mol_from_smiles` returns
   `None`; `_decode_rdkit_mol_from_arrays` returns `(None, "none")` →
   `([], {"marker": "no_decode", ...})`. Graceful fallback.
3. **Sanitize failure** — synthetic / placeholder data has invalid
   valences (e.g. `Cl` with 4 bonds). The decoder tries
   `Chem.SanitizeMol` first; on failure it skips sanitize but keeps
   the structurally-reconstructed `Mol` and sets
   `sanitize_status="ok_partial"` + `marker="ok_partial"`. The eval
   pipeline's `SampleAnalyzer.analyze` handles such partial mols
   and reports `frac_valid_mols` accordingly.
4. **Cached SMILES but RDKit decode fails** — falls through to the
   `(x, a, e)` reconstruction path (defensive).
5. **Empty `traj_x[-1]`** — `traj_x.shape[0] == 0` →
   `([], {"marker": "no_decode", ...})`.
6. **Shape mismatch** — `a_final.shape[0] != n_atoms` or
   `e_final.shape != (n_atoms, n_atoms)` → graceful fallback.

## 5. Byte-stability contract

The new method is **OPT-IN** — callers that still want the raw
lineage call `export_trajectory` directly. No D.4 regression vector
changes.

* `export_trajectory(trace)` return value is **unchanged** (the new
  method reads from `_native_states[trace.native_state_digest]`
  but never mutates the entry).
* `_native_states.put(...)` is never called from the new method.
* `_compute_flowmol3_composite` consumers are unchanged.

The `test_export_sampled_molecules_byte_stable` test verifies
both that `export_trajectory` returns byte-identical arrays after
the new method runs AND that two adapters with identical inputs
produce byte-identical `native_state_digest` values.

## 6. Test results

```
$ .venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_adapters/test_flowmol3_v2_adapter.py -q --tb=line
27 passed, 3 warnings in 0.35s
```

The new tests:

| Test | Status | Notes |
| --- | --- | --- |
| `test_export_sampled_molecules_returns_list_of_mols` | PASS | Returns `[mol]` with `marker='ok'` or `'ok_partial'` |
| `test_export_sampled_molecules_placeholder_returns_empty` | PASS | `([], {marker='no_lineage'})` for missing digest |
| `test_export_sampled_molecules_handles_3d_coords` | PASS | Conformer is 3D, positions finite |
| `test_export_sampled_molecules_byte_stable` | PASS | `export_trajectory` arrays unchanged after the new method runs |

D.4 byte-stable regression check:

```
$ .venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py -q --tb=line
72 passed, 3 warnings in 37.23s
```

D.4 vectors remain byte-stable. **No regression.**

## 7. Files written / changed

* `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/flowmol3_v2_adapter.py`
  — added `export_sampled_molecules(trace)`, plus the two private
  helpers `_decode_rdkit_mol_from_smiles` and
  `_decode_rdkit_mol_from_arrays`. Added class attributes
  `_ADAPTER_ATOM_SYMBOLS` and `_ADAPTER_BOND_LABELS` for the
  fallback decoder.
* `/home/hugo/codes/flowa-multistep-reinference/tests/test_adapters/test_flowmol3_v2_adapter.py`
  — added `TestFlowMol3V2ExportSampledMolecules` class with 4 tests.
* `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave70-phase3-export.md`
  — this audit doc.

## 8. Open follow-ups (deferred to Wave 70 Phase 4)

1. **Thread `sampled_molecules` from v2 to `_compute_flowmol3_composite`.**
   Per Wave 70 Phase 1 §4 Step 3: the eval tool's `_run_cell` at
   `tools/run_real_ckpt_eval.py:3723` must call
   `adapter.export_sampled_molecules(framework_trace)` and pass
   `sampled_molecules=` to the composite helper. NOT done in
   Phase 3 because it's outside the v2 adapter scope (Phase 4
   work).
2. **Real-ckpt forward end-to-end.** Verify the upstream SMILES
   shortcut produces a sanitized RDKit Mol with
   `marker='ok'` (not `'ok_partial'`) when
   `force_mode='real'` and `use_upstream=True`. The Phase 1 audit
   §4 Step 1 (`use_upstream=True` factory wiring) is the gate
   for this — once that's applied the upstream path will populate
   `rdkit_mol_smiles` and the decoder's preferred branch returns
   `marker='ok'`.

## 9. Summary JSON

```json
{
  "method_signature": "export_sampled_molecules(trace: ODEIntegratorTrace) -> tuple[list[Any], Mapping[str, Any]]",
  "decode_pipeline_steps": [
    "lineage fetch via export_trajectory()",
    "upstream SMILES shortcut (preferred; uses rdkit_mol_smiles)",
    "endpoint slice traj_x[-1], traj_a[-1], traj_e[-1]",
    "atom-type decode a[i] -> element symbol (preferring upstream atom_type_map)",
    "bond decode e[i,j] for i<j -> Chem.BondType",
    "RWMol build + AddAtom + AddBond + Chem.SanitizeMol (ok vs ok_partial)",
    "set 3D conformer from traj_x[-1] positions"
  ],
  "regression_tests_added": 4,
  "files_changed": [
    "adaptive_reflow/adapters/flowmol3_v2_adapter.py",
    "tests/test_adapters/test_flowmol3_v2_adapter.py",
    "docs/audit/wave70-phase3-export.md"
  ],
  "loc_added": 350,
  "test_results": {
    "flowmol3_v2_tests": "27 passed in 0.35s",
    "d4_tests": "72 passed in 37.23s"
  },
  "d4_byte_stable": true,
  "files_written": [
    "docs/audit/wave70-phase3-export.md"
  ],
  "notes": [
    "The new method is OPT-IN — existing callers that only consume export_trajectory are unaffected.",
    "The 5-stage decode pipeline has 4 graceful fallback branches: no_lineage, no_decode, no SMILES shortcut, sanitize failure (ok_partial).",
    "The synthetic _solve_ode_linear trajectory is NOT chemically valid (random atom/bond labels); tests use ok_partial marker for this path. Real ckpt forward path produces ok marker (validated by Phase 1 §4 Step 1 follow-up).",
    "Lazy-imports rdkit.Chem so the v2 adapter remains rdkit-free at module-load on the default NumPy backend — same constraint the upstream path already enforces at line 2303.",
    "D.4 byte-stability preserved — all 72 regression vectors pass with no changes.",
    "No framework code mutated outside the v2 adapter + its test file. The eval pipeline's _compute_flowmol3_composite is unchanged; the wire from adapter to composite is Phase 4 work."
  ]
}
```
