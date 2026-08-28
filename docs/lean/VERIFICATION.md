# Lean Survey Verification Report (Round 2)

## Summary
- Writer files claimed: 5
- Writer files found: 5
- Total Lean files in repo: 485
- Total citations spot-checked: ~30 (12 in THEOREM_1_MAPPING, 6 in PAPER_QUANTITIES_MAPPING, 5+ in FLOWA_INTEGRATION, 5+ paper quotes in GAPS)
- Citations confirmed: ~28
- Citations refuted: 0
- Fabrications found: 0
- Verdict: **PASS** (with one minor cosmetic issue — see Issues section)

## Per-file checks

### docs/lean/INDEX.md
- Exists: yes
- Line count: 612 (substantial — well above 100 line minimum)
- Total Lean files claimed: 485. **Confirmed** (actual `find … -name "*.lean" | wc -l` = 485)
- File counts per directory confirmed:
  - Top-level `.lean` files: writer says 5 (FlowAArchitectureProofs.lean, lakefile.lean, FlowA/*4 files). Actual: 7 `.lean` files at repo root (FlowAArchitectureProofs.lean, lakefile.lean, scripts/NSRTrustedBoundary.lean + 4 FlowA/). **Writer omits `scripts/NSRTrustedBoundary.lean` (433 lines) from the "top-level" count but does list it as a row**, so net claim "Top-level files (5 files, 2,659 lines)" understates by 1 file. Minor bookkeeping inconsistency, not a fabrication.
  - FlowA/: writer says 4 files / 886 lines. **Confirmed** (71+81+140+594 = 886).
  - CommutatorSafeChannelFreezing/: writer says 6 files. **Confirmed**.
  - FlowOEExpertAggregation/: writer says 3 files / ~1,800 lines. **Confirmed** (469+328+1097 = 1,894, writer's "~1,800" is approximate but reasonable).
  - StratifiedChemicalTransport/: writer says 8 files. **Confirmed** (7 Formal/* + StratifiedChemicalTransport.lean).
  - NoiseSelectedRectification/: writer says 461 files. **Confirmed** (`find … -path "*NoiseSelectedRectification*"` = 461).
- Spot-checked line counts on individual files:
  - FlowA/CurrentHybridReflowEvidence.lean: writer says 71 → actual 71 ✓
  - FlowA/CurrentTrainingDataSignificance.lean: writer says 81 → actual 81 ✓
  - FlowA/DataSignificance.lean: writer says 140 → actual 140 ✓
  - FlowA/HybridReflowEffectiveness.lean: writer says 594 → actual 594 ✓
  - FlowAArchitectureProofs.lean: writer says 1773 → actual 1773 ✓
  - scripts/NSRTrustedBoundary.lean: writer says 433 → actual 433 ✓
  - CountableStratifiedGaussianPosteriorSelection.lean: writer says 626 → actual 626 ✓
  - P1ActualPosteriorAssembly.lean: writer says 1721 → actual 1721 ✓
  - RadialTwistMidpointInfiniteRadialFibers.lean: writer says 2064 → actual 2064 ✓
  - 50+ Research files individually enumerated (mostly medium-size, with specific line counts on the larger ones).
- Random spot-checks of file paths in INDEX.md against actual filesystem: all 10 sampled paths exist.
- Lean files listed: All 485 enumerated via per-directory clusters. Fabrications found in INDEX: **0**.
- Verdict on INDEX: **PASS** — minor bookkeeping issue only ("5 top-level" should be 7 if counting nested scripts/NSRTrustedBoundary.lean).

### docs/lean/PAPER_QUANTITIES_MAPPING.md
- Exists: yes
- Line count: 139
- Rows in mapping table: **4** (sheet_evidence_A, root_cell_packing_B, per_cell_coefficient_C, exterior_gap_e_rho) — matches the 4 pure evaluators in `adaptive_reflow/contracts/paper_quantities.py` (verified via `grep "def sheet_evidence_A|def root_cell_packing_B|def per_cell_coefficient_C|def exterior_gap_e_rho"` → all 4 found at lines 64, 135, 226, 271).
- Citations spot-checked:
  - `P2ProfileSheetEvidence.lean:25` `def profileSheetRescaledWindow` → **CONFIRMED** (line 25: `def profileSheetRescaledWindow (epsilon : ℝ) : Set (ℝ × ℝ)`).
  - `P2ProfileSheetEvidence.lean:73` `profileSheetRescaledDensity_le_majorant` → **CONFIRMED** (line 73: `theorem profileSheetRescaledDensity_le_majorant`).
  - `P2ProfileIsolatedTubeMass.lean:38` `def isolatedGaussianMassConstant` → **CONFIRMED** (line 38: `def isolatedGaussianMassConstant (c rho : ℝ) : ℝ :=` with the cited body `Real.sqrt (Real.pi / ((1 - rho) ^ 2 * c ^ 2 / 4)) * Real.sqrt (Real.pi / ((1 - rho) ^ 2 / 4))`).
  - `P2ProfileIsolatedTubeMass.lean:42` `theorem isolatedDensityMajorant_eq_root_mul_common` → **CONFIRMED** (line 42: `theorem isolatedDensityMajorant_eq_root_mul_common`).
  - `P2ProfileGaussianDensity.lean:44` `def isolatedDensityMajorant` → **CONFIRMED** (line 44: `def isolatedDensityMajorant (c rho r : ℝ) (q : ℝ × ℝ) : ℝ :=`).
  - `P2ProfileLiteralComplementGap.lean:49` `theorem energy_lower_bound_outside_strictProfileTubeUnion` → **CONFIRMED** (line 49: `theorem energy_lower_bound_outside_strictProfileTubeUnion` with the exact conclusion `min (rho ^ 2 / 4) (eta ^ 2 / 4) ≤ profile.energy z`).
  - `P1UniformlySeparatedCleanFibreClass.lean:195` `theorem exists_literal_exterior_gap` → **CONFIRMED** (line 195: `theorem exists_literal_exterior_gap (profile : UniformlySeparatedSimpleRootProfile)`).
  - `P2ProfileLiteralComplementGap.lean:113` `exists_lowEnergy_covered_by_strictProfileTubeUnion` → **CONFIRMED**.
  - `P2ProfileSharedAllocation.lean` line range 110-176 with `exists_sharedProfileTube_allocation` → **CONFIRMED** (theorem located in that range; line 113 contains the theorem statement).
- Body of `def isolatedGaussianMassConstant` reproduced verbatim in the mapping — **EXACT MATCH** with the actual Lean source.
- Verdict on PAPER_QUANTITIES_MAPPING: **PASS** — every cited file:line resolves to a real declaration with the cited body.

### docs/lean/THEOREM_1_MAPPING.md
- Exists: yes
- Line count: 316
- Citations spot-checked (12):
  - `P2ProfileSheetChangeOfVariables.lean:24` `def closedProfileSheetTube` → **CONFIRMED** (line 24: `def closedProfileSheetTube : Set (ℝ × ℝ) := {z | |z.2| ≤ 1 / 2}`).
  - `P2ProfileSheetChangeOfVariables.lean:28` `def sheetRescalingDerivative` → **CONFIRMED**.
  - `P2ProfileSheetChangeOfVariables.lean:31` `theorem hasFDerivAt_sheetRescaling` → **CONFIRMED**.
  - `P2ProfileSheetChangeOfVariables.lean:105` `theorem closedProfileSheetTube_integral_eq_epsilon_mul_rescaled` → **CONFIRMED** (line 105 contains the theorem signature; line 105-120 contains the body).
  - `P2ProfileSheetEvidence.lean:25` `def profileSheetRescaledWindow` → **CONFIRMED**.
  - `P2ProfileSheetEvidence.lean:36` `def profileSheetRescaledLimitDensity` → **CONFIRMED** (line 36 contains `Real.exp (-(p.2 ^ 2 * (profile.g p.1 ^ 2 + 1)) / 2)`).
  - `P2ProfileSheetEvidence.lean:196` `theorem profileSheetRescaledDensity_integral_tendsto` → **CONFIRMED** (line 196 starts `theorem profileSheetRescaledDensity_integral_tendsto`).
  - `P2ProfileSheetObservable.lean:141` `theorem inv_mul_closedProfileSheetTube_ambientObservable_numerator_tendsto` → **CONFIRMED**.
  - `P2ProfileIsolatedTubeMass.lean:38` `def isolatedGaussianMassConstant` → **CONFIRMED**.
  - `P2ProfileRootCountability.lean:326` `theorem summable_rootGaussian` → **CONFIRMED** (line 326: `theorem summable_rootGaussian` with the cited body).
  - `CountableStratifiedGaussianPosteriorSelection.lean:39` `structure CountableStratifiedData` → **CONFIRMED** (line 39: `structure CountableStratifiedData (ι : Type*) [Countable ι] where`).
  - `CountableStratifiedGaussianPosteriorSelection.lean:86` `theorem summable_leadingTerm` → **CONFIRMED**.
  - `CountableStratifiedGaussianPosteriorSelection.lean:91` `theorem leadingCoefficient_pos` → **CONFIRMED**.
  - `CountableStratifiedGaussianPosteriorSelection.lean:177` `theorem relativeTotal_tendsto_leadingCoefficient` → **CONFIRMED**.
  - `CountableStratifiedGaussianPosteriorSelection.lean:271` `theorem higherLayerPosteriorMass_tendsto_zero_of_tannery` → **CONFIRMED**.
  - `CountableStratifiedGaussianPosteriorSelection.lean:599` `theorem no_countable_selection_without_uniform_tightness` → **CONFIRMED**.
  - `P1ActualPosteriorAssembly.lean:1290` `theorem actualNormalizedObservable_tendsto` → **CONFIRMED** (line 1290 contains the theorem; body shows `Tendsto (fun epsilon : ℝ => numerator epsilon / denominator epsilon) (𝓝[>] (0 : ℝ)) (𝓝 (numeratorLimit / denominatorLimit))` — matches the paper's "divide numerator by denominator" assembly step).
- All 17 spot-checked citations resolved to real declarations.
- Verdict on THEOREM_1_MAPPING: **PASS** — citations are uniformly accurate.

### docs/lean/FLOWA_INTEGRATION.md
- Exists: yes
- Line count: 337
- File coverage: writer claims 5 files; **5 FlowA files exist** (FlowA/CurrentHybridReflowEvidence.lean, FlowA/CurrentTrainingDataSignificance.lean, FlowA/DataSignificance.lean, FlowA/HybridReflowEffectiveness.lean + FlowAArchitectureProofs.lean at root).
- Spot-checked line counts:
  - CurrentHybridReflowEvidence.lean: writer says 71 → actual 71 ✓
  - CurrentTrainingDataSignificance.lean: writer says 81 → actual 81 ✓
  - DataSignificance.lean: writer says 140 → actual 140 ✓
  - HybridReflowEffectiveness.lean: writer says 594 → actual 594 ✓
  - FlowAArchitectureProofs.lean: writer says 1773 → actual 1773 ✓
- Spot-checked declarations:
  - CurrentHybridReflowEvidence.lean:11-24 SHA-256 hashes → **CONFIRMED** (`hybridEvidenceHistoricalPanelSha256`, `hybridEvidenceSemanticExpertSha256`, `hybridEvidenceTrainingProbeSha256`, `hybridEvidenceGNINACalibrationSha256`, `hybridEvidenceActivePlanSha256` all present at lines 11-24).
  - CurrentTrainingDataSignificance.lean:11-21 → **CONFIRMED** (lines 11-21 contain the certificate definition `currentTrainingDataSignificanceCertificate` with `trainRows := 2792, devRows := 277`, all four `OverlapCount := 0`).
  - DataSignificance.lean:14-18 `structure FamilyCoverage` → **CONFIRMED**.
  - DataSignificance.lean:20-52 `structure TrainingDataCertificate` → **CONFIRMED**.
  - DataSignificance.lean:54-59 `FamilyCoverage.Significant` → **CONFIRMED**.
  - DataSignificance.lean:61-68 `NonToyDataEvidence` with thresholds `trainRows ≥ 2000`, `devRows ≥ 200`, `trainUniqueTargets ≥ 2000`, `trainUniqueScaffolds ≥ 1000` → **CONFIRMED** (note: writer said `devUniqueScaffolds ≥ 150` which appears in actual line 67 — slight imprecision, writer's claim is `trainUniqueScaffolds ≥ 1000, devUniqueScaffolds ≥ 150`).
  - HybridReflowEffectiveness.lean:87 `theorem unchanged_source_and_condition_replay_the_same_endpoint` → **CONFIRMED** (actual line 87 contains the theorem).
  - HybridReflowEffectiveness.lean:134 `theorem consumed_identity_expert_is_also_conditionally_null` → **CONFIRMED**.
  - HybridReflowEffectiveness.lean:139 `theorem consumed_identity_expert_cannot_change_deterministic_endpoint` → **CONFIRMED**.
  - HybridReflowEffectiveness.lean:167 `theorem frozen_observable_cannot_improve_its_metric` → **CONFIRMED**.
  - HybridReflowEffectiveness.lean:180 `theorem changed_condition_without_rhs_sensitivity_leaves_endpoint_unchanged` → **CONFIRMED**.
  - HybridReflowEffectiveness.lean:188 `theorem changed_condition_without_rhs_sensitivity_leaves_metric_unchanged` → **CONFIRMED**.
  - HybridReflowEffectiveness.lean:199 `theorem semantic_change_without_metric_sensitivity_does_not_imply_gain` → **CONFIRMED**.
  - HybridReflowEffectiveness.lean:297 `theorem two_certified_target_gains_compose` → **CONFIRMED** (at line 296-298).
  - HybridReflowEffectiveness.lean:305 `theorem non_regression_is_transitive` → **CONFIRMED** (around line 306).
  - HybridReflowEffectiveness.lean:313 `theorem later_non_regressive_round_preserves_earlier_strict_gain` → **CONFIRMED**.
  - FlowAArchitectureProofs.lean:23-28 `inductive MetricFamily` with `materialization, posebustersGeometry, druglikeness, bindingContact` → **CONFIRMED**.
- Verdict on FLOWA_INTEGRATION: **PASS** — file:line citations are accurate.

### docs/lean/GAPS.md
- Exists: yes
- Line count: 183
- Paper quotes spot-checked:
  - **Gap 1** quotes "lines 335-341" of paper. Actual paper lines 335, 337, 339 contain the cited text. Lines 336, 338, 340 are blank. **Quote is verbatim; line range "335-341" overstates by 2 blank lines** — quote text itself matches the source exactly. Gap 2 then cites "line 341" which is correct (the Proposition 3 sentence).
  - **Gap 2** quote: "Normalization, uniform tightness, and bounded-Lipschitz convergence in Proposition 3 are analytic consequences of the four displayed estimates. No Lean theorem is cited as a substitute for this assembly." → **EXACT MATCH** with paper line 341.
  - **Gap 3** claim "Paper line 161: A_g := (2π)^{-1/2} ∫_ℝ e^{-s²/2}/√(1+g(s)²) ds" → **CONFIRMED** (paper line 161 contains exactly this definition).
  - **Gap 3** claim "Paper line 117: A_g > 0" → **CONFIRMED** (paper line 116-117 displays `A_g = (2π)^{-1/2}... > 0`).
  - **Gap 3** claim "Paper Corollary 1 (line 165): Z_{g,ε} ≥ C_1 ε" → **CONFIRMED** (paper line 165 contains `Z_{g,\varepsilon}\geq C_1\varepsilon`).
  - **Gap 4** claim "Paper Lemma 5 (line 132): Σ_{z ∈ Z_g} e^{-z²/4} < ∞" → **CONFIRMED** (paper line 132 contains `$\sum_{z\in Z_g}e^{-z^2/4}<\infty$`).
  - **Gap 5** claim "Paper line 188: a = (1-ρ)² min{c², 1} > 0" → **CONFIRMED** (paper line 188 area contains `Put $a=(1-\rho)^{2}\min\{c^{2},1\}>0$`).
  - **Gap 5** claim "Paper line 191: C_g = e^{ρ²/2} / a" → **CONFIRMED** (paper line 191 area contains `one may take $C_g=e^{\rho^{2}/2}/a$`).
  - **Gap 6** claim "Paper line 128: e_ρ := min{ρ⁴, (1-ρ)²η²} > 0" → **CONFIRMED** (paper line 128 contains exactly this).
- Lean-citation spot-checks in GAPS:
  - `P2ProfileSheetEvidence.lean:196` → **CONFIRMED**.
  - `P2ProfileSheetObservable.lean:141` → **CONFIRMED**.
  - `P2ProfileSheetBoundary.lean:29, 72, 81, 93` → writer marks "(mid)" but doesn't pin down each line. Spot-checked: file exists with 4 distinct theorems. Acceptable.
  - `P2ProfileRootCountability.lean:326-335` `summable_rootGaussian` → **CONFIRMED**.
  - `P2ProfileIsolatedTubeMass.lean:38` `def isolatedGaussianMassConstant` → **CONFIRMED**.
  - `P2ProfileLiteralComplementGap.lean:53` `theorem energy_lower_bound_outside_strictProfileTubeUnion` (writer says `:53` in code block, mapping table at line 49-108) → minor inconsistency between text (line 53) and table (49-108), but both file and theorem name are correct.
- Verdict on GAPS: **PASS** — paper quotes are accurate. Lean citations are accurate.

## Specific issues (minor, non-fabricating)

1. **INDEX.md "top-level" count inconsistency**: writer says "Top-level files (5 files, 2,659 lines)" but the repo root actually has 7 `.lean` files when counting `scripts/NSRTrustedBoundary.lean` (the writer does include NSRTrustedBoundary as a row, just not under the "top-level" heading). Net effect: the "5 files" header is slightly misleading; the listed file count (FlowAArchitectureProofs.lean, lakefile.lean, 4 FlowA/* files) totals 6, not 5. NSRTrustedBoundary at 433 lines is listed separately. Cosmetic, not a fabrication.

2. **GAPS.md Gap 1 line range**: writer claims "lines 335-341" but the substantive quoted text actually spans paper lines 335, 337, 339 (lines 336, 338, 340 are blank; line 341 belongs to Gap 2's quote). The quoted text itself is verbatim; only the line-range label is loose. Cosmetic.

3. **GAPS.md Gap 6 line reference**: writer cites `P2ProfileLiteralComplementGap.lean:53` for the theorem (in the code block at "Lean (`P2ProfileLiteralComplementGap.lean:53`)") but the table at line 49-108 also lists it. Both refer to the same theorem (verified). Minor: the theorem header actually begins at line 49, with `ρ, η` exists quantified at lines 51-52, and the body at 53+. The cited `:53` is the inside of the theorem body; not strictly the declaration line but the writer is consistent within their own doc.

None of the above are fabrications. They are line-range imprecision / internal consistency nits. All five files exist with substantial content, citations are real, paper quotes are verbatim or near-verbatim.

## Verdict

**PASS.** All 5 writer files exist with the claimed content. Spot-checking ~30 citations across the five files yielded 0 refutations and 0 fabrications. The paper text quotes in GAPS.md are verbatim (modulo blank-line accounting in one line range). The Python function names in PAPER_QUANTITIES_MAPPING.md exactly match the 4 functions in `adaptive_reflow/contracts/paper_quantities.py`. All file:line citations to Lean resolve to real declarations. The minor issues identified are cosmetic (line-range labels in INDEX and GAPS) and do not constitute errors in the survey itself.

The writer has produced a substantially accurate Lean 4 formalisation survey. The previous FAIL verdict was because no files existed; this retry has delivered five well-cited documents.