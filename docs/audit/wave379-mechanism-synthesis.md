# Wave 379 — FlowA mechanism synthesis for the paper narrative

**Date:** 2026-09-27  
**Source commit:** `3b062f6` plus the recorded evidence artifacts below  
**Scope:** Identify the mechanism chain that should organize the TNNLS paper, using existing code and verified results rather than adding a new experiment.  
**No GPU work:** This is a read-only synthesis of recorded runs and adapter code.

## 1. The mechanism chain

FlowA's contribution is a three-stage inference transformation:

1. **Glue path — restart state becomes a model-native state.** The adapter receives a typed state bundle, applies a bounded restart policy, and routes the resulting state back through the frozen velocity field. In the generic framework path, `_solve_framework` carries the endpoint through `export_endpoint` and then calls `apply_restart_distribution(endpoint, policy)` (`tools/eval/framework.py:753-822`). Kanzi and LineageFlow implement the blend in their native latent/categorical state spaces (`adaptive_reflow/adapters/kanzi.py:2008+`; `adaptive_reflow/adapters/lineageflow.py:1684+`). This is the mechanism that converts one-shot inference into an intervention on the checkpoint's state trajectory.

2. **Geometry path — the intervention is expressed in the checkpoint's native coordinates.** The Kanzi `framework_inv_proj` driver samples a latent, applies the trained inverse projection and DAE decoder, converts the result to backbone coordinates, and then invokes the adapter ODE (`tools/_kanzi_sweep_runner.py:402-480`). The bridge is not post-processing: it is the representation alignment that makes the restart state meaningful to the frozen model. The paired R2 artifact reports RMSD 0.9020 Å → 0.8798 Å at `N=1000` (`paper-data/R2_kanzi_rmsd/R2_SOURCE.md`).

3. **Allocation path — correction capacity follows residual opportunity.** `ScheduleDerivedPolicyDriver` maps scheduler `n_cap` to restart noise and memory (`adaptive_reflow/algorithm/policy_driver.py:293-365`). `TierAwareCodimensionSheetScheduler` multiplies `n_cap` for the easy tier while preserving the hard/medium envelope (`adaptive_reflow/algorithm/scheduler/tier_aware.py:453-513`). The paired pLDDT effects are strongly difficulty-dependent on both Kanzi k6 and LineageFlow: hard tiers improve while easy tiers can regress. This gives a principled reason to allocate compute selectively rather than uniformly.

The ledger and typed contracts bind the three paths together. They record the state representation, policy, schedule and endpoint at every transition, so a gain can be attributed to a representation bridge, a restart intervention, a capacity allocation, or their interaction.

## 2. Existing mechanism-isolation evidence

### 2.1 Restart glue versus multi-round iteration

Wave 184 isolates the glue path from the iteration path with `n_rounds ∈ {1,2,3,5,7}` at fixed NFE=100 (`docs/CLAIMS.md` CLM-049; `verification_outputs/wave184-p4-ablation-table.csv`). On synthetic LineageFlow, all framework round counts produce identical aggregate metrics while the framework improves pLDDT by +0.81 and scPerplexity by −4.00. The gain is therefore attributable to the restart glue path; repeated averaging contributes no measurable change in that adapter. On Kanzi, paper-quantity profiles are active: `n_rounds=1` already isolates the scheduler intervention, while later rounds add a non-monotonic modulation. This is the strongest available causal decomposition in the project and should be a central figure or table in the paper.

### 2.2 Scheduler strength and budget regime

The Kanzi ladder separates scheduler intensity from iteration. At NFE=100, the `n_rounds=1` regression is present before multi-round averaging begins; the paper-quantity scheduler is therefore the primary control on that cell. At larger budgets, the framework's cross-model headline uses the scheduler in a regime where the checkpoint has room for the intervention. The paper should present this as a **budget-matching law**: the same controller can be beneficial or overactive depending on the ratio between allocated capacity and the checkpoint's remaining correction demand.

### 2.3 Difficulty redistribution

The R6 hard/medium/easy pattern is replicated across Kanzi and LineageFlow. The aggregate paired mean decomposes as

\[
\bar{\delta}=\sum_t (n_t/N)\bar{\delta}_t,
\]

so an overall near-zero effect can conceal a large hard-tier gain and an easy-tier loss. The tier-aware controller is the algorithmic response: retain capacity for hard records and reduce redundant intervention on easy records. The existing `d_z=+0.2235` overall tier-aware number is a counterfactual transformation of frozen paired differences; it should be shown as a design validation, with the live scheduler run framed as the direct next experiment.

## 3. Recommended paper structure

The paper should be organized around the following causal figure and sections:

1. **Figure 1 — FlowA mechanism:** native-state bridge → restart blend → frozen ODE → endpoint observation → scheduler feedback.
2. **Section 3 — Three mechanisms:** glue, geometry, allocation, each tied to one interface and one measurable quantity.
3. **Section 6 — Mechanism isolation:** Wave 184 round-count decomposition and the Kanzi NFE ladder.
4. **Section 7 — Cross-domain evidence:** R2 geometry gain, R6 difficulty redistribution, R1/R3 glue-path gains, then image regime boundaries.
5. **Section 8 — Transfer principle:** the typed contract keeps the mechanism invariant while adapters change the state geometry.

This structure gives the paper a research claim stronger than “FlowA improves several metrics”: **FlowA is a training-free state-intervention layer whose benefit comes from aligning the intervention with checkpoint geometry and allocating its strength to the remaining correction demand.**

## 4. Eight-page assessment

Eight pages are acceptable for an initial TNNLS submission, but the current eight-page version spends too much space on status inventory and reproducibility detail relative to the causal story. A 10–12 page version would better fit an ambitious Q1 submission if the added pages are spent on the mechanism figure, Wave 184 isolation table, scheduler/budget diagram, and cross-adapter difficulty plot. More pages without those causal objects would not improve the paper.
