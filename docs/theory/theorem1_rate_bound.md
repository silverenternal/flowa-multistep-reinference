# Theorem 1 — Explicit rate bound

**Paper reference:** Theorem 1 (line 87-92).
**Framework module:** `adaptive_reflow.theory.rate_bound`.
**Framework checker:** `adaptive_reflow.theory.rate_bound.check_explicit_rate_bound`.
**Framework dataclass:** `adaptive_reflow.theory.rate_bound.ExplicitRateBoundReport`.
**Planar witness:** `adaptive_reflow.eval.lipschitz_diagnostic.planar_bl_convergence_witness`.
**Analytic constant:** `adaptive_reflow.eval.lipschitz_diagnostic.PLANAR_BL_CONSTANT` (re-exported as
`adaptive_reflow.theory.rate_bound.DEFAULT_ANALYTIC_CONSTANT`).

## Theorem statement

**Theorem (Explicit BL rate bound, restated from paper Theorem 1).**

Let `g : R → R` satisfy the F-side hypotheses (line 22-26: c, d, ρ, η;
see `adaptive_reflow.theory.validation.validate_g_admissible`). Let
`μ_{g,ε}` denote the residual posterior on `R²` and let `ν_g` denote
its `ε → 0` limit (paper notation). Then for every `ε > 0`,

```
BL(μ_{g,ε}, ν_g)  ≤  √(2/π) · ε .
```

The constant `√(2/π)` is g-independent: it depends only on the noise
marginal, not on the profile `g`.

## Proof

**Step 1 — Construct a coupling.** The synchronous coupling
`(x, g(x) + ε·z) ↔ (x, g(x))` with `z ~ N(0, 1)` is a valid coupling of
`μ_{g,ε}` and `ν_g`:

* The first marginal `(x, g(x) + ε·z)` has `x ~ N(0, 1)` and, conditional on `x`,
  `y = g(x) + ε·z` is a draw from the Gaussian centred at `g(x)` with
  scale `ε` — exactly the marginal of `μ_{g,ε}` (paper line 77-79).
* The second marginal `(x, g(x))` lies on the sheet `{F_g = 0}`, which is
  exactly the support of `ν_g`.

**Step 2 — Compute the expected cost.** The Euclidean distance between
the two coupled points is

```
|(x, g(x) + ε·z) − (x, g(x))|  =  |ε·z| .
```

Taking expectations and using `E|z| = √(2/π)` for `z ~ N(0, 1)`,

```
E_{(x, z)} |(x, g(x) + ε·z) − (x, g(x))|  =  ε · √(2/π) .
```

**Step 3 — Kantorovich-Rubinstein duality.** `BL(μ, ν)` is the infimum
over all couplings of the truncated-metric cost

```
BL(μ, ν)  =  inf_{couplings γ of (μ, ν)}  E_{(u, v) ~ γ} min(‖u − v‖, B) ,
```

with `B > 0` (Kantorovich duality, paper line 91-92). A feasible
coupling's cost upper-bounds the infimum. The synchronous coupling is
feasible (Step 1) with expected cost `ε · √(2/π)` (Step 2). Therefore

```
BL(μ_{g,ε}, ν_g)  ≤  ε · √(2/π) .   QED.
```

### Notes

* The constant `√(2/π)` is **not optimal** — the synchronous coupling is
  just one feasible coupling, and the optimal coupling (which would
  minimise the expected cost) may give a smaller constant. The bound
  is an upper bound, so a smaller true constant would only strengthen
  the result; we use `√(2/π)` because it is the simplest to derive
  and is g-independent.
* The bound is g-independent but the **measured** BL distance may be
  much smaller for specific `g` (e.g. periodic `g(x) = sin(x)` gives
  ratio ≈ 0.05 at ε = 0.1). The framework's empirical-to-bound ratio
  therefore carries signal as a quantitative tightness diagnostic.

## Framework surface

| Framework symbol | Maps to |
|---|---|
| `adaptive_reflow.eval.lipschitz_diagnostic.PLANAR_BL_CONSTANT` | The constant `√(2/π)` (Wave 12 A1-high-3). |
| `adaptive_reflow.eval.lipschitz_diagnostic.planar_bl_convergence_witness` | Finite-eps BL witness on `R²` (Hungarian assignment on the empirical measures). |
| `adaptive_reflow.theory.rate_bound.DEFAULT_ANALYTIC_CONSTANT` | Re-export of `PLANAR_BL_CONSTANT` (Wave 15 B). |
| `adaptive_reflow.theory.rate_bound.ExplicitRateBoundReport` | Immutable dataclass carrying the bound state (eps, bl_distance, analytic_constant, expected_upper_bound, empirical_to_bound_ratio, within_bound, n_samples). |
| `adaptive_reflow.theory.rate_bound.check_explicit_rate_bound` | The checker: fail-closed F-side pre-check (via `validate_g_admissible`) + planar witness + ratio computation. |

## Acceptance gate

**Gate name:** `G-ALGO-RATE-BOUND`.

**Pre-condition:** `G-ALGO-PLANAR-BL` (Wave 12 high-3) passed.

**Pass conditions:**
- `adaptive_reflow.theory.rate_bound.check_explicit_rate_bound` exported
  from `adaptive_reflow.theory`.
- `tests/test_theory/test_rate_bound.py` passes (≥ 4 tests including
  MUST-FAIL fixtures for F-side-violating `g`).
- This doc exists with formal statement + proof + paper-equation
  citation (A.4 contribution).
- `mkdocs --strict` exits 0 with `docs/theory/` in the nav.
- Commit + (no push per task scope).

## Fail-closed audit policy

Per `docs/adr/0005-fail-closed-audit-code-policy.md`, the checker
raises `NotInFsideClassError` for F-side-violating `g` (Prop 6
sharpness examples; empty `Z_g`; uniform-simplicity violations). The
rate bound itself is g-independent and holds for any measurable `g`,
but the theorem is conditional on F-side hypotheses so an F-side-
violating `g` is out of the theorem's scope and the checker surfaces
this as a raise rather than silently reporting a (potentially
misleading) `within_bound = True`. The flag `enforce_f_side = False`
disables the F-side pre-check for audit-only callers.

## Out of scope (per `todo/algo-improvement-rate-bound.md`)

* Tighter explicit constants (the synchronous coupling is not the
  optimal coupling; the optimal constant may be smaller but requires
  paper machinery beyond Theorem 1).
* Multi-dim `g : R^d → R^m` rate bounds (paper Theorem 1 is `R^d → R^m`
  but the framework's `bounded_lipschitz_distance_2d` is `R²` only).

## Cross-references

* Paper Theorem 1 (line 87-92) — the `μ_{g,ε} --BL--> ν_g` statement.
* Paper Remark 1 (line 54-56) — Theorem 1 is periodicity-free; the
  framework's checker applies to any F-side-admissible `g`,
  including the non-periodic family `g_a(x) = a(x)·sin(x)` from
  Proposition 2.
* Paper Proposition 2 (line 62-64) — `g_a(x) = (1 + 0.25·tanh(x))·sin(x)`
  is the canonical positive fixture in the test suite.
* Paper Proposition 6 (line 294-300) — `H(x) = e^{-x²/2}·sin(π·x)` is
  the canonical sharpness (must-fail) fixture in the test suite.
* Paper Lemma 5 (line 132, 135-138) — disjoint-cell constraint `ρ < d/4`
  enforced by `validate_f_side`.
* `adaptive_reflow.eval.lipschitz_diagnostic.PLANAR_BL_CONSTANT` —
  the canonical constant source (Wave 12 A1-high-3).
* `adaptive_reflow.theory.validation.validate_g_admissible` — the
  F-side pre-check integrated into the checker.
* `adaptive_reflow.theory.checkers.theorem1_bl_convergence_witness` —
  the Wave 14 A repointed BL-convergence witness that the rate-bound
  checker reuses.
* `docs/adr/0005-fail-closed-audit-code-policy.md` — fail-closed
  semantics for the F-side pre-check.
* `docs/baseline-audit-report.md` A.0 — paper-statement inventory
  (this entry closes gap G4: "Theorem 1 explicit rate constant
  `BL = O(some explicit eps power)`").
* `todo/algo-improvement-rate-bound.md` — task spec.
* `todo/framework-internal-metrics.md` A.3 — "Explicit theorems
  exposed as framework surface (dataclass + checker + tests + must-fail
  fixture + equation citation)" = 2 by Wave 13 B (rate bound adds second).