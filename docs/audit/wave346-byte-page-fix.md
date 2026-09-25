# Wave 346 — tnnls_submission/README.md Byte/Page Number Fix

**Date:** 2026-09-25
**Author:** Wave 346 governance agent (USER AUTHORIZED — README.md byte/page fix only)
**Status:** ACTIVE — additive governance fix
**Trigger:** `tnnls_submission/README.md` continued to carry the Wave 324 byte/page numbers (`10 pages, 381510 bytes`) describing the old `paper-flat-ieeetran.pdf` even after Wave 331 renamed the canonical manuscript to `paper-A-final.pdf` (and the new PDF was rebuilt in Wave 343/344 to its current 14 pages / 305270 bytes).
**Scope:** `tnnls_submission/README.md` (3 stale byte/page replacements across 3 sections: §0 file listing, §1.3 manuscript-compiles-cleanly check, §2.3 ScholarOne Step 3 upload instruction).
**Hard-rule compliance:** ADDITIVE ONLY (no number changes in any audit/CLAIMS doc, no destructive edits); per Wave 268 strict-clean rule, per Wave 325 NO-PUSH policy.
**Out of scope (deliberately):** `tnnls_submission/MANIFEST.md` row 22 SHA-256 column needs a re-hash to match the new `README.md` content — flagged as §6 open issue for a follow-up wave; this wave does not modify MANIFEST.md (matches the Wave 345 split: README.md Phase 1 + supplementary Phase 2 + MANIFEST SHA re-hash as a later bookkeeping step).

---

## 1. Executive Summary

`docs/drafts/paper-A-final.pdf` is the canonical manuscript and is currently **14 pages, 305270 bytes** (verified via `pdfinfo` + `ls -la` on 2026-09-25; see §3). The `tnnls_submission/README.md` ScholarOne upload walkthrough still described it as `10 pages, 381510 bytes` in three places — two of which (line 29 file-listing and line 56 pdfinfo expected output) are byte-precision instructions the corresponding author would copy-paste, and one (line 88 ScholarOne Step 3 upload instruction) is a page-count claim an Editorial Manager reviewer could spot.

This wave executes the smallest possible fix: 3 mechanical byte/page replacements in `tnnls_submission/README.md`, plus a fresh SHA-256 for the file. All 3 old strings matched unique contexts and were applied via the Edit tool (no destructive bulk replace). The MANIFEST.md SHA-256 ledger will need to be re-hashed in a follow-up wave (see §6 open issue).

---

## 2. Byte/Page Replacements (3 mechanical line-edits in tnnls_submission/README.md)

### 2.1 Pre-edit / Post-edit Counts

```
$ grep -c "10 pages" tnnls_submission/README.md
2
$ grep -c "381510 bytes" tnnls_submission/README.md
2
$ grep -c "14 pages" tnnls_submission/README.md
0
$ grep -c "305270 bytes" tnnls_submission/README.md
0
```

After Wave 346:

```
$ grep -c "10 pages" tnnls_submission/README.md
0
$ grep -c "381510 bytes" tnnls_submission/README.md
0
$ grep -c "14 pages" tnnls_submission/README.md
2
$ grep -c "305270 bytes" tnnls_submission/README.md
2
```

Net change: 2 stale `10 pages` references removed + 2 stale `381510 bytes` references removed → 2 fresh `14 pages` references + 2 fresh `305270 bytes` references added (line 88 has only the page count, not the byte count). Total line count preserved.

### 2.2 Per-occurrence Replacement Map

| # | Line (post-edit) | Section | old_string | new_string |
|---|---|---|---|---|
| 1 | 29 | §0 Where the package lives (file listing) | `docs/drafts/paper-A-final.pdf   ← 10 pages, 381510 bytes (Wave 324 D+5, ready-to-submit)` | `docs/drafts/paper-A-final.pdf   ← 14 pages, 305270 bytes (Wave 324 D+5, ready-to-submit)` |
| 2 | 56 | §1.3 Manuscript compiles cleanly (`pdfinfo` expected output) | `Expect: \`Pages: 10\`, \`File size: 381510 bytes\`.` | `Expect: \`Pages: 14\`, \`File size: 305270 bytes\`.` |
| 3 | 88 | §2.3 ScholarOne Step 3 (Manuscript File upload instruction) | `- Upload: **\`docs/drafts/paper-A-final.pdf\`** (10 pages, IEEEtran-journal typeset).` | `- Upload: **\`docs/drafts/paper-A-final.pdf\`** (14 pages, IEEEtran-journal typeset).` |

Each `old_string` was used as a unique match in the Edit tool (no ambiguous matches; per Wave 268 strict-clean rule, no use of destructive bulk replace_all).

### 2.3 Net Prose Delta

- **Line 29:** `10 pages, 381510 bytes` → `14 pages, 305270 bytes` (file-listing parenthetical)
- **Line 56:** `Pages: 10`, `File size: 381510 bytes` → `Pages: 14`, `File size: 305270 bytes` (pdfinfo expectation)
- **Line 88:** `(10 pages, IEEEtran-journal typeset)` → `(14 pages, IEEEtran-journal typeset)` (upload instruction)

All three numbers are now self-consistent and match the actual `paper-A-final.pdf` on disk (verified 2026-09-25 — see §3).

---

## 3. Verification — actual paper-A-final.pdf on disk

```bash
$ ls -la docs/drafts/paper-A-final.pdf
-rw-r--r-- 1 hugo hugo 305270 Sep 25 13:40 /home/hugo/codes/flowa-multistep-reinference/docs/drafts/paper-A-final.pdf

$ pdfinfo docs/drafts/paper-A-final.pdf | grep -E "Pages|File size"
Pages:           14
File size:       305270 bytes
```

The post-edit `README.md` line-29 parenthetical, line-56 `pdfinfo` expectation, and line-88 page-count claim all now match the actual file. The 4-page expansion (10 → 14) and 76240-byte contraction (381510 → 305270) both trace to the Wave 343 pdflatex rebuild that incorporated the BGV12 + Villani 2003 bibliography fix + RMSPreserving disposition.

---

## 4. New SHA-256 of tnnls_submission/README.md

```
a3c9452c3b428ca35ae38426e5788636feb10f0a2073850d8a85c495b5a4cb12  tnnls_submission/README.md
```

(Pre-edit SHA-256: `128137fe1209b0d2b6bbba71667afb9f241aadb8022d40ef941c6471456dcb20` per Wave 345 MANIFEST.md row 22.)

---

## 5. Hard-rule compliance recap

- **ADDITIVE ONLY:** All 3 replacements point to the actual on-disk numbers (14 pages / 305270 bytes). No audit or CLAIMS number was changed.
- **NO-PUSH:** Per Wave 325 policy, no `git push`. Local commit is gated on user approval.
- **Wave 268 strict-clean:** 3 surgical Edit calls, each with unique-context `old_string`, no `replace_all` bulk. Fewer lines changed than a `sed`-style rewrite would have produced.
- **TNNLS submission freeze:** Once `v3.0-tnnls-ready` is cut, `tnnls_submission/*` accepts additive docs only — this wave is additive (stale numbers → fresh numbers pointing at the canonical PDF, which the MANIFEST already lists as the canonical artifact).
- **Number provenance:** 14 pages / 305270 bytes comes from `pdfinfo` + `ls -la` on the actual canonical file (verified 2026-09-25). No hard-coded magic numbers.

---

## 6. Open issue — `tnnls_submission/MANIFEST.md` SHA-256 column stale

`tnnls_submission/MANIFEST.md` row 22 currently records the pre-Wave-346 SHA-256 for `README.md`:

```
| `README.md` | 9398 | `128137fe1209b0d2b6bbba71667afb9f241aadb8022d40ef941c6471456dcb20` | ... |
```

That SHA is the **pre-edit** hash. The post-edit hash is `a3c9452c3b428ca35ae38426e5788636feb10f0a2073850d8a85c495b5a4cb12` (see §4).

This is **deliberately out of scope** for Wave 346 Phase 1 (matches the Wave 345 split: README.md fix in Phase 1, MANIFEST SHA re-hash deferred). Per the flowa-paper-evidence skill, "When you change `tnnls_submission/*`, update the SHA-256 column in `tnnls_submission/MANIFEST.md`" — but the user's Phase 1 authorization was scoped to `tnnls_submission/README.md` only. A Phase 2 (or follow-up bookkeeping wave) needs to:

1. Update MANIFEST.md row 22 SHA-256 column: `128137fe1209b0d2b6bbba71667afb9f241aadb8022d40ef941c6471456dcb20` → `a3c9452c3b428ca35ae38426e5788636feb10f0a2073850d8a85c495b5a4cb12`.
2. Re-run `cd tnnls_submission && sha256sum -- *.md supplementary/README.md` and confirm every other row still matches.
3. Re-run `python tools/check_claims_consistency.py` (no drift expected — README.md is not a claims surface).

Until that follow-up, `tnnls_submission/MANIFEST.md` row 22 SHA-256 column is stale-by-one-hash. **This is the only ledger drift introduced by Wave 346.**

---

## 7. No other stale byte/page references in tnnls_submission/README.md

```
$ grep -nE "10 pages|381510 bytes|14 pages|305270 bytes|paper-flat-ieeetran" tnnls_submission/README.md
29:docs/drafts/paper-A-final.pdf   ← 14 pages, 305270 bytes (Wave 324 D+5, ready-to-submit)
56:   Expect: `Pages: 14`, `File size: 305270 bytes`.
88:- Upload: **`docs/drafts/paper-A-final.pdf`** (14 pages, IEEEtran-journal typeset).
```

All 3 matches are now the post-edit canonical numbers. No `paper-flat-ieeetran` references remain (Wave 345 already removed those). No `381510 bytes` references remain. No `10 pages` references remain. Wave 346 closes the byte/page drift flagged in Wave 345's §6 open issue (line 148-150 of `docs/audit/wave345-cross-doc-fixes.md`).

---

## 8. Summary

- 3 stale byte/page references fixed in `tnnls_submission/README.md`.
- New SHA-256: `a3c9452c3b428ca35ae38426e5788636feb10f0a2073850d8a85c495b5a4cb12`.
- No CLAIMS / audit / paper-surface numbers were touched.
- One bookkeeping follow-up flagged: MANIFEST.md row 22 SHA-256 column re-hash (deferred per Phase 1 scope).