# Manuscript defect review #3 — third `.tex`/`.md` consistency sweep

**Date:** 2026-10-12
**Scope:** Third reviewer-facing defect sweep across `docs/drafts/paper-A-final.{md,tex}` + the submission SHA ledger, after the user request *"你现在看看写好的论文还有没有什么毛病，之前修复计划里没修完的任务你再看看，能做的现在都做好"* — i.e. a fresh read of the finished manuscript plus a revisit of every still-open item from the prior repair plans (`docs/audit/manuscript-defect-review.md`, `docs/audit/manuscript-defect-review-2.md`).
**Status:** COMPLETE — 5 defect groups fixed, 1 documented-not-fixed; manuscript SHAs refreshed; PDF rebuilt; **no metric / claim number changed; no status label moved.**

---

## 1. Observed facts (defects + fixes)

All edits are **wording/structure** corrections (guardrail §3.4 honest-uncertainty + §3.5 freeze + §3.7 stricter=cleaner). Six candidate defect groups were found in the fresh read; five were verifiable against ground truth and fixed; the sixth (R5a seed-coverage provenance) is genuinely muddy at the project level and is **documented, not silently reworded**.

| # | Defect | Fix |
|---|---|---|
| F1 | §7.9's Bonferroni-family paragraph cited the family list as "The 4 families (§7.3)", but the four pre-registered families are defined in **§7.4**. | `.md:696` — `The 4 families (§7.3)` → `The 4 families (§7.4)`. |
| F2 | The audit-row column count was labelled **"12-column"** / **"12-col audit row"** in the §7.11 power-disclosure discussion and in `docs/CLAIMS.md`, but the audit row is **13 columns** (`n_paired, mean_diff, sd_diff, t, df, p_raw, CI_95_low, CI_95_high, d_z, test_type, family, alpha_bonferroni, bonf_sig`). | `.md:536/588/666` and `docs/CLAIMS.md:2667/3737/3747/3790` — `12-column`/`12-col audit row` → `13-column`/`13-col audit row`. This **reverses** the review-2 §4 deferral (which had treated the mislabel as a "doc-wide canonical label"); the count is factually 13. |
| F3 | §3.4.2's capability-token description stated a **"24-field `AdapterCapabilities`"** with "**(9 flags)**", "**Eight True / one False**", and group (iv) as "**(6 fields)**". Ground truth (verified via `dataclasses.fields`) is **22 fields, 10 boolean `has_*` flags (Nine True / one False), and 7 fields** in group (iv). | `.md:184` — `24-field`→`22-field`, `(9 flags)`→`(10 flags)`, `Eight True / one False`→`Nine True / one False`, `(6 fields, …)`→`(7 fields, …)`, and "splits cleanly into four logical groups"→"splits into four principal logical groups". |
| F4 | §7.9's regime-curve figure note falsely claimed the figure "closes the §10.8 'Future-work: plot the regime curve as a figure' gap". §10.8 carries **no** such future-work item — the figure's relationship to §10.8 is narrative. | `.md:652` — replaced the false citation with: *"The figure renders the §7.9 three-point regime curve as a standalone artifact (the §10.8 regime-curve discussion and the §10.5(d) regime-dependent future-work item remain the paper's narrative treatment); the empirical regime-dependence is preserved verbatim per the Wave 268 strict-clean 'no number change' rule."* |
| F5 | §4.5 contained a **self-contradiction**: it asserted the four optional theoretical-perspective controllers "appear as bare headlines on some cells", while the same paragraph established that R6 is the sole theoretical-perspective cell. | `.md:372` — rewritten so that only R6 (k6 foldability, via `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler`) wires a theoretical-perspective headline; the four optional controllers "consume companion quantities … none of the 4 appears as the bare headline on any of the 11 cells". The cosine arm is stated as the predominant headline reading, with R6's tier-aware counterfactual the sole theoretical-perspective exception. |
| F6 | **R5a seed coverage** is documented inconsistently across surfaces: the source tool default is "5 seeds", the R-level statistical test uses **n = 3**, and the legacy Wave-158 label reads "single-seed". | **Documented, not fixed.** The three readings are not reconcilable from the manuscript surfaces alone without a provenance decision that belongs to a ledger-wide audit, not a manuscript-surface pass. Recorded here as a known documentation gap. |

## 2. Evidence

- Manuscript SHAs: `sha256sum docs/drafts/paper-A-final.{md,tex,pdf}` → `9e40bf680a33e177fe06d195501afe76c1edd7b7861d0940545b57b39a85f60c` (211113 B) / `25f256bc841bbfb8e9d10ab655d6adb945a225e9a3fd72c8f3bf130784b2ad98` (63970 B) / `ce0f0461de3b240bf14d0df8c7198fd4c1819aa75973ae596fc0abb2b39b1225` (447019 B, 11 pages).
- PDF: `pdflatex -interaction=nonstopmode -halt-on-error` ×3 passes, zero undefined references, zero LaTeX errors; 11 pages (447019 bytes).
- F3 ground truth: `AdapterCapabilities` inspected via `dataclasses.fields` → **22 fields**, **10** boolean `has_*` flags (**9** `True` / **1** `False`), group (iv) = **7** fields. The capability-token JSON = 22 keys / 9 True / 1 False; token `sha256 = 584f8e02…` (762 bytes, unchanged).
- F2 column set: the 13 audit-row columns are `n_paired, mean_diff, sd_diff, t, df, p_raw, CI_95_low, CI_95_high, d_z, test_type, family, alpha_bonferroni, bonf_sig`.
- F1 family definition: the four pre-registered Bonferroni families are defined in `docs/drafts/paper-A-final.md` §7.4 (R-level primary `k=7`; R6 per-tier `k=6`; Table B `k=16`; ablation `k=5`).
- **MANIFEST post-edit SHA:** `98f62741ba5a826cd4b8357f78069b68d9fde38eef21cd391981de8feaffb552` (61948 bytes). The MANIFEST self-row retains the pre-edit `d1fc6d40…` per the self-referencing-SHA convention; this audit pins the post-edit value. `SUBMISSION_READINESS.md` post-edit SHA: `cd199fa0eb5567d16d769f3f6c7b7c41ce775955b194b439fbcb216236092232` (37523 bytes). `submission_checklist.md` post-edit SHA: `414379a20be626ffea1445d5c37be0281e51e7479b32e2bfbaa63cc9c129d544` (33589 bytes).
- `docs/CLAIMS.md` post-edit SHA: `5d401438a83a29f82a478ceca914cdfc030ce71f3abea38cb248ed625bb698a8` (415983 bytes).

### 2.1 Gate results (acceptance record)

| Gate | Command | Result |
|---|---|---|
| claims consistency | `python3 tools/check_claims_consistency.py` | **PASS** — "No drift detected" |
| docs-against-code | `python3 tools/check_docs_against_code.py` | **PASS** — "OK: 4142 claims verified" |
| ruff | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **PASS** — "All checks passed!" |
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **PASS** — 30 passed |
| mkdocs strict | `mkdocs build --strict` | **PASS** — zero nav/link warnings |
| mypy strict | `.venvs/flowmol3_venv/bin/python -m mypy adaptive_reflow` | **KNOWN-RED (pre-existing)** — 39 errors in 13 adapter files; environment-dependent (sidecar-venv stubs) and **not touched by this docs-only pass**. Acknowledged in CLM-024. |

## 3. Interpretation

- F1/F2/F3 are **stale-number** defects: an earlier renumbering/refactor changed the ground-truth value (section number, column count, dataclass field count) but the prose was not propagated. The fixes restore prose↔ground-truth consistency without touching any metric.
- F4 is a **false-citation** defect: a standalone figure was described as "closing" a future-work item that does not exist in §10.8. The honest form (guardrail §3.4) states the figure's actual relationship — a standalone rendering whose empirical regime-dependence is preserved verbatim.
- F5 is a **logical-contradiction** defect: the paragraph's two halves disagreed about whether the theoretical-perspective controllers appear as bare headlines. The rewrite keeps R6 as the sole theoretical-perspective cell and the cosine arm as the predominant headline reading — a *reframing* only, with no status promotion or number change.
- F2 reverses a review-2 deferral. Review-2 §4 had left "12-column audit row" untouched as a presumed doc-wide canonical label; the fresh read established that the audit row genuinely has 13 columns, so the mislabel is a plain factual error rather than a canonical alias. The correction is bundled here rather than left as a standing inconsistency.

## 4. Unresolved gaps / caveats

- **F6 (R5a seed coverage)** is documented, not fixed — see the table above. Resolving it requires a ledger-wide provenance decision (source-tool default vs statistical-test n vs legacy label) that must not be bundled with a manuscript-surface pass.
- **`.tex`/`.md` structural re-sync** remains deferred (the `.tex` carries no PEP-695 / honest-disclosure / hash-chained-ledger subsections). Per user direction only cross-references and labels are kept self-consistent per surface.
- **R5c "Bonferroni $p = 3.95 \times 10^{-11}$" label** (`docs/CLAIMS.md` R5c row; `.md:669` / `.tex` R5c row) is a **doc-wide canonical label** (per-3-arm-count $k = 3$) and was intentionally left as-is — relabelling it is a ledger-wide change that must not be bundled with a manuscript-surface pass.
- `docs/audit/manuscript-defect-review{,-2}.md` and the MANIFEST 2026-10-11 / consistency-pass addenda retain the superseded `c88d6069…` / `cca0be6f…` / `8bc37858…` and `8315f67e…` / `f3d7b9fb…` / `33d3a771…` readings as historical record (not edited).
