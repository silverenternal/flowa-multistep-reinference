# Wave 52 — SOTA Re-Inference Baselines Survey

**Author:** Wave 52 Agent A — research subagent
**Date:** 2026-09-07
**Status:** read-only research, no code changes
**Scope:** identify 2–3 SOTA re-inference / sampling baselines that compete with
the `adaptive_reflow` paper-quantity-driven re-inference framework, document
their math story, 2026 best practices, and relationship to our restart loop.

---

## 1. Background — what the framework actually competes against

`adaptive_reflow` is an **inference-time** re-inference framework: it runs
the *same* frozen ODE checkpoint over `R` rounds, where each round mutates
the boundary state via a closed-form capacity schedule
`n_cap(r)` driven by four paper-theorem computable constants
$(A_g, B_g, C_g, e_\rho)$ (Li 2026 Theorem 1). The model weights are frozen
across the run; only the per-round state evolves, and the per-round
discretization budget is paper-quantity-driven rather than heuristic.

This puts the competitive landscape in a narrow wedge:

* **training-time** few-step methods (rectified-flow reflow, progressive
  distillation, score-distillation) — produce a *new* checkpoint with
  straight couplings / compressed trajectories; compete on "few-step
  quality" but never re-query a frozen model.
* **inference-time** single-step / few-step methods (consistency models,
  latent consistency models, adversarial diffusion distillation) — learn
  an explicit "skip the ODE" mapping that consumes the model's output
  *once*; compete on "one-pass quality" rather than on adaptive
  re-query.
* **inference-time** adaptive solvers (DPM-Solver++, UniPC, EDM Heun,
  Dormand–Prince RK45) — keep the model and the trajectory, but adapt
  *the solver's* step selection to local truncation error; closest
  analog to our `n_cap(r)` schedule, but at the *sub-trajectory* level
  rather than the round level.

The right baseline set is the second and third categories — methods that
already perform the inference-time computation that the framework
multi-rounds. We pick the three that cover the most ground:

| # | Baseline | Category | Relation to paper-quantity restart |
|---|---|---|---|
| 1 | **Consistency Models (CM) + iCT** (Song 2023; Song & Dhariwal 2024) | inference-time, single/few-step | **Competitor.** iCT's log-normal schedule + adaptive discretization + pseudo-Huber loss is the closest published analog to a paper-quantity-driven restart — but baked into the loss rather than a per-round scheduler. |
| 2 | **Rectified Flow Reflow** (Liu et al. 2022, ICLR 2023 Spotlight) | training-time, coupling refinement | **Complement.** Reflow retrains the velocity field to straighten couplings; `adaptive_reflow` is the inference-time analog that re-queries the *same* frozen field with mutated initial states. Both target "few-step generation"; the axes are orthogonal. |
| 3 | **DPMSolver++ (multistep)** (Lu et al. 2022/2023) | inference-time, adaptive ODE solver | **Orthogonal competitor.** DPM-Solver++ adapts *the discretization step size* within a single ODE call via log-SNR Taylor expansion and x₀-prediction parameterization; the framework adapts *the round-level state* and lets the inner solver do its standard job. The two compose cleanly (DPM-Solver++ as the inner solver, `adaptive_reflow` as the outer round loop). |

We deliberately omit **Progressive Distillation** (Salimans & Ho 2022,
arXiv:2206.00364), **Latent Consistency Models** (LCM, Luo et al. 2023),
**Adversarial Diffusion Distillation** (ADD, Sauer et al. 2023), and
**UniPC** (Zhao et al. 2023) from the chosen set. Each is a 1-step or
few-step *distillation* approach — they do not re-query a frozen ODE
checkpoint and so do not measure the re-inference axis the framework is
about. They are noted in §6 as the natural next layer of comparison
*after* these three are settled.

We also omit **Flow Matching + Optimal Transport** (Lipman et al. 2023)
as a separate baseline because, in the linear-interpolation special case,
it is mathematically equivalent to Rectified Flow (Liu 2022) and to
Stochastic Interpolants (Albergo & Vanden-Eijnden 2023); the three were
published concurrently at ICLR 2023 and use the same straight-line
coupling. Where we cite "Flow Matching / Rectified Flow" below we mean
the unified ICLR-2023 family, not the entire FM literature.

---

## 2. Baseline 1 — Consistency Models (CM) + iCT (Song 2023; Song & Dhariwal 2024)

### 2.1 Math story

Consistency Models (Song et al., 2023, *ICML 2023*, arXiv:2303.01469) learn
a consistency function $f_\theta(x_t, t)$ that maps any point $x_t$ on a
PF-ODE trajectory to the trajectory's origin $x_0$ (or, in continuous-time
CM, to $x_\epsilon$ at a boundary). The defining property is **boundary
consistency**: for any two adjacent times on the same trajectory,

$$
f_\theta(x_{t_{n+1}}, t_{n+1}) = f_\theta(x_{t_n}, t_n)
$$

which lets inference run in *one* network call rather than a 50-step ODE
integration. Training uses either Consistency Distillation (CD) — distill
from a pre-trained diffusion model via a single-step PF-ODE Euler approximation
of the score — or Consistency Training (CT) — train from scratch with an
empirical estimate of the PF-ODE derivative. The iCT follow-up (Song &
Dhariwal, *ICLR 2024*, arXiv:2310.03289) replaces the LPIPS learned metric
with **pseudo-Huber losses**, drops the teacher EMA that biased CT, and uses
a **log-normal noise schedule** on the discretization steps — yielding
FID 2.51 on CIFAR-10 and 3.25 on ImageNet 64×64 in *one* step, and FID 2.24
/ 2.77 in two steps.

### 2.2 2026 best practices (per Wave 37 + Wave 45 web research)

* **Discretization is the key lever.** iCT/ECM use exponentially decreasing
  timesteps; CCM (Liu et al., *Dec 2024*, arXiv:2412.06295) adapts via PSNR
  thresholds; sCM (Lu & Song, *Oct 2024*, arXiv:2406.14548) approaches
  "infinite" discretization (infinitesimally close points); ADCM
  (arXiv:2510.17266, *Oct 2025*) extends to Flow Matching without manual
  tuning.
* **Better couplings.** Generator-Induced Coupling (Issenhuth et al., 2024)
  and OT couplings reduce independent-coupling variance — the same insight
  Rectified Flow reflow already exploits.
* **Multi-boundary consistency distillation** divides the trajectory into
  segments for easier training + better deterministic sampling quality.
* **Domain tweaks matter.** Consistency Policy (Prasad et al., 2024) for
  robotics uses low-variance noise sampling $\mathcal{N}(0, 1/T^2)$ and
  chains 2-3 steps for inference — a near-direct analog of our round
  budget.
* **Practical LCM / SD-XL pipelines** stabilize consistency at latent scale
  with LoRA adapters + mixed precision + CFG-aware distillation; SD3
  consistency distillation reached sub-1.0 FID gaps from teacher.

### 2.3 Relationship to `adaptive_reflow`'s paper-quantity-driven restart

**Direct competitor on the "few-step generation" axis**, and the strongest
single-step / few-step SOTA for diffusion-style generative models as of
2026-09.

iCT's log-normal discretization schedule and pseudo-Huber loss encode a
*static*, loss-baked version of the same information the framework encodes
*dynamically* via the four constants $(A_g, B_g, C_g, e_\rho)$. The mapping:

| CM / iCT concept | `adaptive_reflow` analog |
|---|---|
| boundary consistency $f_\theta(x_{t_{n+1}}, t_{n+1}) = f_\theta(x_{t_n}, t_n)$ | per-round state mutation + bounded-merge envelope at the round boundary |
| log-normal noise schedule (iCT) | closed-form cosine `n_cap(r)` driven by paper quantities |
| exponential discretization step schedule (ECM) | paper-quantity-driven per-round `n_cap(r)` |
| pseudo-Huber loss for Lipschitz smoothness | bounded-Lipschitz assumption underlying Theorem 1 |

iCT is **training-time** (loss baked into weights); `adaptive_reflow` is
**inference-time** (state mutation driven by observed quantities). iCT
amortizes the per-step cost across all calls; `adaptive_reflow` pays the
cost per call but adapts per call. They are not equivalent — iCT wins on
amortized 1-step latency; `adaptive_reflow` wins on the *control* axis
(per-round capacity is observable and tunable).

A reasonable experimental framing: on a fixed ODE checkpoint, compare

* **CM baseline**: 1-step iCT sampling (the strongest published
  single-step result for the model family);
* **`adaptive_reflow`**: 4-round run with cosine `n_cap(r)` + paper-quantity
  scheduler, single ODE solve per round at the chosen NFE.

The signed-mean metric axis used in `tools/run_real_ckpt_eval.py` is the
right tool: it asks "does the per-round control loop add value over the
single-call baseline?" — and CM's 1-step output is exactly the single-call
baseline to beat.

---

## 3. Baseline 2 — Rectified Flow + Reflow (Liu et al. 2022, ICLR 2023 Spotlight)

### 3.1 Math story

Liu, Gong, Liu (UT Austin) introduced **Rectified Flow** (arXiv:2209.03003)
with the regression objective

$$
L(\theta) = \mathbb{E}_{t, X_0, X_1} \, \| v_\theta(X_t, t) - (X_1 - X_0) \|^2,
\qquad X_t = t \cdot X_1 + (1-t) \cdot X_0,
$$

where $v_\theta$ is a velocity field, $X_0 \sim \pi_0$ is noise, and
$X_1 \sim \pi_1$ is data. After one round of *rectification* the learned
coupling is straight, so ODE integration is cheap — sometimes one Euler
step.

**Reflow** (Section 4 of the paper) repeats the procedure using synthetic
$(X_0, X_1)$ pairs drawn from the *learned* coupling; the retrained $v_\theta$
is straight on this refined coupling. Each reflow round is a full retraining
pass; the metric is "trajectory straightness" on a held-out batch. The
theoretical guarantee is that the rectification yields couplings with
**non-increasing convex transport costs** (covers all convex costs
simultaneously, not just Wasserstein).

The framework has been adopted in production by **Stable Diffusion 3**
(March 2024, with logit-normal timestep sampling), **FLUX.1** (Aug 2024,
12B-parameter rectified-flow transformer by Black Forest Labs), and
**InstaFlow** (Liu et al., *ICLR 2024*, arXiv:2309.06380), which adds a
three-stage text-conditioned reflow + distillation pipeline to push
SD-grade one-step FID to **23.3 → 22.4** on MS-COCO.

### 3.2 2026 best practices

* **Logit-normal timestep sampling** (Stable Diffusion 3) — midpoint bias
  for $t$, replaces uniform sampling. Aligns training-time signal density
  with inference-time error density.
* **Optimal-transport couplings** during reflow — generator-induced or
  mini-batch OT instead of independent noise-data pairing (used in SD3 and
  FLUX.1).
* **Reflow as a one-time training cost**, not a perpetual loop —
  production stacks converge to $K = 1$ or $K = 2$ reflow rounds and amortize
  via distillation (see InstaFlow's three-stage pipeline).
* **Equivalence to Flow Matching + OT** (Lipman et al. 2023, ICLR 2023) and
  Stochastic Interpolants (Albergo & Vanden-Eijnden 2023, ICLR 2023) — the
  three were published concurrently and coincide exactly in the
  linear-interpolation special case; this is *the* ICLR 2023 unified
  framework.

### 3.3 Relationship to `adaptive_reflow`'s paper-quantity-driven restart

**Closest training-time cousin.** `docs/distinguishing-from-reflow.md`
already draws the line: reflow operates at *training time* on a *new
velocity field* $v_\theta$; `adaptive_reflow` operates at *inference time*
on a *frozen velocity field* with a per-round mutated initial state. The
mathematical guarantees (straightness of the coupling vs. bounded-Lipschitz
convergence to the sheet measure $\nu_g$) are different.

The practical comparison: for a fixed dataset and architecture,

* **Rectified Flow + 2-Reflow baseline**: trained $v_\theta$ + 2 reflow
  passes (~$2\times$ training cost), 1-step sampling FID;
* **`adaptive_reflow` baseline**: vanilla 1-Rectified-Flow $v_\theta$ (no
  reflow), 4-round re-inference at the framework's per-round NFE.

The two are orthogonal and *compose* — one could reflow + re-inference —
but the natural baseline comparison is **same checkpoint, different outer
loop** (rectified-flow "single sample" vs. `adaptive_reflow` "4 rounds").
This is exactly the comparison already executed in the wave-10 LineageFlow
+ wave-15 RF-CIFAR + wave-42 LineageFlow real-ckpt eval runs; the
rectified-flow number is in `docs/CONSOLIDATED_RESULTS.md` Table 9.

The 2026 follow-up at arXiv:2410.04997 ("2024 flow matching interpretation")
revisits Rectified Flow from the flow-matching angle — still
training-time. The framework's per-channel convex combination
$(1-\beta)\cdot \mathrm{initial\_state} + \beta \cdot \mathrm{fresh}$
(`adaptive_reflow.contracts.apply_restart_distribution`) is the
inference-side analog but **does not modify** the velocity field.

---

## 4. Baseline 3 — DPMSolver++ multistep (Lu et al. 2022/2023)

### 4.1 Math story

DPMSolver (Lu, Zhou, Bao, Chen, Li, Zhu; *NeurIPS 2022 Oral*,
arXiv:2206.00927) is an **exponential integrator** for the diffusion ODE
built from Taylor expansions of the neural network prediction in log-SNR
space $\lambda_t = \log(\alpha_t / \sigma_t)$. The first- and second-order
variants achieve ~10–20 step sampling for *unguided* generation. The
follow-up **DPMSolver++** (Lu et al., *ICLR 2023*, arXiv:2211.01095)
addresses a robustness issue under classifier-free guidance: large
guidance scales narrow the convergence radius and the converged solution
drifts out of the training distribution. The two root-cause fixes:

1. **Data-prediction parameterization** ($\hat{x}_0$ instead of $\hat{\epsilon}$)
   — better conditioned under guidance.
2. **Dynamic thresholding** (from Imagen, Saharia et al. 2022b) — clamps
   intermediate samples to the training-distribution range.
3. **Multistep variant** — reduces effective step size to mitigate
   instability.

Result: **15–20 step guided sampling** for Stable Diffusion and Guided
Diffusion, replacing DDIM's 100–250 steps. Now the default scheduler for
Stable Diffusion in HuggingFace Diffusers (`DPMSolverMultistepScheduler`).

### 4.2 2026 best practices

* **DPMSolverMultistepScheduler** (second-order multistep) is the standard
  text-to-image choice; **DPMSolverSinglestepScheduler** is used when
  memory matters more than step count.
* **x₀-prediction parameterization** is now the default in EDM and most
  modern flow-matching pipelines (Rectified Flow uses it implicitly via
  velocity prediction).
* **Dynamic thresholding** has been generalized to **EDM's preconditioner
  network** (Karras et al. 2022) and to flow-matching pipelines via the
  framework's own bounded-merge envelope (see `merge.py`).
* **Related follow-ups**: ERA-Solver, SA-Solver, differentiable solver
  search; **UniPC** (Zhao et al., *CVPR 2023*) generalizes the
  predictor-corrector pattern to any order; **DPM-Solver-23** /
  exponential-integrator variants.

### 4.3 Relationship to `adaptive_reflow`'s paper-quantity-driven restart

**Orthogonal competitor — the two compose cleanly.** DPM-Solver++
adapts *the inner solver's step selection* within a single ODE call via
log-SNR Taylor expansion and x₀-prediction; `adaptive_reflow` adapts
*the outer round loop* via `n_cap(r)` and the per-round restart
distribution. The two layers do not interfere:

```
for r in 0..n_rounds:
    state = apply_restart_distribution(state, policy(r))   # framework
    state = dpmsolver_multistep(state, n_steps=20)        # solver
    paper_quantities = compute_paper_quantities(state)     # framework
    scheduler.update(paper_quantities)                    # framework
```

The framework already supports Heun / Dormand–Prince RK45 / explicit
Euler / midpoint as inner solvers (see
`adaptive_reflow.algorithm.integrators`). Adding DPMSolver++ as a
registered inner solver would slot in cleanly behind the
`IntegratorProtocol` boundary — a single-file change, no scheduler or
merge-operator modification needed.

The experimental framing: **same checkpoint, same outer loop, different
inner solver** — Euler baseline (NFE-equivalent) vs. DPMSolver++ (20
steps, log-SNR aware). This measures the framework's contribution
independent of the inner solver choice, which is what the v4
per-scheduler CIFAR-10 ablation (`docs/CONSOLIDATED_RESULTS.md` §4.3)
already does for the framework's own scheduler family.

---

## 5. Why these three (and not others)

| Candidate | Reason for exclusion |
|---|---|
| **Progressive Distillation** (Salimans & Ho 2022, arXiv:2206.00364) | Training-time student of a *teacher* ODE — produces a fixed checkpoint that does not re-query. Single-step CID-FID 3.0 on CIFAR-10 is strong, but the framework is about *adaptive re-query*; PD's student is static. **Recommended as a future 4th baseline** once CM / RF / DPM-Solver++ numbers are stable. |
| **Latent Consistency Models** (LCM, Luo et al. 2023) | Specialization of CM to the latent space (Stable Diffusion 1.5 / SDXL). Subsumed by CM for the purposes of "few-step" comparison; not a separate axis. |
| **Adversarial Diffusion Distillation** (ADD, Sauer et al., *arXiv:2311.17042*) | Adds a GAN discriminator loss on top of distillation. Outperforms LCM on SDXL but does not change the re-inference axis. |
| **Flow Matching + OT** (Lipman et al. 2023) | Mathematically equivalent to Rectified Flow in the linear-OT special case (ICLR 2023 unified framework). Picking RF covers FM; we cite both. |
| **Stochastic Interpolants** (Albergo & Vanden-Eijnden 2023) | Same equivalence as FM / RF. |
| **UniPC** (Zhao et al. 2023) | A 5th-order predictor-corrector solver. Belongs in the inner-solver category alongside DPMSolver++; covered if we add a 4th baseline. |
| **Dormand–Prince RK45 / Heun / RK4** | Already registered inner solvers in the framework; the framework's convergence-order verification (`tests/test_algo_uplifts/`) compares them. They are *part of* the framework, not a baseline. |

---

## 6. Recommended comparison matrix (for the next experimental wave)

For a fixed checkpoint (Kanzi, LineageFlow, RF-CIFAR, or 2D-toy),
side-by-side comparison:

| Configuration | Category | NFE | Per-call cost | Notes |
|---|---|---|---|---|
| **iCT 1-step** (Song & Dhariwal 2024) | inference single-step | 1 | 1× net | strongest published single-step FID |
| **Rectified Flow + 2-Reflow 1-step** (Liu 2022) | training-time few-step | 1 | 1× net | requires 2× training cost |
| **DPMSolver++ 20-step** (Lu 2023) | inference adaptive solver | 20 | 20× net (but cheap) | log-SNR Taylor; default SD scheduler |
| **`adaptive_reflow` 4-round, paper-quantity scheduler** (this framework) | inference re-inference | $4 \cdot \text{NFE}_{\text{inner}}$ | 4× solver cost | inner solver = Heun / DPMSolver++ / DOPRI5 |
| **`adaptive_reflow` 4-round + DPMSolver++ inner** | composed | $4 \cdot 20 = 80$ | composition | the natural "outer + inner" baseline |

The signed-mean metric axis (`tools/run_real_ckpt_eval.py`) is the right
tool to compare these five: it asks "does the framework's outer loop add
value over the strongest single-call baseline?" — with iCT 1-step and
Rectified-Flow reflow 1-step as the published SOTA ceilings and
DPMSolver++ 20-step as the published solver-side ceiling.

---

## 7. References (citations)

1. Song, Y., Dhariwal, P., Chen, M., Sutskever, I. (2023). *Consistency
   Models.* arXiv:2303.01469. ICML 2023.
2. Song, Y., Dhariwal, P. (2024). *Improved Techniques for Training
   Consistency Models (iCT).* arXiv:2310.03289. ICLR 2024.
3. Lu, C., Zhou, Y., Bao, F., Chen, J., Li, C., Zhu, J. (2022). *DPM-Solver:
   A Fast ODE Solver for Diffusion Probabilistic Model Sampling in Around
   10 Steps.* arXiv:2206.00927. NeurIPS 2022 Oral.
4. Lu, C., Zhou, Y., Bao, F., Chen, J., Li, C., Zhu, J. (2022/2023).
   *DPM-Solver++: Fast Solver for Guided Sampling of Diffusion
   Probabilistic Models.* arXiv:2211.01095. ICLR 2023.
5. Liu, X., Gong, C., Liu, Q. (2022). *Flow Straight and Fast: Learning to
   Generate and Transfer Data with Rectified Flow.* arXiv:2209.03003.
   ICLR 2023 Spotlight.
6. Liu, X., Zhang, X., Ma, J., Peng, J., Liu, Q. (2023/2024). *InstaFlow:
   One Step is Enough for High-Quality Diffusion-Based Text-to-Image
   Generation.* arXiv:2309.06380. ICLR 2024.
7. Lipman, Y., Chen, R. T. Q., Ben-Hamu, H., Nickel, M., Le, M. (2023).
   *Flow Matching for Generative Modeling.* arXiv:2210.02747. ICLR 2023.
8. Albergo, M. S., Vanden-Eijnden, E. (2023). *Stochastic Interpolants:
   A Unifying Framework for Flows and Diffusions.* arXiv:2303.08797.
   ICLR 2023 Spotlight.
9. Salimans, T., Ho, J. (2022). *Progressive Distillation for Fast
   Sampling of Diffusion Models.* arXiv:2206.00364.
10. Liu, X., et al. (2024). *Curriculum Consistency Model (CCM).*
    arXiv:2412.06295. Dec 2024.
11. Lu, C., Song, Y. (2024). *Simplified Consistency Models (sCM).*
    arXiv:2406.14548. Oct 2024.
12. Issenhuth, T., et al. (2024). *Improving Consistency Models with
    Generator-Induced Coupling.* arXiv:2406.09570. Jun 2024.
13. Karras, T., Aittala, M., Aila, T., Laine, S. (2022). *Elucidating the
    Design Space of Diffusion-Based Generative Models (EDM).*
    arXiv:2206.00364.
14. Saharia, C., et al. (2022). *Photorealistic Text-to-Image Diffusion
    Models with Deep Language Understanding (Imagen).* arXiv:2205.11487.
15. Zhao, W., et al. (2023). *UniPC: A Unified Predictor-Corrector
    Framework for Fast Sampling of Diffusion Models.* CVPR 2023.
16. Sauer, A., et al. (2023). *Adversarial Diffusion Distillation.*
    arXiv:2311.17042.
17. Li, Y. (2026). *Noised profile convergence for sheet-measure
    recovery in flow-matching generative models.* (Theorem 1 + Lemmas
    2-5; cited in `docs/paper-draft.md` §1 and the framework's
    `paper_quantities.py`.)
18. Nichol, A., Dhariwal, P. (2021). *Improved Denoising Diffusion
    Probabilistic Models.* arXiv:2102.09672. (Background on cosine
    schedule; cited in `docs/schedule-theory.md` §2.)

---

## 8. Decision summary

* **Pick Consistency Models + iCT, Rectified Flow Reflow, and
  DPMSolver++ multistep** as the three SOTA re-inference baselines for
  the next experimental wave.
* **Run all three on a fixed checkpoint** (Kanzi, LineageFlow, or
  RF-CIFAR) and report the signed-mean metric axis.
* **Add DPMSolver++ as a registered inner solver** under
  `IntegratorProtocol` if the comparison shows the inner-solver choice
  matters; otherwise leave Heun / DOPRI5 in place and cite DPMSolver++
  as a "supported alternative" in the paper writeup.
* **Defer Progressive Distillation, LCM, ADD, and UniPC** to a future
  wave — each is a viable 4th–5th baseline but does not change the
  re-inference axis the framework is about.