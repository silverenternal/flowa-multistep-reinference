# Wave 246 P1 — Commit the metrics.py Patch to Git

**Status:** DONE — `data/FlowMol3/repo/flowmol/analysis/metrics.py` is now
tracked in git via a force-add (`git add -f`); see commit SHA at the end of
this doc.

## Motivation

The Wave 244 P5 + Wave 245 P1 defensive patch
(`docs/audit/wave244-p5-metrics-patch.md`,
`docs/audit/wave245-p1-metrics-patch-validation.md`) lives in vendored upstream
code under `data/FlowMol3/repo/flowmol/analysis/metrics.py`. The entire
`data/FlowMol3/` directory is excluded by the project `.gitignore` (rule
`data/*` on line 9), so until this commit the patch was a *local-only*
modification: it worked, but it was invisible to reviewers inspecting the git
tree.

DeepSeek reviewer feedback flagged this as dishonest: a vendored metric file
that the framework relies on for headline R3 numbers was silently modified
without a commit trail. The fix is to make the patch byte-addressable in git
so reviewers can `git diff <before>..<after>` the file and see exactly which
lines were added.

## Strategy

We do **NOT** remove `data/FlowMol3/` from `.gitignore` — that would
accidentally `git add` ~100 upstream source files we have no business
maintaining in this repo (and would balloon the repo by ~tens of MB on the
first push). Instead, we use `git add -f` to force-add ONLY this single file
to the index while leaving the surrounding `.gitignore` rules untouched.

After this commit, `git status` on a fresh clone will show:
- `data/FlowMol3/repo/flowmol/analysis/.gitignore` and friends: still ignored
- `data/FlowMol3/repo/flowmol/analysis/metrics.py`: **tracked** (the only one)

The README "Numerical Stability" section (added in this wave) cross-references
this audit doc so reviewers can find the diff in one click.

## Files force-added

| Path | Lines patched | Patch source |
|---|---:|---|
| `data/FlowMol3/repo/flowmol/analysis/metrics.py` | 111 (Wave 245 P1 3-tier extension) + 349–358 + 363 + 394–401 (Wave 244 P5) | `docs/audit/wave244-p5-metrics-patch.md` + `docs/audit/wave245-p1-metrics-patch-validation.md` |

Total LOC added (defensive fallbacks): ~25 lines (try/except + getattr +
hasattr chain + comments).

## Patch summary (for reviewers reading the diff)

**Line 111–122 (`analyze()`):** 3-tier fallback for `molecule.num_atoms`.
Originally crashed with `AttributeError: 'Mol' object has no attribute
'num_atoms'` for plain rdkit `Mol` objects, then crashed again on
partial `SampledMolecule` objects lacking both `.num_atoms` and `.GetAtoms()`.
Wave 245 P1 extended the Wave 244 P5 single-attribute `getattr()` with a
3-tier chain: `.num_atoms` → `.GetNumAtoms()` → `len(.GetAtoms())` → 0.

**Lines 349–358 (`check_stability()`):** try/except around the
`molecule.atom_types / .valencies / .atom_charges` reads; on `AttributeError`
fall back to walking the RDKit `Mol.GetAtoms()` and using `GetSymbol() /
GetTotalValence() / GetFormalCharge()`.

**Line 363 (`check_stability()`):** `fake_atoms = getattr(molecule,
'fake_atoms', False)` — RDKit `Mol` objects don't carry the upstream
`.fake_atoms` boolean.

**Lines 394–401 (`check_stability_midi()`):** mirror of the
`check_stability()` try/except for the alternate valence table.

## Numerical-equivalence status

**Pre-patch (seed 43, N=200):** original code path was exercised; all 200
seed-43 molecules were full `SampledMolecule` objects with `.num_atoms`,
`.atom_types`, `.valencies`, `.atom_charges`, `.fake_atoms` all present.
Result: clean `n_smiles=200, n_errors=0, n_dropped=0`, `fg_dev = 0.7361`,
`validity_pct = 1.0`. (Source:
`verification_outputs/wave242-p1-flowmol3-seed43-summary.json`.)

**Post-patch (seed 44, N=200, in flight at audit-doc save time):**
Wave 242 seed 44 retry v3 (PID `wave242_p1_flowmol3_rescue_single_mol.py`)
was launched with the Wave 245 P1 3-tier extension applied. Final
numerical-equivalence verdict is PENDING until seed 44 framework metrics
land in `verification_outputs/wave242-p1-flowmol3-seed44-framework.json`.
The audit `docs/audit/wave245-p1-metrics-patch-validation.md` defines the
expected diff envelopes:
- `|Δ fg_dev |` ≤ 0.04 (statistical-variation noise floor at N=200)
- `|Δ validity_pct |` = 0 (tied at ceiling)
- `|Δ pb_validity_pct |` ≤ 0.10 (high SEM at N=200)
- `|Δ ood_ring_rate |` ≤ 0.02

If any seed 44 metric falls outside the envelope, this commit must be
reverted and the patch should be diagnosed as a CODE bug rather than an
acceptable defensive fallback.

## Hard rules preserved

- **D.4 30/30 PASS:** verified at HEAD (`1b570a2`); the metrics.py changes
  are scoped to the `analyze()`/`check_stability()` path, which the D.4
  regression vectors do NOT exercise (they test framework internals, not
  vendored upstream metrics).
- **mkdocs 0 warnings:** preserved (no `.md` file structural changes that
  affect the nav graph).
- **claims_consistency no drift:** preserved (no CLAIMS.md row touched).
- **Wave 242 GPU task untouched:** the running seed 44 retry v3 (PID
  `wave242_p1_flowmol3_rescue_single_mol.py --seed 44`) was NOT
  interrupted.

## Cross-references

- `data/FlowMol3/repo/flowmol/analysis/metrics.py` — the file tracked in
  this commit
- `docs/audit/wave244-p5-metrics-patch.md` — Wave 244 P5 original 3-place
  patch narrative
- `docs/audit/wave245-p1-metrics-patch-validation.md` — Wave 245 P1
  numerical-equivalence validation PARTIAL (seed 44 framework metrics
  pending)
- `README.md` § Numerical Stability — the new top-level section that
  points reviewers to this audit doc + the in-tree diff
- `tnnls_submission/data_availability.md` § Code availability — TNNLS
  statement that the framework uses a patched `metrics.py` and links this
  doc
- `verification_outputs/wave242-p1-flowmol3-seed43-summary.json` — seed 43
  pre-patch framework metrics
- `verification_outputs/wave242-p1-flowmol3-seed44-{baseline,framework,
  summary}.json` — seed 44 post-patch metrics (pending; will be produced
  by the in-flight Wave 242 retry v3)

## Commit SHA

`a2f42cc1311b0123d9e66c72cfc0e0ac89f97fb8` (Wave 246 P1).

Reviewers can inspect the diff with:

```bash
git show a2f42cc -- data/FlowMol3/repo/flowmol/analysis/metrics.py
```

Or query git by subject:

```bash
git log --grep="Wave 246 P1"
```
