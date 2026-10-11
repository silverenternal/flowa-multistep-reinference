# Manuscript defect review #5 — fifth consistency sweep

**Date:** 2026-10-12
**Scope:** Fifth reviewer-facing defect sweep across `docs/drafts/paper-A-final.{md,tex}` + the submission SHA ledger, after the user request *"你现在看看写好的论文还有没有什么毛病，之前修复计划里没修完的任务你再看看，能做的现在都做好"* — i.e. a fresh read of the finished manuscript plus a revisit of every still-open item from the prior repair plans (`docs/audit/manuscript-defect-review{,-2,-3,-4}.md`).
**Status:** COMPLETE — 5 defect groups fixed (1 in both surfaces, 4 in the markdown source); **all three pass-#4 deferred items (G4/G5/G6) closed**; ledger SHAs refreshed; PDF rebuilt. **No metric / claim number changed; no status label moved.**

---

## 1. Observed facts (defects + fixes)

A fresh read of all 1028 lines of `docs/drafts/paper-A-final.md` and all 571 lines of `docs/drafts/paper-A-final.tex`, cross-checked against the source artifacts (`verification_outputs/wave280-p-r5c/aggregate.json`, `verification_outputs/wave189-p2-post-cd70821-combined.json`, `verification_outputs/wave206-p6-honest-negative-curve.json`, `verification_outputs/wave191-p3-mnist-n1000.json`) and the `reproduce/` recipe manifest, surfaced five defect groups. All five are fixed this pass; the three items the pass-#4 audit recorded as "documented-not-fixed" (G4/G5/G6) are resolved.

| # | Defect | Fix |
|---|---|---|
| H1 | **Duplicated sentence.** The R3 per-cell row stated the same deferred-sweep fact twice in consecutive sentences ("…remains on the camera-ready deferred list pending the DGL vendor-level fix (the per-mol prior-tiling patch). The full N=1000 paired fg_dev sweep remains on the camera-ready deferred list pending the DGL vendor-level fix."). | Removed the redundant second sentence in `.md:560` **and** the near-duplicate second sentence in `.tex:460` (the two surfaces carried the same redundancy with slightly different wording). |
| H2 | **§8.10 manifest list.** The "The 11 cells are:" sentence listed `R4_legacy` (2D Eight Gaussians) among the eleven cells, but the canonical 11-cell taxonomy (§1, §7.1) is R1, R2, R3, R5a, R5b, R5c, R6, K1, K4, K5, K7 — `R4_legacy` is a retained legacy ablation. The sentence thus named 12 cells while the manifest has 11 recipe rows. **(closes pass-#4 G6)** | `.md:720` — reworded: "The manifest's 11 recipe files cover the eleven headline cells — … (K4 + K5 …, sharing one recipe file) — plus the retained legacy `R4_legacy` … ablation recipe, kept for provenance." |
| H3 | **§9 dimension labels collided with the K-cells.** §9's eight limitation dimensions were labelled `K1`–`K8` (K1 Generative-paradigm, … K7 Multi-round-vs-restart, K8 compute-budget), the same tokens as the four supplementary K-cells (`K1`/`K4`/`K5`/`K7`) in §7.1/§7.2/§10.7; the §9 `K1` and `K7` paragraphs even embedded K-*cell* disclosures. **(closes pass-#4 G5)** | Renamed the eight §9 headings `K1`–`K8` → `L1`–`L8`; added a one-line disambiguation note to the §9 introduction ("The eight dimensions are labelled **L1–L8** to distinguish them from the supplementary K-cell identifiers …"); disambiguated the two embedded K-cell disclosures ("the K1 cell was demoted…", "the K7 cell demoted…"). |
| H4 | **§10.3 / §8.3 stale seed-coverage.** §10.3 listed "R5a (single-seed), R5c (smoke ckpt single-seed + production ckpt 1-seed)", contradicting §7.2 (R5a = `n = 3` unpaired seeds) and §7.9 (R5c production ckpt = 3 seeds); §8.3 likewise listed R5a among the single-seed cells. **(closes pass-#4 G4)** | `.md:830` — §10.3 coverage corrected to R1 / R3 / R5c-smoke+intermediate / K3+R5b, with a note that R5a (§7.2) and the R5c production ckpt (§7.9) are already 3-seed. `.md:692` — §8.3's single-seed list changed to "(R5c smoke ckpt, K7); R5a uses three unpaired seeds in its primary test (§7.2), so it is not in this set." |
| H5 | **Stale word-count metadata.** `README.md` / `README.zh.md` pinned "(25,175 words)" while the current `wc -w docs/drafts/paper-A-final.md` = 25,564. | Updated `25,175 words` → `25,564 words` in both READMEs (4 sites). |

## 2. Evidence

- Manuscript SHA (this pass): `sha256sum docs/drafts/paper-A-final.md` → `794c6eae80fed8ef8ef43bc5310dd1971c731118bcd44e42bf6f7e22defae752` (211927 bytes). `.tex` → `99638eb09ac930ab37df5a0ea67029287bf82e7ad67f78fd558df73d976d50bf` (63879 bytes). `.pdf` → `68b28acda286a394cabe17a92f67d715f09208cf19b10385f29fd67b732d0238` (446895 bytes, **11 pages**, rebuilt with two `pdflatex` passes; zero fatal errors, zero undefined references).
- **H1 ground truth:** `grep -o "remains on the camera-ready deferred list pending the DGL vendor-level fix" paper-A-final.md` → **2** hits (both in the R3 row); the `.tex` carried the same fact twice with differing wording.
- **H4 ground truth:** `verification_outputs/wave280-p-r5c/aggregate.json` → `"n_seeds": 3` (production ckpt, seeds 42/43/44); `verification_outputs/wave189-p2-post-cd70821-combined.json#two_moons` → `"n_seeds": 3`. The `.tex` §8.3 already stated the correct coverage ("R5a uses three unpaired seeds in its primary test; R5c smoke and intermediate settings have one seed; the R5c production setting has three"), so this pass aligned the `.md` to the `.tex`.
- **H2 ground truth:** the canonical 11-cell taxonomy (§1 line 17, §7.1 line 534) is R1, R2, R3, R5a, R5b, R5c, R6, K1, K4, K5, K7; `R4_legacy` is not among them. The §8.10 recipe table has 11 rows, the last being `R4_legacy` (`paper-data/R5_legacy_2d_eight_gaussians/SOURCE.md`).
- **H3 ground truth:** no in-paper or cross-doc reference targets the §9 dimension labels `K1`–`K8` (a repo-wide grep for `§9 K…` finds only `docs/audit/` history), so the rename is self-contained.
- **Cross-reference check:** a scripted scan of every `§N.M` reference in the `.md` resolves to a heading; the only non-heading `§` reference is the cross-doc `CONSOLIDATED_RESULTS.md §13` pointer.
- **MANIFEST post-edit SHA:** `f9e03fa9627d55f6597b1c60cdcee3df9d1c9d5fc241f1271917038c2903d66d` (66737 bytes). The MANIFEST self-row retains the pre-edit reading per the self-referencing-SHA convention; this audit pins the post-edit value. `SUBMISSION_READINESS.md` post-edit SHA: `3f877b10a9f0a7512d1006695ce61ac0289282fcfc3078e1fca87e8e79b4d203` (41054 bytes). `submission_checklist.md` post-edit SHA: `015f3e2b7e74c173853dddbf88efbfd8b1d574c843f0fe611cc40af4c6d7aa67` (33621 bytes).

### 2.1 Gate results (acceptance record)

| Gate | Command | Result |
|---|---|---|
| claims consistency | `python3 tools/check_claims_consistency.py` | **PASS** — "No drift detected" |
| docs-against-code | `python3 tools/check_docs_against_code.py` | **PASS** — "OK: 4142 claims verified" |
| ruff | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **PASS** — "All checks passed!" |
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **PASS** — 30 passed |
| mkdocs strict | `mkdocs build --strict` | **PASS** — exit 0, zero nav/link warnings |
| mypy strict | `.venvs/flowmol3_venv/bin/python -m mypy adaptive_reflow` | **KNOWN-RED (pre-existing)** — 39 errors in adapter files; environment-dependent (sidecar-venv stubs) and **not touched by this docs-only pass**. Acknowledged in CLM-024. |

## 3. Interpretation

- H1 is a **redundancy** defect: the same deferred-sweep fact appeared twice. Removing the duplicate tightens the R3 row without changing any number or status.
- H2–H4 close the three items the pass-#4 audit recorded as requiring "a taxonomy/provenance decision". The decisions are grounded in verifiable ground truth: H2 (the canonical taxonomy excludes `R4_legacy`), H3 (no reference targets the §9 dimension labels), H4 (source JSONs give R5a = 3 seeds, R5c production = 3 seeds; the `.tex` §8.3 already states this). None of the three touches a metric, a claim number, or a status label.
- H5 is a **metadata** correction: the pinned word count was stale relative to the current source.

## 4. Unresolved gaps / caveats

- **`.tex`/`.md` structural re-sync** remains deferred (the `.tex` is a condensed IEEEtran build that carries no PEP-695 / honest-disclosure / hash-chained-ledger subsections, no §8.10 manifest, no §9 `L1`–`L8` dimensions, and no §10.3). Per the established scope decision, only cross-references and labels are kept self-consistent per surface. This is **not** a defect — the two surfaces are intentionally different builds.
- **R5c "Bonferroni $p = 3.95 \times 10^{-11}$" label** (`.md:552` / `.md:669` / `.tex` R5c row) was **verified correct** this pass against `verification_outputs/wave191-p3-mnist-n1000.json` (`evidence_driven.p_value_bonferroni = 3.9528e-11`, i.e. the per-3-arm-count $k=3$ corrected value) — no change needed; the pass-#4 audit's "doc-wide canonical label" note is confirmed.
- The historical records — `docs/audit/manuscript-defect-review{,-2,-3,-4}.md`, the MANIFEST pass-#2/#3/#4 blockquotes, and the SUBMISSION_READINESS §12/§13/§14 addenda — retain the superseded `8315f67e…` / `f3d7b9fb…` / `33d3a771…` / `9e40bf68…` / `8323488f…` / `25f256bc…` / `ce0f0461…` readings as provenance (not edited).
