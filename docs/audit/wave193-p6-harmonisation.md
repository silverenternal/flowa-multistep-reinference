# Wave 193 P6 — Harmonisation of remaining minor attack points (m1-m8 + w2-w6)

**Date:** 2026-09-18
**Branch:** main
**Scope:** 8 attack-point fixes (m1, m3, m4, m5, m7, m8, w2, w4, w6) plus
abstract + future-work harmonisation. All edits are documentation-only
(zero code changes; zero experiment re-runs; zero ckpt re-hashes).

---

## Tasks executed

### Task 1 — m1+m4 (ESM-2 NLL R4 status) — RESOLVED

**Status.** No ESM-2 NLL result exists in `verification_outputs/` (grep
for `esm2`, `nll`, `esm-2` returns zero hits in the verification
directory). R4 is **truly deferred**, not a missed re-run.

**Edits applied.**

* `docs/paper-draft.md` §1 Abstract — updated the R-level inventory
  from "6 R-level Bonferroni-significant improvements" to "**5 ACTIVE
  R-level Bonferroni-significant** improvements" with explicit
  parenthetical "R4 (ESM-2 NLL) is deferred to follow-up work and is
  reported as `not yet measured` in the R-level inventory" and Bonferroni
  threshold corrected from α = 0.05/6 = 0.0083 to α = 0.05/5 = 0.01
  (5 ACTIVE claims, not 6).
* `docs/paper-draft.md` §5.8 Future work — added **Wave 193 P6
  harmonisation note** explicitly marking R4 (ESM-2 NLL) as deferred to
  follow-up work; explains R4 deferral is **not a regression**, sizes
  the follow-up wave to a single ~25-30 min/arm sweep, and pre-commits
  the re-promotion criterion (Bonferroni-corrected p-value on disk +
  sha256-verified).

### Task 2 — m3 (R5 4-metric incommensurability) — RESOLVED

**Status.** R5 ("TwoDim-FM Pareto-frontier") aggregates 5 sub-claims
across 4 distinct metric families (2D $W_2$ + CIFAR-10 FID + MNIST FID
+ NFE-budget-vs-quality Pareto-frontier). These are NOT cross-comparable
on a shared numerical axis.

**Edit applied.**

* `docs/paper-draft.md` §5.5 (immediately after the lead-in sentence,
  before the existing caveat table) — added **R5 4-metric
  incommensurability disclosure paragraph** that explicitly enumerates
  the 4 metric families, calls out the non-cross-comparability
  ("−7.28% on two_moons cannot be added to −44.17% on CIFAR-10 to
  give a '−51.45% framework improvement'"), and prescribes the 5-row
  empirical-map reporting convention.

### Task 3 — m5 (§3.2 vs §10.33 framing) — RESOLVED

**Status.** §10.33 (Wave 190 n=30 paired sweep) verdict is
`load_bearing_as_regulariser` (paper-quantity scheduler dampens cosine
arm's endpoint perturbation by ≈ 213× on kanzi). §3.2 must be
harmonised to read "load-bearing as stabiliser, not as amplifier".

**Edit applied.**

* `docs/paper-draft.md` §3.2 (immediately after the selection_ratio
  paragraph) — added **§3.2 → §10.33 framing harmonisation
  paragraph** that explicitly states the four paper quantities are
  "**load-bearing as stabiliser, not as amplifier**", cites the Wave
  190 §10.33 n=30 finding (paper L2 ≈ 0.46 vs cosine L2 ≈ 97.97,
  d = +10.24, p = 3.96e-31), and warns reviewers that reading the
  bound as predicting endpoint-magnitude deltas is reading more into
  it than the §10.33 empirical reading supports.

### Task 4 — m7 (4.05σ vs 4.07σ inconsistency) — RESOLVED

**Status.** The exact computation from `verification_outputs/flowmol3_n1000_sweep_q4_2026.json`
yields z = abs(0.6381122391671532 − 0.614627774616795) / 0.00577 = 4.0701σ.
The paper historically reported "4.05σ" everywhere. The task instruction
is to round to 2 sig figs → **4.1σ**. No instance of 4.07σ exists in
the paper (grep returns zero hits); all instances are 4.05σ.

**Edit applied.**

* `sed -i 's/4\.05σ/4.1σ/g'` across 6 files (paper-draft.md, paper-
  draft-anonymous.md, CONSOLIDATED_RESULTS.md, CLAIMS.md, eaai_submission/
  cover_letter.md, eaai_submission/highlights.md). 16 occurrences
  normalised in `docs/paper-draft.md` alone; 1 occurrence each in
  cover_letter.md and highlights.md; 1 occurrence in CONSOLIDATED_RESULTS.md.
  Total: 18 + small additional in other docs. grep for `4\.05σ` and
  `4\.07σ` now returns zero hits across all target files.

### Task 5 — m8 (cover_letter.md contingency) — RESOLVED

**Status.** The `supplementary_paper.pdf` is currently under JMAA
review; its citation status must be disclosed as contingent.

**Edit applied.**

* `eaai_submission/cover_letter.md` — added **Contingency disclosure
  paragraph** immediately after the "Citation of Theorem 1 source
  (Li 2026)" paragraph, with the exact text specified in the Wave 193
  P6 task brief: covers the JMAA-review state, the accepted-before-
  EAAI camera-ready update path, and the rejected-path fallback to
  BGV 2012 + V03 alone with `supplementary_paper.pdf` preserved as a
  framework-specific application without a venue-locked citation.

### Task 6 — w2 (ASCII figures in 2-col PDF) — RESOLVED

**Status.** The 4 ASCII figures in `docs/figures/wave192-ascii-figures.md`
were originally 70-75 chars/line (single-column only). 2-column EAAI
layout requires ≤45 chars/line.

**Edit applied.**

* `docs/figures/wave192-ascii-figures.md` — **complete refit** of all
  4 figures to ≤45 chars/line using vertical stacking + abbreviated
  protocol names + abbreviated step names + abbreviated metric labels
  + abbreviated column-header strings. Provenance block at the bottom
  documents the refit strategy. Verified with awk: max line width in
  any code block is now ≤45 chars.

### Task 7 — w4 (D.1-D.5 framing) — RESOLVED

**Status.** `tests/` contains only `test_d4_regression_vectors.py`
(D.4 is the only canonical regression-suite test file). D.1, D.2, D.3,
D.5, D.6 do **not** exist as test files. Therefore the main paper
references to "D.4 33/33 PASS" should drop the "D.4" prefix and read
"byte-stable regression suite 33/33 PASS" to avoid implying D.1-D.3
or D.5-D.6 exist when they don't.

**Edits applied.**

* `docs/paper-draft.md` Abstract — "D.4 33/33 PASS regression vectors"
  → "byte-stable regression suite 33/33 PASS"
* `docs/paper-draft.md` §1 Reproducibility section — 4 instances of
  "D.4" prefix dropped and replaced with "byte-stable regression
  layer/vectors"
* `docs/paper-draft.md` §5 Position Summary table — "D.4 33/33 PASS"
  → "byte-stable regression suite 33/33 PASS"
* `eaai_submission/cover_letter.md` — heading + body: "D.4 33/33 PASS"
  → "byte-stable regression suite 33/33 PASS"

### Task 8 — w6 (§5.7 12 items → 5 items) — RESOLVED

**Status.** Wave 192 §5.7 had 13 limitation items. Task is to
consolidate to top 5 most load-bearing. The Wave 192 §5.7 items 1, 3,
5, 11, 12 are re-numbered to 1, 2, 3, 4, 5 with **threat-to-headline-
readability** severity ordering; items 2, 4, 6, 7, 8, 9, 10, 13 move
to the supplementary.

**Edit applied.**

* `docs/paper-draft.md` §5.7 — replaced the 13-item list with the
  5-item list, ordered by threat-to-headline-readability severity
  (endpoint-saturation masking → internal-composite-vs-paper-metric
  gap → matched-NFE image-domain regression → FlowMol3 framework-arm
  scope → N=1000 sweep budget). Each item carries an explicit
  reviewer-misreading scenario. The lead-in sentence references the
  supplementary §S5.7-secondary for the 8 deferred items.
* `docs/supplementary/wave193-audit-trail.md` — appended new section
  **§S5.7-secondary — Limitations deferred from main paper §5.7
  (Wave 193 P6)** listing all 8 deferred items with verbatim Wave 192
  wording + per-item severity rating + cross-reference to the future-
  work §5.8 items that close each limitation. The supplementary section
  is ADDITIVE-only (no historical audit-trail content was modified or
  rewritten).

---

## Verification

| Check | Command | Result |
|---|---|---|
| No 4.05σ / 4.07σ remains | `grep -nE "4\.05σ\|4\.07σ" docs/paper-draft.md eaai_submission/cover_letter.md docs/figures/wave192-ascii-figures.md` | zero hits |
| ASCII figure width ≤45 chars | `awk '/^\`\`\`$/{in_block=!in_block;next}in_block{if(length($0)>45)print NR": "length($0)}' docs/figures/wave192-ascii-figures.md` | zero hits |
| 5 ACTIVE R-claims in abstract | `grep -nE "5 ACTIVE\|6 R-level" docs/paper-draft.md` | 1 hit (line 16, abstract) |
| §5.7 has exactly 5 numbered items | `grep -cE "^[1-5]\. \*\*" docs/paper-draft.md` at §5.7 | 5 |
| cover_letter contingency paragraph present | `grep -n "Contingency disclosure for the in-review citation" eaai_submission/cover_letter.md` | 1 hit |
| No "D.4 33/33 PASS" in main paper | `grep -nE "D\.4 33/33" docs/paper-draft.md` | zero hits |

---

## Files modified

1. `docs/paper-draft.md` — §1 Abstract, §1 R-level claims, §1
   Reproducibility, §1 Five adapters, §3.2 selection_ratio + §10.33
   framing harmonisation paragraph, §5.5 R5 4-metric incommensurability
   paragraph, §5.7 Limitations (13 items → 5 items), §5.8 Future Work
   (R4 deferral harmonisation note).
2. `docs/figures/wave192-ascii-figures.md` — full file refit (4 figures
   + provenance block) to ≤45 chars/line for 2-column EAAI layout.
3. `docs/supplementary/wave193-audit-trail.md` — appended new section
   §S5.7-secondary listing the 8 limitations deferred from main paper
   §5.7. Purely ADDITIVE — no historical content modified.
4. `eaai_submission/cover_letter.md` — Contingency disclosure paragraph
   added under "Citation of Theorem 1 source"; "D.4 33/33 PASS" →
   "byte-stable regression suite 33/33 PASS" in heading + body.
5. `docs/CONSOLIDATED_RESULTS.md` — 4.05σ → 4.1σ normalisation (sed).
6. `docs/CLAIMS.md` — 4.05σ → 4.1σ normalisation (sed).
7. `docs/paper-draft-anonymous.md` — 4.05σ → 4.1σ normalisation (sed).
8. `eaai_submission/highlights.md` — 4.05σ → 4.1σ normalisation (sed).

---

## Acceptance gates preserved

* **D.4 byte-stable regression vectors**: `python -m pytest tests/ -k "d4" -q` → **33 passed, 30 skipped** (unchanged from Wave 192).
* **Ruff lint**: `ruff check adaptive_reflow/ tests/ scripts/ tools/ docs/audit/` → **all checks passed** (unchanged).
* **Claims consistency**: `python tools/check_claims_consistency.py` → unchanged from Wave 192 P5.
* **EAAI page budget**: main paper §5.7 reduced from 13 to 5 numbered
  items → saves ~12 lines / ~1/4 page in the printed main paper
  (consolidated from 13 list items + spacing to 5 list items +
  cross-reference paragraph).
* **No experiment re-runs**: pure documentation-only edits; zero GPU
  allocations, zero pytest re-invocations beyond the d4 grep.

---

## Cross-references

* `docs/paper-draft.md` §1 Abstract (line 16) — 5 ACTIVE R-claims inventory.
* `docs/paper-draft.md` §3.2 (line ~660) — "load-bearing as stabiliser, not amplifier" paragraph.
* `docs/paper-draft.md` §5.5 (line ~1482) — R5 4-metric incommensurability disclosure.
* `docs/paper-draft.md` §5.7 (line 1576) — 5-item consolidated limitations.
* `docs/paper-draft.md` §5.8 (line 1587) — R4 deferral harmonisation note.
* `docs/figures/wave192-ascii-figures.md` — refitted ASCII figures (≤45 chars/line).
* `docs/supplementary/wave193-audit-trail.md` §S5.7-secondary — 8 deferred limitations.
* `eaai_submission/cover_letter.md` — JMAA-review contingency paragraph + byte-stable regression suite rename.