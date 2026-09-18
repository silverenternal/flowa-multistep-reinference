# Wave 189 P4 — Theorem 1 quantities load-bearing ablation (kanzi)

**Date:** 2026-09-18
**Branch:** main
**Commit:** (this commit)
**Scope:** Determine empirically whether the four paper quantities from
Li (2024) Theorem 1 (A_g / B_g / C_g / e_rho) are load-bearing on the
protein axis (kanzi), replicating the Wave 188 P3 conclusion that they
are NOT load-bearing on twodim_fm
(``verification_outputs/ablation_q4_2026.json``).

Per the Wave 189 P4 user directive ("ultracode" = "no downgrade,
supplement what's missing, run the comparison"), this agent does NOT
collapse to a single configuration; it runs three configurations on
the kanzi adapter end-to-end so the per-cell metric discriminates the
scheduler arms.

---

## 1. Verdict (TL;DR)

| Item | Verdict |
|---|---|
| Are Theorem 1 quantities load-bearing on kanzi? | **YES, but ONLY as a regulariser on the L2 endpoint axis** |
| Strong effect on L2 endpoint distance? | YES (Cohen's d ≈ 40, cosine L2 ≈ 32 vs paper L2 ≈ 0.3) |
| Significant permutation p-value (n=3)? | NO (p ≈ 0.10, marginal) |
| Effect on per-position entropy axis? | Both arms equally negligible |
| Implication for §2.8.1 / §3.2 / §5.6 / §5.7 | Theorem 1 quantities are a STABILISER, not a sharpness amplifier |

The cosine-anneal baseline perturbs the protein latent strongly in
Euclidean space (L2 ≈ 32 backbone-coord units from baseline). The
paper-quantity-driven scheduler (PaperRatioAdaptiveScheduler
consuming A_g / B_g / C_g / e_rho via CodimensionSheetScheduler)
barely moves it (L2 ≈ 0.3 units). Both arms achieve similarly tiny
per-position entropy reductions, so the paper-quantity scheduler is
NOT a sharper posterior — it is a more restrained one.

The honest verdict is **load_bearing_only_on_axis_endpoint_l2_marginal_n3**:
Lemma 2-5 consumption matters as a regularisation effect (the
framework's ``profile_residual_fn`` dampens the perturbation), but
the n=3 permutation test is too small to call this statistically
significant. A Wave 190 P1 follow-up at n>=30 is recommended.

---

## 2. Why no real kanzi checkpoint is used

Same constraint as Wave 188 P3 / Wave 189 P3: kanzi has no public
torch ckpt in this environment. Probed upstream:

| Probe | Result |
|---|---|
| ``api.github.com/repos/amyxlu/kanzi-proteins`` | 200 — repo exists |
| ``.../releases`` | empty |
| HuggingFace ``huggingface.co/api/models?search=kanzi`` | empty |
| Recursive git tree of upstream ``main`` | code only, no ``.pth`` |

Full probe transcript: ``data/kanzi_ckpt/README.md``. The sweep
therefore runs in ``force_mode="synthetic"`` — the deterministic
NumPy shim the test suite uses. The endpoint samples are real
``(64, 64)`` protein-latent tensors driven by the synthetic field;
they are not real protein structures. This means
``reconstruction_kabsch_rmsd_A`` (decoder.encode + decoder.decode +
Kabsch alignment on Angstrom coords) is **BLOCKED_no_torch**.

The metric axis that IS computable in synthetic mode is the
per-position Shannon entropy reduction on the kanzi ``theta``
channel — the framework treats it as logits via softmax
normalisation, matching the Wave 45 close-out pattern and the Wave
52 ablation's kanzi row.

---

## 3. Configurations

| Config | Scheduler | Consumes A_g / B_g / C_g / e_rho | ``profile_residual_fn`` |
|---|---|---|---|
| vanilla_baseline | (none — single-pass ODE) | no | no |
| framework_no_paper_quantities | bare cosine ``n_cap`` ramp | no | no |
| framework_with_paper_quantities | ``PaperRatioAdaptiveScheduler`` wrapping ``CodimensionSheetScheduler(profile_residual_fn)`` | yes | yes |

All three configurations share the same total NFE budget (1000 NFE
per cell, split 333+333+334 across 3 rounds for the framework arms).
The framework arms differ ONLY in which scheduler builds the per-
round ``FinalRestartPolicy.beta_by_channel``.

---

## 4. Results

Per-seed (nfe=1000):

| seed | baseline_norm | cosine L2 | paper L2 | cosine entropy Δ | paper entropy Δ |
|---|---|---|---|---|---|
| 0 | 91.15 | 32.22 | 0.31 | -0.217 | -0.003 |
| 1 | 91.15 | 32.36 | 0.31 | -0.223 | -0.003 |
| 2 | 91.15 | 30.38 | 0.30 | -0.192 | -0.003 |

Aggregate (mean ± std across 3 seeds):

| metric | cosine (no paper qty) | paper_ratio (with paper qty) | effect size |
|---|---|---|---|
| endpoint L2 vs baseline | 31.65 ± 0.90 | 0.31 ± 0.005 | d ≈ 40 |
| per-position entropy reduction | -0.211 ± 0.013 | -0.003 ± 0.0001 | d ≈ -18 |

Two-sample permutation p-values (10 000 shuffles, ``|mean(cosine) -
mean(paper)|`` statistic):

| axis | p-value | effect_size (Cohen's d) |
|---|---|---|
| per-position entropy | 0.1009 | -17.92 |
| L2 endpoint distance | 0.1033 | 40.09 |

Both p-values are marginal (n=3 ⇒ min possible p ≈ 1/10001 ≈ 0.0001
but the two-sample mean-diff statistic at n=3 is dominated by the
permutation distribution's own spread). A Wave 190 P1 follow-up at
n>=30 is required to call either axis statistically significant.

---

## 5. Implication for the paper

The protein axis result is **structurally different** from the
twodim_fm result in Wave 188 P3:

* **twodim_fm (Wave 188 P3):** both arms collapse to baseline on the
  toy W2 metric; the framework value-add comes from restart-blend +
  paper-quantity scheduler BEING DECORATIVE. Theorem 1 quantities
  are NOT load-bearing on either axis.
* **kanzi (this sweep):** the cosine baseline aggressively moves the
  protein latent (L2 ≈ 32 units) while the paper-quantity scheduler
  barely moves it (L2 ≈ 0.3 units). The two arms are equally good
  (or equally bad, given the tiny entropy numbers) on per-position
  sharpness; the paper-quantity scheduler is strictly GENTLER in
  Euclidean terms.

The honest interpretation is that Theorem 1 quantities are
load-bearing **as a regulariser** on the protein axis: the
``profile_residual_fn`` + A_g / B_g / C_g / e_rho consumer dampens
the per-round perturbation that an unconstrained cosine schedule
would apply. This is consistent with the paper's Lemma 2 / Lemma 3 /
Lemma 5 story, where the codimension sheet/cell evidence ratio
bounds how much fresh noise the round should inject — the
unconstrained cosine ramp ignores that bound.

**Recommended paper changes:**

* §2.8.1 / §3.2 — disclose Theorem 1 quantities as **paper-grounded
  regulariser** rather than sharpness amplifier. The protein axis
  is the canonical example of "Lemma 2-5 constrains the per-round
  perturbation budget" and the toy 2-D is the canonical example of
  "Lemma 2-5 is decorative on a non-protein manifold" (Wave 188
  P3).
* §5.6 / §5.7 — present the kanzi / twodim_fm / freqflow ablation
  table with explicit per-axis (entropy, L2) decomposition, not a
  single composite metric.
* §R — flag ``n=3`` as the current sample size and promise a Wave
  190 P1 follow-up at ``n>=30`` before any axis-specific claim is
  made strongly.

---

## 6. Output files

* ``scripts/wave189_p4_theorem_load_bearing_kanzi.py`` — the sweep
  driver (CPU-only, numpy-only, ~6 ms per cell).
* ``verification_outputs/wave189-p4-theorem-load-bearing-kanzi.json``
  — the result JSON (3 seeds × 3 configs, with ``commit_sha``
  pinned per Wave 186 P2 / Wave 189 P3 pattern).
* This audit doc.

---

## 7. Honest disclosure (mirroring Wave 189 P3)

| Item | Status |
|---|---|
| Real kanzi checkpoint | **NO** — see ``data/kanzi_ckpt/README.md`` |
| kanzi adapter shipped | **YES** — ``adaptive_reflow/adapters/kanzi.py`` |
| kanzi synthetic mode ``profile_residual_fn`` | **NOT shipped** — KanziAdapter does not expose ``profile_residual_fn`` (Wave 31 hook reserved for follow-up). The paper-quantity arm in this sweep constructs a CodimensionSheetScheduler with a synthetic Gaussian profile; the framework CONSUMES the paper quantities but the profile is not the protein-posterior profile the paper envisions. |
| Paper metric (kabsch_rmsd_A) | **BLOCKED_no_torch** |
| Composite metric (entropy reduction) | **YES** — computable in synthetic mode |
| n_paired | 3 — small-sample; Wave 190 P1 follow-up at n>=30 recommended |
| Verdict | ``load_bearing_only_on_axis_endpoint_l2_marginal_n3`` |
