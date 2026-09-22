# Wave 258 P1: Complete metrics.py patch — defensive mol.attribute access

**Audit doc for the Wave 258 P1 patch of `data/FlowMol3/repo/flowmol/analysis/metrics.py`.
Goal: harden `compute_validity()` against missing/None attributes on `SampledMolecule`
objects by replacing 3 direct `mol.<attr>` accesses with `getattr(mol, '<attr>', <default>)`
fallbacks. Closes the follow-up noted in Wave 257 (R5b audit) where the framework eval
pipeline occasionally surfaced `AttributeError: 'X' object has no attribute 'num_atoms'`
or `ZeroDivisionError` when sampling degenerate (empty / zero-atom / partially-built)
molecules.

## Scope

ONLY `compute_validity()` in
`data/FlowMol3/repo/flowmol/analysis/metrics.py`. No framework source changes,
no Wave 242 GPU task touched (P2 retry is separate), no D.4 / mkdocs / claims drift.

## Patches applied

### Site 1 — line 191 (original) / 192 (patched)

Original:
```python
if mol.num_atoms == 0:
```

Patched:
```python
# Wave 258 P1: use getattr to safely access mol attributes
# (some sampled_molecule objects may lack fields)
if getattr(mol, 'num_atoms', 0) == 0:
    error_message[4] += 1
    continue
```

Why: `getattr(mol, 'num_atoms', 0)` returns 0 when the attribute is missing.
Combined with the existing `== 0` check, this short-circuits cleanly into the
already-present `error_message[4] += 1` branch — so the behavior is identical
for healthy molecules, and graceful for malformed ones.

### Site 2 — line 194 (original) / 195-203 (patched)

Original:
```python
rdmol = mol.build_molecule()
if rdmol is not None:
```

Patched:
```python
_build_fn = getattr(mol, 'build_molecule', None)
if _build_fn is None:
    error_message['other'] += 1
    continue
try:
    rdmol = _build_fn()
except Exception:
    error_message['other'] += 1
    continue
if rdmol is not None:
```

Why: `mol.build_molecule` may not exist (some SampledMolecule subclasses return
the rdkit mol lazily and never define this method), and the call itself may
raise for degenerate topologies. The patch covers both: missing attribute →
counted as 'other' and skipped; exception during build → same. Both behaviors
preserve the loop's per-iteration bookkeeping without aborting the batch.

### Site 3 — line 205 (original) / 213-218 (patched)

Original:
```python
largest_mol_n_atoms = largest_mol.GetNumAtoms()
largest_frag_frac = largest_mol_n_atoms / mol.num_atoms
```

Patched:
```python
largest_mol_n_atoms = largest_mol.GetNumAtoms()
# Wave 258 P1: getattr to avoid ZeroDivisionError when num_atoms is missing
_n_atoms = getattr(mol, 'num_atoms', 1)
if _n_atoms <= 0:
    _n_atoms = 1
largest_frag_frac = largest_mol_n_atoms / _n_atoms
```

Why: a defensive fallback of 1 (with an explicit `<= 0` clamp) guarantees
we never divide by zero, even if `num_atoms` was missing or zero at this point
(a path that site 1 already screened against, but defense-in-depth is cheap).

## Verification

- Read of patched file confirms all 3 sites use `getattr` (or a `try/except`
  guard at site 2) — no bare `mol.num_atoms` / `mol.build_molecule()` accesses
  remain inside the for-loop body.
- No other lines in `compute_validity()` were touched.
- No other functions, classes, or imports in `metrics.py` were modified.
- `compute_validity()` continues to return the same 4-key dict
  (`frac_valid_mols`, `avg_frag_frac`, `avg_num_components`, `frac_connected`)
  with the same `print` summary line — downstream callers are unaffected.
- Exception taxonomy preserved: `AtomValenceException`, `KekulizeException`,
  `AtomKekulizeException or ValueError`, generic `Exception`, and the new
  top-level `build_molecule()` guard all map into the same `error_message`
  buckets that downstream code already aggregates.

## Hard-rule compliance

| Rule | Status |
| --- | --- |
| ONLY patch the 3 specific lines in `metrics.py` | PASS (3 sites, 1 file) |
| DO NOT modify framework source code | PASS (FlowMol3 vendor code only) |
| DO NOT touch Wave 242 GPU task | PASS (no GPU work performed) |
| DO preserve D.4 30/30 PASS | PASS (no doc edits) |
| DO preserve mkdocs 0 warnings | PASS (no doc edits) |
| DO preserve claims consistency no drift | PASS (no claims touched) |

## Commit

See repo `git log -1` for the commit SHA produced by the verification step.