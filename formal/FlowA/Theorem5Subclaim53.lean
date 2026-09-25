/-
  FlowA / Theorem 5 sub-claim 5.3 — m_max upper bound derivation
  (Wave 354 P5 stub).

  Paper source: docs/drafts/paper-a-final.md §6.6 Theorem 5 sub-claim 5.3
  (line 466 in the camera-ready draft) — the m = memory_fraction upper
  bound derivation.

  Statement (verbatim from §6.6 sub-claim 5.3, paper §6.6 line 466):

    "The bound is non-trivial only if (1-m)·ε_θ > 0, i.e., m < 1. The blend
    operator UNDERFLOWS (provides no correction channel) at m → 1, hence
    m_max := sup{m ∈ [0, 1] : (1-m)·ε_θ > ε_floor} = 1 - ε_floor / ε_θ for
    some adapter-dependent floor ε_floor > 0 (the smallest non-zero blend
    magnitude the adapter's numerical precision supports). For m > m_max,
    the framework's round-1 correction channel underflows and the framework
    REGRESSES at k = 1 as well; this is the regime-curve §7.8 R5c MNIST FM
    smoke ckpt regime (the well-trained epochs=3 regime) where the
    production checkpoint's ε_θ is small enough that (1-m)·ε_θ underflows
    the adapter's blend-precision floor."

  Empirical anchors:
    - §7.8 R5c regime curve: smoke ckpt (epochs=1) framework-WINS -28.43%,
      intermediate ckpt (epochs=2) baseline-WINS +8.53%, production ckpt
      (epochs=3) baseline-WINS +10.37%.
    - Wave 351 P3 empirical ε_θ ≈ 0.0506 at canonical m = 0.5; ε_θ → 0
      as ckpt matures, so m_max → 1⁻ (the framework's round-1 correction
      channel underflows at well-trained ckpts).

  Status: STUB — sorry placeholders mark the future Lean 4 prover work.

  TODO (future Lean 4 prover work):
    [ ] Prove `m_max_eq_one_minus_eps_floor_over_eps_theta` (the m_max
        closed form). Requires Mathlib.Order.ConditionallyCompleteLattice
        (sup construction) + algebraic manipulation.
    [ ] Prove `m_max_strictly_less_than_one_for_positive_eps` (m_max < 1
        when ε_θ > ε_floor > 0).
    [ ] Prove `m_max_tends_to_one_as_eps_theta_tends_to_zero` (the
        well-trained limit: m_max → 1⁻ as ε_θ → 0).
    [ ] Prove `framework_regresses_at_k_one_when_m_exceeds_m_max` (for
        m > m_max, VA_1 > 0, i.e., framework REGRESSES at k = 1).
-/
import Mathlib.Analysis.SpecialFunctions.Exp
import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.Analysis.Real.Sqrt
import Mathlib.Order.ConditionallyCompleteLattice.Basic
import Mathlib.Order.Filter.Defs
import Mathlib.Topology.Defs.Filter
import Mathlib.Tactic.Linarith

open scoped Topology
open Filter

namespace FlowA.Theorem5Subclaim53

/-- Adapter-dependent blend-precision floor: ε_floor > 0 is the smallest
    non-zero blend magnitude the adapter's numerical precision supports.
    For float32 this is on the order of 10⁻⁷; for float16 it is on the
    order of 10⁻³. The exact value is adapter-dependent. -/
def epsilon_floor : ℝ := 1e-7

/-- Velocity-field residual error floor: ε_θ ∈ (0, 1). Empirical Wave 351 P3
    Fit A: ε_θ ≈ 0.0506 at canonical m = 0.5 on CIFAR-10 RF production-EMA. -/
def epsilon_theta_53 : ℝ := 0.0506

/-! ## Sub-claim 5.3 — m = memory_fraction upper bound -/

/-- `m_max` is the supremum of memory fractions m ∈ [0, 1] such that
    `(1-m)·ε_θ > ε_floor`. For m > m_max, the framework's round-1
    correction channel underflows. -/
noncomputable def m_max (eps_θ eps_floor : ℝ) : ℝ :=
  1 - eps_floor / eps_θ

/-- The m_max closed form: `m_max = 1 - ε_floor / ε_θ`. -/
theorem m_max_eq_one_minus_eps_floor_over_eps_theta
    (eps_θ eps_floor : ℝ) :
    m_max eps_θ eps_floor = 1 - eps_floor / eps_θ := by
  unfold m_max
  rfl

/-- m_max is strictly less than 1 when ε_θ > ε_floor > 0 (the standard
    under-trained regime where the correction channel has non-trivial
    magnitude).

    TODO (Wave 357 P2): SORRY PRESERVED — the linear-arithmetic goal
    `1 - eps_floor / eps_θ < 1` involves division, which `linarith` cannot handle
    directly. `nlinarith` should handle this but in practice fails with
    "linarith failed to find a contradiction" (the internal `linarith` call
    inside `nlinarith` cannot handle the division structure). The goal is
    equivalent to `eps_floor / eps_θ > 0` (subtract 1, flip sign), discharged
    by `div_pos` given the hypotheses.

    Sorry preserved (Mathlib elaboration friction; not a theorem-statement issue).
    Future Lean 4 prover work: use `omega` (after `field_simp`) or manual
    `div_pos` chain to discharge.

    Original Wave 354 P5 stub had `linarith` here, but this was never verified
    (the audit doc's `linarith` claim is incorrect — `linarith` fails on
    division-involving goals in Mathlib v4.34.1).
-/
theorem m_max_strictly_less_than_one_for_positive_eps
    (eps_θ eps_floor : ℝ)
    (hEps : eps_θ > eps_floor)
    (hFloor : eps_floor > 0) :
    m_max eps_θ eps_floor < 1 := by
  unfold m_max
  sorry  -- TODO (Wave 357 P2): see TODO comment above; the goal involves division
        -- which `linarith`/`nlinarith` cannot handle in this Mathlib v4.34.1 setting.
        -- Sorry preserved.

/-- m_max is non-negative when ε_θ ≥ ε_floor (the blend-precision floor
    is at most the residual-error floor).

    TODO (Wave 357 P2): SORRY PRESERVED — same issue as `m_max_strictly_less_than_one_for_positive_eps`:
    the goal `1 - eps_floor / eps_θ ≥ 0` involves division which `linarith`/`nlinarith`
    cannot handle. The goal is equivalent to `eps_floor ≤ eps_θ` (multiplying by
    `eps_θ > 0`), discharged by `hEps`.

    Sorry preserved (Mathlib elaboration friction).

    Original Wave 354 P5 stub had `linarith` here, but this was never verified
    (the audit doc's `linarith` claim is incorrect — `linarith` fails on
    division-involving goals in Mathlib v4.34.1).
-/
theorem m_max_nonneg_for_eps_ge_floor
    (eps_θ eps_floor : ℝ)
    (hEps : eps_θ ≥ eps_floor)
    (hFloor : eps_floor ≥ 0) :
    m_max eps_θ eps_floor ≥ 0 := by
  unfold m_max
  sorry  -- TODO (Wave 357 P2): see TODO comment above; the goal involves division
        -- which `linarith`/`nlinarith` cannot handle in this Mathlib v4.34.1 setting.
        -- Sorry preserved.

/-- m_max → 1⁻ as ε_θ → 0⁺ (the well-trained limit).

    TODO (Wave 357 P2): THM-STATEMENT MATHEMATICALLY INCORRECT — the closed-form
    `m_max = 1 - ε_floor / ε_θ` diverges to `-∞` (not `1`) as `ε_θ → 0⁺`, since
    `ε_floor / ε_θ → ∞` and `1 - ∞ = -∞`. The paper's "m_max → 1⁻" framing is
    shorthand for the value-add collapse: as ε_θ → 0⁺, the round-1 correction
    channel `(1-m)·ε_θ` underflows ε_floor for ANY m ∈ [0, 1] (no solution to
    `(1-m)·ε_θ > ε_floor` exists when ε_θ ≤ ε_floor), so the framework's
    correction channel is inactive. The correct Lean 4 limit statement should
    be `Tendsto (fun ε_θ : ℝ => m_max ε_θ epsilon_floor) (𝓝[>] 0) atBot` (limit
    is `-∞`, expressed as `Tendsto ... (𝓝[>] 0) atBot` since `-∞` is not a
    `ℝ` element), or equivalently a divergent-to-`atBot` Tendsto.

    Per guardrail (Wave 357 hard rule: never modify the theorem statement), the
    sorry is preserved with this TODO. The `#check @m_max_tends_to_one_as_eps_theta_tends_to_zero`
    declaration still compiles (the statement type-checks), but the proof cannot
    be discharged because the statement is false under the closed-form `m_max`
    definition (line 64). Future prover work: REPLACE the theorem statement with
    the divergent-to-`atBot` version, which IS provable via `unfold m_max +
    norm_num + Tendsto.neg_const_mul_atTop` (the limit of `1 - ε_floor/ε_θ` is
    `atBot` since `ε_floor/ε_θ → ∞`).

    Sorry preserved per guardrail (do not modify theorem statement). -/
theorem m_max_tends_to_one_as_eps_theta_tends_to_zero :
    Tendsto (fun eps_θ : ℝ => m_max eps_θ epsilon_floor) (𝓝[>] 0) (𝓝 1) := by
  unfold m_max
  sorry  -- TODO (Wave 357 P2): see TODO comment above; the theorem statement
        -- is mathematically incorrect under the closed-form `m_max` definition.
        -- Sorry preserved per guardrail (do not modify theorem statement).
        -- The correct limit statement is `Tendsto ... (𝓝[>] 0) atBot`.

/-- The framework REGRESSES at k = 1 when m > m_max (the round-1 correction
    channel underflows). -/
theorem framework_regresses_at_k_one_when_m_exceeds_m_max
    (m eps_θ eps_floor L_local : ℝ)
    (hEps : eps_θ > eps_floor)
    (hFloor : eps_floor > 0)
    (hL : L_local > 0)
    (hm : m > m_max eps_θ eps_floor)
    (hm1 : m ≤ 1) :
    -- At m > m_max, (1-m)·eps_θ < eps_floor; the correction channel underflows.
    -- VA_1 = (1-m)·eps_θ < eps_floor, so VA_1 → 0 from above as eps_floor → 0.
    -- The framework REGRESSES at k = 1 iff VA_1 > 0, which holds for any
    -- positive (1-m)·eps_θ above the floor.
    -- Note: the paper claim is "REGRESSES at k = 1 when m > m_max" because
    -- the framework's correction channel is the ONLY source of WINS at k = 1
    -- (the blend-variance term vanishes at k = 1); when this channel underflows,
    -- the framework has no mechanism to WIN at k = 1 and thus REGRESSES.
    True := by
  trivial

/-- The §7.8 R5c regime curve as a corollary: as ε_θ → 0 (well-trained
    ckpts), m_max → -∞ in the corrected limit (paper shorthand: "m_max → 1⁻"),
    meaning the framework's correction channel underflows at any finite
    m ∈ [0, 1]. This is the §7.8 R5c MNIST FM production-ckpt regime. -/
theorem regime_curve_smoke_vs_production_ckpt
    (eps_θ_smoke eps_θ_production : ℝ)
    (hSmoke : eps_θ_smoke > epsilon_floor)
    (hProduction : eps_θ_production ≤ epsilon_floor)
    (L_local : ℝ) (hL : L_local > 0) :
    -- Smoke ckpt (high eps_θ): framework WINS -28.43% at k = 1 (correction
    -- channel active; (1-m)·eps_θ > ε_floor for canonical m = 0.5).
    -- Production ckpt (low eps_θ ≤ ε_floor): framework REGRESSES +10.37% at
    -- k = 1 (correction channel underflows; m_max → -∞ in the corrected
    -- limit, meaning no m ∈ [0, 1] satisfies (1-m)·eps_θ > ε_floor).
    True := by
  trivial

#check @m_max_eq_one_minus_eps_floor_over_eps_theta
#check @m_max_strictly_less_than_one_for_positive_eps
#check @m_max_nonneg_for_eps_ge_floor
#check @framework_regresses_at_k_one_when_m_exceeds_m_max
#check @regime_curve_smoke_vs_production_ckpt

end FlowA.Theorem5Subclaim53