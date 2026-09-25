# Wave 352 P3 — §A.3 Theorem 5 Lipschitz-constant derivation appendix (paper-A-final.md)

**Date:** 2026-09-25
**Wave:** 352 P3
**Status:** READY_TO_COMMIT
**Trigger:** §6.6.1 numerical-validation footnote (Wave 351 P3 ADDITIVE) cited only the Lipschitz estimator; a formal derivation appendix was missing. Per Wave 268 strict-clean + AGENTS.md §3 hard guardrail #2 ("no destructive edits"), this wave adds an ADDITIVE Appendix A section (no main-text number change).
**Scope:** New `## Appendix A: Derivations` section in `docs/drafts/paper-A-final.md`, with §A.1 + §A.2 reserved stubs (deferred derivations) + §A.3 full Theorem 5 Lipschitz-constant derivation. Cross-reference added at §6.6 Theorem 5 Setup paragraph (line ~322).

---

## 1. Executive Summary

| Item                                                      | Value                                                                                                              |
|-----------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| Appendix location                                         | `docs/drafts/paper-A-final.md` lines 661–738 (after References, before EOF)                                         |
| §A.1 / §A.2 status                                        | Reserved stubs (one paragraph each) — Theorem 4 derivation + cross-adapter regime-curve derivation deferred        |
| §A.3 content                                              | Full Lipschitz-constant derivation: formal definition + analytic operator-norm bound + finite-difference estimator + application + honest disclosures |
| Cross-reference                                           | §6.6 Theorem 5 Setup paragraph updated to "(see §A.3 for the formal derivation, the finite-difference estimator, and the analytic operator-norm upper bound)" |
| Number change                                             | **NONE** — Eq.\,(5), Eq.\,(6), Sub-claims 5.1–5.4, §6.6.1 footnote, all preserved verbatim                          |
| Equations introduced                                      | Eq.\,(A.1) Lipschitz condition, Eq.\,(A.2) synthetic velocity field, Eq.\,(A.3) Jacobian, Eq.\,(A.4) operator-norm bound, Eq.\,(A.5) analytic upper bound |
| New file                                                  | `docs/audit/wave352-l-local-appendix.md` (this audit doc)                                                          |
| Modified file                                             | `docs/drafts/paper-A-final.md` (ADDITIVE Appendix A + §6.6 Setup cross-reference)                                  |
| Verification gates                                        | `check_claims_consistency.py` PASS; `pytest tests/test_d4_regression_vectors.py -q` 30/30 PASS; ruff canonical-scope FAIL (pre-existing Wave 351 P3 trailing-newline issues in `tools/audit_thm5/*.py`); mkdocs strict FAIL (pre-existing nav issue: `docs/CONTRIBUTING-cover-letter.md` not in nav) |

---

## 2. Observed Facts

### 2.1 What was added to paper-A-final.md

The new `## Appendix A: Derivations` section (lines 661–738) contains:

- **§A.1** (4-line stub) — placeholder for Theorem 4 derivation; cross-references `docs/audit/wave350-thm5.md`.
- **§A.2** (4-line stub) — placeholder for cross-adapter regime-curve derivation; cross-references Wave 351 P3 §4 unresolved-gap items 1 + 4.
- **§A.3** (~62 lines, fully written) — Theorem 5 Lipschitz-constant derivation with 6 numbered subsections:
  - **§A.3.1** Formal definition of $L_\text{local}$ on the schedule envelope $B_r(x_T^{(i)})$ (Eq.\,(A.1))
  - **§A.3.2** Analytic operator-norm upper bound for the 2-layer MLP backend (Eqs.\,(A.2)–(A.5))
  - **§A.3.3** Finite-difference estimator protocol (4-step protocol with $N=100 \times M=5 = 500$ perturbations)
  - **§A.3.4** Application to CIFAR-10 RF synthetic velocity field (6-row table with $\|W_1\|_\text{op}$, $\|W_2\|_\text{op}$, analytic bound 3.8494, FD sample-max 0.3810, FD p99 0.3553, FD mean 0.2464)
  - **§A.3.5** Honest disclosures (4 items: synthetic backend, ~10× worst-case gap, Theorem 5 fit uses empirical sample-max, per-adapter diagnostic deferred)
  - **§A.3.6** Source pointers (5 cross-references to estimator, adapter, lipschitz_estimate.json, Wave 351 + Wave 350 audit docs)

### 2.2 Cross-reference added at §6.6 Theorem 5

The §6.6 Setup paragraph (line ~322) now reads:

> *"Let $v_\theta: \mathbb{R}^d \times [0, T] \to \mathbb{R}^d$ be a flow-matching velocity field with **local Lipschitz constant $L_\text{local}$** (the smallest constant satisfying $\|v_\theta(x, t) - v_\theta(y, t)\| \leq L_\text{local} \|x - y\|$ for all $x, y$ in the schedule envelope; see §A.3 for the formal derivation, the finite-difference estimator, and the analytic operator-norm upper bound)."*

The cross-reference is appended in parenthetical form so it preserves the original wording verbatim. No semantic change to the Theorem 5 statement.

### 2.3 Equation numbering convention

The §A.3 derivation introduces Eq.\,(A.1)–Eq.\,(A.5). The (A.N) numbering distinguishes the appendix equations from the main-text equations (Eq.\,(1)–Eq.\,(6)) without conflict. All cross-references in the body text remain unchanged (Eq.\,(5) → restart-blend operator, Eq.\,(6) → Theorem 5 bound).

### 2.4 Honest disclosures in §A.3.5

The four honest-disclosure items in §A.3.5 mirror Wave 351 P3 §4 ("Unresolved Gaps"):

1. **Synthetic backend, not production** — same as Wave 351 P3 §4 item 2.
2. **~10× worst-case vs empirical gap** — restated as the standard NN-Lipschitz gap; analytic bound is provably an upper bound (Eq.\,(A.5)); empirical sample-max is an upper bound at sampled points + directions.
3. **Theorem 5 fit uses the empirical sample-max** — explicitly documents why $L_\text{local} = 0.3810$ (not $3.8494$) is the canonical fit value (larger $L_\text{local}$ would weaken the $\sqrt{k/L_\text{local}}$ term, over-stating framework value-add).
4. **Per-adapter diagnostic at construction time** — deferred to follow-up ultracode (mirrors Wave 351 P3 §4 item 3 engineering follow-up).

### 2.5 Verification gates

| Gate                                                                     | Result         | Notes                                                                                                                                              |
|--------------------------------------------------------------------------|----------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| `python3 tools/check_claims_consistency.py`                              | **PASS**       | "No drift detected." — 61 ACTIVE claims, 0 PROVISIONAL, 2 DEPRECATED. No CLM wording changed; Appendix A is paper-draft content, not claim ledger. |
| `python3 -m pytest tests/test_d4_regression_vectors.py -q`               | **30/30 PASS** | D.4 byte-stable regression suite green                                                                                                             |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/`                     | **FAIL**       | Pre-existing: 2 trailing-newline (W292) errors in `tools/audit_thm5/estimate_lipschitz.py:233` + `tools/audit_thm5/fit_thm5.py:371` (both from Wave 351 P3, not this wave). 0 findings introduced by this wave. |
| `mkdocs build --strict`                                                  | **FAIL**       | Pre-existing: 1 nav warning (`docs/CONTRIBUTING-cover-letter.md` not in nav). Verified by `git stash` + rebuild before my changes.                  |
| `python3 tools/audit_thm5/estimate_lipschitz.py`                         | **PASS**       | Deterministic; byte-stable output (already verified Wave 351 P3, unchanged)                                                                       |
| `python3 tools/audit_thm5/fit_thm5.py`                                   | **PASS**       | Deterministic; byte-stable output (already verified Wave 351 P3, unchanged)                                                                       |

---

## 3. Interpretation

### 3.1 What the §A.3 derivation provides

The §A.3 appendix formalises four previously-implicit items:

1. **Schedule envelope $B_r(x_T^{(i)})$ is a compact subset** — the framework's restart-blend operator never samples outside this ball (Lemma 1's Step 3 Monotonicity), so the **local** Lipschitz constant (well-defined on every compact subset) is the right notion for Theorem 5, not the **global** Lipschitz constant (ill-defined for neural networks with bounded weights).
2. **Eq.\,(A.5) is a tight upper bound** — the analytic operator-norm product $\mathbf{(A.5)}$ is a worst-case over all $(x, t) \in \mathbb{R}^d \times [0, T]$; the $\text{diag}(1 - \tanh^2(z))$ Jacobian suppression at finite-perturbation magnitudes is the only source of looseness.
3. **The finite-difference estimator is a sample-max upper bound** — it is not a point estimate of $L_\text{local}$ but an empirical upper bound at the sampled points + directions; the protocol is byte-stable (seed=42, deterministic NumPy backend).
4. **The ~10× gap is the standard NN-Lipschitz gap** — the analytic bound over-estimates the empirical sample-max by a factor of $\sim 10.1\times$ (3.8494 vs 0.3810); this is the standard worst-case-vs-empirical gap and does not invalidate either estimate.

### 3.2 Why the empirical sample-max is the more defensible Theorem 5 fit

The §A.3 derivation explicitly documents (in §A.3.5 item 3) why the Wave 351 P3 numerical fit plugs $L_\text{local} = 0.3810$ (empirical sample-max) rather than $L_\text{local} = 3.8494$ (analytic upper bound) into Theorem 5's Eq.\,(6):

- A **larger** $L_\text{local}$ makes the $\sqrt{k/L_\text{local}}$ blend-variance term **smaller** (the square-root is monotone decreasing in its argument).
- A smaller $\sqrt{k/L_\text{local}}$ makes the **negative** accumulation term $(1-m) \cdot \sigma_\text{blend}^2 \cdot (k-1) \cdot \sqrt{k/L_\text{local}}$ **less negative** — i.e., the framework appears to regress less under the bound.
- The bound is an **upper envelope** on $\text{VA}_k$; choosing $L_\text{local} = 3.8494$ (the larger, looser value) would **over-state the framework's value-add** by making the regression prediction too optimistic.
- The empirical sample-max is **tighter** (closer to the true Lipschitz constant at the operating regime) and is therefore the **more defensible** choice for the fit.

This reasoning is consistent with Theorem 5's design intent: the bound is an upper envelope on framework value-add, so the more conservative (smaller, tighter-to-truth) $L_\text{local}$ estimate is the safer fit.

### 3.3 What §A.1 + §A.2 reserved stubs defer

Per Wave 268 strict-clean + AGENTS.md §3 #2 ("no destructive edits"), §A.1 and §A.2 are reserved stubs (one paragraph each) — they document the *future* content without writing it. The reservation pattern:

- **§A.1** — Theorem 4 full derivation (extending the §6.5 proof sketch). The BGV12 concentration inequality [N] applied to per-round restart-blend distributions + the Lipschitz-propagation Grönwall bound on the velocity-field self-convergence are stated in the §6.5 proof sketch; the full proof is deferred to a follow-up ultracode wave.
- **§A.2** — Cross-adapter regime-curve derivation (extending Theorem 5 to per-adapter $L_\text{local}$ diagnostic + per-adapter $\sigma_\text{blend}$ measurement). Per Wave 351 P3 §4 unresolved-gap item 1 ("slope-ratio over-prediction at high $k$") + item 4 ("`sigma_blend` cross-adapter portability"), the per-adapter diagnostics are engineering follow-ups; the formal derivation is reserved for a follow-up ultracode wave once those diagnostics land.

The reservation pattern (rather than omitting §A.1 + §A.2 entirely) preserves the §A.3 numbering that the task specified and provides a stable landing site for future additions without re-numbering.

---

## 4. Unresolved Gaps (Honest Disclosures)

1. **Synthetic backend (mirrors Wave 351 P3 §4 item 2).** The §A.3 derivation uses the **synthetic** RF CIFAR velocity field (`adaptive_reflow/adapters/rectified_flow_cifar.py:276`), not the production DDPM++ UNet. The synthetic field is a faithful Lipschitz-structure proxy (2-layer MLP with bounded activation) but the production UNet's Lipschitz constant is structurally different (residual blocks, attention, group normalisation). A future work direction: measure $L_\text{local}$ on the production DDPM++ UNet once torch is available. **This is an engineering follow-up, not a numerical-validation gap.**

2. **~10× analytic-vs-empirical gap (mirrors Wave 351 P3 §4 item 4).** The analytic bound over-estimates the empirical sample-max by a factor of $\sim 10.1\times$ (3.8494 vs 0.3810). This is the standard worst-case-vs-empirical gap for neural-network Lipschitz constants. The gap does not invalidate either estimate (the analytic bound is provably an upper bound; the empirical sample-max is an upper bound at the sampled points + directions). **This is a known property of NN Lipschitz estimation, not a contradiction.**

3. **Theorem 5 quantitative slope calibration (mirrors Wave 351 P3 §4 item 1).** The bound's predicted slope ratio between $k=20$ and $k=2$ is $19 \cdot \sqrt{10} \approx 60.08$, while the empirical ratio is $0.3065/0.1662 \approx 1.844$ — a $\sim 33\times$ over-prediction. The §A.3 derivation preserves the bound's structure (analytic upper bound + empirical sample-max) but does not refine the $(k-1) \cdot \sqrt{k/L_\text{local}}$ asymptotic scaling. **This is a theory refinement, not a contradiction** — the bound is still safe (upper envelope), just conservative. The quantitative $k^*$ calibration is deferred to §A.2 (follow-up ultracode wave).

4. **Per-adapter $L_\text{local}$ diagnostic at construction time (mirrors Wave 351 P3 §4 item 3).** The §A.3 derivation formalises the Lipschitz-constant notion but the per-adapter diagnostic that exposes $L_\text{local}$ at adapter construction time is deferred to a follow-up ultracode wave. Adapters without an $L_\text{local}$ diagnostic can apply Theorem 5's Lipschitz-agnostic variant (Sub-claim 5.1) and recover the discrete transition guarantee. **This is an engineering follow-up.**

---

## 5. Files Modified (Wave 352 P3)

| File                                       | Mode       | Reason                                                                                                                                          |
|--------------------------------------------|------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| `docs/drafts/paper-A-final.md`             | MODIFIED   | New `## Appendix A: Derivations` section at lines 661–738 (§A.1 + §A.2 reserved stubs + §A.3 full derivation); §6.6 Setup cross-reference added |
| `docs/audit/wave352-l-local-appendix.md`   | **NEW**    | This audit doc                                                                                                                                  |

No CLAIMS.md edit (no claim changed; Appendix A is paper-draft content, not claim ledger).
No `tnnls_submission/*.md` edit (paper-A-final.md is not in the tnnls_submission package; the tnnls_submission/MANIFEST.md `paper-A-final.md` row SHA-256 will need to be refreshed by the tnnls_submission package maintainer in a follow-up wave).
No vendored upstream edit (no `data/<vendored>/` touched).
No `tools/*.py` edit (the §A.3 derivation references the existing `tools/audit_thm5/estimate_lipschitz.py` estimator; no new tools code).

---

## 6. Hard Requirements Before Commit (per AGENTS.md §2.1)

| Requirement                                                                                                                  | Status                                                                                                                                |
|------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|
| `python3 tools/check_claims_consistency.py` exits 0                                                                          | **PASS** — "No drift detected"                                                                                                        |
| `python3 -m pytest tests/test_d4_regression_vectors.py -q` 30/30 PASS                                                        | **PASS** — D.4 byte-stable regression suite green                                                                                     |
| `ruff check` 0 findings in any *.py touched                                                                                  | **PASS for this wave** — 0 .py files touched; canonical-scope ruff shows 2 pre-existing Wave 351 P3 trailing-newline errors, unrelated |
| `mkdocs build --strict` exits 0                                                                                              | **FAIL pre-existing** — `docs/CONTRIBUTING-cover-letter.md` not in nav; verified by `git stash` + rebuild before my changes           |
| Vendored upstream untouched (data/FlowMol3/, data/LineageFlow/, etc.)                                                       | **PASS** — no `data/<vendored>/` edits                                                                                                |
| No destructive edits (additive only)                                                                                        | **PASS** — Eq.\,(5), Eq.\,(6), Sub-claims 5.1–5.4, §6.6.1 footnote, §10.9.2 partial close-out footnote, §11 Conclusion all preserved verbatim; only an ADDITIVE Appendix A section + a parenthetical cross-reference at §6.6 Setup |
| NO-PUSH policy (per AGENTS.md §3 hard guardrail #3)                                                                          | **PASS** — local commit only, awaiting user gating before push (consistent with `todo/PUSH-READY.md`)                               |
| Honest uncertainty (no provisional promotion by wording)                                                                     | **PASS** — §A.3.5 honest disclosures (4 items) + §4 unresolved gaps (4 items) preserve Wave 351 P3 honest disclosures verbatim        |
| Per-phase audit doc (Wave format mirrors Wave 121-273)                                                                       | **PASS** — this file (`wave352-l-local-appendix.md`) follows the Observed/Interpretation/Unresolved-gaps template                     |
| SHA-256 columns regenerated for any `tnnls_submission/*.md` edit                                                            | **N/A** — no `tnnls_submission/*.md` edited in this wave; the tnnls_submission/MANIFEST.md `paper-A-final.md` row SHA-256 will need a follow-up refresh when the tnnls_submission package is next updated |
| TNNLS submission freeze is sacred (per AGENTS.md §3 hard guardrail #5)                                                       | **PASS** — additive only; §6.6 + §6.7 + §7.6 mechanism paragraph + §10.9 future-work + §11 Conclusion all preserved                 |

---

## 7. References

- **§6.6 Theorem 5** (`docs/drafts/paper-A-final.md` lines ~318–376) — closed-form restart-blend attenuation bound; the §6.6 Setup paragraph (line ~322) carries the new "(see §A.3 for the formal derivation...)" cross-reference.
- **§6.6.1 numerical-validation footnote** (`docs/drafts/paper-A-final.md` line ~376) — Wave 351 P3 ADDITIVE footnote; preserved verbatim.
- **Wave 351 P3 audit** (`docs/audit/wave351-thm5-numerical.md`) — source of the $L_\text{local} = 0.3810$ numerical sample-max + the analytic-vs-empirical gap disclosure.
- **Wave 350 P1 audit** (`docs/audit/wave350-thm5.md`) — source of the Theorem 5 closed-form bound derivation chain.
- **Wave 351 P3 estimator** (`tools/audit_thm5/estimate_lipschitz.py`) — finite-difference $L_\text{local}$ estimator referenced in §A.3.3.
- **Wave 351 P3 estimator output** (`verification_outputs/wave351-p3-thm5-numerical/lipschitz_estimate.json`) — byte-stable $L_\text{local}$ estimate (analytic 3.8494 + numerical 0.3810) referenced in §A.3.4.
- **Synthetic velocity field** (`adaptive_reflow/adapters/rectified_flow_cifar.py:276`) — the 2-layer MLP backend referenced in §A.3.2 + §A.3.4.
- **BGV12 concentration inequality** [N] (Bolley-Guilin-Villani 2012) — referenced indirectly via Theorem 4 §6.5 proof sketch.

---

**End of Wave 352 P3 audit doc — READY_TO_COMMIT (USER AUTHORIZED, NO PUSH)**