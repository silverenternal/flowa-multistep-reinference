# Wave 151 P5 — Headline Evidence Cross-Link Audit

**Date:** 2026-09-14
**Wave:** 151 Agent 5 (headline-evidence cross-link verification)
**Commit baseline:** `9fca231` (HEAD at start of Wave 151 P5)
**Scope:** verify that every `SOURCE.md` / `source_audit*.md` in
`docs/headline-evidence/` (R1-R6) resolves to existing files + carries
correct headline numbers; flag any MISSING/STALE/BROKEN_LINK.
**Constraint:** ADDITIVE only. NO destructive edits to headline-evidence
SOURCE.md text. ADDITIVE append-note fixes where needed.

---

## TL;DR

| R | Directory | source_audit | SOURCE.md | Sweep JSON | Numbers | Verdict |
|---|---|---|---|---|---|---|
| R1 | `r1_lineageflow_hmmer_p1e-10/` | OK (symlink → ARCHIVE) | OK (+ BROKEN_LINK notes appended) | n/a (honest disclosure) | 158 → 342 +116% p<1e-10 OK | **OK** (after ADDITIVE note) |
| R2 | `r2_flowmol3_fgdev_4p05sigma/` | MISSING (no source_audit.md, SOURCE.md sufficient) | OK (+ BROKEN_LINK note appended) | 6/6 sweep JSONs OK | 0.6381 → 0.6146 OK | **OK** (after ADDITIVE note) |
| R3 | `r3_cifar_rf_v2_fid_m44p17pct/` | MISSING (no source_audit.md, SOURCE.md sufficient) | OK (+ STALE note appended) | n/a (honest disclosure) | 218.87 → 122.18 -44.17% OK | **OK** (after ADDITIVE note) |
| R4 | `r4_2d_two_moons_w2_m7p28pct/` | OK (symlink → r4-survey) | OK | 2/2 CSV symlinks OK | 0.5029 → 0.4663 -7.28% OK | **OK** |
| R5 | `r5_2d_eight_gaussians_w2_m10p40pct/` | OK (symlink → r4-survey) | OK (+ STALE note appended) | 2/2 CSV symlinks OK | 0.6606 → 0.5919 -10.40% per source_audit (R5 SOURCE.md shows STALE 0.5579/0.4999) | **OK** (after ADDITIVE note) |
| R6 | `r6_mnist_fm_fid_m15p01pct/` | OK (symlink → ARCHIVE) | OK (+ BROKEN_LINK note appended) | 1/1 JSON symlink OK | 409.18 → 347.75 -15.01% OK | **OK** (after ADDITIVE note) |

**Headline numbers all match the README.md Tier-1 source-of-truth table** at
`docs/headline-evidence/README.md` lines 17-22. The headline evidence
package is internally consistent (after the ADDITIVE append-notes below).

---

## 1. Per-R.N status

### R1 — LineageFlow `hmmscan_total_hits` +116%

- **Directory:** `docs/headline-evidence/r1_lineageflow_hmmer_p1e-10/`
- **source_audit_doc.md:** symlink → `docs/ARCHIVE/audit-waves-1-99/wave86-phase3-sweep.md` (resolves)
- **SOURCE.md:** exists, cites +116% (158 → 342, p<1e-10) which matches the
  source-of-truth audit doc §2 and `docs/headline-evidence/README.md` line 17
- **Sweep JSONs:** none on-disk (honestly disclosed in SOURCE.md §"Provenance";
  raw Wave 86 sweep output was never archived to repo; this is a known
  Wave 135 caveat per `docs/audit/wave135-headline-evidence.md` §"Honest caveats")
- **Findings:**
  - BROKEN_LINK in SOURCE.md prose text references
    `docs/audit/wave86-phase3-sweep.md`,
    `docs/audit/wave81-phase4-final.md`, and
    `docs/audit/wave86-phase1-audit.md`. These files were archived to
    `docs/ARCHIVE/audit-waves-1-99/` in Wave 137 (commit `3f4a09e`);
    the inline SOURCE.md text references were not updated.
  - The actual `source_audit_doc.md` symlink correctly points to the
    ARCHIVE path, so the directory-level discovery works.
- **Verdict:** **OK after ADDITIVE fix** (append a "Post-Wave-137 ARCHIVE
  relocation note" section to the end of R1 SOURCE.md pointing to the
  canonical ARCHIVE paths). No destructive edit to existing prose.

### R2 — FlowMol3 `fg_dev` 4.05σ

- **Directory:** `docs/headline-evidence/r2_flowmol3_fgdev_4p05sigma/`
- **source_audit.md:** **MISSING** (no `source_audit.md` in this directory)
- **SOURCE.md:** exists, cites -0.0235 (0.6381 → 0.6146) which matches
  `docs/headline-evidence/README.md` line 18 + the sweep JSONs
- **Sweep JSONs:** 6/6 symlinks resolve:
  - `flowmol3_n1000_sweep_q4_2026.json` ✓
  - `flowmol3_n1000_sweep_wave87_q4_2026.json` ✓
  - `flowmol3_n1000_baseline_q4_2026.json` ✓
  - `flowmol3_n1000_framework_q4_2026.json` ✓
  - `flowmol3_n1000_baseline_wave87_q4_2026.json` ✓
  - `flowmol3_n1000_framework_wave87_q4_2026.json` ✓
- **Findings:**
  - MISSING source_audit.md: R2 has no `source_audit.md` file. The
    SOURCE.md is self-sufficient because it cites all 6 sweep JSONs by
    name. Per the Wave 135 audit (`docs/audit/wave135-headline-evidence.md`
    §"What was created"), R2 was a "Phase 3" deliverable that intentionally
    relied on the JSON symlinks instead of a separate audit doc.
  - BROKEN_LINK in SOURCE.md prose text reference
    `docs/audit/wave89-phase1-final.md` (also archived in Wave 137).
- **Verdict:** **OK after ADDITIVE fix** (append a "Post-Wave-137 ARCHIVE
  relocation note" section to the end of R2 SOURCE.md pointing to the
  canonical ARCHIVE path for the Wave 89 audit doc). No destructive edit.

### R3 — CIFAR-10 RF v2 FID -44.17%

- **Directory:** `docs/headline-evidence/r3_cifar_rf_v2_fid_m44p17pct/`
- **source_audit.md:** **MISSING** (no `source_audit.md` in this directory)
- **SOURCE.md:** exists, cites 218.87 → 122.18 (-44.17%) which matches
  `docs/headline-evidence/README.md` line 19 + `docs/CONSOLIDATED_RESULTS.md`
  line 177 (v2 row)
- **Sweep JSONs:** none on-disk (honestly disclosed in SOURCE.md;
  Wave 135 caveat per `docs/audit/wave135-headline-evidence.md` §"Honest caveats")
- **Findings:**
  - MISSING source_audit.md: R3 has no `source_audit.md` file. The
    SOURCE.md is self-sufficient because it cites the v2 row of
    `docs/CONSOLIDATED_RESULTS.md` by line number.
  - STALE section reference: SOURCE.md says "Source-of-truth:
    docs/CONSOLIDATED_RESULTS.md §4.3" but the actual v2 row lives
    at **§6** (line 174-195), not §4.3. §4.3 is the load-bearing
    test of the 2D FM ablation, NOT the CIFAR-10 RF v2 row. Both
    R3 numbers (218.87 → 122.18 -44.17%) DO appear in §6 line 177,
    which matches the SOURCE.md headline.
- **Verdict:** **OK after ADDITIVE fix** (append a "Section pointer
  correction" note to the end of R3 SOURCE.md clarifying that the v2
  row lives at §6 line 177, not §4.3). No destructive edit.

### R4 — 2D Two Moons W2 -7.28%

- **Directory:** `docs/headline-evidence/r4_2d_two_moons_w2_m7p28pct/`
- **source_audit.md:** symlink → `docs/r4-survey/10-sota-2d-experiment-results.md`
  (resolves; file exists)
- **SOURCE.md:** exists, cites 0.5029 → 0.4663 (-7.28%) which matches
  `docs/headline-evidence/README.md` line 20 + the source_audit.md
  per-target table (line 17) + `verification_outputs/g1_deep_dive_q3_2026.json`
  (lines 45-46)
- **Sweep CSVs:** 2/2 symlinks resolve:
  - `noise_injection_two_moons_baseline.csv` ✓
  - `noise_injection_two_moons_framework.csv` ✓
- **Findings:** None. All references and numbers internally consistent.
- **Verdict:** **OK** — no fix needed.

### R5 — 2D Eight Gaussians W2 -10.40%

- **Directory:** `docs/headline-evidence/r5_2d_eight_gaussians_w2_m10p40pct/`
- **source_audit.md:** symlink → `docs/r4-survey/10-sota-2d-experiment-results.md`
  (resolves; file exists)
- **SOURCE.md:** exists; **STALE absolute numbers**
- **Sweep CSVs:** 2/2 symlinks resolve:
  - `noise_injection_eight_gaussians_baseline.csv` ✓
  - `noise_injection_eight_gaussians_framework.csv` ✓
- **Findings:**
  - **STALE:** R5 SOURCE.md headline says "baseline W2 = 0.5579,
    framework W2 = 0.4999" but the canonical numbers per source_audit.md
    (line 32, line 55), per `docs/headline-evidence/README.md` line 21,
    and per `verification_outputs/g1_deep_dive_q3_2026.json` lines 60-61
    are **0.6606 → 0.5919**. Both ratios compute to -10.40% so the
    percentage is correct, but the absolute values in R5 SOURCE.md are
    stale. The stale numbers 0.5579/0.4999 appear ONLY in this file
    (verified via `grep -rn '0.5579\|0.4999'` across `docs/` and
    `verification_outputs/`); no other doc carries these stale values,
    so there is no downstream propagation risk.
- **Verdict:** **OK after ADDITIVE fix** (append a "Canonical numbers
  reconciliation" note to the end of R5 SOURCE.md clarifying that the
  source-of-truth (source_audit.md + README.md + g1_deep_dive JSON)
  shows 0.6606 → 0.5919 = -10.40%; the SOURCE.md headline numbers
  0.5579/0.4999 also compute to -10.40% but are stale absolute values
  from a pre-canonical snapshot). No destructive edit.

### R6 — MNIST FM FID -15.01%

- **Directory:** `docs/headline-evidence/r6_mnist_fm_fid_m15p01pct/`
- **source_audit.md:** symlink → `docs/ARCHIVE/audit-waves-1-99/wave41-paper-audit.md`
  (resolves; file exists; FID numbers at line 204)
- **SOURCE.md:** exists, cites 409.18 → 347.75 (-15.01%) which matches
  `docs/headline-evidence/README.md` line 22 + source_audit.md line 204
  + `docs/CONSOLIDATED_RESULTS.md` line 292 (parity row) and line 298
  (Wave 28 re-measurement row)
- **Sweep JSONs:** 1/1 symlink resolves:
  - `baseline_comparison_q4_2026.json` ✓ (contains Wave 52 baseline-vs-framework
    numbers; FID numbers cross-referenced in source_audit.md line 204)
- **Findings:**
  - BROKEN_LINK in SOURCE.md prose text reference
    `docs/audit/wave41-paper-audit.md:204` (archived in Wave 137 to
    `docs/ARCHIVE/audit-waves-1-99/wave41-paper-audit.md`).
  - The actual `source_audit.md` symlink correctly points to the
    ARCHIVE path, so directory-level discovery works.
- **Verdict:** **OK after ADDITIVE fix** (append a "Post-Wave-137
  ARCHIVE relocation note" to the end of R6 SOURCE.md). No destructive edit.

---

## 2. ADDITIVE fixes applied (this audit)

To honor the ADDITIVE-only constraint, the fix strategy was to APPEND
clarification sections to the end of each affected SOURCE.md rather than
modify existing prose. Each appended section is prefixed with a
"Post-Wave-151 P5 audit reconciliation note" header so future reviewers
know the provenance.

### Fixes applied (this commit)

| R | Fix applied | File | Additions |
|---|---|---|---|
| R1 | Append ARCHIVE relocation note pointing to `docs/ARCHIVE/audit-waves-1-99/wave86-phase3-sweep.md` (canonical) + ARCHIVE paths for wave81/wave86 references | `r1_lineageflow_hmmer_p1e-10/SOURCE.md` | +13 lines (APPEND only) |
| R2 | Append ARCHIVE relocation note pointing to `docs/ARCHIVE/audit-waves-1-99/wave89-phase1-final.md` (canonical) | `r2_flowmol3_fgdev_4p05sigma/SOURCE.md` | +11 lines (APPEND only) |
| R3 | Append section pointer correction note (v2 row is at §6 line 177, not §4.3) | `r3_cifar_rf_v2_fid_m44p17pct/SOURCE.md` | +11 lines (APPEND only) |
| R5 | Append canonical numbers reconciliation note (0.6606 → 0.5919 per source_audit/README/g1_deep_dive; SOURCE.md's 0.5579/0.4999 are stale absolute values that compute to the same -10.40%) | `r5_2d_eight_gaussians_w2_m10p40pct/SOURCE.md` | +13 lines (APPEND only) |
| R6 | Append ARCHIVE relocation note pointing to `docs/ARCHIVE/audit-waves-1-99/wave41-paper-audit.md` (canonical; FID numbers at line 204) | `r6_mnist_fm_fid_m15p01pct/SOURCE.md` | +11 lines (APPEND only) |

R4 has no findings — no fix needed.

**No source code changes, no destructive edits to existing prose,
no figures/tables removed, no measurement scope shift.**

---

## 3. Gates verified (this audit)

- **D.4 (regression vectors):** PASS — 72/72 tests pass per
  `PYTHONPATH=. python -m pytest tests/test_d4_regression_vectors.py
  tests/test_adapters/test_regression_vectors.py -q` (output:
  "72 passed, 3 warnings in 37.79s"; matches Wave 149/150 baseline).
- **claims_consistency:** PASS — "No drift detected." (39 active, 0
  provisional, 2 deprecated; matches Wave 149/150 baseline).
- **ruff 0:** PRESERVED (no source code changes).
- **mkdocs strict:** PRESERVED (no mkdocs config changes).

---

## 4. Wave 149-150 follow-up relevance

Wave 149-150 did not touch any R1-R6 headline number. R.38 in
`docs/baseline-audit-report.md` line 4678 (Wave 150 baseline row)
documents the Wave 149 follow-up close + K1 RC4 ablation CLI fix +
paper §10.4 K1 disclosure update + LineageFlow HMMER POC artefacts +
paper.pdf warning reduction 38→5. None of these touch the R1-R6
headline numbers (R1 +116%, R2 4.05σ, R3 -44.17%, R4 -7.28%, R5
-10.40%, R6 -15.01%). The headline numbers are byte-stable across
Waves 135-151 inclusive.

---

## 5. Wave 151 P5 acceptance

- All 6 R* headline evidence packages verified on-disk.
- 5 ADDITIVE fix notes appended to R1/R2/R3/R5/R6 SOURCE.md.
- 1 directory (R4) unchanged (no findings).
- D.4 72/72 PASS preserved.
- claims_consistency PASS preserved.
- ruff 0 preserved.
- mkdocs strict preserved.

**Verdict:** Headline evidence package is submission-ready. The
broken-link / stale-reference issues are bookkeeping-only (the
actual headline numbers and source symlinks all resolve correctly)
and are now explicitly documented in each affected SOURCE.md via
ADDITIVE append-notes that future reviewers will see immediately.

---

## Appendix: How to reproduce this audit

```bash
# Inventory
ls -la docs/headline-evidence/
ls docs/headline-evidence/r{1,2,3,4,5,6}_*/

# Per-R: verify source_audit + SOURCE.md + symlinks
for r in r{1,2,3,4,5,6}_*/; do
  echo "=== $r ==="
  ls -la docs/headline-evidence/$r/
done

# Verify sweep JSON/CSV symlinks resolve
find docs/headline-evidence -type l -exec readlink -f {} \; | sort -u

# Gates
PYTHONPATH=. python -m pytest tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py -q
python tools/check_claims_consistency.py
```

Co-Authored-By: Claude Code <noreply@anthropic.com>
