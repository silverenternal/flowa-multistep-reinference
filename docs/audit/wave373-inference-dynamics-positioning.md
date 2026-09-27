# Wave 373 — Inference-dynamics positioning without an FID theorem

**Date:** 2026-09-27  
**Base commit:** `a2d376c`  
**Scope:** Manuscript prose, TeX/PDF, and additive TNNLS package notices. No code, config, checkpoint, vendored source, or GPU experiment was changed. The relevant sidecars are `.venvs/flowmol3_venv`, `.venvs/lineageflow_venv`, and `.venvs/kanzi_venv` per `docs/environments.md`; none was activated.

## Observed facts

1. The Wave 372 PDF described a feedback loop and a composite map but did not foreground the two linked changes in the sampling relation. The Markdown source already contained the stronger inference-dynamics framing in §2.2, while the TeX heading said only “Composite inference map.”
2. The frozen ODE remains $\dot x_t=v_\theta(x_t,t)$. The construction changes the initial-condition rule and iterates the unchanged endpoint map $\Phi_T^{v_\theta}$; it does not rewrite the two sides of that differential equation. Thus “both sides of the sampling relation” is the precise wording.
3. Theorem 4 gives $\|G_b^k(x)-x_b^*\|\le(mK)^k\|x-x_b^*\|$ only for an invariant envelope, fixed fresh input, and $mK<1$. Theorem 5 gives an exact squared-endpoint-error identity and the measurable inequality in manuscript Eq. (7). Neither result implies an Inception FID sign.
4. The R5b single-round evidence is protocol-sensitive: `verification_outputs/wave235-p1-r5b-fix.json` has four negative $\Delta$FID values at $N=200$, one only $-0.117\%$; `verification_outputs/wave247-p3-r5b-n1000-n1/summary.json` has two improving scheduler arms at $N=1000$, seed 42, matched NFE=50. R5c's smoke, intermediate, and production settings differ in architecture/data at the first transition; the intermediate setting has one seed (`docs/CLAIMS.md` CLM-059/060; `docs/CONSOLIDATED_RESULTS.md`). These records motivate diagnostics, not theorem-level FID predictions.

## Interpretation and changes

The revised abstract, introduction, §2.2, and TeX §II.B foreground the inference-dynamics reformulation. TeX and Markdown §3.8 explain that observed boundaries belong to particular instantiated composite maps under their checkpoint, schedule, and evaluator, while optional companion quantities are mostly dormant. After Theorem 4, the paper proposes measuring $q=mK$ across fixed-architecture checkpoint settings. After Theorem 5, it proposes measuring the terms of the squared-error identity across rounds with a specified endpoint target. These are falsifiable links to R5c and R5b; the paper explicitly retains the FID metric gap. The five editor-facing positioning points were carried into the frozen submission package as additive notices.

## Unresolved gaps

No production-adapter invariant envelope or Lipschitz constant $K$ has been estimated. No endpoint-target squared-error diagnostic or bridge to Inception FID has been measured. The current data therefore support an operating-regime hypothesis, not a prediction of the R5b or R5c FID direction. The smallest experimental next step is one fixed-checkpoint, fixed-evaluator, matched-NFE round-count study that logs the blend-error terms; a separate fixed-architecture checkpoint series can estimate $mK$.

## Verification

The final manuscript PDF was rebuilt twice with `pdflatex -interaction=nonstopmode -halt-on-error -output-directory=/tmp docs/drafts/paper-A-final.tex`, checked with `pdfinfo` and `pdftotext`, and remains eight IEEEtran double-column pages. `python3 tools/check_claims_consistency.py`, `mkdocs build --strict`, `python3 -m pytest tests/test_d4_regression_vectors.py -q`, manifest SHA-256/size verification, and `git diff --check` are recorded in the final turn checks. Vendored `data/` paths remain untouched.
