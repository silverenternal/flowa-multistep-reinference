# Wave 244 P5 — Defensive Patch to Upstream metrics.py

**Status:** local-only patch (vendored `data/FlowMol3/repo/flowmol/analysis/metrics.py` is `.gitignore`-d; patch is NOT committed to git).

## Bug

Wave 242 seed 44 framework arm (N=200 single_mol NFE=250) failed metrics computation at line 349 with:
```
AttributeError: 'Mol' object has no attribute 'atom_types'
```

Root cause: Some molecules returned by the upstream FlowMol3 sampler are plain `rdkit.Chem.Mol` objects (not full `SampledMolecule`), and lack the `.atom_types` / `.valencies` / `.atom_charges` attributes expected by `check_stability(molecule)`.

## Patch (Wave 244 P5 — USER ACTION approved option B)

Wrapped lines 349–351 in `try/except AttributeError` with a fallback to RDKit atom-symbol walk:

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
    # ...rest of function unchanged...
```

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