# Wave 194 P3 — Section rewrite in MrFlow / EAAI style

**Date:** 2026-09-19
**Branch:** main
**Scope:** Rewrite of §1 Introduction, §2 Related Work, §3 Method, §4
Experiments in `docs/paper-draft.md` to the MrFlow (Zheng et al. 2026,
arXiv:2607.01642) / EAAI 5-section style. Results-oriented, concise,
with explicit "we propose / we achieve / we demonstrate" framing. Drop
per-Wave audit-trail language from the four main-text sections
(audit-trail citations are now compact, anchored to commit SHAs or
`verification_outputs/` paths only, never `(Wave X P Y)` markers).

---

## Source style guide

Reference text: `docs/refs/w194-reference-template-plan.md` (MrFlow
section structure), `/tmp/w194/mrflow.txt` (full 32-page paper text),
and `/tmp/w194/mrflow-abstract.txt` (279-word abstract).

MrFlow opening sentence pattern:

> "Hardware-agnostic strategies for accelerating text-to-image
> diffusion ... can reduce inference time without custom kernels or
> system-level optimization. Among them, multi-resolution generation
> strategies have recently received broad attention, attaining more
> than 5× speedup without any training."

MrFlow result-framing pattern:

> "Quantitative and qualitative results on FLUX.1-dev and Qwen-Image
> show that MrFlow exploits the quadratic token reduction and reduced
> step requirement of low-resolution sampling to achieve 10× end-to-
> end acceleration while keeping OneIG within a 1% gap relative to that
> before acceleration ..."

MrFlow contribution-list pattern:

> "A multi-resolution acceleration pipeline ... [bullet 1]
> Principle innovation and analysis of each stage ... [bullet 2]
> Combining operational flexibility and simplicity, high speedup,
> good generation quality, and strong generalization. ... [bullet 3]"

---

## Tasks executed

### Task 1 — §1 Introduction rewrite — DONE

**Goal.** Replace the §1.1 problem / §1.2 limitations / §1.3
contribution / §1.4 contributions-bullets structure with a MrFlow-
style 5-paragraph opener: (1) what we present, (2-3) the problem, (4-
5) limitations of existing approaches, (6-8) our approach, (9-10)
contributions.

**Edit applied.** `docs/paper-draft.md` §1 entirely rewritten with the
following 5-paragraph structure:

- **Paragraph 1** — "We present FlowA, a training-free, solver-
  agnostic re-inference framework that improves frozen flow-matching
  checkpoints via paper-quantity-driven multi-round scheduling ..."
  (opener + value proposition + headline 2.5–10× NFE speedup).
- **Paragraph 2** — "Today's released checkpoints ... ship as frozen
  θ: practitioners cannot re-train, distill, or otherwise modify the
  inference surface. A frozen FM checkpoint has a latent distribution
  gap ..." (problem statement: what makes the inference problem hard).
- **Paragraph 3** — "Solver-level acceleration (DPM-Solver++, EDM,
  UniPC) reduces NFE per sample but operates on a fixed marginal;
  trajectory-level acceleration (Consistency Models, iCT, CTM, LCM-
  LoRA) straightens the path at training time but requires retraining;
  re-inference alpha-blending consumes outcome-conditioned feedback
  without a theory-grounded schedule." (three families of prior
  work and their limitations, condensed).
- **Paragraph 4** — "We present FlowA, a re-inference framework that
  closes the gap. A frozen θ plugs in via an eight-method
  FlowMatchingODEAdapter Protocol. FlowA wires four pluggable
  feedback loops, codified as 17 typed state machines with 333 typed
  transitions, plus three new algorithms that consume the framework's
  four paper quantities $(A_g, B_g, C_g, e_\rho)$ — the FlowA re-
  parameterisation of the BGV12 / V03 constants — as executable
  formulas." (our approach, formal).
- **Paragraph 5** — contributions bullet list, results-oriented
  ("we demonstrate 6 Bonferroni-significant framework_improves on
  paper-metric axes ... 3 byte-stable composite-axis improvements
  ... 4-arm head-to-head wins ... 2.5–10× NFE speedup").

**Result.** §1 now reads as a polished paper section, not as an audit
log. Every per-Wave marker dropped.

### Task 2 — §2 Related Work rewrite — DONE

**Goal.** Each of §2.1–§2.4 condensed to 1-2 paragraphs; ending
positioning line is "FlowA is training-free + solver-agnostic +
theory-grounded, three axes the existing literature does not jointly
occupy."

**Edit applied.** `docs/paper-draft.md` §2 rewritten. Each family
sits in a single 1-2 paragraph section:

- **§2.1 Flow matching foundations** — 1 paragraph covering
  Lipman 2023 + Liu 2022 + MeanFlow 2024 + stochastic FM 2024. The
  flow-matching prior is defined; FlowA plugs in by holding θ fixed
  and varying the schedule across rounds.
- **§2.2 Solver-level acceleration** — 1 paragraph on DPM-Solver++
  / EDM / UniPC / RK45. The structural pattern: NFE-per-sample
  reduction on a fixed marginal; no outcome-conditioned feedback
  across samples.
- **§2.3 Trajectory-level acceleration** — 1 paragraph on Consistency
  Models / iCT / CTM / LCM-LoRA / Reflow. The structural pattern:
  retraining θ (or a LoRA); only generalises within the training
  distribution's manifold.
- **§2.4 Re-inference alpha-blending** — 1 paragraph on Sabour
  alpha-blending + restart-blend + Fast-DLLM + AB-Cache + LeDiFlow.
  The structural pattern: outcome-conditioned feedback without a
  theory-grounded schedule.
- **§2.5 Position of FlowA** — 1 paragraph positioning FlowA as
  training-free + solver-agnostic + theory-grounded — three axes the
  existing literature does not jointly occupy — followed by the
  FlowA-position table.

**Result.** §2 closes with the three-axes positioning line in the
required form.

### Task 3 — §3 Method rewrite — DONE

**Goal.** §3.1 opens with a 1-sentence summary; §3.2-§3.6 each open
with a 1-sentence summary; "we propose X / Y is computed as Z" pattern
throughout; figures and tables referenced inline.

**Edit applied.** `docs/paper-draft.md` §3 rewritten:

- **§3.1 FlowA architecture overview** — 1-sentence opener:
  "FlowA is composed of four layers ..."; the four layers enumerated.
  References Figure 1.
- **§3.2 Typed Protocol surface** — 1-sentence opener: "A model
  joins FlowA by satisfying FlowMatchingODEAdapter, an eight-method
  structural Protocol." Code block follows; Table 1 lists the four
  Protocols and the eight shipped adapters.
- **§3.3 Hexagonal port set + scheduler families** — 1-sentence
  opener: "FlowA's hexagon exposes eight named ports that an adapter
  or operator implementation may swap without code edits." Table 2
  enumerates the ports and the four scheduler families.
- **§3.4 Three new algorithms** — 1-sentence opener: "FlowA
  introduces three algorithms that consume the four paper quantities
  $(A_g, B_g, C_g, e_\rho)$ as algorithm inputs." Table 3 enumerates
  algorithm / input / output / grounding. Each algorithm follows the
  "we propose X; Y is computed as Z" pattern.
- **§3.5 17 state machines + 333 transitions** — 1-sentence opener:
  "Every scheduler class plus the ReInferenceRunner orchestrator
  carries an observation-only StateMachine." Mermaid diagram follows.
  Figure 2 referenced.
- **§3.6 Theoretical grounding** — 1-sentence opener: "FlowA's
  BL-convergence claim is a specialised application of two peer-
  reviewed results: BGV12 (2012, Thm 1.1) and V03 (Thm 7.3)." Tables
  enumerate the four quantities.

**Result.** §3 follows the MrFlow "Formulation → Equation(s) →
Analysis → Cross-reference" pattern with one-paragraph op + detail
flow.

### Task 4 — §4 Experiments rewrite — DONE

**Goal.** §4.1 opens with the adapter matrix (Table 1 in the task
spec — repurposed to Table 4 in the paper for numbering consistency
with §3) + setup; §4.2 uses the R-level table (R1-R6); §4.3 ablations
in 3-4 sub-tables; §4.4 head-to-head with 16 per-cell deltas; §4.5
honest negatives in 1 paragraph.

**Edit applied.** `docs/paper-draft.md` §4 rewritten:

- **§4.1 Setup** — 1-paragraph opener: "The claim under test is
  deliberately narrow: when a published flow-matching model is run
  through FlowA's multi-round re-inference loop, sample-quality
  metrics change measurably relative to the same model's single-pass
  baseline." Table 4 (5 adapters × 3 domains experimental matrix).
  Baselines enumerated (vanilla + Fast-DLLM + AB-Cache + LeDiFlow).
  Implementation paragraph.
- **§4.2 Main results** — Table 5 (R1-R6 headline evidence, 6
  Bonferroni-significant `framework_improves` + 3 byte-stable
  composite-axis improvements). Tier 3 condensed sweep paragraph.
- **§4.3 Ablation study** — Table 6 (5×3 ablation matrix). Three
  reading bullets. Three ablation sub-tables: (a) n_rounds + NFE
  curve, (b) hyperparameter sensitivity, (c) Theorem 1 load-bearing.
- **§4.4 Head-to-head comparison** — Table 7 (16 per-cell pLDDT +
  scPerplexity deltas on R6).
- **§4.5 Honest negatives** — 1 paragraph listing the four
  disclosures (Kanzi TIES within FSQ noise; CIFAR-10 RF v4 matched-
  NFE=50 +24-31% regress; 2D TIES post-cd70821; FreqFlow synthetic-
  only deferred).

**Result.** §4 follows the MrFlow "Main Results → Ablation Study"
structure with explicit tables for each sub-result type.

### Task 5 — Drop (Wave X P Y) markers — DONE

**Goal.** Drop all "(Wave X P Y)" audit markers from §1-§4; citations
collapse to commit SHAs or `verification_outputs/` paths.

**Edit applied.** Manual replace of (Wave X P Y) → file/commit/path
form across §1, §2, §3, §4. Per-Wave markers that remained in §5
Conclusion and §10 Limitations were preserved (they're outside the
scope of this task).

**Counter.** Before: 38 `(Wave ...)` markers in §1-§4. After: 0
`(Wave X P Y)` markers in §1-§4. (The §5 Conclusion / §10
Limitations sections retain their markers because the §5.2 top-5
limitations explicitly enumerate the Wave provenance as part of the
limitations enumeration; this is outside the §1-§4 scope per the
task spec.)

---

## Final state

```json
{
  "introduction_rewritten": true,
  "related_work_rewritten": true,
  "method_rewritten": true,
  "experiments_rewritten": true,
  "wave_markers_remaining_main": 0,
  "commit_sha": "69a9e0c3adeeb517241243d2fdd6450090dbbcea"
}
```
