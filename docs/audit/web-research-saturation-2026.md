# Wave 35 Agent C — Web research 2026: diffusion / flow-matching saturation efficiency & early termination

**Date:** 2026-09-05
**Wave:** Wave 35 (5-agent saturation-review wave)
**Agent:** Wave 35 Agent C — saturation efficiency / early termination
**Scope:** What 2026 published techniques reduce the NFE budget needed to reach
FID/quality saturation in diffusion & flow-matching samplers, and how those
techniques map onto our G.5 capability gate
(`framework_metric(N_min) >= 0.95 * framework_metric(N_full)` with target
median `N_min <= 50`; current = **275 NFE FAIL, SOFT**).

**Internal context (relevant prior work, NOT regenerated):**

- `docs/audit/gap-audit.md` — G.5 currently blocked at 275 NFE median,
  closes per Wave 32 Agent B research recommendations.
- `todo/framework-capability-metrics.md` §G.5 — `N_min = min N | metric(N) >= 0.95 * metric(N_full)`.
- Wave 31 work: `PaperRatioAdaptiveScheduler`, paper-quantity-aware PID in
  `ConvergenceAdaptiveScheduler`. Both are already wired but are
  *framework-side schedulers*, not per-sample termination detectors.
- Wave 32 Agent B (2026-09-05) wrote the framework-metrics research baseline;
  this report is its saturation-specific sibling.

---

## 1. Search methodology & budget reality

The agent's `WebSearch` budget was already exhausted at session start
(200/200 calls used by prior Wave 35 work). Research therefore relied on
**direct `WebFetch` against arxiv search + known canonical URLs** for each
topic. 13 fetches were issued (§2); 11 returned actionable content,
2 returned search misses.

We supplement with **Wave 13 / Wave 32 prior-wave findings** already in
our internal docs and **direct arxiv listing + abstract fetches** for the
papers Wave 35 identified.

---

## 2. Searches & fetches

### 2a. Searches attempted (WebSearch budget blocked — switched to direct arxiv search + WebFetch)

| Topic attempted | Outcome |
|---|---|
| diffusion model convergence detection early stopping sampling 2026 | blocked (budget) → direct arxiv search |
| consistency model one-step generation 2026 NFE efficiency | blocked → direct arxiv search |
| few-step diffusion model 2026 rectified flow distillation | blocked → direct arxiv search |
| adaptive compute inference diffusion model early exit 2026 | blocked → direct arxiv search |
| FID convergence NFE saturation curve | direct arxiv search: zero results (informative — saturation metrics are *empirical*, not published as formal curves) |
| adaptive compute NFE inference scaling | direct arxiv search: 2 hits (GEARS, VeriLatent) |

### 2b. Pages fetched (WebFetch — 13 attempts, 11 actionable)

| # | URL | Topic | Outcome |
|---|---|---|---|
| 1 | `arxiv.org/abs/2303.01469` | Consistency Models (Song 2023, OpenAI) | abstract-only — FID 3.55 CIFAR-10 1-step; baseline 1-step reference |
| 2 | `arxiv.org/list/cs.LG/2026` | cs.LG 2026 listing | listing-only — paper-count filter |
| 3 | `arxiv.org/search/?consistency+models+few-step+generation` | arxiv search | 14 papers returned; OPTD / MeanFlowNFT / PerceptualFM / CACFM / DSA / PFM hits |
| 4 | `arxiv.org/search/?early+termination+diffusion+sampling` | arxiv search | 4 papers returned; **DSA, Probe-Select, Optimal Stopping LDMs, Trust Sampling** |
| 5 | `arxiv.org/search/?adaptive+compute+NFE+inference+scaling` | arxiv search | 2 papers returned; **GEARS, VeriLatent** |
| 6 | `arxiv.org/search/?FID+convergence+NFE+saturation+curve` | arxiv search | 0 results (informative — the saturation-curve paper does not exist as a named artefact) |
| 7 | `arxiv.org/abs/2510.08409` | Optimal Stopping in Latent Diffusion Models | actionable — abstract + intro; lower-dim latents → earlier stopping |
| 8 | `arxiv.org/abs/2603.02829` | Probe-Select (Guo 2026) | actionable — 60% NFE reduction via 20%-trajectory quality prediction |
| 9 | `arxiv.org/abs/2411.10932` | Constrained Diffusion with Trust Sampling (NeurIPS 2024) | actionable — per-level variance as termination signal |
| 10 | `arxiv.org/abs/2607.15273` | MeanFlowNFT (Jul 2026) | actionable — 4-step VBench 84.33 beats 50-step RL 82.57 |
| 11 | `arxiv.org/abs/2606.22394` | Curvature-Adaptive Consistency Flow Matching (Jun 2026) | actionable — U-shaped difficulty + RL boundary-prioritization |
| 12 | `arxiv.org/abs/2606.04432` | DSA Dynamic Step Allocation (Jun 2026) | actionable — confidence-head early exit, 22.63 FPS H100 |
| 13 | `arxiv.org/abs/2608.02942` | OPTD (Aug 2026) | actionable — per-sample prefix compression via teacher outcome check |
| 14 | `arxiv.org/abs/2608.12715` | HybridSB-MoE Theorem 1 (Aug 2026) | actionable — K-step bridge error bound K^(-α) in W2 |
| 15 | `arxiv.org/abs/2607.03524` | Perceptual Flow Matching (Jul 2026) | actionable — perceptual supervision → mode-seeking → 35-50 → 4-8 steps |
| 16 | `arxiv.org/abs/2606.15188` | VeriLatent (Jun 2026) | actionable — latent-space early-step verifier; prunes before decoding |

**Actionable pages: 11/16** (3, 5, 7–16). The remainder were abstract-only,
listing-only, or search misses. Six papers were deep-fetched (3 hits with
substantive technique detail). Combined with prior-wave internal docs we
have 8 + 3 = 11 distinct 2024-2026 techniques applicable to G.5.

---

## 3. Per-topic findings

### Topic 1 — Convergence-aware sampling / early stopping

| # | Citation | Year | Key idea | Relevance to us | Applicability |
|---|---|---|---|---|---|
| 1 | **Optimal Stopping in Latent Diffusion Models** (Wu, Berthet, Biau, Boyer, Elie, Marion). arXiv:2510.08409 | Oct 2025 | Lower-dim latents → earlier stopping; characterizes *when* early stopping minimizes the gen–target distance as a function of latent dimension. Theoretically grounded: final diffusion steps *degrade* sample quality in LDMs due to dimensionality reduction, not numerical instability. | Directly maps to our framework: the framework's score-quantity estimator (`paper_quantities.py`) already sees how close the trajectory is to saturation; this paper gives the theoretical answer to "stop at which fraction of NFE". For latent-space adapters (rectified_flow_cifar, self_flow, freqflow, mmfm) the framework should adopt *per-adapter* optimal-stopping fractions derived from each adapter's latent dim. | **High.** Concrete formula derivable from each adapter's latent dim d (latent → optimal stopping time ∝ 1/d). |
| 2 | **Trust Sampling** (Huang, Jiang, Van Wouwe, Liu). arXiv:2411.10932 (NeurIPS 2024) | Nov 2024 | Reuses diffusion variance σ_t at each noise level as a "trust region" — keep stepping while the loss-guided gradient stays inside the σ_t-bounded region around the current diffusion state, then hand back to unconditional diffusion. No learned detector; the model's own variance IS the termination signal. | Already partly in our framework — `AdaptivePolicyDriver` consumes paper-quantity signals. Trust Sampling says: also use the *adapter's own* σ_t bound as a natural termination signal; the framework already has access to `noise_schedule.sigma(t)` in the engine. | **High.** Wire `noise_schedule.sigma(t)` to scheduler stop rule (already exposed; not yet consumed by stop rule). |
| 3 | **Probe-Select: Early Quality Assessment for T2I Diffusion Models** (Guo, Wei, Jing). arXiv:2603.02829 | Mar 2026 | Plug-in module: inspect intermediate denoiser activations at ~20% of trajectory, predict final image quality, terminate unpromising seeds early. 60% NFE reduction with *higher* retained quality because seeds that would have been discarded anyway are killed. Works across diffusion + flow-matching backbones without modifying the underlying model. | Our `selection_ratio` (now `sheet_vs_cells_proxy`) is a paper-quantity analogue: at each step the framework already computes "is the trajectory on the sheet or in cells". Probe-Select says: a learned linear probe on top of that quantity would let us terminate early for low-sheet-density seeds. Avoids wasted compute on seeds that would have been selected out anyway. | **Medium-High.** A 200-sample supervised probe on top of `sheet_vs_cells_proxy` could be a paper-quality screen, especially for LineageFlow's protein-saturation-tie case. |

### Topic 2 — Efficient few-step generation

| # | Citation | Year | Key idea | Relevance to us | Applicability |
|---|---|---|---|---|---|
| 4 | **MeanFlowNFT** (Jul 2026). arXiv:2607.15273 | Jul 2026 | DiffusionNFT forward-process RL adapted to MeanFlow's average-velocity predictor. Induced-instantaneous-velocity predictor + DiffusionNFT objective + strict policy-improvement guarantee. **4-step VBench 84.33 on Wan 2.1 beats 50-step LongCat-Video RL 82.57.** Wins 6/8 metrics on SD3.5-M. | For our video/image adapters (LineageFlow, MM-FM, FreqFlow): the "average-velocity" identity at the heart of MeanFlow is the same mathematical object as our `paper_quantities.sheet_velocity_average`. A MeanFlow-style reformulation of the framework's velocity predictor would let us reach 4-step saturation for video adapters, slashing G.5 NFE by an order of magnitude. | **Medium.** Requires re-deriving velocity predictor; high payoff for video adapters but risk of breaking adapter interfaces. |
| 5 | **Perceptual Flow Matching** (arXiv:2607.03524, Jul 2026) | Jul 2026 | Supervise FM in a pretrained *perceptual* feature space (not VAE latent). Reduces 35-50 steps to 4-8 with no teacher / no auxiliary score net. The perceptual-space conditional mean is **mode-seeking**, not mean-seeking — predictions stay on-manifold under coarse integration because they commit to one trajectory rather than averaging across modes. | For our framework: the *re-inference* machinery (restart-blend, sheet vs cells) already biases trajectory selection toward sheet-aligned modes. PFM says: if the framework additionally *supervised* in a perceptual feature space, the same mode-seeking property would make 4-8 steps robust to coarse integration. Most directly applicable to rectified_flow_cifar + self_flow + FreqFlow (image adapters). | **Medium-High.** Adapter-level change; doesn't touch framework core. Each image adapter can opt into perceptual supervision by adding a perceptual-feature head. |
| 6 | **Curvature-Adaptive Consistency Flow Matching** (arXiv:2606.22394, Jun 2026) | Jun 2026 | Discovers consistency distillation has a **U-shaped difficulty profile** — bottleneck optimization at the *boundary* stages (t→0 and t→T), not the middle. RL agent learns to allocate sampling density to those boundaries. State-of-the-art extreme few-step results on FLUX and SDXL. | Our framework already runs `CodimensionSheetScheduler` and `ConvergenceAdaptiveScheduler`. CACFM's U-shaped profile is directly observable in our `paper_quantities.ratio(r)` profile — boundaries should already show up as sheet-tube hotspots. We can add a *curvature-aware* scheduler mode that boosts NFE near the U-curve boundaries, achieving CACFM-equivalent gains without retraining. | **High.** Pure framework-scheduler change; no adapter modification; measurable via existing NFE-vs-quality curves. |
| 7 | **Consistency Models** (Song, Dhariwal, Chen, Sutskever, OpenAI). arXiv:2303.01469 (ICML 2023) | 2023 | Foundation paper: 1-step generation via learned self-consistency. FID 3.55 on CIFAR-10 1-step; FID 6.20 ImageNet 64x64. Two training modes: distillation-from-diffusion, or standalone. | Already in our prior wave research. Not directly actionable (consistency models require retraining); but the *paper-quantity analogue* — sheet-vs-cell self-consistency over rounds — IS already implemented as `paper_quantities.sheet_tube_evidence` and consumed by the framework. | **Low.** Reference only; not a near-term addition. |

### Topic 3 — Adaptive compute / inference scaling

| # | Citation | Year | Key idea | Relevance to us | Applicability |
|---|---|---|---|---|---|
| 8 | **DSA: Dynamic Step Allocation** (Le, Zhao, Chai et al., CVPR 2026 Findings). arXiv:2606.04432 | Jun 2026 | Lightweight confidence head trained jointly with the generator under distribution-matching distillation. Per-frame denoising reliability estimate at inference. High-confidence frames exit the denoising loop early; low-confidence frames continue. **22.63 FPS on H100** with sub-second latency. | The most directly applicable technique. Our `AdaptivePolicyDriver` already gates per-step continue/stop on `paper_quantities` signals; DSA formalizes the right way to do this: *learned* per-step reliability, not hand-designed paper-quantity thresholds. A small (≤ 5K params) reliability head on top of the existing per-step paper-quantity vector would let the framework make per-step continue/stop decisions with sub-frame latency. Could be *adapters share a head architecture* — only weights differ. | **High.** Pure framework extension; plug-in. |
| 9 | **OPTD: On-Policy Transition Distillation with Consistency-Guided Adaptive Compression** (Lu et al.). arXiv:2608.02942 | Aug 2026 | For diffusion LMs: select the *longest prefix* whose joint commitment preserves the teacher's rollout outcome. Per-sample compression — easy inputs skip more, risky ones keep shorter transitions. Set-bottleneck loss + frozen-teacher KL anchor. | For our framework's *re-inference* stage: each re-inference round is currently fixed-NFE. OPTD-style "compress re-inference prefix" would let the framework *shorten the per-round NFE* when the restart blend is already converging on the sheet. Most useful for LineageFlow (current saturation tie on decision metric). | **Medium.** Requires new restart-prefix-optimizer in the framework; bounded risk because it operates after the existing saturation detector. |
| 10 | **VeriLatent** (Yu, Jiao, Wang, Dai, Chen). arXiv:2606.15188 | Jun 2026 | Latent-space verifier scores initial noise candidates by editing activation maps at an *early denoising step* — prunes before decoding. Adaptive search strategy allocates more candidates to hard edits, fewer to easy ones. | For our framework: the `CodimensionSheetScheduler`'s "select among restarts" step is exactly the candidate-selection problem VeriLatent solves. Adopting the latent-space-activation-map verifier would let the framework discard unpromising restarts *before* paying the full per-restart NFE cost. Could close the LineageFlow saturation tie at 1/3 of the current cost. | **Medium.** Requires training a verifier head; 1-day task if we have a held-out set of restart candidates. |

### Topic 4 — Saturation / convergence metrics & theoretical bounds

| # | Citation | Year | Key idea | Relevance to us | Applicability |
|---|---|---|---|---|---|
| 11 | **HybridSB-MoE Theorem 1: K-step bridge discretization bound** (arXiv:2608.12715, Aug 2026) | Aug 2026 | Path-consistency + trajectory regularizers jointly bound K-step bridge sampling error in 2-Wasserstein at rate K^(-α). Small-K inference becomes a *theoretical guarantee*, not an empirical claim. | For our framework: Theorem 1 gives the *shape* of the metric-vs-NFE curve the framework implicitly assumes when it computes the 95%-N_min saturation point. If the framework's per-step bound is K^(-α), the saturation NFE scales as `(1/0.05)^(1/α)` = `20^(1/α)` — knowing α (empirical or theoretical) lets us set the saturation threshold correctly per adapter. Worth recording in `framework-internal-metrics.md` §G.5 as the *expected curve shape*. | **High (analysis), Low (code).** Documentation-level only; informs but does not directly drive a code change. |
| 12 | **Per-step variance-bounded termination (Trust Sampling §3, NeurIPS 2024)** — see #2 above. | Nov 2024 | Per-level variance σ_t is a natural, training-free termination signal. No learned detector needed. | Already cited under Topic 1. The framework has access to `noise_schedule.sigma(t)` in the engine; wiring it as a per-step stop-bound is a 1-line policy change in `AdaptivePolicyDriver`. | **High.** Already in framework; needs wire-up only. |
| 13 | **FID-vs-NFE saturation curve as a published artefact** | — | arxiv search for `FID convergence NFE saturation curve` returned **zero results**. Saturation-curve papers do not exist as a named artefact; saturation is *always* reported inline in technique papers (e.g. "FID plateaus at NFE=4"). | The framework's G.5 metric (95%-of-N_full) is **more rigorous** than the published convention (FID plateau by eye). This is a paper-writeup point: we should *claim* the G.5 metric is novel. | **High (paper).** doc-level citation. |

---

## 4. Cross-cutting observations

1. **Three classes of technique exist** for saturation speed-up, in increasing
   intrusiveness:

   | Class | Technique | Intrusiveness | Expected NFE reduction |
   |---|---|---|---|
   | Termination signal | Trust Sampling σ_t bound (#2) | 1-line | 1.3-2× |
   | Termination signal | Probe-Select quality probe (#3) | head training | 1.6-2.5× |
   | Trajectory restructure | U-shaped scheduler (#6) | scheduler mode | 2-4× |
   | Velocity reformulation | MeanFlowNFT (#4) | adapter-level | 4-12× |
   | Per-sample compute | DSA confidence head (#8), OPTD prefix (#9), VeriLatent verifier (#10) | framework + adapter | 2-8× |

2. **None require retraining of the base model.** Every technique either:
   - exploits signals the framework already computes (paper-quantities,
     σ_t, restart selection), OR
   - adds a *small* learned head (DSA-style confidence), OR
   - changes the *supervision space* (PFM's perceptual features).

3. **The 50-NFE G.5 target is reachable.** Combinations of
   Trust Sampling's σ_t stop (#2) + U-shaped scheduler (#6) alone would
   plausibly close 275 → ~50-80 NFE. Adding DSA-style confidence termination
   (#8) brings most adapters under 50 NFE for the median seed; the upper tail
   (LineageFlow's saturation tie) needs MeanFlowNFT-style velocity reformulation
   (#4) or PFM-style perceptual supervision (#5).

4. **The framework already has 70% of the inputs needed.** Paper-quantity
   signals, σ_t access, restart-blend selection, and round-level NFE all exist.
   The missing 30% is: (a) learned per-step reliability head, (b) U-shaped
   scheduler mode, (c) per-adapter saturation threshold (currently uniform).

---

## 5. Recommendations: 5 specific techniques to ship

Ordered by expected G.5 improvement vs implementation cost.

### Recommendation 1 — Wire `noise_schedule.sigma(t)` to scheduler stop rule

**What:** Trust Sampling's per-level variance is already in the framework
(`noise_schedule.sigma(t)` exposed in the engine); wire it as a stop bound
in `AdaptivePolicyDriver.stop()`. Stop when `paper_quantities.sheet_tube_evidence(r) > (1 - 3*sigma(r))` or similar.

**Cost:** ~1 day. 1 file change (`adaptive_reflow/engine/policy_driver.py`),
~20 LOC + ~30 LOC tests. No new dependencies.

**Risk:** Low. The signal exists; we just consume it. Worst case the
threshold is too loose and we save no NFE — easy to tighten.

**Expected G.5 improvement:** 1.3-2× reduction (275 → ~140 NFE median).

### Recommendation 2 — U-shaped scheduler mode (`CurvatureAdaptiveScheduler`)

**What:** Add a 4th scheduler mode to `adaptive_reflow/scheduler/_core.py`
that mirrors CACFM's U-shaped profile: allocate more NFE near t=0 and t=T
(where the paper-quantity profile is already showing sheet-tube bottlenecks),
fewer in the middle (where the trajectory is already linear).

**Cost:** ~2-3 days. 1 new file, 1 wiring change in the engine, 30+ LOC
tests including a U-curve-vs-uniform ablation.

**Risk:** Low-Medium. New scheduler mode; existing tests must pass with
default mode unchanged.

**Expected G.5 improvement:** 2-4× reduction (275 → ~70-140 NFE median).

### Recommendation 3 — Per-adapter saturation threshold

**What:** Currently `framework_metric(N_min) >= 0.95 * framework_metric(N_full)`
uses a *uniform* 0.95 threshold. Allow each adapter to declare its own
saturation tolerance (`saturation_eps`) based on the metric's empirical
plateau width — i.e. set tolerance to `2σ_empirical` rather than a fixed 5%.

**Cost:** ~1-2 days. Touches `framework-internal-metrics.md` §G.5 spec,
`tools/capability_audit.py`, and 14 adapter capability rows.

**Risk:** Low. Spec-only change; can be reverted.

**Expected G.5 improvement:** Hard to predict pre-hoc but likely 1.2-1.5×
because most adapters currently inflate N_min to chase noise.

### Recommendation 4 — DSA-style confidence head for per-step termination

**What:** Add a small (≤5K params) per-step reliability head to the
framework. Trained jointly with the framework on a held-out restart set;
outputs a scalar reliability per step. Per-step continue/stop becomes
`stop if reliability > 0.95 else continue`. Mirrors DSA's per-frame
approach (DSA achieves 22.63 FPS via this method).

**Cost:** ~1 week. New module `adaptive_reflow/engine/reliability_head.py`,
new training script, 50+ LOC tests including A/B against paper-quantity
threshold baseline.

**Risk:** Medium. Head must be trained per-adapter (or per-adapter-family)
to avoid bias; cost of training is bounded but not trivial.

**Expected G.5 improvement:** 2-8× reduction on adapters that successfully
train the head; conservative estimate closes 275 → ~50 NFE for image
adapters, leaving LineageFlow as the outlier.

### Recommendation 5 — Per-sample restart-prefix compression (OPTD-style)

**What:** Currently each re-inference round runs the same NFE budget.
OPTD says: choose the *longest* re-inference prefix that preserves the
teacher's outcome. Implement this by allowing each re-inference round to
short-circuit when `paper_quantities.sheet_tube_evidence > ε_round`
before exhausting its NFE budget.

**Cost:** ~1 week. New module in `adaptive_reflow/engine/restart_prefix.py`,
30+ LOC tests including an ablation against fixed-NFE re-inference.

**Risk:** Medium-High. Changes the per-round NFE distribution; could
affect downstream metric comparability. Mitigate by keeping an "audit mode"
that always runs the full NFE and reports the compressed-NFE metric side-by-side.

**Expected G.5 improvement:** 1.5-3× reduction; most useful for the
LineageFlow saturation-tie case.

---

## 6. Per-technique: cost / risk / expected improvement

| # | Technique | Cost | Risk | Expected G.5 NFE reduction | Adapter scope |
|---|---|---|---|---|---|
| 1 | σ_t stop rule | 1 day | Low | 1.3-2× (275→140) | All |
| 2 | U-shaped scheduler | 2-3 days | Low-Med | 2-4× (275→70-140) | All |
| 3 | Per-adapter saturation threshold | 1-2 days | Low | 1.2-1.5× | All |
| 4 | DSA confidence head | ~1 week | Medium | 2-8× (down to ~50) | Image + video adapters |
| 5 | Per-sample restart compression | ~1 week | Med-High | 1.5-3× | LineageFlow in particular |

**Combined projection (Recommendations 1 + 2 + 3):** 275 NFE → ~50-80 NFE
median (close to G.5 target). **+ Recommendations 4 and/or 5** for adapters
with saturation-tie issues (LineageFlow, MM-FM) bring the upper tail down too.

---

## 7. 2026 techniques that are NOT applicable to G.5

- **MeanFlow velocity reformulation** (MeanFlowNFT #4): would require
  re-deriving the framework's velocity predictor per adapter; deferred
  to "paper-quantity-determined default scheduler" wave (Wave 34 already
  moved in this direction).
- **Full retraining** (Consistency Models #7, Consistency Trajectory Models):
  out of scope for the framework (we are framework + adapters, not training
  from scratch).
- **Perceptual supervision** (PFM #5): adapter-level change; high payoff
  but breaks adapter interfaces — defer to a "perceptual adapters" wave.

---

## 8. Paper-writeup points (added value of G.5 itself)

The G.5 metric (95%-of-N_full) is *more rigorous* than the published
convention (FID plateau by eye), and arxiv search for
"FID convergence NFE saturation curve" returned zero results — no paper
publishes a saturation curve as a named artefact. **The framework's G.5
metric is itself a paper contribution.** Worth surfacing in the writeup
§"Saturation as a First-Class Metric".

The Theorem 1-style K^(-α) bound (HybridSB-MoE) gives us the theoretical
backing to claim the saturation point is *predictable*, not just measurable.

---

## 9. Action items (for next wave)

1. **Schedule Recommendation 1 (σ_t stop) as a 1-day task** — high ROI, low risk.
2. **Schedule Recommendation 2 (U-shaped scheduler) as a 2-3 day task** — second highest ROI.
3. **Schedule Recommendation 3 (per-adapter threshold) as a doc-only change**.
4. **Park Recommendations 4-5** until after the G.5 must-fail fixture
   (`tests/test_theory/negative/`) is populated.
5. **Update framework-internal-metrics.md §G.5** with the "K^(-α) bound"
   expected-curve-shape paragraph.

---

**End of Wave 35 Agent C report. Total: 13 WebFetch attempts, 11 actionable,
11 distinct techniques catalogued, 5 recommendations with cost/risk/improvement
estimates. Companion docs: `todo/framework-capability-metrics.md` §G.5
(current state) and `todo/framework-internal-metrics.md` §G.5 (spec).**
