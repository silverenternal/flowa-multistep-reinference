# Abstract — Final (Wave 232 P2)

**Status.** Finalised after Wave 232 P2 TPAMI-envelope trim (250 words, 9
sentences). Body trimmed from 465 → 250 words via Wave 232 P2; all
key claims preserved (training-free + solver-agnostic re-inference
framework; 4 paper quantities; canonical F-side witness; 5-component
scheduler architecture; 12-adapter L_emp range; A_g vs L_emp
distinction; 6 R-cell validation; per-record 4-arm sweep; framework-WINS
positioning; SHA-256 + hash-chained + D.4).

Original Wave 211 P2 status: six-claim refinement + signature ordering.
First sentence standardised per DeepSeek F3 framing; the remainder
preserves the Wave 207 four-sentence structure (problem → framework →
validation → positioning).

---

## Abstract (final, paper-ready)

Standard ODE solvers treat the trajectory with uniform boundary conditions, ignoring local velocity-field geometry. Deployed checkpoints ship as frozen weights, leaving no mechanism to schedule the inference loop to local velocity-field geometry. We introduce FlowA, a training-free, solver-agnostic re-inference framework deriving a closed-form upper bound on the bounded-Lipschitz distance between the framework's sampling distribution and the ODE target through four paper quantities (A_g, B_g, C_g, e_ρ) — Lipschitz aggregate, NFE decay rate, residual bias coefficient, exterior-gap constant — derived from a canonical F-side witness g(x)=(1+0.25·tanh(x))·sin(x). The scheduler architecture (CosineAnnealScheduler, CodimensionSheetScheduler, BoundedMergeOperator, EvidenceDrivenScheduler, BRAI) consumes those quantities directly as inputs and adapts per-record to local velocity-field geometry. Empirical Lipschitz constants L_emp for the 12 adapters span L_emp^max ∈ [0.68, 35.63] — a 52× range — confirming varying per-adapter geometry while preserving the g-independent rate-bound e^{A_g}≈2.35. A_g is the F-side family Lipschitz constant of the canonical witness, distinct from the per-adapter Jacobian L_emp. Validating across six R-level cells spanning protein (LineageFlow, Kanzi), molecular 3D (FlowMol3), and image (CIFAR-10 Rectified Flow, MNIST Flow Matching, 2D Rectified Flow) at N=1000, observing 2.5–10× NFE compression at matched quality with byte-stable composite-axis lifts on three Tier-3 checkpoints, delineating the matched-NFE image-domain boundary where the framework regresses. Per-record 4-arm sweep at N=1000 shows 14/16 cells granularity-bounded (|d_z|<0.07), with 3 Bonferroni-significant at |d_z|∈[0.145,2.103] (vanilla scPerplexity NFE50/100, abcache scPerplexity NFE50 — framework-WINS). FlowA repositions inference-time control as a paper-quantity-driven scheduling problem, structurally disjoint from solver-level, trajectory-level, re-inference alpha-blending acceleration, with SHA-256-pinned checkpoints, hash-chained transition logs, D.4 byte-stable regression suite.

---

## Word count

Body: 250 words (at the TPAMI 250-word envelope); 9 sentences;
first sentence 14 words.

| Sentence | Words | Function |
|---|---:|---|
| Sentence 1 | 14 | **Standard-ODEs framing** (DeepSeek F3): positions FlowA against the uniform-boundary assumption of standard ODE solvers |
| Sentence 2 | 18 | **Problem framing** (Wave 207 S1): frozen-checkpoint gap, no posterior-driven scheduler |
| Sentence 3 | 53 | **Framework introduction** (Wave 207 S2): FlowA, four quantities, canonical F-side witness |
| Sentence 4 | 21 | **Scheduler architecture**: five-component scheduler/operator suite |
| Sentence 5 | 28 | **Empirical anchors** (Wave 229 P1–P3): L_emp range across 12 adapters, 52× range, g-independent rate-bound |
| Sentence 6 | 17 | **A_g vs L_emp** (Wave 231 P4): F-side family constant distinct from per-adapter Jacobian |
| Sentence 7 | 49 | **Validation** (Wave 207 S3): six R-cells, N = 1000, 2.5–10× NFE compression, byte-stable lifts, matched-NFE image-domain boundary |
| Sentence 8 | 23 | **Granularity signature** (Wave 229 P1): 14/16 granularity-bounded, 3 Bonferroni-significant at \|d_z\| ∈ [0.145, 2.103] (framework-WINS) |
| Sentence 9 | 27 | **Positioning** (Wave 207 S4): structural disjointness, SHA-256 + hash-chained + D.4 |
| — | **250 words** | at TPAMI envelope — Wave 232 P2 trim |

## Why the new first sentence

The DeepSeek F3 review surfaced that the original Wave 207 abstract
opened with the **consequence** ("Deployed flow matching checkpoints
ship as frozen weights...") rather than the **standard-assumption that
FlowA rejects**. The new first sentence ("Standard ODE solvers for
flow matching treat the entire trajectory with uniform boundary
conditions, ignoring the local geometric structure of the velocity
field.") explicitly names the standard assumption that FlowA replaces,
making the contribution legible in one sentence. The original Wave 207
sentence 1 is preserved as the new sentence 2 (problem framing), so no
information is lost.

## Provenance

- **Wave 207 P6** four-sentence structure: `docs/drafts/paper-flattened-draft.md` §Abstract (preserved verbatim, sentence 2–5).
- **Wave 211 P2** new first sentence (DeepSeek F3 framing).
- **Cross-check:** the four paper quantities $(A_g, B_g, C_g, e_\rho)$ are the same four quantities as the four-lemma path in Theorem 1
  (`docs/theory/theorem-1-self-contained.md`); the three scheduler/operator
  components (CodimensionSheetScheduler, EvidenceDrivenScheduler,
  BoundedMergeOperator) are the same three components in the five-arm
  ablation (paper §3.4 A2/A3/A4); the six R-level cells are the same six
  cells in the paper §3.1 Table 3.1; the 2.5–10× NFE compression figure
  matches the Wave 211 P1 efficiency narrative.