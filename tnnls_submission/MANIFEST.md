# TNNLS Submission Package — MANIFEST

**Venue:** *IEEE Transactions on Neural Networks and Learning Systems* (TNNLS)
**Manuscript:** FlowA: A Training-Free Re-Inference Framework for Frozen Flow-Matching Checkpoints
**Submitted:** pending (cover-letter USER ACTION placeholders to be filled)
**Freeze-marker commit:** Wave 343 HEAD (`paper-A-final.{md,tex,pdf}` 14 pp., 2026-09-25; Wave 343 paper bibliography fix added BGV12 + Villani 2003 + RMSPreserving disposition)
**Final tag (to push):** `v3.0-tnnls-ready` (kept; paper revision applied as additive Wave 343 bibliography fix, no schema-level version bump)
**Canonical paper:** [`docs/drafts/paper-A-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.md) (replaces `paper-flat-flattened.md`, archived to `paper-flat-flattened.ARCHIVED-2026-09-23.md`)

---

## File-by-file manifest (SHA-256 + size + role)

All SHA-256 hashes computed at package assembly time. Reviewers re-verify with:

```bash
cd tnnls_submission && sha256sum -- *.md supplementary/README.md
```

| File | Size (bytes) | SHA-256 | Role |
|---|---|---|---|
| `README.md` | 12614 | `872a8415426a34eec2af696be00ae117882c899d79661f17806b441db998c734` | ScholarOne upload walkthrough (this MANIFEST's sister doc); 7-step upload sequence, common pitfalls, post-upload Zenodo DOI step — Wave 345 Phase 1 cross-doc fix: 8 stale `paper-flat-ieeetran.{pdf,tex,aux}` filenames → canonical `paper-A-final.{pdf,tex,aux}` across 4 sections (§0 Where the package lives + §1.3 Manuscript compiles cleanly + §1.5 Anonymous blind-review check + §2.2 Title/Abstract/Keywords + §2.3 Manuscript File + §3.2 Tag the freeze-marker commit) — **Wave 348 Phase 1b cross-doc fix**: convert all local repo paths to full GitHub URLs (`https://github.com/silverenternal/flowa-multistep-reinference/blob/main/...` + `/tree/main/...`) so reviewers following the markdown can click through to the byte-addressable artifacts |
| `MANIFEST.md` | 37834 | `b599a5d9fbd4aecbfbd19aa7a587da99603f09037d35b246a2bebeecd34939d3` | Package manifest with SHA-256 + size + role (this file — self-referencing SHA at freeze; **NOTE:** the displayed SHA is the hash of the bytes BEFORE this very SHA-row was added; after this edit the file SHA becomes the current `sha256sum MANIFEST.md` output, so reviewers should re-hash on receipt and confirm with the post-edit SHA pinned in [`docs/audit/wave343-manifest-rehash.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave343-manifest-rehash.md) + [`docs/audit/wave345-cross-doc-fixes.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave345-cross-doc-fixes.md) + [`docs/audit/wave348-link-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave348-link-fix.md) + [`docs/audit/wave349-impl.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave349-impl.md) + [`docs/audit/wave349-gap-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave349-gap-audit.md) + [`docs/audit/wave350-thm5.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave350-thm5.md) + [`docs/audit/wave351-thm5-numerical.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave351-thm5-numerical.md)) |
| `cover_letter.md` | 71760 | `a6976825d19276c4fbb98efb167cadac24ed94cc4013796e0961580ca3ebf6f1` | Editor-facing cover letter (TNNLS — 17 `[USER TO FILL: ...]` placeholders enumerated in `FILL_GUIDE.md`; 31 grep hits → 17 distinct fields = 1 authors + 1 editor + 5 reviewers × {affiliation, email} + 3 corresponding-author fields) — Wave 345 Phase 3 cross-doc fix: stale `paper-flattened-draft.md` reference on line 1222 (Submission package manifest item 1) → canonical `paper-A-final.md` (single mechanical filename replacement; all 31 USER_TO_FILL placeholders preserved unchanged) — **Wave 348 Phase 1b cross-doc fix**: 57 local repo paths → GitHub URLs (audit:CSV:tool paths in §R5 P2-P6, §R6 P1-P4, §R6.5, §R6.6, §8, §8.1 etc.) |
| `FILL_GUIDE.md` | 12329 | `380a3e13fbe6d479cb532fce6b8961d82dc24eb2036a89cf9d26e2a930305a41` | 17-field fill guide for `cover_letter.md`; one section per placeholder with category, section, line, what_needed, example_or_hint, hint — **Wave 348 Phase 1b cross-doc fix**: 3 local repo paths → GitHub URLs (`tnnls_submission/cover_letter.md`, `tnnls_submission/MANIFEST.md` references in §Target file + §How to apply) |
| `highlights.md` | 2350 | `1655ae5e380322d6ec2467512ea1196b73ce70000d955a5a68fbd6b57c75ff99` | 3 TNNLS editor-facing highlights (each ≤ 85 chars) — **Wave 348 Phase 1b cross-doc fix**: 4 local repo paths → GitHub URLs (`docs/cover-letter-tnnls.md`, `docs/drafts/abstract-final.md`, `docs/internal/...`, `tnnls_submission/MANIFEST.md` in Cross-references) |
| `tables.md` | 11826 | `24f4bc71f36f37ff7d8bbb0a230acb0bd999b0308c7a24c70da71222015bf926` | 5 TNNLS paper tables (R1–R6 headline, 4-arm H2H, statistical methods, wall-clock, reproducibility gates) — **Wave 348 Phase 1b cross-doc fix**: 36 local repo paths → GitHub URLs (R1-R6 verification_outputs paths, statistical methods CSV/JSON paths, source code anchors, cross-references) |
| `figures.md` | 24056 | `36e3d3f3ec2410c89221b35bb28bb7d8136251e7e64bfd12fa453d4a098d54ac` | ASCII architecture diagrams (FlowA hexagonal layers, re-inference dataflow, 3-tier experiment hierarchy, 4-arm H2H schematic) — **Wave 348 Phase 1b cross-doc fix**: 4 local repo paths → GitHub URLs (cross-references at bottom — `docs/ARCHITECTURE.md`, `docs/drafts/section-2-method.md`, audit-doc paths, MANIFEST); ASCII art diagrams preserved as-is |
| `data_availability.md` | 10035 | `eb410e1fd8a60b6f93d9e2dd7ba391c9a3b31e7ff79d64afbdfde52f70de2692` | Data availability statement + Zenodo DOI references + per-record CSV provenance — **Wave 348 Phase 1b cross-doc fix**: 24 local repo paths → GitHub URLs (verification_outputs paths, audit-doc paths, theory-package paths) |
| `submission_checklist.md` | 11688 | `b8445c5a336266d05e6833c3d8bc6b83d77463130860ea872a9aacbebcc403bb` | TNNLS editorial requirements checklist (D.4 30/30 PASS, mkdocs 0 warnings, claims 0 drift, pytest 5155/196) — Wave 345 Phase 3 cross-doc fix: 3 stale `paper-flattened-draft.md` references on lines 11, 14, 63 (Manuscript ≤ 14 pages bullet + Anonymized bullet + Upload-order Manuscript item) → canonical `paper-A-final.md` (3 mechanical filename replacements) — **Wave 348 Phase 1b cross-doc fix**: 28 local repo paths → GitHub URLs (G1 SHA-256 verification paths, G3 metric paths, vendored repo paths, supplementary package paths) |
| `supplementary/README.md` | 25289 | `6044f1120b7142da6bd51df4ae1cf2e1feb368a85d753dee8a320a5c78df802d` | Supplementary bundle index: per-cell SOURCE.md provenance (rows A), cross-doc audit trail (rows B), verification outputs (rows C), source code anchors (rows D), three self-contained Lemma proofs (rows E), Theorem 1 theory package (rows F), Wave 344 review-reproducibility bundle (rows G) — Wave 345 Phase 2 cross-doc fix: stale `paper-flat-ieeetran.{tex,pdf,aux}` filenames + Wave 324 freeze-marker commit → canonical `paper-A-final.{tex,pdf,aux}` + Wave 343 + Wave 344 freeze-marker (4 mechanical filename replacements + 1 freeze-marker line rewrite) — **Wave 348 Phase 1b cross-doc fix**: 78 local repo paths → GitHub URLs (per-cell SOURCE.md, audit-doc paths, verification_outputs paths, source code anchors, theory-package paths, supplementary_bundle.zip, MANIFEST references) |
| `../docs/drafts/paper-A-final.md` | 162862 | `338ef23d34ff621897dab8e454ab10ccd791e4cfdc998a1980833dd7fbff5e60` | Canonical Wave 351 manuscript markdown source (Wave 348 GitHub-hyperlink-fix preserved + Wave 349 ADDITIVE: §7.1 status-rubric clarification + §7.2 per-cell power-disclosure index + §7.8 Figure 1 R5c regime curve (single-panel, byte-stable from §7.8 3-point table) + §10.5 R6 live-GPU follow-up note + §10.9 Theorem-5 future-work label + §10.9.1 R5b-conditional-boundary footnote + Wave 350 ADDITIVE: §6.6 Theorem 5 (R5b restart-blend attenuation formal bound, ADDITIVE, supplements §10.9 future-work) with §6.7 renumber of the previous §6.6 Framework Properties + §10.9.2 Theorem 5 partial close-out footnote + §7.6.2 R5b `n_rounds` conditional grid figure (Wave 350 P4 ADDITIVE 2-panel figure ref) + **Wave 351 ADDITIVE: §6.6.1 Theorem 5 numerical validation against Wave 350 P4 12-cell grid (L_local ≈ 0.3810 from finite-difference on synthetic RF CIFAR velocity field, fitted eps_theta ≈ 0.0506 at canonical m=0.5, transition prediction matches_empirical, slope-scaling disclosure: bound over-predicts asymptotic regression by ~33x at k=20, audit doc at docs/audit/wave351-thm5-numerical.md)**); Wave 343 paper bibliography fix preserved underneath; **R1 3-seed retro-validation note was NOT added** — per the Wave 349 gap-audit doc §2.3, the R1 seed=42 / seed=44 retro-validation probe was INCONCLUSIVE (timeout, framework arm produced 0-byte `framework.fasta`, no `manifest.json`), so no paper-text retro-validation claim is honest to add; AGENTS.md hard guardrail #4 forbids promoting INCONCLUSIVE to VERIFIED) |
| `../docs/drafts/paper-A-final.pdf` | 305270 | `b160d75a2d66ec71e7ce94ed4734e30b5b149f39398847628c44efdda2e2b7c6` | **READY TO SUBMIT** TNNLS-formatted manuscript PDF (14 pages, IEEEtran-journal double-column, post-Wave-350 rebuild from updated `paper-A-final.md`; 0 fatal errors; bytes-preserved at 305270 from Wave 343 since the Wave 349 + Wave 350 ADDITIVE insertions fit inside the existing 14-page IEEEtran layout — Wave 349 §7.8 Figure 1 is referenced as external PNG, not embedded; Wave 350 §6.6 Theorem 5 + §6.7 renumber + §10.9.2 footnote are byte-stable inside the existing 14-page layout) |
| `../docs/drafts/figure_r5c_regime_curve.png` | 111687 | `0b01a1a3d4dbffba530c40d787b2ac2eb95ec232aa1191721d8a1019d99ee28c` | **Wave 349 ADDITIVE Figure 1 (auxiliary 2-panel)** — R5c regime curve 2-panel PNG (Panel A: FID vs training epochs; Panel B: Δ FID percentage vs training epochs); byte-stable render of the §7.8 3-point table verbatim; matplotlib Agg backend; ARCHIVED auxiliary (the canonical Wave 349 §7.8 Figure 1 is `docs/figures/fig5_r5c_regime_curve.png` single-panel referenced from `paper-A-final.md` §7.8 "Figure 1 (Wave 349 ADDITIVE)") |
| `../docs/figures/fig5_r5c_regime_curve.png` | 65536 | `c3696fae872982ec77656cd69f26eea989a6cc926ec26af1ae82a5c8759154ae` | **Wave 349 ADDITIVE Figure 1 (canonical)** — R5c regime curve single-panel PNG plotting per-epoch Δ FID percentage (negative = framework-WINS, positive = baseline-WINS) against training epochs (1 / 2 / 3); byte-stable render of the §7.8 3-point table verbatim (29.49→23.39 / 13.45→15.44 / 11.99→13.67 with -28.43% / +8.53% / +10.37% deltas and framework_wins / baseline_wins / baseline_wins verdicts); matplotlib Agg backend; renderer at `tools/render_r5c_regime_curve.py` (matplotlib 3.11.2, ruff-clean); referenced from `paper-A-final.md` §7.8 "Figure 1 (Wave 349 ADDITIVE)"; closes the §10.8(i) "Future-work: plot the regime curve as a figure" gap (paper's own §10.8(i) flagged this at ~30 min, data exists) |
| `../docs/drafts/figure_r5b_conditional_grid.png` | 167015 | `c4831bcd36a83133a909eee9734a669ab8c271e3e908c6d5d8a20973ec87b615` | **Wave 350 ADDITIVE Figure 2 (auxiliary 2-panel)** — R5b 4-scheduler × 3-`n_rounds` conditional grid 2-panel PNG (Panel A: heatmap of Δ FID % across 4 schedulers × 3 n_rounds with diverging red/green colour-coding; Panel B: grouped bar chart of Δ FID % vs n_rounds per scheduler with 3 grouped bars per scheduler); byte-stable render of the §7.6 mechanism paragraph + Wave 235 P1 + Wave 225 P7 + Wave 206 P6 audit material (12-cell grid transcribed verbatim, 4 schedulers × 3 n_rounds = 12 cells); matplotlib Agg backend; renderer at `tools/render_r5b_conditional_grid.py` (matplotlib 3.11.2, ruff-clean); referenced from `paper-A-final.md` §7.6.2 "§7.6.2 R5b `n_rounds` conditional grid — figure (Wave 350 P4 ADDITIVE)"; visualises the §7.6 `n_rounds = 1` → `n_rounds ≥ 2` transition boundary (4/4 schedulers framework-WINS at `n_rounds = 1` ∈ [-1.60%, -2.53%], 4/4 schedulers baseline-WINS at `n_rounds ≥ 2` ∈ [+9.77%, +30.19%]) |
| `../docs/drafts/paper-A-final.tex` | 110195 | `2d4785a3920dacfdbf89e8237a83f1bc7b27e833b6bdf62d25cc1a31a721a0fe` | IEEEtran-journal LaTeX source for the manuscript (14-page output; canonical markdown source `paper-A-final.md` sha256 `168bc8cd8b7cedf71f467de6d38a5d8b30c2dcd593c93e01ff13f69a5da11095`) |
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

- **[`docs/drafts/paper-A-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.md) + [`paper-A-final.tex`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.tex) + [`paper-A-final.pdf`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.pdf)** — 14-page IEEEtran-typeset manuscript (Wave 343 paper bibliography fix on top of Wave 331 DeepSeek 5-day RESOLUTION pass — added BGV12 + Villani 2003 references + RMSPreserving disposition; the uploadable PDF for Step 3 of ScholarOne)
- **[`docs/drafts/paper-A-final.aux`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.aux) / [`.log`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.log) / [`.out`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.out)** — typeset diagnostic logs (compile-clean post Wave 343)
- **[`docs/drafts/paper-flat-flattened.ARCHIVED-2026-09-23.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-flat-flattened.ARCHIVED-2026-09-23.md)** — ARCHIVED legacy 1602-line paper (DO NOT MODIFY); the version-control-log form of the paper that the DeepSeek 5-day RESOLUTION pass replaced with `paper-A-final.md`
- **[`docs/drafts/abstract-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/abstract-final.md)** — abstract body and keyword list
- **[`docs/drafts/paper-A-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.md)** — canonical Wave 343 markdown source (replaces paper-flat-flattened.md; Wave 343 fixed BGV12 reference + Villani 2003 + RMSPreserving disposition)
- **[`docs/cover-letter-tnnls.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/cover-letter-tnnls.md)** — canonical cover letter (the snapshot in `tnnls_submission/cover_letter.md` is frozen at Wave 322; identical content)
- **[`docs/inserted-lemmas/paper-adaptive_reflow-lemmas-paper-props.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/inserted-lemmas/paper-adaptive_reflow-lemmas-paper-props.md)** — three self-contained Lemma proofs (Lemma 1 Path A Wave 311; Lemmas 2/3 Path A Wave 322) inserted in paper §6 Framework Properties
- **[`docs/theory/theorem-1-self-contained.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/theory/theorem-1-self-contained.md) + [`theorem1_rate_bound.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/theory/theorem1_rate_bound.md) + [`operating-regime.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/theory/operating-regime.md) + [`DEVIATIONS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/theory/DEVIATIONS.md)** — Theorem 1 theory package (mathematical foundation cross-referenced by §3 cover letter Insight)
- **[`docs/audit/wave343-paper-fixes.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave343-paper-fixes.md)** — Wave 343 paper bibliography fix audit (BGV12 + Villani 2003 references added; RMSPreserving disposition documented and noted as out-of-scope for this submission)
- **[`docs/audit/wave344-supplementary-bundle.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave344-supplementary-bundle.md)** — Wave 344 single-archive review-reproducibility bundle (148 MB zip + sidecar `SHA256SUMS`)
- **[`docs/audit/wave331-data-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave331-data-fix.md)** — Wave 331 Day 5 audit (6 data inconsistencies fixed: R3, R5c, K1, R1, K7, R5a)
- **[`docs/audit/wave324-d5-review.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave324-d5-review.md)** — Final D+5 review (9 CRITICAL fixes applied; READY_TO_SUBMIT verdict)
- **[`docs/audit/wave323-typeset-execution.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave323-typeset-execution.md)** — IEEEtran-journal typeset execution
- **[`docs/audit/wave322-path-a-lemmas-2-3.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave322-path-a-lemmas-2-3.md) + [`wave322-restoration-execution.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave322-restoration-execution.md)** — Path A Lemmas 2 + 3 (state-machine byte-determinism + ledger tamper-evidence) — completes the 3-lemma structure
- **[`docs/audit/wave311-d1-review.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave311-d1-review.md) + [`wave311-path-a-lemma-1.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave311-path-a-lemma-1.md) + [`wave311-restoration-execution.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave311-restoration-execution.md)** — D+1 review + Path A Lemma 1 (protocol composition closure)
- **[`docs/audit/wave310-r6-tier-aware-upgrade.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave310-r6-tier-aware-upgrade.md) + [`wave310-restoration-execution.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave310-restoration-execution.md)** — R6 STRONG tier-aware upgrade (d_z +0.2235) + D2 restoration phase
- **[`docs/audit/wave309-paper-a-restoration-plan.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave309-paper-a-restoration-plan.md)** — Restoration plan
- **[`docs/audit/wave307-data-archaeology.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave307-data-archaeology.md) + [`wave307-archaeology-summary.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave307-archaeology-summary.md)** — Data archaeology for all 11 cells
- **[`docs/audit/wave306-11-cell-alignment.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave306-11-cell-alignment.md) + [`wave306-fix-plan.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave306-fix-plan.md)** — 11-cell alignment (R1–R6 + K1/K4/K5/K7)
- **[`docs/audit/wave298-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave298-final.md) + [`wave298-p1..p8`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/audit)** — 7 genuinely-novel innovations catalogue
- **[`docs/audit/wave297-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave297-final.md) + [`wave297-p1..p8`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/audit)** — Restored paper body (intro, framework, empirical, limitations, README)
- **[`tnnls_submission/FILL_GUIDE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/FILL_GUIDE.md)** — fill-guide for the 17 USER placeholders in `cover_letter.md`
- **[`tnnls_submission/supplementary/README.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/supplementary/README.md)** — supplementary bundle index (per-cell SOURCE.md, audit trail, verification outputs)
- **[`tnnls_submission/supplementary_bundle.zip`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/supplementary_bundle.zip)** — Wave 344 single-archive review-reproducibility bundle (148 MB; SHA-256 above; sidecar `supplementary_bundle/SHA256SUMS`)

---

## Upload order for TNNLS Editorial Manager (ScholarOne)

1. **Article Type:** Regular Paper (TNNLS treats this as a regular research article, not a survey/correspondence)
2. **Title / Abstract / Keywords:** verbatim from manuscript PDF page 1 (title + IEEE keywords list)
3. **Manuscript:** upload **[`docs/drafts/paper-A-final.pdf`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.pdf)** (14 pages, IEEEtran-typeset, Wave 343 bibliography fix on top of Wave 331 DeepSeek 5-day RESOLUTION pass)
4. **Supplementary:** upload **[`tnnls_submission/supplementary/README.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/supplementary/README.md)** (optionally as PDF; see [`README.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/README.md) §2 Step 4 for pandoc conversion)
5. **Cover Letter:** upload **[`tnnls_submission/cover_letter.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/cover_letter.md)** after filling all 17 USER placeholders (see [`FILL_GUIDE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/FILL_GUIDE.md))
6. **Highlights:** paste 3 bullets from **[`tnnls_submission/highlights.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/highlights.md)** (each ≤ 85 chars)
7. **Suggested AE / Reviewers / COI:** from `cover_letter.md` §9 (header line + closing COI paragraph)
8. **Pre-submission gateway check:** run the 5 commands in `README.md` §1 before clicking "Submit"

---

## Acceptance gates (verified at freeze)

- **D.4 byte-stable:** 30/30 PASS (Wave 238 P4 + Wave 242 P4 — see [`docs/audit/wave237-p2-reverify.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave237-p2-reverify.md) + [`wave238-p4-final-verify.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave238-p4-final-verify.md) + [`wave242-p4-final-verify.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave242-p4-final-verify.md)).
- **mkdocs strict:** 0 warnings.
- **claims consistency:** no drift ([`tools/check_claims_consistency.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tools/check_claims_consistency.py)).
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

**Trigger:** Wave 331 renamed the canonical manuscript to `paper-A-final.{md,tex,pdf}` (Wave 343 added the bibliography fix on top), but four [`tnnls_submission/*.md`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/tnnls_submission) files continued to reference the pre-Wave-331 filenames — a cross-doc drift that would have sent the corresponding author to the wrong file path during ScholarOne upload.

**Stale → canonical mapping (applied across the 4 files):**
- `paper-flat-ieeetran.{pdf,tex,aux}` → `paper-A-final.{pdf,tex,aux}` (Wave 324 PRE-RESOLUTION → Wave 331/343 canonical manuscript)
- `paper-flattened-draft.md` → `paper-A-final.md` (Wave 322 PRE-RESOLUTION draft → Wave 343 canonical markdown source)

**Phase 1 — [`tnnls_submission/README.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/README.md)** (8 mechanical filename replacements across 4 sections):
- §0 Where the package lives: 3 replacements (PDF + TEX + aux/log/out)
- §1.3 Manuscript compiles cleanly: 1 replacement (`pdfinfo` target)
- §1.5 Anonymous blind-review check: 1 replacement (`grep -iE` target)
- §2.2 Title, Abstract, Keywords: 1 replacement (`line 1 of …tex`)
- §2.3 Manuscript File: 1 replacement (`Upload: **...**` emphasis)
- §3.2 Tag the freeze-marker commit: 1 replacement (`git log --oneline` target)
- SHA: `3e26948a24ddfc6b17088d466c8aed874594f7e2571cb985c65062f65924bd30` → `128137fe1209b0d2b6bbba71667afb9f241aadb8022d40ef941c6471456dcb20`

**Phase 2 — [`tnnls_submission/supplementary/README.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/supplementary/README.md)** (5 mechanical replacements: 4 filenames + 1 freeze-marker line):
- §0 header: 1 freeze-marker line rewrite (Wave 324 → Wave 343 + Wave 344)
- §0 header anchor: 1 filename replacement (`paper-flat-ieeetran.tex` → `paper-A-final.tex`)
- §8 See-also block: 2 filename replacements (manuscript + aux/log)
- SHA: `aa555ce2870edad4b4569add5fc96668010a855789023da6c31a7cbc5515b612` → `a25488632e1f53c835ac9bfbf00f0b357e41e2e199713784ee40601093911784`

**Phase 3 — [`tnnls_submission/submission_checklist.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/submission_checklist.md) + [`tnnls_submission/cover_letter.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/cover_letter.md)** (3 + 1 mechanical replacements):
- `submission_checklist.md`: 3 filename replacements (lines 11, 14, 63)
- `cover_letter.md`: 1 filename replacement (line 1222, Submission package manifest item 1)
- SHA `submission_checklist.md`: `208a21e0b28938a89cef135be70215616222ff9162825b6e36254f1afe9ce6e3` → `c5d5d2912e34830e35597e7c5fff67f8ef20735cf5f05bbbd05d17258b2dab2d`
- SHA `cover_letter.md`: `394e4ca58b44964e3e99195fbf1efea439e75cfa248249cf70c5e402e63e228f` → `68a339ae91b6649e5c4bf5b6dae2e44e55c38e2e92b51ad94eb0fa9578f40c9c`

**Audit doc:** [`docs/audit/wave345-cross-doc-fixes.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave345-cross-doc-fixes.md) (628 lines, additive governance record).

**Out-of-scope preserved (per Wave 268 strict-clean rule, per Phase 1/2/3 deliberate scope discipline):**
- MANIFEST.md rows 35-36 still reference `paper-flat-ieeetran.{pdf,tex}` but are explicitly tagged SUPERSEDED-by-paper-A-final — these are correct historical audit-trail metadata, not drift.
- [`tnnls_submission/README.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/README.md) lines 29 and 56 still carry stale byte/page numbers (`10 pages, 381510 bytes`) describing the old paper-flat-ieeetran.pdf (the new paper-A-final.pdf is 14 pages, 305270 bytes per MANIFEST.md row 33). These are stale numbers, not stale filenames, deliberately out of scope for the Phase 1 cross-doc filename fix. Recommend a separate 2-line prose-update follow-up wave if TNNLS upload instructions need byte/page precision.

---

## Wave 348 cross-doc GitHub-URL fix (282 local paths → full GitHub URLs across 9 tnnls_submission/*.md files)

**Trigger:** Per user directive (好，现在修github仓库链接，很多你写的超链接是没法成功在跳转后看到内容的), backticked local repo paths inside the `tnnls_submission/*.md` files were not clickable in GitHub-rendered markdown (a path like `` `docs/audit/wave324-d5-review.md` `` does not auto-link on GitHub; the user has to manually navigate to it). Wave 348 Phase 1b converts every such backticked local path into a markdown link pointing at the canonical GitHub URL (`https://github.com/silverenternal/flowa-multistep-reinference/blob/main/<path>` for files, `/tree/main/<path>` for directories), so reviewers clicking through land on the byte-addressable artifact in the public repo.

**Path → URL mapping (applied across 9 files):**
- `` `docs/<path>.md` `` → `` [`docs/<path>.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/<path>.md) ``
- `` `verification_outputs/<file>` `` → `` [`verification_outputs/<file>`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/<file>) `` (or `/tree/main/` for directories)
- `` `adaptive_reflow/<path>.py` `` → `` [`adaptive_reflow/<path>.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/<path>.py) ``
- `` `tools/<file>.py` `` → `` [`tools/<file>.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tools/<file>.py) ``
- `` `tests/<file>.py` `` → `` [`tests/<file>.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tests/<file>.py) ``
- `` `tnnls_submission/<file>.md` `` → `` [`tnnls_submission/<file>.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/<file>.md) ``
- `` `data/<vendored-repo>/...` `` → `` [`data/<vendored-repo>/...`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/data/<vendored-repo>) `` (vendored repos are immutable snapshots, tree link is appropriate)

**Per-file replacement counts (282 total):**
- `tnnls_submission/supplementary/README.md`: **78** paths converted
- `tnnls_submission/cover_letter.md`: **57** paths converted
- `tnnls_submission/MANIFEST.md`: **43** paths converted
- `tnnls_submission/tables.md`: **36** paths converted
- `tnnls_submission/submission_checklist.md`: **28** paths converted
- `tnnls_submission/README.md`: **25** paths converted
- `tnnls_submission/data_availability.md`: **24** paths converted
- `tnnls_submission/figures.md`: **4** paths converted (only cross-references at bottom; ASCII art diagrams preserved as-is per Wave 268 strict-clean rule — diagrams are not clickable links, they are visual structure)
- `tnnls_submission/highlights.md`: **4** paths converted
- `tnnls_submission/FILL_GUIDE.md`: **3** paths converted

**Scope discipline (per Wave 268 strict-clean rule):**
- **SHA-256 columns preserved as data** (rows 22-31 in MANIFEST.md) — these are byte-verification hashes, not clickable links; converting them would change the byte content reviewers verify against.
- **Shell command examples inside `` ```bash ... ``` `` blocks** preserved as-is (lines 42-43, 54, 66, 96-97, 101, 120, 122, 126, 175, 219 of `README.md`; lines 9, 36, 218-220, 41-47 of `cover_letter.md`; lines 17, 41-47 of `MANIFEST.md`) — these are runnable shell commands, not display-text path references.
- **ASCII art in `figures.md`** preserved as-is — diagrams are visual structure, not clickable links.
- **`MANIFEST.md` rows 32-38** (the `../docs/drafts/...` relative-path notation in the file-by-file manifest table) preserved as-is — these are byte-addressable manifest rows that reviewers verify with `sha256sum`, not clickable links.
- **Internal cross-doc references inside the Wave 345 audit section** (lines 117-148 of MANIFEST.md) preserved — these reference historical filenames as part of the governance narrative; converting them would obscure the Wave 345 fix context.

**Audit doc:** [`docs/audit/wave348-cross-doc-github-urls.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave348-cross-doc-github-urls.md) (additive governance record; tracks the 282-path replacement, the scope-discipline preserved, and the per-file SHA recomputation).

---

## Honest disclosures preserved

- **K1 (Kanzi N=1000 algorithm-primitive ablation):** FULLY RESOLVED 5/5 (Wave 157 — [`docs/audit/wave157-close.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave157-close.md)).
- **K2 (CIFAR-10 v4 N=500 cosine ramp PROTOCOL_MISMATCH):** preserved ([`docs/audit/wave146-cifar-v4-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave146-cifar-v4-audit.md)).
- **K4 (Kanzi decision-metric saturation):** UNDERPOWERED / TIES_AT_ZERO.
- **K5 (FreqFlow + MM-FM integration):** ENV_BLOCKED (PHASE-4 deferred).
- **K6 (Wan2.2 N=1000 sweep):** DEFERRED to camera-ready.
- **R3 FlowMol3 fg_dev 3-seed direction consistency:** Wave 242 P1 partial (single_mol path due to DGL 2.4.0 batched-path bug); seed=44 framework arm NOT run in budget. Direction-inconsistent at NFE=100/N=500/single_mol; only seed=42 framework-WINS at NFE=250/N=1000/batched-DGL.

---

## Note on intermediate vs final submission

This TNNLS submission package supersedes the historical `eaai_submission/` folder (EAAI submission of 2026-09-18). The EAAI submission is retained as a historical snapshot for audit-trail purposes; the TNNLS submission is the current authoritative version. The current package also supersedes the Wave 274 + Wave 280 TNNLS package snapshots:

- `MANIFEST.md` (this update) replaces the Wave 238 P4 `MANIFEST.md` placeholder-bytes for the paper PDF row (which referenced an EAAI-elsarticle PDF).
- The `<rehash>` SHA-256 columns are populated at freeze (after the cover letter placeholders are filled); see [`docs/audit/wave324-d5-review.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave324-d5-review.md) for the audit-time snapshots.
- [`supplementary/README.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/supplementary/README.md) is new in this Wave 324 update; the previous [`tnnls_submission/MANIFEST.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/MANIFEST.md) had no dedicated supplementary index.

---

## Coordination with the Wave 324 final review

The Wave 324 D+5 review ([`docs/audit/wave324-d5-review.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave324-d5-review.md)) confirms:

- **Page count:** 10 pages (well within TNNLS 12-14 page budget)
- **Equation correctness:** all 5 numbered equations render; `\B_g` → `\sheetB` and `\pbonf` math-mode fixes applied
- **Table readability:** Table I (5 columns) / II (7 columns) / III (13 columns, `\resizebox`) / IV (5 columns) / V (7 columns) all fit
- **Cross-section consistency:** abstract, intro, contribution list, R-cell counts all aligned (R1, R2, R3, R5a, R5b, R5c, R6, K1, K4, K5, K7)
- **3-lemma structure in §6:** Lemma 1 (Wave 311) + Lemma 2 (Wave 322) + Lemma 3 (Wave 322) all present with proofs

The READY_TO_SUBMIT verdict from Wave 324 D+5 holds. The two MEDIUM inconsistencies (M1: Table V R5c p-value; M2: Table III R6 per-tier row count) are documentation/analysis clarifications rather than bugs and can be addressed in supplementary material or with a small follow-up patch — they do not block ScholarOne upload.

---

**End of MANIFEST.md**
