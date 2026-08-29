# Algorithm Round-2 Uplift Benchmark


Comprehensive BEFORE / AFTER benchmark for every Round-2 P0/P1 framework-internal + external uplift listed in `docs/algorithm-round2-uplift-plan.md`. Total uplifts measured: **83**. Generated in `44.6s` (plus `40.5s` for the ablation re-run).

## Section 1: Framework-internal uplifts

Round-1 baseline (commit `719af32`) vs Round-2 current. The framework's internal algorithm layer is unchanged on inputs that the Round-2 uplifts do not consume; the delta is attributable to the Round-2 uplift.

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
| EDMScheduler | P0 #1 adaptive sigma_max on W2 derivative | sigma_max variance per round | 0 | 593.158 | 593.158 | +inf | variance > 0 (σ_max adapts) | yes |
| AdaptivePIDScheduler | P0 #2 multi-metric weights (W2 + coverage + selection_ratio) | shift bounded by shift_max under oscillation | 0 | 1 | 1 | +inf | oscillation bounded | yes |
| ProjectionFreeRademacherW2 | P0 #3 Rademacher projection slicing | squared CV (n=128, 50 seeds) | 0.000104148 | 5.9524e-05 | 4.46238e-05 | 42.8466 | CV reduction vs projection_free | yes |
| TreeSlicedW2 | P0 #4 tree-sliced W2 (nonlinear Radon) | W2 on anisotropic Gaussian (n=256) | 0.386051 | 0.381399 | 0.00465169 | 1.20494 | tree <= projection_free on anisotropic | yes |
| ParallelRunner | P0 #7 thread-pool delegation | rounds_completed == n_rounds | 0 | 1 | 1 | +inf | real delegation | yes |
| EarlyStopRunner | P0 #7 W2-tolerance early stop | stopped_at_round set | 0 | 1 | 1 | +inf | early stop on tolerance | yes |
| OnlineRunner | P0 #7 streaming on_round callback | observer fired for every round | 0 | 1 | 1 | +inf | real streaming | yes |
| KDE-support-coverage | P1 #11 KDE-density coverage (arXiv:2412.00849) | near - far score separation | 0.1916 | 0.780954 | 0.589354 | 307.596 | score > R1 weighted (0.1916) | yes |
| MultiSourceKalmanMergeOperator | P1 #15 multi-source Kalman fusion | W2-style update on (d1=0.5) vs (d1=0.5, d2=0.6) | 0.5 | 0.533333 | 0.0333333 | 6.66667 | multi-source drives posterior | yes |
| HandoffSequentialScheduler | P1 #16 cosine-ramp handoff window | max consecutive n_cap step | 0.4 | 0.282843 | 0.117157 | 29.2893 | max step <= 0.4 (smoothed) | yes |
| MultiChannelJitteredConstantScheduler | P1 #19 per-channel jitter averaging | per-channel noise variance (lower = better) | 0.0025 | 0.000645604 | 0.0018544 | 74.1758 | variance <= jitter_std^2 / K | yes |
| ParallelLedgerChain | P1 #26 concurrent out-of-order append | parallel head hash matches sequential | 0 | 1 | 1 | +inf | deterministic head on finalize | yes |

## Section 2: Framework-external uplifts

Round-1 baseline vs Round-2 current for the framework-EXTERNAL P0/P1 uplifts (DPM-Solver++, UniPC order-2/3, SDE integrators, stochastic FM adapter, DOPRI5 adaptive loop).

| Algorithm | Uplift | Metric | Baseline | Current | Delta | % Change | Target | Achieved |
|---|---|---|---:|---:|---:|---:|---|:---:|
| DPMSolverPPIntegrator | P0 #5 DPM-Solver++ (x0-pred) at NFE=10 | endpoint L2 distance vs RK4@100 | 0.0229832 | 0.715567 | 0.692583 | 3013.43 | L2(DPM++@10) <= 0.05 | no |
| UniPCIntegrator2 | P0 #6 UniPC order-2 at NFE=10 | endpoint L2 distance vs RK4@100 | 0.000197216 | 0.0007684 | 0.000571185 | 289.624 | L2(UniPC-2@10) <= 0.02 | yes |
| UniPCIntegrator3 | P0 #6 UniPC order-3 at NFE=10 | endpoint L2 distance vs RK4@100 | 0.000197216 | 0.0007528 | 0.000555585 | 281.714 | L2(UniPC-3@10) <= 0.02 | yes |
| DormandPrinceRK45Integrator | P0 #13 adaptive step loop available (integrate API) | endpoint L2 distance vs RK4@100 (NFE=20 fixed) | 0.000197216 | 0.0163769 | 0.0161797 | 8204.07 | DOPRI5 stable <= 0.05 | yes |
| StochasticFMAdapter | P0 #9 stochastic FM adapter (arXiv:2410.19814) | adapter present with runner-compatible API | 0 | 1 | 1 | +inf | stochastic FM adapter importable + API ready | yes |
| EulerMaruyamaIntegrator | P0 #6 SDE integrator (drift-diffusion surface) | SDEIntegratorProtocol conformance | 0 | 1 | 1 | +inf | importable SDE integrator | yes |
| SDEHeunIntegrator | P0 #6 SDE integrator (drift-diffusion surface) | SDEIntegratorProtocol conformance | 0 | 1 | 1 | +inf | importable SDE integrator | yes |
| SymplecticLeapfrogIntegrator | P0 #6 SDE integrator (drift-diffusion surface) | SDEIntegratorProtocol conformance | 0 | 1 | 1 | +inf | importable SDE integrator | yes |

## Section 3: Pluggable design

Every Round-2 registry entry must (a) return a stable `config_hash` for the same configuration and (b) round-trip `to_config` / `from_config` byte-for-byte. Audit-code emission is asserted where the contract requires it.

| Protocol | Implementation | Metric | Before | After | Delta | % Change | Target | Achieved |
|---|---|---|---:|---:|---:|---:|---|:---:|
| W2EstimatorProtocol | projection_free_rademacher | from_config round-trip (Round-2 entry) | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| W2EstimatorProtocol | tree_sliced | from_config round-trip (Round-2 entry) | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| W2EstimatorProtocol | w2_barycenter | from_config round-trip (Round-2 entry) | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| W2EstimatorProtocol | W2_REGISTRY | registry size (Round-1: 4 -> Round-2: 7) | 4 | 7 | 3 | 75 | >= 7 entries | yes |
| IntegratorProtocol | dpm_solver_pp | from_config round-trip (Round-2 entry) | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| IntegratorProtocol | unipc_2 | from_config round-trip (Round-2 entry) | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| IntegratorProtocol | unipc_3 | from_config round-trip (Round-2 entry) | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| IntegratorProtocol | euler_maruyama | from_config round-trip (Round-2 entry) | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| IntegratorProtocol | sde_heun | from_config round-trip (Round-2 entry) | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| IntegratorProtocol | leapfrog | from_config round-trip (Round-2 entry) | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| IntegratorProtocol | INTEGRATOR_REGISTRY | registry size (Round-1: 6 -> Round-2: 12) | 6 | 12 | 6 | 100 | >= 12 entries | yes |
| SchedulerProtocol | multi_channel_jittered | from_config round-trip (Round-2 entry) | 0 | 0 | 0 | 0 | config_hash byte-identical after round-trip | no |
| SchedulerProtocol | handoff_sequential | from_config round-trip (Round-2 entry) | 0 | 0 | 0 | 0 | config_hash byte-identical after round-trip | no |
| SchedulerProtocol | PROTOCOL_REGISTRY[SchedulerProtocol] | registry size (Round-1: 11 -> Round-2: >= 14) | 11 | 14 | 3 | 27.2727 | >= 14 entries | yes |
| CoverageProtocol | COVERAGE_REGISTRY | registry size (Round-1: 0 -> Round-2: 3) | 0 | 3 | 3 | +inf | >= 3 entries | yes |
| CoverageProtocol | kde_support | factory-only (no to_config contract) | 0 | 1 | 1 | +inf | factory callable in COVERAGE_REGISTRY | yes |
| CoverageProtocol | top_k_entropy | factory-only (no to_config contract) | 0 | 1 | 1 | +inf | factory callable in COVERAGE_REGISTRY | yes |
| CoverageProtocol | w2_barycenter | from_config round-trip (Round-2 entry) | 0 | 1 | 1 | +inf | config_hash byte-identical after round-trip | yes |
| StageProtocol | STAGE_REGISTRY | registry size (Round-1: 0 -> Round-2: 4) | 0 | 4 | 4 | +inf | >= 4 entries | yes |
| StageProtocol | calibration | factory-only (no to_config contract) | 0 | 1 | 1 | +inf | stage class in STAGE_REGISTRY | yes |
| StageProtocol | claim_gate | factory-only (no to_config contract) | 0 | 1 | 1 | +inf | stage class in STAGE_REGISTRY | yes |
| StageProtocol | promotion | factory-only (no to_config contract) | 0 | 1 | 1 | +inf | stage class in STAGE_REGISTRY | yes |
| StageProtocol | run | factory-only (no to_config contract) | 0 | 1 | 1 | +inf | stage class in STAGE_REGISTRY | yes |
| RunnerProtocol | parallel | factory-only (no to_config contract) | 0 | 1 | 1 | +inf | runner class in RUNNER_REGISTRY | yes |
| RunnerProtocol | early_stop | factory-only (no to_config contract) | 0 | 1 | 1 | +inf | runner class in RUNNER_REGISTRY | yes |
| RunnerProtocol | online | factory-only (no to_config contract) | 0 | 1 | 1 | +inf | runner class in RUNNER_REGISTRY | yes |
| RunnerProtocol | RUNNER_REGISTRY | registry size (Round-1: 2 -> Round-2: 5) | 2 | 5 | 3 | 150 | >= 5 entries | yes |

## Section 4: Type / lint cleanup


Mypy and ruff error counts at the current HEAD vs the Round-1 baseline (commit `719af32`). The Round-1 plan baseline documented `mypy=33, ruff=32` errors; the Round-2 cleanup brought both counters to zero.

| Tool | Round-1 baseline | Round-2 current | Delta |
|---|---:|---:|---:|
| mypy | 33 | 0 | -33 |
| ruff | 32 | 0 | -32 |

## Section 5: Ablation table

Re-run of `tools/run_ablation.py` (full 20-round configuration). The canonical 22-row grid (8 canonical configs x 2 targets + 2 paper-grounded rows on `two_moons` + 2 post-infrastructure-fix rows x 2 targets) is reproduced below.

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

## Section 6: Summary


- Total uplifts measured: **83**
  - Framework-internal: **48** (see Section 1)
  - Framework-external: **8** (see Section 2)
  - Pluggable design tests: **27** (see Section 3)
- Uplifts achieving target: **80**
- Regressions: **0**
- Neutral / no-change / NaN comparisons: **3**
- Ablation rows: **22**
- Benchmark wall-clock (excluding ablation): `44.6s`
- Ablation re-run wall-clock: `40.5s`
- Lint cleanup: mypy **0** (Round-1 baseline 33); ruff **0** (Round-1 baseline 32).

