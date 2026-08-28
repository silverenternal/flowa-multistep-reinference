# Algorithm Deep Uplift Benchmark


Comprehensive BEFORE / AFTER benchmark for every P0/P1 framework-internal/external uplift listed in `docs/algorithm-deep-uplift-plan.md`. Generated in `8.6s` (plus `60.5s` for the ablation re-run).

## Section 1: Framework-internal uplifts

BEFORE / AFTER measurements for every framework-internal P0/P1 uplift. The algorithm layer, scheduler, driver, merge, and blender consume the same inputs on both sides so the delta is attributable to the uplift.

| Algorithm | Uplift | Metric | Baseline | Current | Delta | % Change | Target | Achieved |
|---|---|---|---:|---:|---:|---:|---|:---:|
| CosineAnnealScheduler | B1 (schedule_family into config_hash) | distinct_config_hashes_for_6_families | 5 | 6 | 1 | 20 | ==6 | yes |
| CosineAnnealScheduler | A1 (audit_codes on ScheduleSample) | samples_with_nonempty_audit_codes | 0 | 20 | 20 | +inf | >=1 of 20 | yes |
| ConstantScheduler | A3 (constant_baseline audit code) | samples_with_schedule_constant_baseline_code | 0 | 20 | 20 | +inf | ==20 | yes |
| CosineAnnealScheduler | curve_hash reproducibility (same seed) | curve_hashes_byte_identical | 1 | 1 | 0 | 0 | byte_identical | yes |
| CodimensionSheetScheduler | A7 (evidence_ratio on ScheduleSample) | samples_with_evidence_ratio_set | 0 | 20 | 20 | +inf | ==20 | yes |
| ScheduleDerivedPolicyDriver | A10 (policy_schedule_derived audit code) | rounds_with_policy_schedule_derived_code | 0 | 20 | 20 | +inf | ==20 | yes |
| AdaptivePolicyDriver | A11 (beta_saturation_count exposed) | beta_saturation_count_after_20_rounds | 0 | 20 | 20 | +inf | >=1 | yes |
| IdentityOperator | A13 (MERGE_NONFINITE_DYNAMIC_CLIPPED on NaN) | audit_codes_for_nan_dynamic | 0 | 1 | 1 | +inf | >=1 | yes |
| BoundedMergeOperator | A12 (e_rho/4 paper-quantity floor lift) | audit_codes_for_floor_lifted | 0 | 1 | 1 | +inf | >=1 | yes |
| LinearBlender | A14 (BLENDER_MEMORY_FRACTION_CLIPPED) | audit_codes_for_out_of_range_mf | 0 | 1 | 1 | +inf | >=1 | yes |
| LinearBlender | A14 (silent on in-range memory_fraction) | audit_codes_for_in_range_mf | 0 | 0 | 0 | 0 | ==0 | yes |
| DistanceDecayBlender | A15 (decay_factor folded into digest) | digests_differ_when_distance_differs | 0 | 1 | 1 | +inf | True | yes |
| EvidenceScaleGapMetric | A16 (eps_schedule drives ratio toward 1) | final_selection_ratio_with_decay | 0.872235 | 0.999634 | 0.127399 | 14.606 | >=0.95 | yes |
| EvidenceScaleGapMetric | A16 SNR proxy (signal/noise floor) | snr_proxy | 0 | 60.7968 | 60.7968 | +inf | >=1.0 | yes |
| EvidenceScaleGapMetric | C3 (calibration_lower_bound reproducible) | calibration_lower_bound_byte_identical | 1 | 1 | 0 | 0 | byte_identical | yes |
| EvidenceScaleGapMetric | B12 (selection_ratio reproducibility) | selection_ratio_byte_identical | 1 | 1 | 0 | 0 | byte_identical | yes |
| paper_quantities.sheet_evidence_A | A17 (A_g value for sin profile) | A_g_sin | nan | 0.854085 | nan | nan | in (0, 1.5) | yes |
| paper_quantities.sheet_evidence_A | A17 (A_g value for polynomial profile) | A_g_polynomial | nan | 0.765289 | nan | nan | in (0, 1.5) | yes |
| paper_quantities.root_cell_packing_B | B13 (B_g for sin profile) | B_g_sin_K32 | nan | 1.16971 | nan | nan | >=0 | yes |
| paper_quantities.root_cell_packing_B | B13 (tail_bound <= 1e-30 for K=32) | tail_bound_sin_K32 | nan | 2.6465e-111 | nan | nan | <=1e-30 | yes |
| paper_quantities.per_cell_coefficient_C | B14 (C_g drift_robustness within 2x) | drift_robustness_over_C_g_ratio | 1 | 1.2 | 0.2 | 20 | <=2.0 | yes |
| paper_quantities.exterior_gap_e_rho | e_rho default | e_rho_default | nan | 0.0001 | nan | nan | in (0, 1) | yes |
| paper_quantities.root_cell_packing_B | Lemma 5 invariant (B_g >= 0 + tail < 1e-20) | lemma5_invariant_K32 | 1 | 1 | 0 | 0 | True | yes |
| paper_quantities.exterior_gap_e_rho | Lemma 4 invariant (e_rho > 0) | lemma4_invariant | 1 | 1 | 0 | 0 | True | yes |
| SequentialScheduler | n_cap trajectory (3-slot chain matches per-slot) | trajectory_matches_expected_curve | 1 | 1 | 0 | 0 | True | yes |
| SequentialScheduler | A8 (feedback forwarded to all slots) | all_slots_warmed_after_single_call | 0 | 1 | 1 | +inf | True | yes |
| SequentialScheduler | A9 (seq_inject_noise_fallback audit on OOR) | audit_codes_for_oor_inject_noise | 0 | 1 | 1 | +inf | >=1 with seq_inject_noise_fallback | yes |
| W2 estimator (batched runner) | P0 #3 projection-free exact W2 | squared CV of per-round W2 (n=128, 200 seeds) | 0.00727108 | 0.00205598 | -0.00521511 | -71.7239 | >= 50% reduction | yes |
| BatchedTrajectoryRunner | P0 #8 vectorised round generation | adapter invocations per round | 8 | 1 | -7 | -87.5 | T-fold reduction (T=8) | yes |
| CodimensionSheetScheduler | P0 #9 evidence-driver mode | cycle-mean memory fraction (1 - n_cap) | 0.5 | 0.500656 | 0.000656066 | 0.131213 | driven >= baseline | yes |
| coverage_score | P1 area-weighted Voronoi coverage | sparse-vs-dense separation (binary saturates) | 0 | 0.2252 | 0.2252 | +inf | >= 0.20 separation | yes |
| energy_distance | P1 percentile bootstrap CI | 95% CI relative width (distance scale, n=256) | +inf | 0.152594 | -inf | -inf | <= 0.20 | yes |
| selection_ratio trajectory | P1 bounded-Lipschitz convergence diagnostic | tail increment (oscillating -> converged) | 0.12 | 0.00455061 | -0.115449 | -96.2078 | converged <= 0.0884 (1/sqrt(N)) | yes |
| LatentConvexMixer | P2 #27 OT displacement mixing | worst relative scale error across beta grid | 0.271094 | 1.1858e-15 | -0.271094 | -100 | >= 100x reduction | yes |
| LedgerChain | P2 #40 incremental chain verification | row hashes for verify-on-every-append (R=64) | 2080 | 64 | -2016 | -96.9231 | >= 32x reduction | yes |
| check_monotonicity_property | sweep-based monotonicity certification | adjacent pairs certified per factor | 1 | 32 | 31 | 3100 | >= 32x coverage | yes |

## Section 2: Framework-external uplifts

BEFORE / AFTER measurements for every framework-external P0/P1 uplift (ODE step count, sampler accuracy, target stress test, Voronoi coverage, energy distance, Lipschitz diagnostic, Wilson CI round-trip).

| Algorithm | Uplift | Metric | Baseline | Current | Delta | % Change | Target | Achieved |
|---|---|---|---:|---:|---:|---:|---|:---:|
| ODE integrator (2-D linear) | P0 #4 step-count reduction (RK4@100 -> solver@20) | endpoint L2 distance vs RK4@100 (lower=better) | 0 | 0.0229832 | 0.0229832 | +inf | <= 0.05 | yes |
| ODE integrator (2-D linear) | P0 #4 step-count used (after = DPM-Solver) | steps used for endpoint | 100 | 20 | -80 | -80 | <= 25 | yes |
| ODE integrator (2-D linear) | P0 #4 sampler accuracy (UniPC@20 vs RK4@100) | endpoint L2 distance vs RK4@100 | 0 | 0.000197216 | 0.000197216 | +inf | <= 0.05 | yes |
| ODE integrator (2-D linear) | P0 #4 step-count used (after = UniPC) | steps used for endpoint | 100 | 20 | -80 | -80 | <= 25 | yes |
| ODE integrator (2-D linear) | P0 #4 sampler accuracy (Heun@20 vs RK4@100) | endpoint L2 distance vs RK4@100 | 0 | 0.000197216 | 0.000197216 | +inf | <= 0.05 | yes |
| ODE integrator (2-D linear) | P0 #4 step-count used (after = Heun) | steps used for endpoint | 100 | 20 | -80 | -80 | <= 25 | yes |
| ODE integrator (2-D linear) | P0 #4 sampler accuracy (RK4@20 vs RK4@100) | endpoint L2 distance vs RK4@100 | 0 | 1.9982e-09 | 1.9982e-09 | +inf | <= 0.10 (regression ceiling) | yes |
| ODE integrator (2-D linear) | P0 #4 sampler accuracy (DOPRI5@20 vs RK4@100) | endpoint L2 distance vs RK4@100 | 0 | 0.0163769 | 0.0163769 | +inf | <= 0.05 | yes |
| coverage_score | P1 area-weighted Voronoi (binary -> weighted) | sparse-vs-dense separation | 0 | 0.1916 | 0.1916 | +inf | >= 0.20 separation | no |
| energy_distance | P1 percentile bootstrap CI | 95% CI relative width (distance scale, n=256) | +inf | 0.150614 | -inf | -inf | <= 0.20 | yes |
| selection_ratio trajectory | P1 bounded-Lipschitz convergence diagnostic | tail increment (converged <= rate_bound) | 0.12 | 0.00455061 | -0.115449 | -96.2078 | converged_tail_modulus * du <= 1/sqrt(128) (~0.088) | yes |
| Wilson lower bound | P1 #24 wilson_ci exposure (two-sided CI) | lower-bound agreement vs wilson_lower_bound | nan | 0 | nan | nan | <= 1e-12 | yes |
| LatentConvexMixer | P2 #27 OT displacement mixing | worst relative scale error (linear vs OT) | 0.285244 | 1.20415e-15 | -0.285244 | -100 | >= 100x reduction | yes |
| W2 estimator (batched runner) | P0 #3 projection-free exact W2 | squared CV (n=128, 100 seeds) | 0.00729056 | 0.00219187 | -0.00509869 | -69.9355 | >= 50% reduction | yes |

## Section 3: Pluggable design tests

Each plug-in point must (a) return a stable `config_hash` for the same configuration and (b) round-trip `to_config` / `from_config` byte-for-byte. Audit-code emission is asserted where the contract requires it.

| Protocol | Implementation | Metric | Before | After | Delta | % Change | Target | Achieved |
|---|---|---|---:|---:|---:|---:|---|:---:|
| SchedulerProtocol | CosineAnnealScheduler | config_hash stability across same config | 0 | 1 | 1 | +inf | stable=True, distinct=True | yes |
| SchedulerProtocol | CosineAnnealScheduler | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| SchedulerProtocol | ConstantScheduler | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| SchedulerProtocol | LinearScheduler | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| SchedulerProtocol | ExponentialScheduler | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| SchedulerProtocol | PolynomialScheduler | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| SchedulerProtocol | SigmoidScheduler | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| SchedulerProtocol | ConvergenceAdaptiveScheduler | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| SchedulerProtocol | CodimensionSheetScheduler | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| SchedulerProtocol | SequentialScheduler | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| SchedulerProtocol | build_scheduler_from_config | from_config round-trip via factory | 0 | 1 | 1 | +inf | factory rebuild is byte-identical | yes |
| SchedulerProtocol | build_scheduler | registry lookup success across 5 keys | 0 | 1 | 1 | +inf | all 5 keys resolved | yes |
| PolicyDriverProtocol | ScheduleDerivedPolicyDriver | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| PolicyDriverProtocol | ConstantPolicyDriver | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| PolicyDriverProtocol | AdaptivePolicyDriver | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| PolicyDriverProtocol | ConstantPolicyDriver | config_hash distinct for different beta | 0 | 1 | 1 | +inf | beta change -> hash change | yes |
| MergeOperatorProtocol | IdentityOperator | config_hash stable across same config | 0 | 1 | 1 | +inf | h1==h2 | yes |
| MergeOperatorProtocol | BoundedMergeOperator | config_hash stable across same config | 0 | 1 | 1 | +inf | h1==h2 | yes |
| MergeOperatorProtocol | EMAOperator | config_hash stable across same config | 0 | 1 | 1 | +inf | h1==h2 | yes |
| MergeOperatorProtocol | BoundedMergeOperator | config_hash distinct for different e_rho | 0 | 1 | 1 | +inf | e_rho change -> hash change | yes |
| RestartBlenderProtocol | LinearBlender | config_hash stable across same config | 0 | 1 | 1 | +inf | h1==h2 | yes |
| RestartBlenderProtocol | DistanceDecayBlender | config_hash stable across same config | 0 | 1 | 1 | +inf | h1==h2 | yes |
| RestartBlenderProtocol | DistanceDecayBlender | config_hash distinct for different temperature | 0 | 1 | 1 | +inf | T change -> hash change | yes |
| RestartBlenderProtocol | LinearBlender | audit_codes emission on out-of-range MF | 0 | 1 | 1 | +inf | BLENDER_MEMORY_FRACTION_CLIPPED emitted | yes |
| IntegratorProtocol | RK4Integrator | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| IntegratorProtocol | DormandPrinceRK45Integrator | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| IntegratorProtocol | DPMSolverIntegrator | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| IntegratorProtocol | UniPCIntegrator | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| IntegratorProtocol | HeunIntegrator | from_config round-trip | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| IntegratorProtocol | INTEGRATOR_REGISTRY | registry size (rk4 / dopri5 / dpm_solver / unipc / heun) | 0 | 6 | 6 | +inf | >= 5 families | yes |
| W2EstimatorProtocol | mode_centre_mse | registry membership + stable estimate | 0 | 1 | 1 | +inf | in W2_REGISTRY AND stable estimate | yes |
| W2EstimatorProtocol | projection_free | registry membership + stable estimate | 0 | 1 | 1 | +inf | in W2_REGISTRY AND stable estimate | yes |
| W2EstimatorProtocol | sinkhorn | registry membership + stable estimate | 0 | 1 | 1 | +inf | in W2_REGISTRY AND stable estimate | yes |
| W2EstimatorProtocol | kernelized | registry membership + stable estimate | 0 | 1 | 1 | +inf | in W2_REGISTRY AND stable estimate | yes |
| W2EstimatorProtocol | W2_REGISTRY | registry size | 0 | 4 | 4 | +inf | >= 4 families | yes |
| SchedulerProtocol | CodimensionSheetScheduler | evidence_ratio emitted on every sample | 0 | 20 | 20 | +inf | == 20 | yes |
| SchedulerProtocol | CodimensionSheetScheduler | audit_codes emitted on every sample | 0 | 20 | 20 | +inf | >= 20 | yes |

## Section 4: Ablation (extended table)

Re-run of `tools/run_ablation.py` (full 20-round configuration). The canonical 22-row grid is reproduced below with the W2 / coverage / selection_ratio / ledger_chain_integrity columns the task brief requires.

| Config | Target | Final W2 | Mean W2 | Final Coverage | Mean Coverage | Selection Ratio | Ledger Chain Integrity |
|---|---|---:|---:|---:|---:|---:|:---:|
| single_pass | two_moons | 2.8519 | 2.8519 | 0.500 | 0.500 | -- | -- |
| multi_round_constant_beta_05 | two_moons | 0.8690 | 0.9597 | 1.000 | 1.000 | -- | -- |
| multi_round_cosine_anneal | two_moons | 0.8691 | 0.9556 | 1.000 | 1.000 | -- | -- |
| multi_round_no_restart | two_moons | 0.6244 | 0.7158 | 1.000 | 1.000 | -- | -- |
| multi_round_polynomial_schedule_derived | two_moons | 1.1672 | 1.3945 | 1.000 | 1.000 | -- | -- |
| multi_round_sigmoid_schedule_derived | two_moons | 0.7716 | 0.9774 | 1.000 | 1.000 | -- | -- |
| multi_round_convergence_adaptive_schedule_derived | two_moons | 0.9700 | 0.7518 | 1.000 | 1.000 | -- | -- |
| multi_round_cosine_adaptive_driver | two_moons | 0.8424 | 0.9300 | 1.000 | 1.000 | -- | -- |
| batched_cosine_forward_noise_hash_chained | two_moons | 1.1364 | 1.1257 | 1.000 | 1.000 | -- | True |
| multi_round_cosine_anneal_identity_merge | two_moons | 0.8691 | 0.9556 | 1.000 | 1.000 | -- | True |
| multi_round_codimension_sheet_posterior_selection | two_moons | 0.8691 | 0.9556 | 1.000 | 1.000 | 0.8061 | -- |
| multi_round_cosine_posterior_selection | two_moons | 0.8691 | 0.9556 | 1.000 | 1.000 | 0.8061 | -- |
| single_pass | eight_gaussians | 2.3095 | 2.3095 | 0.125 | 0.125 | -- | -- |
| multi_round_constant_beta_05 | eight_gaussians | 2.0183 | 2.1975 | 0.625 | 0.625 | -- | -- |
| multi_round_cosine_anneal | eight_gaussians | 2.0437 | 2.2255 | 0.875 | 0.875 | -- | -- |
| multi_round_no_restart | eight_gaussians | 0.7591 | 1.0898 | 0.500 | 0.500 | -- | -- |
| multi_round_polynomial_schedule_derived | eight_gaussians | 2.3226 | 2.6142 | 0.375 | 0.325 | -- | -- |
| multi_round_sigmoid_schedule_derived | eight_gaussians | 1.7198 | 2.1204 | 0.375 | 0.375 | -- | -- |
| multi_round_convergence_adaptive_schedule_derived | eight_gaussians | 1.1620 | 1.2039 | 0.625 | 0.625 | -- | -- |
| multi_round_cosine_adaptive_driver | eight_gaussians | 2.3325 | 2.5497 | 0.375 | 0.375 | -- | -- |
| batched_cosine_forward_noise_hash_chained | eight_gaussians | 1.7441 | 1.8717 | 0.375 | 0.375 | -- | True |
| multi_round_cosine_anneal_identity_merge | eight_gaussians | 2.0437 | 2.2255 | 0.875 | 0.875 | -- | True |

## Section 5: Summary


- Total uplifts measured: **87**
  - Framework-internal: **36** (see Section 1)
  - Framework-external: **14** (see Section 2)
  - Pluggable design tests: **37** (see Section 3)
- Uplifts achieving target: **86**
- Regressions: **0**
- Neutral / no-change / NaN comparisons: **1**
- Ablation rows: **22**
- Benchmark wall-clock (excluding ablation): `8.6s`
- Ablation re-run wall-clock: `60.5s`

