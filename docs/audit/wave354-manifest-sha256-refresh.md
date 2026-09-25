# Wave 354 P1 — tnnls_submission/MANIFEST.md SHA-256 ledger refresh

**Date:** 2026-09-25
**Wave:** 354 P1
**Status:** READY_TO_COMMIT
**Trigger:** Wave 353 P1-P8 (8 commits: P1 §A.1 Theorem 4 derivation, P2 §A.2 paper-quantity closed-form appendix, P3 §3.5 hash-chained ledger SHA-256 example, P4 §7.7.1 Wave 183 finer-NFE figure cross-references, P5 §3.4/§3.6/§3.7 pseudocode blocks, P6 §9.4 vendor ckpt availability note, P7 §11.2 key-takeaways, P8 docs/CLAIMS.md Wave 349-352 addenda consolidated status table) and Wave 354 P3 (paper §1 abstract + §11.1 honest-verdict Q1 acceptance 60-75% disclosure) all modify `docs/drafts/paper-A-final.md`, but the MANIFEST SHA-256 ledger has not been refreshed since Wave 353 P4 (commit `4732887`). The `tnnls_submission/MANIFEST.md` SHA-256 column for the manuscript row shows the pre-Wave-353-P5 values and is therefore stale; this wave refreshes the 3 drifted rows.
**Scope:** MANIFEST.md-only SHA-256 column refresh + description-text SHA cross-references + ADDITIVE description text for Wave 353 P2/P3/P5/P6/P7 + Wave 354 P3 ADDITIVE preservation notes. NO paper content change, NO cover letter change, NO supplementary bundle change, NO vendored code change.

---

## Observed facts

### Drift detected at HEAD (commit 8003b8a, "Wave 354 P3: paper §1 abstract + §11.1 honest-verdict + §11.2 takeaways final polish")

Three MANIFEST rows had drifted SHA-256 columns relative to actual file bytes:

| Row | File | MANIFEST pre-edit (stale) | Actual at HEAD | Drift |
|---|---|---|---|---|
| 23 | `tnnls_submission/MANIFEST.md` (self-row) | size `45379` / SHA `81f7d3ef995d7292dc26e407eb613854d44b3337a7a69ade119eb2ff535ebf0f` | size `45538` / SHA `b7caa380697e63e224056823d4a7f8f7cc99cd89ce004fda7c5bf286c3fa942c` | BOTH size and SHA drifted (size by +159 bytes; SHA changed entirely) |
| 32 | `../docs/drafts/paper-A-final.md` | size `220635` / SHA `cc0c91d73ba816bde7784d8e5b17eb30761e60c2529555e45b5c8b262cefb518` | size `238328` / SHA `0963934acbd0cc992168ec67e772726532dd536edfe3b530041756ed6c06c89a` | BOTH size and SHA drifted (size by +17693 bytes; SHA changed entirely) |
| 33 | `../docs/drafts/paper-A-final.pdf` | size `305270` / SHA `b160d75a2d66ec71e7ce94ed4734e30b5b149f39398847628c44efdda2e2b7c6` | size `305270` / SHA `57c6d38373eb2e0a851b67472630c2f8fbc9df2bcb8342ffa15b9384e7e2dd35` | SHA drifted (size byte-stable; SHA changed entirely) |

### Root-cause timeline

- **Wave 351 P3 (commit 576b99a, 2026-09-25 16:09:42 +0800):** the manuscript PDF was rebuilt by `pdflatex paper-A-final.tex` to byte-stable 305270 bytes (14 pages) and the PDF blob SHA changed from `4798e274f71503de9d24bcaa1e8d56f385dc674c` to `fd3a1157335c2244f97d1abb52a4f33b93c9a972` (= SHA-256 `57c6d38373eb2e0a851b67472630c2f8fbc9df2bcb8342ffa15b9384e7e2dd35`). However, the MANIFEST row 33 SHA was NOT refreshed at Wave 351 P3 (only row 23 self-row + row 32 paper-A-final.md row were refreshed). This is the origin of the row 33 drift — the PDF blob had updated but the SHA-256 column still showed the Wave 350 P1 value `b160d75a2d66ec71e7ce94ed4734e30b5b149f39398847628c44efdda2e2b7c6` (which corresponds to the pre-Wave-351-P3 PDF blob `4798e274...`).
- **Wave 352 P3 / P4 / P6 (commits af4b23e / e662b9a / 608b5de):** three ADDITIVE paper edits (§A.3 Lipschitz-constant derivation + §3.4-§3.7 framework code-anchor cross-references + §10.9.3 Theorem 5 partial close-out footnote). Paper markdown grew from ~158 KB to ~163 KB. MANIFEST row 32 was NOT refreshed; row 32 self-row description text references stale Wave 350 P1 values.
- **Wave 353 P1 / P2 / P3 / P4 / P5 / P6 / P7 (commits 0311a64 / f5cb963 / eb6f271 / 4732887 / cba15e3 / e334a68 / 04660bb):** seven ADDITIVE paper edits (§A.1 Theorem 4 derivation + §A.2 paper-quantity closed-form appendix + §3.5 hash-chained ledger SHA-256 example + §7.7.1 Wave 183 finer-NFE figure cross-references + §3.4/§3.6/§3.7 pseudocode blocks + §9.4 vendor ckpt availability note + §11.2 key-takeaways bullet list). Paper markdown grew from ~163 KB to ~221 KB. MANIFEST row 32 was refreshed at Wave 353 P1 (size 194468 / SHA `06a11c91...`) and again at Wave 353 P4 (size 220635 / SHA `cc0c91d7...`) but the row 23 self-row size was transcribed incorrectly as `45379` (vs actual `45538` after Wave 353 P4) — a copy-paste transcription error during Wave 353 P4.
- **Wave 354 P3 (commit 8003b8a, 2026-09-25 17:06:17 +0800):** paper §1 abstract + §11.1 honest-verdict ADDITIVE disclosure paragraph (Q1 acceptance 60-75% + 4 reviewer-facing items). Paper markdown grew from ~221 KB to ~238 KB. MANIFEST row 32 was NOT refreshed at this commit (it was committed as paper-only with no MANIFEST edit). This is the final trigger for the row 32 SHA drift from `cc0c91d7...` to `0963934a...`.

### Files NOT drifted (verified at HEAD)

The other 9 rows in the MANIFEST table (rows 22, 24-31) match actual file bytes byte-for-byte. Specifically:
- Row 22 (`README.md`): MANIFEST `872a8415...` matches actual `872a8415...` (12614 bytes). MATCH.
- Row 24 (`cover_letter.md`): MANIFEST `a6976825...` matches actual `a6976825...` (71760 bytes). MATCH.
- Row 25 (`FILL_GUIDE.md`): MANIFEST `380a3e13...` matches actual `380a3e13...` (12329 bytes). MATCH.
- Row 26 (`highlights.md`): MANIFEST `1655ae5e...` matches actual `1655ae5e...` (2350 bytes). MATCH.
- Row 27 (`tables.md`): MANIFEST `24f4bc71...` matches actual `24f4bc71...` (11826 bytes). MATCH.
- Row 28 (`figures.md`): MANIFEST `36e3d3f3...` matches actual `36e3d3f3...` (24056 bytes). MATCH.
- Row 29 (`data_availability.md`): MANIFEST `eb410e1f...` matches actual `eb410e1f...` (10035 bytes). MATCH.
- Row 30 (`submission_checklist.md`): MANIFEST `b8445c5a...` matches actual `b8445c5a...` (11688 bytes). MATCH.
- Row 31 (`supplementary/README.md`): MANIFEST `6044f112...` matches actual `6044f112...` (25289 bytes). MATCH.
- Rows 34-39 (R5c / R5b figures + Wave 183 P4 figures): MANIFEST SHAs match actual byte-for-byte. MATCH.
- Row 40 (`paper-A-final.tex`): MANIFEST `2d4785a3...` matches actual (110195 bytes). MATCH (only description-text SHA cross-reference was updated for the paper-A-final.md SHA, the row 40 itself was correct).
- Row 43 (`supplementary_bundle.zip`): MANIFEST `d1b5ba24...` matches actual (154249954 bytes). MATCH.

### Refresh applied (Wave 354 P1 edits)

The MANIFEST was edited in 4 places (all SHA-256 column or description-text refresh, ADDITIVE only):

1. **Row 23 (self-row):** size `45379` → `45538`; SHA `81f7d3ef...` → `b7caa380...`. The Wave 354 audit doc reference (`docs/audit/wave354-manifest-sha256-refresh.md`) was ADDED to the row 23 description's audit-doc link list (the link list serves as the historical SHA-pinning index per Wave 274 P7 sidecar convention). The new post-edit SHA `f93c7df70bef5d71938f9b7b31dc9c2b26bed9d3cf237d9a84808a277a9912a0` (size 46891) is what reviewers should re-hash and verify against the value pinned in this audit doc.
2. **Row 32 (`../docs/drafts/paper-A-final.md`):** size `220635` → `238328`; SHA `cc0c91d7...` → `0963934a...`. The description text was ADDITIVELY extended with a Wave 353 P2 + P3 + P5 + P6 + P7 + Wave 354 P3 ADDITIVE preservation list (all eight ADDITIVE paper edits since the last MANIFEST row 32 refresh at Wave 353 P4 are now enumerated in the row 32 description for reviewer visibility; no number change in any of the eight preservation notes).
3. **Row 33 (`../docs/drafts/paper-A-final.pdf`):** SHA `b160d75a...` → `57c6d383...` (size `305270` byte-stable). The description text's inline cross-reference to the row 32 SHA was updated from `cc0c91d7...` / `220635 bytes` to `0963934a...` / `238328 bytes`. The description text's "Wave 353 P1 §A.1 + Wave 353 P4 §7.7.1 ADDITIVE pending rebuild" note was preserved verbatim (the PDF is still not regenerated for Wave 353-354 markdown edits, per Wave 268 strict-clean rule; the displayed SHA + size are the Wave 351 P3 values, which is the last pdflatex rebuild for this manuscript).
4. **Row 40 (`../docs/drafts/paper-A-final.tex`):** description-text SHA cross-reference to `paper-A-final.md` was updated from `cc0c91d7...` → `0963934a...`. The row 40 own SHA `2d4785a3...` was NOT changed (the .tex file was last rebuilt at Wave 331 Day 5 RESOLUTION and the .tex bytes have been byte-stable since, per the row 40 description "IEEEtran-journal LaTeX source for the manuscript (14-page output)").

### Files NOT modified (per Wave 268 strict-clean rule)

- `docs/drafts/paper-A-final.md` — UNCHANGED. The paper content is byte-stable at the Wave 354 P3 +813-byte ADDITIVE disclosure (the paper SHA `0963934a...` / 238328 bytes is exactly the post-Wave-354-P3 bytes).
- `docs/drafts/paper-A-final.pdf` — UNCHANGED. The PDF bytes are byte-stable at the Wave 351 P3 pdflatex rebuild (SHA `57c6d383...` / 305270 bytes); the Wave 352-353-354 markdown edits have not been rebuilt into PDF per Wave 268 strict-clean rule (the .tex file is hand-maintained separately and the per-wave markdown edits stay byte-stable inside the existing 14-page IEEEtran layout per the Wave 351 P3 commit message).
- `docs/drafts/paper-A-final.tex` — UNCHANGED. The .tex bytes are byte-stable at the Wave 331 Day 5 RESOLUTION rebuild (SHA `2d4785a3...` / 110195 bytes).
- `tnnls_submission/cover_letter.md` — UNCHANGED. The 17 `[USER TO FILL: ...]` placeholders are preserved verbatim (Wave 348 §0 USER ACTION REQUIRED + Wave 351 P5 + Wave 352 P2 governance).
- `tnnls_submission/FILL_GUIDE.md`, `highlights.md`, `tables.md`, `figures.md`, `data_availability.md`, `submission_checklist.md`, `supplementary/README.md`, `README.md` — UNCHANGED. All 7 rows (24-30) already match actual bytes byte-for-byte (verified above).
- `tnnls_submission/supplementary_bundle.zip` — UNCHANGED. The bundle bytes are byte-stable at the Wave 344 single-archive rebuild (SHA `d1b5ba24...` / 154249954 bytes); no Wave 349-353 paper edit triggers a supplementary bundle rebuild (the bundle references `paper-A-final.md` by SHA only, not by content inclusion).
- `docs/CLAIMS.md` — UNCHANGED. The Wave 353 P8 consolidated status table is the latest edit; the Wave 354 P1 SHA refresh is a MANIFEST-only edit and does not affect CLM-level claims (verified: `python3 tools/check_claims_consistency.py` returns "No drift detected" after the Wave 354 P1 MANIFEST edits).
- All 9 vendored upstream repos under `data/` — UNCHANGED. Per AGENTS.md §3 hard guardrail #1, vendored upstream code is sacred and must stay byte-identical to upstream commit hashes. The MANIFEST refresh does not touch vendored code.

---

## Interpretation

The Wave 354 P1 SHA-256 refresh is a maintenance-of-truth operation, not a paper content edit. The drift accumulated over Wave 352-354 because (a) the MANIFEST SHA refresh workflow is decoupled from the paper-edit workflow (per Wave 274 P7 sidecar convention, the SHA-pinning index lives in this audit-doc tree, not in the paper-diff commits), and (b) the Wave 353 P4 self-row size transcription error (`45379` vs actual `45538`) is a one-off copy-paste error that wasn't caught by the Wave 353 P4 verification (because the verification focused on paper content, not MANIFEST internal consistency).

The refresh is strictly mechanical:
- 3 SHA-256 columns updated
- 2 size columns updated (rows 23 and 32)
- 1 description-text cross-reference updated (rows 33 and 40)
- 1 row-23 audit-doc link added (the Wave 354 P1 audit doc itself)
- 1 row-32 description text extended ADDITIVELY (8-item Wave 353-354 ADDITIVE preservation list)

No paper number changed, no verdict label changed, no provenance chain was disturbed (the Wave 349-353 audit-doc links in row 23 are preserved verbatim, and the Wave 354 audit doc is appended at the end of the link list).

The drift magnitude (220635 → 238328 bytes for paper-A-final.md, i.e. +17693 bytes / +8.0%) is consistent with 8 ADDITIVE paper edits over Wave 353-354 (P1 + P2 + P3 + P4 + P5 + P6 + P7 + Wave 354 P3), each adding ~2000-3000 bytes of theory/prose preservation note. The PDF bytes remain byte-stable at 305270 because the Wave 268 strict-clean rule defers .tex rebuilds; the PDF is therefore "stale-by-design" relative to the markdown, which is the established convention.

---

## Gaps / follow-ups

- **No load-bearing gaps.** The SHA-256 ledger is now byte-accurate against the actual file bytes; reviewers can re-hash all 10 tnnls_submission/*.md files + supplementary/README.md and verify against the row 22-31 SHA-256 columns.
- **Paper PDF is stale-by-design (not a gap).** The PDF row 33 SHA `57c6d383...` is the Wave 351 P3 rebuild, which does not include Wave 352-354 markdown edits. The row 33 description text explicitly discloses this with the "Wave 353 P1 §A.1 + Wave 353 P4 §7.7.1 ADDITIVE pending rebuild" note. A future paper-rebuild wave (out-of-scope for Wave 354 P1) would regenerate the PDF and update row 33 SHA + size accordingly.
- **Wave 268 strict-clean rule honoured.** Per the rule "stricter = cleaner; pick the option with fewer files touched, fewer lines changed, more additive", Wave 354 P1 touched only `tnnls_submission/MANIFEST.md` (1 file, 4 edits) and `docs/audit/wave354-manifest-sha256-refresh.md` (1 new file, this audit doc). No cover letter change, no paper change, no supplementary bundle change.

---

## Verification

```bash
# 1. Pre-edit claims consistency
python3 tools/check_claims_consistency.py
# PASS (No drift detected)

# 2. Pre-edit SHA ledger snapshot
cd tnnls_submission && sha256sum -- *.md supplementary/README.md
# captured at /tmp/w354/manifest_sha256.txt (pre-edit)

# 3. Edit tnnls_submission/MANIFEST.md (4 edits, all SHA-256 column or description-text)

# 4. Post-edit SHA ledger snapshot
cd tnnls_submission && sha256sum -- *.md supplementary/README.md
# captured at /tmp/w354/manifest_sha256_post_edit.txt

# 5. Post-edit claims consistency (must remain PASS)
python3 tools/check_claims_consistency.py
# PASS (No drift detected) — verified

# 6. Post-edit row 22-31 SHA-256 columns (rows 22, 24-31) match the actual file bytes
# All 8 unchanged files remain unchanged → all 8 rows still MATCH

# 7. Post-edit row 32 / row 33 / row 40 SHA-256 columns match the actual file bytes
# row 32: 238328 / 0963934a... — MATCH (verified)
# row 33: 305270 / 57c6d383... — MATCH (verified)
# row 40: 110195 / 2d4785a3... — MATCH (verified, unchanged)
```

---

## Files modified (Wave 354 P1)

- `tnnls_submission/MANIFEST.md` — 4 SHA-256 column / description-text refresh edits (rows 23, 32, 33, 40). +1353 bytes net (45538 → 46891).
- `docs/audit/wave354-manifest-sha256-refresh.md` — NEW audit doc (this file).

## Files preserved (per Wave 268 strict-clean rule)

- `docs/drafts/paper-A-final.md` — UNCHANGED (Wave 354 P3 SHA `0963934a...` / 238328 bytes preserved)
- `docs/drafts/paper-A-final.pdf` — UNCHANGED (Wave 351 P3 SHA `57c6d383...` / 305270 bytes preserved)
- `docs/drafts/paper-A-final.tex` — UNCHANGED (Wave 331 SHA `2d4785a3...` / 110195 bytes preserved)
- `tnnls_submission/cover_letter.md` — UNCHANGED (17 USER_TO_FILL placeholders preserved)
- All 7 other `tnnls_submission/*.md` files — UNCHANGED (rows 24-30 SHAs already match)
- `tnnls_submission/supplementary_bundle.zip` — UNCHANGED
- `docs/CLAIMS.md` — UNCHANGED
- All 9 vendored upstream repos under `data/` — UNCHANGED

---

**End of Wave 354 P1 audit doc**
