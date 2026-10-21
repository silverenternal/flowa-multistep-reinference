# Wave 371 — Paper contribution and evidence framing

**Date:** 2026-09-27  
**Base commit:** `c70df31`  
**Scope:** `docs/drafts/paper-A-final.md` abstract, Introduction, and §7.9. Read-only evidence review followed by a focused prose edit; no experiment or framework code change.

## Observed facts

- The mathematical reformulation is already stated in paper §2.2: the frozen flow map is iterated from a restart-blended initial condition. Paper §3 describes the four typed control ports, §5 the adapter boundary, and §8 the reproducibility contract. The existing abstract listed these features without explaining their relationship.
- The per-cell status inventory in paper §7.2 and `docs/CONSOLIDATED_RESULTS.md` §15.103 reports four strong main cells, one tie, and six partial or supplementary cells. `docs/CLAIMS.md` CLM-060 and `docs/audit/wave363-all-cell-recipes.md` record the heterogeneous protocols. R1's three-seed pool was invalidated; R3's paired per-record result was measured at 200 records and a larger-sample result was projected; R6's tier-aware headline is counterfactual. Thus the former Introduction statement that every cell has three seeds and paired N=1000 was too broad.
- R5b changes direction across round counts at matched NFE (`docs/audit/wave336-r5b-mechanism.md`, `verification_outputs/wave235-p1-r5b-fix.json`); R5c changes direction between smoke and better-trained checkpoints (`docs/audit/mnist/wf334-r5c-regime-curve.md`, paper §7.8). The cross-budget NFE claim answers a different comparison question from these matched-NFE tests.
- `tnnls_submission/supplementary_bundle/headline_evidence/NFE_SPEEDUP_2P5_TO_10X_SOURCE.md` identifies `verification_outputs/wave73_phase2_tier1_speedup.json` as the NFE source: the 2.5–10× range is extrapolated from published trajectories, while directly measured speedup is 1.0× at one baseline NFE point. The former main-text wording described the extrapolation as an observed matched-quality compression.
- Reproducibility commands are `reproduce/08_verify_R6_recipe.sh` and `reproduce/09_verify_all_cell_recipes.sh`; sidecar environments are listed in `docs/environments.md` (`.venvs/flowmol3_venv`, `.venvs/lineageflow_venv`, `.venvs/kanzi_venv`). No sidecar was activated or sweep rerun for this prose change.

## Interpretation and edit

The defensible strength is the combination of a changed inference dynamic, a portable typed interface, an auditable decision trace, and an empirical operating boundary. The abstract now presents that chain. The Introduction and §7.1 state the per-cell evidence distribution and varying seed/sample policies; §7.6, §7.9, §9, and §11 label the NFE range as extrapolative. No result number, per-cell verdict, theorem statement, or claim-ledger row was altered.

## Unresolved gaps

- `docs/drafts/paper-A-final.tex` and `.pdf` predate the Wave 367–371 Markdown prose revisions and are not synchronized with the current Markdown manuscript. They require a separate source reconciliation and PDF rebuild before submission.
- The paper's historical addenda and the separately typeset TeX source still contain older universal seed/N=1000 language or stronger result summaries. This wave changes the current Markdown's highest-visibility surfaces; the per-cell §7.2 disclosures remain the authoritative protocol details.
- The source record contains different R5b scheduler counts at different waves and sample sizes. This edit deliberately states the direction change without promoting a scheduler-count claim.

## Verification

The edit is documentation only. Final gates: `python3 tools/check_claims_consistency.py` exited 0 (no drift); `mkdocs build --strict` exited 0; `python3 -m pytest tests/test_d4_regression_vectors.py -q` passed 30/30; and `git diff --check` found no whitespace errors. The abstract has 175 words. No code, config, or numerical evidence was touched.
