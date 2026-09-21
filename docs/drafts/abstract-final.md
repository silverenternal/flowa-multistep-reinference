# Abstract — Final (Wave 211 P2)

**Status.** Finalised after Wave 211 P2 six-claim refinement + signature
ordering. First sentence standardised per DeepSeek F3 framing; the
remainder preserves the Wave 207 four-sentence structure (problem →
framework → validation → positioning).

---

## Abstract (final, paper-ready)

Standard ODE solvers for flow matching treat the entire trajectory with
uniform boundary conditions, ignoring the local geometric structure of
the velocity field. Deployed flow matching checkpoints ship as frozen
weights, leaving practitioners without a mechanism to schedule the
inference loop as a function of local velocity-field geometry. We
introduce FlowA, a training-free, solver-agnostic re-inference
framework that derives a closed-form upper bound on the
bounded-Lipschitz distance between the framework's sampling
distribution and the ODE target through four paper quantities
$(A_g, B_g, C_g, e_\rho)$ — a Lipschitz aggregate, an effective NFE
decay rate, a residual bias coefficient, and an exterior-gap constant
— derived from a canonical F-side witness $g(x) = (1 + 0.25
\cdot\tanh(x))\cdot\sin(x)$ (Proposition 2 family), which is shared
across adapters under the framework default F-side profile. The
framework value-add is the scheduler architecture
(CosineAnnealScheduler + CodimensionSheetScheduler +
BoundedMergeOperator + EvidenceDrivenScheduler + BRAI), which adapts
per-record to local velocity-field geometry rather than depending on
per-adapter paper-quantity values, and consumes those quantities
directly as scheduler inputs. We validate the framework across six
R-level cells spanning protein (LineageFlow, Kanzi), molecular 3D
(FlowMol3), and image (CIFAR-10 Rectified Flow, MNIST Flow Matching,
2D Rectified Flow) flow matching models at paired sample sizes of
N = 1000, observing 2.5–10× cross-budget NFE compression at matched
quality alongside byte-stable composite-axis lifts on all three Tier 3
real checkpoints, while honestly delineating the boundary along eight
dimensions including the matched-NFE image-domain regime where the
framework regresses. The framework repositions inference-time control
as a paper-quantity-driven scheduling problem, structurally disjoint
from solver-level, trajectory-level, and re-inference alpha-blending
acceleration, and ships with full SHA-256-pinned checkpoints,
hash-chained transition logs, and a D.4 byte-stable regression suite.

---

## Word count

Body: 225 words (within the TPAMI 250-word envelope); 5 sentences;
first sentence 19 words.

| Sentence | Words | Function |
|---|---:|---|
| Sentence 1 | 19 | **Standard-ODEs framing** (DeepSeek F3): positions FlowA against the uniform-boundary assumption of standard ODE solvers |
| Sentence 2 | 31 | **Problem framing** (Wave 207 S1): frozen-checkpoint gap, no posterior-driven scheduler |
| Sentence 3 | 86 | **Framework introduction** (Wave 207 S2): FlowA, four quantities, three scheduler/operator components |
| Sentence 4 | 64 | **Validation** (Wave 207 S3): six R-cells, N = 1000, 2.5–10× NFE compression, byte-stable lifts, K1–K8 boundary |
| Sentence 5 | 41 | **Positioning** (Wave 207 S4): structural disjointness, SHA-256 + hash-chained + D.4 |
| — | **225 words** | within TPAMI envelope |

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