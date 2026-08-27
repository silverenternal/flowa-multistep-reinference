# Changelog

All notable changes to `flowa-multistep-reinference` are documented in
this file. The format follows [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/);
this project does **not** adhere to [Semantic Versioning](https://semver.org/)
because the contract surface evolves with the research questions, not
on a fixed cadence. Version markers in commit messages follow the
`vMAJOR.MINOR.PATCH` schema used by GitHub tags.

## [Unreleased] - Code review fixes (non-paper claims)

### Fixed

- **B1** — `adaptive_reflow/frame/engine.py` now type-checks `bundle.source_round` before the `int(...)` cast. Previously, a `None` source_round would raise `TypeError` from inside `int()`. The new code performs a defensive type check (rejecting non-int / non-None values with a clear audit error) and rounds a float `source_round` to `int` first. Severity: MEDIUM (defensive input handling). Tests: `test_engine_coerces_bundle_source_round` in `tests/test_frame/test_engine.py`.
- **B2** — `two_moons` / `eight_gaussians` mode centres consolidated to a single source of truth in `adaptive_reflow/adapters/twodim_fm_centers.py`. Previously, definitions of the analytic mode-centre set could drift between the adapter (`adaptive_reflow/adapters/twodim_fm.py`) and the evaluator (`adaptive_reflow/eval/posterior_selection_evaluator.py`); the ablation's `selection_ratio` was measuring against inconsistent geometry. Now: canonical definitions live in one module; the adapter and the evaluator both import from it. Tests assert byte-equality between the two sites (`tests/test_eval/test_posterior_selection_evaluator.py::test_centers_match_adapter_geometry`). Severity: HIGH (silent measurement drift). 
- **B3** — `ConvergenceAdaptiveScheduler.ema` docstring corrected. The formula `smoothed_w2 = ema * w2 + (1 - ema) * smoothed_w2` means `ema=0` is MAXIMUM smoothing (frozen; the recurrence ignores new samples) and `ema=1` is NO smoothing (raw; the recurrence always takes the new sample). The docstring previously said the opposite. Test now asserts both extremes and the convergence property at intermediate values. Severity: LOW (documentation-only). Tests: `test_convergence_adaptive_ema_extremes` in `tests/test_algorithm/test_scheduler.py`.
- **B4** — `AdaptivePolicyDriver` docstring corrected. The floor divisor in the policy-hash bucket assignment is `2**64` (matching the `policy_hash` convention of `uint64` precision), not `2**256`. The implementation has always used `2**64`; only the docstring was wrong. Severity: LOW (documentation-only). Tests: existing `test_adaptive_policy_driver_hash_bucket_within_uint64_range` continues to pass.

### Deferred

- **B5** — `ReInferenceRunner`'s `selection_ratio` metric semantics need human discussion before any code change. The reviewer suspected a wiring defect (wrong bundle passed to the evaluator); investigation in `docs/review/B5-VERIFICATION.md` showed the actual defect is strictly worse — the evaluator's parameter is inert (the metric is a fixed unconditional replay of the adapter/target pair, invariant to loop state). No small correct code fix is available; the right next step is a design decision about whether to implement an endpoint-conditioned variant. The shipped metric remains as-is until that decision lands.

### Compatibility

- Backwards-compatible. B1 changes only the type-check path; valid inputs (int `source_round`) hit the same `int(...)` cast as before. B2 changes only module boundaries (one canonical definition); the numeric values are unchanged. B3 and B4 are documentation-only.

## [Unreleased] - Code review fixes

### Fixed

- `adaptive_reflow/algorithm/runner.py::_build_base_policy` — the placeholder `FinalRestartPolicy` hardcoded `outer_cycle_id=0`, so two runners configured with different `outer_cycle_id` produced identical `applied_policy_hash` values and indistinguishable audit trails. The helper now accepts an `outer_cycle_id` parameter (forwarded from `ReInferenceConfig.outer_cycle_id`), preserving the audit invariant that the policy hash uniquely identifies the policy surface. Severity: HIGH (audit / hash collision). Tests: `test_runner_outer_cycle_id_propagates_to_policy_hash` in `tests/test_algorithm/test_runner.py`.
- `adaptive_reflow/algorithm/runner.py::_build_initial_phase_state` — the initial `PhaseState` hardcoded `outer_cycle_id=0`, so the engine-propagated phase carried the wrong cycle for every round. The helper now accepts an `outer_cycle_id` parameter (forwarded from `ReInferenceConfig.outer_cycle_id`). Severity: HIGH (audit / round trace divergence). Tests: `test_runner_outer_cycle_id_propagates_to_phase_state` in `tests/test_algorithm/test_runner.py`.
- `adaptive_reflow/algorithm/runner.py::ReInferenceRunner.run` — the per-round endpoints matrix was allocated with `np.empty` and only filled when `trace.integrator_trace` was non-None. Any round where the trajectory capture was skipped left the row reading as uninitialised memory. The matrix is now NaN-initialised so callers can detect "endpoint not captured" via `np.isnan(result.endpoints).any(axis=1)`. Severity: HIGH (uninitialised memory exposure). Tests: `test_runner_endpoints_matrix_is_nan_initialised` in `tests/test_algorithm/test_runner.py`.
- `adaptive_reflow/algorithm/scheduler.py::_paper_evidence_balance` — removed a dead `if denom <= 0.0` fallback that the input validation rules out (`eps > 0` and `n_clipped in [0, 1]` together guarantee `denom > 0`). The closed form is unchanged; the unreachable branch and its misleading comment have been deleted. Severity: LOW (dead code). Tests: existing `test_paper_evidence_balance_helper_closed_form` continues to pass byte-for-byte.

### Compatibility

- Backwards-compatible. `ReInferenceConfig.outer_cycle_id` defaults to `0`, so runs that did not opt into a non-zero cycle continue to produce identical `applied_policy_hash` values for the same inputs. Endpoints-matrix callers that previously relied on `np.empty` semantics should switch to `np.isnan(...)` checks now that the matrix is NaN-initialised.

## [Unreleased] - Paper-grounded algorithm layer (insight doc)

### Added

- `docs/INSIGHTS.md` — the canonical narrative for ADR-0013 ("Paper-grounded algorithm layer: how Li 2024 Theorem 1 maps to flowa's algorithm abstractions"). Five sections: summary (algorithm layer is theory-backed, not arbitrary), paper-to-framework correspondence table (Lemma 2-4 + Proposition 3 mapped to `SchedulerProtocol` / `PolicyDriverProtocol` / `MergeOperatorProtocol` / `RestartBlenderProtocol`), ablation findings (`selection_ratio` is sheet-dominant from round 0 — `0.806` rising to `0.819` on `two_moons`, `0.531` rising to `0.547` on `eight_gaussians`; cosine wins on W2), new capability (`CodimensionSheetScheduler` + `PosteriorSelectionEvaluator` + ADR-0013 together move the framework from "exploratory engineering" to "theory-backed design"), and the next question (does `apply_restart_distribution` realise paper's `sigma -> 0` selection, or is there a gap?).

## [Unreleased] - Paper-grounded algorithm layer

### Added

- `docs/adr/0013-posterior-selection-drives-algorithm.md` — maps Li (2024) *Gaussian Posterior Selection on Noncompact Fibres with Uniformly Separated Roots*, Theorem 1, onto the framework's algorithm layer. The paper's three-estimate proof architecture (Lemma 2 sheet-tube scaling, Lemma 3 root-cell bound, Lemma 4 complement suppression) is the structure the three algorithm abstractions (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`) already have; the ADR records the correspondence as load-bearing rather than incidental.
- `CodimensionSheetScheduler` — a `SchedulerProtocol` implementation of paper Lemma 2-4 directly, rather than of a fixed ramp shape. `n_cap(r) = n_min + (n_max - n_min) * ratio` where `ratio = sheet_evidence / (sheet_evidence + cell_evidence)`, `sheet_evidence = 1 / max(n_cap_base, eps_implicit)` (paper Lemma 2: the codimension-1 sheet scales like `eps^-1`) and `cell_evidence = (1 - n_cap_base)^2 / eps_implicit^2` (paper Lemma 3: each codimension-2 cell is bounded by `O(eps^2)`). When `n_cap_base` is high the sheet dominates and `n_cap` stays high; when `n_cap_base` falls the cells dominate and `n_cap` falls faster than the base ramp. Family identifier `codimension_sheet`; registered in `SCHEDULER_REGISTRY` under `"codimension_sheet"`.
- `PosteriorSelectionEvaluator` (`adaptive_reflow/eval/posterior_selection_evaluator.py`) — empirical validator for paper Theorem 1's prediction. Measures the per-round `sheet_evidence` / `cell_evidence` pair by replaying the 2D-FM adapter and reports `selection_ratio = sheet_evidence / (sheet_evidence + cell_evidence)` as both `raw_score` and (clipped to `[0, 1]`) `bounded_score`; the audit reason on every emitted evidence row contains `posterior_selection`. Regression tests confirm `eight_gaussians` scores a lower ratio than `two_moons` — more competing modes means harder selection, which is paper Lemma 3's per-cell sum growing.
- `ReInferenceConfig.selection_evaluator` — optional `PosteriorSelectionEvaluator`. When supplied, `ReInferenceRunner.run` emits `per_round_metrics[r]["selection_ratio"]` alongside the promoted `W2` / `coverage` pair. `None` (the default) leaves the runner byte-for-byte identical to its ADR-0012 behaviour.
- `tools/run_ablation.py` — two new ablation rows: `multi_round_codimension_sheet_posterior_selection` (`CodimensionSheetScheduler(eps_implicit=0.05)` + `ScheduleDerivedPolicyDriver` + `PosteriorSelectionEvaluator`) and `multi_round_cosine_posterior_selection` (the paper-grounded cosine baseline with the same evaluator). The grid grows from 16 to **18 rows** (8 canonical configs x 2 targets, plus the 2 paper-grounded rows on `two_moons` — the minimal instance of paper Theorem 1's fibre geometry).
- `docs/ABLATION.md` — a `Selection ratio (paper Theorem 1, ADR-0013)` table and a `New findings: posterior selection (ADR-0013)` section. Empirical result: the ratio is sheet-dominant from round 0 (`0.806` rising to `0.819` on `two_moons`) but does **not** reach 1 — the replay estimator scores the adapter at a *fixed* noise scale, and paper Proposition 3's limit is `sigma -> 0`. The ratio is also schedule-independent by construction, so cosine and codimension report the same curve and separate on W2 / coverage instead (`delta_W2 = -0.3000` in cosine's favour at 20 rounds).

### Changed

- Cosine annealing's status is upgraded from "the default schedule" to **the paper-grounded canonical implementation** of paper Lemma 2's sheet-tube scaling. ADR-0012 rejected Karras EDM `sigma(t)` on implementation grounds (no score gradient); ADR-0013 closes the theoretical gap — Karras `sigma(t)` is defined by score matching, not by posterior selection, so it does not inherit Theorem 1's guarantees.
- `adaptive_reflow/algorithm/runner.py` — one optional evaluator call after the per-round W2 / coverage promotion, plus the new `ReInferenceConfig` field.
- `adaptive_reflow/algorithm/scheduler.py::SCHEDULER_REGISTRY` — extended with `"codimension_sheet"`.
- `tools/run_ablation.py` — the `docs/ABLATION.md` findings prose for both ADR-0012 and ADR-0013 is now *generated from the row data* rather than hand-written, so the narrative cannot drift away from the table above it.
- `tests/test_tools/test_run_ablation.py` — asserts the 18-row grid and the presence of the selection-ratio table.

### Compatibility

- Backwards compatibility is total. `ReInferenceConfig.selection_evaluator` defaults to `None`, and every pre-existing scheduler, policy driver, merge operator, blender, `config_hash`, and audit invariant is unchanged. Runs configured without a selection evaluator emit exactly the metric keys they emitted before.

## [Unreleased] - New scheduler families

### Added

- `PolynomialScheduler` — power-law ramp `n_cap = n_min + (n_max - n_min) * (1 - u_r^p)` with `p > 0`. Convex ramp (front-loaded exploration, then plateau) for `0 < p < 1`; concave ramp (capacity stays high longer, then climbs late) for `p > 1`. Cosine is the `p = 2` approximate; the family lets us sweep the convex/concave shape without changing the cycle family. Family identifier `polynomial`; registered in `SCHEDULER_REGISTRY` under `"polynomial"`.
- `SigmoidScheduler` — logit curve `n_cap = n_min + (n_max - n_min) * sigmoid(k * (u_r - m))` with configurable `steepness` and `midpoint`. Plateau + step ramp; large `k` approaches a step function at the chosen `midpoint`. Family identifier `sigmoid`; registered in `SCHEDULER_REGISTRY` under `"sigmoid"`.
- `ConvergenceAdaptiveScheduler` — PID-lite feedback-driven wrapper around a base `CosineAnnealScheduler`. Maintains a bounded shift on the cosine's effective `u_r`; updated by per-round `W2` series. `shift_update = kp * (1.0 - ratio) - kd * delta`; bounded in `[-shift_max, +shift_max]` (default `0.15`). When W2 is improving, shift grows (push toward refinement); when W2 is worsening, shift shrinks (push toward exploration); when W2 stalls, shift holds. **Deterministic and no-train** — no gradient, no bandit arm, no online learning step. Falls back to plain cosine when no feedback is provided. Family identifier `convergence_adaptive_cosine`; registered in `SCHEDULER_REGISTRY` under `"convergence_adaptive"`.
- `SchedulerProtocol.record_round_feedback(round_in_cycle, metrics)` — optional hook on the `SchedulerProtocol` surface; default no-op so non-adaptive schedulers continue to work unchanged. `ConvergenceAdaptiveScheduler` overrides it to consume the `W2` metric.
- `ReInferenceRunner` wires feedback: after each round's metric promotion, the runner calls `self._scheduler.record_round_feedback(r, metric)` gated on `hasattr` for backwards compatibility.
- `tools/run_ablation.py` — four new ablation rows: `multi_round_polynomial_schedule_derived`, `multi_round_sigmoid_schedule_derived`, `multi_round_convergence_adaptive_schedule_derived`, and `multi_round_cosine_adaptive_driver`. The grid grows from 8 to **16 rows** (8 configs x 2 targets). The convergence-adaptive row mirrors the runner's loop inline so the evaluator's W2 can be fed back to the scheduler via `record_round_feedback`.
- `docs/ABLATION.md` — empirical findings on the schedule-shape axis (`cosine` vs `polynomial` vs `sigmoid` vs `convergence-adaptive`, all paired with `ScheduleDerivedPolicyDriver`).
- `docs/adr/0012-noise-schedule-survey.md` — ADR documenting the literature survey of 11 candidate methods, the decisions, and the deferred candidates (Karras EDM `sigma(t)`, bandit, RL).

### Changed

- `tools/run_ablation.py` — the convergence-adaptive cell drives the runner's loop directly (so per-round W2 can be fed back to the scheduler).
- `adaptive_reflow/algorithm/scheduler.py::SCHEDULER_REGISTRY` — extended with `"polynomial"`, `"sigmoid"`, `"convergence_adaptive"`.
- `adaptive_reflow/algorithm/scheduler.py::__all__` — extended with `PolynomialScheduler`, `SigmoidScheduler`, `ConvergenceAdaptiveScheduler`.
- `adaptive_reflow/algorithm/runner.py` — one-line feedback call after per-round W2 promotion (line 475, gated on `hasattr`).

### Compatibility

- Backwards compatibility is total: the four pre-existing families (`cosine`, `constant`, `linear`, `exponential`) continue to work unchanged. `record_round_feedback` is a default no-op on the four pre-existing implementations and the two new trivial implementations, so the runner's behaviour in the absence of an adaptive scheduler is identical to ADR-0011's behaviour.

## [Unreleased] - Algorithm abstractions

### Added

- `adaptive_reflow/algorithm/` package — the algorithm layer is now
  abstract and optional. Four roles, four `Protocol`s:
  `SchedulerProtocol` (per-round capacity), `MergeOperatorProtocol`
  (bounded update operator), `PolicyDriverProtocol` (per-round policy
  generator), and `RestartBlenderProtocol` (prior + fresh blend).
- 4 default implementations that preserve existing behaviour:
  `CosineAnnealScheduler`, `BoundedMergeOperator`,
  `ScheduleDerivedPolicyDriver`, and `LinearBlender` — reachable via the
  `default_cosine_scheduler` / `default_bounded_merge_operator` /
  `default_policy_driver` / `default_blender` factories.
- 6 alternative implementations: `ConstantScheduler`, `LinearScheduler`,
  and `ExponentialScheduler` (schedulers); `IdentityOperator` and
  `EMAOperator` (merge operators); `ConstantPolicyDriver` and
  `AdaptivePolicyDriver` (policy drivers); `DistanceDecayBlender`
  (blender).
- `SCHEDULER_REGISTRY` + `build_scheduler(family, **kwargs)` — select a
  schedule family by string (config file, CLI flag, ablation sweep).
- `ReInferenceRunner` outer framework in
  `adaptive_reflow/algorithm/runner.py`. It orchestrates the scheduler,
  policy driver, merge operator, blender, and evaluator across N rounds
  around the inner `Engine`, and emits a `ReInferenceResult` carrying
  the per-round `RoundTrace` tuple, the endpoints array,
  `per_round_metrics`, and `algorithm_signatures` (the
  `{component: config_hash}` provenance map).
- `tests/test_algorithm/` — per-role conformance, determinism, and
  equivalence-to-legacy regression coverage for all ten
  implementations plus the runner.
- ADR-0011 (`docs/adr/0011-algorithm-abstractions.md`) — documents the
  architecture decision: cosine annealing is now *one option*, not the
  framework.

### Changed

- `tools/run_ablation.py` now drives the grid through
  `ReInferenceRunner` instead of hand-building policies against
  `Engine`, and adds a new mixed-configuration row —
  `multi_round_cosine_constant_driver` (cosine scheduler paired with
  `ConstantPolicyDriver`) — that was impossible to express in the old
  code, where the schedule and the policy were the same decision.

### Compatibility

- Backwards compatibility is total: `CosineScheduleSampler`,
  `n_cap_for_round`, `bounded_merge`, and `bounded_merge_with_schedule`
  remain importable from their existing modules with unchanged
  behaviour, and the ADR-0010 engine-level `beta` override still fires
  for callers who drive `Engine.run_round` directly.

### Deprecated

- `CosineScheduleSampler` now delegates to `CosineAnnealScheduler` and
  emits a `DeprecationWarning` pointing at the algorithm-layer
  replacement (`adaptive_reflow.algorithm.CosineAnnealScheduler`, or
  `default_cosine_scheduler()` behind `SchedulerProtocol`). Its
  computed values are unchanged.

## [Unreleased] - Cosine-driven memory fraction + ablation

### Added

- `memory_fraction_from_schedule(schedule_sample, channel)` helper in
  `adaptive_reflow/schedule/cosine.py`. Returns `1 - n_cap` — the canonical
  transform that maps a cosine capacity sample to a memory fraction in
  the unit interval.
- `Frame.engine.run_round` now wires `schedule.n_cap` to
  `policy.beta_by_channel` per round: when
  `FinalRestartPolicy.beta_from_schedule` is `True` (default), the
  per-round `beta_by_channel` is overwritten from
  `memory_fraction_from_schedule(...)`; when `False`, the explicit
  `beta_by_channel` is preserved for back-compat with callers that
  pre-configure the schedule manually.
- ADR-0010 (`docs/adr/0010-cosine-driven-memory-fraction.md`) — documents
  the algorithm decision that closes the disconnect between the cosine
  schedule's per-round `n_cap` and the adapters' constant
  `beta_from_policy`.
- `docs/ABLATION.md` — empirical ablation results on the 2D toy:
  `single_pass` vs `multi_round_constant_beta_05` vs
  `multi_round_cosine_anneal` vs `multi_round_no_restart`, on both
  `two_moons` and `eight_gaussians`.

### Findings (from `docs/ABLATION.md`)

- On `two_moons`, `multi_round_no_restart` wins on final W2
  (`0.6126`); `multi_round_constant_beta_05` ties `multi_round_cosine_anneal`
  on final coverage (`1.000`). Cosine vs constant-beta-0.5:
  `delta_W2 = -0.0610` (constant-beta slightly tighter on this target)
  and `delta_coverage = +0.000`.
- On `eight_gaussians`, `multi_round_no_restart` wins on both final W2
  (`0.6862`) and final coverage (`0.625`); cosine vs constant-beta-0.5:
  `delta_W2 = +0.2115` (cosine tighter) and
  `delta_coverage = +0.250` (cosine covers twice as many modes).
- Across both targets the cosine-annealed schedule averaged
  `delta_W2 = +0.0753` vs the constant-`beta=0.5` baseline and
  `delta_W2 = -0.7906` vs the full-fresh-noise ablation; coverage
  lifted `+0.125` and `-0.125` respectively. The framework's value is
  the *anneal*: the constant-beta baseline either over-preserves the
  prior (`beta=0.5`) or fully discards it (`beta=1.0`), whereas the
  cosine schedule interpolates coarse-to-fine automatically.

---

## [Unreleased] - Python 3.12 pin

### Notes

- All S-tier polish items completed. Final verification on this tree:
  1028 tests passed / 7 skipped, mypy strict clean over 79 source
  files, ruff clean, `tools/check_docs_against_code.py` verified 1802
  doc claims, and `mkdocs build --strict` builds without warnings.
  `tools/mutate/mutation_baseline.json` carries a real captured
  baseline (overall score 0.6705, per-module `killed`/`survived`
  counts, all four threshold gates satisfied) and the griffe-backed
  `docs/api/*.md` pages render internal modules, not just
  `__init__.py` re-exports.

### Changed

- `requires-python = ">=3.12"` (was `">=3.11"`).
- ruff `target-version = "py312"` (was `"py311"`).
- mypy `python_version = "3.12"` (was `"3.11"`).
- All CI workflows now use `python-version: '3.12'` — `cpu-tests.yml`,
  `bench-regression.yml`, `docs-validate.yml`, `docs-deploy.yml`,
  `mutation-nightly.yml`, and `stress-nightly.yml`.
- The numpy PEP 695 workaround comment is removed (we now pin
  `numpy<2.5`, so the broken stub is unreachable). The
  `[[tool.mypy.overrides]]` entry for `numpy.*` itself is retained and
  re-documented: it keeps strict-mode runs independent of the installed
  numpy version rather than working around an unparseable stub.
- `UP040` added to `[tool.ruff.lint].ignore`. The rule activates at
  `target-version = "py312"` and flags two deliberate import-cycle
  breakers (`universal.adapter.RestartPolicy`,
  `molecular.contracts_RoundResultBundle`) whose paired runtime
  placeholder / lazy resolution a PEP 695 `type` statement would change
  the semantics of.

## [Unreleased] - 2D Rectified Flow Adapter Integration

### Added

- `TwoDimFMAdapter` — real CPU-runnable 2D rectified flow adapter
  (2-moons + 8-gaussians targets). Implements all eight methods of
  `FlowMatchingODEAdapter` against a small velocity-field MLP
  (`3 -> 64 -> 64 -> 2`, ~5.4 k parameters) trained offline on
  NumPy. Source `N(0, I_2)`; RK4 / Dormand-Prince integration;
  memory-fraction restart blend.
- `TwoDimFMEvaluator` — W2 + support coverage + energy distance
  deterministic numerical evaluator for the 2D-FM model. Lives at
  `adaptive_reflow.eval.twodim_fm_evaluator` and satisfies the DTB-R7
  "real replay-through-adapter" evaluation leg.
- `twodim_fm_train.py` — NumPy Adam trainer CLI for the velocity
  field MLP. Hand-rolled analytic-gradient Adam optimizer (no torch,
  no autograd, no SciPy). Reachable as
  `python -m adaptive_reflow.adapters.twodim_fm_train`.
- `data/twodim_fm_*.npz` — pre-trained weights (~2KB each) for the
  two target distributions, shipped under `data/`.
- `[project.optional-dependencies].flow_matching = ["numpy", "scipy"]` —
  opt-in extra for the 2D-FM adapter and its offline trainer.

### Changed

- `docs/ADAPTER_INTERFACE_SPEC.md` — added §16 "Real-Model Adapters:
  TwoDimFMAdapter" with architecture diagram, target distribution
  definitions, restart semantics, ~520 LOC implementation note, and
  pre-trained-weights references.
- `docs/TUTORIAL.md` — new worked-example tutorial walking through
  loading `.npz` weights, building an `Engine`, running five rounds
  with `restart_beta=0.5`, computing `support_coverage` via
  `TwoDimFMEvaluator`, and plotting the endpoint samples.
- `pyproject.toml [tool.mypy] exclude` and
  `[[tool.mypy.overrides]]` — exclude NumPy 2.x stubs (broken `type`
  statement that mypy 1.x cannot parse on Python 3.11); document the
  limitation in this changelog. Tests, ruff, and docs scanner are
  unaffected.

## [Unreleased] — S-tier governance upgrade

### Added

- `ROADMAP.md` — three-bucket (Now / Next / Later) roadmap anchored on
  `todo.json` and the S-tier closure list (DTB-R0 §3 case 2/5,
  ToyGaussianAdapter, synthetic oracle, stress test, reader docs). See
  the dated entries that close each of those items.
- `CONTRIBUTING.md` — single-maintainer contributor guide covering the
  four recurring workflows (hostile-case test, adapter, mutation test,
  docs scanner catalogue).
- `docs/DEPRECATION.md` — versioned deprecation table for the
  `adaptive_reflow.legacy/` quarantine subpackage; documents the
  removal schedule with no symbols removed yet.
- `docs/adr/0001-record-architecture-decisions.md` — meta-ADR adopting
  MADR 4.0 as the ADR format; this file is itself an example.
- `docs/adr/0002-typed-contracts-core-boundary.md` — pins
  `adaptive_reflow.contracts` as the canonical contract surface and
  freezes the import direction (contracts is leaf; molecular and
  universal may import from contracts but never the reverse).
- `docs/adr/0003-universal-vs-molecular-split.md` — freezes the
  universal / molecular split and requires a non-molecular adapter
  (ToyGaussianAdapter) as the proof artifact before any later universal
  surface change.
- `docs/adr/0004-engine-seven-step-operation-order.md` — pins the
  seven-step `Engine.run_round` operation order as a load-bearing
  invariant; changes require a new ADR.
- `docs/adr/0005-fail-closed-audit-code-policy.md` — pins the policy
  that every `AUDIT_*` constant is re-exported in the public
  `__init__.py` and indexed by `tools/check_docs_against_code.py`.
- `SECURITY.md` — explicit "no security-sensitive surface" statement
  with the standard supported-versions and reporting boilerplate.
- `CODEOWNERS` — assigns the load-bearing boundaries
  (`adaptive_reflow/contracts/**`, `adaptive_reflow/universal/**`,
  `adaptive_reflow/frame/engine.py`) to `@flowa-maintainer`; the rest
  of the repo inherits the same ownership.

### Changed

- The doc-drift scanner target was raised from 817 to 880+ verified
  claims as part of the S-tier upgrade; the scanner catalogue now
  resolves every governance-doc identifier in this changelog.
- `README.md` cross-references the new `ROADMAP.md`, `CONTRIBUTING.md`,
  `CHANGELOG.md`, `SECURITY.md`, `CODEOWNERS`, and `docs/adr/` files.

### Deprecated

- None. `adaptive_reflow.legacy/` is already quarantined and continues
  to emit `DeprecationWarning` on import; see `docs/DEPRECATION.md` for
  the removal schedule.

### Removed

- None. No public symbols were removed in this release. The eight
  legacy modules under `adaptive_reflow/legacy/` remain in place until
  their consumers are migrated (see `docs/DEPRECATION.md`).

### Fixed

- None at this release. The previous release's tests, ruff gate, and
  doc scanner (817 / 817 verified) remain green; the S-tier upgrade
  adds governance scaffolding without touching the typed-contracts core.

### Security

- None. The project has no security-sensitive surface (see `SECURITY.md`).
  The audit-code policy documented in ADR-0005 is a *contract-correctness*
  invariant, not a security boundary.

---

## [Unreleased] - Algorithmic Gap Closure

### Fixed

- A1: channel_rule stability-collapse is fail-closed on malformed inputs
- A2: bounded_merge_with_schedule honors per-channel floor config
- A3: bounded_merge uses prev anchored to last_emitted, not scheduled_cap
- A4: engine.run_round coerces round_index on all paths
- A5: engine emits ERR_CHANNEL_DOMAIN_UNDECLARED for undeclared domains
- B1: CosineScheduleSampler split compute/record for purity
- B2: engine wraps all adapter calls in _safe_adapter_call
- B3: claim_gate delegates to _resolve_decision helper (R7-ready)
- B5: bounded_merge emits MERGE_DEGENERATE_INTERVAL audit code
- C1: RMSPreservingCoordinateMixer renamed to EqualRmsCoordinateMixer with back-compat alias
- C2: bounded_merge_with_schedule rejects prev=None with ERR_PREV_REQUIRED
- C3: engine coerces bundle.source_round

### Added

- ADR-0006: engine-wraps-adapter pattern
- ADR-0007: prev-anchored bounded-merge
- ADR-0008: claim-gate deferral placeholder
- ADR-0009: mixer RMS-preservation precondition

---

## How to read this changelog

* Items in **Added** are user-visible additions to the public surface or
  to the governance docs.
* Items in **Changed** are behaviour-affecting modifications to existing
  surface. A reader who upgrades between two releases should diff the
  **Changed** sections.
* Items in **Deprecated** will be removed in a future release; the date
  appears in `docs/DEPRECATION.md`, not here.
* Items in **Removed** are gone. Search the diff between this and the
  previous release for the removal commit hash.
* Items in **Fixed** close a regression. They reference the test or
  fixture that pins the fix.
* Items in **Security** are reserved for vulnerabilities in the supply
  chain. Today this section is empty by construction (see `SECURITY.md`).