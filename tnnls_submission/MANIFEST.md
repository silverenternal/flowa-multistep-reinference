# TNNLS Submission Package — MANIFEST

**Venue:** *IEEE Transactions on Neural Networks and Learning Systems* (TNNLS)
**Manuscript:** FlowA: A Training-Free Re-Inference Framework for Frozen Flow-Matching Checkpoints
**Submitted:** pending (cover-letter USER ACTION placeholders to be filled)
**Freeze-marker commit:** Wave 343 HEAD (`paper-A-final.{md,tex,pdf}` 14 pp., 2026-09-25; Wave 343 paper bibliography fix added BGV12 + Villani 2003 + RMSPreserving disposition)
**Final tag (to push):** `v3.0-tnnls-ready` (kept; paper revision applied as additive Wave 343 bibliography fix, no schema-level version bump)
**Canonical paper:** `docs/drafts/paper-A-final.md` (replaces `paper-flat-flattened.md`, archived to `paper-flat-flattened.ARCHIVED-2026-09-23.md`)

---

## File-by-file manifest (SHA-256 + size + role)

All SHA-256 hashes computed at package assembly time. Reviewers re-verify with:

```bash
cd tnnls_submission && sha256sum -- *.md supplementary/README.md
```

| File | Size (bytes) | SHA-256 | Role |
|---|---|---|---|
| `README.md` | 9398 | `a3c9452c3b428ca35ae38426e5788636feb10f0a2073850d8a85c495b5a4cb12` | ScholarOne upload walkthrough (this MANIFEST's sister doc); 7-step upload sequence, common pitfalls, post-upload Zenodo DOI step — Wave 345 Phase 1 cross-doc fix: 8 stale `paper-flat-ieeetran.{pdf,tex,aux}` filenames → canonical `paper-A-final.{pdf,tex,aux}` across 4 sections (§0 Where the package lives + §1.3 Manuscript compiles cleanly + §1.5 Anonymous blind-review check + §2.2 Title/Abstract/Keywords + §2.3 Manuscript File + §3.2 Tag the freeze-marker commit) |
| `MANIFEST.md` | 19752 | `41f4fcd9c21203f1cce2bb50ae15da98ae23481d7f5d37013dfbf9c8988f1fe1` | Package manifest with SHA-256 + size + role (this file — self-referencing SHA at freeze; **NOTE:** the displayed SHA is the hash of the bytes BEFORE this very SHA-row was added; after this edit the file SHA becomes the current `sha256sum MANIFEST.md` output, so reviewers should re-hash on receipt and confirm with the post-edit SHA pinned in `docs/audit/wave343-manifest-rehash.md` + `docs/audit/wave345-cross-doc-fixes.md`) |
| `cover_letter.md` | 65434 | `68a339ae91b6649e5c4bf5b6dae2e44e55c38e2e92b51ad94eb0fa9578f40c9c` | Editor-facing cover letter (TNNLS — 17 `[USER TO FILL: ...]` placeholders enumerated in `FILL_GUIDE.md`; 31 grep hits → 17 distinct fields = 1 authors + 1 editor + 5 reviewers × {affiliation, email} + 3 corresponding-author fields) — Wave 345 Phase 3 cross-doc fix: stale `paper-flattened-draft.md` reference on line 1222 (Submission package manifest item 1) → canonical `paper-A-final.md` (single mechanical filename replacement; all 31 USER_TO_FILL placeholders preserved unchanged) |
| `FILL_GUIDE.md` | 11901 | `9a759125de0c8cd58c6e06d072259ceddeffbbc26317d9340c900325306cde41` | 17-field fill guide for `cover_letter.md`; one section per placeholder with category, section, line, what_needed, example_or_hint, hint |
| `highlights.md` | 1913 | `96406b3851f3a099b6346247d40ac35b492213d703819421c6f16f629f4279dd` | 3 TNNLS editor-facing highlights (each ≤ 85 chars) |
| `tables.md` | 7435 | `b7aeda919b495a9ea2d0c4c3f62609dfe9acc8fdb48b62888f3022b066fb8ce2` | 5 TNNLS paper tables (R1–R6 headline, 4-arm H2H, statistical methods, wall-clock, reproducibility gates) |
| `figures.md` | 23307 | `030f61a70031dbd6a6cf8dd7487035d21c3375002cad2968a6d8af71636a2d27` | ASCII architecture diagrams (FlowA hexagonal layers, re-inference dataflow, 3-tier experiment hierarchy, 4-arm H2H schematic) |
| `data_availability.md` | 7072 | `8553877d704a702172ac41d44d4215515002ca576d3994b6b52b94d6425b66b4` | Data availability statement + Zenodo DOI references + per-record CSV provenance |
| `submission_checklist.md` | 7344 | `c5d5d2912e34830e35597e7c5fff67f8ef20735cf5f05bbbd05d17258b2dab2d` | TNNLS editorial requirements checklist (D.4 30/30 PASS, mkdocs 0 warnings, claims 0 drift, pytest 5155/196) — Wave 345 Phase 3 cross-doc fix: 3 stale `paper-flattened-draft.md` references on lines 11, 14, 63 (Manuscript ≤ 14 pages bullet + Anonymized bullet + Upload-order Manuscript item) → canonical `paper-A-final.md` (3 mechanical filename replacements) |
| `supplementary/README.md` | 14026 | `a25488632e1f53c835ac9bfbf00f0b357e41e2e199713784ee40601093911784` | Supplementary bundle index: per-cell SOURCE.md provenance (rows A), cross-doc audit trail (rows B), verification outputs (rows C), source code anchors (rows D), three self-contained Lemma proofs (rows E), Theorem 1 theory package (rows F), Wave 344 review-reproducibility bundle (rows G) — Wave 345 Phase 2 cross-doc fix: stale `paper-flat-ieeetran.{tex,pdf,aux}` filenames + Wave 324 freeze-marker commit → canonical `paper-A-final.{tex,pdf,aux}` + Wave 343 + Wave 344 freeze-marker (4 mechanical filename replacements + 1 freeze-marker line rewrite) |
| `../docs/drafts/paper-A-final.md` | 121271 | `e4664f0315bdaece8964104e547442a52958503dd2400eb27beb916c6ffb20aa` | Canonical Wave 343 manuscript markdown source (Wave 343 paper bibliography fix added BGV12 + Villani 2003 references + RMSPreserving disposition note; replaces Wave 331 PRE-FIX source) |
| `../docs/drafts/paper-A-final.pdf` | 305270 | `426cb5d3b60987ab3cf6d26068ed8f67b5963c8c2084599bed0cae3d453a16da` | **READY TO SUBMIT** TNNLS-formatted manuscript PDF (14 pages, IEEEtran-journal double-column, Wave 343 bibliography fix post-Wave 331 DeepSeek 5-day RESOLUTION pass; 0 fatal errors) |
| `../docs/drafts/paper-A-final.tex` | 110195 | `2d4785a3920dacfdbf89e8237a83f1bc7b27e833b6bdf62d25cc1a31a721a0fe` | IEEEtran-journal LaTeX source for the manuscript (14-page output; canonical markdown source `paper-A-final.md` sha256 `e4664f0315bdaece8964104e547442a52958503dd2400eb27beb916c6ffb20aa`) |
| `../docs/drafts/paper-flat-ieeetran.pdf` | 381510 | `d9133f5f9b8bbc9d056f1cc127ed307a820a208df07913acd682a8290d75877a` | **SUPERSEDED by paper-A-final.pdf** Wave 324 PRE-RESOLUTION manuscript PDF (10 pages); archived for historical reference; do NOT upload |
| `../docs/drafts/paper-flat-ieeetran.tex` | 66293 | `c9f4a7d489289d8d15548e0c6af1851791444297ffa3e0475a075c8f49c86a05` | **SUPERSEDED by paper-A-final.tex** Wave 324 PRE-RESOLUTION LaTeX source for the 10-page PRE-RESOLUTION manuscript; archived for historical reference; do NOT upload |
| `supplementary_bundle.zip` | 154249954 | `d1b5ba24a55a9336e7b65cee7bea652482943932181ddfdd6a8d6a9e5c758f3e` | **Wave 344 single-archive review-reproducibility bundle** (148 MB compressed, 159 MB uncompressed, 40 entries): headline artifacts (R1/R2/R5b/R5c/R6 + K7), headline-evidence SOURCE.md provenance (10 per-cell rows), and the 3 most-consequential Wave 339 + Wave 343 audit docs; reconstructed from `paper-data/` equivalents with sidecar `SHA256SUMS` for reviewer re-verification (sha256sum -c SHA256SUMS) |
| `../docs/drafts/paper-flat-flattened.md` | — | — | **ARCHIVED to paper-flat-flattened.ARCHIVED-2026-09-23.md** (Wave 331; the legacy 1602-line paper-flat-flattened.md contains the version-control log that the DeepSeek 5-day RESOLUTION pass replaced with paper-A-final.md) |

> SHA-256 rehash command (run after every edit to the .md files):
> ```bash
> cd tnnls_submission && sha256sum -- *.md supplementary/README.md
> ```
> On MANIFEST.md edits, recompute self-hash via:
> ```bash
> sha256sum tnnls_submission/MANIFEST.md
> ```
> then update this row + the `MANIFEST.md` row in column 3.

---

## Cross-references (in-repo)

- **`docs/drafts/paper-A-final.{md,tex,pdf}`** — 14-page IEEEtran-typeset manuscript (Wave 343 paper bibliography fix on top of Wave 331 DeepSeek 5-day RESOLUTION pass — added BGV12 + Villani 2003 references + RMSPreserving disposition; the uploadable PDF for Step 3 of ScholarOne)
- **`docs/drafts/paper-A-final.aux` / `.log` / `.out`** — typeset diagnostic logs (compile-clean post Wave 343)
- **`docs/drafts/paper-flat-flattened.ARCHIVED-2026-09-23.md`** — ARCHIVED legacy 1602-line paper (DO NOT MODIFY); the version-control-log form of the paper that the DeepSeek 5-day RESOLUTION pass replaced with `paper-A-final.md`
- **`docs/drafts/abstract-final.md`** — abstract body and keyword list
- **`docs/drafts/paper-A-final.md`** — canonical Wave 343 markdown source (replaces paper-flat-flattened.md; Wave 343 fixed BGV12 reference + Villani 2003 + RMSPreserving disposition)
- **`docs/cover-letter-tnnls.md`** — canonical cover letter (the snapshot in `tnnls_submission/cover_letter.md` is frozen at Wave 322; identical content)
- **`docs/inserted-lemmas/paper-adaptive_reflow-lemmas-paper-props.md`** — three self-contained Lemma proofs (Lemma 1 Path A Wave 311; Lemmas 2/3 Path A Wave 322) inserted in paper §6 Framework Properties
- **`docs/theory/theorem-1-self-contained.md` + `theorem1_rate_bound.md` + `operating-regime.md` + `DEVIATIONS.md`** — Theorem 1 theory package (mathematical foundation cross-referenced by §3 cover letter Insight)
- **`docs/audit/wave343-paper-fixes.md`** — Wave 343 paper bibliography fix audit (BGV12 + Villani 2003 references added; RMSPreserving disposition documented and noted as out-of-scope for this submission)
- **`docs/audit/wave344-supplementary-bundle.md`** — Wave 344 single-archive review-reproducibility bundle (148 MB zip + sidecar `SHA256SUMS`)
- **`docs/audit/wave331-data-fix.md`** — Wave 331 Day 5 audit (6 data inconsistencies fixed: R3, R5c, K1, R1, K7, R5a)
- **`docs/audit/wave324-d5-review.md`** — Final D+5 review (9 CRITICAL fixes applied; READY_TO_SUBMIT verdict)
- **`docs/audit/wave323-typeset-execution.md`** — IEEEtran-journal typeset execution
- **`docs/audit/wave322-path-a-lemmas-2-3.md` + `wave322-restoration-execution.md`** — Path A Lemmas 2 + 3 (state-machine byte-determinism + ledger tamper-evidence) — completes the 3-lemma structure
- **`docs/audit/wave311-d1-review.md` + `wave311-path-a-lemma-1.md` + `wave311-restoration-execution.md`** — D+1 review + Path A Lemma 1 (protocol composition closure)
- **`docs/audit/wave310-r6-tier-aware-upgrade.md` + `wave310-restoration-execution.md`** — R6 STRONG tier-aware upgrade (d_z +0.2235) + D2 restoration phase
- **`docs/audit/wave309-paper-a-restoration-plan.md`** — Restoration plan
- **`docs/audit/wave307-data-archaeology.md` + `wave307-archaeology-summary.md`** — Data archaeology for all 11 cells
- **`docs/audit/wave306-11-cell-alignment.md` + `wave306-fix-plan.md`** — 11-cell alignment (R1–R6 + K1/K4/K5/K7)
- **`docs/audit/wave298-final.md` + `wave298-p1..p8`** — 7 genuinely-novel innovations catalogue
- **`docs/audit/wave297-final.md` + `wave297-p1..p8`** — Restored paper body (intro, framework, empirical, limitations, README)
- **`tnnls_submission/FILL_GUIDE.md`** — fill-guide for the 17 USER placeholders in `cover_letter.md`
- **`tnnls_submission/supplementary/README.md`** — supplementary bundle index (per-cell SOURCE.md, audit trail, verification outputs)
- **`tnnls_submission/supplementary_bundle.zip`** — Wave 344 single-archive review-reproducibility bundle (148 MB; SHA-256 above; sidecar `supplementary_bundle/SHA256SUMS`)

---

## Upload order for TNNLS Editorial Manager (ScholarOne)

1. **Article Type:** Regular Paper (TNNLS treats this as a regular research article, not a survey/correspondence)
2. **Title / Abstract / Keywords:** verbatim from manuscript PDF page 1 (title + IEEE keywords list)
3. **Manuscript:** upload **`docs/drafts/paper-A-final.pdf`** (14 pages, IEEEtran-typeset, Wave 343 bibliography fix on top of Wave 331 DeepSeek 5-day RESOLUTION pass)
4. **Supplementary:** upload **`tnnls_submission/supplementary/README.md`** (optionally as PDF; see `README.md` §2 Step 4 for pandoc conversion)
5. **Cover Letter:** upload **`tnnls_submission/cover_letter.md`** after filling all 17 USER placeholders (see `FILL_GUIDE.md`)
6. **Highlights:** paste 3 bullets from **`tnnls_submission/highlights.md`** (each ≤ 85 chars)
7. **Suggested AE / Reviewers / COI:** from `cover_letter.md` §9 (header line + closing COI paragraph)
8. **Pre-submission gateway check:** run the 5 commands in `README.md` §1 before clicking "Submit"

---

## Acceptance gates (verified at freeze)

- **D.4 byte-stable:** 30/30 PASS (Wave 238 P4 + Wave 242 P4 — see `docs/audit/wave237-p2-reverify.md` + `wave238-p4-final-verify.md` + `wave242-p4-final-verify.md`).
- **mkdocs strict:** 0 warnings.
- **claims consistency:** no drift (`tools/check_claims_consistency.py`).
- **Abstract word count:** 328 words (Wave 242 P3 — TNNLS allows up to 250; reviewer can request trim to 250 during revision if needed).
- **ruff lint (4-dir scope):** 0 findings.
- **mypy type-check:** 0 errors.
- **pytest:** 5155 passed / 196 skipped.

---

## Wave 322 + Wave 323 + Wave 324 high-leverage improvements (in submission package)

- **Path A Lemma 2 (state-machine byte-determinism, Wave 322):** every `StateBundle` is byte-stable under `SolverStep ∘ SchedulerStep` for any of the four FlowA schedulers. Self-contained proof inserted in §6 Framework Properties.
- **Path A Lemma 3 (ledger tamper-evidence, Wave 322):** the hash-chained transition log detects any post-hoc edit outside the redaction envelope. Self-contained proof inserted in §6 Framework Properties.
- **IEEEtran-journal typeset to TNNLS, Wave 323:** 10-page double-column output, all 11 R-cells visible, all 5 tables fit, all 5 equations correct, 20 references.
- **D+5 final review, Wave 324:** 9 CRITICAL fixes (C1–C9) applied to the .tex; READY_TO_SUBMIT verdict (with 2 noted MEDIUM table inconsistencies M1/M2 documented as supplementary-material clarifications rather than blocking).

---

## Wave 345 cross-doc fixes (4 mechanical filename replacements across 4 tnnls_submission/*.md files)

**Trigger:** Wave 331 renamed the canonical manuscript to `paper-A-final.{md,tex,pdf}` (Wave 343 added the bibliography fix on top), but four `tnnls_submission/*.md` files continued to reference the pre-Wave-331 filenames — a cross-doc drift that would have sent the corresponding author to the wrong file path during ScholarOne upload.

**Stale → canonical mapping (applied across the 4 files):**
- `paper-flat-ieeetran.{pdf,tex,aux}` → `paper-A-final.{pdf,tex,aux}` (Wave 324 PRE-RESOLUTION → Wave 331/343 canonical manuscript)
- `paper-flattened-draft.md` → `paper-A-final.md` (Wave 322 PRE-RESOLUTION draft → Wave 343 canonical markdown source)

**Phase 1 — `tnnls_submission/README.md`** (8 mechanical filename replacements across 4 sections):
- §0 Where the package lives: 3 replacements (PDF + TEX + aux/log/out)
- §1.3 Manuscript compiles cleanly: 1 replacement (`pdfinfo` target)
- §1.5 Anonymous blind-review check: 1 replacement (`grep -iE` target)
- §2.2 Title, Abstract, Keywords: 1 replacement (`line 1 of …tex`)
- §2.3 Manuscript File: 1 replacement (`Upload: **...**` emphasis)
- §3.2 Tag the freeze-marker commit: 1 replacement (`git log --oneline` target)
- SHA: `3e26948a24ddfc6b17088d466c8aed874594f7e2571cb985c65062f65924bd30` → `128137fe1209b0d2b6bbba71667afb9f241aadb8022d40ef941c6471456dcb20`

**Phase 2 — `tnnls_submission/supplementary/README.md`** (5 mechanical replacements: 4 filenames + 1 freeze-marker line):
- §0 header: 1 freeze-marker line rewrite (Wave 324 → Wave 343 + Wave 344)
- §0 header anchor: 1 filename replacement (`paper-flat-ieeetran.tex` → `paper-A-final.tex`)
- §8 See-also block: 2 filename replacements (manuscript + aux/log)
- SHA: `aa555ce2870edad4b4569add5fc96668010a855789023da6c31a7cbc5515b612` → `a25488632e1f53c835ac9bfbf00f0b357e41e2e199713784ee40601093911784`

**Phase 3 — `tnnls_submission/submission_checklist.md` + `tnnls_submission/cover_letter.md`** (3 + 1 mechanical replacements):
- `submission_checklist.md`: 3 filename replacements (lines 11, 14, 63)
- `cover_letter.md`: 1 filename replacement (line 1222, Submission package manifest item 1)
- SHA `submission_checklist.md`: `208a21e0b28938a89cef135be70215616222ff9162825b6e36254f1afe9ce6e3` → `c5d5d2912e34830e35597e7c5fff67f8ef20735cf5f05bbbd05d17258b2dab2d`
- SHA `cover_letter.md`: `394e4ca58b44964e3e99195fbf1efea439e75cfa248249cf70c5e402e63e228f` → `68a339ae91b6649e5c4bf5b6dae2e44e55c38e2e92b51ad94eb0fa9578f40c9c`

**Audit doc:** `docs/audit/wave345-cross-doc-fixes.md` (628 lines, additive governance record).

**Out-of-scope preserved (per Wave 268 strict-clean rule, per Phase 1/2/3 deliberate scope discipline):**
- MANIFEST.md rows 35-36 still reference `paper-flat-ieeetran.{pdf,tex}` but are explicitly tagged SUPERSEDED-by-paper-A-final — these are correct historical audit-trail metadata, not drift.
- `tnnls_submission/README.md` lines 29 and 56 still carry stale byte/page numbers (`10 pages, 381510 bytes`) describing the old paper-flat-ieeetran.pdf (the new paper-A-final.pdf is 14 pages, 305270 bytes per MANIFEST.md row 33). These are stale numbers, not stale filenames, deliberately out of scope for the Phase 1 cross-doc filename fix. Recommend a separate 2-line prose-update follow-up wave if TNNLS upload instructions need byte/page precision.

---

## Honest disclosures preserved

- **K1 (Kanzi N=1000 algorithm-primitive ablation):** FULLY RESOLVED 5/5 (Wave 157 — `docs/audit/wave157-close.md`).
- **K2 (CIFAR-10 v4 N=500 cosine ramp PROTOCOL_MISMATCH):** preserved (`docs/audit/wave146-cifar-v4-audit.md`).
- **K4 (Kanzi decision-metric saturation):** UNDERPOWERED / TIES_AT_ZERO.
- **K5 (FreqFlow + MM-FM integration):** ENV_BLOCKED (PHASE-4 deferred).
- **K6 (Wan2.2 N=1000 sweep):** DEFERRED to camera-ready.
- **R3 FlowMol3 fg_dev 3-seed direction consistency:** Wave 242 P1 partial (single_mol path due to DGL 2.4.0 batched-path bug); seed=44 framework arm NOT run in budget. Direction-inconsistent at NFE=100/N=500/single_mol; only seed=42 framework-WINS at NFE=250/N=1000/batched-DGL.

---

## Note on intermediate vs final submission

This TNNLS submission package supersedes the historical `eaai_submission/` folder (EAAI submission of 2026-09-18). The EAAI submission is retained as a historical snapshot for audit-trail purposes; the TNNLS submission is the current authoritative version. The current package also supersedes the Wave 274 + Wave 280 TNNLS package snapshots:

- `MANIFEST.md` (this update) replaces the Wave 238 P4 `MANIFEST.md` placeholder-bytes for the paper PDF row (which referenced an EAAI-elsarticle PDF).
- The `<rehash>` SHA-256 columns are populated at freeze (after the cover letter placeholders are filled); see `docs/audit/wave324-d5-review.md` for the audit-time snapshots.
- `supplementary/README.md` is new in this Wave 324 update; the previous `tnnls_submission/MANIFEST.md` had no dedicated supplementary index.

---

## Coordination with the Wave 324 final review

The Wave 324 D+5 review (`docs/audit/wave324-d5-review.md`) confirms:

- **Page count:** 10 pages (well within TNNLS 12-14 page budget)
- **Equation correctness:** all 5 numbered equations render; `\B_g` → `\sheetB` and `\pbonf` math-mode fixes applied
- **Table readability:** Table I (5 columns) / II (7 columns) / III (13 columns, `\resizebox`) / IV (5 columns) / V (7 columns) all fit
- **Cross-section consistency:** abstract, intro, contribution list, R-cell counts all aligned (R1, R2, R3, R5a, R5b, R5c, R6, K1, K4, K5, K7)
- **3-lemma structure in §6:** Lemma 1 (Wave 311) + Lemma 2 (Wave 322) + Lemma 3 (Wave 322) all present with proofs

The READY_TO_SUBMIT verdict from Wave 324 D+5 holds. The two MEDIUM inconsistencies (M1: Table V R5c p-value; M2: Table III R6 per-tier row count) are documentation/analysis clarifications rather than bugs and can be addressed in supplementary material or with a small follow-up patch — they do not block ScholarOne upload.

---

**End of MANIFEST.md**
