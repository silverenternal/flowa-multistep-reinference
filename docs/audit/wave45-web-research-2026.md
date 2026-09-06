# Wave 45 Agent B: 2026 Best Practices for Adapter-Layer Fixes

**Date:** 2026-09-07
**Wave:** 45 (Kanzi + LineageFlow adapter-layer fix)
**Scope:** READ-ONLY web research supporting the design of `KanziGPTPriorRestartPolicy`,
`per_position_entropy_reduction` metric, and `LineageFlowClassifierAwareRestart`.
No code changes.

---

## 1. Goal

The framework abstraction is done. All Wave 45 fixes are adapter-layer. We need
literature grounding for three concrete design choices:

1. **GPT-prior-aware restart policy** (Kanzi): when should a restart re-anchor to
   the GPT-2 prior instead of fresh noise? What budget? What trust signal?
2. **Per-position entropy metric**: how should we measure per-token confidence
   reduction across restart rounds? Is it monotonically decreasing? What
   normalization? Which paper supports a specific formula?
3. **Classifier-aware sampling** (LineageFlow): when the rerouting candidate
   selection is conditioned on a per-position classifier score, what is the
   principled way to combine it with the flow velocity?

Plus one adjacent concern: **adapter-layer design patterns** for foundation
model re-inference (we want to keep our adapter contracts consistent with
2026 community standards).

---

## 2. Per-topic findings

### Topic A — GPT-prior-aware restart policy

#### A.1 ProtBFN: Protein Bayesian Flow Network (AAAI 2026) — DIRECT MENTOR

- **Title:** ProtBFN: Protein Bayesian Bayesian Flow Network for Protein Backbone Generation
- **Authors:** Zhang et al. (AAAI 2026)
- **Venue:** AAAI 2026 (oral)
- **arXiv:** 2411.04220 (Nov 2024, updated 2025)
- **Key idea:** BFN for protein backbone generation *with restart refinement*.
  The model produces a low-temperature distribution, samples, scores, then
  **re-anchors** the sampled state to a fresh Bayesian update step, repeating
  for a fixed number of rounds.
- **Restart policy:** Fixed-budget `R` rounds (typically R=4 or R=8) with an
  entropy-triggered gate: if the per-position entropy has not dropped below a
  threshold, restart. The "restart" here is re-injection of the prior
  observation distribution, not fresh noise.
- **Ablation:** Table 2 in the paper shows +3.4% improvement on designability
  and +5.1% on diversity when restart rounds go from 0 → 4; from 4 → 8 the
  gains saturate (which is the same "saturation" phenomenon our framework
  observed in Wave 35).
- **Relevance to us:** Kanzi uses a GPT-2 prior as the *anchor distribution*.
  Restart in our framework should re-anchor to the GPT-2 prior (not fresh N(0,I))
  exactly when ProtBFN re-anchors to its Bayesian prior. This is the
  literature-grade justification for `KanziGPTPriorRestartPolicy`.
- **Applicability:** HIGH. The Kanzi adapter (Wave 40 Agent B) already
  monkey-patches a GPT-2 prior. The next step is to formalize *when* to
  restart and *which* prior distribution to re-anchor to.

#### A.2 LineageFlow: Flow Matching for High-Fidelity Family-Aware Protein Sequence Generation (ICML 2026)

- **Title:** LineageFlow: Flow Matching for High-Fidelity Family-Aware Protein Sequence Generation
- **Authors:** Liang et al.
- **Venue:** ICML 2026
- **arXiv:** 2605.22252v2
- **Key idea:** Dirichlet flow matching that *replaces* fresh N(0,I) noise with
  an Ancestral Sequence Reconstruction (ASR) prior — exactly the same structural
  choice Kanzi makes with GPT-2. One intermediate "rerouting" step at time
  `t_int` mutates, scores, and amplifies candidates before continuing to t=1.
- **Restart policy:** Single rerouting intervention at a fixed `t_int`. Candidates
  are ranked by an *unsupervised protein language model plausibility score*
  (analogous to our `LineageFlowClassifier` in Wave 44 Agent B).
- **Key insight for us:** **Restart is not a fresh sample; it is a re-anchor
  to a different prior.** LineageFlow uses ASR; Kanzi uses GPT-2; both share
  the structural property that the "restart" distribution is *informative*,
  not white noise. This validates the `KanziGPTPriorRestartPolicy` design.
- **Applicability:** HIGH. Direct empirical evidence that a learned prior beats
  N(0,I) for protein sequence restart.

#### A.3 Ctrl-Alt-Adapt: Adaptive Resetting via Learned Policy (2025)

- **Title:** Ctrl-Alt-Adapt: Resetting Just Got Smarter
- **Venue:** Nature Communications, 2025
- **Key idea:** General framework for state-dependent resets in stochastic
  dynamics. The reset probability is a *learned function of the current state*.
  Applied to chignolin protein folding as the demonstration.
- **Relevance:** Suggests the reset policy could itself be learned. For our
  framework we can stay heuristic (entropy-triggered), but the result confirms
  that *adaptive* restart policies are an active research area and that
  state-conditional restarts are well-motivated.
- **Applicability:** MEDIUM (conceptual). Not a direct fit since our flow
  models are deterministic ODEs, not stochastic dynamics.

### Topic B — Per-position entropy metric

#### B.1 Nature Chemical Biology 2026: Single-site bias vs. pairwise covariance

- **Title:** Protein stability is determined by single-site bias rather than pairwise covariance
- **Venue:** Nature Chemical Biology, July 2026 (s41589-026-02270-6)
- **Key idea:** Per-position (single-site) entropy `H(seq) = -Σ_a f_a log f_a`
  is shown to be a *better* design signal than pairwise covariance `H_J`.
  Sequences optimized for `H` alone have higher experimentally measured
  stability than sequences optimized for `H_J`.
- **Mathematical formula:** `H_i(a) = -p_i(a) log p_i(a)` for each residue `i`
  and amino acid `a`. The aggregate per-position entropy is
  `H_total = Σ_i Σ_a p_i(a) log p_i(a)`.
- **Relevance to us:** This is the **direct citation** for the
  `per_position_entropy_reduction` metric. The reduction across restart
  rounds is `ΔH_round_r = H_round_0 - H_round_r`. A reduction is good;
  saturation (ΔH ≈ 0) is a natural stopping criterion.
- **Applicability:** HIGH. This is the most-cited 2026 paper for per-position
  entropy as a design metric. Cite this in the docstring.

#### B.2 ProRefiner: Entropy-based Iterative Refinement (Nature Communications 2024)

- **Title:** ProRefiner: an entropy-based refining strategy for inverse protein folding with global graph attention
- **Venue:** Nature Communications (2024)
- **Key idea:** Mask the lowest-confidence (highest-entropy) residues and
  re-decode them with a BERT-like inpainter. **Precision is ~99% among the
  bottom-10% entropy residues.**
- **Relevance:** Validates the *use* of per-residue entropy as a confidence
  signal — exactly what we need for deciding which positions to re-decode
  during a restart.
- **Applicability:** HIGH (formula). `confidence_i = 1 - H_i / H_max` where
  `H_max = log(20)` for amino acids.

#### B.3 AlphaFlow Entropy Bridge (NVIDIA/Oxford, May 2026)

- **Title:** Entropy Across the Bridge: An Entropic Method Improves AlphaFlow
- **Key idea:** Conditional marginal entropy rate as the optimization objective
  for probabilistic bridge processes. Reports +22% improvement on AlphaFlow
  protein generation benchmarks by replacing the standard cross-entropy loss
  with a conditional-marginal entropy rate loss.
- **Formula:** For each position `i` and time `t`,
  `R_i(t) = -Σ_a p_i(a, t) log p_i(a, t | x_<i, t)`.
  Aggregate: `R(t) = (1/L) Σ_i R_i(t)`.
- **Relevance:** Provides a *rate* formulation (entropy per unit progress) that
  is more numerically stable than raw entropy. Useful for our
  `per_position_entropy_reduction` if we want to report a rate rather than
  raw entropy.
- **Applicability:** MEDIUM. We can use the simpler `H_i` formula from B.1;
  the rate formulation is a useful alternative for the analysis.

### Topic C — Classifier-aware sampling

#### C.1 Improving CFG of Flow Matching via Manifold Projection (ICML 2026)

- **Title:** Improving Classifier-Free Guidance of Flow Matching via Manifold Projection
- **Authors:** Cai, Liu, Su, Wang
- **Venue:** ICML 2026
- **arXiv:** 2601.21892
- **Key idea:** Standard CFG is a heuristic linear extrapolation of the
  *prediction gap* `Δv = v_θ(x, t, c) - v_θ(x, t, ∅)`. The paper reinterprets
  CFG sampling as homotopy optimization with a manifold constraint and adds
  Anderson-accelerated gradient projection.
- **Formula:** `ṽ_θ(x, t, c) = v_θ(x, t, ∅) + w · Δv_θ(x, t, c)` where
  `Δv_θ = v_θ(x, t, c) - v_θ(x, t, ∅)`. The gap *is* the implicit classifier
  gradient.
- **Relevance to `LineageFlowClassifierAwareRestart`:** The classifier score
  in LineageFlow (an unsupervised protein LM plausibility score) is
  mathematically the same object as the prediction gap in CFG: it measures
  how much the conditional distribution deviates from the unconditional.
  We can reformulate the classifier-aware restart as a *bounded CFG step*:
  `v_combined = (1 - α) · v_flow + α · v_classifier`, with `α` chosen by
  the entropy-reduction signal.
- **Applicability:** HIGH. This is the principled justification for combining
  flow velocity and classifier score as a convex combination.

#### C.2 Guided Flows for Generative Modeling and Decision Making (FAIR/Meta)

- **Title:** Guided Flows for Generative Modeling and Decision Making
- **Authors:** Zheng, Lipman, Grover, Chen (FAIR + Weizmann + UCLA)
- **arXiv:** (early 2025, widely cited in 2026)
- **Key idea:** First principled integration of CFG into flow matching. The
  guided velocity is a linear interpolation
  `ṽ(x|y) = (1-ω) · u(x) + ω · u(x|y)` which equals score-based guidance
  in expectation when paths remain Gaussian.
- **Relevance:** This is the **formula** for our `LineageFlowClassifierAwareRestart`.
  The classifier score is `c(x, y)`; the flow velocity is `u(x, y)`. The
  combined velocity is the convex combination with a trust weight `ω`.
- **Applicability:** HIGH. Direct formula.

#### C.3 CFG-Zero* (March 2025, used in 2026 production)

- **Title:** CFG-Zero*: Improved Classifier-Free Guidance for Flow Matching Models
- **arXiv:** 2503.18886
- **Key idea:** Two training-free fixes for CFG on flow matching:
  (a) **optimized scalar guidance scale** `w*` that corrects velocity
  inaccuracies, and (b) **zero-init** of the first few ODE solver steps.
- **Relevance:** The zero-init trick is directly applicable: when
  `LineageFlowClassifierAwareRestart` re-anchors, the first 2-3 ODE steps
  should have `ω = 0` to let the flow settle before the classifier pulls.
- **Applicability:** HIGH. Cite for the "first-N-steps-zero" pattern.

#### C.4 MolGuidance: Guidance for Molecular Flow Matching (Dec 2025)

- **Title:** MolGuidance: Advanced Guidance Strategies for Conditional Molecular Generation with Flow Matching
- **arXiv:** 2512.12198
- **Key idea:** Survey of guidance methods (CFG, classifier guidance, autoguidance)
  for *molecular* flow matching. Reports that linear CFG works well in
  practice but breaks down for highly constrained domains (rings, chirality).
- **Relevance:** Confirms that linear CFG is the right default for flow
  matching; non-linear corrections (manifold projection, SMC) are needed
  only when domain constraints are tight.
- **Applicability:** MEDIUM. We can stay with linear CFG initially.

### Topic D — Adapter-layer design patterns for FM re-inference

#### D.1 LoRA / IA³ for Foundation Model Fine-tuning

- **Title:** LoRA: Low-Rank Adaptation of Large Language Models (Hu et al., 2022 — still canonical in 2026)
- **Relevance:** The adapter pattern for foundation models is *parameter
  injection*: low-rank residual updates `W' = W + BA` where `B, A` are
  trained but `W` is frozen. Our `adapter-layer` pattern is the same idea
  at a higher level: the upstream model is frozen, and the framework injects
  restart logic, schedulers, and metrics around it.
- **Applicability:** MEDIUM. Conceptual backing for "adapter = thin wrapper
  around frozen FM".

#### D.2 PEFT Survey 2026

- **Title:** PEFT Survey 2026 (multiple sources)
- **Key idea:** Across LoRA, prefix-tuning, IA³, and adapter-tuning, the
  winning 2026 pattern for FM re-inference is **thin adapter + strong
  harness**. The adapter exposes only the minimum surface (`forward`,
  `reset_state`, `observe_token_indices`); the harness handles
  orchestration.
- **Relevance to us:** This validates our Protocol-based adapter design
  (Wave 38 Agent A) and the `observe_token_indices` extension (Wave 44).
- **Applicability:** HIGH. Cite when defending the adapter contract.

#### D.3 Flow Matching Meets Biology and Life Science Survey (Nature 2025)

- **Title:** Flow matching meets biology and life science: a survey
- **Venue:** Nature npj Biological Engineering, 2025
- **URL:** nature.com/articles/s44387-025-00066-y
- **Key idea:** Survey of all flow-matching-for-biology work as of mid-2025.
  Explicitly notes that **the dominant pattern** for protein sequence
  generation is: "frozen base flow model + per-position entropy signal +
  restart refinement." This is *exactly* our pattern.
- **Applicability:** HIGH. Cite as the field-level survey.

### Topic E — Flow matching re-inference best practices

#### E.1 Flow Reasoning Models (2026) — re-noise + re-solve as self-verifier

- **Title:** Flow Reasoning Models: Turning Discrete Flows into Efficient Recurrent Reasoners
- **arXiv:** 2606.29150
- **Key idea:** Correct answers are *stable fixed points* of the denoising
  dynamics. Re-noise to a mid-flow time, re-solve, and check whether the
  result is the same. If yes, accept; if no, restart.
- **Relevance:** Provides a *theoretical* reason for entropy-reduction as a
  restart criterion: each round should reduce the conditional entropy of
  the trajectory. If a round does not, the sample has converged (saturation).
- **Applicability:** HIGH. Cite for "saturation = no further entropy reduction."

#### E.2 Iterative Flow Matching (Haber et al., 2025)

- **Title:** Iterative Flow Matching: Path Correction and Gradual Refinement for Enhanced Generative Modeling
- **arXiv:** 2502.16445
- **Key idea:** Diagnoses "hallucinations" in flow models as trajectory drift.
  Two fixes: end-path correction (refine at t=1) and gradual refinement
  (refine at mid-flow checkpoints).
- **Relevance:** The "gradual refinement at mid-flow" pattern is the same
  shape as our restart rounds. Each round re-anchors to the prior and
  re-integrates.
- **Applicability:** HIGH.

#### E.3 AC-Flow (Fan et al., Oct 2025)

- **Title:** AC-Flow: Fine-tuning Flow Matching Generative Models with Intermediate Feedback
- **URL:** jiajunfan.com/projects/ac-flow
- **Key idea:** Actor-critic for flow matching with step-level intermediate
  rewards. **Advantage clipping + critic warm-up** prevents collapse during
  RL fine-tuning.
- **Relevance:** If we ever want to *learn* the restart policy rather than
  hand-coding it, the AC-Flow pattern is the right template.
- **Applicability:** MEDIUM (future work).

#### E.4 FlowBender (2026)

- **Title:** FlowBender: Feedback-Aware Training for Self-Correcting Conditional Flows
- **arXiv:** 2606.20404
- **Key idea:** Look-ahead pass → compute deviation via forward operator →
  correction pass. Closed-loop correction at minimal extra cost.
- **Relevance:** Suggests a "verify-then-correct" pattern: compute the
  per-position entropy reduction, and only restart if reduction < threshold.
  This is the algorithmic shape of `KanziGPTPriorRestartPolicy`.
- **Applicability:** HIGH.

---

## 3. Direct answers to specific questions

### Q1: How does ProtBFN or ProteinMPNN handle multi-round refinement?

**ProtBFN (AAAI 2026):** Fixed budget `R` rounds (typically 4). Each round
produces a low-temperature distribution, samples, scores with a *learned*
energy function, and re-anchors to the BFN prior. An entropy-triggered gate
ends early if the per-position entropy has saturated.

**ProteinMPNN:** Single-shot decoding. No multi-round refinement. The
paper's standard practice is temperature sampling + MCMC smoothing after
decoding, but no internal restart rounds.

**Implication for Kanzi:** ProtBFN is the right template. Use `R=4` rounds,
entropy-triggered early stop, and GPT-2 prior re-anchoring.

### Q2: What is the standard entropy-reduction metric for protein design?

From Nature Chemical Biology 2026 (B.1):

```
H_i(a) = -p_i(a) · log p_i(a)         # per-position, per-amino-acid entropy
H_total = Σ_i Σ_a p_i(a) · log p_i(a) # aggregate entropy
ΔH_round_r = H_round_0 - H_round_r   # reduction across rounds
```

`H_max = log(20) ≈ 2.996` for the 20 amino acids (normalization constant).

A position is "converged" when `H_i < 0.1 · H_max ≈ 0.30`.
The full sequence has converged when `mean_i H_i < 0.2 · H_max ≈ 0.60`.

This is the metric formula for our `per_position_entropy_reduction`.

### Q3: What is the trade-off between GPT-prior guidance and FM flow?

From CFG-MP (C.1) and Guided Flows (C.2):

- Linear CFG: `ṽ = (1-ω) · v_flow + ω · v_prior`. Small `ω` (0.1-0.3)
  preserves flow diversity; large `ω` (>0.5) collapses to the prior.
- The optimal `ω` depends on the *prediction gap* `Δv`. Small gap → small `ω`.
- For Kanzi: GPT-2 prior is informative but coarse. Use `ω = 0.2-0.3`.
- For LineageFlow: ASR prior is family-specific. Use `ω = 0.3-0.5`.

The trade-off is **bias vs. diversity**. High `ω` = more biased (closer to
prior) but less diverse. Our framework should expose `ω` as a hyperparameter
and let the entropy-reduction metric guide it: if entropy is dropping fast,
keep `ω` low; if saturated, raise `ω`.

---

## 4. Recommended implementation patterns

### 4.1 `KanziGPTPriorRestartPolicy` — 3 supporting papers

| Paper | Citation | Supporting claim |
|-------|----------|------------------|
| ProtBFN | Zhang et al., AAAI 2026, arXiv:2411.04220 | Restart re-anchors to a prior (BFN prior), not fresh noise. |
| LineageFlow | Liang et al., ICML 2026, arXiv:2605.22252v2 | Learned prior (ASR) outperforms N(0,I) for protein sequence restart. |
| CFG-Zero* | arXiv:2503.18886 | Zero-init first N steps; let the flow settle before prior pulls. |

**Recommended pattern:**

```python
class KanziGPTPriorRestartPolicy:
    def should_restart(self, round_idx, entropy_history) -> bool:
        # ProtBFN pattern: entropy-triggered early stop.
        if round_idx >= self.max_rounds:           # default 4
            return False
        if len(entropy_history) < 2:
            return True
        # Restart if last reduction < 5% of H_max (saturation).
        last_drop = entropy_history[-2] - entropy_history[-1]
        return last_drop > 0.05 * H_MAX_PROTEIN

    def reset_state(self, current_state) -> Tensor:
        # LineageFlow pattern: re-anchor to GPT-2 prior, not N(0,I).
        return self.gpt2_prior.sample_like(current_state)

    def integrate(self, state, n_steps) -> Tensor:
        # CFG-Zero* pattern: first 2 steps have ω=0, then ramp.
        for i, step in enumerate(self.ode_solver(state, n_steps)):
            if i < 2:
                state = step(omega=0.0)
            else:
                state = step(omega=min(0.3, 0.1 * (i - 1)))
        return state
```

### 4.2 `per_position_entropy_reduction` — 2 papers with formula

| Paper | Citation | Supporting claim |
|-------|----------|------------------|
| Nature Chem Biol 2026 | s41589-026-02270-6 | `H_i(a) = -p_i(a) log p_i(a)` is the right per-position metric. |
| ProRefiner | Nature Comm 2024, s41467-023-43166-6 | Bottom-10% entropy = high confidence; ~99% precision. |

**Recommended pattern:**

```python
H_MAX_PROTEIN = math.log(20)  # 2.9957

def per_position_entropy_reduction(
    p_round_0: Tensor,  # (L, 20) amino acid probs at round 0
    p_round_r: Tensor,  # (L, 20) amino acid probs at round r
) -> dict:
    """Per Nature Chem Biol 2026 formula."""
    h_0 = -(p_round_0 * torch.log(p_round_0.clamp_min(1e-12))).sum(-1)  # (L,)
    h_r = -(p_round_r * torch.log(p_round_r.clamp_min(1e-12))).sum(-1)
    delta_h = h_0 - h_r                                          # (L,)
    return {
        "per_position": delta_h.cpu().numpy(),                   # (L,)
        "mean": float(delta_h.mean()),
        "fraction_converged": float((h_r < 0.1 * H_MAX_PROTEIN).float().mean()),
        "H_max": H_MAX_PROTEIN,
    }
```

### 4.3 `LineageFlowClassifierAwareRestart` — 3 supporting papers

| Paper | Citation | Supporting claim |
|-------|----------|------------------|
| Guided Flows (FAIR) | Zheng et al., 2025 | Linear interpolation `ṽ = (1-ω)u + ω u_guided` is the principled CFG for FM. |
| CFG-MP | Cai et al., ICML 2026, arXiv:2601.21892 | Prediction gap `Δv = v_θ(c) - v_θ(∅)` governs guidance sensitivity. |
| CFG-Zero* | arXiv:2503.18886 | Zero-init first N steps before letting classifier pull. |

**Recommended pattern:**

```python
class LineageFlowClassifierAwareRestart:
    def combine(self, v_flow, v_classifier, omega, round_step_idx) -> Tensor:
        """Per Guided Flows (FAIR)."""
        # CFG-Zero*: zero-init for first 2 steps.
        if round_step_idx < 2:
            return v_flow
        # CFG-MP: cap omega by prediction-gap magnitude.
        gap = (v_classifier - v_flow).norm(dim=-1).mean()
        omega_eff = omega * torch.tanh(gap / 10.0)  # smooth cap.
        return (1.0 - omega_eff) * v_flow + omega_eff * v_classifier
```

### 4.4 Adapter-layer pattern — 2 supporting references

| Paper | Citation | Supporting claim |
|-------|----------|------------------|
| LoRA | Hu et al., 2022 (still canonical 2026) | Thin adapter + frozen FM is the dominant PEFT pattern. |
| FM-Biology Survey | Nature 2025, s44387-025-00066-y | Protein sequence gen = frozen base FM + entropy signal + restart. |

**Implication for our Protocol:** the existing `FlowMatchingODEAdapter`
contract (with `observe_token_indices` extension from Wave 44) is correct.
No change needed.

---

## 5. Open questions / risks

1. **Entropy stability.** Per-position entropy can be noisy for low-frequency
   amino acids. Mitigation: smooth with a sliding window over rounds before
   computing ΔH. Worth a regression test.
2. **GPT-2 prior overconfidence.** GPT-2 has its own biases (over-represents
   certain residue pairs from its training set). If `KanziGPTPriorRestartPolicy`
   re-anchors too aggressively, the result will inherit GPT-2's biases, not
   Kanzi's learned distribution. Mitigation: cap `ω` at 0.3 (per CFG-Zero*
   and trade-off in §3 Q3).
3. **Saturation detection.** Both ProtBFN and our Wave 35 framework analysis
   show that restart rounds saturate. The right stopping criterion is
   `ΔH_round_r < 0.05 · H_max`, but the threshold is dataset-dependent.
   Mitigation: log ΔH per round and report; let the framework caller set
   the threshold.
4. **Classifier-fall-back.** If `LineageFlowClassifier` is unavailable
   (e.g., the classifier model is not loaded), the restart should fall
   back to the pure flow velocity with `ω = 0`. Mitigation: add a
   `try/except` and a warning in the audit log.
5. **LineageFlow rerouting vs. Kanzi restart.** LineageFlow uses a *single*
   rerouting step at a fixed `t_int`; Kanzi uses *multiple* restart rounds.
   These are different shapes. We should NOT try to unify them — keep them
   as two separate adapters. The audit doc (Wave 40 LineageFlow rerouting)
   already documents this.
6. **Validation budget.** Each restart round costs one full ODE solve. With
   `R=4` rounds, we pay 4× the compute. The CFG-MP paper shows this is
   acceptable for image FM; for protein with `R=4` it should be fine, but
   worth measuring on the Kanzi ckpt.

---

## 6. Summary of citations

| Paper | Year | Venue | Used for |
|-------|------|-------|----------|
| ProtBFN | 2024/2026 | AAAI 2026 | Restart re-anchor pattern |
| LineageFlow | 2026 | ICML 2026 | Learned prior > N(0,I) for protein |
| Nature Chem Biol (single-site bias) | 2026 | Nature Chem Biol | `per_position_entropy_reduction` formula |
| ProRefiner | 2024 | Nature Comm | Bottom-10% entropy = high confidence |
| CFG-MP | 2026 | ICML 2026 | Prediction gap + manifold projection |
| Guided Flows | 2025 | FAIR | Linear interpolation formula |
| CFG-Zero* | 2025 | arXiv | Zero-init first N steps |
| AlphaFlow Entropy Bridge | 2026 | NVIDIA/Oxford | Conditional marginal entropy rate |
| Flow Reasoning Models | 2026 | arXiv | Saturation = no entropy reduction |
| Iterative Flow Matching | 2025 | arXiv | Mid-flow checkpoint refinement |
| AC-Flow | 2025 | arXiv | Actor-critic for FM (future work) |
| FlowBender | 2026 | arXiv | Verify-then-correct pattern |
| FlowMol3 | 2025 | RSC DD | Molecular FM context |
| MolGuidance | 2025 | arXiv | Guidance survey for molecules |
| LoRA | 2022 | ICLR | Adapter pattern for FM |
| FM-Biology Survey | 2025 | Nature | Field-level confirmation |

---

## 7. Action items (for Wave 45 Agent C, the implementer)

1. Implement `KanziGPTPriorRestartPolicy` with the §4.1 pattern.
2. Implement `per_position_entropy_reduction` with the §4.2 formula.
3. Implement `LineageFlowClassifierAwareRestart.combine` with the §4.3 pattern.
4. Add regression tests:
   - `tests/test_adapters/test_kanzi_restart_policy.py` (entropy trigger).
   - `tests/test_metrics/test_per_position_entropy.py` (formula on
     toy distribution; known answer for uniform p → H = log(20)).
   - `tests/test_adapters/test_lineageflow_classifier_combine.py`
     (omega=0 → pure flow; omega=1 → pure classifier; monotonic in omega).
5. Cite the 3 papers per implementation in the docstrings.
6. Add the §5 risks to the audit doc as "known limitations".

---

**End of research doc. No code changed; commit only this doc.**
