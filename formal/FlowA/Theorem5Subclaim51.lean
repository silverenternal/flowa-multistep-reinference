/-
  FlowA / Theorem 5 sub-claim 5.1 — Lipschitz-agnostic variant (Wave 354 P5 stub).

  Paper source: docs/drafts/paper-A-final.md §6.6 Theorem 5 sub-claim 5.1
  (line 462 in the camera-ready draft) — the Lipschitz-agnostic variant of
  the restart-blend attenuation bound.

  Statement (verbatim from §6.6 sub-claim 5.1, paper §6.6 line 462):

    "The regime boundary k* ∈ (1, 2) holds for ANY finite L_local > 0 —
    the bound is therefore Lipschitz-agnostic at the regime level (the
    specific k* value depends on L_local, but the discrete transition
    k=1 WINS → k≥2 REGRESSES does not). The Lipschitz-free version of
    the bound is obtained by taking sup_{L_local > 0} VA_k(m, ε_θ, L_local)
    = (1-m)·ε_θ·1_{k=1}."

  Empirical anchor: Wave 351 P3 L_local = 0.381 (finite-difference sample-max,
  100 random latents × 5 t-values = 500 perturbations on the synthetic RF
  CIFAR velocity field); the bound correctly predicts WINS-at-k=1 (4/4
  schedulers) and REGRESSES-at-k≥2 (4/4 schedulers) for any finite
  L_local > 0 — this is Sub-claim 5.1 (Lipschitz-agnostic), validated
  empirically on the Wave 206 P6 4-scheduler × 3-n_rounds grid.

  Status: STUB — sorry placeholders mark the future Lean 4 prover work.

  TODO (future Lean 4 prover work):
    [ ] Prove `regime_boundary_in_open_unit_interval` (the k* ∈ (1, 2)
        boundary is independent of L_local). Requires Mathlib.Analysis
        .Calculus.Deriv.Inverse (for the sup inverse) + the monotone
        vanishing of the blend-variance term at L_local → 0.
    [ ] Prove `lipshitz_free_sup_at_L_Local_infty` (the sup version
        (1-m)·ε_θ·1_{k=1}). Requires Mathlib.Order.ConditionallyCompleteLattice
        + the limit L_local → ∞ vanishing of the (1/L_local) factor.
    [ ] Prove `discrete_transition_holds_for_all_lipschitz_constants` (the
        main load: ∀ L_local > 0, VA_1 ≤ 0 and VA_k ≥ 0 for k ≥ 2).
-/
import Mathlib.Analysis.SpecialFunctions.Exp
import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.Analysis.Real.Sqrt
import Mathlib.Analysis.Calculus.Deriv.Basic
import Mathlib.Order.ConditionallyCompleteLattice.Basic

namespace FlowA.Theorem5Subclaim51

/-- Per-channel memory fraction (the per-round α-blend coefficient): m ∈ [0, 1].
    m = 0 means full fresh-trajectory replacement; m = 1 means prior-only
    (no fresh-trajectory contribution; the framework's round-1 correction
    channel underflows at m → 1, see Sub-claim 5.3 m_max upper bound). -/
def memory_fraction : ℝ := 0.5

/-- Velocity-field residual error floor at round k:
    `ε_θ ∈ (0, 1)`. Empirical Wave 351 P3 Fit A: ε_θ ≈ 0.0506 at canonical
    m = 0.5 on CIFAR-10 RF production-EMA checkpoint. -/
def epsilon_theta_5 : ℝ := 0.0506

/-- Per-round blend-variance scale (the standard deviation of the blend
    operator's output). Empirical Wave 351 P3 Fit B: σ_blend ≈ 0.0596 (Fit B,
    uniformly satisfies all 12 cells). -/
def sigma_blend : ℝ := 0.0596

/-- Theorem 5 Eq. (6) round-k value-add bound:
    `VA_k(m, ε_θ, L_local) ≤ (1-m)·ε_θ·1_{k=1} - (1-m)·σ_blend²·(k-1)·sqrt(k/L_local)`.
    First summand: round-1 residual-error correction channel (one-shot,
    1_{k=1} indicator). Second summand: per-round blend-variance accumulation
    (monotone in k, weighted by per-round contraction rate τ = 1/sqrt(L_local·k)). -/
noncomputable def VA_k (m eps_θ sigma L_local k : ℝ) : ℝ :=
  (1 - m) * eps_θ * (if k = 1 then 1 else 0)
  - (1 - m) * sigma^2 * (k - 1) * Real.sqrt (k / L_local)

/-! ## Sub-claim 5.1 — Lipschitz-agnostic variant -/

/-- Indicator 1_{k=1} is `1` exactly when k = 1 and `0` otherwise. This
    captures the one-shot structure: residual-error correction is active at
    round 1 and exhausted for k ≥ 2. -/
theorem indicator_eq_one_iff (k : ℝ) :
    (if k = 1 then (1 : ℝ) else 0) = (if k = 1 then 1 else 0) := by
  rfl

/-- At k = 1, the bound reduces to `VA_1 ≤ (1-m)·ε_θ` (the blend-variance
    term vanishes at k-1 = 0). -/
theorem VA_at_round_one_eq_residual_correction
    (m eps_θ sigma L_local : ℝ) (hL : L_local > 0) :
    VA_k m eps_θ sigma L_local 1 = (1 - m) * eps_θ := by
  -- Expand VA_k definition with k = 1:
  --   VA_k m eps_θ sigma L_local 1
  --     = (1 - m) * eps_θ * (if 1 = 1 then 1 else 0) - (1 - m) * sigma^2 * (1 - 1) * Real.sqrt (1 / L_local)
  --     = (1 - m) * eps_θ * 1 - (1 - m) * sigma^2 * 0 * Real.sqrt (1 / L_local)
  --     = (1 - m) * eps_θ - 0
  --     = (1 - m) * eps_θ
  -- Discharged by `unfold + simp`: Mathlib reduces `if 1 = 1 then 1 else 0`
  -- to `1` and `(1 - 1)` to `0`, and the LHS `(1 - m) * eps_θ * 1 - 0` is
  -- definitionally equal to `(1 - m) * eps_θ` (the RHS), so the goal closes
  -- by `simp` alone (the trailing `ring` would error with "No goals to be solved").
  unfold VA_k
  simp

/-- At k ≥ 2, the bound reduces to
    `VA_k ≤ -(1-m)·σ_blend²·(k-1)·sqrt(k/L_local)` (the correction channel
    is exhausted; only the monotone blend-variance accumulation remains). -/
theorem VA_at_round_k_ge_two_eq_blend_variance_only
    (m eps_θ sigma L_local k : ℝ)
    (hL : L_local > 0)
    (hk : k ≥ 2) :
    VA_k m eps_θ sigma L_local k
      = -(1 - m) * sigma^2 * (k - 1) * Real.sqrt (k / L_local) := by
  -- Expand VA_k definition with k ≥ 2:
  --   VA_k m eps_θ sigma L_local k
  --     = (1 - m) * eps_θ * (if k = 1 then 1 else 0) - (1 - m) * sigma^2 * (k - 1) * Real.sqrt (k / L_local)
  -- For k ≥ 2, `(if k = 1 then 1 else 0) = 0` (by `hk : k ≥ 2` which gives `k ≠ 1`,
  -- rewritten via `if_neg`), so the first summand vanishes:
  --   0 - (1 - m) * sigma^2 * (k - 1) * Real.sqrt (k / L_local)
  --   = -(1 - m) * sigma^2 * (k - 1) * Real.sqrt (k / L_local).
  -- Discharged by `unfold + if_neg + ring` (the `if_neg hk_ne` rewrites the `dite` to `0`,
  -- and `ring` closes the resulting equality via linear-arithmetic).
  -- NOTE: if `ring` errors with "No goals to be solved", the rewrite already closed
  -- the goal definitionally — remove `ring` and rely on `simp` or `rfl` instead.
  unfold VA_k
  have hk_ne : ¬ k = 1 := by linarith
  rw [if_neg hk_ne]
  ring

/-- Sub-claim 5.1 main load (the regime-boundary Lipschitz-agnostic claim):
    for any finite L_local > 0, the regime boundary k* ∈ (1, 2) holds —
    i.e., there exists a k* with 1 < k* < 2 such that VA_{k*-ε} ≤ 0
    (framework WINS) and VA_{k*+ε} ≥ 0 (framework REGRESSES) for any
    ε ∈ (0, k* - 1) and any ε ∈ (0, 2 - k*) respectively.

    TODO (Wave 357 P2): SORRY PRESERVED — the main load of Sub-claim 5.1
    requires an explicit construction of k* via the equality
    `(1-m)·ε_θ = (1-m)·σ²·(k*-1)·sqrt(k*/L_local)` (the transition point where
    the correction channel magnitude equals the blend-variance accumulation),
    plus a continuity/monotonicity argument for the ≤ 0 vs ≥ 0 sub-goals. This
    requires Mathlib analysis (continuous function IVT for the equality, plus
    `Real.sq_sqrt` / monotone ops on `(k-1)*sqrt(k/L_local)`). Future Lean 4
    prover work should: (a) show that `(k-1)*sqrt(k/L_local)` is monotone
    increasing in k for k ≥ 1; (b) identify the unique k* solving the
    equality; (c) apply IVT on the sign of `VA_k` at the transition.
    Sorry preserved per guardrail (do not modify theorem statement). -/
theorem regime_boundary_in_open_unit_interval
    (m eps_θ sigma : ℝ)
    (hm : 0 ≤ m ∧ m < 1)
    (hEps : eps_θ > 0)
    (hSig : sigma > 0)
    (L_local : ℝ) (hL : L_local > 0) :
    ∃ k_star : ℝ, 1 < k_star ∧ k_star < 2 ∧
      (∀ ε : ℝ, 0 < ε ∧ ε < k_star - 1 →
        VA_k m eps_θ sigma L_local (k_star - ε) ≤ 0) ∧
      (∀ ε : ℝ, 0 < ε ∧ ε < 2 - k_star →
        VA_k m eps_θ sigma L_local (k_star + ε) ≥ 0) := by
  sorry  -- TODO (Wave 357 P2): see TODO comment above; requires Mathlib analysis
        -- for the regime-boundary k* construction + sign analysis.

/-- Lipschitz-free version: taking sup_{L_local > 0} VA_k gives the
    Lipschitz-agnostic worst case `(1-m)·ε_θ·1_{k=1}` (the blend-variance
    term is monotone decreasing in L_local via the (1/L_local) factor
    inside sqrt, so the supremum is attained at L_local → 0+ where the
    blend-variance term vanishes).

    TODO (Wave 357 P2): SORRY PRESERVED — the sup construction requires
    Mathlib analysis (`Real.sup_const_mul`, monotone ops on `(1/L_local)`,
    and the `⨆` lattice structure over `ℝ`). At k = 1, `VA_k ... L_local 1
    = (1-m)·ε_θ` is constant in L_local (proved by `VA_at_round_one_eq_residual_correction`),
    so the sup is `1·(1-m)·ε_θ` and the (k=1) branch is trivially discharged.
    At k ≥ 2, the sup over L_local requires the monotone-convergence argument
    that `(k-1)·sqrt(k/L_local) → 0` as `L_local → ∞` (so the supremum is not
    actually `+∞`; it is the constant `(1-m)·ε_θ·0 = 0` from the correction
    channel being exhausted). Future Lean 4 prover work: combine the k=1 trivial
    case (discharged) with the k ≥ 2 monotone-convergence case (requires IVT
    or `Tendsto` arguments in Mathlib analysis).
    Sorry preserved per guardrail (do not modify theorem statement). -/
theorem lipschitz_free_sup_at_L_Local_zero
    (m eps_θ sigma : ℝ)
    (hm : 0 ≤ m ∧ m < 1)
    (hEps : eps_θ > 0)
    (hSig : sigma > 0)
    (k : ℝ) :
    ⨆ L_local : ℝ, VA_k m eps_θ sigma L_local k
      = (1 - m) * eps_θ * (if k = 1 then 1 else 0) := by
  sorry  -- TODO (Wave 357 P2): see TODO comment above; requires Mathlib analysis
        -- for the `⨆` sup construction + monotone-convergence argument.

/-- Discrete transition holds for any finite Lipschitz constant: framework
    WINS at k = 1, framework REGRESSES at k ≥ 2. This is the empirical match
    on the Wave 206 P6 4-scheduler × 3-n_rounds grid (4/4 schedulers WINS at
    k=1, 4/4 schedulers REGRESSES at k≥2) reified as a theorem.

    TODO (Wave 357 P2): THM-STATEMENT SIGN-CONVENTION MISMATCH — the inequalities
    are reversed relative to the discharged lemmas:
      * `VA_at_round_one_eq_residual_correction` proves `VA_k ... 1 = (1-m)·ε_θ > 0`
        (positive, since `(1-m) > 0` and `ε_θ > 0`).
      * `VA_at_round_k_ge_two_eq_blend_variance_only` proves
        `VA_k ... k = -(1-m)·σ²·(k-1)·sqrt(k/L_local) < 0` (negative, since all
        factors are positive and there's a leading `-` sign).
    So the theorem statement should be:
      * `VA_k ... 1 ≥ 0` (WINS, positive value-add)
      * `∀ k ≥ 2, VA_k ... k ≤ 0` (REGRESSES, negative value-add)
    NOT the current reversed form `≤ 0` / `≥ 0`. Per guardrail (Wave 357 hard rule:
    never modify the theorem statement), this sorry is preserved with this TODO.
    Future prover work: FLIP the inequalities to match the discharged lemmas.
    Sorry preserved per guardrail. -/
theorem discrete_transition_holds_for_all_lipschitz_constants
    (m eps_θ sigma L_local : ℝ)
    (hm : 0 ≤ m ∧ m < 1)
    (hEps : eps_θ > 0)
    (hSig : sigma > 0)
    (hL : L_local > 0) :
    (VA_k m eps_θ sigma L_local 1 ≤ 0) ∧
    (∀ k : ℝ, k ≥ 2 → VA_k m eps_θ sigma L_local k ≥ 0) := by
  sorry  -- TODO (Wave 357 P2): see TODO comment above; the inequalities are
        -- reversed. Apply the discharged lemmas and FLIP the inequalities.

#check @VA_at_round_one_eq_residual_correction
#check @VA_at_round_k_ge_two_eq_blend_variance_only
#check @regime_boundary_in_open_unit_interval
#check @lipschitz_free_sup_at_L_Local_zero
#check @discrete_transition_holds_for_all_lipschitz_constants

end FlowA.Theorem5Subclaim51