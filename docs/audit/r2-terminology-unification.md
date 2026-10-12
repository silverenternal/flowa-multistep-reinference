# R2 terminology unification — repo-wide "paired" → "index-matched two-sample" (pass #10)

**Date:** 2026-10-12
**Branch:** main
**Base commit:** `3d76f8a` (manuscript-consistency pass #9 — reviewer-facing R2 label change)
**Scope:** whole repository (user directive: **全库统一**)
**Verdict:** terminology-only; **no metric, claim number, status label, or verdict changed**

---

## 1. Purpose

Pass #9 (`3d76f8a`) relabelled the R2 Kanzi reconstruction-RMSD comparison from
"paired" to **"index-matched two-sample"** on the reviewer-facing surfaces only
(`paper-A-final.md` / `.tex` / `.pdf`, `paper-data/R2_kanzi_rmsd/*`, a `docs/CLAIMS.md`
addendum, and an additive `tnnls_submission/MANIFEST.md` note).

The user then directed **全库统一** — propagate the same corrected terminology across
the *whole* repository so that no active governance surface, audit record, ARCHIVE
snapshot, legacy draft, or submission-package file still describes R2's comparison as
a "paired" test. This audit records that propagation.

The substantive correction is unchanged from pass #9: the two R2 arms (baseline =
autoencoder round-trip of the real input record; framework = autoencoder round-trip of
the bridge-generated structure) are matched by record index for bookkeeping only and are
statistically independent (`corr ≈ +0.02`), so the R2 test is a two-sample test, not a
within-subject paired test. The index-matched `t`-test coincides with the unpaired Welch
test (`t = -3.11`, `p = 1.87 × 10⁻³`; index-matched `t = -3.13`, `p = 1.79 × 10⁻³`).

---

## 2. Observed facts

| Item | Value |
|---|---|
| Base commit | `3d76f8a` |
| Files changed | **107** (358 insertions / 356 deletions) |
| Canonical R2 headline (unchanged) | `d_z = -0.0990`, `p_raw = 1.7943 × 10⁻³`, Bonferroni-significant at R-level α = 0.007143, **STRONG framework-WINS** |
| Manuscript `paper-A-final.md` | `c6978764d498baa7390b3b7979f2d045407b40d1a7a1db14f80e2f1f919c0f3b` (213574 bytes) — **unchanged** |
| Manuscript `paper-A-final.tex` | `cd600246f5f5e715c2b640022ccb9c87de19a34c5399949323164f4abc284f73` (66156 bytes) — **unchanged** |
| Manuscript `paper-A-final.pdf` | `b3fd1c3e3d6c4714cd265e46010e45cbe912293d97214f07882a0a803c5e4ffd` (448996 bytes) — **unchanged** |
| `tnnls_submission/cover_letter.md` | `75834a709f5139194001dcdd0e02d0d1d9a0636fa07b86387ecb90192cd24332` (74060 bytes; was `2a438d7f…` / 74006 bytes) |

Change distribution:

| Area | Files |
|---|---|
| `docs/ARCHIVE/audit-by-wave/*` (historical snapshots) | 32 |
| `docs/audit/*` (active audit trail) | 27 (+ kanzi 3, engineering 3, stats_method 2, reproducibility 2) |
| `docs/*` root governance (`CLAIMS`, `CONSOLIDATED_RESULTS`, `METRIC_LEDGER`, `baseline-audit-report`, cover letters, drafts) | 8 |
| `docs/drafts/*` (legacy flattened drafts) | 7 |
| `todo/*` (`WAVES.md`, `SUBMISSION-GAP-CHECKLIST.md`) | 2 |
| `tnnls_submission/*` (`MANIFEST.md`, `cover_letter.md`, `supplementary_bundle/**`) | 4 |
| `paper-data/*`, `verification_outputs/*`, `README*.md`, `DATA_PRESENTATION*.md` | rest |

---

## 3. What was changed (and what was deliberately preserved)

**Changed** — every standalone "paired" token that describes the **R2 comparison**
(test type, design, effect size, sweep, per-record diff, SEM) in an R2 context:

- `paired t-test` / `paired t` / `paired-t` → `index-matched two-sample t-test` / `… t`
- `paired d_z` / `Cohen's d, paired` → `… (index-matched two-sample)`
- `paired N=1000` / `paired sweep` / `paired per-record` / `paired analysis` /
  `paired design` (in R2 context) → `index-matched two-sample …`
- `paired-t design` → `index-matched two-sample t design`

**Preserved (guarded, verified by scan)** — every "paired" that belongs to a
genuinely paired cell or to a schema/identifier:

| Class | Examples | Count (unchanged) |
|---|---|---|
| R1 LineageFlow HMMER paired | "R1 … N=1000 paired" | kept |
| R3 FlowMol3 `fg_dev` per-record paired | "R3 = per-record paired d_z on fg_dev" | kept |
| R6 pLDDT / k6 paired | "paired pLDDT", "paired foldability" | kept |
| K5 HMMER paired delta | "K5 paired delta" | kept |
| n=30 Track-B 4-arm design (CLM-057/062) | "n=30 paired", "4-arm n=30 paired", "synthetic protein axis … paired-t p < 1e-4" | kept |
| `within-subject` phrases | "within-subject d_z", "paired t-test on within-subject diffs" | 57 kept |
| Identifiers / paths | `n_paired`, `paired_n_records`, `paired_t_test`, `paired_diff`, `w196_p3_kanzi_paired_ttest.py`, `r2-kanzi-paired-restartblend`, `gap23-r2-paired-comparison-*` | kept |
| Data fields | JSON `"pairing": "paired"` (21), CSV `test_type` `,paired,` (3), bare `| paired |` pairing cells (31) | kept |
| Filenames | `wave196-p2-4arm-paired.json`, `paired-restartblend` | kept |

---

## 4. Over-reaches caught and reverted during the pass

An initial nearest-cell heuristic over-reached on three non-R2 contexts; all were
reverted before commit and re-verified to zero:

1. `docs/drafts/paper-flattened-draft.md` — the n=30 CLM-057 synthetic-axis line
   (`Bonferroni-corrected paired-t p < 1e-4`) is genuinely paired; kept.
2. `tnnls_submission/MANIFEST.md` — the pass-#9 note's own quote
   `not a within-subject "paired" test` describes the *old* label; kept verbatim.
3. `tnnls_submission/cover_letter.md` — `frozen paired differences` is the R6
   tier-aware counterfactual, not R2; kept.

Additional semantic fixes for readability: `a index-matched` → `an index-matched`;
`N=1000 index-matched two-sample sample` → `N=1000 sample`;
`tightly-index-matched two-sample` → `tightly index-matched`;
`(seed 42 index-matched two-sample)` → `(seed 42, index-matched two-sample)`;
`Both are index-matched two-sample design cells` → `Both are per-record effect-size cells`
(R3 is not index-matched).

---

## 5. SHA-256 ledger refresh

15 of the changed artifacts have their SHA-256 quoted in 12 referencing docs. Per the
user's authorization ("Include, refresh SHAs"), every quoted hash (and the adjacent
byte size in ledger tables) was refreshed:

`tnnls_submission/MANIFEST.md`, `paper-data/MANIFEST.md`,
`docs/drafts/ARCHIVE_INDEX.md`, `docs/audit/wave326-final-metrics-table.md`,
`wave326-readme-update.md`, `wave330-zh-review-version.md`, `wave340-readme-update.md`,
`wave356-archive-cleanup.md`, `wave363-all-cell-recipes.md`, `cover-letter-fill-draft.md`,
`repo-docs-maintenance-2.md`, `readiness-verifier-repoint.md`.

Post-refresh scan for stale references (full 64-char / 16 / 12 / 8-char prefixes of the
pre-change hashes): **0 remaining**. The manuscript `.md` / `.tex` / `.pdf` hashes are
unchanged (the manuscript was already correct at pass #9).

---

## 6. Guardrail compliance

| Guardrail (AGENTS.md §3) | Status |
|---|---|
| #1 vendored upstream byte-identical | ✅ untouched (no `data/` file in the change set) |
| #2 additive is the rule | ✅ documented; the only non-additive edits are the terminology token swaps themselves (wording-only, no numbers) |
| #3 NO-PUSH | ✅ commit only |
| #4 honest uncertainty — reframe wording, not numbers | ✅ no number, status, or verdict moved |
| #5 TNNLS freeze — numbers must not move; SHA-256s regenerated | ✅ numbers unchanged; the submission-package SHA ledger (`MANIFEST.md`) regenerated; user explicitly authorized including `tnnls_submission/cover_letter.md` content |
| #6 per-increment audit doc | ✅ this file |
| #7 stricter = cleaner | ✅ single curated script, data-field guards, byte-identical MANIFEST until the intentional additive note |

---

## 7. Verification

| Gate | Result |
|---|---|
| `python3 tools/check_claims_consistency.py` | No drift detected |
| `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed |
| `ruff check` | All checks passed |
| `mkdocs build --strict` | exit 0, 0 warnings |
| `reproduce/09_verify_all_cell_recipes.sh` | 11/11 paper cells verified |
| stale-SHA scan | 0 remaining |
| half-changed R2 scan | 0 remaining |
| n=30 / R3 / fg_dev over-reach scan | 0 remaining |

---

## 8. Unresolved / noted

- Two **historical prose** size references to changed files remain intentionally
  un-updated because they are snapshots of a past state, not current ledgers:
  `docs/audit/wave345-cross-doc-fixes.md:563` ("92017 bytes per `ls -la`", Wave 345) and
  `docs/audit/cover-letter-fill-draft.md:51` ("74223 → 74006", a past-fix record).
- The two historical R2 recipe audits (`docs/audit/wave363-r2-recipe.md`,
  `docs/audit/wave366-p2-reproducibility-manifest.md`) are **not** frozen-label
  exceptions here — they are part of the unified change set; only their quoted SHA-256
  readings elsewhere were refreshed.
