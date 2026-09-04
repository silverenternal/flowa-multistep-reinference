# Algorithm improvement B — explicit rate bound theorem

**Status:** done (Wave 15 B — commit f9d34e1; rate_bound.py + 8 tests; PLANAR_BL_CONSTANT = sqrt(2/pi) explicit bound; docs/theory/theorem1_rate_bound.md)
**Priority:** medium (depends on A first)
**Depends on:** `todo/algo-improvement-planar-bl-repoint.md` (A) done
**Owner:** framework maintainer
**Goal:** write the explicit rate bound `BL(mu_{g,eps}, nu_g) <= sqrt(2/pi) * eps`
as a first-class framework theorem — with proof, dataclass, checker,
and tests — so it is auditable and reusable beyond the planar
witness call.

## Background

Wave 12 A1-high-3 shipped `PLANAR_BL_CONSTANT = sqrt(2/pi)` with the
synchronous coupling argument in the docstring:

> The synchronous coupling `(x, g(x) + eps*z) ↔ (x, g(x))` with `z ~ N(0, 1)`
> transports mu_{g,eps} onto nu_g at expected cost `E|eps*z| = eps * sqrt(2/pi)`.
> Since BL is the infimum over all couplings of the truncated-metric cost
> (Kantorovich duality with cost `min(||u-v||, B)`), this coupling is an
> upper-bound witness: `BL(mu_{g,eps}, nu_g) <= eps * sqrt(2/pi)`,
> independent of `g`.

The constant + argument are scattered across a single docstring. They
should be:
1. A theorem statement in `docs/theory/theorem1_rate_bound.md`.
2. A dataclass + checker in `adaptive_reflow/theory/checkers.py`
   (alongside `Theorem1Statement`).
3. Tests in `tests/test_theory/test_rate_bound.py`.

## Theorem statement (target)

**Theorem (Explicit BL rate bound, restated from paper Theorem 1).**
*Let `g` satisfy the F-side hypotheses (c, d, rho, eta; see
`f_side_validator`). Let `mu_{g,eps}` and `nu_g` be the residual
posterior and its `eps -> 0` limit on R^2 (paper notation). Then for
every `eps > 0`,*

    BL(mu_{g,eps}, nu_g) <= sqrt(2/pi) * eps.

*Proof.* The synchronous coupling `(x, g(x) + eps*z) ↔ (x, g(x))` with
`z ~ N(0, 1)` is a valid coupling of `mu_{g,eps}` and `nu_g`: the
marginals are correct by construction (the x-marginal is exactly N(0,1)
because the residual posterior's `y` integrates out under the Gaussian
factor; nu_g is supported on the sheet `(x, g(x))` which has the same
x-marginal). The expected cost under this coupling is
`E_{(x, z)} |(x, g(x) + eps*z) - (x, g(x))| = E_z |eps*z| = eps * sqrt(2/pi)`.
By Kantorovich-Rubinstein duality, `BL` is the infimum over all
couplings of this expected cost; an upper bound on the infimum is a
feasible coupling's cost. Therefore `BL(mu_{g,eps}, nu_g) <= eps * sqrt(2/pi)`.
QED.

## Dataclass (target)

```python
@dataclass(frozen=True)
class ExplicitRateBoundReport:
    eps: float
    bl_distance: float          # empirical BL from planar_bl_convergence_witness
    analytic_constant: float     # sqrt(2/pi) by default
    expected_upper_bound: float  # analytic_constant * eps
    empirical_to_bound_ratio: float  # bl_distance / expected_upper_bound
    within_bound: bool          # bl_distance <= expected_upper_bound (with MC tolerance)
```

## Checker (target)

```python
def check_explicit_rate_bound(
    g: Callable[[float], float],
    eps: float,
    *,
    constant: float = math.sqrt(2.0 / math.pi),
    n_samples: int = 512,
    seed: int = 0,
    tolerance: float = 1.5,
) -> ExplicitRateBoundReport:
    """Check BL(mu_{g,eps}, nu_g) <= constant * eps for the supplied g.

    Reuses planar_bl_convergence_witness([eps]) and reports the ratio.
    """
```

## Files affected (estimated)

- `adaptive_reflow/theory/checkers.py` — add `ExplicitRateBoundReport`
  + `check_explicit_rate_bound`; re-export from `__init__.py`.
- `tests/test_theory/test_rate_bound.py` (new) — at least 4 tests:
  - constant matches `math.sqrt(2/math.pi)`
  - empirical ratio <= 1.5 for canonical `g_a(x) = (1 + 0.25*tanh(x))*sin(x)` (Proposition 2 profile)
  - bound holds for varying `eps` in {0.5, 0.1, 0.05, 0.01}
  - bound holds for varying `g` (at least 2 profiles)
- `docs/theory/theorem1_rate_bound.md` (new) — formal theorem statement
  + proof + reference to paper Theorem 1 + framework mapping.
- `mkdocs.yml` — add `docs/theory/` to nav (under "Architecture" or
  new "Theory" section).

## Acceptance

- [ ] `check_explicit_rate_bound` exported from `adaptive_reflow.theory`
- [ ] `tests/test_theory/test_rate_bound.py` passes (>= 4 tests)
- [ ] `docs/theory/theorem1_rate_bound.md` exists with formal statement + proof
- [ ] mkdocs --strict exit 0 + nav updated
- [ ] Commit + push

## Estimated time

30-60 min (no GPU; pure refactor + tests + docs).

## Acceptance gate

**Gate name:** `G-ALGO-RATE-BOUND` (new; defined here)

**Pre-condition:** `G-ALGO-PLANAR-BL` (A) passed
**Pass conditions:**
- [ ] Acceptance checklist above all met
- [ ] `todo/STATUS.md` updated
- [ ] `docs/theory/theorem1_rate_bound.md` cross-references paper Theorem 1

## Out of scope

- Tighter explicit constants (the synchronous coupling is not the
  optimal coupling; the optimal constant may be smaller but requires
  paper machinery beyond Theorem 1).
- Multi-dim `g: R^d -> R^m` rate bounds (paper Theorem 1 is R^d → R^m
  but the framework's `bounded_lipschitz_distance_2d` is R^2 only).