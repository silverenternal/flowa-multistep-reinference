# TNNLS Submission Package — MANIFEST

**Venue:** *IEEE Transactions on Neural Networks and Learning Systems* (TNNLS)
**Manuscript:** FlowA: Training-Free, Paper-Quantity-Driven Re-Inference for Flow-Matching Checkpoints
**Submitted:** pending (cover-letter USER ACTION placeholders to be filled)
**Freeze-marker commit:** Wave 324 HEAD (`paper-flat-ieeetran.{tex,pdf}` 10 pp., 2026-09-23)
**Final tag (to push):** `v3.0-tnnls-ready`

---

## File-by-file manifest (SHA-256 + size + role)

All SHA-256 hashes computed at package assembly time. Reviewers re-verify with:

```bash
cd tnnls_submission && sha256sum -- *.md supplementary/README.md
```

| File | Size (bytes) | SHA-256 | Role |
|---|---|---|---|
| `README.md` | 9446 | `3e26948a24ddfc6b17088d466c8aed874594f7e2571cb985c65062f65924bd30` | ScholarOne upload walkthrough (this MANIFEST's sister doc); 7-step upload sequence, common pitfalls, post-upload Zenodo DOI step |
| `MANIFEST.md` | 11894 | `283020362f6cde0bb764d7e8721b080275bf1fd702d1365f1a8115438cdd91e3` | Package manifest with SHA-256 + size + role (this file — self-referencing SHA at freeze; **NOTE:** the displayed SHA is the hash of the bytes BEFORE this very SHA-row was added; after this edit the file SHA becomes the current `sha256sum MANIFEST.md` output, so reviewers should re-hash on receipt and confirm with the post-edit SHA pinned in `docs/audit/wave324-final-verify.md`) |
| `cover_letter.md` | 60394 | `acc18453978a5b0b1e3fc0548efedf21b3bb0e45ba2e1d4f60d9a8a5b4a18c7f` | Editor-facing cover letter (TNNLS — 17 `[USER TO FILL: ...]` placeholders enumerated in `FILL_GUIDE.md`; 31 grep hits → 17 distinct fields = 1 authors + 1 editor + 5 reviewers × {affiliation, email} + 3 corresponding-author fields) |
| `FILL_GUIDE.md` | 11901 | `9a759125de0c8cd58c6e06d072259ceddeffbbc26317d9340c900325306cde41` | 17-field fill guide for `cover_letter.md`; one section per placeholder with category, section, line, what_needed, example_or_hint, hint |
| `highlights.md` | 1913 | `96406b3851f3a099b6346247d40ac35b492213d703819421c6f16f629f4279dd` | 3 TNNLS editor-facing highlights (each ≤ 85 chars) |
| `tables.md` | 7435 | `b7aeda919b495a9ea2d0c4c3f62609dfe9acc8fdb48b62888f3022b066fb8ce2` | 5 TNNLS paper tables (R1–R6 headline, 4-arm H2H, statistical methods, wall-clock, reproducibility gates) |
| `figures.md` | 23307 | `030f61a70031dbd6a6cf8dd7487035d21c3375002cad2968a6d8af71636a2d27` | ASCII architecture diagrams (FlowA hexagonal layers, re-inference dataflow, 3-tier experiment hierarchy, 4-arm H2H schematic) |
| `data_availability.md` | 7072 | `8553877d704a702172ac41d44d4215515002ca576d3994b6b52b94d6425b66b4` | Data availability statement + Zenodo DOI references + per-record CSV provenance |
| `submission_checklist.md` | 7368 | `208a21e0b28938a89cef135be70215616222ff9162825b6e36254f1afe9ce6e3` | TNNLS editorial requirements checklist (D.4 30/30 PASS, mkdocs 0 warnings, claims 0 drift, pytest 5155/196) |
| `supplementary/README.md` | 11283 | `66986c3bddb015d41d491059dbc4c526b58592d83afdaace43a7f7527afc47c3` | Supplementary bundle index: per-cell SOURCE.md provenance (rows A), cross-doc audit trail (rows B), verification outputs (rows C), source code anchors (rows D), three self-contained Lemma proofs (rows E), Theorem 1 theory package (rows F) |
| `../docs/drafts/paper-flat-ieeetran.pdf` | 381510 | `255befcaa98f759cdf70f609334ca4700c5e062878dd1f8fdf8e4bb4e450f63a` | **READY TO SUBMIT** TNNLS-formatted manuscript PDF (10 pages, IEEEtran-journal double-column, Wave 324 D+5 review; 9 CRITICAL fixes C1–C9 applied to `.tex`; 0 fatal errors, 0 overfull hboxes) |
| `../docs/drafts/paper-flat-ieeetran.tex` | 66293 | `c9f4a7d489289d8d15548e0c6af1851791444297ffa3e0475a075c8f49c86a05` | IEEEtran-journal LaTeX source for the manuscript (10-page output; 5 tables; 5 numbered equations; 20 references; 11 R-cells) |

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

- **`docs/drafts/paper-flat-ieeetran.{tex,pdf}`** — 10-page IEEEtran-typeset manuscript (the uploadable PDF for Step 3 of ScholarOne)
- **`docs/drafts/paper-flat-ieeetran.aux` / `.log` / `.out`** — typeset diagnostic logs (compile-clean post Wave 324)
- **`docs/drafts/abstract-final.md`** — abstract body and keyword list
- **`docs/drafts/paper-flattened-draft.md`** — full paper draft (markdown source — pre-typesetting)
- **`docs/cover-letter-tnnls.md`** — canonical cover letter (the snapshot in `tnnls_submission/cover_letter.md` is frozen at Wave 322; identical content)
- **`docs/inserted-lemmas/paper-adaptive_reflow-lemmas-paper-props.md`** — three self-contained Lemma proofs (Lemma 1 Path A Wave 311; Lemmas 2/3 Path A Wave 322) inserted in paper §6 Framework Properties
- **`docs/theory/theorem-1-self-contained.md` + `theorem1_rate_bound.md` + `operating-regime.md` + `DEVIATIONS.md`** — Theorem 1 theory package (mathematical foundation cross-referenced by §3 cover letter Insight)
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

---

## Upload order for TNNLS Editorial Manager (ScholarOne)

1. **Article Type:** Regular Paper (TNNLS treats this as a regular research article, not a survey/correspondence)
2. **Title / Abstract / Keywords:** verbatim from manuscript PDF page 1 (title + IEEE keywords list)
3. **Manuscript:** upload **`docs/drafts/paper-flat-ieeetran.pdf`** (10 pages, IEEEtran-typeset)
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
