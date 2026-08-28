# Algorithm Uplift Plan

Survey of every algorithm in `adaptive_reflow/algorithm/`,
`adaptive_reflow/eval/posterior_selection_evaluator.py`, and
`adaptive_reflow/contracts/paper_quantities.py`. Each entry lists
current capability / limitation, then concrete uplifts split into
framework-driving (better hooks for the runner / engine / audit
ledger) and algorithmic (better math, lower variance, closer to paper
Theorem 1). Quantitative targets and the test that proves them are
mandatory.

References:

- Paper: `NoiseSelectedRectification_EN.md` (Li 2024) — Theorem 1
  (`mu_{g,eps} --BL--> nu_g`), Lemma 2 (`eps^{-1} int_T phi p_eps
  -> A_g`), Lemma 3 (`int_{I_z} p_eps <= C_g e^{-z^2/4} eps^2`),
  Lemma 4 (`int_{T^c \setminus cells} p_eps <= e^{-e_rho/(2 eps^2)}`),
  Lemma 5 (`sum_z e^{-z^2/4} < infty`), Proposition 3 (`Z_{g,eps}
  >= C_1 eps`), Proposition 5 (compact containment).
- Ablation baseline: `docs/ABLATION.md` (22 rows, current
  `final_W2 = 0.8691` on two_moons for cosine, `0.7591` for
  `multi_round_no_restart` on eight_gaussians; selection_ratio
  plateaus at `0.8061` on two_moons).
- Engine hooks: `verify_ledger_chain` (P0-8),
  `Engine.run_round` (P0-7 forward-noise + merge step), paper-quantity
  re-wiring in `runner._apply_paper_quantities_rewiring`.

---

## 1. Schedulers

### 1.1 CosineAnnealScheduler

| Algorithm | Current | Limitation | Uplift | Quantitative Target | Test |
|---|---|---|---|---|---|
| CosineAnnealScheduler | Closes `n_cap_for_round`; pure; `inject_noise` uses `sqrt(n_cap)`; `config_hash` captures family + cycle_length + n_min/n_max + seed. | `ScheduleSample` carries no audit code (just `schedule_hash`); engine has no way to identify which family was sampled. | **A1** Add `audit_codes: tuple[str, ...]` field to `ScheduleSample` (`scheduler.py:84`) so runner/engine can fan out the round's per-round diagnostic without re-deriving it. | New field present on 100% of samples; engine consumes it in 100% of rounds when set; no byte-breakage for `ScheduleSample` equality. | `tests/test_algorithm/test_scheduler.py::test_cosine_sample_carries_audit_codes` |
| CosineAnnealScheduler | Default closed-form is correct; no paper-quantity tie-in. | The scheduler doesn't know `A_g` or `eps_implicit` so its `inject_noise` uses raw `n_cap` instead of the paper's selection-driven noise mass. | **A2** Wire `paper_quantities.sheet_evidence_A(g)` into `CosineAnnealScheduler` (optional `profile_residual_fn` arg, `scheduler.py:281`) — when present, `inject_noise` scales by `sqrt(A_g)` matching CodimensionSheetScheduler. | Selection ratio SNR rises 5% on two_moons vs. baseline when wired; bit-identical for callers that don't supply a profile. | `tests/test_algorithm/test_scheduler.py::test_cosine_paper_quantity_wiring` |
| CosineAnnealScheduler | `config_hash` is a SHA-256 of family + cycle_length + n_min + n_max + seed. | Doesn't include `schedule_family` (a string alias like `"cosine_no_restart"`), so two schedulers with different `schedule_family` strings share a hash. | **B1** Fold `schedule_family` into `config_hash` (`scheduler.py:330`) — the family name is already on the input config but is omitted from the digest payload. | Two schedulers differing only in `schedule_family` produce different `config_hash`; existing byte-identical round-trip preserved. | `tests/test_algorithm/test_scheduler.py::test_cosine_config_hash_distinguishes_family` |

### 1.2 ConstantScheduler

| Algorithm | Current | Limitation | Uplift | Quantitative Target | Test |
|---|---|---|---|---|---|
| ConstantScheduler | Reference baseline; `n_cap` constant per round; `inject_noise` uses configured `n_cap`. | Sits at `0.5` (mid-cycle marker) but doesn't emit the constant-marker to the audit trail. | **A3** Append `audit_codes=("schedule_constant_baseline",)` to `ScheduleSample` (`scheduler.py:584`) so the audit ledger shows the round used the constant baseline (and downstream selection_ratio replay can mark it). | Engine reads the code; ledger row carries it on every round. | `tests/test_algorithm/test_scheduler.py::test_constant_audit_code` |
| ConstantScheduler | `n_cap` defaults to `0.5`. | The `memory_fraction = 0.5` anchor is implicit — callers can't read it from the API. | **B2** Expose `memory_fraction_baseline` as a property (`scheduler.py:548`); closes the gap to `ADR-0010`'s "memory_fraction = 1 - n_cap". | Property returns `0.5` for default; changes linearly with `n_cap`; no regression in `sample()` output. | `tests/test_algorithm/test_scheduler.py::test_constant_memory_fraction_baseline` |

### 1.3 LinearScheduler

| Algorithm | Current | Limitation | Uplift | Quantitative Target | Test |
|---|---|---|---|---|---|
| LinearScheduler | Closed-form `n_max - (n_max - n_min) * u_r`. | No `inject_noise` direction variant (only `n_cap` ramp). | **A4** Add `direction: str = "ramp_down"` knob (`scheduler.py:688`); when `"ramp_up"`, `inject_noise` scales by `sqrt(n_max)` instead of `sqrt(n_cap)` so the noise mass sits at the schedule's peak. | Engine consumes the override; round-trip equality preserved. | `tests/test_algorithm/test_scheduler.py::test_linear_inject_noise_direction` |
| LinearScheduler | Single ramp. | No `audit_codes` field. | **A5** Inherit the new `audit_codes` field from **A1** (same line). | Same as A1. | Same as A1. |

### 1.4 ExponentialScheduler

| Algorithm | Current | Limitation | Uplift | Quantitative Target | Test |
|---|---|---|---|---|---|
| ExponentialScheduler | `n_cap(r) = n_max * exp(-alpha * r)`; clip to `[0, 1]`. | No `inject_noise` uses an explicit `alpha`-scaled variance; falls back to `sqrt(n_cap)` only. | **B3** Add `noise_floor: float = 0.0` constructor arg (`scheduler.py:908`); `inject_noise` returns `state + sqrt(n_cap + noise_floor) * noise`. | Two schedulers with different `noise_floor` produce different `inject_noise` outputs; `noise_floor=0` matches legacy output byte-for-byte. | `tests/test_algorithm/test_scheduler.py::test_exponential_noise_floor` |
| ExponentialScheduler | High-variance in early rounds when `alpha` is small. | No analytic mean / variance for the `n_cap` sequence. | **B4** Compute `expected_n_cap = n_max / alpha * (1 - exp(-alpha * L)) / L` and stash on `last_sample` (extend dataclass) so the runner can report schedule-mean to the audit ledger. | Mean estimate within `1e-6` of the analytic integral; runner emits `schedule_n_cap_mean` per round. | `tests/test_algorithm/test_scheduler.py::test_exponential_expected_n_cap` |

### 1.5 PolynomialScheduler

| Algorithm | Current | Limitation | Uplift | Quantitative Target | Test |
|---|---|---|---|---|---|
| PolynomialScheduler | `n_cap(r) = n_min + (n_max - n_min) * (1 - u_r ** power)`; clip `[0, 1]`. | `power=2` concave ramp front-loads exploration — there's no `power=0.5` convex preset exposed. | **C1** Add `preset: Literal["linear","convex_05","concave_2","concave_3"]` arg (`scheduler.py:1133`) that maps to canonical `(n_min, n_max, power)` triples; closes the ablation's lack of "convex ramp" row. | New preset produces a row in the ablation; convex ramp `power=0.5` reports lower `final_W2` on `eight_gaussians` than concave (`power=2`) by >=5%. | `tests/test_algorithm/test_scheduler.py::test_polynomial_convex_preset` + ablation row added. |

### 1.6 SigmoidScheduler

| Algorithm | Current | Limitation | Uplift | Quantitative Target | Test |
|---|---|---|---|---|---|
| SigmoidScheduler | `sigmoid(steepness * (u_r - midpoint))`; near-step at midpoint. | No early-start knob — when `midpoint=0.5`, the first half of the cycle stays at `n_min`. | **B5** Add `tail_floor: float = 0.0` (defaults to `n_min`) so the early rounds can lift the floor without losing the steep transition. | A `tail_floor=0.1` row reports `final_coverage` lift >= 0.125 on `eight_gaussians` vs. the `tail_floor=0` baseline. | `tests/test_algorithm/test_scheduler.py::test_sigmoid_tail_floor` + ablation row. |

### 1.7 ConvergenceAdaptiveScheduler

| Algorithm | Current | Limitation | Uplift | Quantitative Target | Test |
|---|---|---|---|---|---|
| ConvergenceAdaptiveScheduler | PID-lite: `shift = kp * (1 - ratio) - kd * delta`, EMA on `W2`. | W2 feedback is the only signal; ignores `coverage`, `selection_ratio`, paper quantities. | **A6** Extend `record_round_feedback` to accept a `dict[str, float]` (`scheduler.py:1848`); index by metric name (`"W2"`, `"coverage"`, `"selection_ratio"`) and route to per-metric shifts with default weights `1.0`, `0.3`, `0.5`. | Adding `coverage` and `selection_ratio` to feedback reduces `final_W2` by >= 5% on `eight_gaussians` vs. W2-only. | `tests/test_algorithm/test_scheduler.py::test_convergence_adaptive_multi_metric` |
| ConvergenceAdaptiveScheduler | EMA is `alpha * new + (1-alpha) * prev`. | No variance reduction beyond EMA (no Kalman-style prior). | **B6** Add `kalman_like: bool = False` flag (`scheduler.py:1664`); when set, shift update uses `sigma2_prev / (sigma2_prev + sigma2_obs)`-style weighting. | Variance of `_shift` over 20-round trajectory drops by >= 30% on a deterministic oracle replay. | `tests/test_algorithm/test_scheduler.py::test_convergence_adaptive_kalman_like` |

### 1.8 CodimensionSheetScheduler

| Algorithm | Current | Limitation | Uplift | Quantitative Target | Test |
|---|---|---|---|---|---|
| CodimensionSheetScheduler | Wires paper quantities (`A_g`, `B_g`, `C_g`, `e_rho`) when `profile_residual_fn` is supplied; reports `last_evidence_ratio` (`scheduler.py:2401`). | `last_evidence_ratio` is a *reportable* metric, not consumed by the runner/engine — runner only sees `n_cap`. | **A7** Extend `ScheduleSample` (via **A1**) with `evidence_ratio: float` so runner/engine can branch on the sheet-vs-cell balance without a second `scheduler.last_evidence_ratio` read. | Runner reads `sample.evidence_ratio` directly; codimension row's `selection_ratio` matches `sample.evidence_ratio` within `1e-6`. | `tests/test_algorithm/test_scheduler.py::test_codimension_sample_evidence_ratio` |
| CodimensionSheetScheduler | Collapses to cosine when `profile_residual_fn` is `None`. | Falls back to the framework heuristic; ablation shows it's identical to cosine. | **B7** Add `profile_residual_fn: Callable[[float], float]` as a *required* (not optional) argument and remove the inline-heuristic path. Migrate callers in `runner._apply_paper_quantities_rewiring` to always supply one. | Ablation `codimension_sheet_posterior_selection` row shows a real `delta_selection_ratio` vs. cosine (currently `0.0000`). | `tests/test_algorithm/test_scheduler.py::test_codimension_requires_profile` |

---

## 2. SequentialScheduler

| Algorithm | Current | Limitation | Uplift | Quantitative Target | Test |
|---|---|---|---|---|---|
| SequentialScheduler | Chained `(scheduler, n_rounds)` slots; config_hash covers every sub-scheduler's hash. | `record_round_feedback` only forwards to the *active* sub-scheduler; inactive sub-schedulers never see feedback. | **A8** Modify `record_round_feedback` (`sequential.py:287`) to forward to *all* sub-schedulers (active + inactive) with `round_in_cycle` clamped to the slot's range, so chained adaptive schedulers can warm up before their slot starts. | Adaptive-chained row's `final_W2` drops >= 10% vs. naive forwarding on `eight_gaussians`. | `tests/test_algorithm/test_sequential.py::test_sequential_feedback_to_all_slots` |
| SequentialScheduler | `inject_noise` falls back to `slot[0]` when out-of-range. | Silent fallback hides caller mis-wiring. | **A9** Replace silent fallback with an `audit_codes` entry (`sequential.py:307`) so the audit ledger records `seq_inject_noise_fallback` when the chain's total length is shorter than the caller's `computed_at_round`. | Ledger row carries the code on every fallback; `verify_ledger_chain` still passes. | `tests/test_algorithm/test_sequential.py::test_sequential_inject_noise_fallback_audit` |

---

## 3. Policy Drivers

| Algorithm | Current | Limitation | Uplift | Quantitative Target | Test |
|---|---|---|---|---|---|
| ScheduleDerivedPolicyDriver | `beta = n_cap`; ignores `prior_endpoint_digest` and `audit_codes`. | Doesn't expose a per-round `audit_codes` (no saturation / clipping to surface). | **A10** Append `audit_codes=("policy_schedule_derived",)` to the returned policy's `provenance` so engine's audit trail attributes the policy. | Ledger row carries the code on every round. | `tests/test_algorithm/test_policy_driver.py::test_schedule_derived_audit_code` |
| ConstantPolicyDriver | `beta = constant`; no per-round adaptation. | Default `0.5` doesn't reflect the paper's `e_rho` minimum-energy floor (Lemma 5). | **B8** Add `min_floor: float = 0.0` constructor arg (`policy_driver.py:412`); the driver's `beta = max(configured, min_floor)` so callers can pin a paper-aligned floor. | Driver with `min_floor=0.05` reduces `final_W2` by >= 5% on `eight_gaussians`. | `tests/test_algorithm/test_policy_driver.py::test_constant_min_floor` |
| AdaptivePolicyDriver | `beta = (1 - |p - t|) / C_g`; C_g-driven saturation when `< 1`. | Saturation audit code `BETA_SATURATION_FROM_PAPER_QUANTITY` carries only the raw value; no count of saturated rounds. | **A11** Extend `compute_policy` (`policy_driver.py:646`) to emit a per-call counter `BETA_SATURATION_FROM_PAPER_QUANTITY:count` aggregated across rounds (sticky on the runner). | Runner's `per_round_metrics` includes `beta_saturation_count` summing saturated rounds; final value >= 1 when C_g < 1. | `tests/test_algorithm/test_policy_driver.py::test_adaptive_saturation_counter` |
| All drivers | `config_hash` captures family + scalar args. | Doesn't include `policy_id` (a free-form string callers may want). | **C2** Add optional `name: str` arg to all drivers (default `""`); fold into `config_hash` (`policy_driver.py:720`). | Two drivers with different `name` produce distinct hashes; `name=""` matches legacy. | `tests/test_algorithm/test_policy_driver.py::test_driver_config_hash_includes_name` |

---

## 4. Merge Operators

| Algorithm | Current | Limitation | Uplift | Quantitative Target | Test |
|---|---|---|---|---|---|
| BoundedMergeOperator | `clamp(dynamic, [floor, prev - down], [cap, prev + up])`; clip-and-audit on degenerate intervals. | `tolerance` knob is accepted but unused (reserved). | **B9** Implement near-degenerate handling (`merge_operator.py:387`): when `hi < lo + tolerance`, return the midpoint of `(lo, hi)` clipped to `[0, 1]` and append `MERGE_NEAR_DEGENERATE:tolerance`. | `tolerance=1e-3` row's `final_W2` drops by >= 3% on `eight_gaussians` vs. `tolerance=0` baseline. | `tests/test_algorithm/test_merge_operator.py::test_bounded_tolerance_used` |
| BoundedMergeOperator | No paper-quantity tie-in. | The envelope `cap / floor` is schedule-supplied, but the paper's `e_rho` (Lemma 5) is not folded into the floor. | **A12** Add optional `exterior_gap_e_rho: float \| None` arg (`merge_operator.py:386`); when set, `floor = max(floor, e_rho / 4)` to enforce paper Lemma 5's exterior-gap floor. | Runner-driven row with paper-quantity wiring reports `final_W2` drop >= 2% on `two_moons`. | `tests/test_algorithm/test_merge_operator.py::test_bounded_paper_quantity_floor` |
| IdentityOperator | Pass-through `dynamic`. | Doesn't forward `merge_audit_codes` even when `dynamic` is non-finite. | **A13** Inherit the new `audit_codes` contract (`merge_operator.py:584`) by emitting `MERGE_NONFINITE_DYNAMIC_CLIPPED` on every call where `dynamic` was clipped. | Ledger row carries the code when `dynamic` is `nan`; byte-identical when `dynamic` is in `[0, 1]`. | `tests/test_algorithm/test_merge_operator.py::test_identity_emits_finiteness_code` |
| EMAOperator | `prev + alpha * (dynamic - prev)`; alpha fixed default `0.1`. | No `alpha` schedule — `alpha=0.1` for every round. | **B10** Add `alpha_schedule: Callable[[int], float] \| None` arg (`merge_operator.py:613`); when set, `alpha_t = alpha_schedule(round_in_cycle)`. Default `lambda r: self._alpha`. | Row with `alpha_schedule=lambda r: 0.05 + 0.1 * r / L` reduces `final_W2` >= 5% on `eight_gaussians`. | `tests/test_algorithm/test_merge_operator.py::test_ema_alpha_schedule` |

---

## 5. Restart Blenders

| Algorithm | Current | Limitation | Uplift | Quantitative Target | Test |
|---|---|---|---|---|---|
| LinearBlender | `m * prior + (1 - m) * fresh`; canonical convex combination. | The `memory_fraction` is clipped but no audit code is emitted when clipped. | **A14** Add `audit_codes` arg to `blend` (`blender.py:455`); append `BLENDER_MEMORY_FRACTION_CLIPPED` when input was outside `[0, 1]`. | Ledger row carries the code on clipped inputs; byte-identical when input is in `[0, 1]`. | `tests/test_algorithm/test_blender.py::test_linear_audit_code_on_clip` |
| LinearBlender | One-shot linear interpolation. | No paper-quantity tie-in (e.g. `C_g`-scaled `m`). | **B11** Add optional `per_cell_coefficient_C: float \| None = None` arg (`blender.py:447`); when set, `m_eff = m ** (1 / C_g)` so the memory fraction lives on paper Lemma 3's per-cell evidence scale. | Driver wired to `C_g` reports a tighter `final_W2` by >= 3% on `eight_gaussians`. | `tests/test_algorithm/test_blender.py::test_linear_paper_quantity_scaling` |
| DistanceDecayBlender | `decay = sigmoid(-||p - f|| / T)`; fresh-noise gating. | Temperature defaults to `1.0` but is folded into per-call digest, not the audit trail. | **A15** Append `decay_factor` to `provenance` (already on `native_state_digest`); expose it in the runner's `per_round_metrics["blender_decay_factor"]`. | Runner-driven row reports `decay_factor` per round; mean across rounds within `[0.05, 0.95]`. | `tests/test_algorithm/test_blender.py::test_distance_decay_metric_emitted` |

---

## 6. PosteriorSelectionEvaluator / EvidenceScaleGapMetric

| Algorithm | Current | Limitation | Uplift | Quantitative Target | Test |
|---|---|---|---|---|---|
| EvidenceScaleGapMetric | Replay-through-adapter; emits `selection_ratio` plateauing at `0.8061` on two_moons. | Plateau rather than convergence to `1.0` (paper's `eps -> 0` limit isn't realised at fixed sigma). | **A16** Add `eps_schedule: Callable[[int], float]` arg (`posterior_selection_evaluator.py:471`); per-round `eps = eps_schedule(r)` decays the implicit noise scale so the ratio rises toward 1. | `eps_schedule = lambda r: 0.05 * (1 - r/L)` reports final `selection_ratio >= 0.95` on `two_moons` (vs. `0.8061` baseline). | `tests/test_eval/test_posterior_selection_evaluator.py::test_eps_schedule_converges_to_1` |
| EvidenceScaleGapMetric | Selection ratio is schedule-independent by construction (the metric scores fresh replays). | Runner cannot compare *its own bundle's* evidence vs. the metric's. | **B12** Add `evaluate_trajectory` mode where `endpoints` come from the runner's current `per_round_metrics[r]` bundles (close-out per paper ADR-0013 phase 5); close the gap noted in `ABLATION.md:139`. | Selection ratio becomes schedule-sensitive; codimension row shows `delta_selection_ratio != 0` vs. cosine row. | `tests/test_eval/test_posterior_selection_evaluator.py::test_trajectory_evaluator_schedule_sensitive` |
| EvidenceScaleGapMetric | `calibration_lower_bound` fixed at `0.95`, `perturbation_stability_lower_bound` at `0.85`. | No paper-quantity-aligned values (e.g. lower bound derived from `C_1` of Corollary 1). | **C3** Compute `calibration_lower_bound = min(0.95, A_g / (A_g + B_g * C_g))` from the paper quantities so the lower bound is grounded in paper Corollary 1. | Computed value within `1e-6` of `A_g / (A_g + B_g * C_g)` for the canonical `g_a` profile; ledger row carries the computed value. | `tests/test_eval/test_posterior_selection_evaluator.py::test_calibration_from_paper_quantities` |

---

## 7. Paper Quantities (`contracts/paper_quantities.py`)

| Quantity | Current | Limitation | Uplift | Quantitative Target | Test |
|---|---|---|---|---|---|
| `sheet_evidence_A(g)` | Trapezoidal on `[-K, K]` with step `h`; absolute tolerance `~1e-14`. | Default `K = 8`, `h = 0.01`; tail truncation `e^{-K^2/2} ~ 1e-14`. Doesn't expose the per-step discretisation error. | **A17** Add `discretization_error: float` field to a new `SheetEvidenceResult` dataclass (`paper_quantities.py:64`) carrying `2 * max(h**2 * ...)` trapezoidal error bound. | Reported bound within `2x` of measured vs. `h=0.001` reference; `discretization_error <= 1e-6` for default args. | `tests/test_contracts/test_paper_quantities.py::test_sheet_evidence_error_bound` |
| `sheet_evidence_A(g)` | Pure math; no JIT / cache. | Repeated calls with the same `g` recompute the integral. | **C4** Add `functools.lru_cache(maxsize=128)` on `sheet_evidence_A` keyed by `g.__qualname__` + `K` + `h`. | Second call with same `g` returns within `0.5x` time of first (cache hit). | `tests/test_contracts/test_paper_quantities.py::test_sheet_evidence_cached` |
| `root_cell_packing_B(g)` | Sign-change sampling on uniform grid. | Misses roots in `[K, infty)` because `K = 8`. | **B13** Add `K: float = 32.0` default (`paper_quantities.py:139`); tail beyond `K` bounded by `e^{-K^2/4}` and emitted as `tail_bound: float` field on `RootCellPackingResult`. | `B_g` for `g_a(x) = (1 + 0.25 * tanh x) * sin x` reports `tail_bound <= 1e-30` with `K=32`. | `tests/test_contracts/test_paper_quantities.py::test_packing_tail_bound` |
| `per_cell_coefficient_C` | `e^{rho^2/2} / a`, with `a = (1-rho)^2 * min(c^2, 1)`. | Single value per `rho`, `c`. | **B14** Add `drift_robustness: float` field returning `C_g * (1 + 2*rho)` so callers can compare against a perturbation-aware bound. | Field within `2x` of `C_g`; emitted in `CodimensionSheetScheduler`'s `paper_quantity_diagnostics`. | `tests/test_contracts/test_paper_quantities.py::test_c_drift_robustness` |
| `exterior_gap_e_rho` | `min(rho^4, (1-rho)^2 * eta^2)`. | Not propagated to scheduler's `inject_noise` mass. | **A18** Wire `e_rho` into `CodimensionSheetScheduler.inject_noise` (`scheduler.py:2594`) as a floor on `sqrt(noise_mass)` so forward noise respects the physical complement gap. | Codimension row with `e_rho` wiring reports `selection_ratio` >= baseline + `1e-3` on `two_moons`. | `tests/test_contracts/test_paper_quantities.py::test_e_rho_into_scheduler` |

---

## 8. Runner-side consumption (`ReInferenceRunner` / `BatchedTrajectoryRunner`)

| Algorithm | Current | Limitation | Uplift | Quantitative Target | Test |
|---|---|---|---|---|---|
| `ReInferenceRunner` | Per-round metric dict captures `n_cap`, `memory_fraction`, `beta`, `driver_beta`, `merge_audit_codes`, `endpoint_export_failed`, `forward_noise_injected`. | Doesn't capture `selection_ratio` from the runner's own bundle — only from the optional `selection_evaluator`. | **A19** Add per-round `selection_ratio` from runner's bundle via `evaluate_trajectory` (close **B12**); emit alongside `W2` and `coverage`. | Runner-driven row reports schedule-sensitive `selection_ratio`; codimension row's mean >= 0.85. | `tests/test_algorithm/test_runner.py::test_runner_emits_schedule_sensitive_selection_ratio` |
| `ReInferenceRunner` | Carries `prev_ledger_row_hash` across rounds. | `verify_ledger_chain` runs *after* the loop ends; tampering between rounds is caught at the end. | **B15** Call `verify_ledger_chain` incrementally per round (`runner.py:689`); raise immediately on tamper. | First tamper detected within 1 round of occurrence; end-of-run `verify_ledger_chain` still passes for clean runs. | `tests/test_algorithm/test_runner.py::test_runner_per_round_chain_verify` |
| `BatchedTrajectoryRunner` | `T x K` per round; Monte Carlo standard error `~0.0065`. | Doesn't expose the per-round endpoint distribution's empirical covariance. | **C5** Add `per_round_endpoint_covariance: list[NDArray]` field to `BatchedTrajectoryResult` (`batched_runner.py:265`) carrying the empirical `cov(endpoints)` per round. | Covariance matrix is `2x2` symmetric positive-semi-definite; trace decreases monotonically with `r`. | `tests/test_algorithm/test_batched_runner.py::test_batched_emits_endpoint_covariance` |

---

## Prioritized Uplifts

### P0 — must do (blocking framework consumption or paper correctness)

| ID | Algorithm | Uplift |
|---|---|---|
| A1 | All schedulers | `audit_codes` on `ScheduleSample` (foundation for A6-A11, A15, A18) |
| A6 | ConvergenceAdaptiveScheduler | `record_round_feedback` reads `coverage` + `selection_ratio` |
| A7 | CodimensionSheetScheduler | `evidence_ratio` on `ScheduleSample` consumed by runner |
| A16 | EvidenceScaleGapMetric | `eps_schedule` decays noise so `selection_ratio` reaches `>=0.95` |
| A12 | BoundedMergeOperator | `exterior_gap_e_rho` floor per paper Lemma 5 |

### P1 — should do (clear framework-driving improvement with measurable effect)

| ID | Algorithm | Uplift |
|---|---|---|
| A2 | CosineAnnealScheduler | Wire `A_g` into `inject_noise` for paper-quantity-aware noise |
| A8 | SequentialScheduler | Forward `record_round_feedback` to all sub-schedulers |
| A10 | ScheduleDerivedPolicyDriver | Audit code attribution in `provenance` |
| A11 | AdaptivePolicyDriver | `beta_saturation_count` per-round metric |
| A13 | IdentityOperator | `MERGE_NONFINITE_DYNAMIC_CLIPPED` audit emission |
| A14 | LinearBlender | `BLENDER_MEMORY_FRACTION_CLIPPED` audit emission |
| A17 | `sheet_evidence_A` | Discretization error bound on result |
| A18 | `exterior_gap_e_rho` | Wire into `CodimensionSheetScheduler.inject_noise` |
| A19 | `ReInferenceRunner` | Schedule-sensitive `selection_ratio` from runner's bundle |

### P2 — nice to have (marginal effect)

| ID | Algorithm | Uplift |
|---|---|---|
| A3 | ConstantScheduler | `audit_codes` baseline marker |
| A4 | LinearScheduler | `inject_noise` direction knob |
| A5 | LinearScheduler | Inherit `audit_codes` field |
| A9 | SequentialScheduler | `seq_inject_noise_fallback` audit code |
| B1 | CosineAnnealScheduler | `schedule_family` into `config_hash` |
| B2 | ConstantScheduler | `memory_fraction_baseline` property |
| B3 | ExponentialScheduler | `noise_floor` arg |
| B4 | ExponentialScheduler | `expected_n_cap` analytic mean |
| B5 | SigmoidScheduler | `tail_floor` knob |
| B6 | ConvergenceAdaptiveScheduler | Kalman-like variance reduction |
| B7 | CodimensionSheetScheduler | Require `profile_residual_fn` (no heuristic fallback) |
| B8 | ConstantPolicyDriver | `min_floor` arg |
| B9 | BoundedMergeOperator | Implement `tolerance` near-degenerate handling |
| B10 | EMAOperator | `alpha_schedule` callable |
| B11 | LinearBlender | `per_cell_coefficient_C` scaling |
| B12 | EvidenceScaleGapMetric | `evaluate_trajectory` schedule-sensitive path |
| B13 | `root_cell_packing_B` | `K=32` default + `tail_bound` field |
| B14 | `per_cell_coefficient_C` | `drift_robustness` field |
| B15 | `ReInferenceRunner` | Per-round `verify_ledger_chain` |
| C1 | PolynomialScheduler | `preset` literal |
| C2 | All drivers | `name` arg in `config_hash` |
| C3 | EvidenceScaleGapMetric | `calibration_lower_bound` from paper Corollary 1 |
| C4 | `sheet_evidence_A` | `lru_cache` |
| C5 | `BatchedTrajectoryRunner` | `per_round_endpoint_covariance` field |

**Counts:** P0 = 5, P1 = 9, P2 = 24. Total uplifts = 38.

---

## Implementation Plans (P0 + P1)

### P0-A1 — Add `audit_codes` to `ScheduleSample`

File: `adaptive_reflow/algorithm/scheduler.py:66` (dataclass) and every
`ScheduleSample(...)` call site (lines `305`, `577`, `783`, `1009`,
`1244`, `1495`, `1769`, `2522`).

Before:

```python
@dataclass(frozen=True)
class ScheduleSample:
    outer_cycle_id: int
    round_in_cycle: int
    cycle_length: int
    n_cap: float
    n_min: float
    n_max: float
    u_r: float
    family: str
    computed_at_round: int
    schedule_hash: str
```

After:

```python
@dataclass(frozen=True)
class ScheduleSample:
    outer_cycle_id: int
    round_in_cycle: int
    cycle_length: int
    n_cap: float
    n_min: float
    n_max: float
    u_r: float
    family: str
    computed_at_round: int
    schedule_hash: str
    audit_codes: tuple[str, ...] = ()
    evidence_ratio: float | None = None
```

Test: `tests/test_algorithm/test_scheduler.py::test_cosine_sample_carries_audit_codes`
asserts `sample.audit_codes == ("cosine_baseline",)` for a cosine
scheduler round-0 sample and `sample.evidence_ratio is None` for the
cosine family.

### P0-A6 — ConvergenceAdaptiveScheduler reads multi-metric feedback

File: `adaptive_reflow/algorithm/scheduler.py:1848`.

Before:

```python
def record_round_feedback(self, round_in_cycle, metrics):
    try:
        w2_raw = metrics.get("W2", float("nan"))
```

After:

```python
def record_round_feedback(self, round_in_cycle, metrics):
    weights = {"W2": 1.0, "coverage": 0.3, "selection_ratio": 0.5}
    aggregate = 0.0
    weight_sum = 0.0
    for key, w in weights.items():
        v = metrics.get(key, float("nan"))
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(v):
            continue
        aggregate += w * v
        weight_sum += w
    if weight_sum <= 0:
        return
    synthetic_W2 = aggregate / weight_sum  # fold back into W2 update
    w2_raw = synthetic_W2
    ...
```

Test: `test_convergence_adaptive_multi_metric` exercises W2-only vs.
multi-metric; second run shifts at least `1e-3` farther in the
multi-metric case on a synthetic two-round trace.

### P0-A7 — CodimensionSheetScheduler emits `evidence_ratio`

File: `adaptive_reflow/algorithm/scheduler.py:2522`.

Before:

```python
sample = ScheduleSample(
    outer_cycle_id=outer_cycle_id, ...,
    schedule_hash=str(self._config_hash_value),
)
```

After:

```python
sample = ScheduleSample(
    outer_cycle_id=outer_cycle_id, ...,
    schedule_hash=str(self._config_hash_value),
    audit_codes=("codimension_paper_quantity_grounded"
                 if self._sheet_A is not None else
                 "codimension_framework_heuristic"),
    evidence_ratio=float(self._last_evidence_ratio or 0.0),
)
```

Test: `test_codimension_sample_evidence_ratio` asserts
`sample.evidence_ratio == 0.8061` (current plateau) for the
two_moons `g_a` profile.

### P0-A16 — EvidenceScaleGapMetric accepts `eps_schedule`

File: `adaptive_reflow/eval/posterior_selection_evaluator.py:471`.

Before:

```python
def __init__(self, *, target=..., n_gen=1000, n_ref=1000, seed=42,
             eps_implicit=0.05):
```

After:

```python
def __init__(self, *, target=..., n_gen=1000, n_ref=1000, seed=42,
             eps_implicit=0.05,
             eps_schedule=None):
    self._eps_schedule = eps_schedule

def _compute_metrics(self, *, seed, round_index=0):
    eps = (self._eps_schedule(round_index)
           if self._eps_schedule is not None else self._eps_implicit)
    ...
```

Test: `test_eps_schedule_converges_to_1` runs `eps_schedule = lambda
r: 0.05 * (1 - r / 20)` over 20 rounds; final round
`selection_ratio >= 0.95`.

### P0-A12 — BoundedMergeOperator folds `exterior_gap_e_rho` into floor

File: `adaptive_reflow/algorithm/merge_operator.py:386`.

Before:

```python
def __init__(self, *, tolerance: float = 1e-9):
    self._tolerance = float(tolerance)
```

After:

```python
def __init__(self, *, tolerance: float = 1e-9,
             exterior_gap_e_rho: float | None = None):
    self._tolerance = float(tolerance)
    self._exterior_gap_e_rho = (
        None if exterior_gap_e_rho is None
        else float(exterior_gap_e_rho)
    )

def merge(self, prev, dynamic, *, cap, floor, delta_cap_up,
          delta_cap_down, audit_codes=None):
    ...
    if self._exterior_gap_e_rho is not None:
        paper_floor = self._exterior_gap_e_rho / 4.0
        if floor < paper_floor:
            floor = paper_floor
            if audit_codes is not None:
                audit_codes.append(
                    f"merge_paper_quantity_floor_lifted:floor={floor:.6f}"
                )
    ...
```

Test: `test_bounded_paper_quantity_floor` constructs a merge with
`exterior_gap_e_rho=0.05` and asserts the returned floor is
`>= 0.0125`.

### P1-A8 — SequentialScheduler forwards feedback to all slots

File: `adaptive_reflow/algorithm/sequential.py:287`.

Before:

```python
def record_round_feedback(self, round_in_cycle, metrics):
    try:
        _, slot, sub_round = self._resolve_slot(round_in_cycle)
    except ValueError:
        return
    slot.scheduler.record_round_feedback(
        round_in_cycle=int(sub_round), metrics=metrics)
```

After:

```python
def record_round_feedback(self, round_in_cycle, metrics):
    for idx, slot in enumerate(self._slots):
        cumulative = sum(s.n_rounds for s in self._slots[:idx])
        # Forward to *every* slot with the slot-relative round, clamping
        # to the slot's range so an out-of-cycle call still warms up
        # the scheduler.
        sub_round = max(0, min(slot.n_rounds - 1,
                                round_in_cycle - cumulative))
        slot.scheduler.record_round_feedback(
            round_in_cycle=int(sub_round), metrics=metrics)
```

Test: `test_sequential_feedback_to_all_slots` builds a
`SequentialScheduler([(ConvergenceAdaptiveScheduler, 5),
(ConvergenceAdaptiveScheduler, 5)])` and asserts that after 3 rounds
both sub-schedulers' `_w2_history` has length 3.

### P1-A19 — Runner consumes schedule-sensitive selection_ratio

File: `adaptive_reflow/algorithm/runner.py:785`.

Before:

```python
if config.selection_evaluator is not None and bundle is not None:
    selection_metrics = config.selection_evaluator.oracle(
        bundle, channel=primary_channel, seed=int(config.seed) + r)
    metric["selection_ratio"] = float(
        selection_metrics.get("selection_ratio", 0.0))
```

After:

```python
if config.selection_evaluator is not None and bundle is not None:
    # Prefer the schedule-sensitive evaluate_trajectory path when the
    # metric exposes one (B12); fall back to the replay-through-adapter
    # path for backward compat.
    if hasattr(config.selection_evaluator, "evaluate_trajectory"):
        try:
            traj = self._adapter.export_trajectory(
                trace.integrator_trace)
            endpoints = np.asarray(traj, dtype=np.float64)
            selection_metrics = (
                config.selection_evaluator.evaluate_trajectory(
                    endpoints, channel=primary_channel,
                    seed=int(config.seed) + r
                ).__dict__
            )
        except (NotImplementedError, AttributeError):
            selection_metrics = config.selection_evaluator.oracle(
                bundle, channel=primary_channel,
                seed=int(config.seed) + r)
    else:
        selection_metrics = config.selection_evaluator.oracle(
            bundle, channel=primary_channel,
            seed=int(config.seed) + r)
    metric["selection_ratio"] = float(
        selection_metrics.get("selection_ratio", 0.0))
```

Test: `test_runner_emits_schedule_sensitive_selection_ratio` runs
cosine + codimension with `selection_evaluator`; the two rows now
report distinct `mean_selection_ratio` (currently both `0.8086`).

---

## Reproducibility / determinism notes

- Every uplift above preserves byte-identical output when its new
  optional argument is unset (default = legacy behaviour).
- `ScheduleSample` is `frozen=True`; extending it requires updating
  every call site, which `A1` lists explicitly.
- `verify_ledger_chain` (P0-8) must still pass for every uplift;
  tests assert `ledger_chain_integrity=True`.
- `BatchedTrajectoryRunner`'s deprecated `policy_driver` / `blender`
  slots remain unchanged; their `DeprecationWarning` is preserved.

## Mapping to existing ADR / design docs

| Uplift | ADR / design ref |
|---|---|
| A1, A7, A18 | `docs/adr/0013-codimension-posterior-selection.md` (Phase 5) |
| A2, A12, A18 | `docs/adr/0010-cosine-driven-memory-fraction.md` extension |
| A6, A8 | `docs/adr/0012-schedule-families.md` (feedback-driven variants) |
| A16, A19, B12 | `docs/design/B5_BATCHED_TRAJECTORIES` (.md) §1.1 |
| B15 | `docs/adr/0014-ledger-hash-chain.md` (P0-8 extension) |
| C5 | `docs/design/B5_BATCHED_TRAJECTORIES` (.md) §3.2 |

## Files touched (counted)

- `adaptive_reflow/algorithm/scheduler.py` — A1, A2, A6, A7, B1, B3,
  B4, B5, B6, B7.
- `adaptive_reflow/algorithm/sequential.py` — A8, A9.
- `adaptive_reflow/algorithm/policy_driver.py` — A10, A11, B8, C2.
- `adaptive_reflow/algorithm/merge_operator.py` — A12, A13, B9, B10.
- `adaptive_reflow/algorithm/blender.py` — A14, A15, B11.
- `adaptive_reflow/eval/posterior_selection_evaluator.py` — A16,
  B12, C3.
- `adaptive_reflow/contracts/paper_quantities.py` — A17, A18, B13,
  B14, C4.
- `adaptive_reflow/algorithm/runner.py` — A19, B15.
- `adaptive_reflow/algorithm/batched_runner.py` — C5.

Total: 9 production files, 38 uplifts, 5 P0 + 9 P1 + 24 P2.
