# Manuscript-consistency pass #9 — R2 "paired" → "index-matched two-sample" terminology

**Date:** 2026-10-12
**Author:** manuscript-consistency agent (USER AUTHORIZED, NO PUSH)
**Status:** **COMPLETE — R2 comparison relabelled "index-matched two-sample" across the manuscript `.md`/`.tex`, the `paper-data/` recipe, and `docs/CLAIMS.md`. No metric, no number, no status label, and no verdict changed; the PDF was rebuilt.**
**Trigger:** user directive **"改掉 paired 措辞"** (change the R2 "paired" wording), the follow-up to the GAP-23 retraction in commit `886c148` (`docs/audit/gap23-r2-paired-comparison-invalid.md` §6 + `docs/audit/gap23-r2-paired-comparison-fix.md` §7).
**Scope:** ADDITIVE terminology change only. The two R2 arms (baseline = autoencoder round-trip of the real input record; framework = autoencoder round-trip of the bridge-generated structure) are matched by record index for bookkeeping and are statistically independent (`corr ≈ +0.02`), so the R2 test is an **index-matched two-sample** test, not a within-subject "paired" test. Every number is held fixed per AGENTS.md §3 guardrails #2 (additive) and #4 (reframe wording, do not change numbers).

---

## 1. Executive summary

| Item | Value | Source |
|---|---|---|
| Terminology change | "paired" → **"index-matched two-sample"** | this pass |
| Manuscript `.md` spots | **6** (§7.2 R2 row, §7.2 power-index R2 row, §7.6.1, §7.10, §7.11 R2 row, §8.10 manifest R2 row) | `docs/drafts/paper-A-final.md` |
| Manuscript `.tex` spots | **4** (summary table R2 row, §7.2 R2 row, §7.6.1, §7.10) | `docs/drafts/paper-A-final.tex` |
| `paper-data/` spots | **2 files** (`REPRODUCIBILITY_RECIPE.md` terminology throughout; `R2_SOURCE.md` 3 rows) | `paper-data/R2_kanzi_rmsd/` |
| Claims-ledger change | **1 additive bullet** (CLM-060 R2 label addendum) | `docs/CLAIMS.md` |
| Numbers changed | **0** (`d_z = -0.0990`, `p_raw = 1.7943 × 10⁻³`, α = 0.007143, verdict framework-WINS preserved) | §3 |
| Status labels changed | **0** (R2 remains STRONG framework-WINS) | §3 |
| Recipe SHA repointed (live §8.10 table) | `be3a4ff2…` → `664f3bb9…` | §2.3 |
| PDF rebuild | 11 pages, 448996 bytes, 0 overfull / 0 undefined | §5.1 |

**Headline:** The R2 headline was described as a "paired" comparison, which implies the framework arm consumed the input record. It did not — the two arms are independent draws matched by index, so the label is now **"index-matched two-sample"**, with an inline disclosure that the index-matched `t`-test coincides with the unpaired Welch test (`t = -3.11`, `p = 1.87 × 10⁻³`). The change is terminology-only: `d_z = -0.0990`, `p_raw = 1.7943 × 10⁻³`, Bonferroni-significance at α = 0.007143, and the STRONG framework-WINS verdict are all preserved verbatim.

---

## 2. Observed facts

### 2.1 Manuscript `.md` (6 spots)

| Line | Section | Old | New |
|---|---|---|---|
| 546 | §7.2 R2 row | `(protein flow-AE, paired $N = 1000$)` … `(paired $N = 1000$, …)` | `(protein flow-AE, index-matched two-sample $N = 1000$)` … `(index-matched two-sample $N = 1000$, …; the two arms are independent, corr ≈ +0.02, so the index-matched t-test coincides with the unpaired Welch test — t = -3.11, p = 1.87e-3)` |
| 571 | §7.2 power-index table R2 row | `(paired-t d_z=-0.0990)` | `(index-matched two-sample t, d_z=-0.0990)` |
| 607 | §7.6.1 | `The paired $N=1000$ reconstruction RMSD` | `The index-matched two-sample $N=1000$ reconstruction RMSD` |
| 656 | §7.10 summary | `R2 measures a small paired reconstruction gain` | `R2 measures a small index-matched two-sample reconstruction gain` |
| 665 | §7.11 R2 row | `Cohen's $d_z = -0.0990$, paired $N = 1000$` | `Cohen's $d_z = -0.0990$, index-matched two-sample $N = 1000$` |
| 727 | §8.10 manifest R2 row | `(Kanzi RMSD N=1000 paired-t)` | `(Kanzi RMSD N=1000 index-matched two-sample t)` |

### 2.2 Manuscript `.tex` (4 spots)

| Line | Section | Old | New |
|---|---|---|---|
| 426 | summary table R2 row | `Small paired gain` | `Small index-matched gain` |
| 452 | §7.2 R2 row | `(protein flow-AE, paired $N = 1000$)` … `(paired $N = 1000$, …)` | `(protein flow-AE, index-matched two-sample $N = 1000$)` … `(index-matched two-sample $N = 1000$, …; … coincides with the unpaired Welch test --- $t = -3.11$, $p = 1.87 \times 10^{-3}$)` |
| 500 | §7.6.1 | `The paired $N=1000$ reconstruction RMSD` | `The index-matched two-sample $N=1000$ reconstruction RMSD` |
| 515 | §7.10 | `R2 supports a small paired reconstruction gain` | `R2 supports a small index-matched two-sample reconstruction gain` |

### 2.3 `paper-data/` + live SHA repoint

| File | Change | Old SHA-256 | New SHA-256 |
|---|---|---|---|
| `paper-data/R2_kanzi_rmsd/REPRODUCIBILITY_RECIPE.md` | terminology throughout ("paired t" → "index-matched two-sample t"; "paired Δ" → "index-matched Δ"; "paired records" → "index-matched records") | `be3a4ff26fb1d436a5d29dcbb0c8e62a8c826ff9b8ed4c177e6c808310146a27` | `664f3bb954a2fd64725bfcf81449482a182261c49d9aedaa02f4007cae19e998` |
| `paper-data/R2_kanzi_rmsd/R2_SOURCE.md` | 3 rows (index-matched two-sample t / index-matched-diff headline / CLM-039 index-matched two-sample t) | `b6a261f9aa62bac290845da2508587924488726e840035c9ee2fd6c4319d64ae` | `95d94930e07a3e3f0d44406066657491e1360c670ac4ce66257753be4fdc9204` |

**Live manifest repoint.** The reviewer-facing §8.10 recipe table (`docs/drafts/paper-A-final.md:727`) now cites the recipe's **new** SHA-256 `664f3bb9…`. The recipe's own SHA is referenced in exactly three places in the repository: this live §8.10 table (repointed), `docs/audit/wave363-r2-recipe.md:20`, and `docs/audit/wave366-p2-reproducibility-manifest.md:83`. The two audit records are frozen per-wave snapshots ("Recipe SHA-256 … verified at this wave"); they are **left verbatim** as historical readings, superseded by this pass — consistent with the project's append-only ledger convention (the MANIFEST addendum chain follows the same pattern: "the previous readings are superseded").

**No verifier breakage.** No script hard-codes the R2 recipe SHA: `reproduce/02_R2_Kanzi.sh` verifies the `verification_outputs/wave218-p3-kanzi-framework-wins.json` stats (d_z / p_raw / verdict / bonf_sig); `reproduce/09_verify_all_cell_recipes.sh:105` only `test -f`'s the recipe and hashes the Wave 218 JSON chain; `tools/verify_submission_readiness.py` gate 6 hashes the R2 JSON (`kanzi_n1000_paper_metrics.json` = `02e9df30…`), which is unchanged. `R2_SOURCE.md`'s own hash is not pinned in `paper-data/SHA256SUMS` or `paper-data/MANIFEST.md`.

### 2.4 Retained "paired" instances (legitimate — NOT changed)

The relabelling is scoped to the R2 comparison only. The following "paired" usages are correct and were deliberately preserved:

- **R1** (LineageFlow HMMER, `N = 1000` paired per-record t), **R3** (FlowMol3 fg_dev paired per-record `n = 200`), **R6** (Kanzi k6 `N = 1000` paired pLDDT `δ_i`) and **K5** (LineageFlow HMMER paired delta) are genuinely paired comparisons.
- The `n_paired` audit-row field name and the `scripts/wave218_p3_paired_ttest.py` / `tools/sweep_kanzi_paired_restartblend.py` identifiers are code identifiers, not prose labels.
- The substring "unpaired" (e.g. "the unpaired Welch test") contains "paired"; it is retained.

---

## 3. Interpretation — why "index-matched two-sample", and why no number moved

The R2 baseline arm is an autoencoder round-trip of the **real input record**; the R2 framework arm is an autoencoder round-trip of the **bridge-generated structure** (a sampled latent passed through the trained `project_out⁻¹` bridge + DAE decode before the ODE solve). The two arms therefore do **not** share a per-record random seed or latent — they are independent samples matched by record index for bookkeeping. The empirical correlation between the two arms is `corr ≈ +0.02`.

Because the arms are independent, `sd_diff ≈ √(sd_b² + sd_f²)`, and the **index-matched paired SE (0.006058) equals the unpaired Welch SE (0.006089)**. Hence:

| convention | t | p |
|---|---|---|
| index-matched (paired) | −3.131 | 1.79 × 10⁻³ |
| unpaired Welch | −3.114 | 1.87 × 10⁻³ |

The significance is **not** a pairing artifact — it survives the unpaired test. This is precisely why the GAP-23 "pairing artifact" claim was retracted (commit `886c148`), and why the honest remediation is a **label** change rather than a number change. AGENTS.md §3 guardrail #4 ("reframe wording, do not change numbers") and #5 (submission freeze — numbers must not move) both require exactly this.

---

## 4. Files changed

| File | Change type | Notes |
|---|---|---|
| `docs/drafts/paper-A-final.md` | wording + 1 SHA repoint | 6 R2 spots + §8.10 recipe SHA |
| `docs/drafts/paper-A-final.tex` | wording | 4 R2 spots |
| `docs/drafts/paper-A-final.pdf` | rebuilt | 11 pages, 448996 bytes |
| `paper-data/R2_kanzi_rmsd/REPRODUCIBILITY_RECIPE.md` | wording | terminology throughout |
| `paper-data/R2_kanzi_rmsd/R2_SOURCE.md` | wording | 3 rows |
| `docs/CLAIMS.md` | additive | CLM-060 R2 label addendum (no number / status / verdict change) |
| `tnnls_submission/MANIFEST.md` | additive | pass-#9 addendum (new `.md`/`.tex`/`.pdf` SHA-256 + byte sizes) |
| `docs/audit/manuscript-defect-review-9.md` | NEW | this audit note |

---

## 5. Verification evidence

### 5.1 PDF rebuild

```
$ pdflatex -interaction=nonstopmode -halt-on-error paper-A-final.tex   # pass 1
$ pdflatex -interaction=nonstopmode -halt-on-error paper-A-final.tex   # pass 2
Output written on paper-A-final.pdf (11 pages, 448996 bytes).
```

`grep -c Overfull` = 0; `grep -cE "undefined|LaTeX Warning|Missing|Emergency"` = 0. (147 benign "Underfull \hbox" advisories, standard for two-column IEEEtran with long URLs.)

### 5.2 Final artifact SHA-256 + sizes

| Artifact | SHA-256 | Bytes | Pages |
|---|---|---|---|
| `docs/drafts/paper-A-final.md` | `c6978764d498baa7390b3b7979f2d045407b40d1a7a1db14f80e2f1f919c0f3b` | 213574 | — |
| `docs/drafts/paper-A-final.tex` | `cd600246f5f5e715c2b640022ccb9c87de19a34c5399949323164f4abc284f73` | 66156 | — |
| `docs/drafts/paper-A-final.pdf` | `b3fd1c3e3d6c4714cd265e46010e45cbe912293d97214f07882a0a803c5e4ffd` | 448996 | 11 |

Word count (`wc -w`): 25799.

### 5.3 Gates (see §6)

- `python3 tools/check_claims_consistency.py` → no drift
- `python3 -m pytest tests/test_d4_regression_vectors.py -q` → 30/30 PASS
- `ruff check adaptive_reflow/ tests/ scripts/ tools/` → 0 findings
- `mkdocs build --strict` → exit 0
- `reproduce/09_verify_all_cell_recipes.sh` → 11/11 recipes verified

---

## 6. Hard-guardrail compliance (AGENTS.md §3)

1. **Vendored upstream sacred** ✓ — no vendored file touched.
2. **No destructive edits** ✓ — additive/terminology only; numbers held fixed; the two historical R2 recipe audits left verbatim (superseded, not rewritten).
3. **NO-PUSH policy** ✓ — commit-only; no `git push`.
4. **Honest uncertainty** ✓ — R2 label reframed, not promoted; STRONG framework-WINS preserved verbatim; the misleading "paired" implication removed.
5. **TNNLS submission freeze** ✓ — only additive docs in `tnnls_submission/`; no number moved; the MANIFEST SHA-256 ledger regenerated.
6. **Per-increment audit doc** ✓ — this file.
7. **Stricter = cleaner** ✓ — the minimal label change (5 files + 1 SHA repoint) over any re-analysis; the two historical audits preserved as frozen snapshots.

---

## 7. Cross-references

- **`docs/audit/gap23-r2-paired-comparison-invalid.md`** §6 — the GAP-23 retraction (the "pairing artifact" claim is statistically false; R2 stays STRONG framework-WINS).
- **`docs/audit/gap23-r2-paired-comparison-fix.md`** §7 — the bridge-less driver correction (it is NOT the canonical R2).
- **`docs/CLAIMS.md`** CLM-060 — the additive R2 index-matched two-sample label addendum.
- **`paper-data/R2_kanzi_rmsd/REPRODUCIBILITY_RECIPE.md`** — the R2 reproducibility recipe (new SHA `664f3bb9…`).
- **`tnnls_submission/MANIFEST.md`** — the pass-#9 addendum (new artifact SHA-256 + byte sizes).

---

_Last updated: 2026-10-12 (manuscript-consistency pass #9 — R2 "paired" → "index-matched two-sample" terminology propagated across the manuscript `.md`/`.tex`, the `paper-data/` recipe, and `docs/CLAIMS.md`; recipe SHA repointed in the live §8.10 table; PDF rebuilt (11 pages, 448996 bytes); 0 numbers, 0 status labels, 0 verdicts changed)._