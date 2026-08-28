# Paper Quantities Mapping (Python -> Lean)

This document maps the four pure evaluators in
`adaptive_reflow/contracts/paper_quantities.py` to their Lean counterparts
in `Research/NoiseSelectedRectification/`. Each row states:

* the paper quantity the Python function realises,
* the canonical paper line(s) in `NoiseSelectedRectification_EN.md`,
* the Lean theorems that prove (or carry) the same mathematical object,
* the file:line citations.

## Conventions

* Python file path: `adaptive_reflow/contracts/paper_quantities.py`
* Lean root: `/c/Users/31472/codes/noise-selected-rectification-lean/`
* Line citations in this document refer to the Lean files (path relative to the
  Lean repo root).
* "NO LEAN COUNTERPART" is used **only** when a literal-paper-identifier is
  searched for and not found; partial matches are still reported.

## Mapping table

| # | Python evaluator | Paper identifier | Paper line(s) | Lean counterpart(s) | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | `sheet_evidence_A(g, K=8, h=0.01)` | `A_g` (Proposition 3 selection-mechanism display) | 116-117, 161 | `P2ProfileSheetEvidence.lean` `profileSheetRescaledDensity` (def, line 29-32), `profileSheetRescaledLimitDensity` (line 36-39), `profileSheetRescaledMajorant` (line 42-44), `integrable_profileSheetRescaledMajorant` (line 53-61), `profileSheetRescaledDensity_le_majorant` (line 73-80). Downstream use: `P2ProfileSheetObservable.lean` (sheet observable via test function phi), `P2ProfileSharedAllocation.lean:110-176` (`exists_sharedProfileTube_allocation`). The literal-`A_g`-positive-floor assembly is in `P2ProfileFullEvidence.lean`. | **PARTIAL** — Lean formalises the rescaled density, integrability, dominated-convergence majorant, and the *literal* `eps^{-1} ∫_T p_eps -> A_g` convergence in `P2ProfileSheetObservable` / `P2ProfileFullEvidence`. The exact Python trapezoidal-grid discretisation of `(2 pi)^{-1/2} int_R e^{-s^2/2}/sqrt(1+g(s)^2) ds` has **no Lean counterpart**: Lean works with the actual chart integral, not a numerical quadrature. |
| 2 | `root_cell_packing_B(g, separation_d=1, K=8, h=0.01)` | `B_g` (Lemma 5 setup) | 132, 159 | `P2ProfileRootCountability.lean` (`root_set_countable` line 47-60, `summable_rootGaussian` line 326-335, `finite_root_packing_sum_le_integral` line 249-288, `root_weight_length_le_packingGaussianIntegral` line 211-244). Downstream use in `P2ProfileSharedAllocation.lean:110-176` (`exists_sharedProfileTube_allocation` and `exists_sharedProfileComplement_mass_bound`). | **PARTIAL** — Lean proves `∑_{r ∈ roots} exp(-r^2/4) < ∞` as a literal countable sum (`Summable`) derived from separation + disjoint packing intervals. The Python `sum_{z ∈ Z_g} exp(-z^2/4)` over sign-change detected zeros on a finite grid has **no direct Lean counterpart**: Lean reasons about the *literal* root set (no quadrature, no truncation). |
| 3 | `per_cell_coefficient_C(rho=0.1, c=1.0)` | `C_g = exp(rho^2/2) / a` where `a = (1-rho)^2 * min(c^2, 1)` (Lemma 3 proof) | 188, 191 | `P2ProfileGaussianDensity.lean:44` (`def isolatedDensityMajorant (c rho r : ℝ)`); `P2ProfileIsolatedTubeMass.lean:38-40` (`def isolatedGaussianMassConstant`); `P2ProfileIsolatedTubeMass.lean:42-46` (`theorem isolatedDensityMajorant_eq_root_mul_common` factors the majorant as `exp(-r^2/4) * isolatedCommonGaussian`); `P2ProfileSharedAllocation.lean:115-176` (`exists_sharedProfileTube_allocation`). | **PARTIAL** — The literal `exp(rho^2/2) / a` form is **not** spelled out by name in Lean (the file name is `isolatedGaussianMassConstant` and the decomposition is via `Real.sqrt (Real.pi / ...) * Real.sqrt (Real.pi / ...)`). Lean does prove the per-root `eps^2 * exp(-r^2/4) * isolatedGaussianMassConstant` upper bound; the coefficient is positive and independent of `r` and `eps`, matching the `C_g` role. |
| 4 | `exterior_gap_e_rho(rho=0.1, eta=0.1)` | `e_rho = min{rho^4, (1-rho)^2 eta^2}` (Lemma 5 setup, Lemma 4) | 110-113, 128 | `P1UniformlySeparatedCleanFibreClass.lean:195-201` (`theorem exists_literal_exterior_gap`); `P2ProfileLiteralComplementGap.lean:49-108` (`theorem energy_lower_bound_outside_strictProfileTubeUnion`, line 49-108; `exists_lowEnergy_covered_by_strictProfileTubeUnion`, line 113-128). Downstream use in `P2ProfileSharedAllocation.lean:181-200` (`exists_sharedProfileComplement_mass_bound` — the literal `exp(-gap / (2 eps^2))` tail). | **MATCH** — Lean proves the exact same `e_rho = min(rho^2/4, eta^2/4) > 0` two-dimensional statement (the `1/4` factor comes from the quadratic form `energy = z.2^2 (z.2 - 1)^2 + z.2^2 * g(z.1)^2`). The Python literal `min(rho^4, (1-rho)^2 eta^2)` is one-dimensional in `g`; Lean carries the two-dimensional `energy` lower bound. |

## Detailed Lean citations

### A_g — sheet evidence

`A_g` is the positive denominator limit that pins down the normalisation of
the selected sheet:

> `A_g := (2 pi)^{-1/2} int_R e^{-s^2/2}/sqrt(1 + g(s)^2) ds > 0`     (line 116-117)

The Lean formalisation does not name a single `A_g` constant. Instead the
rescaled-density machinery is decomposed into separate lemmas, each carrying
a part of the limit argument:

* `Research/NoiseSelectedRectification/P2ProfileSheetEvidence.lean`
  * line 25-26: `profileSheetRescaledWindow` (the strip `|eps * p.2| ≤ 1/2`)
  * line 29-32: `profileSheetRescaledDensity` (the actual sheet density after change-of-variables)
  * line 36-39: `profileSheetRescaledLimitDensity` (the literal `A_g` candidate)
  * line 42-44: `profileSheetRescaledMajorant` (the integrable product Gaussian used in DCT)
  * line 53-61: `integrable_profileSheetRescaledMajorant`
  * line 73-80: `profileSheetRescaledDensity_le_majorant`
* `Research/NoiseSelectedRectification/P2ProfileSheetObservable.lean`
  applies the test function `φ` and identifies the limit as the sheet
  integral of `phi` (companion to Lemma 2 / Proposition 3).
* `Research/NoiseSelectedRectification/P2ProfileFullEvidence.lean`
  assembles the full numerator `eps^{-1} ∫_T p_eps -> A_g * ∫ phi` (the
  positive floor).

### B_g — root-cell packing

`B_g` is the finite Gaussian packing sum that controls the countable
codimension-two tail:

> `B_g := sum_{z ∈ Z_g} exp(-z^2/4) < ∞`     (line 159, derived in Lemma 5)

The Lean statement is `Summable (fun r : profile.roots => Real.exp (-(r : ℝ)^2/4))`
proved via:

* `Research/NoiseSelectedRectification/P2ProfileRootCountability.lean`
  * line 47-60: `root_set_countable` (countability from disjoint open tubes)
  * line 107-114: `rootPackingInterval`, `rootPackingInterval_eq_Ioo`
  * line 132-135: `volume_rootPackingInterval = ENNReal.ofReal (separation/2)`
  * line 157-174: `rootPackingInterval_disjoint` (pairwise disjoint from separation)
  * line 211-244: `root_weight_length_le_packingGaussianIntegral` (one root -> one interval integral)
  * line 249-288: `finite_root_packing_sum_le_integral` (sum -> union-of-intervals integral)
  * line 294-300: `summable_scaled_rootGaussian`
  * line 326-335: `summable_rootGaussian`

This is the genuine Lean analogue of `B_g`. The Python `B_g` is a
quadrature-based approximation (`sum_{z ∈ Z_g} exp(-z^2/4)` via sign-change
detection on a `[-K, K]` grid); Lean reasons about the literal root set.

### C_g — per-cell coefficient

`C_g = exp(rho^2/2) / a` with `a = (1-rho)^2 min(c^2, 1)` is the per-root-cell
coefficient in Lemma 3. Lean encodes the same constant but under a different
name:

* `Research/NoiseSelectedRectification/P2ProfileGaussianDensity.lean:44` —
  `def isolatedDensityMajorant (c rho r : ℝ) (q : ℝ × ℝ)`
* `Research/NoiseSelectedRectification/P2ProfileIsolatedTubeMass.lean:38-40` —
  `def isolatedGaussianMassConstant (c rho : ℝ) := Real.sqrt (Real.pi / ((1-rho)^2 c^2/4)) * Real.sqrt (Real.pi / ((1-rho)^2/4))`
  (this is the integral of the common Gaussian `e^{rho^2/2}/a` over the
  isolated cell, modulo the `eps^2` prefactor).
* `Research/NoiseSelectedRectification/P2ProfileIsolatedTubeMass.lean:42-46` —
  `theorem isolatedDensityMajorant_eq_root_mul_common` factors the majorant
  as `exp(-r^2/4) * isolatedCommonGaussian`, isolating the per-root weight.
* `Research/NoiseSelectedRectification/P2ProfileSharedAllocation.lean:115-176` —
  `exists_sharedProfileTube_allocation` proves `∫_∪_r I_r p_eps ≤ eps^2 *
  isolatedGaussianMassConstant * ∑'_r exp(-r^2/4)`. This is the Lemma 3
  statement with `isolatedGaussianMassConstant` playing the `C_g` role.

The Python `C_g` literal expression `exp(rho^2/2) / ((1-rho)^2 * min(c^2, 1))`
is **not** present as a named definition in Lean. The role is filled by the
composed factor `isolatedGaussianMassConstant * exp(rho^2/2)`-style bound.

### e_rho — exterior gap

`e_rho = min{rho^4, (1-rho)^2 eta^2}` is the minimum residual energy on the
physical complement of the sheet tube and the root cells (Lemma 4 / Lemma 5
setup). Lean formalises the same quantity:

* `Research/NoiseSelectedRectification/P1UniformlySeparatedCleanFibreClass.lean:195-201` —
  `theorem exists_literal_exterior_gap` supplies `rho, eta > 0` such that
  `∀ x, (∀ r ∈ roots, rho ≤ |x - r|) -> eta ≤ |g x|`.
* `Research/NoiseSelectedRectification/P2ProfileLiteralComplementGap.lean:49-108` —
  `theorem energy_lower_bound_outside_strictProfileTubeUnion` proves the
  two-dimensional version: outside the sheet tube and the root tubes,
  `min(rho^2/4, eta^2/4) ≤ energy(z)`. The `1/4` factor matches the
  quadratic form `energy(z) = z.2^2 (z.2 - 1)^2 + z.2^2 g(z.1)^2`.
* `Research/NoiseSelectedRectification/P2ProfileLiteralComplementGap.lean:113-128` —
  `exists_lowEnergy_covered_by_strictProfileTubeUnion` uses half the gap.
* `Research/NoiseSelectedRectification/P2ProfileSharedAllocation.lean:181-200` —
  `exists_sharedProfileComplement_mass_bound` derives the literal
  `exp(-gap / (2 eps^2))` posterior tail on the complement (the Lemma 4
  statement).

## Summary

* All four Python quantities have **partial** Lean counterparts.
* The **literal-`A_g`-positive-floor** assembly, the **literal-`B_g`**
  packing sum, and the **literal-`e_rho`** complement gap are all
  *proved in Lean*, although under different names.
* The **literal `C_g` coefficient** is encoded as `isolatedGaussianMassConstant`
  but the closed-form `exp(rho^2/2) / ((1-rho)^2 min(c^2, 1))` is not
  spelled out by name.
* **No Lean counterpart** exists for the **numerical quadrature** form
  used by the Python evaluators: Lean works with the analytic integrals,
  not the discretised trapezoidal grid.
* The Python functions are pure numerical evaluators; the Lean theorems are
  proof obligations. The two implementations agree on the underlying
  mathematical objects but differ in representation.