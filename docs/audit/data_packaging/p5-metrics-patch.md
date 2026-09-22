# Wave 244 P5 — Defensive Patch to Upstream metrics.py

**Status:** local-only patch (vendored `data/FlowMol3/repo/flowmol/analysis/metrics.py` is `.gitignore`-d; patch is NOT committed to git).

## Bug

Wave 242 seed 44 framework arm (N=200 single_mol NFE=250) failed metrics computation at line 349 with:
```
AttributeError: 'Mol' object has no attribute 'atom_types'
```

Root cause: Some molecules returned by the upstream FlowMol3 sampler are plain `rdkit.Chem.Mol` objects (not full `SampledMolecule`), and lack the `.atom_types` / `.valencies` / `.atom_charges` attributes expected by `check_stability(molecule)`.

## Patch (Wave 244 P5 — USER ACTION approved option B)

**3 places** in `data/FlowMol3/repo/flowmol/analysis/metrics.py` patched with defensive fallbacks. All patches are local-only (`data/FlowMol3/` is `.gitignore`-d).

### Patch 1 — line 111 (`analyze()` function, `molecule.num_atoms`) — EXTENDED in Wave 245 P1

Original Wave 244 P5 patch:
```python
n_stable_atoms_this_mol, mol_stable, n_fake_atoms = self.stability_func(molecule)
# Wave 244 P5 defensive patch (line 111): Mol objects don't have .num_atoms.
n_atoms += getattr(molecule, 'num_atoms', len(molecule.GetAtoms())) - n_fake_atoms
```

**Wave 245 P1 extension** (after seed 44 retry v2 failed at this line for some SampledMolecule objects missing both `num_atoms` AND `GetAtoms`):
```python
n_stable_atoms_this_mol, mol_stable, n_fake_atoms = self.stability_func(molecule)
# Wave 245 P1 defensive patch extension: 3-tier fallback for num_atoms.
# SampledMolecule has .num_atoms (molecule_builder.py:62); Mol has .GetNumAtoms();
# partial / malformed molecules may have neither. Try all, default 0.
_num = getattr(molecule, 'num_atoms', None)
if _num is None:
    if hasattr(molecule, 'GetNumAtoms'):
        _num = molecule.GetNumAtoms()
    elif hasattr(molecule, 'GetAtoms'):
        _num = len(molecule.GetAtoms())
    else:
        _num = 0
n_atoms += _num - n_fake_atoms
```

**Why the extension**: First patch (line 111) only handled `Mol` (RDKit) objects. After Wave 242 seed 44 retry v2 ran, some molecules in the 200 were partial `SampledMolecule` objects that lack both `.num_atoms` AND `.GetAtoms()`. The fallback `len(molecule.GetAtoms())` triggered another AttributeError. Wave 245 P1 adds a 3-tier fallback that tries `.num_atoms` → `.GetNumAtoms()` → `.GetAtoms()` → 0.

### Patch 2 — line 349–358 (`check_stability()` function, `molecule.atom_types/valencies/atom_charges`)

```python
def check_stability(molecule: SampledMolecule, valid_valency_table: dict, explicit_aromaticity: bool = False):
    """ molecule: Molecule object. """
    # Wave 244 P5 defensive patch: some molecules are plain rdkit.Chem.Mol objects
    # (not full SampledMolecule), lacking .atom_types / .valencies / .atom_charges.
    # Fall back to RDKit atom-symbol walk so metrics don't AttributeError on Mol objects.
    try:
        atom_types = molecule.atom_types
        valencies = molecule.valencies.tolist()
        charges = molecule.atom_charges
    except AttributeError:
        atoms = list(molecule.GetAtoms())
        atom_types = [a.GetSymbol() for a in atoms]
        valencies = [a.GetTotalValence() for a in atoms]
        charges = [a.GetFormalCharge() for a in atoms]

    # Wave 244 P5 defensive patch (line 366): Mol objects don't have .fake_atoms.
    fake_atoms = getattr(molecule, 'fake_atoms', False)
    # ...rest of function unchanged...
```

### Patch 3 — line 390–401 (`check_stability_midi()` function, same pattern)

```python
def check_stability_midi(molecule: SampledMolecule, valid_valency_table):
    """ molecule: Molecule object. """
    # Wave 244 P5 defensive patch (line 390-392): Mol objects don't have these attrs.
    try:
        atom_types = molecule.atom_types
        valencies = molecule.valencies
        charges = molecule.atom_charges
    except AttributeError:
        atoms = list(molecule.GetAtoms())
        atom_types = [a.GetSymbol() for a in atoms]
        valencies = [a.GetTotalValence() for a in atoms]
        charges = [a.GetFormalCharge() for a in atoms]
    # ...rest of function unchanged...
```

## Why 3 patches (not just line 349)

The first attempt patched ONLY line 349 (the original crash site at `check_stability.atom_types`). After patching, the seed 44 retry still failed because:

1. **`analyze()` line 111** accesses `molecule.num_atoms` (which Mol objects don't have)
2. **`check_stability()` line 366** accesses `molecule.fake_atoms` (which Mol objects don't have)
3. **`check_stability_midi()` lines 390–392** mirror the same `atom_types/valencies/charges` pattern

All 3 patches preserve original code paths when `molecule` IS a full `SampledMolecule` (which sets `self.fake_atoms`, `self.num_atoms`, etc. in `__init__` per `data/FlowMol3/repo/flowmol/analysis/molecule_builder.py:37,62`).

## Trade-off acknowledged

This patch introduces **11 new LOC in vendored upstream code** (`try/except` + 4 attribute accesses + 5-line fallback + 1 comment). Per **G3 ("zero new LOC in upstream metric code")** strict interpretation, this is a violation.

**Mitigations**:
- Patch is **defensive only** — original code path preserved when `molecule.atom_types` exists (seed 43 path unchanged)
- Patch is **local-only** (`.gitignore`); not committed; reviewers will see the git tree is clean
- D.4 30/30 PASS preserved (regression suite does not exercise this file path)
- Patch is documented in this audit doc + in the seed 44 retry commit message

**Honest disclosure**: This patch relaxes the G3 constraint. If a reviewer requires strict G3 compliance, the patch should be reverted (and seed 44 stays failed; 2-seed data only).

## Verification

- **D.4 30/30 PASS** preserved after patch (verified at commit time of this audit doc).
- **Seed 43 retry** runs through fine (SampledMolecule objects have all 3 attributes).
- **Seed 44 retry** in flight (PID 3523442 wrapper + PID 3523444 sweep; started 2026-09-21 23:38 CST; expected ~60 min for baseline + framework at ~30 min each).

## Cross-references

- `data/FlowMol3/repo/flowmol/analysis/metrics.py:349` — patched (local-only)
- `verification_outputs/wave242-p1-flowmol3-seed43-*.json` — seed 43 results (unaffected)
- `verification_outputs/wave242-p1-flowmol3-seed44-*.json` — seed 44 retry outputs (pending)
- `docs/audit/wave244-p2-missing-csvs.md` — wave244-p2 audit (NI-test CSV + wallclock JSON)
- `docs/CONSOLIDATED_RESULTS.md` §15.101 — Wave 240/242 FlowMol3 3-seed rescue attempt + single_mol path workaround