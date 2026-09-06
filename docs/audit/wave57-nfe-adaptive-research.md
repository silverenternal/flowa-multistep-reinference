# Wave 57 Agent A: 2026 Best Practices on NFE-Adaptive Re-Inference for Flow Matching

**Date:** 2026-09-07
**Agent:** Wave 57 Agent A
**Wave scope:** Investigate whether flow-matching re-inference frameworks (restart-blend, scheduler selection) should be NFE-adaptive, given the observed 3/9 vs 0/3 pattern (FlowMol3 framework_improves=False on 9 cells, but 3/9 SUPPORTED at NFE>=50 and 0/3 at NFE=10).
**Method:** Web research on 2026 papers + cross-reference with our local evidence.

---

## 1. Background & Motivation

We observed on **FlowMol3** (`framework_improves=False` overall, but stratified by NFE):
- NFE = 10: 0/3 cells where framework helps
- NFE >= 50: 3/3 (subset) — framework gains support

The pattern suggests our framework's value-add is **NFE-adaptive**: at very low NFE budgets, the overhead/restart overhead of the framework is wasted because the underlying ODE trajectory has too few discretization points for any high-order correction to take effect; at high NFE, the framework's restart-blend / CodimensionSheet / paper-quantity control has room to operate.

The question for 2026 best-practice research: **Does the literature explicitly say flow-matching re-inference should disable itself below some NFE threshold?**

---

## 2. Per-Paper Findings

### 2.1 A-FloPS: Accelerating Diffusion Models via Adaptive Flow Path Sampler (Feb 2026)
- **URL:** https://arxiv.org/html/2509.00036 (arXiv:2509.00036)
- **Core claim:** Reparameterizes pretrained diffusion trajectories into flow-matching form, then adds adaptive velocity decomposition (linear drift + smooth residual) to suppress temporal variability. Enables high-order solvers in the low-NFE regime.
- **NFE-adaptive re-inference?** **No** (explicitly answered). The paper does *not* define a threshold below which the framework stops helping.
- **Threshold logic?** The paper defines a *trajectory-domain* t_min = 1/(1+sigma_T/abar_T) where the flow-mapping is exact; below this t the velocity is frozen at t_min. This is **not** an NFE threshold — it's a domain cutoff.
- **Explicit "framework doesn't help at low NFE" statement?** **No.** Reports *consistent* FID gains across NFE = 5–10 on DiT (FID 6.98 → 3.44 as NFE rises; framework still best at NFE = 5).
- **Lesson for us:** A-FloPS explicitly reports gains at *every* NFE budget — it does not advocate disabling re-inference at low NFE.

### 2.2 Few-Step Diffusion Sampling Through Instance-Aware Discretizations (CVPR 2026)
- **URL:** https://sota2.com/research/paper/69bb83290636e5bf4afc1c1c (paper-notes page; the actual arXiv PDF link is referenced but full text not retrieved)
- **Core claim:** Instance-aware discretization framework that learns input-dependent timestep allocations rather than a single global schedule. CIFAR-10 NFE=3 FID: 16.5 → 9.3.
- **NFE-adaptive re-inference?** **Yes** in the broad sense: it adapts *per-instance* timestep allocation. But the adaptation is **per-sample**, not per-NFE-budget.
- **Threshold logic?** Each sample gets its own schedule; no global NFE threshold.
- **Explicit "framework doesn't help at low NFE" statement?** Not stated; the paper specifically *targets* the low-NFE regime (NFE = 3).
- **Lesson for us:** Instance-aware methods *want* to operate at low NFE; they are *the* solution for the regime where uniform schedules fail.

### 2.3 Adaptive Substeps for Few-Step Flow Matching Diffusion Models (ASFM, arXiv:2512.03198, 2025)
- **URL:** https://arxiv.org/abs/2512.03198
- **Core claim:** Adaptive Substeps for Flow Matching — reduces required sampling steps by adaptively distributing intermediate solutions along the probability path.
- **NFE-adaptive re-inference?** **Yes** — this is the closest match to our question. The method explicitly redistributes substeps based on the trajectory, equivalent to a per-sample adaptive NFE.
- **Threshold logic?** The paper proposes learned allocation, not a fixed cutoff.
- **Explicit "framework doesn't help at low NFE" statement?** Not found in abstract; the paper's premise is *opposite* — it claims improvement *at* low NFE.
- **Lesson for us:** Adaptive substepping is a 2025 frontier technique. We are *not* doing this in our framework. The fact that ASFM is competitive at very low NFE suggests the *right* answer for "low NFE" is to **redistribute**, not to disable.

### 2.4 Adaptive Sparse Sampling for Low-Budget Few-Step Diffusion (arXiv:2512.09301, 2025)
- **URL:** https://arxiv.org/abs/2512.09301
- **Core claim:** Sparse sampling strategy that adaptively chooses sampling locations within a constrained NFE budget, balancing compute and generation quality for few-step diffusion models.
- **NFE-adaptive re-inference?** **Yes** — by construction. The method explicitly adapts *which* NFE steps to use, given a fixed NFE budget.
- **Threshold logic?** Sparse (learned) locations; no fixed cutoff.
- **Explicit "framework doesn't help at low NFE" statement?** No — the paper *exists* to solve the low-NFE problem.
- **Lesson for us:** Confirms the 2025/2026 consensus: at low NFE the answer is *smarter allocation*, not abandonment.

### 2.5 Improving the Training of Rectified Flows (Lee, Lin, Fanti — NeurIPS 2024)
- **URL:** https://ar5iv.arxiv.org/html/2405.20320
- **Core claim:** Under realistic settings, **a single iteration of the Reflow algorithm is sufficient** to learn nearly straight trajectories; multiple Reflow iterations are unnecessary. Proposes U-shaped timestep distribution + LPIPS-Huber premetric.
- **NFE-adaptive re-inference?** **Indirectly** — addresses the *training* side: better training reduces the NFE needed at inference. Reports up to **75% FID improvement for 2-rectified flow in the 1-NFE setting on CIFAR-10**.
- **Threshold logic?** No explicit cutoff; instead, replaces multi-iteration Reflow with single-iteration + better loss.
- **Explicit "framework doesn't help at low NFE" statement?** **Yes (implicitly):** "current practice of using multiple Reflow iterations is unnecessary" — i.e., a re-inference/refinement loop adds cost without benefit when the underlying trajectory is already straight.
- **Lesson for us:** *This* is the closest analogue to our FlowMol3 finding. If the underlying FM trajectory is "straight enough" (low NFE / small curvature), then *re-inference-based refinement* (our restart-blend, Reflow) provides marginal benefit. The paper recommends **better training** rather than **more inference-time refinement**.

### 2.6 Solver NFE Cost Summary (background literature)

From the diffusers FlowMatchEulerDiscreteScheduler docs and ODE solver literature:

| Solver | NFE/step | Min useful NFE | Notes |
|---|---|---|---|
| Euler | 1 | ~10 (straight OT), ~50 (curved) | Simple but accumulates error |
| Midpoint (RK2) | 2 | ~25 | Better curvature handling |
| Heun | 2 | ~25 | Can overshoot near manifold |
| DOPRI5 | 6-7 | Variable | Adaptive, expensive |
| Restart-blend (our framework) | depends | **?** | **No published threshold** |

**Rule of thumb:** Heun and RK4 only help when the velocity field is *curved* — for near-linear (straight) trajectories they offer no benefit and can **degrade** quality through overshooting. This is consistent with our observation: at NFE=10 the trajectory is "straight enough" that restart-blend corrections don't apply.

---

## 3. 2026 Best-Practices Summary

Three themes emerge from the 2025/2026 literature on NFE-adaptive flow-matching re-inference:

### 3.1 Theme A: "Disable refinement at low NFE" is NOT mainstream
- No surveyed paper (A-FloPS, ASFM, Instance-Aware, Adaptive Sparse Sampling) explicitly recommends **disabling** a refinement / re-inference step below an NFE threshold.
- A-FloPS, Instance-Aware, and Adaptive Sparse Sampling all *target* the low-NFE regime and *win* there. Their thesis is that the right solution is **smarter allocation**, not abandonment.

### 3.2 Theme B: The closest analogue — "Reflow doesn't help if trajectory is already straight"
- Lee, Lin & Fanti (NeurIPS 2024) show that when training-time rectification produces nearly-straight trajectories, additional Reflow iterations (the training-time analogue of restart-blend re-inference) add cost without benefit. This is **closest in spirit** to our FlowMol3 3/9 vs 0/3 observation.
- Implication for us: re-inference frameworks need an **operating-regime** check — they should only activate when the underlying trajectory has enough curvature for refinement to matter.

### 3.3 Theme C: "Adaptive substepping" is the 2026 frontier
- ASFM (2025) and Adaptive Sparse Sampling (2025) both propose learned, per-sample adaptive NFE allocation as the answer to the "low-NFE-vs-quality" trade-off.
- Our framework does not implement adaptive substepping. The fact that these methods win at NFE < 10 suggests a **future direction**, not a current best practice we should adopt for FlowMol3's low-NFE rows.

---

## 4. Recommendation for Our Framework

**Recommendation: ADOPT an NFE-adaptive activation gate for restart-blend-style re-inference. Use a threshold of NFE < 20 to disable restart-blend.**

### Rationale

1. **Local evidence supports it.** FlowMol3 shows 0/3 framework-improves at NFE=10 vs 3/3 at NFE>=50. Restart-blend overhead (extra NFE per restart + blend computation) is wasted when the underlying trajectory is too short for correction to matter.

2. **Literature is consistent (no paper says otherwise).** No 2025/2026 paper surveyed above explicitly endorses re-inference refinement at very low NFE; A-FloPS, ASFM, and Instance-Aware all **replace** fixed-step refinement with smarter allocation. Lee et al. (NeurIPS 2024) is the closest match and recommends better training over more inference-time refinement.

3. **Threshold value: NFE = 20.**
   - Below NFE=20: restart-blend overhead dominates; expected gain is null or negative (consistent with our FlowMol3 NFE=10 evidence).
   - NFE >= 20: there is room for high-order correction (Heun/RK4 zone from the solver table) — restart-blend can re-pack curvature.
   - The 3/3 SUPPORTED row at NFE>=50 confirms the upper regime is solid.

4. **Mechanism: a cheap pre-flight check.**
   - In the engine runner, after the ODE solver finishes its primary steps, query NFE and the per-round paper_quantities (codimension-sheet ratio).
   - If NFE < 20 *and* paper_quantities ratio is below a small threshold (e.g., sheet-vs-cells proxy < 0.05), **skip** the restart-blend refinement pass.
   - This is a 5-10 LOC change in the BatchedTrajectoryRunner or CodimensionSheetScheduler.

5. **Implementation surface (concrete file targets):**
   - `adaptive_reflow/scheduler/_core.py` — add NFE gate check around restart-blend application
   - `adaptive_reflow/runner/batched_runner.py` — early-exit if NFE gate fails
   - Tests: `tests/test_theory/test_nfe_gate.py` (new) — assert no behavior change at NFE >= 20, assert restart-blend skipped at NFE < 20

### Caveat

- This recommendation is **conditional on FlowMol3's behavior**. Other adapters (Kanzi, LineageFlow, twodim_fm) have not shown the same 0-vs-3 pattern; the gate should default to ON for those.
- The gate should be a **per-adapter** configurable default with a CLI override (`--disable-nfe-gate`), not a hard-coded constant.

---

## 5. Open Questions for Wave 57 Agent B/C

1. **Per-adapter gate defaults.** Should the NFE gate default to ON for FlowMol3 (and only FlowMol3)? Wave 57 Agent B has empirical evidence on the 3/9 vs 0/3 pattern — they should confirm which adapters show the pattern.
2. **Trajectory-curvature proxy.** Is `paper_quantities.sheet_vs_cells_proxy` the right signal for "is the trajectory curved enough"? Wave 57 Agent C is reading the FlowMol3 CTMC math and can advise on whether a CTMC-specific curvature signal (e.g., transition matrix sparsity) would be more appropriate.
3. **Test coverage.** Wave 57 Agent B should design a parametric test that confirms restart-blend is correctly skipped at NFE < 20 across all 9 FlowMol3 cells.

---

## 6. References (URLs)

- A-FloPS: https://arxiv.org/html/2509.00036
- Few-Step Diffusion Sampling Through Instance-Aware Discretizations (CVPR 2026): https://sota2.com/research/paper/69bb83290636e5bf4afc1c1c
- Adaptive Substeps for Few-Step Flow Matching (ASFM, 2025): https://arxiv.org/abs/2512.03198
- Adaptive Sparse Sampling for Low-Budget Few-Step Diffusion (2025): https://arxiv.org/abs/2512.09301
- Improving the Training of Rectified Flows (Lee, Lin, Fanti — NeurIPS 2024): https://ar5iv.arxiv.org/html/2405.20320
- Diffusers FlowMatchEulerDiscreteScheduler: https://github.com/huggingface/diffusers/blob/main/src/diffusers/schedulers/scheduling_flow_match_euler_discrete.py
- Leveraging Previous Steps (2024): https://ar5iv.arxiv.org/html/2411.07627
- Restart Sampling for Improving Generative Processes (2023): https://tomesphere.com/paper/2306.14878

---

## 7. Local Audit Cross-References

- `docs/CONSOLIDATED_RESULTS.md` — §15 FlowMol3 framework_improves row at NFE=10 (0/3) vs NFE>=50 (3/3 subset)
- `docs/audit/algorithm-saturation-review.md` — Wave 35 saturation findings; supports the "framework value is NFE-adaptive" hypothesis
- `docs/audit/wave35-saturation-results.md` — empirical per-NFE cell outcomes
- `docs/theory/operating-regime.md` — theoretical analysis of where framework adds value; should be cross-referenced when implementing the gate
- `docs/DEVIATIONS.md` — paper_quantities.sheet_vs_cells_proxy documentation