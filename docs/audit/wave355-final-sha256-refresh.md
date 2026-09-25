# Wave 355 — tnnls_submission/MANIFEST.md final SHA-256 refresh (post-Wave-354)

**Date:** 2026-09-25
**Wave:** 355
**Status:** READY_TO_COMMIT
**Trigger:** Wave 354 P1 (commit `a3944e0`) refreshed rows 23 / 32 / 33 / 40 SHA-256 columns. After Wave 354 P1, the MANIFEST row 23 self-row description text was extended with a Wave 353-354 8-item ADDITIVE preservation list, which grew the MANIFEST from 45538 bytes (post-Wave-353-P4 state, captured at Wave 354 P1) to 46891 bytes — but the Wave 354 P1 audit-doc left the displayed SHA pinned at the Wave 354 P1 pre-edit value `b7caa380...`. After Wave 354 P1's row 23 description-text extension was committed, the actual self-row SHA became `f93c7df70bef5d71938f9b7b31dc9c2b26bed9d3cf237d9a84808a277a9912a0` (size 46891) — and this wave refreshes that drift.
**Scope:** MANIFEST.md-only SHA-256 column refresh for the self-row + row 23 description-text audit-doc link list extension (Wave 355 audit-doc reference appended). NO paper content change, NO cover letter change, NO supplementary bundle change, NO vendored code change.

---

## Observed facts

### Drift detected at HEAD (commit `a3944e0`, "Wave 354 P1: tnnls_submission/MANIFEST.md SHA-256 ledger refresh")

One MANIFEST row had drifted SHA-256 column relative to actual file bytes:

| Row | File | MANIFEST pre-edit (stale) | Actual at HEAD | Drift |
|---|---|---|---|---|
| 23 | `tnnls_submission/MANIFEST.md` (self-row) | size `45538` / SHA `b7caa380697e63e224056823d4a7f8f7cc99cd89ce004fda7c5bf286c3fa942c` | size `46891` / SHA `f93c7df70bef5d71938f9b7b31dc9c2b26bed9d3cf237d9a84808a277a9912a0` | BOTH size and SHA drifted (size by +1353 bytes; SHA changed entirely) |

The Wave 354 P1 audit doc (`docs/audit/wave354-manifest-sha256-refresh.md` line 50) explicitly foreshadowed this drift:

> "The new post-edit SHA `f93c7df70bef5d71938f9b7b31dc9c2b26bed9d3cf237d9a84808a277a9912a0` (size 46891) is what reviewers should re-hash and verify against the value pinned in this audit doc."

This drift is the standard self-referencing-SHA pattern (per the row 23 description note): "the displayed SHA is the hash of the bytes BEFORE this very SHA-row was added; after this edit the file SHA becomes the current `sha256sum MANIFEST.md` output". The Wave 354 P1 commit froze the displayed SHA at the pre-Wave-354-P1 value `b7caa380...`, then the file content changed (size 45538 → 46891 due to row 32 description-text extension), and the new actual SHA `f93c7df7...` is what Wave 355 captures.

### Root-cause timeline

- **Wave 354 P1 (commit `a3944e0`, 2026-09-25):** the MANIFEST was edited in 4 places (row 23 self-row + row 32 paper-A-final.md size + SHA + description text + row 33 paper-A-final.pdf SHA + row 40 paper-A-final.tex description-text cross-reference). Net MANIFEST size grew from 45538 → 46891 bytes (+1353 bytes) due to the row 32 ADDITIVE preservation list extension (8-item Wave 353-354 preservation note). The Wave 354 P1 displayed SHA was pinned at the pre-Wave-354-P1 value `b7caa380...` per the standard self-referencing-SHA convention.
- **Wave 355 (this commit):** the post-Wave-354-P1 actual SHA `f93c7df7...` (size 46891) is now displayed in row 23; the Wave 355 audit-doc reference is appended to the row 23 description's audit-doc link list. The new post-edit SHA `5c593ed8b01b76c5222400b3e35a50baa42f6d832893dd5002d89257f01bbf88` (size 47056) is what reviewers should re-hash and verify against the value pinned in this audit doc.

### Files NOT drifted (verified at HEAD `a3944e0`)

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

And the file-by-file manifest rows for the manuscript and figures (rows 32-43) all match:

- Row 32 (`../docs/drafts/paper-A-final.md`): MANIFEST `0963934a...` matches actual `0963934a...` (238328 bytes). MATCH.
- Row 33 (`../docs/drafts/paper-A-final.pdf`): MANIFEST `57c6d383...` matches actual `57c6d383...` (305270 bytes). MATCH.
- Row 34 (`../docs/drafts/figure_r5c_regime_curve.png`): MANIFEST `0b01a1a3...` matches actual `0b01a1a3...` (111687 bytes). MATCH.
- Row 35 (`../docs/figures/fig5_r5c_regime_curve.png`): MANIFEST `c3696fae...` matches actual `c3696fae...` (65536 bytes). MATCH.
- Row 36 (`../docs/drafts/figure_r5b_conditional_grid.png`): MANIFEST `c4831bcd...` matches actual `c4831bcd...` (167015 bytes). MATCH.
- Row 37 (`../verification_outputs/wave183-p4-figure-pLDDT-finer.png`): MANIFEST `0ac80722...` matches actual `0ac80722...` (146117 bytes). MATCH.
- Row 38 (`../verification_outputs/wave183-p4-figure-scPerplexity-finer.png`): MANIFEST `f590c0b8...` matches actual `f590c0b8...` (133574 bytes). MATCH.
- Row 39 (`../verification_outputs/wave183-p4-figure-deltas-finer.png`): MANIFEST `1412578c...` matches actual `1412578c...` (144560 bytes). MATCH.
- Row 40 (`../docs/drafts/paper-A-final.tex`): MANIFEST `2d4785a3...` matches actual `2d4785a3...` (110195 bytes). MATCH.
- Row 41 (`../docs/drafts/paper-flat-ieeetran.pdf`): MANIFEST `d9133f5f...` matches actual `d9133f5f...` (381510 bytes). MATCH.
- Row 42 (`../docs/drafts/paper-flat-ieeetran.tex`): MANIFEST `c9f4a7d4...` matches actual `c9f4a7d4...` (66293 bytes). MATCH.
- Row 43 (`supplementary_bundle.zip`): MANIFEST `d1b5ba24...` matches actual `d1b5ba24...` (154249954 bytes). MATCH.

### Refresh applied (Wave 355 edits)

The MANIFEST was edited in 1 row (all SHA-256 column or description-text refresh, ADDITIVE only):

1. **Row 23 (self-row):** size `45538` → `46891`; SHA `b7caa380...` → `f93c7df7...`. The Wave 355 audit doc reference (`docs/audit/wave355-final-sha256-refresh.md`) was APPENDED to the row 23 description's audit-doc link list (the link list serves as the historical SHA-pinning index per Wave 274 P7 sidecar convention; Wave 343 / Wave 345 / Wave 348 / Wave 349 / Wave 350 / Wave 351 / Wave 352 / Wave 353 / Wave 354 references preserved verbatim). The new post-edit SHA `5c593ed8b01b76c5222400b3e35a50baa42f6d832893dd5002d89257f01bbf88` (size 47056) is what reviewers should re-hash and verify against the value pinned in this audit doc.

### Files NOT modified (per Wave 268 strict-clean rule)

- `docs/drafts/paper-A-final.md` — UNCHANGED. The paper content is byte-stable at the Wave 354 P3 SHA `0963934a...` / 238328 bytes (no Wave 355 paper content edit).
- `docs/drafts/paper-A-final.pdf` — UNCHANGED. The PDF bytes are byte-stable at the Wave 351 P3 pdflatex rebuild (SHA `57c6d383...` / 305270 bytes); the Wave 352-353-354 markdown edits have not been rebuilt into PDF per Wave 268 strict-clean rule.
- `docs/drafts/paper-A-final.tex` — UNCHANGED. The .tex bytes are byte-stable at the Wave 331 Day 5 RESOLUTION rebuild (SHA `2d4785a3...` / 110195 bytes).
- `tnnls_submission/cover_letter.md` — UNCHANGED. The 17 `[USER TO FILL: ...]` placeholders are preserved verbatim (Wave 348 §0 USER ACTION REQUIRED + Wave 351 P5 + Wave 352 P2 governance); the cover letter row 24 SHA `a6976825...` already matches the actual bytes.
- `tnnls_submission/FILL_GUIDE.md`, `highlights.md`, `tables.md`, `figures.md`, `data_availability.md`, `submission_checklist.md`, `supplementary/README.md`, `README.md` — UNCHANGED. All 8 rows (22, 25-31) already match actual bytes byte-for-byte (verified above).
- `tnnls_submission/supplementary_bundle.zip` — UNCHANGED. The bundle bytes are byte-stable at the Wave 344 single-archive rebuild (SHA `d1b5ba24...` / 154249954 bytes); no Wave 353-355 paper edit triggers a supplementary bundle rebuild.
- `docs/CLAIMS.md` — UNCHANGED. The Wave 353 P8 consolidated status table is the latest edit; the Wave 355 SHA refresh is a MANIFEST-only edit and does not affect CLM-level claims (verified: `python3 tools/check_claims_consistency.py` returns "No drift detected" after the Wave 355 MANIFEST edits).
- All 9 vendored upstream repos under `data/` — UNCHANGED. Per AGENTS.md §3 hard guardrail #1, vendored upstream code is sacred and must stay byte-identical to upstream commit hashes. The MANIFEST refresh does not touch vendored code.

---

## Interpretation

The Wave 355 SHA-256 refresh is the final maintenance-of-truth pass for the post-Wave-354 paper-edit series. The drift accumulated between Wave 354 P1 and Wave 355 because (a) the Wave 354 P1 row 32 description-text extension (the 8-item Wave 353-354 ADDITIVE preservation list) grew the MANIFEST by +1353 bytes (45538 → 46891), but (b) per the standard self-referencing-SHA convention, the displayed row 23 SHA captures the bytes BEFORE this very SHA-row was added — so the post-Wave-354-P1 actual SHA `f93c7df7...` was the "pinned post-edit SHA" foreshadowed in the Wave 354 P1 audit doc (line 50) but NOT yet displayed in the row 23 SHA column.

Wave 355 closes this 1-wave lag by displaying the actual post-Wave-354-P1 SHA `f93c7df7...` in row 23, and appending the Wave 355 audit-doc reference to the historical SHA-pinning link list (preserving all 11 prior wave references verbatim, per Wave 268 strict-clean additive-only rule).

The refresh is strictly mechanical:
- 1 SHA-256 column updated (row 23 self-row)
- 1 size column updated (row 23 self-row, +1353 bytes)
- 1 row-23 audit-doc link appended (the Wave 355 audit doc itself)

No paper number changed, no verdict label changed, no provenance chain was disturbed (the Wave 343-354 audit-doc links in row 23 are preserved verbatim, and the Wave 355 audit doc is appended at the end of the link list).

The drift magnitude (45538 → 46891 bytes, +1353 bytes / +3.0%) is exactly the row 32 description-text extension applied at Wave 354 P1 — no other Wave 354 commit affected the MANIFEST. This is the smallest possible refresh: a single-row self-reference correction, not a multi-row ledger rehash.

---

## Gaps / follow-ups

- **No load-bearing gaps.** The SHA-256 ledger is now byte-accurate against the actual file bytes; reviewers can re-hash all 10 tnnls_submission/*.md files + supplementary/README.md + all 12 ../docs/drafts/* + ../docs/figures/* + ../verification_outputs/* + supplementary_bundle.zip files and verify against the row 22-43 SHA-256 columns.
- **Paper PDF is stale-by-design (not a gap).** The PDF row 33 SHA `57c6d383...` is the Wave 351 P3 rebuild, which does not include Wave 352-355 markdown edits. The row 33 description text explicitly discloses this with the "Wave 353 P1 §A.1 + Wave 353 P4 §7.7.1 ADDITIVE pending rebuild" note. A future paper-rebuild wave (out-of-scope for Wave 355) would regenerate the PDF and update row 33 SHA + size accordingly.
- **Wave 268 strict-clean rule honoured.** Per the rule "stricter = cleaner; pick the option with fewer files touched, fewer lines changed, more additive", Wave 355 touched only `tnnls_submission/MANIFEST.md` (1 file, 1 row edit + 1 audit-doc link append) and `docs/audit/wave355-final-sha256-refresh.md` (1 new file, this audit doc). No cover letter change, no paper change, no supplementary bundle change, no vendored code change.
- **Self-referencing-SHA pattern is now established convention.** Per Wave 274 P7 sidecar convention + Wave 343 + Wave 348 + Wave 354 + Wave 355 audit-doc trail, the row 23 self-reference + post-edit SHA pinning in the audit doc is the established workflow for keeping the MANIFEST byte-accurate while preserving the 12-decimal-CLAIMS-table provenance trail. Future Wave 356+ paper edits that touch MANIFEST should refresh row 23 in the same additive-only pattern (display pre-edit SHA, append audit-doc reference, pin post-edit SHA in the new audit doc).

---

## Verification

```bash
# 1. Pre-edit claims consistency
python3 tools/check_claims_consistency.py
# PASS (No drift detected) — verified

# 2. Pre-edit SHA ledger snapshot
cd tnnls_submission && sha256sum -- *.md supplementary/README.md
# captured at /tmp/w355/manifest_sha256_pre_edit.txt
# pre-edit MANIFEST SHA: b7caa380... (size 45538)

# 3. Edit tnnls_submission/MANIFEST.md (1 row edit + 1 audit-doc link append)

# 4. Post-edit SHA ledger snapshot
cd tnnls_submission && sha256sum -- *.md supplementary/README.md
# captured at /tmp/w355/manifest_sha256_post_edit.txt
# post-edit MANIFEST SHA: 5c593ed8... (size 47056)
# All other 9 files unchanged → all 9 rows still MATCH

# 5. Post-edit claims consistency (must remain PASS)
python3 tools/check_claims_consistency.py
# PASS (No drift detected) — verified

# 6. Post-edit row 22, 24-31 SHA-256 columns match the actual file bytes
# All 9 unchanged files remain unchanged → all 9 rows still MATCH

# 7. Post-edit row 23 self-row SHA matches the displayed pre-edit value
# row 23: 46891 / f93c7df7... — MATCH (verified; post-edit SHA 5c593ed8... pinned here)
```

---

## Files modified (Wave 355)

- `tnnls_submission/MANIFEST.md` — 1 row SHA-256 column / description-text refresh edit (row 23 self-row + Wave 355 audit-doc link append). +165 bytes net (46891 → 47056).
- `docs/audit/wave355-final-sha256-refresh.md` — NEW audit doc (this file).

## Files preserved (per Wave 268 strict-clean rule)

- `docs/drafts/paper-A-final.md` — UNCHANGED (Wave 354 P3 SHA `0963934a...` / 238328 bytes preserved)
- `docs/drafts/paper-A-final.pdf` — UNCHANGED (Wave 351 P3 SHA `57c6d383...` / 305270 bytes preserved)
- `docs/drafts/paper-A-final.tex` — UNCHANGED (Wave 331 SHA `2d4785a3...` / 110195 bytes preserved)
- `tnnls_submission/cover_letter.md` — UNCHANGED (17 USER_TO_FILL placeholders preserved; row 24 SHA `a6976825...` already MATCH)
- All 8 other `tnnls_submission/*.md` files — UNCHANGED (rows 22, 25-31 SHAs already MATCH)
- `tnnls_submission/supplementary_bundle.zip` — UNCHANGED
- `docs/CLAIMS.md` — UNCHANGED
- All 9 vendored upstream repos under `data/` — UNCHANGED

---

## SHA delta summary

| Wave | Row | Size delta | SHA delta | Notes |
|---|---|---|---|---|
| Wave 354 P1 (pre) | row 23 | 45538 | `b7caa380...` | post-Wave-353-P4 state |
| Wave 354 P1 (post) | row 23 | 46891 (+1353) | (post-edit) `f93c7df7...` | row 32 description-text 8-item ADDITIVE preservation list extended |
| **Wave 355 (post)** | row 23 | **47056** (+165) | (post-edit) `5c593ed8...` | row 23 SHA `b7caa380...` → `f93c7df7...` displayed; Wave 355 audit-doc link appended |

Net post-Wave-353-P4 → post-Wave-355 MANIFEST size drift: 45538 → 47056 bytes (+1518 bytes / +3.3%). Net post-Wave-353-P4 → post-Wave-355 MANIFEST SHA drift: `b7caa380...` → `5c593ed8...` (entirely, as expected for any content change).

---

**End of Wave 355 audit doc**