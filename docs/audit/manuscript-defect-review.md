# Manuscript defect review — `.tex`/`.md` consistency pass

**Date:** 2026-10-11
**Scope:** Reviewer-facing defect fixes across `docs/drafts/paper-A-final.{md,tex}` + the submission SHA ledger, after the user request *"你现在看看写好的论文还有没有什么毛病"* followed by *"先记录一下要修哪些然后再开始逐一修复"*.
**Status:** COMPLETE — 11 defect groups fixed; manuscript SHAs refreshed; PDF rebuilt; no metric / claim number changed.

---

## 1. Observed facts (defects + fixes)

All edits are **wording/structure/additive**; **no load-bearing number moved** (guardrail §3.4 honest-uncertainty + §3.5 freeze). The `.tex` and `.md` surfaces have divergent section numbering; per user direction the `.tex` cross-references were fixed to the **`.tex`'s own rendered numbering**, and the `.md` to its own.

| # | Defect | Fix |
|---|---|---|
| 1 | `.tex` §R5c + `.md` §7.9 paired the **headline** FIDs (29.49→23.39) with the **chunk-mean** ΔFID (−28.43%), inviting the reader to compute −20.70%. Root cause: `scripts/wave191_p3_mnist_sweep.py:562` computes `delta_vs_baseline_pct` from paired **chunk-mean** FIDs, not headline FIDs; CLAIMS.md:2983 ties −28.43% to "chunk-FID 30.28 ± 1.17". | Added a **basis note** (`.md` §7.9 + `.tex` §R5c): ΔFID = paired chunk-mean delta; headline columns are single-pass FIDs. Numbers unchanged. |
| 2 | `.tex` stale cross-references. | `.tex:59` `Secs. 7.6 and 7.8` → `7.8 and 7.10`; `.tex:78` handshake `§3.4`→`§3.5`, PEP-695 ref merged into `§3.1` (no PEP-695 subsection exists in `.tex`); `.tex:80` honest-disclosure `§3.6`→`§8.5`; `.tex:496` `§7.5`→`§7.6`; `.tex:526` `§7.3`→`§7.4`. |
| 3 | `.md:66` same stale refs (PEP-695 `§3.5`→`§3.6`; honest-disclosure `§3.6`→`§8.7`) under `.md` numbering. | Fixed. |
| 4 | `.tex:300` malformed `\$$n_\text{cap}(r)=...$\$` (literal-dollar + math + literal-dollar). | Replaced with an unnumbered display equation `\[ ... \]` (avoids shifting equation numbers). |
| 5 | `.md` §10.7 K4/K5 labelled bare `SUPPORTED`, conflicting with the governing Wave 280 P §3.2 readings (K4 = POWERED, K5 = SUPPORTS-WITH-CAVEAT) disclosed in §7.11. | Added the Wave 280 P qualifier to both §10.7 rows (additive). |
| 6 | `.md:656` bucketed R5b under the bare "4 STRONG" while `.md:666` labels it CONDITIONAL. | Added `(conditional single-round)` to the R5b entry in the verdict-distribution line. |
| 7 | `.md:780` K2 CIFAR range `+24.89% to +30.65%` conflicts with `.md:620` `+24.46% to +30.65%` and is inconsistent with its own stated FID floor (103.41 ↔ +24.46%). CLAIMS CLM-070: 4-scheduler deltas Cosine +24.89 / Codim +25.13 / EvidenceDriven **+24.46** / FreeTraj +30.65. | Corrected `.md:780` to `+24.46% to +30.65%`. |
| 8 | §4.4 said "15-site dispatch table" / "across 15 sites"; the canonical `PAPER_QUANTITIES_SITE_NAMES` frozenset has **16** entries (15 = dormant count). | Corrected `15`→`16` in `.md:366/368` and `.tex:315/317`. |
| 9 | `.md:193/225` four dead `](#)` links; `.md:225` referenced non-existent `docs/audit/wave349-r1-3seed-gpu.md`. | Repointed to real GitHub blob URLs; the missing file → `docs/audit/wave349-gap-audit.md` (the R1 3-seed retro-validation audit). |
| 10 | `.md:628` used `§7.8.1` as an inline bold label with no such heading (inconsistent with the real `§7.6.1` heading); `.md:354/372` said "12/13 R-cells" / "13 R-cells" vs the canonical eleven-cell count (`.tex` §4.5: "Ten of eleven"). | Promoted `§7.8.1` to a `####` heading; corrected the counts to `10 of the 11 cells` / `11 cells` / `10 cosine cells`. |
| 11 | `.md` figure-number collisions: `.md:632` "Figure 3" collided with `.md:538` (the real in-build Figure 3), and `.md:575/652/669` "Figure 1" collided with `.md:112` (in-build Figure 1). The colliding figures (R5c regime curve + finer-NFE curves) are **not in the `.tex` build** (which has exactly 3 figures). | Relabelled the `.md`-only figures descriptively ("standalone figure, not in the IEEEtran build"); reserved `Figure N` for the 3 in-build figures. |
| 12 | `.md` R2 rows mislabelled the raw p-value as Bonferroni (`Bonferroni p = 1.79e-3`; CLAIMS: `p_raw = 1.7943e-3`) and omitted the kanzi-synthetic measurement-basis disclosure. | Relabelled to `raw p = 1.79e-3, Bonferroni-significant at …`; added the honest disclosure (synthetic Gaussian-perturbed input coords, σ=0.10 Å; `framework_inv_proj` feeds the real 512-d trajectory endpoint — `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:5-13`). |
| 13 | `tnnls_submission/SUBMISSION_READINESS.md` §1 rows 10–11 claim Theorem 4/5 closed-form bounds retracted by the manuscript's Wave 372 proof-scope correction; row 8's seed44 manifest digest `d71e76e2…` is stale (actual `cc4390bc…`). | Added **§11 manuscript-consistency corrections** (additive; frozen rows retained verbatim). |
| 14 | PDF rebuilt after the `.tex` edits; SHA ledger refreshed. | `paper-A-final.pdf` → 11 pp / 446703 B / `8bc37858…`; `.md` → `c88d6069…`; `.tex` → `cca0be6f…`; MANIFEST (6 rows + addendum), `submission_checklist.md`, `SUBMISSION_READINESS.md`, `README{,.zh}.md`, `todo/{STATUS,INDEX,WAVES}.md`, `docs/README.md` refreshed. |

## 2. Evidence

- Manuscript SHAs: `sha256sum docs/drafts/paper-A-final.{md,tex,pdf}` → `c88d6069…` / `cca0be6f…` / `8bc37858…`.
- PDF: `pdfinfo` → 11 pages, 612 × 792 pts; pdflatex 3 passes, zero undefined refs, zero LaTeX errors.
- R5c chunk-mean basis: `verification_outputs/wave191-p3-mnist-n1000.json` (`framework_arms.evidence_driven.delta_vs_baseline_pct = -28.431…`) + `verification_outputs/wave280-p-r5c/aggregate.json` (`smoke_ckpt_baseline.best_arm_pct = -28.431…`); CLAIMS.md:2983.
- K2 range: `docs/CLAIMS.md` CLM-070 (Cosine +24.89 / Codim +25.13 / EvidenceDriven +24.46 / FreeTraj +30.65).
- Cache sites: `adaptive_reflow/framework/paper_quantities_cache.py:112` `PAPER_QUANTITIES_SITE_NAMES` = 16 entries.
- R2 basis: `docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md` + `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:5-13`.
- seed44 manifest: `verification_outputs/wave349-r1-3seed-gpu/seed44_manifest.json` SHA `cc4390bc4a02799dc2add0ad251e7e5ece08e29f1ec2322c8c6f28f813cf44ed`.
- **MANIFEST post-edit SHA:** `a846cb220eecf32660d61f86a14ea701a81301e6b1f6944503c2558527824d84` (57474 bytes). The MANIFEST self-row (row 31) retains the pre-edit `d1fc6d40…` per the self-referencing-SHA convention; this audit pins the post-edit value. `submission_checklist.md` post-edit SHA: `1e45153387ef4100be37efb69063969f1b9e1ee00280e1a683bd47bd0434ecd4` (33564 bytes).

## 3. Interpretation

- The `.tex` is a rendering of the `.md` (per its header `Source: docs/drafts/paper-A-final.md`); the two diverged in §3 and §7 subsection structure, so the cross-reference numbers were stale in both surfaces. The user chose per-surface self-consistency.
- The R5c "arithmetic mismatch" was a **basis conflation**, not a wrong number: the canonical −28.43% is the paired chunk-mean delta; the fix makes the basis explicit rather than moving the number.
- The K4/K5 §10.7 labels and the R2 p-value label were **label drift** against the claims ledger; the fixes align the paper with CLAIMS without changing any number.

## 4. Unresolved gaps / caveats

- **CLAIMS CLM-060 R2 disclosure is stale.** CLAIMS.md:3134 states the R2 `kanzi_inv_proj` "byte-stable composite" is a synthetic-only output with "no ODE rollout"; the R2 audit + tool show the current N=1000 `framework_inv_proj` arm uses the **real** ckpt (`data/kanzi_ckpt/cleaned_model.pt`) and feeds the bridge the **real 512-d trajectory endpoint**. The paper's new disclosure follows the audit/tool; CLAIMS.md:3134 should be reconciled in a separate claims pass (out of scope here — this pass is paper-surface only).
- **`.tex`/`.md` structure divergence** remains (the `.tex` has no PEP-695 / honest-disclosure / hash-chained-ledger subsections). Per user direction, only the cross-references were fixed; a full structural re-sync is deferred.
- `docs/audit/wave385-figures.md` and the MANIFEST Wave 385 addendum retain the superseded `461ee92e…` reading as historical record (not edited).
