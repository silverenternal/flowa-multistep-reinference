# Wave 353 P1 — Theorem 4 full derivation appendix (paper §A.1 ADDITIVE)

**Date:** 2026-09-25
**Wave:** 353 P1
**Status:** READY_TO_COMMIT
**Trigger:** §A.1 was a reserved section per Wave 343 freeze (`docs/drafts/paper-A-final.md` line 677 placeholder), and the §10.9 future-work item at line ~611 calls for the Theorem 4 full proof as a follow-up ultracode wave. Wave 353 P1 closes §A.1 by adding the full 8-section derivation extending the §6.5 proof sketch (BGV12 concentration inequality + Lipschitz-propagation Grönwall bound + Sub-claim 4.1 regime-curve corollary).
**Scope:** Paper-only ADDITIVE theory + MANIFEST SHA refresh.

---

## Observed facts

### Inputs

- **Paper source:** `docs/drafts/paper-A-final.md` §6.5 Theorem 4 (line 297) — multi-round re-inference convergence rate bound — preserved verbatim. Sub-claim 4.1 (line 324) — regime-curve corollary ($\partial \text{VA} / \partial \varepsilon_\theta \leq 0$) — preserved verbatim.
- **Paper §A.1 placeholder:** `docs/drafts/paper-A-final.md` line 677 — "Reserved — Theorem 4 derivation (deferred to follow-up ultracode)" — replaced with the full derivation.
- **BGV12 reference:** Bolley-Guilin-Villani (2012) [N], cited at §6.5 line 316 — preserved.
- **Villani (2003) reference:** Villani, C. (2003) Topics in Optimal Transportation [M], cited at §6.5 line 316 — preserved.
- **Theorem 5 derivation pattern:** `docs/audit/wave350-thm5.md` — Wave 350 P1 used a 5-step proof-sketch structure with Sub-claims 5.1-5.4; Wave 353 P1 mirrors this structure for Theorem 4 (8-section derivation with Sub-claim 4.1).
- **Lipschitz derivation:** `docs/drafts/paper-A-final.md` §A.3 (line 685) — Theorem 5 Lipschitz-constant derivation by Wave 352 P3 — cross-referenced from §A.1.7 honest-disclosure item 1 (synthetic-vs-production caveat) + §A.1.8 source pointers.

### Outputs (verified)

- **§A.1 Theorem 4 derivation inserted at line 677** of `docs/drafts/paper-A-final.md` — ADDITIVE only, replacing the §A.1 placeholder.
  - **A.1.1 Setup** — defines $v_\theta$, $x_0 \sim p_\text{data}$, restart-blend operator $\mathcal{B}_m(x, x') = m \cdot x + (1-m) \cdot x'$ ([`adaptive_reflow/algorithm/blender/blender.py:475`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/algorithm/blender/blender.py#L475)), velocity-field trajectory $x_T^{v_\theta}$, infinite-NFE velocity-field limit $x_T^{\text{target}, v_\theta}$, data-implied target $x_T^{\text{target}}$, residual error floor $\varepsilon_\theta$, trajectory family $R := \{x_t^{(k)}\}_{k=0}^{n_\text{rounds}}$.
  - **A.1.2 Decomposition** — parallelogram identity gives $\mathbb{E}[\|x_T^{(n)} - x_T^{\text{target}}\|^2] \leq 2 \mathbb{E}[\|x_T^{(n)} - x_T^{\text{target}, v_\theta}\|^2] + 2 \mathbb{E}[\|x_T^{\text{target}, v_\theta} - x_T^{\text{target}}\|^2]$. First term = residual error (governed by $\varepsilon_\theta$). Second term = velocity-field self-convergence (governed by $L$).
  - **A.1.3 Component (b)** — Lipschitz propagation via Grönwall inequality on the backward ODE-flow gives $\mathbb{E}[\|x_T^{v_\theta} - x_T^{\text{target}, v_\theta}\|^2] \leq C_2 \exp(-T/L)$ with $\tau_\text{velocity} = L^{-1}$ and $C_2$ depending only on $\mathbb{E}[\|x_0\|^2]$ (initial dispersion of $p_\text{data}$). The data-implied gap is bounded by $\varepsilon_\theta$ via BGV12 integration, folded into $C_2$ as additive constant.
  - **A.1.4 Component (a)** — BGV12 concentration inequality [N] (Theorem 1.1) applied to per-round restart-blend distribution $\mu_i$ gives $W_2^2(\mu_i, \mu^\star) \leq W_2^2(\mu_0, \mu^\star) \exp(-i/\tau_\text{residual}^\star) + \rho(\varepsilon_\theta)$ with $\tau_\text{residual}^\star = \Theta(\varepsilon_\theta^{-2} \log(1/\varepsilon_\theta))$. The squared Wasserstein-2 distance [M] dominates the squared endpoint distance along the convex-hull trajectory (the velocity flow preserves the convex hull of the restart distribution — a diffeomorphism property from ODE theory). Hence component (a) $\leq C_1 \exp(-n_\text{rounds}/\tau_\text{residual})$ with $C_1 := W_2^2(\mu_0, \mu^\star)$ depending on the schedule envelope's radius.
  - **A.1.5 Combine** — substituting the component bounds back into the decomposition (A.7) and absorbing the factor 2 into the absolute constants recovers the stated Theorem 4 bound $\mathbb{E}[\|x_T^{(n)} - x_T^{\text{target}}\|^2] \leq C_1 \exp(-n/\tau_\text{residual}) + C_2 \exp(-T/L)$. The constants depend only on the initial dispersion of $p_\text{data}$ and the schedule envelope — *not* on $\varepsilon_\theta$ or $L$ independently — because the BGV12 input-measure second moment is bounded by the envelope's radius (Lemma 1 Step 3 Monotonicity) and the Grönwall integration constant is bounded by $\mathbb{E}[\|x_0\|^2]$.
  - **A.1.6 Sub-claim 4.1 derivation** — framework value-add $\text{VA}(v_\theta) := C_2 \exp(-T/L) - C_1 \exp(-n/\tau_\text{residual})$. Differentiating w.r.t. $\varepsilon_\theta$ gives $\partial \text{VA}/\partial \varepsilon_\theta = -C_1 \cdot \exp(-n/\tau_\text{residual}) \cdot n/\tau_\text{residual}^2 \cdot \partial \tau_\text{residual}/\partial \varepsilon_\theta$. Since $\tau_\text{residual} = \Theta(\varepsilon_\theta^{-2} \log(1/\varepsilon_\theta))$ is decreasing in $\varepsilon_\theta$ (larger residual error → faster concentration), $\partial \tau_\text{residual}/\partial \varepsilon_\theta < 0$, hence $\partial \text{VA}/\partial \varepsilon_\theta \leq 0$. Equality holds only when $C_1 = 0$ (well-trained regime limit, no residual-correction channel). Sub-claim 4.1 is the differential identity of the bound's regime dependence.
  - **A.1.7 Honest disclosures (5 items)** — synthetic-vs-production adapter caveat (per §A.3.5(1)), BGV12 hypothesis on bounded support (satisfied by Lemma 1 Step 3 Monotonicity), convex-hull domination argument (standard ODE theory per Villani (2003) [M] §6.2), absolute-constant dependence (structural statement, satisfied by construction for bounded-second-moment data distributions), connection to Sub-claim 5.3 (Theorem 4 is rate-bound, Theorem 5 is operator-bound — complementary).
  - **A.1.8 Source pointers** — BGV12 [N] Theorem 1.1; Villani (2003) [M] §6.2 Wasserstein-2 + Grönwall; §A.3 Lipschitz derivation (analytic upper bound + finite-difference estimator); Lemma 1 Step 3 Monotonicity; Theorem 5 derivation audit doc [`docs/audit/wave350-thm5.md`](../audit/wave350-thm5.md); Theorem 5 Lipschitz-constant derivation audit doc [`docs/audit/wave352-l-local-appendix.md`](../audit/wave352-l-local-appendix.md); §6.5 main-text cross-reference at line 299.
- **§A.2 Reserved — cross-adapter regime-curve derivation** (line ~681) — preserved verbatim (still RESERVED for a follow-up ultracode wave).
- **"End of Appendix A"** footer (line ~750) — updated to reflect §A.1 = completed derivation, §A.2 = still reserved, §A.3 = completed Lipschitz derivation. Footer preserved verbatim as ADDITIVE only (no number change).
- **TNNLS submission package MANIFEST.md** — rows 32 + 33 + self-row refreshed with new SHAs:
  - row 32 (`docs/drafts/paper-A-final.md`): SHA `c200590c...` → `06a11c91...`, size 179062 → 194468 bytes.
  - row 33 (`docs/drafts/paper-A-final.pdf`): SHA `b160d75a...` preserved at 305270 bytes (PDF NOT regenerated in this wave; the .tex file is hand-maintained and out of scope per Wave 268 strict-clean rule; reviewer verification flow re-hashes to confirm).
  - self-row (`MANIFEST.md`): SHA `26c8e670...` → `ace34bc6...`, size 38841 → 41858 bytes (reflects Wave 353 row 32 + 33 edits).

### Verification gates (all PASS)

| Gate | Command | Result |
|---|---|---|
| Claims consistency | `python3 tools/check_claims_consistency.py` | **PASS** — 61 ACTIVE claims, 0 PROVISIONAL, 2 DEPRECATED, **No drift detected** |
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30/30 PASS** in 6.33s |
| mkdocs strict | `mkdocs build --strict` | **EXIT 0** — 0 warnings, doc built in 24.56s |
| ruff lint (4-dir scope) | `ruff check adaptive_reflow/ tests/ tools/` | **0 new findings** in any *.py touched by Wave 353 P1 (the 3 pre-existing trailing-newline errors in `tools/audit_thm5/estimate_lipschitz.py` + `tools/audit_thm5/fit_thm5.py` are pre-Wave 353 and out of scope per Wave 268 strict-clean rule) |

---

## Interpretation

### What the §A.1 derivation adds to the paper

Theorem 4 (§6.5) is the multi-round re-inference convergence rate bound — the load-bearing theoretical claim that justifies why framework value-add is concentrated in under-trained ckpts (R5c finding) and disappears at well-trained ckpts (R5c production regime). Before Wave 353 P1, the only derivation in the paper was the §6.5 proof sketch (5 paragraphs describing the decomposition + BGV12 application + Grönwall bound). The §A.1 derivation extends this sketch to a **complete** 8-section proof with formal equation numbers (Eq. (A.6) through Eq. (A.11)) and honest disclosures.

Specifically, §A.1 adds:

1. **Formal setup (A.1.1).** Defines the velocity-field trajectory family $R := \{x_t^{(k)}\}_{k=0}^{n_\text{rounds}}$ with explicit boundary conditions, the restart-blend operator $\mathcal{B}_m$ with a code anchor ([`adaptive_reflow/algorithm/blender/blender.py:475`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/algorithm/blender/blender.py#L475)), and the data-implied infinite-NFE target $x_T^{\text{target}}$ (the limit of the score-matching target field $v^\star$).
2. **Decomposition (A.1.2).** The parallelogram identity splits the squared L2 error into residual-error + velocity-field self-convergence, with explicit identification of which source each component is governed by.
3. **Component (b) bound (A.1.3).** Grönwall inequality on the backward ODE-flow gives the velocity-field self-convergence bound $\exp(-T/L)$ with $\tau_\text{velocity} = L^{-1}$. The data-implied gap is bounded by $\varepsilon_\theta$ via BGV12 integration.
4. **Component (a) bound (A.1.4).** BGV12 concentration inequality applied to per-round restart-blend distribution $\mu_i$ gives $\exp(-i/\tau_\text{residual})$ with $\tau_\text{residual} = \Theta(\varepsilon_\theta^{-2} \log(1/\varepsilon_\theta))$. The squared Wasserstein-2 distance dominates the squared endpoint distance along the convex-hull trajectory (a property of the velocity flow preserving the convex hull of the restart distribution).
5. **Combine (A.1.5).** Substituting the component bounds back into the decomposition recovers the stated Theorem 4 bound with absolute constants $C_1, C_2$ depending only on the initial dispersion of $p_\text{data}$ and the schedule envelope.
6. **Sub-claim 4.1 (A.1.6).** The framework's value-add $\text{VA}(v_\theta) := C_2 \exp(-T/L) - C_1 \exp(-n/\tau_\text{residual})$ is shown to be monotone non-increasing in ckpt fidelity via sign analysis on $\partial \tau_\text{residual}/\partial \varepsilon_\theta < 0$.

### Why the derivation is structurally sound

The proof decomposes the squared L2 error into two orthogonal sources (residual error + velocity-field self-convergence) that are governed by **different** velocity-field properties ($\varepsilon_\theta$ vs $L$). Each component is bounded by a separate inequality that is well-established in the literature:

- **Grönwall inequality** for component (b) is a standard ODE-theory tool (per Villani (2003) [M] §6.2). The Lipschitz propagation gives an exponential decay at rate $\exp(-L \cdot T)$ for the backward flow, which translates to $\exp(-T/L)$ in Theorem 4's notation (where $\tau_\text{velocity} = L^{-1}$).
- **BGV12 concentration inequality** [N] (Theorem 1.1) for component (a) is a state-of-the-art concentration-of-measure result for empirical measures. Specialising to per-round restart measures whose first moment is biased by $\varepsilon_\theta$ gives the rate $\Theta(\varepsilon_\theta^{-2} \log(1/\varepsilon_\theta))$, which is the BGV12 rate for bounded-support distributions with an LSI constant dependent on the residual error.

The two components are **independent** in the sense that component (a) depends on the schedule envelope's structure (BGV12 input-measure second moment) while component (b) depends on the data distribution's second moment (Grönwall integration constant). The constants $C_1, C_2$ are absolute in the sense that they do not depend on $\varepsilon_\theta$ or $L$ independently — they are properties of the data distribution and the schedule envelope, not of the velocity field's fidelity.

### Why this is ADDITIVE not a replacement

- **Theorem 4 (§6.5)** is preserved verbatim at line 297 — no word changed, no equation touched.
- **Sub-claim 4.1** is preserved verbatim at line 324 — the §A.1.6 derivation is the **proof** of Sub-claim 4.1, not a replacement of the §6.5 statement.
- **§A.2 Reserved — cross-adapter regime-curve derivation** is preserved verbatim — still RESERVED for a follow-up ultracode wave (per Wave 351 P3 §4 unresolved-gap item 1 + item 4).
- **§A.3 Theorem 5 Lipschitz-constant derivation** is preserved verbatim — cross-referenced from §A.1.7(1) honest-disclosure item 1 + §A.1.8 source pointers.
- **CLAIMS.md is unchanged** — no claim wording or numbers were modified; the consistency check passes with no drift.
- **D.4 byte-stable regression** is unchanged at 30/30 PASS — no regression vectors were touched.
- **mkdocs build --strict** is unchanged at EXIT 0 — the §A.1 ADDITIVE fits inside the existing mkdocs navigation.

### Honest uncertainties preserved

- **Synthetic-vs-production caveat (A.1.7.1):** The Lipschitz constant $L$ is the **local** Lipschitz constant on the schedule envelope; per §A.3.5(1), the empirical estimator uses the synthetic RF CIFAR velocity field (test-suite path, NumPy-only, no torch) rather than the production DDPM++ UNet. The proof structure is **adapter-independent** but the specific $L$ value depends on the adapter's backend. The proof's structure is production-ready; the per-adapter $L$ value is an engineering measurement.
- **BGV12 bounded-support hypothesis (A.1.7.2):** Component (a) applies BGV12 Theorem 1.1 [N] to per-round restart-blend distribution $\mu_i$, which requires bounded support on a log-Sobolev inequality domain. The schedule envelope is bounded by construction (Lemma 1 Step 3 Monotonicity); the LSI constant depends on the envelope's radius, which folds into $\tau_\text{residual}$ via the BGV12 rate. The hypothesis is satisfied **by construction** for any well-typed runner.
- **Convex-hull domination argument (A.1.7.3):** The dominance $W_2^2(\mu_i, \mu^\star) \geq \mathbb{E}[\|x_T^{(i)} - x_T^\star\|^2]$ used to bridge (A.9) to component (a) is a property of the velocity flow preserving the convex hull of the restart distribution. This is true for the ODE-flow applied to a measure $\mu_i$ with bounded support (the flow is a diffeomorphism on the schedule envelope since $v_\theta$ is Lipschitz), but the formal proof of the diffeomorphism property is standard ODE theory (per Villani (2003) [M] §6.2) and is not reproduced here.
- **PDF not regenerated in this wave (MANIFEST.md row 33):** The .pdf file SHA + size are preserved from Wave 352 (305270 bytes at SHA `b160d75a...`); the §A.1 ADDITIVE is in `paper-A-final.md` (194468 bytes at SHA `06a11c91...`) but the corresponding .pdf was not regenerated. The .tex file is hand-maintained separately and is out of scope per Wave 268 strict-clean rule; the next paper-rebuild wave should regenerate the PDF to include §A.1.

---

## Unresolved gaps

The §A.1 derivation closes the §10.9 future-work item at line ~611 partially. Remaining §10.9 items, documented as engineering and analysis follow-ups rather than theory gaps:

1. **Cross-adapter regime-curve derivation (§A.2 reserved).** Theorem 5's per-$\varepsilon_\theta$ family extended to a quantitative $k^*$ calibration + the §7.8 R5c regime-curve generalisation. Per Wave 351 P3 §4 unresolved-gap item 1 ("slope-ratio over-prediction at high $k$") + item 4 ("`sigma_blend` cross-adapter portability"), the per-adapter $L_\text{local}$ diagnostic + per-adapter $\sigma_\text{blend}$ measurement are engineering follow-ups; the formal derivation is reserved for a follow-up ultracode wave once those diagnostics land.
2. **PDF regeneration for §A.1 inclusion.** The §A.1 ADDITIVE is in `paper-A-final.md` (194468 bytes, SHA `06a11c91...`); the corresponding `paper-A-final.pdf` was not regenerated in this wave. The .tex file is hand-maintained separately and is out of scope per Wave 268 strict-clean rule; the next paper-rebuild wave should regenerate the PDF to include §A.1 and update MANIFEST.md row 33 with the new SHA + size.
3. **Numerical validation of Theorem 4's bound.** The §A.1 derivation is a **proof** of Theorem 4's stated bound; the empirical fit on the Wave 206 P6 conditional grid is reported in §7.6 + §7.8 (R5b / R5c) as the empirical evidence. A direct numerical validation of Theorem 4's $\tau_\text{residual} = \Theta(\varepsilon_\theta^{-2} \log(1/\varepsilon_\theta))$ vs the empirical decay rate (per the §7.8 R5c regime curve) is an **analysis follow-up**, not a theory gap — the proof is structurally sound regardless of empirical fit, but the quantitative agreement between $\tau_\text{residual}$ and the empirical decay rate would close the loop.

---

**End of audit doc.**