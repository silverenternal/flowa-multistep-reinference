# Wave 372 — Manuscript claim and typesetting audit

**Date:** 2026-09-27  
**Base commit:** `d3c8414`  
**Mode:** artifact audit followed by manuscript revision; no GPU sweep. The relevant sidecars are `.venvs/flowmol3_venv`, `.venvs/lineageflow_venv`, and `.venvs/kanzi_venv` (`docs/environments.md`); none was activated for this audit.

## Observed facts

1. `docs/drafts/paper-A-final.tex` opens `\begin{abstract}` at line 47 and closes it only after §11 at line 571. The PDF text starts with an empty `Abstract—` and then `I. 1 Introduction`. The TeX also lacks Markdown §2.2's composite-map formulation and Markdown §6.6's Theorem 5. The current PDF was created on 2026-09-25 and predates the Wave 367–371 Markdown edits.
2. R5b is protocol-sensitive. `verification_outputs/wave235-p1-r5b-fix.json` reports four negative ΔFID percentages at `n_rounds=1`, N=200, single seed, matched NFE=50; the EvidenceDriven arm is only −0.117%. `verification_outputs/wave247-p3-r5b-n1000-n1/summary.json` reports baseline FID 48.4059, cosine 48.5668, codimension 48.6594, evidence-driven 48.1669, and FreeTraj 48.2522 under N=1000, seed 42, matched NFE=50: two of four arms improve and two regress. Its `comparison.md` agrees. The similarly named top-level `verification_outputs/wave247-p3-r5b-n1000-n1.json` reports a different baseline FID (406.43) and 4/4 apparent wins; these readings must not be merged. `docs/audit/wave341-deep-audit.md` identifies the `summary.json` reading as the production-checkpoint result.
3. `verification_outputs/wave73_phase2_tier1_speedup.json` reports directly measured Tier-1 NFE speedups of 1.0×. The 2.5–10× range is an extrapolation, as documented in `tnnls_submission/supplementary_bundle/headline_evidence/NFE_SPEEDUP_2P5_TO_10X_SOURCE.md`.
4. Markdown Theorem 5 defines `VA_k := ΔFID_k` with negative values meaning improvement, then states an upper bound whose right side is strictly negative for `k≥2` when `m<1` and blend variance is positive; the prose calls this a regression guarantee. The inequality's sign cannot imply that conclusion. Its variance expansion writes a negative covariance cross term for a positive convex blend; the correct identity has a **positive** `2m(1-m)Cov(X,Y)` term. The manuscript does not establish a theorem connecting a blend's second moment to Inception FID.
5. Markdown Theorem 4 assumes a local Lipschitz velocity field but claims exponential decay of a flow error from Grönwall and per-round concentration. Local Lipschitz continuity alone gives stability or growth bounds, not a contraction rate. The cited BGV empirical-measure concentration result does not by itself supply the claimed round-to-round contraction. The stated rate requires additional hypotheses and an independent proof.

## Interpretation

The defensible contribution is the typed, auditable re-inference construction plus cell-specific empirical outcomes. A mathematically valid conditional contraction statement can be derived if the frozen flow map itself is Lipschitz with constant `K` and the restart memory fraction satisfies `mK<1` for a fixed fresh input. The exact convex-blend mean-square identity is also available without invoking FID. Neither statement alone predicts a first-round-only FID win. The manuscript should distinguish these structural properties from the observed R5b boundary.

## Unresolved gaps and edit plan

- Replace unsupported universal convergence and FID-sign claims with conditional mathematical statements and label R5b's first-round boundary as empirical. Retain the old formulas in Git history and this audit trail, not as live theorems.
- Align the main R5b prose to the N=200 and N=1000 source distinction. Keep the single-seed, checkpoint, sample-size, metric, and comparison direction visible.
- Reconcile the TeX with the corrected manuscript, close the abstract at the actual abstract, rebuild the PDF, and update any affected SHA-256 manifest rows and submission references. Check PDF pages and text extraction.

## Wave 372 revision and verification

- `docs/drafts/paper-A-final.md` now states the composite inference map, a conditional contraction theorem under `mK<1`, and the exact convex-blend squared-error identity. Its R5b text distinguishes the N=200 single-round probe, the N=1000 seed-42 production summary, and separate multi-round regressions. It labels 2.5–10× as extrapolation. Historical unsupported formulas remain traceable in Git history and older audit records.
- `docs/drafts/paper-A-final.tex` was rebuilt as a concise IEEEtran manuscript with a real abstract, corrected theory, an evidence-status table, cell-specific caveats, and no raw Markdown table. `pdflatex -interaction=nonstopmode -halt-on-error -output-directory=/tmp docs/drafts/paper-A-final.tex` completed twice; the resulting PDF has 8 pages, and page-one text extraction starts with the substantive abstract. One 4.14 pt overfull box remains in a method paragraph; no fatal LaTeX errors occurred.
- The frozen submission package received additive correction notices in `highlights.md`, `cover_letter.md`, and `MANIFEST.md`. The five current highlights supersede the historical theorem-rate and FID-attenuation claims. The manifest's current manuscript, PDF, TeX, highlight, and cover-letter SHA-256 and size rows were refreshed; its older descriptions remain historical.
- `python3 tools/check_claims_consistency.py`: exit 0, no drift. `mkdocs build --strict`: exit 0. `python3 -m pytest tests/test_d4_regression_vectors.py -q`: 30 passed. `git diff --check`: exit 0. No vendored `data/` path was edited. No long GPU run was launched.

## Remaining evidence limits

The contraction condition has not been measured on the production adapters; squared endpoint error has not been bridged to Inception FID. R5b's two single-round artifacts differ in sample size and evaluator baseline; a fixed-checkpoint, fixed-evaluator replication would be needed to estimate a transferable effect. R3's paired N=1000 and R6's three-seed live GPU re-verifications remain deferred as recorded in the claim ledger.
