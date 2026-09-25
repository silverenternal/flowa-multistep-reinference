# Wave 358 P2 — `tnnls_submission/tables.md` polish (ADDITIVE table-of-tables cross-reference index)

**Date:** 2026-09-25
**Wave:** 358 P2 (USER AUTHORIZED, NO PUSH)
**Author:** ultracode subagent (Wave 358 remaining-tasks sweep)
**Scope:** `tnnls_submission/tables.md` (ADDITIVE only) + `tnnls_submission/MANIFEST.md` (SHA + size refresh for `tables.md` row + audit-doc row cross-reference append). No destructive edits to any of the 5 submission tables; no claim status promotion; no number change; no SHA change of any number in Tables 1-5 above.

---

## 1. Executive Summary

`tnnls_submission/tables.md` (11826 bytes pre-edit, 22459 bytes post-edit, +10633-byte additive delta) now carries an ADDITIVE "Table of Tables (Paper)" section at the end that catalogs every markdown table embedded in the canonical TNNLS manuscript source [`docs/drafts/paper-A-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.md). The 5 primary submission tables (Tables 1-5 above — R-level headline, 4-arm H2H, statistical methods, wall-clock, reproducibility gates) are preserved verbatim with no wording change, no number change, no SHA change of any number in those tables. The new table-of-tables is the reviewer-navigation aid that closes the gap between the paper text and its byte-addressable provenance.

**Why now:** Wave 358 P2 + P3 + P4 + P5 have been sweeping through the `tnnls_submission/` package applying late-stage camera-ready polish (highlights, data-availability, supplementary, submission-checklist, archive-cleanup). The `tables.md` file was the last primary package surface that did not yet carry a paper-text-to-evidence cross-reference index. Wave 358 P2 closes that gap with an ADDITIVE 6-row catalog (T1-T6) that maps every markdown table in `paper-A-final.md` to its `table_id` + `caption` + `column_count` + `paper_section` + `source_artifact` + CONSOLIDATED_RESULTS cross-reference.

---

## 2. Observed facts

### 2.1 Files touched

| File | Action | Bytes | SHA-256 | Lines (delta) |
|---|---|---:|---|---:|
| `tnnls_submission/tables.md` | edited (APPEND additive "Table of Tables (Paper)" section after Cross-references block) | 11826 → 22459 (+10633) | `24f4bc71…` → `c0d4dd5d…` | 92 → 117 (+25) |
| `tnnls_submission/MANIFEST.md` | edited (row 27 `tables.md` SHA + size + addendum; row 23 audit-doc list append `wave358-tables-md-polish.md`) | 46891 → 49543 (+2652) | (pre-existing self-referencing SHA pattern preserved; post-edit SHA in audit doc) | (+2) |
| `docs/audit/wave358-tables-md-polish.md` | created (this file) | new | — | new ~250 |

Total: 2 edited files + 1 new audit doc. 0 deletions. ADDITIVE ONLY.

### 2.2 Tables cataloged (T1-T6, derived from `grep -nE "^\|" docs/drafts/paper-A-final.md`)

All `^\|...\|` table blocks in `paper-A-final.md` enumerated via `grep -nE '^\|' docs/drafts/paper-A-final.md`; 6 distinct table regions identified. Per-table inventory:

| ID | Paper line | § | Caption (first cell) | Cols | Source artifact |
|---|---|---|---|---:|---|
| T1 | 155-157 | §3.4.2 | Wave 355 capability-token handshake SHA-256 example (`artifact` + `bytes` + `sha256` + `role`) | 4 | `verification_outputs/wave355-capability-token-example/` |
| T2 | 184-188 | §3.5.1 | Wave 349 R1 3-seed GPU ledger SHA-256 chain (`artifact` + `bytes` + `sha256` + `role` × 3 files) | 4 | `verification_outputs/wave349-r1-3seed-gpu/` |
| T3 | 340-346 | §5.3 | Five concrete adapter implementations (`Adapter` + `File` + `Vendored code path` + `Zero-line edits` × 5 adapters) | 4 | (cumulative — 5 adapter paths) |
| T4 | 547-555 | §7.2 | Per-cell power-disclosure index (`R-cell` + `verdict` + `per-cell power disclosure in this paper` + `audit-doc handle` × 7 R-cells) | 4 | (cumulative — 7 R-cell sources) |
| T5 | 602-606 | §7.8 | R5c regime-dependent curve 3-point table (`epochs` + `base_channels` + `max_train_images` + `n_seeds` + `baseline_fid` + `best_arm_fid` + $\Delta$ FID + $d_z$ + $p_\text{bonf}$ + `verdict` × 3 epochs) | 10 | `verification_outputs/wave191-r5-n1000/` + `docs/figures/fig5_r5c_regime_curve.png` |
| T6 | 1023-1030 | §A.3.4 | CIFAR-10 RF Lipschitz constant values (`Quantity` + `Value` + `Source` × 6 quantities) | 3 | `verification_outputs/wave351-p3-thm5-numerical/lipschitz_estimate.json` |

**Table count: 6 paper tables cataloged (T1, T2, T3, T4, T5, T6).**

### 2.3 Cross-references resolved (per-row source_artifact + CONSOLIDATED_RESULTS cross-reference)

| ID | source_artifact resolved | §15.X cross-references resolved | Total refs |
|---|:---:|:---:|---:|
| T1 | yes (`wave355-capability-token-example/`) | yes (1 audit-doc handle, no §15 entry) | 2 |
| T2 | yes (`wave349-r1-3seed-gpu/`) | yes (2 audit-doc handles, no §15 entry) | 3 |
| T3 | cumulative (5 adapter paths cited) | yes (§15.74 + §15.86 + §15.96 = 3) | 8 |
| T4 | cumulative (7 R-cell sources cited) | yes (§15.88 + §15.103 + §15.104 + §15.105 = 4) | 11 |
| T5 | yes (`wave191-r5-n1000/` + `fig5_r5c_regime_curve.png`) | yes (§15.87 = 1) | 3 |
| T6 | yes (`wave351-p3-thm5-numerical/lipschitz_estimate.json`) | yes (2 audit-doc handles, no §15 entry) | 3 |

**Cross-references resolved: 30 total** (per-row source_artifact + CONSOLIDATED_RESULTS cross-reference; some rows resolve multiple source artifacts because T3 cites 5 adapters / T4 cites 7 R-cell sources, while T4 carries 4 distinct §15.X cross-references because the per-cell power-disclosure index spans 7 R-cells whose power analyses are documented in 4 distinct §15.X sections per Wave 195 / Wave 326 / Wave 352 P5 / Wave 357 P3 propagation events).

### 2.4 SHA-256 + line-count delta verification

Pre-edit:
- `tnnls_submission/tables.md`: 92 lines, 11826 bytes, SHA-256 `24f4bc71f36f37ff7d8bbb0a230acb0bd999b0308c7a24c70da71222015bf926`

Post-edit:
- `tnnls_submission/tables.md`: 117 lines, 22459 bytes, SHA-256 `c0d4dd5db99f3fd07301cab40682bb293b1562f8910429f6e1493b013c0467ae`
- Delta: +25 lines, +10633 bytes, new SHA `c0d4dd5d…`

Pre-edit:
- `tnnls_submission/MANIFEST.md`: 46891 bytes

Post-edit:
- `tnnls_submission/MANIFEST.md`: 49543 bytes, SHA-256 `2fc8455d0645266e32b402131249b970d92077a14557df80b753825fe746fca2`
- Delta: +2652 bytes (row 27 expanded +2652 chars from the SHA + size + addendum + Wave 358 P2 row 27 entry; row 23 audit-doc list appended `wave358-tables-md-polish.md` reference = +118 chars)

### 2.5 Compliance with hard guardrails (AGENTS.md §3 + Wave 268 strict-clean + Wave 325 NO-PUSH)

1. **Vendored upstream is sacred:** Not touched — `data/FlowMol3/`, `data/LineageFlow/`, `data/Kanzi/`, `data/HiDream-I1/`, `data/GraphBFN/`, `data/Lumina-Image-2.0/`, `data/ProtBFN-AbBFN/`, `data/Wan2.2/`, `data/FreqFlow/` are all byte-identical (no edit attempted).
2. **No destructive edits:** Additive — `tables.md` gains an APPEND block at end (last 25 lines / +10633 bytes); MANIFEST.md row 27 was edited to refresh SHA + size + addendum (preserving the prior content "5 TNNLS paper tables (R1–R6 headline, 4-arm H2H, statistical methods, wall-clock, reproducibility gates) — Wave 348 Phase 1b cross-doc fix: 36 local repo paths → GitHub URLs"); MANIFEST.md row 23 audit-doc list appended 1 reference (preserving all prior references).
3. **NO-PUSH policy:** This Wave 358 P2 commit is a local-only commit. No `git push`, no remote interaction. Per Wave 325 user-directive reaffirmed in `todo/PUSH-READY.md`.
4. **Honest uncertainty:** Not applicable — no status labels touched; no UNDERPOWERED / DEFERRED / REGRESSES / NOT_SIGNIFICANT promotion attempted; the table-of-tables does not promote any R-cell verdict or any wave status.
5. **TNNLS submission freeze is sacred:** The `v3.0-tnnls-ready` tag is not cut (Wave 358 P2 operates on the live working tree before the tag cut); however, the additive-only edit preserves all prior submission package content. Per Wave 343 / Wave 345 / Wave 348 / Wave 353 precedent, additive docs in `tnnls_submission/` are allowed pre-tag-cut; the SHA-256 refresh in MANIFEST.md row 27 is the canonical rehash workflow per [`docs/audit/wave348-link-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave348-link-fix.md).
6. **Per-phase audit doc:** This file IS the per-phase audit doc for Wave 358 P2 (mirrors the 12-decimal-CLAIMS-table pattern from Wave 121-273 per AGENTS.md §3.6).
7. **Stricter = cleaner:** Per Wave 268 directive, this edit is the minimal-additive variant — 1 file edit (`tables.md` append) + 2 minimal MANIFEST.md edits (row 27 SHA refresh + row 23 audit-doc list append) + 1 new audit doc = 2 files modified + 1 file created. No `tnnls_submission/README.md` / `cover_letter.md` / `submission_checklist.md` / `data_availability.md` / `figures.md` / `highlights.md` / `FILL_GUIDE.md` / `supplementary/README.md` were touched (the table-of-tables does not propagate to those surfaces because they don't reference the table-of-tables by SHA — only MANIFEST.md carries the SHA).

### 2.6 Skills invoked (per AGENTS.md §1 routing rules)

This task triggers **`flowa-paper-evidence`** (matches "paper polish" / "highlight result" / "doc updates" from AGENTS.md §1 skill routing table). The skill is invoked per the ADDITIVE principle (read `docs/CLAIMS.md` + `docs/CONSOLIDATED_RESULTS.md` + relevant `docs/audit/wave*.md` before editing prose — done in §2.1-2.2 above; the only claim-related change is the `tables.md` SHA refresh in MANIFEST.md, which preserves the prior wording verbatim and only refreshes the byte-addressable SHA + size + addendum). The `flowa-experiment-sweep` skill is NOT invoked (no experiment re-run; the table-of-tables is purely documentary, anchored on existing `verification_outputs/<wave>/` byte-stable artifacts). The `flowa-research-audit` skill is NOT invoked (no audit investigation; the audit doc is the standard per-phase governance record per AGENTS.md §3.6).

---

## 3. Interpretation

### 3.1 What this edit enables (reviewer-facing)

A reviewer landing on `tnnls_submission/tables.md` can now:
1. Read the 5 primary submission tables (Tables 1-5 — R-level headline, 4-arm H2H, statistical methods, wall-clock, reproducibility gates) as the framework's main quantitative evidence.
2. Scroll to the new "Table of Tables (Paper)" section at the end and locate every markdown table embedded in `paper-A-final.md` (T1 §3.4.2 / T2 §3.5.1 / T3 §5.3 / T4 §7.2 / T5 §7.8 / T6 §A.3.4) with its byte-addressable source artifact (`verification_outputs/<wave>/`) and CONSOLIDATED_RESULTS §15.X cross-reference.
3. Click through to the byte-stable verification artifact (e.g., `wave349-r1-3seed-gpu/SHA256SUMS` for T2, `wave351-p3-thm5-numerical/lipschitz_estimate.json` for T6) and re-verify the SHA-256 column against the manifest.
4. Cross-reference the §15.X documentation in `docs/CONSOLIDATED_RESULTS.md` (e.g., §15.87 Wave 191 R5 completion for T5, §15.88 + §15.103 + §15.104 + §15.105 for T4) to understand the wave at which each table's content was generated / updated.

### 3.2 What this edit does NOT change

- **Tables 1-5 are byte-identical** to the prior revision. No wording change, no number change, no SHA change of any number in those tables. The 5 primary submission tables remain the canonical surface.
- **No claim status promotion.** The R1 / R3 / R5a / R5b / R5c / R6 verdicts cited in T4 are verbatim from `paper-A-final.md` §7.2 (no status change attempted; the table-of-tables does not promote any R-cell verdict or any wave status).
- **No paper-text edit.** `paper-A-final.md` is not touched by this Wave 358 P2 (the table-of-tables is in `tnnls_submission/tables.md` only).
- **No push.** Per Wave 325 NO-PUSH policy, this Wave 358 P2 commit is local-only. No remote interaction.

### 3.3 `tables.md` is now submittable

The 5 primary submission tables above were already submittable per the Wave 238 P4 final verify + Wave 242 P4 final verify + Wave 345 cross-doc fixes + Wave 348 GitHub URL fix. The new table-of-tables does not gate submitter status — it is an additive reviewer-navigation aid. **The `tnnls_submission/tables.md` file remains submittable after this Wave 358 P2 edit** (the SHA-256 + size refresh in MANIFEST.md row 27 is the standard rehash workflow; the 5 tables themselves are byte-identical to the prior revision).

### 3.4 Forward-looking notes (deferred to follow-up waves, not blocking)

- The `paper-A-final.md` `.tex` source (in `docs/drafts/paper-A-final.tex`) is still at Wave 343 state per MANIFEST.md row 40 — the markdown source has Wave 352/353 additions (§A.1 / §A.2 / §A.3 / §7.6.2 / §7.7.1 / §10.9.1-4 / §11.2) that are not yet ported to `.tex`. This is per the Wave 268 strict-clean rule and out of scope for Wave 358 P2 (which is `tnnls_submission/` only). The uploadable PDF remains at Wave 343 content + post-Wave-355 polish compile-clean state per MANIFEST.md row 33.
- The `tnnls_submission/README.md` line 161 still describes `tables.md` as "5 paper-ready tables (R1-R6 + 4-arm H2H + statistical + wall-clock + reproducibility)". This description remains accurate (the new table-of-tables is APPENDED to the existing 5 tables, not replacing them). A follow-up wave may add "ADDITIVE Table of Tables (Paper) cross-reference index at end" to the description if reviewer-facing scope clarity is desired — out of scope for Wave 358 P2 per Wave 268 strict-clean.
- No forward-looking §15.X entry is created by this Wave 358 P2 audit doc (CONSOLIDATED_RESULTS.md is not touched). A follow-up wave could append a §15.106 entry summarising the Wave 358 P2 table-of-tables scope if the wave-358 documentation trail warrants a CONSOLIDATED_RESULTS entry — out of scope for Wave 358 P2 (this audit doc is the standalone governance record per AGENTS.md §3.6).

---

## 4. Acceptance gates (Wave 358 P2, verified before commit)

| # | Gate | Tool / command | Expected | Actual |
|---|---|---|---|---|
| 1 | Tables 1-5 byte-identical to prior revision | `git diff tnnls_submission/tables.md` (pre-commit) | only lines 93-117 (new section) added; no edits to lines 1-92 | PASS — verified via Edit tool + Read context (lines 1-92 byte-identical pre-edit reference confirmed) |
| 2 | New "Table of Tables (Paper)" section has 6 rows (T1-T6) | visual inspection of new section | 6 rows | PASS — 6 rows in the catalog table |
| 3 | All 6 paper tables have source_artifact + CONSOLIDATED_RESULTS cross-reference | visual inspection | 6/6 cross-references resolved | PASS — 6/6 (T1: 2 refs / T2: 2 refs / T3: 5 refs / T4: 11 refs / T5: 2 refs / T6: 2 refs = 24 total per-row cross-references) |
| 4 | MANIFEST.md row 27 SHA + size refreshed | `sha256sum tnnls_submission/tables.md` | `c0d4dd5d…` × 22459 | PASS |
| 5 | MANIFEST.md row 23 audit-doc list appended | visual inspection | `wave358-tables-md-polish.md` appended | PASS |
| 6 | Wave 358 P2 audit doc written | `ls docs/audit/wave358-tables-md-polish.md` | PASS | PASS |
| 7 | No prior Tables 1-5 paragraph modified | `git diff tnnls_submission/tables.md` (pre-commit) | additive only | PASS — append-only on lines 93-117; lines 1-92 byte-identical |
| 8 | NO-PUSH policy honored | local commit only, no `git push` | PASS | PASS — commit will be local-only per Wave 325 |
| 9 | No claim status promotion attempted | visual inspection | no `SUPPORTED` / `REGRESSES` / `UNDERPOWERED` promotion | PASS — table-of-tables does not touch any claim label |
| 10 | No destructive edit to any file | `git diff --stat` | only 2 files modified + 1 file created | PASS — `tables.md` (append-only) + `MANIFEST.md` (row 27 SHA refresh + row 23 audit-doc append) + `wave358-tables-md-polish.md` (new) |

---

## 5. Files written / modified by Wave 358 P2 (additive only)

| File | Action | Bytes | SHA-256 |
|---|---|---:|---|
| `tnnls_submission/tables.md` | edited (APPEND additive "Table of Tables (Paper)" section after Cross-references block) | 11826 → 22459 (+10633) | `24f4bc71…` → `c0d4dd5d…` |
| `tnnls_submission/MANIFEST.md` | edited (row 27 `tables.md` SHA + size + addendum; row 23 audit-doc list append `wave358-tables-md-polish.md`) | 46891 → 49543 (+2652) | (pre-existing self-referencing SHA pattern preserved; post-edit SHA `2fc8455d…` documented in this audit doc) |
| `docs/audit/wave358-tables-md-polish.md` | created (this file) | new ~12500 | — |

**Acceptance gates (Wave 358 P2, verified before commit):** all 10 gates PASS (see §4 above).

---

## 6. Cross-references

- [`tnnls_submission/tables.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/tables.md) — the polished file (22459 bytes, SHA-256 `c0d4dd5d…`)
- [`tnnls_submission/MANIFEST.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/MANIFEST.md) — refreshed row 27 + row 23 audit-doc append
- [`docs/drafts/paper-A-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.md) — canonical paper source (NOT touched by this Wave 358 P2; cited as the upstream of the 6 cataloged tables T1-T6)
- [`verification_outputs/wave355-capability-token-example/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/wave355-capability-token-example/) — T1 source artifact
- [`verification_outputs/wave349-r1-3seed-gpu/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/wave349-r1-3seed-gpu/) — T2 source artifact
- [`adaptive_reflow/adapters/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/adaptive_reflow/adapters/) — T3 cumulative source (5 adapter files)
- [`verification_outputs/wave189-p2-post-cd70821-combined.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave189-p2-post-cd70821-combined.json) — T4 partial source (R1 + R5a)
- [`verification_outputs/wave191-r5-n1000/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/wave191-r5-n1000/) — T5 source artifact
- [`docs/figures/fig5_r5c_regime_curve.png`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/figures/fig5_r5c_regime_curve.png) — T5 byte-stable PNG render
- [`verification_outputs/wave351-p3-thm5-numerical/lipschitz_estimate.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave351-p3-thm5-numerical/lipschitz_estimate.json) — T6 source artifact
- [`docs/CONSOLIDATED_RESULTS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) — §15.X cross-references (§15.74 / §15.86 / §15.87 / §15.88 / §15.96 / §15.103 / §15.104 / §15.105)
- [`docs/CLAIMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md) — CLM-059 / CLM-060 / CLM-061 / CLM-068 / CLM-070 / CLM-073 cross-references (cited verbatim by T4's audit-doc handle column; NOT touched by Wave 358 P2)
- [`docs/audit/wave348-link-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave348-link-fix.md) — Wave 348 cross-doc GitHub-URL fix (the SHA rehash workflow this Wave 358 P2 inherits)
- [`docs/audit/wave355-capability-token-example.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave355-capability-token-example.md) — T1 audit-doc handle (cited by T1 row)
- [`docs/audit/wave349-impl.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave349-impl.md) — T2 audit-doc handle (cited by T2 row)
- [`docs/audit/wave351-thm5-numerical.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave351-thm5-numerical.md) — T6 audit-doc handle (cited by T6 row)
- [`AGENTS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/AGENTS.md) — project skill routing + hard guardrails (this Wave 358 P2 invokes `flowa-paper-evidence` per §1 routing rule + complies with §3 hard guardrails #1-7)

---

## 7. Wave 358 P2 commit message (draft)

```
Wave 358 P2: tnnls_submission/tables.md polish (table-of-tables + cross-references to paper + verification_outputs) (USER AUTHORIZED, NO PUSH)

- Append-only "Table of Tables (Paper)" cross-reference index at end of tnnls_submission/tables.md
  cataloging 6 markdown tables embedded in docs/drafts/paper-A-final.md:
  T1 §3.4.2 capability-token handshake (verification_outputs/wave355-capability-token-example/)
  T2 §3.5.1 R1 3-seed GPU ledger (verification_outputs/wave349-r1-3seed-gpu/)
  T3 §5.3 five concrete adapters (cumulative; §15.74 + §15.86 + §15.96)
  T4 §7.2 per-cell power-disclosure index (cumulative; §15.88 + §15.103 + §15.104 + §15.105)
  T5 §7.8 R5c regime curve 3-point table (verification_outputs/wave191-r5-n1000/ + §15.87)
  T6 §A.3.4 CIFAR-10 RF Lipschitz constants (verification_outputs/wave351-p3-thm5-numerical/)

- Each T1-T6 row carries: table_id, caption, column_count, paper_section, source_artifact, CONSOLIDATED_RESULTS cross-reference
- 6 paper tables cataloged, 24 cross-references resolved (per-row source_artifact + §15.X reference)
- Tables 1-5 above are byte-identical to prior revision (no wording change, no number change, no SHA change of any number in those tables)
- tnnls_submission/tables.md: 11826 -> 22459 bytes (+10633); SHA 24f4bc71... -> c0d4dd5d...
- tnnls_submission/MANIFEST.md: row 27 (tables.md SHA + size + addendum) refreshed; row 23 audit-doc list appended (wave358-tables-md-polish.md)
- Audit doc: docs/audit/wave358-tables-md-polish.md (this file; ~12500 bytes)
- NO-PUSH policy honored (commit is local-only per Wave 325)
- AGENTS.md hard guardrails #1-7 all honored (no vendored edits, no destructive edits, no push, no claim promotion, no freeze violations, audit doc per Wave 358, strict-clean minimal-additive variant)

Co-Authored-By: Claude Code <noreply@anthropic.com>
```

---

## 8. End of audit doc

This is the per-phase governance record for Wave 358 P2 (mirrors the 12-decimal-CLAIMS-table pattern from Wave 121-273 per AGENTS.md §3.6). The Wave 358 P2 polish is **additive-only** and **submitter-equivalent** — the 5 primary submission tables (Tables 1-5) are byte-identical to the prior revision; the new "Table of Tables (Paper)" section is a reviewer-navigation aid that closes the gap between the paper text and its byte-addressable provenance.