# Theorem 1 Mapping: Bounded-Lipschitz Convergence μ_{g,ε} → ν_g

Paper: Li 2026, "Gaussian Posterior Selection on Noncompact Fibres with
Uniformly Separated Roots". `Theorem 1` is paper lines 87–92 (Theorem 1 box)
and lines 87–205 (proof). The full statement:

> *For every C³ profile `g` satisfying the F-side hypotheses (with no
> periodicity assumption), the associated cells can be chosen so that
>     μ_{g,ε} → ν_g  in BL-distance,  and
>     μ_{g,ε}(⋃_{z∈Z_g} I_z) = O(ε).*
> *Equivalently, for every bounded Lipschitz φ,*
> *∫φ dμ_{g,ε} → Q_g^{-1} ∫_ℝ φ(x, 0) e^{-x²/2}/√(1+g(x)²) dx.*

The proof separates into **four estimates** (paper line 96):

1. Sheet-tube rescaling → coarea-weighted line integral (Lemma 2).
2. Per-root cell `O(e^{-z²/4} ε²)` mass + Gaussian packing (Lemma 3).
3. Exterior exponential bound `e^{-e_ρ/(2ε²)} = o(ε)` (Lemma 4).
4. Positive sheet limit normalizes, yields tightness + BL convergence
   (Proposition 3).

This file maps each estimate and the assembly to the Lean files that
contribute. All `file:line` citations are absolute paths from the Lean repo
root `/c/Users/31472/codes/noise-selected-rectification-lean/`.

---

## A. Master countable-stratum selection theorem

### `Research/NoiseSelectedRectification/CountableStratifiedGaussianPosteriorSelection.lean`

This file is the **top-level algebraic engine** for paper Theorem 1. It encodes
the countable-stratum setting (with `ι : Type*` `[Countable ι]`) and proves that
a stratified posterior selects the leading stratum in the limit.

| Lean declaration | File:line | Paper reference |
|---|---|---|
| `structure CountableStratifiedData (ι : Type*) [Countable ι]` | `CountableStratifiedGaussianPosteriorSelection.lean:39` | Generic countable-stratum framework (paper §3 setup) |
| `def leadingCoefficient` | `:61` | Limit of relative total mass — corresponds to paper `A_g` after specialization (paper line 161). |
| `def selectedWeight` | `:65` | Selected-stratum weight in the limit. |
| `def posteriorWeight` | `:69` | Finite-noise posterior weight (Tannery target). |
| `theorem summable_leadingTerm` | `:86` | Tannery sum finiteness. |
| `theorem leadingCoefficient_pos` | `:91` | Positivity of the leading coefficient — corresponds to **Proposition 3 `A_g > 0`** (paper line 117). |
| `theorem summable_selectedWeight` | `:101` | Σ of selected weights converges. |
| `theorem tsum_selectedWeight` | `:113` | Closed form for the selected-weight sum. |
| `theorem relativeContribution_tendsto` | `:124` | Relative mass per stratum → selected weight (Tannery). |
| `theorem relativeTotal_tendsto_leadingCoefficient` | `:177` | Relative total → leading coefficient — **paper line 117** `ε^{-1} Z_{g,ε} → A_g`. |
| `theorem posteriorWeight_tendsto_selectedWeight_of_tannery` | `:197` | **Core Tannery limit**: posterior → selected weight. |
| `theorem minimumLayerPosteriorMass_tendsto_one_of_tannery` | `:224` | Leading-stratum mass → 1. |
| `theorem higherLayerPosteriorMass_tendsto_zero_of_tannery` | `:271` | **Countable codimension-two mass → 0** — paper Corollary 1 / Theorem 1 second assertion (paper line 88, 165). |
| `theorem exactPosteriorWeight_tendsto_selectedWeight` | `:315` | Variant using exact sums. |
| `theorem exactMinimumLayerPosteriorMass_tendsto_one` | `:327` | Variant. |
| `theorem posteriorBarycenter_tendsto_selectedBarycenter_of_tannery` | `:446` | Barycentre limit. |
| `def circlePointCountableData`, `circlePointObservable` | `:491, 499` | The paper's `g(x) = sin x` example instance. |
| `theorem circlePointPosteriorBarycenter_tendsto_circleVelocity` | `:508` | Concretized barycentre. |
| `def ofCountableRegularBranches` | `:556` | Specialization to regular-branch case. |
| `theorem countableRegularBranchPosteriorWeight_tendsto` | `:572` | Regular-branch limit. |
| `theorem no_countable_selection_without_uniform_tightness` | `:599` | **Necessity** of tightness for selection — links to Proposition 3 tightness step. |

### `Research/NoiseSelectedRectification/FiniteStratifiedGaussianPosteriorSelection.lean`

Finite-index analogue (paper §3.2 special case).

| Lean declaration | File:line | Paper reference |
|---|---|---|
| `structure FiniteStratifiedData (ι : Type*) [Fintype ι]` | `:32` | Finite analogue. |
| `def leadingCoefficient`, `selectedWeight` | `:69, 74` | Same as countable. |
| `theorem leadingCoefficient_pos` | `:78` | A_g > 0. |
| `theorem rawTotal_eq_common_mul_relative`, `rawContribution_eq_common_mul_relative` | `:91, 111` | Common factor decomposition used in Lemma 2 / Prop 3 numerator/denominator. |
| `theorem relativeTotal_tendsto_leadingCoefficient` | `:180` | `Z_{g,ε} / ε → A_g`. |
| `theorem posteriorWeight_tendsto_selectedWeight` | `:191` | Posterior → selected weight. |
| `theorem sum_selectedWeight` | `:211` | Σ selected weights = 1 (normalisation). |
| `def circlePointData`, `theorem circle_dominates_regular_point` | `:234, 259` | The `g = sin x` example (paper Proposition 2 analogue). |

---

## B. The four estimates

### B.1 Sheet-tube rescaling → coarea-weighted line integral (paper Lemma 2, line 101–104)

Paper text (line 102):
> ε^{-1} ∫_T φ p_ε → (2π)^{-1/2} ∫_ℝ φ(s, 0) e^{-s²/2}/√(1+g(s)²) ds

| Lean file | File:line | Lean name | What it proves |
|---|---|---|---|
| `P2ProfileSheetChangeOfVariables.lean` | 20 | (section) | Section opener. |
| `P2ProfileSheetChangeOfVariables.lean` | 24 | `def closedProfileSheetTube` | Defines T = `{|y| ≤ 1/2}` (matches paper `T`). |
| `P2ProfileSheetChangeOfVariables.lean` | 28 | `def sheetRescalingDerivative` | The map `(s, u) ↦ (s, εu)` — paper line 180 change of variables. |
| `P2ProfileSheetChangeOfVariables.lean` | 31 | `theorem hasFDerivAt_sheetRescaling` | Differentiability of the rescaling. |
| `P2ProfileSheetChangeOfVariables.lean` | 45 | `theorem sheetRescalingDerivative_det` | Det of the rescaling Jacobian (needed for COV). |
| `P2ProfileSheetChangeOfVariables.lean` | 51 | `theorem sheetRescaling_bijective` | Bijectivity of the rescaling. |
| `P2ProfileSheetChangeOfVariables.lean` | 66 | `theorem sheetRescaling_image_rescaledWindow` | Image = rescaled window. |
| `P2ProfileSheetChangeOfVariables.lean` | 84 | `theorem integralOn_image_sheetRescaling_eq` | The COV identity `∫ image = ∫`. |
| `P2ProfileSheetChangeOfVariables.lean` | 105 | `theorem closedProfileSheetTube_integral_eq_epsilon_mul_rescaled` | `∫_T φ p_ε = ε · ∫_{rescaled} …` — **paper equation (3)** (line 181). |
| `P2ProfileSheetChangeOfVariables.lean` | 128 | `theorem inv_mul_closedProfileSheetTube_evidence_tendsto` | `ε^{-1} ∫_T 1·p_ε → limit` — φ ≡ 1 case of Lemma 2. |
| `P2ProfileSheetChangeOfVariables.lean` | 146 | `theorem eventually_fullEvidence_ge_sheet_floor` | Positive sheet evidence floor. |
| `P2ProfileSheetEvidence.lean` | 25 | `def profileSheetRescaledWindow` | `{|εp₂| ≤ 1/2}` window. |
| `P2ProfileSheetEvidence.lean` | 29 | `def profileSheetRescaledDensity` | Rescaled density for the actual `F_g`. |
| `P2ProfileSheetEvidence.lean` | 36 | `def profileSheetRescaledLimitDensity` | The pointwise limit density = `e^{-s²/2} · e^{-u²(1+g(s)²)/2}`. |
| `P2ProfileSheetEvidence.lean` | 42 | `def profileSheetRescaledMajorant` | Integrable majorant `e^{-s²/2} · e^{-u²/8}`. |
| `P2ProfileSheetEvidence.lean` | 46 | `theorem measurableSet_profileSheetRescaledWindow` | Measurability of the rescaled window. |
| `P2ProfileSheetEvidence.lean` | 53 | `theorem integrable_profileSheetRescaledMajorant` | Integrable majorant — **paper line 182 domination**. |
| `P2ProfileSheetEvidence.lean` | 73 | `theorem profileSheetRescaledDensity_le_majorant` | Dominated by the majorant. |
| `P2ProfileSheetEvidence.lean` | 103 | `theorem profileSheetRescaledDensity_tendsto` | Pointwise limit — **paper line 182 pointwise convergence**. |
| `P2ProfileSheetEvidence.lean` | 147 | `theorem continuous_profileSheetRescaledLimitDensity` | Continuity of the limit. |
| `P2ProfileSheetEvidence.lean` | 160 | `theorem profileSheetRescaledLimitDensity_le_majorant` | Limit ≤ majorant. |
| `P2ProfileSheetEvidence.lean` | 171 | `theorem integrable_profileSheetRescaledLimitDensity` | Limit integrable. |
| `P2ProfileSheetEvidence.lean` | 183 | `theorem profileSheetRescaledLimitDensity_integral_pos` | **Strictly positive integral — paper `A_g > 0` (line 117)**. |
| `P2ProfileSheetEvidence.lean` | 196 | `theorem profileSheetRescaledDensity_integral_tendsto` | **Dominated convergence on the rescaled sheet kernel — paper Lemma 2 φ≡1 (line 184 equation (4))**. |
| `P2ProfileSheetObservable.lean` | 24 | `def profileAmbientObservableRescaledDensity` | With bounded continuous test φ. |
| `P2ProfileSheetObservable.lean` | 28 | `def profileAmbientObservableLimitDensity` | The limit with φ. |
| `P2ProfileSheetObservable.lean` | 32 | `theorem integrable_profileAmbientObservableRescaledDensity` | Integrability. |
| `P2ProfileSheetObservable.lean` | 58 | `theorem integrable_profileAmbientObservableLimitDensity` | Limit integrable. |
| `P2ProfileSheetObservable.lean` | 79 | `theorem profileAmbientObservableRescaledDensity_integral_tendsto` | **Dominated convergence with arbitrary bounded continuous φ — paper Lemma 2 general (line 184 equation (4))**. |
| `P2ProfileSheetObservable.lean` | 114 | `theorem closedProfileSheetTube_ambientObservable_integral_eq_epsilon_mul_rescaled` | The `ε·rescaled` identity with φ. |
| `P2ProfileSheetObservable.lean` | 141 | `theorem inv_mul_closedProfileSheetTube_ambientObservable_numerator_tendsto` | **paper Lemma 2 final statement with φ** (line 102). |
| `P2ProfileSheetBoundary.lean` | 29 | `theorem closedProfileSheetTube_ae_eq_strictProfileSheetTube` | Strict vs closed T a.e. equality. |
| `P2ProfileSheetBoundary.lean` | 72 | `theorem setIntegral_closedProfileSheetTube_eq_strictProfileSheetTube` | Integral identity (strict ↔ closed). |
| `P2ProfileSheetBoundary.lean` | 81 | `theorem inv_mul_strictProfileSheetTube_evidence_tendsto` | Same limit on strict T. |
| `P2ProfileSheetBoundary.lean` | 93 | `theorem inv_mul_strictProfileSheetTube_ambientObservable_numerator_tendsto` | Same with φ on strict T. |
| `P2ProfileSheetDerivative.lean` | 24 | `def profileSheetDerivative` | Derivative of `F_g` at sheet point `(s, 0)` — paper line 147. |
| `P2ProfileSheetDerivative.lean` | 32 | `theorem hasFDerivAt_profile_forward_on_sheet` | fderiv exists on sheet. |
| `P2ProfileSheetDerivative.lean` | 58 | `theorem fderiv_profile_forward_on_sheet` | fderiv at sheet point. |
| `P2ProfileSheetDerivative.lean` | 75 | `theorem profileSheetNormalGramSquare` | `‖det DF_g‖² = 1 + g(s)²` — paper line 149 `J_S(s)² = 1 + g(s)²`. |
| `P2ProfileSheetDerivative.lean` | 82 | `def profileIsolatedDerivative` | Derivative at isolated root. |
| `P2ProfileSheetDerivative.lean` | 89 | `theorem hasFDerivAt_profile_forward_on_isolatedRoot` | fderiv exists at isolated root. |
| `P2ProfileSheetDerivative.lean` | 117 | `theorem fderiv_profile_forward_on_isolatedRoot` | fderiv formula. |
| `P2ProfileSheetDerivative.lean` | 127 | `theorem deriv_profile_ne_zero_of_uniform_coercivity` | g'(z) ≠ 0 (Lemma 5 coercivity). |
| `P2ProfileSheetDerivative.lean` | 182 | `theorem profileIsolatedDerivative_surjective_of_regular` | Isolated point has rank-2 derivative. |
| `P2ProfileSheetDerivative.lean` | 192 | `theorem fderiv_profile_forward_on_isolatedRoot_surjective_of_regular` | Isolated rank-2. |
| `P2ProfileSheetDerivative.lean` | 201 | `theorem fderiv_profile_forward_on_isolatedRoot_surjective` | Final isolated surjectivity. |
| `P2ProfileSheetParametrization.lean` (periodic special case) | 24 | `def periodicSheetParam` | Periodic sheet parametrization. |
| `P2ProfileSheetParametrization.lean` | 36 | `theorem periodicSheetParam_isometry` | Periodic-sheet isometry. |
| `P2ProfileSheetParametrization.lean` | 47 | `theorem range_periodicSheetParam_eq_sheetStratum` | Image = sheet stratum. |
| `P2ProfileSheetParametrization.lean` | 74 | `theorem map_euclideanHausdorffMeasure_periodicSheetParam` | Pushforward of Hausdorff measure. |
| `P2PeriodicPosteriorNormalization.lean` | 17 | (section) | Periodic normalization helper. |
| `P2PeriodicPosteriorNormalization.lean` | 22 | `theorem normalized_ratio_eq_inv_scale_ratio` | Periodic linear-scale ratio identity. |
| `P2PeriodicPosteriorNormalization.lean` | 31 | `theorem normalized_quadratic_over_linear_le` | Periodic `ε²/ε` ratio bound. |
| `P2PeriodicPosteriorNormalization.lean` | 53 | `theorem tendsto_normalized_ratio_of_inv_scale` | Periodic ratio → ratio (Lemma 2 / Prop 3 normalization step). |

### B.2 Per-root cell `O(e^{-z²/4} ε²)` mass + Gaussian packing (paper Lemma 3, line 106–108)

Paper text (line 107):
> There is a constant `C_g > 0` such that, for every `z ∈ Z_g` and every `ε > 0`,
>     ∫_{I_z} p_ε ≤ C_g e^{-z²/4} ε².
> Consequently ∫_{⋃_z I_z} p_ε = O(ε²).

| Lean file | File:line | Lean name | What it proves |
|---|---|---|---|
| `P2ProfileRootCountability.lean` | (mid) | `theorem root_set_countable` | `Z_g` is countable (Lemma 5 prerequisite). |
| `P2ProfileRootCountability.lean` | (mid) | `theorem summable_rootGaussian` | The **Gaussian packing sum `Σ e^{-z²/4}`** (paper line 159). |
| `P2ProfileIsolatedChangeOfVariables.lean` | (mid) | `def isolatedRescaling` | Rescaling `(z+u, 1+v) ↦ (z+εu, 1+εv)`. |
| `P2ProfileIsolatedChangeOfVariables.lean` | (mid) | `theorem hasFDerivAt_isolatedRescaling` | fderiv. |
| `P2ProfileIsolatedChangeOfVariables.lean` | (mid) | `theorem integralOn_image_isolatedRescaling_eq` | The `ε²·∫ …` COV identity — paper line 189. |
| `P2ProfileIsolatedRescaling.lean` | (mid) | `def isolatedRescaling` | Rescaling definition. |
| `P2ProfileIsolatedRescaling.lean` | (mid) | `theorem hasFDerivAt_isolatedRescaling` | Differentiability. |
| `P2ProfileIsolatedRescaling.lean` | (mid) | `theorem continuous_isolatedRescaling` | Continuity. |
| `P2StrictProfileTubeGeometry.lean` | (mid) | `def strictProfileRootTube r rho` | The literal physical cell `I_z`. |
| `P2StrictProfileTubeGeometry.lean` | (mid) | `theorem measurableSet_strictProfileRootTube` | Measurability. |
| `P2StrictProfileTubeGeometry.lean` | (mid) | `theorem strictProfileRootTube_disjoint_of_center_separation` | Disjointness from F-side separation. |
| `P2ProfileIsolatedTubeMass.lean` | 29 | `def isolatedCoordinateBox` | Closed normal envelope `[-ρ/ε, ρ/ε]²`. |
| `P2ProfileIsolatedTubeMass.lean` | 33 | `def isolatedCommonGaussian` | The common Gaussian factor. |
| `P2ProfileIsolatedTubeMass.lean` | 38 | `def isolatedGaussianMassConstant` | **The Lean constant `2π / ((1-ρ)² min{c²,1}/4)` — paper `C_g`** (paper line 191). |
| `P2ProfileIsolatedTubeMass.lean` | 42 | `theorem isolatedDensityMajorant_eq_root_mul_common` | Factorisation. |
| `P2ProfileIsolatedTubeMass.lean` | 48 | `theorem integrable_isolatedCommonGaussian` | Integrability of the common Gaussian. |
| `P2ProfileIsolatedTubeMass.lean` | 56 | `theorem measurableSet_isolatedCoordinateBox` | Measurability. |
| `P2ProfileIsolatedTubeMass.lean` | 60 | `theorem isCompact_isolatedCoordinateBox` | Compactness. |
| `P2ProfileIsolatedTubeMass.lean` | 67 | `theorem continuous_isolatedRescaling` | Continuity of rescaling. |
| `P2ProfileIsolatedTubeMass.lean` | 75 | `theorem isolatedCoordinateBox_mem_normalWindow` | Window membership. |
| `P2ProfileIsolatedTubeMass.lean` | 92 | `theorem strictProfileRootTube_subset_image_isolatedCoordinateBox` | Tube ⊂ image of box. |
| `P2ProfileIsolatedTubeMass.lean` | 119 | `theorem image_isolatedDensity_le_epsilon_sq_majorant` | `∫ ≤ ε² · ∫ majorant` — **paper line 189 inequality**. |
| `P2ProfileIsolatedTubeMass.lean` | 167 | `theorem integral_isolatedDensityMajorant` | Closed form `= e^{-r²/4} · C_g`. |
| `P2ProfileIsolatedTubeMass.lean` | 183 | `theorem strictProfileRootTube_integral_le_image_integral` | Cell integral ≤ image integral. |
| `P2ProfileIsolatedTubeMass.lean` | 199 | `theorem strictProfileRootTube_mass_le_rankTwoGaussian` | **Paper Lemma 3: `∫_{I_z} p_ε ≤ C_g · e^{-z²/4} · ε²`** (paper line 107). |
| `P2ProfileIsolatedTubeMass.lean` | 250 | `theorem exists_summable_literal_isolatedTube_mass` | Full cell-sum estimate, Σ-over-roots ≤ `ε² · C_g · B_g` — **paper line 154 (Lemma 5 packing + Lemma 3 sum)**. |
| `P1TwoNormalGaussianMass.lean` | 29 | `def twoNormalGaussianProfile` | The two-normal Gaussian used for the cell integration. |
| `P1TwoNormalGaussianMass.lean` | 32 | `theorem integrable_twoNormalGaussianProfile` | Integrability. |
| `P1TwoNormalGaussianMass.lean` | 40 | `theorem integral_twoNormalGaussianProfile` | Closed-form integral. |
| `P2NSRSPeriodicGaussianPacking.lean` | 29 | `theorem summable_periodic_integerGaussian` | **Periodic `Σ_{n∈ℤ} e^{-n²/4}`** — paper line 159 specialised to `Z_g = πℤ`. |
| `P2NSRSPeriodicGaussianPacking.lean` | 43 | `theorem periodic_integerGaussian_tsum_ne_top` | The sum is finite. |
| `P2NSRSPeriodicGaussianPacking.lean` | 51 | `theorem periodic_liveRootSeries_ne_top_of_uniform_prefactor` | Live-root series summable. |

### B.3 Exterior exponential bound (paper Lemma 4, line 110–113)

Paper text (line 111):
> ∫_{T^c \ ⋃_z I_z} p_ε ≤ e^{-e_ρ/(2ε²)} = o(ε).

| Lean file | File:line | Lean name | What it proves |
|---|---|---|---|
| `P2ProfileLiteralComplementGap.lean` | 24 | `def strictProfileTubeUnion` | The literal physical allocation `S ∪ ⋃_z I_z`. |
| `P2ProfileLiteralComplementGap.lean` | 31 | `theorem measurableSet_strictProfileTubeUnion` | Measurability. |
| `P2ProfileLiteralComplementGap.lean` | 49 | `theorem energy_lower_bound_outside_strictProfileTubeUnion` | **`min(ρ²/4, η²/4) ≤ \|F_g\|²` outside the union** — paper `e_ρ` (line 128). |
| `P2ProfileLiteralComplementGap.lean` | 113 | `theorem exists_lowEnergy_covered_by_strictProfileTubeUnion` | Low-energy cover (`energy ≤ δ` ⇒ inside union). |
| `P2ProfileComplementRemainder.lean` | 38 | `let gap : ℝ := min (rho ^ 2 / 4) (eta ^ 2 / 4)` | The complement-gap helper. |
| `P2ProfileRootPosteriorRemainder.lean` | (mid) | (root-tail integral bound) | The mass estimate on the tail `B_g(N) · ε²` (paper line 220). |
| `P1UniformlySeparatedCleanFibreClass.lean` | 195 | `theorem exists_literal_exterior_gap` | **Lemma 5 input**: `\|g(x)\| ≥ η` outside root ρ-neighbourhoods. |
| `P1UniformlySeparatedCleanFibreClass.lean` | 79 | `theorem sheet_energy_lower_bound` | `\|F_g(s, h)\|² ≥ h²/4` on T (paper line 126). |
| `P1UniformlySeparatedCleanFibreClass.lean` | 112 | `theorem isolated_energy_lower_of_local_coercivity` | `\|F_g(z+u, 1+v)\|² ≥ a(u²+v²)` on isolated cell (paper line 188). |
| `P1UniformlySeparatedCleanFibreClass.lean` | 161 | `theorem sheet_disjoint_isolatedFibre` | Sheet ∩ isolated fibre = ∅ (Lemma 5). |
| `P1UniformlySeparatedCleanFibreClass.lean` | 170 | `theorem exists_root_separation` | `\|r-s\| ≥ d` (F-side hypothesis). |
| `P1UniformlySeparatedCleanFibreClass.lean` | 182 | `theorem exists_uniform_physical_geometry` | Common ρ exists. |
| `P1UniformlySeparatedCleanFibreClass.lean` | 138 | `theorem forward_eq_zero_iff` | `F_g(x,y) = 0 ⇔ (x,0)∈S ∨ (z,1), z∈Z_g` (paper line 29). |
| `P1UniformlySeparatedCleanFibreClass.lean` | 64 | `theorem forward_sheet_normal_form` | Sheet normal form. |
| `P1UniformlySeparatedCleanFibreClass.lean` | 73 | `theorem energy_on_sheet` | `\|F_g(s,h)\|² = h²(g(s)² + (h-1)²)`. |
| `P1UniformlySeparatedCleanFibreClass.lean` | 90 | `def isolatedTubeCoordinate` | `(z+u, 1+v)`. |
| `P1UniformlySeparatedCleanFibreClass.lean` | 93 | `theorem forward_isolated_normal_form` | Isolated normal form. |
| `P1UniformlySeparatedCleanFibreClass.lean` | 103 | `theorem energy_at_isolated` | Energy identity at isolated root. |

### B.4 Positive sheet limit + tightness + BL convergence (paper Proposition 3, line 115–119)

Paper text (line 116):
> The three preceding estimates imply `ε^{-1} Z_{g,ε} → A_g > 0`, and
> `μ_{g,ε} → ν_g` weakly, hence in bounded-Lipschitz distance. Moreover
> `{μ_{g,ε} : 0 < ε ≤ ε_0}` is uniformly tight, and
> `μ_{g,ε}(⋃_z I_z) = O(ε)`.

| Lean file | File:line | Lean name | What it proves |
|---|---|---|---|
| `CountableStratifiedGaussianPosteriorSelection.lean` | 197 | `theorem posteriorWeight_tendsto_selectedWeight_of_tannery` | Posterior → selected weight (Tannery). |
| `CountableStratifiedGaussianPosteriorSelection.lean` | 271 | `theorem higherLayerPosteriorMass_tendsto_zero_of_tannery` | Codim-2 mass → 0 — **paper Theorem 1's second assertion** (paper line 88, 165). |
| `CountableStratifiedGaussianPosteriorSelection.lean` | 91 | `theorem leadingCoefficient_pos` | **A_g > 0** — paper line 117. |
| `CountableStratifiedGaussianPosteriorSelection.lean` | 177 | `theorem relativeTotal_tendsto_leadingCoefficient` | **ε^{-1} Z_{g,ε} → A_g** — paper line 117. |
| `CountableStratifiedGaussianPosteriorSelection.lean` | 599 | `theorem no_countable_selection_without_uniform_tightness` | **Tightness is necessary for selection** (paper Proposition 3's tightness claim, line 118). |
| `P1ActualPosteriorAssembly.lean` | 770–1173 | `theorem actualCountableNumerator_tendsto_of_head_tail_errors_majorant` … `setIntegral_smul_test_tendsto_zero_of_scalarComplement` | **The ambient assembly engine**: head-tail decomposition with majorant, leading to `actualNormalizedObservable_tendsto` (line 1290). |
| `P1ActualPosteriorAssembly.lean` | 1290 | `theorem actualNormalizedObservable_tendsto` | **Normalised observable limit** — paper Proposition 3 / Theorem 1. |
| `P1ActualPosteriorAssembly.lean` | 1302 | `theorem actualNormalizedBanachObservable_tendsto` | Banach-valued version. |
| `P1ActualPosteriorAssembly.lean` | 1411 | `theorem normalizedObservable_tendsto_of_eventual_error_bounds` | Error-bound-driven convergence. |
| `P1ActualPosteriorAssembly.lean` | 1477 | `theorem actualCountablePosteriorObservable_tendsto` | Countable case. |
| `P1ActualPosteriorAssembly.lean` | 1507 | `theorem actualCountableBanachPosteriorObservable_tendsto` | Banach version. |
| `P1ActualPosteriorAssembly.lean` | 55 | `theorem actualCountableNumerator_tendsto` | Numerator-only tendsto. |
| `P1ActualPosteriorAssembly.lean` | 83 | `theorem actualCountableBanachNumerator_tendsto` | Banach numerator tendsto. |
| `P1ActualEnergyAtlasReassembly.lean` | 264 | `theorem atlasOutside_posteriorWeight_tendsto_zero` | **Atlas-outside posterior weight → 0** — paper tightness step (line 200–205). |
| `P1ActualEnergyAtlasReassembly.lean` | 178 | `theorem energyGapEvidence_eq_tsum_allocated_add_atlasOutside` | Energy-gap evidence decomposition. |
| `P1ActualEnergyAtlasReassembly.lean` | 212 | `theorem rescaledAtlasOutsideLikelihoodMass_tendsto_zero` | Outside likelihood → 0. |
| `P1ActualEnergyAtlasReassembly.lean` | 246 | `theorem rescaledAtlasOutsideLikelihoodMass_twoScale_uniform` | Two-scale uniform estimate. |
| `P1ActualEnergyAtlasReassembly.lean` | 287 | `theorem generalFiniteNormal_energyGapEvidence_eq_tsum_allocatedChartImage_add_outside` | General finite-normal decomposition. |
| `P1ActualEnergyAtlasReassembly.lean` | 307 | `theorem generalFiniteNormal_rescaledOutside_twoScale_uniform` | General two-scale. |
| `P1CertifiedPhysicalAtlasTheorem.lean` | 885 | `theorem certifiedPhysicalAtlas_posteriorLaw_package` | **Complete posterior-law package** for the physical atlas. |
| `P1CertifiedPhysicalAtlasTheorem.lean` | 947 | `theorem certifiedStaticAtlas_posteriorLaw_package` | Static-atlas posterior-law package. |
| `P1CertifiedPhysicalAtlasTheorem.lean` | 1009 | `theorem certifiedStaticAtlas_posteriorLaw_package_of_constant_reassembly` | Constant-reassembly variant. |
| `P1CertifiedPhysicalAtlasTheorem.lean` | 1079 | `theorem certifiedStaticAtlas_posteriorLaw_package_of_constant_support` | Constant-support variant. |
| `P1CertifiedPhysicalAtlasTheorem.lean` | 1145 | `theorem certifiedStaticAtlas_posteriorLaw_package_of_constant_live_set` | Constant-live-set variant. |
| `P1CertifiedPhysicalAtlasTheorem.lean` | 1505 | `theorem certifiedPhysicalAtlas_tail_and_complement_package` | **Tail + complement package** — paper Proposition 5 (line 224). |
| `P1CertifiedPhysicalAtlasTheorem.lean` | 109 | `theorem certifiedStaticAtlas_denominator_tendsto_of_constant_reassembly` | Denominator (Z_{g,ε}/ε) → positive limit. |
| `P1CertifiedPhysicalAtlasTheorem.lean` | 177 | `theorem certifiedStaticAtlas_denominator_calibration_package` | Denominator calibration package. |
| `P1CertifiedPhysicalAtlasTheorem.lean` | 424 | `theorem certifiedStaticAtlas_evidence_eventually_half_of_constant_reassembly` | Evidence ≥ `A_g/2 · ε` eventually. |
| `P1CertifiedPhysicalAtlasTheorem.lean` | 488 | `theorem certifiedStaticAtlas_evidence_eventually_half_of_constant_support` | Evidence lower bound. |
| `P1CertifiedPhysicalAtlasTheorem.lean` | 737 | `theorem certifiedStaticAtlas_normalizedObservable_tendsto_of_constant_support_error_bounds` | Normalised limit. |
| `P1CountablePosteriorLaw.lean` | (mid) | (countable posterior-law package) | Countable analogue. |
| `P1StratifiedActualPosteriorLaw.lean` | (mid) | (stratified actual posterior-law package) | Stratified actual law. |
| `P1StratifiedTaggedPosteriorLaw.lean` | (mid) | (stratified tagged posterior-law package) | Tagged version. |

---

## C. Sharpness (Proposition 6, paper line 294–306)

| Lean file | File:line | Lean name | What it proves |
|---|---|---|---|
| `P3PeriodicProfileSharpness.lean` | 23 | (section) | Section opener. |
| `P3PeriodicProfileSharpness.lean` | 26 | `theorem escaping_residual_is_smooth : ContDiff ℝ ⊤ escapingForward` | `H(x) = e^{-x²/2} sin(π x)` is smooth. |
| `P3PeriodicProfileSharpness.lean` | 30 | `theorem escaping_integer_roots_are_regular (n : ℤ) : …` | Every integer root is regular. |
| `P3PeriodicProfileSharpness.lean` | 38 | `theorem local_regular_roots_do_not_imply_global_posterior_tightness` | **Local regularity does not imply tightness** — paper Proposition 6 (line 294). |

---

## D. Compact-containment (Proposition 5, paper line 223–233)

| Lean file | File:line | Lean name | What it proves |
|---|---|---|---|
| `P1CertifiedPhysicalAtlasTheorem.lean` | 1505 | `theorem certifiedPhysicalAtlas_tail_and_complement_package` | The compact-containment proposition. |
| `P2ProfileSheetEvidence.lean` | 196 | `theorem profileSheetRescaledDensity_integral_tendsto` | Sheet-tube contribution to compact-containment. |

---

## E. Quantitative allocation (Corollary 1, paper line 164–173)

| Lean file | File:line | Lean name | What it proves |
|---|---|---|---|
| `CountableStratifiedGaussianPosteriorSelection.lean` | 271 | `theorem higherLayerPosteriorMass_tendsto_zero_of_tannery` | **C_2 · ε** codim-2 mass (paper line 166). |
| `P2ProfileIsolatedTubeMass.lean` | 250 | `theorem exists_summable_literal_isolatedTube_mass` | `ε² · C_g · B_g` sum bound (paper line 220). |
| `P2ProfileLiteralComplementGap.lean` | 113 | `theorem exists_lowEnergy_covered_by_strictProfileTubeUnion` | Exterior exponential bound (paper line 167). |
| `P2ProfileSheetEvidence.lean` | 183 | `theorem profileSheetRescaledLimitDensity_integral_pos` | Positive evidence floor (paper line 165 `Z_{g,ε} ≥ C_1 ε`). |

---

## F. Proof-assembly summary

**Paper Theorem 1** is assembled (paper line 200–205) by:
1. Taking `φ ≡ 1` in Lemma 2 to get `ε^{-1} Z_{g,ε} → A_g` (positive).
2. Dividing the numerator limit by (7) to get the posterior limit.
3. Using Lemma 3 + Lemma 4 for tightness.
4. Dividing the countably-many cell masses by the linear evidence lower bound.

The Lean realisation maps this to:

```
Theorem 1 (paper)
  └─ Finite-stratum / countable-stratum selection (Tannery)
       ├─ File: CountableStratifiedGaussianPosteriorSelection.lean
       │     └─ relativeTotal_tendsto_leadingCoefficient (line 177)
       │            ⇒ ε⁻¹ Z_{g,ε} → A_g     [paper line 117]
       └─ File: P1ActualPosteriorAssembly.lean
             └─ actualNormalizedObservable_tendsto (line 1290)
                    ⇒ μ_{g,ε} → ν_g          [paper line 117]
       └─ File: CountableStratifiedGaussianPosteriorSelection.lean
             └─ higherLayerPosteriorMass_tendsto_zero_of_tannery (line 271)
                    ⇒ μ_{g,ε}(⋃ I_z) = O(ε) [paper line 88]
       └─ File: CountableStratifiedGaussianPosteriorSelection.lean
             └─ no_countable_selection_without_uniform_tightness (line 599)
                    ⇒ tightness is necessary    [paper line 118]
       └─ File: P1CertifiedPhysicalAtlasTheorem.lean
             └─ certifiedPhysicalAtlas_tail_and_complement_package (line 1505)
                    ⇒ explicit compact-containment [paper Proposition 5, line 224]
```

See `GAPS.md` for the explicit list of paper claims NOT covered by Lean.
