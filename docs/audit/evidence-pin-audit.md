# Evidence pins: 72 recipe hashes, 19 ledgers, 5 figure assets

**Date:** 2026-10-29 · **Scope:** `paper-data/**/*REPRODUCIBILITY_RECIPE.md`,
every `SHA256SUMS` under `paper-data/` and `verification_outputs/`,
`tnnls_submission/figures.md` · **Cost:** CPU only, <2 s ·
**Frozen surfaces touched:** none

## 1. Why

The submission's reproduction path is "run the per-cell script, then
`sha256sum --check` the ledger". Both halves had been audited only by hand.
This round recomputed every pin mechanically.

## 2. Per-cell recipes — 72 pins, 60 exact, 11 need the `paper-data/` root, 1 stale

Ten `*REPRODUCIBILITY_RECIPE.md` files carry 72 `| path | sha256 |` rows.

- **60** resolve from the repo root and match.
- **11** are written relative to `paper-data/` (R2 and R5a use
  `R2_kanzi_rmsd/…`, `R5a_2d_two_moons/…`), so a bare copy-paste from the doc
  fails from the repo root. They all resolve and match once that root is tried.
  This is a documentation inconsistency, not a hash defect; the checker accepts
  both roots and nothing else.
- **1 does not match**: `paper-data/K4_k5_lineageflow_hmmer/REPRODUCIBILITY_RECIPE.md`
  pins `906420fb…` for `verification_outputs/wave280-p-k4k5/SHA256SUMS`; the
  file is `6ea0b3cb…`. The recipe says the ledger "was verified at recipe
  authorship (2026-09-27)", and Wave 308 (`868c60ba`) then migrated the sweep
  outputs out of `/tmp` and regenerated it. The ledger itself is healthy:
  `sha256sum --check` gives 43 OK plus the documented self-line failure.

  The right fix is to delete that row rather than paste the new value — a file
  that lists hashes cannot usefully pin its own hash inside the doc that
  describes it, and a pasted value goes stale again on the next regeneration.
  That is an edit to `paper-data/`, so it is left for authorisation.

## 3. Ledgers — 19 files, 7 clean, 9 self-line-only, 2 stale, 1 misnamed

| class | count | meaning |
|---|---:|---|
| `ok` | 7 | every line matches |
| `self` | 9 | the only failure is the ledger's own line, which is expected and documented |
| `real` | 2 | a listed artifact no longer matches |
| `not_a_ledger` | 1 | named `SHA256SUMS`, holds prose |

**Real #1 — `paper-data/SHA256SUMS` → `headline-evidence/README.md`.**
Ledger and README were both frozen in the Wave 328 packaging commit, but the
README was rewritten in that same commit without regenerating the ledger. The
README carries no number the paper uses; regenerating the ledger fixes it.

**Real #2 — `verification_outputs/r3_n1000_3seed_fixed_q4_2026/SHA256SUMS` →
`wave338-p5-r3-n1000-paired.json`.** Commit `40d6bb55` (GAP-27-R3-POWER,
seed-level CI defect fix) rewrote the paired JSON after the ledger was written.
The JSON on disk is the corrected one — it is exactly what
`reproduce/03_R3_FlowMol3.sh` now verifies (`mean_diff = −0.0377`,
`p = 0.559`, `d_z = −0.401`) — so the artifact is right and the ledger line is
stale. Worth noting because this is the file that carries R3's headline: a
reviewer running `sha256sum --check` there gets a FAILED line on the headline
artifact with no explanation.

**Misnamed — `verification_outputs/wave349-r1-3seed-gpu/SHA256SUMS`.**
The file is a markdown evidence note (per-seed fallback counts, manifest SHAs,
cross-references). `sha256sum --check` answers *"no properly formatted checksum
lines found"*. Its two pinned manifest hashes **do** match, so the content is
sound; the name is wrong. Rename to `EVIDENCE.md` and add a real ledger.

## 4. Figures — 5/5 pinned assets exact

`tnnls_submission/figures.md` pins five PNGs with SHA-256 and byte counts. All
five match exactly:

| asset | bytes |
|---|---:|
| `docs/figures/fig1_flowa_architecture.png` | 46 455 |
| `docs/figures/fig2_algorithm_flow.png` | 35 813 |
| `docs/figures/fig3_flowmol3_paper_metric.png` | 43 926 |
| `docs/figures/fig4_kanzi_composite_nfe.png` | 48 531 |
| `docs/figures/fig5_power_per_cell.png` | 89 826 |

The five ASCII-era companion figures referenced by name
(`fig1-protocol.png`, `fig2-loops.png`, `fig3-selection-ratio.png`,
`fig4-cifar-fid.png`, `fig5-architecture.svg`) all exist under `docs/figures/`.

## 5. What is now enforced

- `tools/check_recipe_hashes.py` — 71 rows, 0 known-stale, 0 unknown.
  Resolves both path conventions; exits non-zero on any new drift.
- `tools/check_evidence_ledgers.py` — 19 ledgers (10 clean, 9 self-line-only),
  0 known issues, 0 unknown. Separates the expected self-line failure from real
  drift, and flags a `SHA256SUMS` that is not a checksum list.
- `tests/test_recipe_hashes.py` (3) and `tests/test_evidence_ledgers.py` (3) —
  both fail if an exemption outlives the issue it covers.

## 6. Resolution (2026-10-29, authorised)

All three defects were repaired; no artifact byte was touched, only the pins
that described them.

- `paper-data/SHA256SUMS` — the `headline-evidence/README.md` line now carries
  `fd5d876a…`, the file's current hash. 68/68 lines match.
- `verification_outputs/r3_n1000_3seed_fixed_q4_2026/SHA256SUMS` — the
  `wave338-p5-r3-n1000-paired.json` line now carries `4da44c2f…`. 13/13 match.
- `verification_outputs/wave349-r1-3seed-gpu/` — the markdown note was renamed
  to `EVIDENCE.md` and a real two-line `SHA256SUMS` was written over the two
  manifests it pins. (This directory is untracked, so the rename is on-disk
  only; the note was never in the submission tree.)
- `paper-data/K4_k5_lineageflow_hmmer/REPRODUCIBILITY_RECIPE.md` — the
  self-referential `SHA256SUMS` row was deleted and the surrounding sentence
  now says "run it rather than comparing a pinned hash of the ledger itself",
  with the count corrected from "All 44 listed files pass" to "43 OK and one
  expected self-line".

No number in the paper moved: these are integrity pins on files whose contents
were already correct.

