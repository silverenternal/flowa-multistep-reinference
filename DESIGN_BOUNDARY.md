# Adaptive Reflow Design Boundary

Owner scope: `inference.adaptive_reflow` (flowa-multistep-reinference component).
Status: **planned_not_implemented**. See `todo.json` for the canonical task list and
`CONTRACTS.md` for the data-contract skeletons that follow from this document.

This document freezes the **design boundary** and the **non-claim boundary** before any
implementation work begins, per DTB-R0. It does NOT authorise a scientific claim, a
runtime write, or an empirical assertion about model performance.

## 1. Scope of the first phase

The first phase is restricted to:

- **Immediate previous round** as the only valid source bundle. No cross-sample memory,
  no cross-target candidate retrieval, no best-so-far archive.
- **Same sample, same run, same checkpoint lineage**. The component never carries state
  across `run_id`, `sample_id`, or `trace_digest` boundaries.
- **Inference-external ODE condition** and **restart distribution** only. The component
  never edits the FlowA ODE main line, the model weights, the checkpoint format, the
  training loss, the cross-attention ownership, or the multirate clock semantics.

Any relaxation of this scope requires an explicit task in `todo.json` and a paired
acceptance test (DTB-R1 cross-references; DTB-R4 archive; DTB-G1 public engine).

## 2. Non-claim boundary

The mathematical references cited by `todo.json` (`docs/formal_architecture_lean4/Research/NoiseSelectedRectification/`,
`.../FlowOEExpertAggregation/`, `.../CommutatorSafeChannelFreezing/`,
`.../StratifiedChemicalTransport/`) are **project-internal Lean / manuscript
constructs**, not public publications as of `2026-08-24`. The component MUST NOT:

- Reference these sources as if they were published theorems or vetted libraries.
- Quote posterior, normal codimension, coarea Jacobian, or epsilon asymptotics as
  closed-form expressions of any model attention, network probability, evaluator score,
  or empirical weight.
- Claim that JMAA NoiseSelectedRectification proves anything about Flow Matching,
  molecular generation, GNINA, PoseBusters, QED/ADMET, or dynamic weight improvement.
- Use SGDR cosine warm restarts or Improved-DDPM cosine α̅ schedules as a *theoretical*
  basis for any selection claim — they are optimisation/sampling heuristics.
- Emit a field named `tail_selection_certified` with value `True`. The literal field
  exists in the schema only as `Literal[False]` so that no code path can set it.
- Translate finite-round empirical diagnostics into asymptotic / noncompact selection
  theorems.

The mathematical references are used only as **fail-closed design principles** for
local evidence / tail admissibility / complement exclusion / operation ordering. Any
empirical effect MUST be re-derived from target-disjoint, paired, round-to-round
experiments (see DTB-R7).

## 3. Hostile-case catalogue

The first phase must be robust against the following six classes of failure. Each class
maps to a fail-closed test fixture and an expected ledger/audit code (see
`CONTRACTS.md` §1 and §2 for the carrier types).

1. **Single high GNINA, geometry failure.** A real GNINA score passes the
   `external_metric_uncertainty` check but PoseBusters / sanitization fails. The
   `materialization_pass` and `geometry_pass` flags must both be present and
   propagate to `gate=False`. The corresponding test is `GeometryFailureFixture`;
   expected audit code `geometry_failure`.

2. **Low uncertainty, cross-seed instability.** A point estimate looks confident but
   `perturbation_stability_lower_bound` collapses on seed/condition perturbation. The
   `ChannelTransferDecision.gate` must be `False` regardless of `raw_score`. The test
   is `MonotonicUncertaintyFixture`; expected audit code
   `perturbation_stability_below_threshold`.

3. **Same-source multi-metric inflation.** Two metric rows derived from the same
   `bundle_id` (e.g. a duplicate GNINA pass and a derived QED score) must not inflate
   the deduplicated transfer-score mass. The test is `DuplicateEvidenceFixture`;
   expected audit code `duplicate_evidence_row_ignored`.

4. **Historical best stitched with current state.** Mixing a `source_round=k-3`
   `coordinate_channel` with a `source_round=k` `charge_channel` in one
   `RoundResultBundle` is rejected as cross-round stitching. The test is
   `CrossRoundStitchFixture`; expected audit code `cross_round_stitching`.

5. **Source revoked mid-run.** A bundle is marked `revoked=True` after a later round
   detects revocation (e.g. evaluator provenance retracted). Any subsequent
   `ChannelTransferEvidence` referencing that bundle must produce `gate=False`. The
   test is `SourceRevocationFixture`; expected audit code `source_revoked`.

6. **Proxy-only pseudo-confidence.** A `feedback_mode == "proxy_only"` value drives a
   non-zero `raw_score`. The rule MUST NOT translate a proxy-only score into a
   non-zero `beta` regardless of other factors. The test is `ProxyOnlyFixture`;
   expected audit code `proxy_only_cannot_satisfy_calibration`.

Additional hostile cases addressed by follow-on tasks (DTB-R3, DTB-R4, DTB-R5):

- Dual executable writer — same run requests executable sampler controls from both
  `adaptive_reflow` and `noise_bias`. Both ids returned in the audit; runtime write
  fails closed (DTB-S1).
- Implicit merge order — a downstream caller re-merges policy bytes by mapping
  insertion order. The `policy_hash` byte-equality check rejects this (DTB-R5).
- Per-round oscillation — every round the schedule flips because the previous-round
  score is large. The schedule capacity is frozen at run start; the score cannot
  redefine the compact set or noise schedule (DTB-NA1).

## 4. Mapping to todo.json tasks

- §1 scope freeze → `DTB-R1`, `DTB-R4`, `DTB-G1`.
- §2 non-claim boundary → `DTB-R7` (evaluation protocol must keep the same boundary),
  `DTB-L4` (cumulative noise mass remains diagnostic-only).
- §3 hostile cases 1–6 → `DTB-R2` (rule), `DTB-NC1` (envelope), `DTB-NC2` (tail), `DTB-R5`
  (trace), `DTB-S1` (writer arbitration).
- `DTB-NA1` schedules (constant / linear / cosine-no-restart / cosine-guarded-restart)
  are the **only** schedule family that any fixture may invoke; an
  `empirical_learned` slot is reserved for a future calibrated schedule.

## 5. Acceptance boundary

A run that has the following is admitted as adaptive-reflow evidence:

- `FinalRestartPolicy.policy_hash` recorded.
- `DynamicRestartTransferLedger.writer_id == "inference.adaptive_reflow"`.
- `empirical_only=True` and `finite_prefix_only=True` on every envelope / tail row.
- All `RoundResultBundle.coordinate_channel` etc. sharing the same `source_round`.
- `operation_order_version` matching the `OperationCompositionContract.version`.
- `FinalRestartPolicy.beta_by_channel` keys equal
  `DynamicRestartTransferLedger.beta_by_channel` keys.

Any deviation fails closed and is recorded as a ledger blocker; the policy MUST NOT be
applied to the next round.

## 6. Out-of-scope assertions

This component MUST NOT assert any of the following, even when local unit tests pass:

- "The noncompact selection is asymptotically tight."
- "Cosine annealing plus warm restarts guarantees convergence of the restart memory."
- "A proxy score suffices as a claim-grade evidence source."
- "Dynamic reflow improves GNINA / QED / ADMET in any unseen target-disjoint split."
- "The phase memory and operation order remove phase bias in any third-party model."

Each of these is a research hypothesis to be evaluated under DTB-R7 / DTB-R8 with
fixed-denominator paired evidence; until then it is **not** a property of the
component.