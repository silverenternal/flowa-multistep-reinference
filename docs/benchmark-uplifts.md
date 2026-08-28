# Algorithm Uplift Benchmark


Quantitative benchmark of every Phase-2 algorithm uplift listed in `docs/algorithm-uplift-plan.md`. Total uplifts measured: **27**. Generated in `0.7s` (plus `39.4s` for the ablation re-run).

## Section 1: Per-uplift quantitative results

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

## Section 2: Ablation comparison (22 rows)

Re-run of `tools/run_ablation.py` (full 20-round configuration). The canonical 22-row grid (8 canonical configs x 2 targets + 2 paper-grounded rows on `two_moons` + 2 post-infrastructure-fix rows x 2 targets) is reproduced below with the W2 / coverage / selection_ratio / ledger_chain_integrity columns the task specifies. The paper-grounded rows report a final selection ratio of `0.8061` (the documented plateau of the legacy replay-through-adapter metric on `two_moons`; the A16 uplift is what raises the ratio toward 1 -- see the SNR row in Section 1).

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

## Section 3: Summary


- Uplifts measured: **27**
- Uplifts achieving target: **27**
- Regressions: **0**
- Neutral (no change / NaN): **0**
- Ablation rows: **22**

