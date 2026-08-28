# Project Claims — single source of truth

Status: governance document. This file is the canonical ledger of every
substantive claim the framework makes. All cross-references between
`docs/INSIGHTS.md`, `docs/ABLATION.md`, `docs/adr/*.md`, and the source
tree resolve through the CLM IDs defined here.

How it works:

* Each claim gets a stable ID (`CLM-NNN`).
* `Asserted by` records the file/line that grounds the claim in code.
* `Disputed by` records any file/line that contradicts it; the verifier
  in `tools/check_claims_consistency.py` automatically promotes a claim
  to `PROVISIONAL` when a `Disputed by` reference is present.
* `Status` is one of `ACTIVE`, `PROVISIONAL`, `DEPRECATED`:
  - `ACTIVE` — currently the canonical claim.
  - `PROVISIONAL` — has a `Disputed by` reference; needs human review.
  - `DEPRECATED` — superseded; cited only for historical context.
* The verifier (`tools/check_claims_consistency.py`) reads this file,
  walks every `Asserted by` reference, and exits non-zero if drift is
  detected.

## CLM-001: Sheet tube evidence scales as `Theta(eps^{+1})` {#CLM-001}

- Status: ACTIVE
- Date: 2026-08-28
- Source: paper Theorem 1 / Lemma 2 (Li 2024,
  `NoiseSelectedRectification_EN.md` line 101-103)
- Asserted by: docs/adr/0013-posterior-selection-drives-algorithm.md:115-117
- Disputed by: —
- Statement: Paper Lemma 2 proves the sheet tube's unnormalised
  contribution to the small-noise posterior is `Theta(eps^{+1})`,
  derived from the substitution `y = eps u` which contributes one
  Jacobian factor `eps`.
- Evidence: paper Lemma 2 (line 101-103); framework contract
  `adaptive_reflow/contracts/paper_quantities.py:64`
  (`sheet_evidence_A` returns `A_g`, the positive limit derived from
  Lemma 2's sheet tube).

## CLM-002: Root cell evidence scales as `O(eps^{+2})` per cell {#CLM-002}

- Status: ACTIVE
- Date: 2026-08-28
- Source: paper Theorem 1 / Lemma 3 (Li 2024, line 107)
- Asserted by: docs/adr/0013-posterior-selection-drives-algorithm.md:119-120
- Disputed by: —
- Statement: Paper Lemma 3 proves each isolated root cell contributes at
  most `O(eps^{+2})` to the unnormalised posterior, because codimension-2
  cells carry two Jacobian factors.
- Evidence: paper Lemma 3 (line 107); framework contract
  `adaptive_reflow/contracts/paper_quantities.py:226`
  (`per_cell_coefficient_C` returns `C_g = e^{rho^2/2} / a`,
  the per-cell coefficient Lemma 3 proves is literal and explicit).

## CLM-003: Framework `selection_ratio` metric is invariant to scheduler {#CLM-003}

- Status: ACTIVE
- Date: 2026-08-28
- Source: ADR-0013 §"Selection metric status" / `docs/review/B5-VERIFICATION.md`
- Asserted by: docs/INSIGHTS.md:60,
  docs/ABLATION.md:130-133
- Disputed by: —
- Statement: The shipped `selection_ratio = sheet_evidence /
  (sheet_evidence + cell_evidence)` metric emitted by
  `EvidenceScaleGapMetric` is schedule-independent by construction; both
  `CosineAnnealScheduler` and `CodimensionSheetScheduler` report
  bit-identical per-round curves on each target because the evaluator
  scores the adapter's own posterior geometry at a fixed noise scale.
- Evidence: `tools/run_metric_per_family.py` produces identical
  per-round values across all five scheduler families on both targets
  (`two_moons`, `eight_gaussians`); pinned by
  `tests/test_eval/test_posterior_selection_evaluator.py`.

## CLM-004: Framework `selection_ratio` plateaus, does NOT converge to 1 {#CLM-004}

- Status: ACTIVE
- Date: 2026-08-28
- Source: ADR-0013 §"Selection metric status" (post-review, 2026-08-28)
- Asserted by: docs/INSIGHTS.md:60-62,
  docs/ABLATION.md:183-189,
  docs/adr/0013-posterior-selection-drives-algorithm.md:651-706
- Disputed by: —
- Statement: The shipped `selection_ratio` is a fixed-noise replay
  estimator; it plateaus at the value dictated by the adapter's
  training noise rather than converging to 1 as rounds progress.
  Convergence to 1 would require an endpoint-conditioned metric
  operating in the `eps -> 0` limit, which is the open follow-up.
- Evidence: `docs/ABLATION.md` §"What the data shows WITHOUT claiming
  paper backing" reports `two_moons` plateau `~0.81`,
  `eight_gaussians` plateau `~0.49` across 20 rounds.

## CLM-005: Cosine annealing is the canonical implementation of paper Lemma 2 {#CLM-005}

- Status: ACTIVE
- Date: 2026-08-28
- Source: ADR-0013 §"Sheet tube scaling -> CosineAnnealScheduler"
- Asserted by: docs/adr/0013-posterior-selection-drives-algorithm.md:142-173
- Disputed by: —
- Statement: `CosineAnnealScheduler`'s monotonic decrease in fresh-noise
  capacity is the direction-aligned surrogate of the paper's
  `eps -> 0` limit; it is the canonical implementation of paper
  Lemma 2's sheet tube scaling *at the direction level*.
- Evidence:
  `adaptive_reflow/algorithm/scheduler.py:182`
  (`CosineAnnealScheduler.sample(...)` produces
  `n_cap(r) = n_min + 0.5 * (n_max - n_min) * (1 - cos(pi * r / (L - 1)))`).

## CLM-006: CodimensionSheetScheduler implements paper Lemma 2 + Lemma 3 as closed form {#CLM-006}

- Status: ACTIVE
- Date: 2026-08-28
- Source: ADR-0013 §"Framework mapping" / §"paper_quantities as algorithm input"
- Asserted by: docs/adr/0013-posterior-selection-drives-algorithm.md:556-577,
  docs/INSIGHTS.md:13-15
- Disputed by: —
- Statement: `CodimensionSheetScheduler` instantiates paper Lemma 2 +
  Lemma 3 as a first-class `SchedulerProtocol` implementation,
  emitting the sheet-vs-cell evidence balance via
  `_paper_evidence_balance` (with positive `eps` powers, not the
  historical inversion).
- Evidence: `adaptive_reflow/algorithm/scheduler.py:1671`
  (`CodimensionSheetScheduler` class),
  `adaptive_reflow/algorithm/scheduler.py:1548`
  (`_paper_evidence_balance` helper).

## CLM-007: Physical complement is exponentially suppressed {#CLM-007}

- Status: ACTIVE
- Date: 2026-08-28
- Source: paper Theorem 1 / Lemma 4 (Li 2024, line 111-112)
- Asserted by: docs/adr/0013-posterior-selection-drives-algorithm.md:121-124,
  docs/INSIGHTS.md:40
- Disputed by: —
- Statement: Paper Lemma 4 proves the "physical" complement
  (`{ y != 0 }`) is exponentially suppressed at rate
  `exp(-e_rho / (2 eps^2)) = o(eps)`, with
  `e_rho = min{rho^4, (1 - rho)^2 eta^2}`.
- Evidence: `adaptive_reflow/contracts/paper_quantities.py:271`
  (`exterior_gap_e_rho` returns `e_rho`, the literal Lemma 5 constant).

## CLM-008: Framework's heuristic `selection_ratio` is NOT a paper quantity {#CLM-008}

- Status: ACTIVE
- Date: 2026-08-28
- Source: ADR-0013 §"Framework-internal heuristic: the `selection_ratio` metric"
- Asserted by: docs/adr/0013-posterior-selection-drives-algorithm.md:289-321,
  docs/INSIGHTS.md:21-27
- Disputed by: —
- Statement: The `selection_ratio` emitted by `EvidenceScaleGapMetric`
  (formerly `PosteriorSelectionEvaluator`) is a framework-internal
  heuristic for monitoring the sheet-vs-cell evidence *scale gap*; it
  is NOT a paper quantity, and convergence to 1 is NOT a paper claim.
- Evidence:
  `adaptive_reflow/eval/posterior_selection_evaluator.py:396`
  (`EvidenceScaleGapMetric` class); pinned by
  `tests/test_eval/test_posterior_selection_evaluator.py::test_metric_classification_does_not_claim_paper_theorem`.

## CLM-009: `eight_gaussians` plateau is lower than `two_moons` {#CLM-009}

- Status: ACTIVE
- Date: 2026-08-28
- Source: ablation data, `tools/run_metric_per_family.py`
- Asserted by: docs/ABLATION.md:128, docs/INSIGHTS.md:58
- Disputed by: —
- Statement: The framework's heuristic `selection_ratio` is
  target-sensitive in the direction paper Lemma 3 predicts: more
  competing cell roots means a lower plateau value. Empirically
  `eight_gaussians` (7 cells) plateaus materially below `two_moons`
  (1 cell).
- Evidence: `tests/test_eval/test_posterior_selection_evaluator.py::test_evaluator_8_gaussians_ratio_lower_than_2_moons`
  pins the ordering; `docs/ABLATION.md` §"What the data shows WITHOUT
  claiming paper backing" reports the per-family mean values
  (`~0.49` for `eight_gaussians`, `~0.81` for `two_moons`).

## CLM-010: Bounded noise floor prevents escape from the fibre {#CLM-010}

- Status: ACTIVE
- Date: 2026-08-28
- Source: ADR-0013 §"Physical complement suppression -> bounded noise floor"
- Asserted by: docs/adr/0013-posterior-selection-drives-algorithm.md:248-265
- Disputed by: —
- Statement: `SchedulerProtocol.config.n_min > 0` and the
  `BoundedMergeOperator` cap (`MERGE_FLOOR_FALLBACK`,
  `MERGE_DEGENERATE_INTERVAL`) implement paper Lemma 4's bounded-noise
  guarantee: a non-zero noise floor is the structural guarantee that
  the posterior stays on the fibre.
- Evidence: `adaptive_reflow/algorithm/merge_operator.py` /
  `adaptive_reflow/algorithm/scheduler.py:182`
  (`CosineAnnealScheduler` carries the `n_min` field).

## CLM-011: Four paper quantities are first-class algorithm inputs {#CLM-011}

- Status: ACTIVE
- Date: 2026-08-28
- Source: ADR-0013 §"paper_quantities as algorithm input"
- Asserted by: docs/adr/0013-posterior-selection-drives-algorithm.md:545-624,
  docs/INSIGHTS.md:79
- Disputed by: —
- Statement: The four paper quantities `A_g`, `B_g`, `C_g`, `e_rho`
  (exposed via `adaptive_reflow.contracts.paper_quantities`) are
  consumed end-to-end as first-class algorithm-layer inputs by
  `CodimensionSheetScheduler`, `AdaptivePolicyDriver`, and
  `ReInferenceRunner` whenever the corresponding opt-in configuration
  is supplied.
- Evidence: `adaptive_reflow/contracts/paper_quantities.py:39-44`
  (`__all__`); `adaptive_reflow/algorithm/scheduler.py:1844-1854`
  (`CodimensionSheetScheduler` constructs the four constants);
  `adaptive_reflow/algorithm/policy_driver.py:485-490`
  (`AdaptivePolicyDriver` accepts `per_cell_coefficient_C`);
  `adaptive_reflow/algorithm/runner.py:155`
  (`ReInferenceConfig.paper_quantities_provider`).

## CLM-012: Paper Theorem 1 proves bounded-Lipschitz convergence {#CLM-012}

- Status: ACTIVE
- Date: 2026-08-28
- Source: paper Theorem 1 (Li 2024, line 88-91)
- Asserted by: docs/adr/0013-posterior-selection-drives-algorithm.md:794-798,
  docs/INSIGHTS.md:110
- Disputed by: —
- Statement: Paper Theorem 1 proves `mu_{g,eps} --BL--> nu_g` as
  `eps -> 0`; the limiting measure is supported on the codimension-1
  sheet with local density
  `q_g(x) / Q_g = exp(-x^2 / 2) / (sqrt(1 + g(x)^2) * Q_g)`.
- Evidence: paper Theorem 1 (line 88-91);
  `adaptive_reflow/contracts/paper_quantities.py:1-31`
  (module docstring quotes the theorem statement).

## CLM-013: Paper Corollary 1 yields `Z_{g,eps} >= C_1 * eps` {#CLM-013}

- Status: ACTIVE
- Date: 2026-08-28
- Source: paper Corollary 1 (Li 2024, line 165)
- Asserted by: docs/adr/0013-posterior-selection-drives-algorithm.md:805-809,
  docs/INSIGHTS.md:112
- Disputed by: —
- Statement: Paper Corollary 1 deduces the normalisation lower bound
  `Z_{g,eps} >= C_1 * eps` for sufficiently small `eps`, where the
  constant `C_1` is derived from the positive limit
  `A_g = (2*pi)^{-1/2} \int_R exp(-s^2/2) / sqrt(1 + g(s)^2) ds`
  (Proposition 3 / line 161).
- Evidence: paper Corollary 1 (line 165);
  `adaptive_reflow/contracts/paper_quantities.py:64`
  (`sheet_evidence_A` returns `A_g`).

## CLM-014: Posterior mass on isolated cells is `O(eps)` {#CLM-014}

- Status: ACTIVE
- Date: 2026-08-28
- Source: paper Corollary 1 (Li 2024, line 165-168)
- Asserted by: docs/adr/0013-posterior-selection-drives-algorithm.md:799-804,
  docs/INSIGHTS.md:111
- Disputed by: —
- Statement: Paper Corollary 1 proves
  `mu_{g,eps}(union_z I_z) <= C_2 * eps` for sufficiently small `eps`,
  the *normalised* mass statement derived from Lemma 3's
  `int_{I_z} p_eps <= C_g e^{-z^2/4} eps^2` unnormalised bound divided
  by Corollary 1's `C_1 * eps` lower bound.
- Evidence: paper Corollary 1 (line 165-168).

## CLM-015: Framework does NOT prove paper Theorem 1 magnitude-level competition {#CLM-015}

- Status: ACTIVE
- Date: 2026-08-28
- Source: ADR-0013 §"What the paper does NOT claim"
- Asserted by: docs/adr/0013-posterior-selection-drives-algorithm.md:782-790,
  docs/INSIGHTS.md:103
- Disputed by: —
- Statement: The framework's `n_cap` ramp is a convex mixing weight on
  a state vector; it is *directionally* aligned with the paper's
  `eps -> 0` limit but does not produce the
  `Theta(eps^{+1}) / O(eps^{+2})` evidence competition the paper
  proves at the magnitude level. The framework's `eps_implicit`
  parameter is a tunable hyperparameter, not the paper's `eps`.
- Evidence: `docs/audit/EPSILON_DIRECTION.md` (canonical audit record
  of the dimensional-orthogonality finding).

## CLM-016: (DEPRECATED) Original `_paper_evidence_balance` used inverted `eps` exponents {#CLM-016}

- Status: DEPRECATED
- Date: 2026-08-28
- Source: ADR-0013 §"What the paper does NOT claim"
- Asserted by: docs/adr/0013-posterior-selection-drives-algorithm.md:771-781
- Disputed by: docs/adr/0013-posterior-selection-drives-algorithm.md:198-219
  (the corrected closed form using *positive* powers)
- Statement: The prototype `_paper_evidence_balance` helper historically
  claimed `sheet = eps^{-1}` and `cell = eps^{-2}`, *inverting* paper
  Lemma 2 + Lemma 3's exponents. The corrected helper uses positive
  powers (`sheet = Theta(eps^{+1})`, `cell = O(eps^{+2})`) per the
  audit at `docs/audit/EPSILON_DIRECTION.md` §4.2.
- Evidence: `docs/audit/EPSILON_DIRECTION.md` §4.2; corrected code at
  `adaptive_reflow/algorithm/scheduler.py:1548`
  (`_paper_evidence_balance` closed form).

## CLM-017: (DEPRECATED) `selection_ratio` converges to 1 over rounds {#CLM-017}

- Status: DEPRECATED
- Date: 2026-08-28
- Source: prior versions of `docs/INSIGHTS.md` /
  `docs/adr/0013-posterior-selection-drives-algorithm.md`
- Asserted by: docs/adr/0013-posterior-selection-drives-algorithm.md:680-688
  (the prior prediction, now demoted)
- Disputed by: docs/adr/0013-posterior-selection-drives-algorithm.md:651-706
  (the post-review clarification that demotes the prediction),
  docs/ABLATION.md:183-189 (the empirical plateau finding)
- Statement: The shipped `selection_ratio` does NOT converge to 1 over
  rounds; it plateaus at the value dictated by the adapter's
  fixed-noise replay. The "converges to 1" prediction applies to a
  future *endpoint-conditioned* metric that scores the round's own
  bundle rather than a fresh replay — a real architectural change
  deferred behind the runner-batch-trajectories open decision.
- Evidence: `docs/review/B5-VERIFICATION.md` (the canonical
  investigation); `docs/ABLATION.md` §"What the data shows WITHOUT
  claiming paper backing" (the empirical plateau).

## CLM-018: Cosine wins on W2 vs polynomial, sigmoid, and convergence-adaptive {#CLM-018}

- Status: ACTIVE
- Date: 2026-08-28
- Source: ablation data, `tools/run_ablation.py`
- Asserted by: docs/ABLATION.md:115-116
- Disputed by: —
- Statement: On `two_moons`, the ordering by final W2 is
  `cosine (0.8140)` < `convergence-adaptive (0.8973)` <
  `sigmoid (0.9397)` < `polynomial (1.0521)`. On `eight_gaussians`,
  `convergence-adaptive (1.1688)` < `cosine (1.9298)` <
  `polynomial (2.0943)` < `sigmoid (2.2849)`. No schedule family
  dominates both targets.
- Evidence: `docs/ABLATION.md` §"New findings: schedule families
  (ADR-0012)"; regression coverage in
  `tests/test_tools/test_run_ablation.py`.

## CLM-019: `SchedulerProtocol` is the canonical first-class scheduler axis {#CLM-019}

- Status: ACTIVE
- Date: 2026-08-29
- Source: ADR-0011 §"The four-axis product", `docs/defaults-matrix.md` §1
- Asserted by: docs/defaults-matrix.md:21-32,
  docs/schedule-theory.md:170-180,
  docs/INSIGHTS.md:11
- Disputed by: —
- Statement: `SchedulerProtocol` is the canonical first-class
  scheduler axis exposed by `adaptive_reflow.algorithm.scheduler`;
  nine concrete implementations are registered in
  `SCHEDULER_REGISTRY` (`cosine`, `constant`, `linear`,
  `exponential`, `polynomial`, `sigmoid`, `convergence_adaptive`,
  `codimension_sheet`, `sequential`). The defaults matrix's
  Scheduler column references four of these nine families; the
  other five are valid but not the reader-facing defaults.
- Evidence:
  `adaptive_reflow/algorithm/scheduler.py:2739`
  (`SCHEDULER_REGISTRY`),
  `adaptive_reflow/algorithm/sequential.py:95`
  (`SequentialScheduler`),
  `docs/defaults-matrix.md` §"The matrix".

## CLM-020: `BoundedMergeOperator` enforces a non-zero noise floor {#CLM-020}

- Status: ACTIVE
- Date: 2026-08-29
- Source: ADR-0007 §"Bounded merge semantics", `docs/defaults-matrix.md` §2.3
- Asserted by: docs/defaults-matrix.md:97-103,
  docs/INSIGHTS.md:40
- Disputed by: —
- Statement: `BoundedMergeOperator` enforces a hard `[floor, cap]`
  envelope on every per-round merge; the `floor` parameter is the
  structural guarantee that the noise scale stays inside the
  scheduled envelope and that the algorithm does not freeze on the
  prior. The defaults matrix uses `floor=0.1` for short runs
  (`cycle_length=4`) and `floor=0.05` for long runs
  (`cycle_length=20`) — the floor drops with `cycle_length` because
  longer cycles can tolerate a lower floor.
- Evidence:
  `adaptive_reflow/algorithm/merge_operator.py:350`
  (`BoundedMergeOperator` class),
  `adaptive_reflow/algorithm/merge_operator.py:386`
  (`floor`/`cap` keyword arguments),
  `tests/test_algorithm/test_merge_operator.py`
  (the bounded-merge regression suite).

## CLM-021: `SequentialScheduler` mirrors PyTorch's SequentialLR composite scheduler {#CLM-021}

- Status: ACTIVE
- Date: 2026-08-29
- Source: ADR-0012 §"Sequential chain", `docs/sequential-protocol.md` §1
- Asserted by: docs/sequential-protocol.md:9-20,
  docs/defaults-matrix.md:30-32
- Disputed by: —
- Statement: `SequentialScheduler` is the `adaptive_reflow` analog
  of PyTorch's SequentialLR composite learning-rate scheduler: it
  takes a list of `(sub_scheduler, n_rounds)` tuples and routes
  round `r` to the sub-scheduler at slot index `i` where `r` falls
  in `[sum(n_rounds[:i]), sum(n_rounds[:i+1]))`. The chain's
  `cycle_length()` returns `sum(n_rounds)` and its `config_hash()`
  includes every sub-scheduler's own `config_hash()` so two chains
  with the same shape but different sub-schedulers produce distinct
  hashes. The implementation is registered in `SCHEDULER_REGISTRY`
  under the key `"sequential"`.
- Evidence:
  `adaptive_reflow/algorithm/sequential.py:95`
  (`SequentialScheduler` class),
  `adaptive_reflow/algorithm/scheduler.py:2748`
  (`SCHEDULER_REGISTRY["sequential"]` entry),
  `tests/test_algorithm/test_sequential.py`
  (16+ regression tests).
