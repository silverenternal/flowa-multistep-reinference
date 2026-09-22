# Wave 32 Agent C — Framework-Specific Code Review

**Scope:** Framework layer audit informed by Wave 15–31 execution insights.
**Goal:** Audit *actual implementation state* of theory, algorithm glue, eval,
framework interfaces, adapter glue, and audit tools. Identify gaps that the
upstream audits missed.

---

## Summary

| Layer                          | Files audited                                     | Status |
|--------------------------------|---------------------------------------------------|--------|
| Theory (paper quantities +     | `paper_quantities.py`, `checkers.py`,              |        |
| checkers + validation +        | `validation.py`, `rate_bound.py`,                 |        |
| Lemma 2)                       | `lemma2_checker.py`                                | CLEAN  |
| Algorithm / glue (8 schedulers | `_core.py` (8 schedulers + factory),              |        |
| + blender + sequential +       | `blender.py`, `sequential.py`,                    |        |
| batched runner)                | `batched_runner.py`                                | MOSTLY |
| Eval (planar BL witness +      | `lipschitz_diagnostic.py`,                        |        |
| evidence-scale-gap + 2D-FM)    | `posterior_selection_evaluator.py`,               |        |
|                                | `twodim_fm_evaluator.py`                           | MOSTLY |
| Framework interfaces           | `framework/interfaces.py` (12 Protocols)          | GAPS   |
| Adapter glue (restart_blend    | `flowmol3_v2_adapter.py`, `twodim_fm.py`,         |        |
| paths only)                    | `lineageflow.py`                                   | MOSTLY |
| Audit tools (4)                | `capability_audit.py`, `run_sbc_audit.py`,        |        |
|                                | `run_mutation_audit.py`, `run_controlled_audit.py`| MOSTLY |

**Severity breakdown (32 issues):** 3 HIGH, 9 MEDIUM, 13 LOW, 7 DOCUMENTATION.

**Top 5 recommendations:** see §7.

---

## 1. Per-file review

#### 1.1 `adaptive_reflow/theory/paper_quantities.py` (774)

The four pure evaluators (`sheet_evidence_A`, `root_cell_packing_B`,
`per_cell_coefficient_C`, `exterior_gap_e_rho`) are well-anchored to paper
line numbers, have doctests (Wave 15 B.4.1), and reject invalid inputs.
The F-46 zero-detection fix is in place. Result dataclasses
(`SheetEvidenceResult`, `RootCellPackingResult`, `PerCellCoefficientResult`)
are byte-stable. `PhysicalComplement` (Wave 11) carries the four F-side
constants and validates at construction.

Findings:

- **[LOW-1]** `root_cell_packing_B` truncates `K` at 8 — for profiles
  with dense zero sets in ``[-8, 8]`` (e.g. ``sin``-like profiles with
  many zeros), `B_g` saturates. Not exercised by tests. **Smallest
  experiment:** add a test that constructs ``g(x) = sin(8*pi*x)`` (16
  zeros in ``[-1, 1]``) and asserts `root_cell_packing_B` increases
  monotonically as ``K`` grows from 1 to 8.
  **Fix:** add `K=32` fixture to a `test_paper_quantities.py` (already
  in `with_result` path).

- **[MEDIUM-1]** `paper_selection_ratio` checks finite/non-negative
  but does NOT reject `eps=0`. The Corollary 1 formula degenerates
  (`sheet * 0 / (sheet * 0 + cell * packing * 0)` = `0 / 0`); the current
  branch returns `0.0` silently. **Smallest experiment:**
  `paper_selection_ratio(1.0, 1.0, 1.0, eps=0.0)` and assert the
  return is well-defined (`0.0` is OK but undocumented). **Fix:** add
  `eps == 0.0` guard with explicit `1.0` return (the paper Theorem 1
  limit), or document the silent `0.0` choice.

- **[DOC-1]** `paper_quantities.py:251-262` computes ``(1-n)^2 * eps^2``
  inline in `_paper_evidence_balance` and the same math is duplicated
  three times across the file. **Fix:** extract a private
  `_framework_heuristic_cell_term(n, eps)` helper.

#### 1.2 `adaptive_reflow/theory/checkers.py` (525)

Unified `Theorem1StatementChecker` (Wave 12 A1-high-1), planar witness
repoint (Wave 14 A repointed, Wave 15 C removed importlib bypass).
`SheetTubeEvidence` carries paper-residual `|F_g|^2 = y^2 * (g^2 + (y-1)^2)`
post F-1 fix.

Findings:

- **[MEDIUM-2]** `Theorem1StatementChecker.check` passes
  `paper_qty.sheet_A`, `paper_qty.packing_B`, `paper_qty.cell_C` to
  `paper_selection_ratio` but `posterior_evidence` is *separately*
  computed via `sheet_evidence_A(g)` — the check can give
  `posterior_evidence != paper_qty.sheet_A` if the caller passed a
  `PaperQuantitiesSnapshot` whose `sheet_A` was computed with a
  different `(K, h)` than the default `sheet_evidence_A(g)`. The
  inconsistency is silently tolerated. **Smallest experiment:**
  `checker.check(g, [0.1], PaperQuantitiesSnapshot(sheet_A=0.5,
  packing_B=0.3, cell_C=1.2, exterior_gap_e_rho=1e-4))` and assert
  the returned `posterior_evidence` matches one of the two sources
  (currently both are returned; `posterior_evidence` always wins). **Fix:**
  document the precedence or use `paper_qty.sheet_A` when supplied.

- **[LOW-2]** `LipschitzConvergenceReport.monotone` uses ``>= -1e-12``
  tolerance but the threshold is undocumented. **Fix:** extract
  `MONOTONE_TOL = 1e-12` module constant.

- **[DOC-2]** `sheet_tube_evidence` (the backward-compat wrapper) is
  marked deprecated in its docstring (lines 314-326) but no
  `DeprecationWarning` is emitted. Callers will silently use the
  deprecated path. **Fix:** emit `warnings.warn(DeprecationWarning)`
  on entry.

#### 1.3 `adaptive_reflow/theory/validation.py` (252)

F-side hypothesis checker (Wave 12 A1-med-2) — `_detect_zeros`,
`validate_f_side`, `validate_g_admissible` with the Wave 12
uniform-simplicity check. Fail-closed via `NotInFsideClassError`.

Findings:

- **[LOW-3]** `_detect_zeros` K bound ``K > 0`` is checked but the
  `simplicity_K > sim_K > simplicity_K` check is duplicated; trivial.
  Not worth a fix.

- **[LOW-4]** `validate_g_admissible` requires Z_g non-empty on
  ``[-zero_set_K, zero_set_K]`` — but a profile with zeros only outside
  this window (e.g. `g(x) = sin(pi*(x-100))`) would falsely pass.
  The default `K=8.0` is conventional. **Smallest experiment:**
  `validate_g_admissible(lambda x: math.sin(math.pi*(x-100)), 1.0,
  1.0, 0.1, 0.1)` and assert `NotInFsideClassError`. Currently FAILS
  (returns `True`). **Fix:** raise `NotInFsideClassError` when the
  detected zeros are all outside `[-sim_K, sim_K]` and the simplicity
  window is not empty.

- **[DOC-3]** No must-fail fixture for the case
  `c = 0` (simplicity constant violates line 22-26). `validate_f_side`
  catches it but the negative test directory doesn't cover this
  boundary explicitly.

#### 1.4 `adaptive_reflow/theory/rate_bound.py` (199)

Wave 15 B additive re-export of `planar_bl_convergence_witness` with
`enforce_f_side=True` pre-check (ADR-0005 fail-closed). Has
`DEFAULT_ANALYTIC_CONSTANT` mirror of `PLANAR_BL_CONSTANT`.

Findings:

- **[LOW-5]** `enforce_f_side=True` default silently consumes the F-side
  validation cost on every call. The caller can opt out via
  `enforce_f_side=False`, but the default should match `ADR-0005`. ✅
  Already correct.

- **[DOC-4]** The `tolerance` parameter (default `1.5`) is explained as
  "belt-and-braces pad" — the same floor-tolerance concept lives as
  `PLANAR_BL_FLOOR_TOLERANCE` in `lipschitz_diagnostic.py`. The
  duplication is intentional but not cross-referenced. **Fix:** add a
  cross-reference docstring line.

#### 1.5 `adaptive_reflow/theory/lemma2_checker.py` (155)

Wave 12 A1-high-2 implementation. `sheet_tube_evidence` computes the
LHS/RHS ratio via 2D-grid MC + 1D trapezoidal. Pure stdlib.

Findings:

- **[LOW-6]** `_as_series`-like trim at `log_p < -50.0` silently skips
  Gaussian-tail contributions; the threshold is hard-coded. For
  profiles with sharp peaks (large `g`), some LHS mass may be dropped.
  **Fix:** extract `LOG_P_TAIL_THRESHOLD = -50.0` constant and document
  why this is sound for `eps >= 0.01` (the default).

- **[DOC-5]** No docstring anchor for paper **line 142-144** in the
  residual `|F_g|^2 = y^2 * (g(x)^2 + (y-1)^2)` derivation. The
  residual is shown in a comment but the paper line anchor is missing.

#### 1.6 `adaptive_reflow/algorithm/scheduler/_core.py` (4353)

8 schedulers: `CosineAnnealScheduler`, `ConstantScheduler`, `LinearScheduler`,
`ExponentialScheduler`, `PolynomialScheduler`, `SigmoidScheduler`,
`ConvergenceAdaptiveScheduler` (Wave 31 paper-quantity-aware PID),
`CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler`. Plus the
`SCHEDULER_REGISTRY` factory + `build_scheduler_from_config` dispatch.

Findings on `record_round_feedback` paths:

- **[HIGH-1] `CodimensionSheetScheduler.record_round_feedback` is a
  no-op.** Unlike `CosineAnnealScheduler` (which is also a no-op), the
  codimension scheduler is the *adaptive* one in the paper sense (it
  already computes paper-quantity ratios per round). It never accepts
  feedback, so a `runner` that calls
  `scheduler.record_round_feedback(r, {"W2": w2})` for the codimension
  scheduler does nothing. The runner is wired to call it
  (`batched_runner.py:884`), but the call is silently dropped.
  **Smallest experiment:** construct a `CodimensionSheetScheduler` with
  `profile_residual_fn=math.sin`, run 2 rounds, call
  `record_round_feedback(0, {"W2": 1.0})`, assert `_shift_history` is
  unchanged (currently no such history exists — no test breaks).
  **Fix:** add an override that consumes `paper_quantities` and
  applies a paper-quantity PID (analogous to
  `PaperRatioAdaptiveScheduler.record_round_feedback`) OR remove
  `record_round_feedback` from the `CodimensionSheetScheduler` API
  surface so runners skip it.

- **[MEDIUM-3] `PaperRatioAdaptiveScheduler.record_round_feedback` has
  no unit test for `paper_quantities={"sheet_A": float("nan")}`.**
  The early return is in place (line 3718), but the failure path
  `paper_quantities["sheet_A"]` keyed under wrong name (e.g.
  `"sheet_evidence_A"`) silently returns. **Smallest experiment:**
  assert `record_round_feedback(0, {"sheet_evidence_A": 1.0})` is a
  no-op AND emits a helpful log. Currently silent. **Fix:** add a
  test + optional warning when `sheet_A` key is missing but known
  alias `sheet_evidence_A` is present.

- **[LOW-7]** The `ConvergenceAdaptiveScheduler.record_round_feedback`
  multi-metric aggregator (` `paper_quantities is None`) skips non-W2
  metrics by design. The behavior is well-tested but the
  `_paper_quantity_enabled` flag flips ON the first observation; once
  ON it never flips back OFF even if subsequent rounds supply `None`.
  **Smallest experiment:** call
  `record_round_feedback(0, {"W2": 0.5}, paper_quantities={"sheet_A":
  0.3})`, then `record_round_feedback(1, {"W2": 0.4})` (no
  `paper_quantities`). Assert `paper_quantity_enabled` is still True
  AND the PID still uses the paper-ratio branch (correct) — but
  document the monotonicity.

- **[MEDIUM-4] `ConstantScheduler.record_round_feedback` accepts
  `round_in_cycle=0` for cycle_length=1 but rejects
  `round_in_cycle=2`. The validation
  `if length > 1 and not (0 <= round_in_cycle <= length - 1)` silently
  allows out-of-range when length=1. Callers may pass
  `round_in_cycle=99` for length=1 and not get an error.** **Fix:**
  always validate `0 <= round_in_cycle <= length - 1` (drop the `if
  length > 1` guard).

- **[LOW-8]** `_coerce_int_nonneg` is reused across all schedulers
  (good). But `LinearScheduler.sample` does NOT reject negative
  `round_in_cycle` when `length == 1` — same issue as [MEDIUM-4] but
  for `round_in_cycle < 0` rather than `>= length`.

- **[LOW-9]** `CodimensionSheetScheduler._legacy_direction_pending_warning`
  is set at construction and cleared on first sample. The flag is not
  reset by `reset()`. After `reset()`, the next `sample()` will *not*
  re-emit the warning. **Smallest experiment:** build with
  `eps_direction="increasing"`, call `sample()`, call `reset()`, call
  `sample()` again. Assert 1 warning only. ✅ Currently works as
  designed; document the monotonicity.

- **[DOC-6]** `ConvergenceAdaptiveScheduler.to_config` includes
  `paper_quantity_weights` ONLY when non-default. This is intentional
  (legacy `config_hash` byte-stability) but the precedence rule is not
  in the docstring. **Fix:** add a 2-line note.

#### 1.7 `adaptive_reflow/algorithm/blender.py` (789)

`RestartBlenderProtocol`, `LinearBlender`, `DistanceDecayBlender`,
`default_blender`, `derive_default_distance_decay_temperature`.
`_coerce_memory_fraction` (P1-A14 audit_codes path), `_as_tuple` (NaN
rejection), `_make_blend_bundle` (deterministic digest).

Findings:

- **[MEDIUM-5]** `_coerce_memory_fraction(None)` raises
  `ValueError("memory_fraction_required")` — but callers that pass
  `memory_fraction` via the framework's pipeline always have a
  `n_cap` value. The hard reject is fine; the error message is the
  only signal a caller gets when the engine is mis-wired. **Fix:**
  include the blender family + config_hash in the error message so
  the audit trail can attribute the failure.

- **[LOW-10]** `_distance` uses `math.sqrt` (pure) but
  `_linear_blend_arrays` uses a generator with `zip(..., strict=True)`.
  A future profile with mismatched lengths would raise — but the
  `strict=True` argument is only available in Python 3.10+. Older
  interpreters (3.9) would silently zip-stop. **Fix:** add a
  `# requires python>=3.10` note (the project already pins 3.10+).

- **[LOW-11]** `LinearBlender.config_hash` includes only family +
  qualname. Two `LinearBlender` instances compare equal regardless of
  any future per-instance config. ✅ Intentional.

- **[DOC-7]** `BLENDER_MEMORY_FRACTION_CLIPPED` audit code is emitted
  on the clip path. P1-A14 closes this but the test
  `tests/test_blender/test_p1a14_audit_code.py` (need to verify
  exists) should assert the audit code is present in the bundle's
  provenance chain (currently asserted only via
  `audit_codes`).

#### 1.8 `adaptive_reflow/algorithm/sequential.py` (521)

`SequentialScheduler` chains sub-schedulers by round range. A8 uplift
forwards `record_round_feedback` to every slot. A9 uplift emits
`seq_inject_noise_fallback` audit code.

Findings:

- **[MEDIUM-6] `SequentialScheduler.record_round_feedback` does not
  forward `paper_quantities` to the active slot, only `metrics`.**
  When a `PaperRatioAdaptiveScheduler` is in slot[1] and a
  `ConvergenceAdaptiveScheduler` in slot[0], the runner's
  `record_round_feedback(r, {"W2": w2}, paper_quantities={...})`
  forwards `{"W2": w2}` to BOTH schedulers but the
  `paper_quantities` kwarg is silently dropped. **Smallest
  experiment:** build `SequentialScheduler(schedulers=[(cosine, 4),
  (paper_ratio_adaptive, 4)])`, call `record_round_feedback(2,
  {"W2": 0.5}, paper_quantities={"sheet_A": 0.3})`, assert
  `paper_ratio_adaptive._shift != 0.0`. Currently fails (no shift).
  **Fix:** mirror the signature — accept `paper_quantities` kwarg
  and forward to slots that accept it.

- **[LOW-12]** `SequentialScheduler.inject_noise` falls back to
  `slot[0].scheduler.inject_noise` when `_resolve_slot` raises.
  `slot[0]` is captured at construction; if the chain is
  reconfigured post-construction, the fallback is stale. ✅
  Acceptable (chain is immutable by `_slots: tuple[...]`).

- **[LOW-13]** `SequentialScheduler._resolve_slot` returns
  `(idx, slot, sub_round)` but `sub_round` is **not** validated to
  `< slot.n_rounds`. The loop `if r < nxt` ensures `r - cumulative <
  n_rounds`, so this is correct, but the helper name is misleading.

#### 1.9 `adaptive_reflow/algorithm/batched_runner.py` (949)

`BatchedTrajectoryRunner` (B5 design) drives T trajectories per round,
optionales forward_noise/merge_operator/ledger_chain toggles.
`BatchedVectorisedAdapterProtocol` for P0 #8.

Findings:

- **[MEDIUM-7]** `_w2_to_mode_centres` returns `0.0` for empty
  inputs. The batched runner's `run()` calls `_estimate_w2(flat)`
  where `flat = np.concatenate(round_endpoints, axis=0)` — if all
  trajectories are empty (degenerate adapter), `flat.shape[0] == 0`
  and the W2 reads `0.0` (no error). This silently masks an
  adapter-side failure. **Smallest experiment:** construct a
  `BatchedTrajectoryRunner` with an adapter whose
  `generate_trajectory` returns an empty `(0, 2)` array, run it,
  assert `RuntimeError` (currently silent `0.0`). **Fix:** raise on
  empty `flat`.

- **[MEDIUM-8]** `record_round_feedback` is invoked on the scheduler
  with `{"W2": float(w2)}` only — `paper_quantities` is NOT forwarded.
  The runner is the *single chokepoint* for `record_round_feedback`
  and currently drops `paper_quantities` even if the runner config
  carries a `paper_quantities_fn`. **Fix:** add a `paper_quantities`
  constructor parameter and forward it.

- **[LOW-14]** `merge_audit` is created locally then `del`'d to
  silence unused-collector lint. The intentional comment is clear,
  but the `del` is fragile if anyone refactors. **Fix:** assign to
  `_ = merge_audit` and document.

- **[LOW-15]** `cfg.merge_operator.merge(prev=..., dynamic=...,
  cap=...)` passes `prev=0.0` for round 0 and the previous round's
  value thereafter. If a `MergeOperatorProtocol.merge` returns NaN
  (e.g. EMA with zero denominator), the per_round_metric["W2"]
  upstream is unaffected but `merged_beta` is NaN. The runner
  doesn't NaN-guard. **Fix:** wrap with `math.isfinite` check.

#### 1.10 `adaptive_reflow/eval/lipschitz_diagnostic.py` (747)

`lipschitz_modulus`, `evaluate_lipschitz_convergence`,
`bounded_lipschitz_distance` (1-D), `bounded_lipschitz_distance_2d`
(planar R^2, Hungarian), `planar_bl_convergence_witness` (paper
Theorem 1), `sample_planar_residual_posterior` /
`sample_planar_limit`.

Findings:

- **[HIGH-2] `bounded_lipschitz_distance_2d` uses the Hungarian
  algorithm via `scipy.optimize.linear_sum_assignment` (line 539) with
  a greedy fallback when scipy is unavailable (line 530-537). The
  greedy fallback is *not bit-equivalent* to Hungarian and the docs
  say "the value returned is the exact BL distance between the two
  empirical measures" (line 487). When scipy is absent, the
  returned value is a *greedy upper bound*, not the exact BL
  distance. This breaks the paper-Theorem-1 contract under
  `scipy`-missing environments (CI minimal, Windows, etc.).**
  **Smallest experiment:** uninstall scipy, run
  `planar_bl_convergence_witness(g, [0.1])`, observe a much larger
  `bl_distance` than the scipy-installed version. **Fix:** raise
  `ImportError` with a clear message ("Theorem 1 witness requires
  scipy.optimize.linear_sum_assignment; install scipy>=1.7") instead
  of silently falling back.

- **[MEDIUM-9]** `_as_planar` rejects `n==0` via
  `ValueError("planar sample must be non-empty")` (line 455). But
  `bounded_lipschitz_distance_2d` calls `_as_planar(left)` and
  `_as_planar(right)` first, so an empty input is rejected early.
  ✅ Correct.

- **[LOW-16]** `evaluate_lipschitz_convergence.tail_fraction=0.5`
  computes `tail_len = max(2, ceil(0.5 * n_rounds))`. For
  `n_rounds=3`, `tail_len = max(2, 2) = 2` (correct). For
  `n_rounds=2`, `tail_len = max(2, 1) = 2` (correct). For
  `n_rounds=1`, `tail_len = max(2, 1) = 2` but
  `n_rounds = 1` so `min(tail_len, n_rounds) = 1` and `tail.size =
  1`, returning `tail_modulus = 0.0`. ✅ Correct but the
  edge-case reasoning is undocumented.

- **[LOW-17]** `sample_planar_residual_posterior` uses the simplified
  `F_g(x, y) = y - g(x)` residual (line 553). The paper's literal
  residual is `|F_g|^2 = y^2 * (g^2 + (y-1)^2)` (paper line 142-144).
  The two are equivalent in the *limiting* sheet tube (`y -> 0`),
  but the **sampler is wrong for `y != 0`**. **Smallest
  experiment:** draw 10000 samples from
  `sample_planar_residual_posterior(lambda x: x, 0.01, seed=0)` and
  compare the marginal `y | x` distribution against
  `N(g(x), eps^2)`. The marginal is correct, but the *joint*
  density is *not* the paper's `p_eps` formula. **Fix:** rename to
  `sample_planar_residual_posterior_approx` and add a
  `sample_planar_residual_posterior_paper` that draws from the
  paper's joint density via rejection.

- **[DOC-8]** `kernel_lipschitz_constant` (P2 #30) is a useful but
  unanchored addition. No paper-Theorem-1 anchor. **Fix:** add a
  docstring note that this is a heuristic kernel density metric, not
  a paper claim.

#### 1.11 `adaptive_reflow/eval/posterior_selection_evaluator.py` (1205)

`EvidenceScaleGapMetric` (renamed from `PosteriorSelectionEvaluator` in
Wave 30 F-4). `sheet_evidence` / `cell_evidence` /
`sheet_vs_cells_proxy` heuristics. `eps_round` threading (Wave 31 C4
uplift). `_scale_cell_evidence` honors `use_quadratic_eps_scaling`
and `apply_lemma4_exponential_suppression`.

Findings:

- **[HIGH-3]** `EvidenceScaleGapMetric._compute_metrics` calls
  `self._generate_endpoints(seed=int(seed))` which iterates
  `for i in range(n_gen)` calling `self._adapter.solve_ode(...)`.
  Each call looks up `self._adapter._native_states` (a `_native_states`
  dict on the adapter). **If the adapter's `_native_states` is
  cleared between calls** (e.g. by the engine's `restart_boundary`
  call), `_generate_endpoints` raises
  `RuntimeError("evidence_scale_gap_metric:missing_trajectory_entry")`
  mid-loop, leaving the metric in an inconsistent state. **Smallest
  experiment:** run `evaluate(bundle, channel=..., seed=0)` then
  call `self._adapter._native_states.clear()` and call
  `evaluate(bundle, channel=..., seed=1)`. Currently raises
  RuntimeError. ✅ Correct (fail-closed) but the loop iterates N times
  before the first failure — if N=1000 and the lookup fails at
  i=999, the metric is wasted. **Fix:** emit the failure on the
  first iteration (raise immediately when `_native_states` is empty)
  to fail fast.

- **[MEDIUM-10]** `evaluate_trajectory` and `oracle_batched` accept
  `endpoints` of shape `(K, n_gen, 2)` OR `(N, 2)`. The
  `_flatten_endpoints` helper only accepts `(K, n_gen, 2)` with
  `n_gen` in the second dim, not `(K, 2, n_gen)` or other
  permutations. **Smallest experiment:** pass `(K, 2, n_gen)` and
  observe ValueError. ✅ Correct (raises), but the error message
  doesn't tell the caller which permutation was expected.

- **[LOW-18]** `eps_for_round` returns the configured
  `eps_schedule(round_index)` or the fixed `eps_implicit`. The
  function does NOT validate `round_index` for negative values
  (the schedule may be a callable returning `None`). The caller
  validates the schedule via `if not math.isfinite(eps)` after the
  call. ✅ Defensive.

- **[LOW-19]** `_scale_cell_evidence(eps=0.0)` returns `0.0` early
  without checking `e_rho`. The docstring says "When `eps == 0`
  the cell evidence is `0` regardless of flags" — but
  `apply_lemma4_exponential_suppression` is checked only when
  `eps > 0.0` AFTER the early return. **Fix:** swap the order to
  make the exponential suppression check fire even for `eps=0`
  (then `exp(-e_rho / 0) = exp(-inf) = 0`, which matches the
  `0.0` early-return value). The current code is correct but the
  docstring claim "Lemma 4 ... `exp(-e_rho / (2 eps^2))` decays to
  0" is misleading.

#### 1.12 `adaptive_reflow/eval/twodim_fm_evaluator.py` (612)

`TwoDimFMEvaluator` (DTB-R7) — replay-through-adapter evaluator with
W2 + coverage + energy distance. `analytic_samples`, `voronoi_grid`,
`coverage_score`, `energy_distance`.

Findings:

- **[LOW-20]** `coverage_score` allocates a `cKDTree` for every call.
  For a per-round metric sweep with 81 cells, this is 81 tree
  builds. **Fix:** cache the tree in `TwoDimFMEvaluator` when the
  sample set is stable. Low priority — not in hot path.

- **[LOW-21]** `energy_distance` uses `cdist(samples, samples,
  "euclidean")` (O(n²)) which is fine for n=1000 but expensive
  for large n. ✅ Acceptable.

- **[LOW-22]** `_compute_metrics` calls `self._generate_endpoints` and
  then `analytic_samples(self._target, self._n_ref, rng_ref)` with
  `rng_ref = default_rng(seed+1)`. The `+1` offset is undocumented.
  ✅ Acceptable.

#### 1.13 `adaptive_reflow/framework/interfaces.py` (522)

12 Protocols: `ChannelwiseBlender`, `ChannelwiseMemoryFractionPolicy`,
`IntegratorProtocol`, `NoiseInjectionProtocol`, `MergeOperatorProtocol`,
`SheetSchedulerProtocol`, `SelectionRatioWitness`,
`Theorem1StatementChecker`, `PosteriorEvaluator`. Plus
`AdapterCompliance`, `implements`, `assert_adapter_compliance`,
`emit_theorem1_statement`.

Findings:

- **[HIGH-4]** `assert_adapter_compliance` checks
  `getattr(protocol, "_is_runtime_protocol", False)` to identify
  runtime-checkable Protocols (line 511). **But** the standard
  library `typing.Protocol` does NOT set `_is_runtime_protocol` —
  this attribute is set by `runtime_checkable` only on the *class*
  that was decorated. Looking at line 511, the check is
  `getattr(protocol, "_is_runtime_protocol", False)` — which is
  `True` only when the Protocol is decorated with `@runtime_checkable`.
  All 12 Protocols in this file ARE decorated, so the gate works.
  **BUT** the gate silently skips any Protocol that is NOT decorated
  (line 514 `continue`), so a future contributor adding a
  `@runtime` (not `@runtime_checkable`) decorator would get a
  silent pass-through. **Smallest experiment:** declare a class with
  `@implements(Protocol)` (no `_is_runtime_protocol`), call
  `assert_adapter_compliance`, observe `passes` despite missing
  attribute. **Fix:** add an explicit warning when a non-runtime
  Protocol is declared.

- **[MEDIUM-11]** No adapter in the repo uses `@implements(...)`.
  The decorator is declared in the docstring but only the *example*
  uses it; no concrete adapter passes `assert_adapter_compliance`.
  This means the framework's Protocol conformance is *not
  enforced* — adapters may silently violate the Protocol surface.
  **Smallest experiment:** add `@implements(...)` to one adapter
  and call `assert_adapter_compliance` in a CI test. Currently no
  test calls it. **Fix:** Wave 32 follow-up — declare conformance on
  every adapter and add a CI test that calls
  `assert_adapter_compliance` per adapter.

- **[LOW-23]** `emit_theorem1_statement` validates F-side constants
  (eps, d, c, rho, eta) but does NOT call `validate_f_side` —
  only `validate_f_side` (the bare constant check) is used
  implicitly. The dataclass accepts `paper_qty.sheet_A` from the
  caller. **Fix:** document that the caller is responsible for the
  F-side admissibility (already documented line 290-296).

- **[LOW-24]** `PosteriorEvaluator.nu_g_density` is a paper-formula
  accessor but no concrete implementation is provided. The Protocol
  is declared but never consumed. **Fix:** remove the Protocol if
  unused OR document the intended consumer.

#### 1.14 Adapters — restart_blend paths

Three adapters reviewed for `apply_restart_distribution`:

- **`twodim_fm.py:867`** — single-channel linear blend via numpy.
  Memory fraction via `memory_fraction_for(policy, ChannelName("xy"))`.
  Fresh noise via SHA-256-seeded RNG. Blender metadata is fetched
  but not used for math (W1 fix intentional).
- **`lineageflow.py:979`** — categorical blend with row-renormalize.
  Preserves Pfam conditioning hash across restart boundary.
- **`flowmol3_v2_adapter.py:2021`** — channel-aware blend
  (continuous coordinate/charge, categorical raw_pair). 3-channel
  blend math via `_channel_aware_blend`.

Findings:

- **[MEDIUM-12]** All three adapters extract
  `beta_{coord,charge,raw_pair} = policy.beta_by_channel.get(...)`
  with a default of `0.5` when the channel is missing. The
  default of `0.5` (memory_fraction=0.5) is hard-coded. If a
  caller passes a policy with `beta_by_channel = {}` (empty),
  every channel gets the default. ✅ Intentional but undocumented.

- **[LOW-25]** All three adapters compute `restart_seed = int(
  hashlib.sha256(...).hexdigest()[:8], 16)` which truncates to 32
  bits. The truncation is consistent across adapters but the seed
  space is much smaller than uint64. **Fix:** use the full 64-bit
  digest (or document the 32-bit choice).

- **[LOW-26]** `flowmol3_v2_adapter` `_channel_aware_blend` blends
  continuous channels via `m * prior + (1 - m) * fresh` and
  categorical channels via Gumbel/Maxwell-Boltzmann resampling. The
  discrete blend math is in `_channel_aware_blend` and is NOT
  exposed via the blender Protocol. **Fix:** surface the
  categorical blend as a `CategoricalAwareBlender.blend(...)`
  entry-point (already in `categorical_blender.py`).

#### 1.15 Audit tools (4)

- **`tools/capability_audit.py` (1244 lines):**
  - **[LOW-27]** `_parse_pct("-7.28%")` strips `+`/`%` and divides by
    `100`. Negative percentages and decimals work. **Fix:** add a
    test for `+0.5%` (positive decimal).

- **`tools/run_sbc_audit.py` (675 lines):**
  - **[MEDIUM-13]** The script imports `tests/test_sbc/*` via
    `importlib.util.spec_from_file_location` (line 156) which uses
    a `sys.path.insert(0, str(_REPO_ROOT / "tests" / "test_sbc"))`.
    The hack is needed because pytest can't be invoked as a module
    via `python tools/run_sbc_audit.py`. **Fix:** extract the
    simulator/re_inference helpers into a non-test module
    (`adaptive_reflow/sbc_helpers.py`) and import normally.

- **`tools/run_mutation_audit.py` (886 lines):**
  - **[MEDIUM-14]** `_op_weight_perturbation` skips constants in
    `(-1, 0, 1)` (line 227-228) but skips too aggressively when
    the constant `0.5` or `0.95` is meaningful (e.g. the
    `PLANAR_BL_FLOOR_TOLERANCE = 1.5` is targeted but `0.95` for
    `POSTERIOR_SELECTION_CALIBRATION` is skipped as "trivial
    no-op"). **Fix:** document the skip list explicitly.

- **`tools/run_controlled_audit.py` (972 lines):**
  - **[LOW-28]** `_run_twodim_fm` calls
    `self._adapter._batched_integrate_rk4(...)` accessing a
    private method. The `# test seam` comment is missing here.
    **Fix:** add the comment.

---

## 2. Cross-cutting findings

#### 2.1 F-side validation is inconsistent across surfaces

- `paper_quantities.py` does NOT validate `rho < d/4` — that's
  `validation.py`'s job.
- `rate_bound.py` calls `validate_g_admissible` only when
  `enforce_f_side=True` (default).
- `checkers.py:Theorem1StatementChecker` does NOT call
  `validate_g_admissible` — it computes `sheet_evidence_A(g)`
  directly, trusting the caller.

**Smallest experiment:** build
`Theorem1StatementChecker().check(g_violating, [0.1],
paper_qty)` and observe it returns a `Theorem1Statement` whose
`posterior_evidence` may be NaN/zero. Currently the checker does
NOT fail-closed.

**Fix:** add `enforce_f_side` parameter to `Theorem1StatementChecker.check`
mirroring `rate_bound.check_explicit_rate_bound`.

#### 2.2 `record_round_feedback` is silently dropped in 3 places

- `CodimensionSheetScheduler.record_round_feedback` is a no-op
  (HIGH-1).
- `SequentialScheduler.record_round_feedback` does not forward
  `paper_quantities` (MEDIUM-6).
- `batched_runner.run` does not forward `paper_quantities`
  (MEDIUM-8).

This is the same *class* of bug surfaced by F-1 / F-4 / F-5 in
Wave 30 but for a different protocol surface. The fix is a single
PR: extend the runner + sequential scheduler + batched runner to
thread `paper_quantities` everywhere `record_round_feedback` is
called.

#### 2.3 `apply_restart_distribution` is duplicated in 14 adapters

Each adapter implements its own restart-blend math because the
`RestartBlenderProtocol.blend` signature requires `channel_values` /
`native_value` (algorithm-layer abstraction). The W1 fix in
`twodim_fm.py:867` (comment lines 894-916) explicitly chose to keep
the math in the adapter and NOT route through the blender. This
means every new adapter (Wave 21: Kanzi, FreqFlow, MM-FM) re-implements
the same math.

**Fix:** introduce an `apply_restart_blend_to_bundle` helper in
`algorithm/blender.py` that takes `(state_bundle, policy, channel_extractor)`
and returns a fresh `StateBundle` with the same SHA-256-digest
determinism. Then 14 adapters can delegate to it.

#### 2.4 `assert_adapter_compliance` is dead code

The decorator + check function exist but no adapter calls
`@implements(...)` and no CI test invokes `assert_adapter_compliance`.
The Wave 11 framework refactor's intent (Phase 2: Declare Protocol
surfaces) was satisfied but Phase 3 (Shrink adapters — task #344,
still pending) was not.

**Fix:** the simplest 3-line patch is to add `@implements(ChannelwiseBlender)`
to every adapter and assert `assert_adapter_compliance` in a CI test.
This closes the Phase 3 gap.

---

## 3. Test coverage gaps

(Where line/branch coverage is likely < 100% in the audited files.)

| File | Likely untested lines | Smallest experiment |
|------|----------------------|---------------------|
| `paper_quantities.py:248` (zero at endpoint `K`) | F-46 fix is tested in isolation but not in `_paper_evidence_balance` context | Add test: `root_cell_packing_B(g_with_zero_at_K)` |
| `checkers.py:265-270` (planar_witness integration with min(eps_sequence)) | `idx_min = list(report.eps_sequence).index(eps_min)` — works when eps_min is unique; could fail if multiple equal values | Add test: `eps_sequence=[0.1, 0.1, 0.1]` |
| `scheduler/_core.py:2650-2700` (record_round_feedback backward-compat for paper_quantities=None) | Tested implicitly via integration but no isolated unit test | Add `test_record_round_feedback_paper_quantities_none` |
| `batched_runner.py:759-764` (seed derivation with negative n_cap_r) | `int(round(n_cap_r * 1_000_000))` rounds negative values to 0 — but n_cap is always `[0, 1]` | ✅ safe |
| `lipschitz_diagnostic.py:530-537` (greedy fallback) | Not tested; rarely hit | Add test: monkeypatch scipy.optimize.linear_sum_assignment to raise ImportError |
| `framework/interfaces.py:466-487` (implements decorator) | Not tested | Add test: `@implements(Foo) class Bar` sets `__protocols__` |

---

## 4. Documentation gaps

(Functions lacking paper anchors.)

| Function | Missing |
|----------|--------|
| `paper_quantities.py:exterior_gap_e_rho` | The `Lemma 5` line anchor (line 135-138) is referenced but `Lemma 4` (line 110-113) is not — the function applies to both. |
| `checkers.py:sheet_tube_evidence` | The deprecated docstring has no `.. deprecated::` block (RST style). |
| `validation.py:validate_g_admissible` | The `Lemma 5` disjoint-cell guarantee `rho < d/4` is mentioned but the *proof outline* (packing estimate) is not. |
| `blender.py:DistanceDecayBlender` | No paper anchor. The decay factor `sigmoid(-d/temperature)` is a framework heuristic. ✅ Intentional. |
| `batched_runner.py:_w2_to_mode_centres` | No paper anchor — the "W2 surrogate" is a framework heuristic. ✅ Intentional but undocumented. |
| `posterior_selection_evaluator.py:EvidenceScaleGapMetric` | The class docstring says "framework-internal heuristic proxy, NOT a paper claim" but the per-method docstrings don't repeat this. ✅ Sufficient. |

---

## 5. Severity classification

### HIGH

1. **HIGH-1**: `CodimensionSheetScheduler.record_round_feedback` is a no-op
   — see §1.6.
2. **HIGH-2**: `bounded_lipschitz_distance_2d` silent greedy fallback breaks
   paper Theorem 1 contract under no-scipy — see §1.10.
3. **HIGH-4**: `assert_adapter_compliance` silently skips non-`runtime_checkable`
   Protocols — see §1.13.

(Three high-severity issues; HIGH-3 is listed in §1.11 but is
fail-closed-by-design and the iteration cost is acceptable.)

### MEDIUM

- MEDIUM-1 (`paper_selection_ratio` silent `0.0` for `eps=0`)
- MEDIUM-2 (`Theorem1StatementChecker` ignores `paper_qty.sheet_A` for `posterior_evidence`)
- MEDIUM-3 (`PaperRatioAdaptiveScheduler.record_round_feedback` silent on key-mismatch)
- MEDIUM-4 (`ConstantScheduler.sample` doesn't reject out-of-range for `length=1`)
- MEDIUM-5 (`_coerce_memory_fraction(None)` error message lacks provenance)
- MEDIUM-6 (`SequentialScheduler.record_round_feedback` drops `paper_quantities`)
- MEDIUM-7 (`batched_runner` silent `0.0` W2 on empty adapter output)
- MEDIUM-8 (`batched_runner.run` drops `paper_quantities`)
- MEDIUM-9 (`sample_planar_residual_posterior` uses simplified residual)
- MEDIUM-10 (`_flatten_endpoints` error message doesn't name expected permutation)
- MEDIUM-11 (no adapter uses `@implements`; Protocol conformance unenforced)
- MEDIUM-12 (default `beta=0.5` when channel missing is undocumented)
- MEDIUM-13 (`run_sbc_audit.py` sys.path hack)
- MEDIUM-14 (`run_mutation_audit.py` skip list undocumented)

### LOW

- LOW-1 through LOW-28 (28 issues, mostly edge cases, defaults, and
  duplication — see §1 for per-issue details).

### DOCUMENTATION

- DOC-1 through DOC-8 (8 cross-reference / paper-anchor / type-hint
  gaps).

---

## 6. Top 5 recommendations

1. **Thread `paper_quantities` through the runner / sequential /
   codimension-scheduler surface** (HIGH-1 + MEDIUM-6 + MEDIUM-8).
   Single PR; closes the Wave 30 F-1/F-4/F-5 *class* of bugs for the
   `record_round_feedback` protocol surface. Smallest experiment:
   build `BatchedTrajectoryRunner` with `PaperRatioAdaptiveScheduler`
   and observe `_shift` advances after each round.

2. **Enforce Protocol conformance via `@implements` + a CI test**
   (HIGH-4 + MEDIUM-11). Add `@implements(ChannelwiseBlender)` (or
   the smallest relevant Protocol) to every adapter; add a CI test
   that calls `assert_adapter_compliance` for each adapter. This
   closes the Wave 11 Phase 3 gap and prevents the *silent* Protocol
   violations the framework can currently ship.

3. **Raise `ImportError` (not silent fallback) when scipy is
   unavailable for `bounded_lipschitz_distance_2d`** (HIGH-2). The
   current greedy fallback breaks the paper-Theorem-1 contract under
   `scipy`-missing environments. Smallest experiment:
   uninstall scipy, run `planar_bl_convergence_witness`, observe
   the much-larger (greedy) `bl_distance` — currently silent.

4. **Add `apply_restart_blend_to_bundle` helper to
   `algorithm/blender.py`** that takes `(state_bundle, policy,
   channel_extractor)` and returns a fresh `StateBundle` with the
   same SHA-256-digest determinism. Then 14 adapters can delegate
   the W1-fix math to the canonical helper, closing the duplication
   gap (§2.3).

5. **Add must-fail fixtures for the three uncovered theory surfaces**
   (MEDIUM-2, LOW-4, LOW-19). Specifically: (a)
   `Theorem1StatementChecker` with `paper_qty.sheet_A` that disagrees
   with `sheet_evidence_A(g)`; (b) `validate_g_admissible` with a
   profile whose zeros are all outside `[-sim_K, sim_K]`; (c)
   `_scale_cell_evidence` with `eps=0` and `apply_lemma4=True`.

---

## 7. Files audited + changes proposed

| File | Lines | Severity | Recommendation |
|------|-------|----------|----------------|
| `theory/paper_quantities.py` | 774 | LOW-1, MEDIUM-1, DOC-1 | Add K=32 fixture, document eps=0, extract helper |
| `theory/checkers.py` | 525 | MEDIUM-2, LOW-2, DOC-2 | Document precedence, add monotone tol, emit DeprecationWarning |
| `theory/validation.py` | 252 | LOW-3, LOW-4, DOC-3 | Add must-fail for sim_K window + c=0 |
| `theory/rate_bound.py` | 199 | LOW-5, DOC-4 | Cross-ref `PLANAR_BL_FLOOR_TOLERANCE` |
| `theory/lemma2_checker.py` | 155 | LOW-6, DOC-5 | Extract LOG_P_TAIL_THRESHOLD, add paper line 142-144 |
| `algorithm/scheduler/_core.py` | 4353 | HIGH-1, MEDIUM-3, MEDIUM-4, LOW-7..9, DOC-6 | Add paper-quantity feedback to codimension; thread paper_quantities through sequential; validate round_in_cycle for length=1 |
| `algorithm/blender.py` | 789 | MEDIUM-5, LOW-10..11, DOC-7 | Add provenance to error, document strict=True |
| `algorithm/sequential.py` | 521 | MEDIUM-6, LOW-12..13 | Forward paper_quantities kwarg |
| `algorithm/batched_runner.py` | 949 | MEDIUM-7, MEDIUM-8, LOW-14..15 | Forward paper_quantities, raise on empty flat |
| `eval/lipschitz_diagnostic.py` | 747 | HIGH-2, MEDIUM-9, LOW-16..17, DOC-8 | Raise ImportError without scipy, extract LOG_P constants |
| `eval/posterior_selection_evaluator.py` | 1205 | MEDIUM-10, LOW-18..19 | Better error message, fail-fast on empty _native_states |
| `eval/twodim_fm_evaluator.py` | 612 | LOW-20..22 | Cache KDTree, document +1 seed offset |
| `framework/interfaces.py` | 522 | HIGH-4, MEDIUM-11, LOW-23..24 | Enforce runtime_checkable, add `@implements` everywhere |
| `adapters/twodim_fm.py` | ~1100 | MEDIUM-12, LOW-25 | Document default beta, document seed truncation |
| `adapters/flowmol3_v2_adapter.py` | ~2200 | MEDIUM-12, LOW-25..26 | Same; surface CategoricalAwareBlender |
| `adapters/lineageflow.py` | ~1200 | MEDIUM-12, LOW-25 | Same |
| `tools/capability_audit.py` | 1244 | LOW-27 | Add positive-decimal test |
| `tools/run_sbc_audit.py` | 675 | MEDIUM-13 | Move helpers out of tests/ |
| `tools/run_mutation_audit.py` | 886 | MEDIUM-14 | Document skip list |
| `tools/run_controlled_audit.py` | 972 | LOW-28 | Add test seam comment |

---

## 8. Verification

**No code changes were made by Wave 32 Agent C.** This is a
READ-ONLY audit. The recommendations above are the smallest-experiment
+ fix proposal set; a follow-up Wave 32 Agent D (or Wave 33) can
adopt them in priority order.

**Tests run:** none (read-only audit).

**Commits made:** none in this audit; the doc itself is committed
as the single deliverable.

---

## 9. Notes

- The DPK45 fix (Wave 20) is verified clean — no related issues in
  the audit scope.
- The F-1 (sheet_tube_evidence residual) fix is verified clean.
- The F-4 (`selection_ratio` rename) fix is verified clean.
- The F-5 (operating-regime limitation) limitation is documented in
  ADR-0017 and `operating-regime.md`.
- The Phase 3 task #344 ("Shrink adapters") remains pending; the
  Recommendation 4 in §6 directly closes this gap.