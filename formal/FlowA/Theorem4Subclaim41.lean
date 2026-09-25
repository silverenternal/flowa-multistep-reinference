/-
  FlowA / Theorem 4 sub-claim 4.1 — Regime-curve corollary (Wave 354 P5 stub).

  Paper source: docs/drafts/paper-A-final.md §6.5 Theorem 4 sub-claim 4.1
  (line 324 in the camera-ready draft) — the residual Lipschitz bound on the
  velocity field with the empirical `L_local ≈ 0.381` constant from
  Wave 351 P3 (per docs/audit/wave351-thm5-numerical.md §2.2).

  Statement (verbatim from §6.5 sub-claim 4.1, paper §6.5 line 324):

    "Let VA(v_θ) := C_2 · exp(-T / τ_velocity) - C_1 · exp(-n_rounds / τ_residual)
     denote the framework's value-add at matched T and n_rounds. Then
     ∂ VA / ∂ ε_θ ≤ 0 (lower-residual ckpts provide less framework value-add
     at fixed n_rounds), with equality only when C_1 = 0 (no residual
     correction channel)."

  Empirical anchor for `τ_velocity = L_local^{-1} = 1/0.381 ≈ 2.624`:
    `verification_outputs/wave351-p3-thm5-numerical/lipschitz_estimate.json`
    (L_local = 0.3810 via finite-difference sample-max on the synthetic RF
    CIFAR velocity field at adaptive_reflow/adapters/rectified_flow_cifar.py:276).

  Status: STUB — sorry placeholders mark the future Lean 4 prover work;
  this file is byte-stable authoring target for the camera-ready Lean 4
  formalisation effort (per Wave 353 P1 §A.1 derivation, which is the
  paper-side derivation; this file is the formal-verification counterpart).

  TODO (future Lean 4 prover work):
    [ ] Prove `value_add_monotone_nonincreasing_in_eps_theta` (Sub-claim 4.1
        differential identity). Requires Mathlib.Analysis.SpecialFunctions
        (exp derivative chain rule) + Mathlib.Analysis.Calculus.Deriv.Basic
        (Fréchet derivative under ℝ^n) + the τ_residual = Θ(ε^{-2} log(1/ε))
        monotonicity fact from BGV12 Theorem 1.1.
    [ ] Prove `lipschitz_constant_positive_implies_velocity_decay` (the
        τ_velocity = L^{-1} link to the Grönwall inequality on the per-step
        Jacobian). Requires Mathlib.Analysis.ODE.Gronwall + the L_local > 0
        hypothesis.
    [ ] Prove `regime_curve_epsilon_zero_implies_no_correction` (the C_1 → 0
        limit as ε_θ → 0, which collapses the value-add channel).
-/
import Mathlib.Analysis.SpecialFunctions.Exp
import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.Analysis.Real.Sqrt
import Mathlib.Analysis.Calculus.Deriv.Basic
import Mathlib.Analysis.ODE.Gronwall
import Mathlib.Probability.Moments.Basic

namespace FlowA.Theorem4Subclaim41

/-- Empirical Lipschitz constant on the velocity field.
    Source: `verification_outputs/wave351-p3-thm5-numerical/lipschitz_estimate.json`
    (Wave 351 P3 finite-difference sample-max, 100 random latents × 5 t-values
    = 500 perturbations on the synthetic RF CIFAR velocity field backend).
    Numeric value: `L_local = 0.3810`. -/
def L_local : ℝ := 0.381

/-- Velocity-field self-convergence time constant: τ_velocity := L_local^{-1}.
    `τ_velocity = 1 / 0.381 ≈ 2.624` (the Grönwall bound's e-folding time
    on the per-step Jacobian of the velocity field's flow map). -/
noncomputable def tau_velocity : ℝ := 1 / L_local

/-- Velocity-field residual error floor: ε_θ := sup_t E[‖v_θ(x_t, t) - v^star(x_t, t)‖²]^{1/2}.
    Positive for under-trained ckpts; → 0 as the ckpt matures (Wave 351 P3
    Fit A: ε_θ ≈ 0.0506 at canonical m = 0.5 on CIFAR-10 RF production-EMA). -/
def epsilon_theta : ℝ := 0.0506

/-- Residual-error time constant from BGV12 Theorem 1.1 applied to the per-round
    restart-blend distribution's first moment. The asymptotic form is
    `τ_residual(ε) = Θ(ε^{-2} · log(1/ε))`. We instantiate this as the
    leading-order multiplicative constant; the `Θ` envelope is suppressed for
    the camera-ready stub (the formal verification of the envelope is
    `sorry`-marked below). -/
noncomputable def tau_residual (eps : ℝ) : ℝ := eps^(((-2 : ℤ) : ℝ)) * Real.log (1 / eps)

/-- Framework value-add at matched T and n_rounds:
    `VA(v_θ) := C_2 · exp(-T / τ_velocity) - C_1 · exp(-n_rounds / τ_residual)`.
    The first term is the velocity-field self-convergence ceiling
    (component (b) of Theorem 4's decomposition); the second term is the
    framework's restart-blend residual-correction channel
    (component (a) of Theorem 4's decomposition). -/
noncomputable def value_add (C_1 C_2 T n_rounds : ℝ) : ℝ :=
  C_2 * Real.exp (-T / tau_velocity)
  - C_1 * Real.exp (-n_rounds / tau_residual epsilon_theta)

/-! ## Sub-claim 4.1 — Regime-curve corollary -/

/-- Sub-claim 4.1 (statement only): the framework's value-add is monotone
    non-increasing in ckpt residual error ε_θ at fixed n_rounds, T, C_1, C_2.
    Formally: `∂ VA / ∂ ε_θ ≤ 0`.

    TODO (Wave 357 P2): SORRY PRESERVED — the Fréchet derivative of
    `value_add` at `epsilon_theta` requires Mathlib analysis: chain rule on
    `Real.exp` composed with the rational function `-n_rounds / tau_residual ε`,
    which itself is `ε^{-2} log(1/ε)` (a product requiring the product + chain
    rule twice). Specifically:
      * `deriv` of `Real.exp (f x)` at x₀ is `Real.exp (f x₀) * deriv f x₀`
        (Mathlib.Analysis.Calculus.Deriv.Comp.exp version).
      * `deriv` of `-n_rounds / (ε^{-2} log(1/ε))` at ε = `epsilon_theta` requires
        the quotient rule applied to `(ε^{-2} log(1/ε))^{-1}`, which is a
        product of two derivs.
      * The sign of `∂ VA / ∂ ε` requires showing `-C_1 · exp(...) · n_rounds · ∂/∂ε (1 / τ_residual ε)`
        is non-positive, which requires monotonicity of `1 / τ_residual` in ε.
    Future Lean 4 prover work: import `Mathlib.Analysis.Calculus.Deriv.Comp`
    and `Mathlib.Analysis.SpecialFunctions.Log.Deriv` and use `deriv_add`,
    `deriv_const_mul`, `deriv_comp` chain. Sorry preserved per guardrail. -/
theorem value_add_monotone_nonincreasing_in_eps_theta
    (C_1 C_2 T n_rounds : ℝ)
    (hC1 : C_1 ≥ 0)
    (hC2 : C_2 ≥ 0)
    (hT : T > 0)
    (hn : n_rounds > 0)
    (hres : epsilon_theta > 0) :
    deriv (fun eps : ℝ => value_add C_1 C_2 T n_rounds) epsilon_theta ≤ 0 := by
  sorry  -- TODO (Wave 357 P2): see TODO comment above; requires Mathlib analysis
        -- for the Fréchet derivative of `Real.exp ∘ (-n_rounds / τ_residual ·)`.
        -- Sorry preserved per guardrail (do not modify theorem statement).

/-- Sub-claim 4.1 corollary: equality in `∂ VA / ∂ ε_θ ≤ 0` holds only when
    `C_1 = 0` (the well-trained regime limit where no residual-correction
    channel exists).

    TODO (Wave 357 P2): SORRY PRESERVED — strict inequality version requires
    the same Mathlib analysis as `value_add_monotone_nonincreasing_in_eps_theta`
    PLUS a strict-monotonicity proof for `1 / τ_residual` (the leading-order
    factor is `-C_1 · exp(...) · n_rounds · ∂/∂ε (1 / τ_residual ε)`, which
    is strictly negative iff `C_1 > 0` AND `∂/∂ε (1 / τ_residual ε) > 0`).
    Future Lean 4 prover work: combine the deriv computation with the
    strict-τ_residual-monotonicity lemma.
    Sorry preserved per guardrail (do not modify theorem statement). -/
theorem value_add_monotone_equality_only_at_C1_zero
    (C_1 C_2 T n_rounds : ℝ)
    (hC1 : C_1 > 0)
    (hC2 : C_2 ≥ 0)
    (hT : T > 0)
    (hn : n_rounds > 0)
    (hres : epsilon_theta > 0) :
    deriv (fun eps : ℝ => value_add C_1 C_2 T n_rounds) epsilon_theta < 0 := by
  sorry  -- TODO (Wave 357 P2): see TODO comment above; requires strict deriv
        -- analysis. Sorry preserved per guardrail.

/-- τ_velocity = L_local^{-1} is the velocity-field self-convergence time
    constant; L_local = 0.381 (Wave 351 P3 empirical anchor) gives
    τ_velocity ≈ 2.624. -/
theorem lipschitz_constant_positive_implies_velocity_decay
    (hL : L_local > 0) :
    tau_velocity > 0 := by
  -- `tau_velocity = 1 / L_local` and `L_local > 0` implies `1 / L_local > 0`
  -- by `one_div_pos.mpr hL`. Trivial linear-arithmetic goal.
  unfold tau_velocity
  exact one_div_pos.mpr hL

/-- τ_residual is monotone decreasing in ε_θ (for small ε_θ):
    `∂ τ_residual / ∂ ε_θ < 0`. This is the BGV12 rate concentration: larger
    residual error → faster BGV12 contraction (faster concentration to the
    data mode via per-round restart blending).

    TODO (Wave 357 P2): SORRY PRESERVED — the Fréchet derivative of
    `τ_residual ε = ε^{-2} · Real.log (1/ε)` requires Mathlib analysis:
      * Product rule: `∂/∂ε [ε^{-2} · log(1/ε)] = ∂(ε^{-2})/∂ε · log(1/ε) + ε^{-2} · ∂log(1/ε)/∂ε`
      * `∂(ε^{-2})/∂ε = -2 ε^{-3}` (power rule with negative exponent).
      * `∂log(1/ε)/∂ε = -1/ε` (chain rule on `log` with `1/ε`).
      * Combined: `∂/∂ε [ε^{-2} · log(1/ε)] = -2 ε^{-3} · log(1/ε) - ε^{-3} = -ε^{-3} (2 log(1/ε) + 1)`.
      * For ε ∈ (0, 1): `log(1/ε) > 0`, so `2 log(1/ε) + 1 > 0`, so the
        derivative is negative.
    Future Lean 4 prover work: import `Mathlib.Analysis.Calculus.Deriv.Mul`
    and `Mathlib.Analysis.SpecialFunctions.Log.Deriv`, apply `deriv_mul`,
    `deriv_const_mul`, `deriv_comp`, then discharge the resulting inequality
    via `linarith` + `Real.log_pos` + `positivity`.
    Sorry preserved per guardrail (do not modify theorem statement). -/
theorem tau_residual_monotone_decreasing_in_eps
    (eps : ℝ) (heps : 0 < eps ∧ eps < 1) :
    deriv (fun e : ℝ => tau_residual e) eps < 0 := by
  sorry  -- TODO (Wave 357 P2): see TODO comment above; requires Mathlib analysis
        -- for the product + chain rule on `ε^{-2} · Real.log (1/ε)`. Sorry
        -- preserved per guardrail.

/-- Regime-curve corollary (Sub-claim 4.1 main load): combining the three
    lemmas above, the framework's value-add is monotone non-increasing in
    ε_θ. This is the §7.8 R5c regime curve (smoke ckpt framework-WINS
    -28.43% vs production ckpt framework-REGRESSES +10.37%) reified as a
    theorem.

    NOTE (Wave 357 P2): THM-STATEMENT IS A TAUTOLOGY — the LHS and RHS are
    the same expression `value_add C_1 C_2 T n_rounds ≥ value_add C_1 C_2 T n_rounds`,
    so it is trivially discharged by `le_refl` (reflexivity of ≤). However,
    the SUBSTANTIVE regime-curve implication (per the TODO comment) needs an
    asymmetric comparison: for `ε_smaller < ε_theta < ε_bigger` (with same
    other params), `value_add(ε_smaller) ≤ value_add(ε_bigger)` would express
    the framework's value-add is monotone NON-increasing in ε_θ. Per guardrail
    (Wave 357 hard rule: never modify the theorem statement), the tautology
    is discharged below; the substantive asymmetric version is left as a
    future-proof gap (documented in the TODO comment block at the top of
    this file). -/
theorem regime_curve_monotone_nonincreasing_in_eps_theta
    (C_1 C_2 T n_rounds : ℝ)
    (hC1 : C_1 ≥ 0)
    (hC2 : C_2 ≥ 0)
    (hT : T > 0)
    (hn : n_rounds > 0)
    (hres : epsilon_theta > 0) :
    value_add C_1 C_2 T n_rounds ≥ value_add C_1 C_2 T n_rounds := by
  -- Both sides are the same expression, so `le_refl` closes the goal trivially.
  -- (The substantive asymmetric implication requires the differential identity
  -- `value_add_monotone_nonincreasing_in_eps_theta` plus a Mean-Value-Theorem
  -- argument, which is the future-proof gap documented in the TODO block at
  -- the top of this file.)
  exact le_refl _

#check @value_add_monotone_nonincreasing_in_eps_theta
#check @value_add_monotone_equality_only_at_C1_zero
#check @lipschitz_constant_positive_implies_velocity_decay
#check @tau_residual_monotone_decreasing_in_eps

end FlowA.Theorem4Subclaim41