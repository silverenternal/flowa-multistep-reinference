# Gaps: Where the Lean Formalisation Does Not Match Paper Claims

This file lists every place the Lean formalisation in
`/c/Users/31472/codes/noise-selected-rectification-lean/` is **incomplete**,
**diverges from the paper text**, or **explicitly delegates to the analytic
proof** without a Lean theorem.

All paper quotes are verbatim from
`NoiseSelectedRectification_EN.md` in the flowa repo. All Lean citations are
absolute `file:line` from the Lean repo root.

---

## Gap 1 — Paper Lemma 2's dominated-convergence step is analytic, not formalised

### Paper text (verbatim)

Paper section "Formal verification and reproducibility", `NoiseSelectedRectification_EN.md` substantive content on lines 335, 337, 339, 341 (the range 335–341 contains blank separators):

> `P1UniformlySeparatedCleanFibreClass.lean` proves the literal fibre and
> energy identities, common physical geometry, local isolated coercivity,
> and the residual-side exterior gap used in Lemma 5.
>
> The P2 uniformly-separated rescaling development proves the exact normal
> rescaling identity and its profile-independent exponent bound. The
> companion P2 periodic-sheet-law development additionally formalizes the
> dominated sheet-integral limit and ambient-observable limit for the
> periodic admissible subclass. **The periodicity-free dominated-convergence
> step in Lemma 2 remains the analytic argument written here.**
>
> The root packing sum, its uniform Gaussian cell integration, and the
> conversion of the literal gap into the integrated estimate of Lemmas 3–4
> are analytic parts of this manuscript; Lean supplies their geometric
> inputs, not a claimed countable-atlas theorem.

### What this means

The paper **explicitly disclaims** a Lean formalisation of Lemma 2's dominated
convergence in the **period-free** setting. The period-free
`P2ProfileSheetEvidence.lean:196` `profileSheetRescaledDensity_integral_tendsto`
proves the rescaled density → limit density on the rescaled window, and
`P2ProfileSheetObservable.lean:141` `inv_mul_closedProfileSheetTube_ambientObservable_numerator_tendsto`
proves the `ε^{-1} ∫_T φ p_ε → …` limit with bounded continuous `φ`. But the
*full* dominated-convergence step — including the *strict* profile-tube vs
*closed* profile-tube identification — is partially analytic. The Lean file
`P2ProfileSheetBoundary.lean` (lines 29–93) closes the gap for the strict-vs-
closed equality, so the missing step is now *narrower* than the paper text
suggests but the period-free analytic integration step (`∫ → (2π)^{-1/2}·…` 
via the explicit Gaussian integral `∫ e^{-u²(1+g²)/2} du = √(2π)/√(1+g²)`)
remains in the proof.

### Lean coverage

| Lean file | File:line | Status |
|---|---|---|
| `Research/NoiseSelectedRectification/P2ProfileSheetEvidence.lean` | 196 | `theorem profileSheetRescaledDensity_integral_tendsto` — proves `∫ density_ε → ∫ limit_density` (rescaled picture). |
| `Research/NoiseSelectedRectification/P2ProfileSheetObservable.lean` | 141 | `theorem inv_mul_closedProfileSheetTube_ambientObservable_numerator_tendsto` — proves `ε^{-1} ∫_T φ p_ε → limit` with `φ`. |
| `Research/NoiseSelectedRectification/P2ProfileSheetChangeOfVariables.lean` | 84, 105, 128 | `integralOn_image_sheetRescaling_eq`, `closedProfileSheetTube_integral_eq_epsilon_mul_rescaled`, `inv_mul_closedProfileSheetTube_evidence_tendsto` — the COV chain. |
| `Research/NoiseSelectedRectification/P2ProfileSheetBoundary.lean` | 29, 72, 81, 93 | Strict-vs-closed equality + the strict-tube version of the limit. |

The remaining step (paper line 184: "after multiplying by ‖φ‖_∞, is dominated
by ‖φ‖_∞ e^{-s²/2} e^{-u²/8}") is fully Leanised in `P2ProfileSheetEvidence.lean:42, 53, 73, 103, 196`. The "integrate over `u` to get `(2π)^{-1/2}/√(1+g(s)²)`" step (paper line 256) is **not** a single named Lean theorem.

---

## Gap 2 — Paper Proposition 3 assembly is analytic, not formalised

### Paper text (verbatim)

Paper line 341:

> **Normalization, uniform tightness, and bounded-Lipschitz convergence in
> Proposition 3 are analytic consequences of the four displayed estimates. No
> Lean theorem is cited as a substitute for this assembly.**

### What this means

The full "take φ ≡ 1 in (4)–(6) and divide" assembly of paper Proposition 3
(line 200–205) is **explicitly** not in Lean. The Lean machinery *proves all
the inputs* but does not produce a single `theorem proposition_3_assembly`
or `theorem theorem_1_assembly`.

### Lean coverage of inputs

| Lean file | File:line | Input proved |
|---|---|---|
| `CountableStratifiedGaussianPosteriorSelection.lean` | 177 | `relativeTotal_tendsto_leadingCoefficient` — the denominator limit (paper line 117). |
| `CountableStratifiedGaussianPosteriorSelection.lean` | 271 | `higherLayerPosteriorMass_tendsto_zero_of_tannery` — codim-2 mass → 0 (paper line 165). |
| `CountableStratifiedGaussianPosteriorSelection.lean` | 599 | `no_countable_selection_without_uniform_tightness` — tightness necessity. |
| `P1ActualPosteriorAssembly.lean` | 1290 | `actualNormalizedObservable_tendsto` — the normalised-observable limit. |
| `P1CertifiedPhysicalAtlasTheorem.lean` | 1505 | `certifiedPhysicalAtlas_tail_and_complement_package` — tail + complement (paper Proposition 5). |
| `P1CertifiedPhysicalAtlasTheorem.lean` | 109 | `certifiedStaticAtlas_denominator_tendsto_of_constant_reassembly` — denominator → A_g. |
| `P1CertifiedPhysicalAtlasTheorem.lean` | 885 | `certifiedPhysicalAtlas_posteriorLaw_package` — the full posterior-law bundle. |

The Lean equivalent of "the convergence against every bounded continuous φ
identifies the limit as ν_g" (paper line 200–205) is
`P1ActualPosteriorAssembly.lean:1290` `actualNormalizedObservable_tendsto` and
`P1ActualPosteriorAssembly.lean:1411` `normalizedObservable_tendsto_of_eventual_error_bounds`.
These theorems are *more general* than the paper's Proposition 3 (they apply
to arbitrary countable-stratum atlases, not just `F_g`), but **no Lean
theorem explicitly instantiates them to the paper's `F_g` to produce the
paper's exact Theorem 1 statement**.

---

## Gap 3 — The `A_g > 0` constant is not extracted as a named object

### Paper text

Paper line 161: `A_g := (2π)^{-1/2} ∫_ℝ e^{-s²/2}/√(1+g(s)²) ds`. Paper line 117:
"`A_g > 0`". Paper Corollary 1 (line 165): "`Z_{g,ε} ≥ C_1 ε`".

### Lean coverage

The Lean limit density `profileSheetRescaledLimitDensity`
(`P2ProfileSheetEvidence.lean:36`) is the unnormalised integrand
`e^{-s²/2} · e^{-u²(1+g(s)²)/2}`. After integrating over `u` and applying the
prior's `(2π)^{-1}` factor, this yields `A_g`. But:

- `A_g` is **not** named as a constant in Lean.
- The `(2π)^{-1/2}` factor is **not** extracted.
- The "positive evidence floor" claim (`Z_{g,ε} ≥ C_1 ε`) is formalised only
  abstractly via `P1CertifiedPhysicalAtlasTheorem.lean:424`
  `certifiedStaticAtlas_evidence_eventually_half_of_constant_reassembly`
  (`Z ≥ A_g/2 · ε` for small `ε`).

The paper's *exact* `A_g` (paper line 161) has **no Lean counterpart** as a
named constant.

---

## Gap 4 — The `B_g` general packing sum is asserted, not proved from scratch

### Paper text

Paper Lemma 5 (line 132): "`Σ_{z ∈ Z_g} e^{-z²/4} < ∞`". Paper proof (line 137):
"`Σ_{z∈Z_g} e^{-z²/4} ≤ (⌈1/d⌉+1) Σ_{k∈ℤ} e^{-((|k|-1)₊)²/4} < ∞`".

### Lean coverage

The Lean `summable_rootGaussian`
(`P2ProfileRootCountability.lean:326-335` per the user's INDEX update;
per my survey, line 326 in that file) is invoked as a hypothesis in
`P2ProfileIsolatedTubeMass.lean:274, 307`. The *counting argument*
`Σ_{k∈ℤ} e^{-((|k|-1)₊)²/4} < ∞` is **not displayed** as a separate Lean
theorem. The period-free packing is therefore *asserted* (via
`summable_rootGaussian`) rather than *proved from scratch* in the Lean
formalisation.

The periodic case `Z_g = πℤ` is proved from scratch in
`P2NSRSPeriodicGaussianPacking.lean:29, 43, 51`.

---

## Gap 5 — The `C_g` formula is `e^{ρ²/2}/a` in the paper but `2π/((1-ρ)² min{c²,1}/4)` in Lean

### Paper text

Paper line 188: "`a = (1-ρ)² min{c², 1} > 0`". Paper line 191:
"`C_g = e^{ρ²/2} / a`".

### Lean coverage

Lean `isolatedGaussianMassConstant` (`P2ProfileIsolatedTubeMass.lean:38`) is

```
def isolatedGaussianMassConstant (c rho : ℝ) : ℝ :=
  Real.sqrt (Real.pi / ((1 - rho) ^ 2 * c ^ 2 / 4)) *
    Real.sqrt (Real.pi / ((1 - rho) ^ 2 / 4))
```

which after simplification equals `2π / ((1-ρ)² min{c²,1}/4) = 8π / ((1-ρ)² min{c²,1})`.

The discrepancy comes from how the Lean proof integrates the per-cell
Gaussian: Lean uses `twoNormalGaussianProfile` (the standard two-normal
density `e^{-(u²/(2·α) + v²/(2·β))}`) and pulls out the full Gaussian mass
`2π·√(αβ)`. The paper (line 189) writes the integral as
`(2π)^{-1} · ∫ e^{-a(u²+v²)/(2ε²)} du dv = (2π)^{-1} · (2π/a) · ε²`,
which factors as `(ε²/a)` — but the paper then absorbs the `1/(2π)` prior
constant differently. The Lean constant is **larger** by a factor `4e^{ρ²/2}/(1-ρ)²`
*if you compare literally*, but the per-cell bound `ε² · exp(-r²/4) · C_g · B_g`
*matches* in both formulations because Lean factors `exp(-r²/4)` separately.

The Lean proof does NOT explicitly extract `C_g = e^{ρ²/2}/a` as a named
constant; instead the proof establishes the equivalent bound directly through
`integral_isolatedDensityMajorant` (line 167) and
`strictProfileRootTube_mass_le_rankTwoGaussian` (line 199).

---

## Gap 6 — The `e_ρ` constant differs by squaring

### Paper text

Paper line 128: "`e_ρ := min{ρ⁴, (1-ρ)²η²} > 0`".

### Lean coverage

Lean (`P2ProfileLiteralComplementGap.lean:49`, signature spans lines 49–53):

```
theorem energy_lower_bound_outside_strictProfileTubeUnion :
    ∃ rho eta, 0 < rho ∧ 0 < eta ∧
      ∀ z ∉ strictProfileTubeUnion profile rho,
        min (rho ^ 2 / 4) (eta ^ 2 / 4) ≤ profile.energy z
```

The Lean constant is `min(ρ²/4, η²/4)`, not `min(ρ⁴, (1-ρ)²η²)`. The
discrepancy is:

- `ρ⁴ → ρ²/4`: the paper's `ρ⁴` arises from `|y|² ≥ ρ²/4` combined with
  `|y|⁴ ≥ ρ⁴` (when y is far from 1, |y(y-1)|² = y²(y-1)² ≥ ρ⁴/4 because
  both |y| ≥ ρ and |y-1| ≥ ρ). The Lean bound `ρ²/4` is the *square root*
  of the paper's exponent.
- `(1-ρ)²η² → η²/4`: the `(1-ρ)²` factor is absorbed into the `1/4` from
  the `y` bound.

The Lean bound is **strictly stronger** than the paper's (smaller gap),
because `min(ρ²/4, η²/4) ≤ √(min(ρ⁴, (1-ρ)²η²))`. The exponential
`e^{-e_ρ/(2ε²)}` is therefore `e^{-η²/(8ε²)}` in Lean vs `e^{-e_ρ/(2ε²)}` in
the paper — but the Lean version is a *stronger* bound (larger negative
exponent).

---

## Gap 7 — No Lean proof of byte-determinism in any file

### What is byte-determinism?

The framework's `paper_quantities.py` documents its functions as "byte-stable":
"Two calls with identical inputs return bit-identical floats." This is a
property of the Python evaluator, not a Lean theorem.

### Lean coverage

**There is no Lean theorem that asserts byte-determinism of any framework
runtime.** The closest analogues are:

| Lean file | File:line | Statement | What it proves |
|---|---|---|---|
| `FlowA/HybridReflowEffectiveness.lean` | 87 | `theorem unchanged_source_and_condition_replay_the_same_endpoint` | Functional determinism (same input → same output), NOT byte-equality. |
| `FlowA/HybridReflowEffectiveness.lean` | 134 | `theorem consumed_identity_expert_is_also_conditionally_null` | Identity expert has no effect. |
| `FlowA/HybridReflowEffectiveness.lean` | 139 | `theorem consumed_identity_expert_cannot_change_deterministic_endpoint` | Determinism. |
| `FlowA/HybridReflowEffectiveness.lean` | 180 | `theorem changed_condition_without_rhs_sensitivity_leaves_endpoint_unchanged` | Determinism over condition changes. |
| `FlowA/HybridReflowEffectiveness.lean` | 188 | `theorem changed_condition_without_rhs_sensitivity_leaves_metric_unchanged` | Metric determinism. |
| `FlowA/HybridReflowEffectiveness.lean` | 199 | `theorem semantic_change_without_metric_sensitivity_does_not_imply_gain` | Semantic determinism. |
| `FlowAArchitectureProofs.lean` | 1269 | `theorem flowoe_python_runtime_symbols_are_mirrored` | Name-level mirroring (not byte-level). |
| `FlowAArchitectureProofs.lean` | 1274 | `theorem flowoe_runtime_schema_names_are_mirrored` | Name-level mirroring. |
| `FlowAArchitectureProofs.lean` | 1317 | `theorem flowoe_runtime_mirror_matches_python_symbols_and_schemas` | Combined mirror. |

The `FlowA/CurrentHybridReflowEvidence.lean` ledger contains SHA-256 hashes
as constants but **no theorem** that the framework produces these bytes.

---

## Gap 8 — No Lean proof of scheduler monotonicity (`SchedulerProtocol`)

### What is scheduler monotonicity?

The framework's `adaptive_reflow/schedule/` directory contains a
`SchedulerProtocol` (per `FILE_MAPPING.md`, `UNIVERSAL_MOLECULAR_MAPPING.md`).
Monotonicity is an invariant of this protocol.

### Lean coverage

**There is no Lean theorem that explicitly states "scheduler is monotonic"
or references a `SchedulerProtocol`.** The closest analogues are:

| Lean file | File:line | Statement | What it proves |
|---|---|---|---|
| `FlowAArchitectureProofs.lean` | 1237 | `theorem re_inference_freeze_is_compatible_with_mainline` | Re-inference state machine does not break mainline (qualitative monotonicity). |
| `FlowA/HybridReflowEffectiveness.lean` | 98 | `theorem deterministic_endpoint_change_requires_source_or_condition_change` | Endpoint function is monotone in `(source, condition)`. |
| `FlowA/HybridReflowEffectiveness.lean` | 167 | `theorem frozen_observable_cannot_improve_its_metric` | Frozen observable is monotone (cannot decrease below frozen metric). |
| `FlowA/HybridReflowEffectiveness.lean` | 297 | `theorem two_certified_target_gains_compose` | Gains compose monotonically. |
| `FlowA/HybridReflowEffectiveness.lean` | 305 | `theorem non_regression_is_transitive` | Transitivity. |
| `FlowA/HybridReflowEffectiveness.lean` | 313 | `theorem later_non_regressive_round_preserves_earlier_strict_gain` | Strict gains preserved by non-regression. |

The framework's `adaptive_reflow/contracts/schedule.py` has no direct Lean
counterpart.

---

## Gap 9 — Memory contracts (`MemoryContract`, `restart_memory`, `phase_state`) are NOT in Lean

### What's deleted

Per `gitStatus`:
```
D restart_memory.py
D restart_memory_types.py
D phase_state.py
D policy_authority.py
D policy_orchestrator.py
D mechanism_adapter.py
```

### Lean coverage

**No Lean file references `MemoryContract`, `restart_memory`, `phase_state`,
`policy_authority`, `policy_orchestrator`, or `mechanism_adapter`.** These
are framework-side abstractions; the Lean formalisation does not import or
re-encode them.

---

## Gap 10 — `BundleContains`, `BundleOwnership`, `BundleAllocation` are abstract in Lean

### What's in Lean

`FlowAArchitectureProofs.lean:916` defines `BundleContains`, `:960`
`MechanismUsableWithGeneratedObject`, `:964` `ConcreteBundleCovers`,
`:969` `FamilyHasDesignOwner`. These are type-level predicates, not
algorithmic bundle-management theorems.

### What's not in Lean

There is no Lean theorem that proves a *concrete* bundle assignment satisfies
all the framework's bundle-ownership invariants (the framework's
`adaptive_reflow/contracts/bundle.py` is a different layer).

---

## Gap 11 — Paper's "analytic argument written here" disclaimers

The paper has three explicit disclaimers:

1. **Line 337**: "The periodicity-free dominated-convergence step in Lemma 2
   remains the analytic argument written here." → see Gap 1.
2. **Line 339**: "The root packing sum, its uniform Gaussian cell
   integration, and the conversion of the literal gap into the integrated
   estimate of Lemmas 3–4 are analytic parts of this manuscript; Lean
   supplies their geometric inputs, not a claimed countable-atlas theorem."
   → see Gaps 4, 5, 6.
3. **Line 341**: "Normalization, uniform tightness, and bounded-Lipschitz
   convergence in Proposition 3 are analytic consequences of the four
   displayed estimates. No Lean theorem is cited as a substitute for this
   assembly." → see Gap 2.

These three disclaimers collectively mean **the Lean formalisation is not
machine-checked proof of Theorem 1**, only of selected inputs.

---

## Gap 12 — The framework's `paper_quantities.py` Python evaluators are NOT formalised in Lean

### What Python does

`paper_quantities.py` provides *numerical evaluators* using trapezoidal /
sign-change / min evaluators on a `[-K, K]` grid. The function bodies are
~300 lines total.

### What Lean does

The Lean formalisation works with the *literal* root set, the *literal*
`(2π)^{-1/2}` Gaussian integral, and the *literal* packing sum `Σ e^{-z²/4}`.
There is no Lean translation of the trapezoidal / sign-change algorithms.

### Implication

The Python evaluator `sheet_evidence_A` and the Lean `A_g` ingredient
machinery are **conceptually parallel but algorithmically distinct**. A
Lean proof that the Python evaluator converges to the Lean limit is **not
in scope** of either formalisation.

---

## Gap 13 — The sharpness example (Proposition 6) is the only "result" with a complete Lean counterpart

Paper line 343: "`P3PeriodicProfileSharpness.lean` formalizes the normalized
escaping posterior and its failure of tightness."

The Lean file (`Research/NoiseSelectedRectification/P3PeriodicProfileSharpness.lean`)
declares three theorems (lines 26, 30, 38) and three definitions
(`escaping_residual_is_smooth`, `escaping_integer_roots_are_regular`,
`local_regular_roots_do_not_imply_global_posterior_tightness`).
This is the **only** paper theorem whose full statement-and-proof is
encapsulated in a single Lean file.

---

## Gap 14 — Lean profiles do not include the radial-twist family

The Lean file `CountableStratifiedGaussianPosteriorSelection.lean:491`
defines `circlePointCountableData` (a circle point example) and proves
`circlePointPosteriorBarycenter_tendsto_circleVelocity` (line 508). However:

- The radial-twist machinery (`RadialTwist*.lean`, ~70 files) is
  *infrastructure* for a different formalisation thread (the "two-dimensional
  variable-Jacobian example" referenced in paper line 290).
- The radial-twist does **not** appear in paper Theorem 1 — it is a
  supplementary calibration, explicitly disclaimed at paper line 290:
  "Supplementary material contains Lean 4 formalizations of auxiliary
  calibrations (including a variable-Jacobian example and radial-complexity
  pairs). They are not used in the proof of Theorem 1."

---

## Gap 15 — No Lean proof that `currentFlowoERuntimeImplementation` produces the SHA-pinned bytes of `hybridEvidence*Sha256`

`FlowA/CurrentHybridReflowEvidence.lean` declares 50+ SHA-256 hashes as
constants (`hybridEvidenceHistoricalPanelSha256`, …,
`hybridEvidenceGNINACalibrationSha256`).
`FlowAArchitectureProofs.lean:974` defines `currentFlowoERuntimeImplementation`
as a concrete runtime.

**There is no Lean theorem asserting that
`currentFlowoERuntimeImplementation` produces exactly the bytes recorded in
`hybridEvidence*Sha256`.** This would require (a) formalising the runtime
semantics byte-by-byte, and (b) comparing against the hash literals. Neither
is done.

---

## Summary table

| Gap | Paper claim | Lean coverage | Status |
|---|---|---|---|
| 1 | Lemma 2 dominated convergence | Partial | Rescaled density → limit density proved; final integration step analytic. |
| 2 | Proposition 3 assembly | Partial | All inputs proved; no single `theorem proposition_3_assembly`. |
| 3 | `A_g > 0` constant | Partial | Ingredients proved; constant not named. |
| 4 | `B_g < ∞` general packing | Partial | Asserted via `summable_rootGaussian`; periodic case proved from scratch. |
| 5 | `C_g = e^{ρ²/2}/a` formula | Partial | Lean constant is `2π/((1-ρ)² min{c²,1}/4)`; equivalent bound proved. |
| 6 | `e_ρ = min{ρ⁴, (1-ρ)²η²}` | Partial | Lean bound is `min(ρ²/4, η²/4)`; **stronger** than paper. |
| 7 | Byte-determinism | None | Only functional determinism. |
| 8 | Scheduler monotonicity | Partial | Qualitative analogues; no `SchedulerProtocol`. |
| 9 | `MemoryContract`, `restart_memory`, etc. | None | Not imported, not re-encoded. |
| 10 | Bundle ownership invariants | Abstract only | Type-level predicates; no concrete runtime assertion. |
| 11 | Paper's three explicit disclaimers | Honoured | The Lean repo matches the paper's stated scope. |
| 12 | Python `paper_quantities.py` | None | Different formalisation strategy. |
| 13 | Proposition 6 (sharpness) | Complete | Single Lean file. |
| 14 | Radial-twist family | Infra only | Not used in Theorem 1. |
| 15 | SHA-pinned byte equality | None | Hashes are constants; runtime-byte equivalence not asserted. |
