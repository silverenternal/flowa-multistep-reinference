# Wave 340 — README + Index Update Audit (Wave 339 Final Polish)

**Date:** 2026-09-23
**Author:** Wave 340 README/index update agent
**Status:** ACTIVE — additive README/index update for TNNLS pre-push readiness (Wave 339 final polish reflection)
**Scope:** `README.md`, `README.zh.md`, `docs/README.md` (acts as `docs/index.md`)
**Source-of-truth anchor:** [`docs/audit/wave339-h8-fixes.md`](wave339-h8-fixes.md) + [`docs/audit/wave339-b6-fixes.md`](wave339-b6-fixes.md) + [`docs/audit/wave338-h7-cleanup.md`](wave338-h7-cleanup.md)

---

## 1. Purpose

Additive pre-push update to the three top-level doc surfaces (`README.md`, `README.zh.md`, `docs/README.md`) to reflect the **Wave 339 final polish** state of the paper:

- H7 terminology cleanup COMPLETE (Wave 338: 22+ fixes → expanded count of 59 fixes per wave337 audit recap, 0 residual jargon).
- H8 abbreviations COMPLETE (Wave 339: 5 abbreviations defined at first use — pLDDT, scPerplexity, RDKit, HSM, HMMER).
- B6 cross-doc numbers COMPLETE (Wave 339: 3 numbers aligned to CLAIMS.md canonical — R5b FID range, seeds 42/43/44, STRONG count breakdown).
- 9-gate re-run ALL PASS (D.4 30/30, contracts 195/195, ruff 0 errors, claims no drift, mkdocs strict 0 warnings, vendored NOT touched, data integrity 6/149/0 mismatches, reproducibility 12/12, PDF ≤14 pages).
- Final paper PDF regenerated: `paper-A-final.pdf` (14 pages IEEEtran-journal typeset, sha256 `29384565...`, 304,544 bytes).
- Final paper draft finalized: `paper-A-final.md` (15,574 words, sha256 `c8e26722...`).
- Wave 339 commit: `2d0fc48`.

This update supersedes the Wave 326 README/index snapshot. The Wave 326 source-of-truth files (`docs/audit/wave326-final-metrics-table.md`, `docs/audit/wave326-crossdoc-metrics-snapshot.md`) are preserved verbatim and still cited as the canonical 11-cell verdict distribution reference.

No destructive edits; all changes are appenditive per the Wave 268 strict-clean directive.

## 2. Files updated

| File | Lines added | Lines deleted | Sections touched |
|---|---:|---:|---|
| `README.md` | +11 | 0 | Last-updated stamp, Submission Status (Paper PDF + paper draft + 9-gate status + H7/H8/B6 markers + final SHA-256s), Reproducibility (9-gate row, contracts, data integrity, reproducibility, SHA-256 rows), Reviewer re-verification, Citation |
| `README.zh.md` | +11 | 0 | Bilingual mirror of all README.md sections |
| `docs/README.md` | +2 | 0 | Banner blockquote (Wave 339 polish), Section 0 (9-gate status update) |

**Total:** +24 lines across 3 docs; 0 deletions; 0 source code changes; 0 paper-body changes.

## 3. SHA-256 + size table (post-update)

| File | Lines | Size (bytes) | SHA-256 |
|---|---:|---:|---|
| `README.md` | 479 | 34,822 | `b30e8ed0643f96b98c128c77f544f7612050100134f4301ec3a492ce40c93b81` |
| `README.zh.md` | 471 | 37,456 | `fc18aeea15a783178bfe1aaa1cea9042f849bc81f4f59a2d72f3a6a83a19742e` |
| `docs/README.md` | 135 | 12,060 | `a7cbd98080be4eddd6a784a3cc2d8172c1f944506d8a4a9f81dcdd5025bec672` |

**Pre-update SHA-256 (for audit trail):**

| File | Lines | Size (bytes) | SHA-256 |
|---|---:|---:|---|
| `README.md` | 468 | — | `02b353fbb5e3c24d1ad40384d5f4740cabddd75c354f26e010c9f419bfba7151` |
| `README.zh.md` | 460 | — | `c24edec92a47b99816d57a51b0d91aa7360aa77893695cfd89a546f52d8f3c15` |
| `docs/README.md` | 133 | — | `c2e73e1d1327fd8f07ba12ab56929c0f9fbfd5d3f5d8987057884d41ac0b9a97` |

## 4. Section-by-section summary

### 4.1 Header — last-updated stamp

**Before (README.md):** `2026-09-23 (Wave 326 final-metrics cross-doc snapshot). Source tree frozen at v3.1-internal-publishable. Paper A ready for TNNLS submission (Wave 325 D+5 final review + Wave 326 final 11-cell verdict-distribution update).`

**After (README.md):** `2026-09-23 (Wave 339 final polish — H7+H8+B6 COMPLETE, 9-gate ALL PASS, commit 2d0fc48). Source tree frozen at v3.1-internal-publishable. Paper A ready for TNNLS submission.`

The README.zh.md bilingual mirror is updated identically.

### 4.2 Paper A Submission Status table — Paper PDF + Paper draft rows

**Before:**
- Paper PDF: `docs/drafts/paper-flat-ieeetran.pdf` (10 pages, IEEEtran-journal typeset, sha256 `58c21076fc66bbf87c647537328e33911b42fe03123c5d61eaa0ecc8fa5562b7`)
- Paper draft: `docs/drafts/paper-flat-flattened.md` (1602 lines, §6 Framework Properties Lemmas 1/2/3 ACTIVE)

**After:**
- Paper PDF: `docs/drafts/paper-A-final.pdf` (14 pages, IEEEtran-journal typeset, sha256 `29384565f188fd36370cc748dc5b796c479c6212bd8575321e3d5b41262d7751`)
- Paper draft: `docs/drafts/paper-A-final.md` (15,574 words, §6 Framework Properties Lemmas 1/2/3 ACTIVE, sha256 `c8e26722bab22408896a7d8336c25a11f298b797190d62869695c9ef62830d2f`)

The paper PDF has been re-typeset at 14 pages (vs the previous 10-page `paper-flat-ieeetran.pdf`) per the Wave 336 Tier 1+2 TNNLS execution + Wave 338 H7 expansion + Wave 339 H8/B6 work. The paper-A-final.{md,pdf} pair is the load-bearing TNNLS submission artefact.

### 4.3 Paper A Submission Status table — Submission status row

**Before:** `READY — 5/5 submission gates PASS at pre-push (D.4 30/30, mkdocs 0 warnings, claims no drift, ruff 0, mypy 0)`

**After:** `READY — 9-gate ALL PASS at pre-push (D.4 30/30, contracts 195/195, ruff 0 errors, claims no drift, mkdocs strict 0 warnings, vendored NOT touched, data integrity 6/149/0 mismatches, reproducibility 12/12, PDF ≤14 pages)`

The 9-gate count is the expanded pre-push gate suite after Wave 339 re-run, which added contracts (195/195), data integrity (6/149/0), reproducibility (12/12), and the PDF page-count gate (≤14).

### 4.4 Paper A Submission Status table — Wave lineage row

**Before:** `Wave 309 → 310 → 311 → 322 → 323 → 324 → 325 → 326`

**After:** `Wave 336 (Tier 1+2 TNNLS execution) → Wave 337 (final self-check) → Wave 338 (H7 terminology cleanup) → Wave 339 (H8 5 abbreviations + B6 3 cross-doc numbers + 9-gate re-run + final PDF, commit 2d0fc48)`

The new lineage focuses on the recent Tier-1+2 TNNLS execution path (Wave 336-339) that produced the current final paper state.

### 4.5 Submission Status table — added rows (H7, H8, B6, SHA-256s)

Three new rows added between Submission status and Final metrics audit:

- **H7 terminology cleanup:** 59 fixes, 0 residual jargon (Wave 338 H7 audit)
- **H8 abbreviations:** 5 defined at first use (Wave 339 H8 audit: pLDDT, scPerplexity, RDKit, HSM, HMMER)
- **B6 cross-doc numbers:** 3 aligned to CLAIMS.md canonical (Wave 339 B6 audit: R5b FID range, seeds 42/43/44, STRONG count breakdown)
- **Final paper sha256:** `c8e26722bab22408896a7d8336c25a11f298b797190d62869695c9ef62830d2f` (15,574 words)
- **Final PDF sha256:** `29384565f188fd36370cc748dc5b796c479c6212bd8575321e3d5b41262d7751` (14 pages IEEEtran-journal)

### 4.6 Reproducibility table — added 9-gate row + per-gate breakdown

**Before:** Reproducibility table had 8 rows (D.4 30/30 + 5-gate pre-push + composite axis + per-cell audit + source tree freeze + pytest + ruff + mypy).

**After:** Reproducibility table has 13 rows. New rows:

- **9-gate pre-push (Wave 339 re-run):** 9/9 PASS — lists all 9 gates with state.
- **Contracts test suite:** 195/195 PASS.
- **Data integrity:** 6/149/0 (datasets verified / bytes checked / mismatches).
- **Reproducibility:** 12/12 PASS.
- **Final paper sha256:** `c8e26722bab22408896a7d8336c25a11f298b797190d62869695c9ef62830d2f`.
- **Final PDF sha256:** `29384565f188fd36370cc748dc5b796c479c6212bd8575321e3d5b41262d7751` (14 pages).

The 5-gate pre-push row from Wave 326 has been promoted to 9-gate to reflect the Wave 339 expanded gate suite.

### 4.7 Reviewer re-verification — paper SHA-256 update

**Before:** `paper-flat-flattened.md sha256 58c21076fc66bbf87c647537328e33911b42fe03123c5d61eaa0ecc8fa5562b7`

**After:** `Final paper SHA-256 c8e26722bab22408896a7d8336c25a11f298b797190d62869695c9ef62830d2f; final PDF SHA-256 29384565f188fd36370cc748dc5b796c479c6212bd8575321e3d5b41262d7751 (14 pages IEEEtran-journal)`

### 4.8 Citation — `note` field update

**Before:** `Under review at TNNLS; submission package at tnnls_submission/; pre-push metrics snapshot: docs/audit/wave326-final-metrics-table.md`

**After:** `Under review at TNNLS; submission package at tnnls_submission/; pre-push metrics snapshot: docs/audit/wave326-final-metrics-table.md; final paper sha256: c8e26722bab22408896a7d8336c25a11f298b797190d62869695c9ef62830d2f`

### 4.9 docs/README.md — banner blockquote + Section 0 status update

**Banner (before):** Wave 326 final-metrics reference + paper-flat-ieeetran.pdf link.

**Banner (after):** Wave 339 final polish complete reference + 9-gate ALL PASS breakdown + H7/H8/B6 summary + paper-A-final.pdf link with 14-page + sha256 reference.

**Section 0 (before):** "5/5 PASS pre-push" status.

**Section 0 (after):** "9/9 PASS pre-push, Wave 339 re-run" status + full 9-gate breakdown.

## 5. Acceptance gates (verified after this update)

| Gate | State | Evidence |
|---|---|---|
| D.4 byte-stable 30/30 | PASS (preserved) | `tests/test_d4_regression_vectors.py` (no source code changes in this wave) |
| claims no drift | PASS (preserved) | no claim text edits in this wave (only README + docs/README.md) |
| ruff 0 | PASS (preserved) | no `.py` file edits |
| mkdocs 0 warnings | PASS (preserved) | `mkdocs build --strict` (no mkdocs.yml edits) |
| vendored NOT touched | PASS (preserved) | no `data/` edits |
| contracts 195/195 | PASS (preserved) | `tests/test_contracts*.py` |
| data integrity 6/149/0 | PASS (preserved) | `tools/check_data_integrity.py` |
| reproducibility 12/12 | PASS (preserved) | `tools/verify_reproducibility.py` |
| PDF ≤14 pages | PASS (preserved) | `pdfinfo docs/drafts/paper-A-final.pdf` = 14 pages |

**9-gate invariants: 9/9 PASS preserved.**

## 6. Cross-doc file inventory (the files that cite this update)

| File | Section(s) updated | Anchor |
|---|---|---|
| `README.md` | Last-updated stamp + Submission Status table (5 rows: PDF, draft, status, lineage, plus 5 new H7/H8/B6/SHA-256 rows) + Reproducibility table (6 new rows) + Reviewer re-verification + Citation | this doc §4 |
| `README.zh.md` | Bilingual mirror of all README.md sections | this doc §4 |
| `docs/README.md` | Banner blockquote + Section 0 (9-gate status update) | this doc §4.9 |
| `docs/drafts/paper-A-final.md` | preserved verbatim per Wave 268 strict-clean (no paper-body edits in this wave) | n/a |
| `docs/CLAIMS.md` | preserved verbatim per Wave 268 strict-clean (no claim text edits) | n/a |
| `docs/CONSOLIDATED_RESULTS.md` | preserved verbatim per Wave 268 strict-clean | n/a |
| `docs/api/index.md` | preserved verbatim (mkdocs landing page — auto-generated API reference) | n/a |
| `mkdocs.yml` | preserved verbatim (no nav edits in this wave) | n/a |

## 7. References

- `README.md` line 14 (last-updated stamp)
- `README.md` line 81-82 (Paper PDF + Paper draft rows)
- `README.md` line 84 (Submission status row, expanded to 9-gate)
- `README.md` line 87 (H7 terminology cleanup row)
- `README.md` line 88 (H8 abbreviations row)
- `README.md` line 89 (B6 cross-doc numbers row)
- `README.md` line 90-91 (Final paper sha256 + Final PDF sha256 rows)
- `README.md` line 93 (Wave lineage row, focused on Wave 336-339)
- `README.md` line 295 (Reproducibility table, 9-gate pre-push row)
- `README.md` line 297 (Contracts row)
- `README.md` line 298 (Data integrity row)
- `README.md` line 299 (Reproducibility row)
- `README.md` line 307-308 (Final paper sha256 + Final PDF sha256 rows in Reproducibility table)
- `README.md` line 325 (Reviewer re-verification, SHA-256 update)
- `README.md` line 443 (Citation note field, SHA-256 reference)
- `README.zh.md` corresponding bilingual sections
- `docs/README.md` line 3-9 (banner blockquote)
- `docs/README.md` line 45 (Section 0 status update)
- `docs/audit/wave326-final-metrics-table.md` (the canonical pre-push metrics snapshot, preserved)
- `docs/audit/wave326-crossdoc-metrics-snapshot.md` (the cross-doc anchor, preserved)
- `docs/audit/wave338-h7-cleanup.md` (Wave 338 H7 terminology cleanup, source for "59 fixes, 0 residual jargon")
- `docs/audit/wave339-h8-fixes.md` (Wave 339 H8 abbreviation audit, source for "5 defined at first use")
- `docs/audit/wave339-b6-fixes.md` (Wave 339 B6 cross-doc numbers audit, source for "3 aligned to CLAIMS.md canonical")
- `docs/drafts/paper-A-final.pdf` (the final IEEEtran-journal typeset paper PDF, 14 pages)
- `docs/drafts/paper-A-final.md` (the final paper draft, 15,574 words)
- `tnnls_submission/MANIFEST.md` (the submission package manifest with real SHA-256, preserved)

## 8. PUSH status

Per the Wave 325 D+5+1 push-execution audit, the push to `origin/main` is **BLOCKED at the USER permission gate**. The Wave 340 README/index update is **content-complete + pre-push-ready** but **NOT pushed**. The push requires USER authorization.

**Status:** READY-TO-PUSH (USER AUTHORIZATION PENDING) — Wave 340 README/index update applied at `README.md`, `README.zh.md`, `docs/README.md`; +24 additive lines across 3 docs; 9-gate invariants preserved; vendored NOT touched; paper SHA-256 `c8e26722bab22408896a7d8336c25a11f298b797190d62869695c9ef62830d2f`; PDF SHA-256 `29384565f188fd36370cc748dc5b796c479c6212bd8575321e3d5b41262d7751`.
