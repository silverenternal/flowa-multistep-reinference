# Phase-4 docstring audit surface

> **Author:** Agent F4 (Phase-4 follow-up; documentation only)
> **Date:** 2026-08-31
> **Source audit:**
> [`../r4-survey/18-comprehensive-code-review.md`](../r4-survey/18-comprehensive-code-review.md)
> §5.5 (documentation drift), §6.6 (audit-code vocabulary sprawl),
> F-11, F-12, F-23, F-40, F-41.
> **Status:** READ-ONLY audit of docstring coverage. No code changes.
> Each entry records a module + the missing-or-stale docstring surface
> the Phase-4 audit identified, plus the recommended remediation that a
> future code-review pass should land.

---

## §1. Method

The Phase-4 audit walked the algorithm layer, adapters, runner,
engine, evaluators, paper quantities, state machines, and contracts
surface. For each module the audit checked:

1. **Module-level docstring** — does the file open with a numpydoc /
   google-style summary that names the module's role in the
   framework?
2. **Public surface docstrings** — does every Protocol method or
   `__init__` on a public class carry a docstring that names
   parameters, return type, and the audit invariants the method
   upholds?
3. **Audit-code vocabulary** — does the docstring enumerate the
   audit codes the module can emit? (Audit-code vocabulary sprawl is
   a §6.6 finding.)
4. **Cross-references** — does the docstring point at the relevant
   CLM-NNN claim, ADR, and regression test?

The Phase-4 audit flagged the modules below as missing-or-stale on
one or more of those axes. The flag column reads `MISSING` (no
docstring at all), `STALE` (docstring present but contradicts the
current code), `THIN` (docstring present but lacks parameters /
audit codes / cross-references), or `MISLEADING` (docstring makes a
claim the audit refuted).

---

## §2. Module-by-module table

| # | Module | Line | Flag | Docstring axis | Recommended remediation |
|---|---|---:|---|---|---|
| 1 | `adaptive_reflow/algorithm/merge_operator_v3.py` | 1-50 | THIN | module-level | Add numpydoc module docstring naming `MeanFlowMergeOperator`'s role as a plug-in `MergeOperatorProtocol` (arXiv:2505.13447) and the per-method audit-code vocabulary. |
| 2 | `adaptive_reflow/algorithm/merge_operator_v3.py` (`MeanFlowMergeOperator.merge`) | 240-300 | THIN | public surface | Document the `_prev_dynamic` update ordering (F-19), the `[0,1]`-then-`[floor,cap]` re-clip behaviour (F-21), and the missing `reset()` method (F-20). |
| 3 | `adaptive_reflow/algorithm/merge_operator.py` (`BoundedMergeOperator`) | 254-260 | STALE | public surface | The `MergeOperatorProtocol` docstring still claims "MUST return a finite `float` ... MUST NOT raise on ... `cap < floor`" — refuted by F-18. Update once the P0-3 fix lands (and per `CLM-042` the same commit must update `CLM-025`). |
| 4 | `adaptive_reflow/algorithm/merge_operator.py` (`BoundedMergeOperator.tolerance`) | 386-392 | STALE | public surface | Document that `tolerance` is accepted but has no observable effect (F-23). Either remove the field or implement the near-degenerate warning. |
| 5 | `adaptive_reflow/algorithm/merge_operator.py` (`EMAOperator.schedule_weight`) | 807-821 | THIN | public surface | Document the `alpha` over-range modulation behaviour (F-22) and the defensive `[0,1]` clip that hides the bug. |
| 6 | `adaptive_reflow/algorithm/scheduler/freetraj.py` (`FreeTrajScheduler._compute_trajectory_progress`) | 308-321 | STALE | public surface | Docstring claims the cache advances with `record_round_feedback`; the implementation caches unconditionally (F-1). Update once P0-2 lands. |
| 7 | `adaptive_reflow/algorithm/scheduler/_core.py` (`CodimensionSheetScheduler.record_round_feedback`) | 2816-2822 | THIN | public surface | Document the no-op semantics (F-5) and the planned C4-style uplift. |
| 8 | `adaptive_reflow/algorithm/scheduler/_core.py` (`ConvergenceAdaptiveScheduler.sample`) | 1927-1935 | STALE | public surface | Document the `schedule_family` precondition for the cosine re-derivation (F-4) — raise `NotImplementedError` for non-cosine base. |
| 9 | `adaptive_reflow/algorithm/scheduler/_core.py` (`_paper_evidence_balance`) | 2257-2264 | STALE | internal helper | Document the unreachable `denom <= 0.0` fallback (F-11) or remove it (the closed form's input validation rules it out). |
| 10 | `adaptive_reflow/algorithm/scheduler/_core.py` (`CosineScheduleConfig.frozen_before_evaluation`) | 562 | STALE | dead config | The field is set in every factory but never read (F-12). Remove or wire to the engine's pre-round evaluation freeze check. |
| 11 | `adaptive_reflow/algorithm/scheduler/evidence_driven.py` (`EvidenceDrivenScheduler.config_hash`) | 402-417 | STALE | public surface | Document the missing `k_eps` and `eps_implicit_base` digest inputs (F-2); add a `test_evidence_driven_config_hash_varies_with_k_eps` regression. |
| 12 | `adaptive_reflow/algorithm/scheduler/evidence_driven.py` (`EvidenceDrivenScheduler.sample`) | 338-346 | THIN | public surface | Document the round-lag semantics of `_last_pid_delta` (F-3) — round `r` uses round `r-1`'s evidence ratio by construction; the audit code should carry the annotation. |
| 13 | `adaptive_reflow/algorithm/runner.py` (`ReInferenceRunner.run` merge bypass) | 672-686 | STALE | public surface | Document the `schedule_derived` merge bypass (F-31); remove the bypass once P0-1 lands (the bounded merge collapses to the same value for `delta_cap=1.0`, so the call is free). |
| 14 | `adaptive_reflow/algorithm/runner.py` (`ReInferenceRunner.run` endpoint reshape) | 832-858 | STALE | public surface | Document the `.reshape(2)` hard-code (F-24) and the `adapter.state_shape` lookup; replace with `arr[-1].reshape(adapter.state_shape)`. |
| 15 | `adaptive_reflow/algorithm/runner.py` (`ReInferenceRunner.run` record_round_feedback) | 620-1000 | THIN | public surface | Document the missing `record_round_feedback` call (F-32) — the runner never feeds `metric` back into the scheduler, breaking Loop 2 outside the harness. |
| 16 | `adaptive_reflow/algorithm/runner.py` (`ReInferenceRunner.run` state-machine reset) | 600-1000 | THIN | public surface | Document the missing `_state_machine.reset()` call between runs (F-33). |
| 17 | `adaptive_reflow/eval/mnist_fid.py` (`MnistFidEvaluator`) | 154-264 | MISLEADING | public surface | Rename to `MnistFrechetProjectionEvaluator` (F-40); document that the evaluator computes Fréchet distance on a random linear projection of pixel space, NOT canonical FID. |
| 18 | `adaptive_reflow/eval/w2.py` (`ModeCentreMSEW2`) | 253-295 | MISLEADING | public surface | Document that this is NOT a Wasserstein distance (F-41); the runner's metric key should carry the estimator family. |
| 19 | `adaptive_reflow/eval/w2.py` (`ProjectionFreeExactW2`) | 302-440 | THIN | public surface | Document the quantile interpolator (F-42) — pin to `np.quantile(..., method='linear')` for byte-determinism across numpy versions. |
| 20 | `adaptive_reflow/eval/coverage.py` (`CoverageEvaluator`) | (file) | THIN | public surface | Add `config_hash()` and `to_config()` methods (F-43) following the W2-estimator pattern. |
| 21 | `adaptive_reflow/contracts/paper_quantities.py` (`sheet_evidence_A.discretization_error`) | 338 | STALE | result dataclass | Document the rough trapezoidal error bound (F-45) — replace with the exact second-derivative bound. |
| 22 | `adaptive_reflow/contracts/paper_quantities.py` (`root_cell_packing_B`) | 212-229 | STALE | public surface | Document the missed zero at `x=K` (F-46) — add an explicit post-loop `if ys[-1] == 0.0` guard. |
| 23 | `adaptive_reflow/contracts/paper_quantities.py` (`per_cell_coefficient_C`) | 265-275 | THIN | public surface | Document the silent `c`-clip (F-47) — `min(c*c, 1.0)` caps `c` at 1 without a warning. |
| 24 | `adaptive_reflow/contracts/paper_quantities.py` (`exterior_gap_e_rho`) | 307-311 | THIN | public surface | Document the near-zero-floor risk (F-48) — when `e_rho < 1e-4` the codim scheduler's `noise_mass` floor is effectively zero. |
| 25 | `adaptive_reflow/contracts/state_machine.py` (parallel fallback) | 752-773 | THIN | internal helper | Document the no-region-handled parallel fallback (F-49) — emit a `parallel_no_region_handled` log entry. |
| 26 | `adaptive_reflow/contracts/state_machine.py` (priority tie-break) | 813-820 | THIN | internal helper | Document the registration-order tie-break (F-50) — switch to a stable secondary key (transition's target state). |
| 27 | `adaptive_reflow/contracts/state_machine.py` (`with_strict_guards`) | 425-426 | THIN | public surface | Document the silent-disable behaviour (F-51) — emit an audit log entry when a guard rejects even in non-strict mode. |
| 28 | `adaptive_reflow/contracts/state_machine.py` (`TransitionLog`) | 134-178 | THIN | result dataclass | Add an explicit `__hash__` method (F-52) that hashes only the `(state, event, source, target)` tuple. |
| 29 | `adaptive_reflow/contracts/authority.py` (`hash_policy_hash`) | (file) | THIN | helper | Document the missing `driver_computed_beta` digest input (F-53). |
| 30 | `adaptive_reflow/contracts/authority.py` (`validate_final_restart_policy`) | (file) | THIN | validator | Document the missing `ChannelName` key check (F-56). |
| 31 | `adaptive_reflow/frame/engine.py` (`run_round` `_policy_with_schedule_beta`) | 770-814 | STALE | internal helper | Document the inline override path (F-36) and the runner's `driver_computed_beta=True` flag that suppresses it; consolidate to one source of truth. |
| 32 | `adaptive_reflow/frame/engine.py` (`run_round` audit order) | 939-1014 | THIN | internal helper | Document the canonical audit-code ordering (F-38) — capability → bundle → policy → integrator → endpoint. |
| 33 | `adaptive_reflow/frame/orchestrator.py` (`AdaptiveReflowPolicyOrchestrator.merge_operator`) | 300-432 | THIN | public surface | Document the missing `MergeOperatorProtocol` validation (F-35). |
| 34 | `adaptive_reflow/frame/orchestrator.py` (`reset_cycle`) | 1139 | THIN | public surface | Document the missing `_last_bounded_fraction` reset between cycles (F-39). |
| 35 | `adaptive_reflow/adapters/twodim_fm.py` (`TwoDimFMAdapter.inject_forward_noise`) | 469-1182 | MISSING | public surface | Implement the missing `inject_forward_noise` hook (F-25); the runner sets `forward_noise_emitted=True` for all adapters but only CIFAR and MNIST implement the hook. |
| 36 | `adaptive_reflow/adapters/rectified_flow_cifar.py` (`inject_forward_noise`) | 997-1051 | THIN | public surface | Document the shape precondition (F-27) — `if np.asarray(injected).shape != RF_CIFAR_STATE_SHAPE: raise ValueError(...)`. |
| 37 | `adaptive_reflow/adapters/reference_flowa.py` (`export_trajectory`) | 303-318 | THIN | public surface | Document the `NotImplementedError` (F-26) — the engine should emit a separate `ENDPOINT_EXPORT_NOT_IMPLEMENTED` audit code for this case. |

---

## §3. Audit-code vocabulary (cross-reference surface)

The Phase-4 audit (§6.6) flagged the audit-code vocabulary as a sprawl
without a central registry. The 37 modules above emit ~30 distinct
audit codes (`BETA_SATURATION_FROM_PAPER_QUANTITY`,
`FORWARD_NOISE_INJECTED`, `MERGE_DEGENERATE_INTERVAL`,
`MERGE_PAPER_QUANTITY_FLOOR_LIFTED`, `MERGE_NONFINITE_PREV_CLIPPED`,
`MERGE_NONFINITE_DYNAMIC_CLIPPED`, `MERGE_CAP_OUT_OF_RANGE`,
`MERGE_FLOOR_OUT_OF_RANGE`, `MEANFLOW_DECOMPOSITION_AUDIT`,
`MEANFLOW_PAIR_INVALID`, `ERR_CAPABILITY_UNSUPPORTED`,
`ERR_SCHEDULE_SAMPLE_MISSING`, ...). A future code-review pass should
publish an `AUDIT_CODE_REGISTRY` in `adaptive_reflow.contracts.audit`
so the audit trail is enumerable; until then this table is the
canonical cross-reference surface for a reader trying to enumerate the
vocabulary from the source.

---

## §4. Action items (no code changes — READ-ONLY audit)

The Phase-4 audit + fix plan is documentation only. The 37 entries in
§2 each carry a "Recommended remediation" column that the next
code-review pass should land. Until then:

- `tools/check_claims_consistency.py` exits clean (no drift).
- `tools/check_docs_against_code.py` exits clean (no doc-claim drift).
- The audit + fix plan live in `docs/r4-survey/18-*.md` and
  `docs/r4-survey/19-*.md`.
- `CLM-041` records the bug count, `CLM-042` records the
  `CLM-025` doc-drift risk, `CLM-043` records the docstring audit
  surface (this file).

---

## §5. References

- `docs/r4-survey/18-comprehensive-code-review.md` — the canonical
  audit (52 bugs, severity 1-5).
- `docs/r4-survey/19-fix-plan.md` — the canonical fix plan (7 P0,
  15 P1, 30 P2).
- `docs/CLAIMS.md` — `CLM-041` (Phase-4 audit), `CLM-042` (CLM-025
  doc-drift risk), `CLM-043` (this audit surface).
- `tools/check_claims_consistency.py` — the verifier that auto-
  promotes a claim to `PROVISIONAL` when its `Disputed by` reference
  is present (relevant for `CLM-025` after P0-3 lands).
