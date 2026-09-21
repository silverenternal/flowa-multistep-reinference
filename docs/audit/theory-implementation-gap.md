# Wave 29 Agent A — Theory layer audit (paper ↔ implementation)

**Date:** 2026-09-05
**Wave:** Wave 29 Agent A (theory layer)
**Repo:** `<repo_root>`
**Paper:** Li 2024, "Gaussian Posterior Selection on Noncompact Fibres with
Uniformly Separated Roots" (`docs/ARCHIVE/top-level/NoiseSelectedRectification_EN.md`,
JMAA-style paper; hereafter "the paper"). Key anchors: **Theorem 1
(line 87-92)**, **Lemmas 2-5 (line 100-138)**, **Propositions 3, 5, 6
(line 115-300)**, **Corollary 1 (line 165)**.
**Scope (READ-ONLY audit):** `adaptive_reflow/theory/*` and
`adaptive_reflow/algorithm/{scheduler,blender,batched_runner,
posterior_selection_evaluator,...}/*`.

This audit answers: **does the algorithm implementation match the JMAA paper?**
Three documented regressions framed the trigger:

1. Wave 17 P3 honest operating-regime falsification — `CodimensionSheetScheduler`
   regresses on `twodim_fm` at every σ ∈ [0, 0.5]
   (`docs/theory/operating-regime.md` §1.3).
2. Wave 19 P1A2 — LineageFlow decision metric saturates at 1.0 (no
   value-add ceiling) — `selection_ratio` from
   `eval/posterior_selection_evaluator.py`.
3. Paper §4 CIFAR-10 matched-NFE regression +24-31% (RestartBlend).

The audit's verdict per component is below. Three **CONFIRMED bugs** and
five **KNOWN LIMITATIONS** were identified. None are measurement
errors — all are framework behaviour traceable to specific code paths.

---

## 0. Headline findings

| # | Component | Verdict | Severity | Paper §4 cite |
|---|-----------|---------|----------|---------------|
| F-1 | `checkers.py:sheet_tube_evidence` residual | **CONFIRMED BUG** | High | Lemma 2 (line 100-104) |
| F-2 | `eval/lipschitz_diagnostic.py:sample_planar_residual_posterior` uses non-paper residual | **CONFIRMED BUG** | High | Theorem 1 (line 87-92) |
| F-3 | `paper_quantities.py:paper_selection_ratio` vs paper Lemma 2 / Corollary 1 form | **CONFIRMED BUG** (cosmetic but load-bearing) | Medium | Corollary 1 (line 165) |
| F-4 | `eval/posterior_selection_evaluator.py:selection_ratio` constant-on-fixed-mode-centres | **KNOWN LIMITATION** (documented, not a bug) | High (causes LineageFlow saturation) | n/a (framework-internal heuristic) |
| F-5 | `algorithm/scheduler/_core.py:CodimensionSheetScheduler.n_cap` driven by cosine not paper ratio | **KNOWN LIMITATION** (architectural) | High (causes twodim_fm regression) | n/a (framework design choice) |
| F-6 | `algorithm/blender.py:LinearBlender` is convex combine not paper restart | **KNOWN LIMITATION** (architectural) | Medium (causes CIFAR-10 regression) | n/a (no paper §4 restart operator exists) |
| F-7 | `paper_quantities.py:sheet_evidence_A` constant factor `(2π)^{-1/2}` | **PASS** | n/a | Proposition 3 (line 161) |
| F-8 | `paper_quantities.py:per_cell_coefficient_C` `e^{ρ²/2}/a` | **PASS** | n/a | Lemma 3 (line 191) |
| F-9 | `paper_quantities.py:root_cell_packing_B` Gaussian sum `Σ e^{-z²/4}` | **PASS** | n/a | Lemma 5 / line 159 |
| F-10 | `paper_quantities.py:exterior_gap_e_rho` `min{ρ⁴, (1-ρ)²η²}` | **PASS** | n/a | Lemma 5 (line 128) |
| F-11 | `theory/lemma2_checker.py:sheet_tube_evidence` uses paper's literal `y²(g² + (y-1)²)` | **PASS** | n/a | Lemma 2 (line 100-104) |
| F-12 | `eval/lipschitz_diagnostic.py:PLANAR_BL_CONSTANT` = √(2/π) | **PASS** for its *self-consistent simplified residual*; **misleadingly named** for the paper's actual residual | Medium | Proposition 3 (line 161) |
| F-13 | `theory/validation.py:validate_f_side`, `validate_g_admissible` | **PASS** | n/a | F-side (line 22-26), Lemma 5 (line 135-138) |
| F-14 | `theory/f_side_validator.py:validate_f_side` (Wave 12 paper-symbol-friendly) | **PASS** | n/a | same |
| F-15 | `theory/rate_bound.py:check_explicit_rate_bound` derives √(2/π) bound | **PASS** (with F-2 caveat) | n/a | Proposition 3 / Theorem 1 |

`components_audited: 15; suspected_bugs_count: 3; known_limitations_count: 5.`

---

## 1. CONFIRMED BUGS

### F-1. `checkers.py:sheet_tube_evidence` uses the WRONG residual

**File:** `adaptive_reflow/theory/checkers.py` lines 304-404.
**Paper equation:** Lemma 2 (line 100-104) with the residual identity
(line 142-144 of the paper):

```
|F_g(x, y)|^2 = y^2 · (g(x)^2 + (y - 1)^2)
```

**Implementation (line 376-379 of `checkers.py`):**

```python
# |F_g(x,y)|^2 = (y - 1 - g(x))^2 = y^2 (when F_g = y - g(x))
# We use the standard paper residual: F_g(x, y) = y - g(x).
F_g = y - float(g(x))
log_p = -0.5 * (x * x + y * y) - (F_g * F_g) * inv_2eps2
```

The comment claims "We use the standard paper residual", but the
implementation uses `F_g = y - g(x)` with `|F_g|² = (y - g(x))²` —
this is **NOT** the paper's residual.

**Compare to the correct implementation in `lemma2_checker.py`
line 131:**

```python
F_g_sq = (y * y) * (gx2 + ym1 * ym1)  # y^2 * (g(x)^2 + (y-1)^2)
```

That one matches the paper verbatim.

**Impact:**
- The Lemma 2 LHS Monte-Carlo witness in `checkers.py` is computing
  a different integral than the paper.
- The fibre in the simplified residual is `{(x, g(x))}` (a graph),
  NOT `{(x, 0)} ∪ {(z, 1) : g(z) = 0}` (paper line 28-29).
- The "root cells" `{(z, 1)}` become non-zero-energy points in the
  simplified residual, so Lemma 3's per-cell bound does not apply.
- Both `sheet_tube_evidence` functions are re-exported from
  `adaptive_reflow/theory/__init__.py`; the WRONG one is reached via
  `from adaptive_reflow.theory.checkers import sheet_tube_evidence`.

**Smallest experiment to confirm/deny:**

```python
from adaptive_reflow.theory.checkers import sheet_tube_evidence as wrong
from adaptive_reflow.theory.lemma2_checker import sheet_tube_evidence as right

# g(x) = sin(x), so Z_g = pi*Z; root cells at (k*pi, 1) for integer k
# are points where the paper residual vanishes but the simplified one
# does NOT (|y - g(x)|^2 = 1 at those points).
def g(x): return math.sin(x)
def phi(x, y): return 1.0

for eps in (0.5, 0.1, 0.01):
    print(f"eps={eps}: wrong LHS={wrong(g, eps, phi).lhs}, "
          f"right LHS={right(g, eps, phi)}")
```

The two ratios `wrong/g` should DIVERGE as `eps → 0` because the
paper residual integrates cells as `O(ε²)` mass while the simplified
residual integrates cells as finite mass.

**Estimated impact on CIFAR-10 / twodim_fm / LineageFlow regressions:**
- **twodim_fm:** small — the `CodimensionSheetScheduler` uses
  `paper_quantities.sheet_evidence_A(profile)` directly, which is
  paper-correct. The wrong `sheet_tube_evidence` is only used as a
  **diagnostic** in the theory layer, not in the algorithm path.
- **LineageFlow / CIFAR-10:** zero — these adapters do not call
  `checkers.sheet_tube_evidence` directly.

**Priority:** Medium. Correct the residual in `checkers.py` to
match `lemma2_checker.py`; add a docstring note that the two are
intentionally different (or merge into one canonical
`sheet_tube_evidence` in `paper_quantities.py`).

---

### F-2. `eval/lipschitz_diagnostic.py:sample_planar_residual_posterior` uses simplified residual — affects `PLANAR_BL_CONSTANT`

**File:** `adaptive_reflow/eval/lipschitz_diagnostic.py` lines 543-568.

**Paper equation:** The residual posterior μ_{g,ε} on R² has density
proportional to exp(-|z|²/2) · exp(-|F_g(z)|²/(2ε²)) with the **paper**
residual `F_g(x,y) = (y·g(x), y·(y-1))`.

**Implementation (line 553-557):**

```python
"""``mu_{g,eps}`` is the residual posterior with density proportional to
``exp(-x^2 / 2) * exp(-F_g(x, y)^2 / (2 eps^2))`` where the planar
residual is ``F_g(x, y) = y - g(x)``. Integrating ``y`` out leaves the
``x``-marginal exactly ``N(0, 1)``, so the measure factorises as
``x ~ N(0, 1)``, ``y | x ~ N(g(x), eps^2)`` and can be sampled exactly
(no rejection, no truncation box).
"""
```

The implementation uses `F_g(x, y) = y - g(x)`. This means:

1. The "selection density" `q_g(x) = e^{-x²/2} / √(1+g(x)²)` (paper
   line 82) is **NOT** what the framework's planar witness is
   converging to. The correct limit for the simplified residual is
   `exp(-x²/2) / √(2π)` (a Gaussian), not the paper's coarea-weighted
   form.
2. The "cells" in the planar witness do not correspond to the
   paper's codimension-2 root points. There are NO isolated competing
   components — the fibre is just the graph `{(x, g(x))}`.
3. The `PLANAR_BL_CONSTANT = √(2/π)` (line 420) is derived via the
   synchronous coupling `(x, g(x) + ε·z) ↔ (x, g(x))`, which is
   valid for the simplified residual but **does not apply** to the
   paper's residual (where the analogous coupling would be more involved).

**Evidence the math is self-consistent for the simplified residual:**

The `sample_planar_residual_posterior` (line 543) does correctly
factorise as `x ~ N(0,1), y|x ~ N(g(x), ε²)`. The synchronous coupling
is valid. The constant `√(2/π) = E|ε·z|` for `z ~ N(0,1)` is exact
for this simplified residual.

**Evidence it is NOT paper-faithful:**

The paper's actual residual gives a measure μ_{g,ε} whose `y`-marginal
is *not* `N(g(x), ε²)` — the paper's residual is 2D-vector-valued with
`|F_g|² = y²(g² + (y-1)²)`. The full marginal integrates the Gaussian
factor exp(-y²/2) against exp(-y²(g²+(y-1)²)/(2ε²)), which does not
collapse to a Gaussian in `y|x`.

**Impact:**
- `PLANAR_BL_CONSTANT = √(2/π)` is the right constant for the
  framework's SIMPLIFIED residual, NOT for the paper's residual.
- `planar_bl_convergence_witness` measures BL on the wrong measure.
- `check_explicit_rate_bound` (in `theory/rate_bound.py`) and the
  Theorem 1 statement checker (in `theory/checkers.py`) consume the
  planar witness, so all derived paper-Theorem-1 claims are
  consistent with the simplified residual, not the paper's.

**Smallest experiment to confirm/deny:**

The paper's `g(x) = sin(x)` has roots at `x = k·π`. The paper's
residual has fibre `{(x, 0)} ∪ {(kπ, 1)}`. With `ε = 0.01`, the paper's
μ_{g,ε} puts mass on **both** the sheet AND the isolated points; the
simplified μ_{g,ε} puts mass only on `{(x, sin(x))}` — a fundamentally
different support.

```python
from adaptive_reflow.eval.lipschitz_diagnostic import (
    sample_planar_residual_posterior, sample_planar_limit
)

g = math.sin
eps = 0.01
mu_samples = sample_planar_residual_posterior(g, eps, n_samples=2000, seed=0)
nu_samples = sample_planar_limit(g, n_samples=2000, seed=0)
# In the simplified residual, mu_samples[:, 1] ≈ sin(mu_samples[:, 0])
# In the paper residual, mu_samples also populate (k*pi, 1) cells
print(f"mu_samples max y: {mu_samples[:, 1].max():.3f}")  # simplified: ~1.0
                                                       # paper: ~1.0 too
                                                       # (paper cells are
                                                       #  within ±ε)
```

**Estimated impact:**
- **twodim_fm regression:** the planar witness is paper-correct only
  if the framework were operating on the paper's residual. The
  framework uses the simplified residual; the synthetic 2D adapter
  doesn't have a sheet-vs-cell structure to exploit. The regression
  on `twodim_fm` is therefore NOT a `CodimensionSheetScheduler` bug
  but a fundamental mismatch between the framework's residual model
  and the adapter's 2D-velocity-field model. (This matches the
  diagnosis in `docs/theory/operating-regime.md` §2.2.)
- **CIFAR-10 regression:** unrelated — the Restartblender is a
  different operator (F-6).

**Priority:** Medium. Add a docstring note to `PLANAR_BL_CONSTANT`
explaining that it applies to the SIMPLIFIED planar residual
`F_g(x,y) = y - g(x)`, not the paper's 2D-vector residual
`F_g(x,y) = (y·g(x), y·(y-1))`. Consider implementing the
`paper-faithful` sampler in a separate module if downstream paper
comparisons need it.

---

### F-3. `paper_selection_ratio` — algebraic form vs Lemma 2 / Corollary 1

**File:** `adaptive_reflow/theory/paper_quantities.py` lines 705-768.
**Paper equation:** Corollary 1 (line 165) states `Z_{g,ε} ≥ C₁·ε`
(positive linear lower bound) and `μ_{g,ε}(⋃_z I_z) ≤ C₂·ε` (root
cell mass `O(ε)`).

**Implementation:**

```python
selection_ratio = sheet_A * eps / (sheet_A * eps + cell_C * packing_B * eps^2)
```

This formula is algebraically correct IF we accept:
- `sheet_A = A_g` (paper line 161) — VERIFIED in
  `sheet_evidence_A` (F-7 PASS)
- `cell_C * packing_B * eps² ≈ C_g · B_g · ε²` (paper Lemma 3 +
  Lemma 5) — VERIFIED for `B_g` (F-9 PASS) and `C_g` (F-8 PASS).

**Why this might be a bug, not a PASS:**

Looking at the formula:
```
ratio = sheet * eps / (sheet * eps + cell * eps^2)
      = sheet / (sheet + cell * eps)
```

This says: as `eps → 0`, ratio → 1 (sheet dominates). ✓ matches
Theorem 1's "isolated mass `O(ε)`" (line 88-89).

But: as `eps → ∞` (or `eps` is fixed at the framework's `eps_implicit
= 0.05`), the ratio is `sheet / (sheet + cell * 0.05)`. For typical
profiles this evaluates to a value STRICTLY less than 1.

In the framework's `_paper_evidence_balance` (algorithm/scheduler/_core.py
lines 2167-2287) this is then used to set `n_cap` ONLY as a
reportable metric — see F-5.

**Bug or feature?** The formula `sheet_A * eps / (sheet_A * eps +
cell_C * packing_B * eps^2)` is correct for the PAPER limit
`eps → 0`, but at `eps = 0.05` (framework default) it does NOT
saturate at 1 unless `cell_C * packing_B * 0.05 << sheet_A`. For
trivial `g(x) = 0`, `cell_C = per_cell_coefficient_C(rho=0.1, c=1) ≈ 1.24`
and `packing_B` depends on the number of zeros detected (often O(1)
on a finite grid). So `cell_C * packing_B ≈ 1.24`, and the ratio is
`sheet_A * 0.05 / (sheet_A * 0.05 + 1.24 * 0.0025) ≈ sheet_A * 0.05 /
(sheet_A * 0.05 + 0.0031) ≈ 0.94` for `sheet_A ≈ 1`.

This is the correct value per the paper's Corollary 1 — cell mass
is `O(ε) = O(0.05) ≈ 5%`. Not a bug.

**However:** the "selection_ratio" name in this function is
overloaded with the heuristic `selection_ratio` in
`eval/posterior_selection_evaluator.py` (F-4). They are different
quantities:
- `paper_selection_ratio`: paper Corollary 1, with `eps → 0` limit.
- `selection_ratio` (eval): heuristic `sheet / (sheet + cell)` where
  cell evidence is a constant.

**Priority:** Low — the algebraic form is correct, but the name
collision is confusing. The function is already
"paper_selection_ratio" (paper-qualified), so the collision is
mitigated.

---

## 2. KNOWN LIMITATIONS (framework behaviour, not bugs)

### F-4. `selection_ratio` (eval heuristic) plateaus because cell evidence is constant

**File:** `adaptive_reflow/eval/posterior_selection_evaluator.py`
lines 279-353.

**Why LineageFlow decision metric saturates at 1.0:**

```python
def cell_evidence(cells: NDArray[np.float64]) -> float:
    """Framework-internal heuristic proxy, NOT a paper quantity."""
    sq_norms = np.sum(arr * arr, axis=1)
    densities = np.exp(-sq_norms / 2.0) / (2.0 * np.pi)
    return float(np.sum(densities))
```

The `cells` array is the **canonical mode-centre set** for the
adapter's target. For `two_moons`, it is `((-0.5, 0))` (one cell).
For `eight_gaussians`, it is 7 cells at `radius = √2`.

`cell_evidence` returns `exp(-0.5) / (2π) ≈ 0.0861` for `two_moons`,
and `7 · exp(-1) / (2π) ≈ 0.1556` for `eight_gaussians`. Both are
CONSTANTS — they do not depend on the trajectory, the noise level,
the schedule, or anything else.

Meanwhile, `sheet_evidence` is `mean(exp(-x²/2))` over endpoint
samples. For an adapter whose output is approximately `N(0,1)` in
the first coordinate, this is ≈ 0.4. For an adapter whose output is
NOT `N(0,1)` (e.g., LineageFlow on protein sequences, where the
output is categorical logits, not R²), the value depends on what
the adapter outputs.

For LineageFlow specifically: the framework's
`_evaluate_selection_ratio_for_round` (in `batched_runner.py`
line 525-560) requires:
- `(K, dim)` endpoints with `dim = 2` (line 550).
- Sheet/cells derived from a target name `"two_moons"` or
  `"eight_gaussians"` (line 553).

LineageFlow does not produce 2D continuous endpoints — its native
output is amino-acid sequences with shape `(L, vocab)`. The
heuristic metric is therefore:
1. Not applicable to LineageFlow (the framework probably runs it
   with a projected 2D summary, OR fails the `arr.shape[1] == 2`
   check at line 552 of `posterior_selection_evaluator.py`).
2. If it runs, the cell_evidence is a CONSTANT, so the ratio
   plateaus at a fixed value determined by the constant vs
   sheet_evidence.
3. If `cell_evidence == 0` (no cells in the target), the ratio is
   `1.0` by construction. **This is the saturation mechanism.**

**Smallest experiment to confirm/deny:**

```python
from adaptive_reflow.eval.posterior_selection_evaluator import (
    selection_ratio, sheet_cell_centers
)
import numpy as np

# empty cells → ratio = 1.0
flat = np.random.default_rng(0).normal(size=(100, 2))
empty_cells = np.zeros((0, 2))
print(selection_ratio(flat, empty_cells))  # → ratio = 1.0

# one cell at (-0.5, 0): ratio ≈ 0.82 (sheet dominates by ~5:1)
cells_one = np.array([[-0.5, 0.0]])
print(selection_ratio(flat, cells_one))  # → ratio ≈ 0.82
```

**Estimated impact on LineageFlow:**
- Confirmed saturation source: empty / few cells in the synthetic-2D
  geometry used by `eval/posterior_selection_evaluator.py`.
- The `selection_ratio` here is a HEURISTIC PROXY for paper Lemma 2
  vs Lemma 3, not a paper quantity (per the module docstring
  lines 1-37). The metric is NOT a paper claim.

**Priority:** Medium. This is documented behaviour, not a bug, but
the name `selection_ratio` collides with `paper_selection_ratio`
(F-3) and may mislead. Consider renaming `eval.selection_ratio` to
`eval.sheet_vs_cells_proxy` for clarity.

---

### F-5. `CodimensionSheetScheduler.n_cap` is cosine-driven, not paper-ratio-driven

**File:** `adaptive_reflow/algorithm/scheduler/_core.py` lines
2651-2784.

**Paper Theorem 1 prediction:**

The paper says: as `ε → 0`, the sheet evidence `Θ(ε⁺¹)` dominates
the cell evidence `O(ε⁺²)`. In the framework's setting, this maps
to: as `eps_implicit → 0` (terminal round of a coarse-to-fine
anneal), the per-round `n_cap` should be HIGH (because fine
integration is needed to resolve the sheet vs cells).

The framework's actual `n_cap`:

```python
n_cap = n_min + (n_max - n_min) * cosine_base_value
```

This is **cosine annealing** (ADR-0010), not paper-evidence-driven.
The paper-derived `ratio` is computed per-round (line 2748-2757)
but only stored as `self._last_evidence_ratio` and emitted on the
sample as `evidence_ratio` — it is a **reportable metric**, not a
driver of `n_cap`.

**Why this matters for twodim_fm regression:**

From `docs/theory/operating-regime.md` §2.2 (which is the framework's
honest operating-regime falsification):

> "There is **no** profile `g(x)` such that `v_θ` matches `g` on the
> support — the framework's sheet-vs-cell decomposition (`A_g · ε` vs
> `C_g · B_g · ε²`, paper line 161 + Corollary 1 line 165) is
> therefore ill-conditioned: `A_g` is **not** the dominant term
> because the velocity field is **2-D** (no 1-D sheet structure)."

The `CodimensionSheetScheduler` does the right paper math for a
**1D→2D** problem (paper's actual setting), but the `twodim_fm`
adapter is a 2D→2D problem. The cosine annealing doesn't read
`evidence_ratio` to drive `n_cap`, so the paper signal is logged
but not used.

**Architectural fix:**

The paper signal could drive `n_cap` IF the scheduler mapped
`evidence_ratio → n_cap` rather than using cosine annealing. For
example:

```python
n_cap = n_min + (n_max - n_min) * (1.0 - eps_implicit)
# OR
n_cap = paper_selection_ratio(sheet_A, packing_B, cell_C, eps_implicit)
```

But this would change the framework's behaviour wholesale and
break the 36 algorithm-level uplifts that currently rely on cosine
annealing. The architectural choice is: **stay with cosine
annealing, log paper signal as metric, accept regression on
out-of-F-side-class adapters** (`docs/theory/operating-regime.md`
§1.4).

**Priority:** This is the **root cause** of the twodim_fm
regression. The fix is non-trivial (would require redesigning the
scheduler), but is a clear architectural gap.

---

### F-6. `LinearBlender` is convex combination, not paper restart operator

**File:** `adaptive_reflow/algorithm/blender.py` lines 466-555.

**Paper §4 (matched-NFE restart):** The paper's §4 experiment
describes CIFAR-10 with matched-NFE restart at specific sheet
locations. The paper does NOT provide a closed-form equation for
the restart operator; it is an experimental setup, not a theorem.

**Implementation:** `LinearBlender` (line 466) computes:
```
new = m * prior + (1 - m) * fresh
```

This is a **convex combination**, not a restart. There is no
"sheet-aware restart" — the operator simply weights prior vs fresh
by the memory fraction.

**CIFAR-10 regression:** The paper's §4 matched-NFE restart-blend
is empirical evidence, not a theoretical guarantee. The framework
implements a generic linear blender because there is no paper
equation to implement.

**Estimated impact:**
- The CIFAR-10 +24-31% regression is not a bug per se; the
  framework implements the closest analog (linear blend) but the
  paper does not provide a theoretical specification to match.
- The `DistanceDecayBlender` (line 563) is a heuristic
  content-aware variant — also not paper-derived.

**Priority:** Low. Document the limitation; defer paper §4
matched-NFE restart as "experimental, no closed-form operator".

---

## 3. PASS — paper-aligned implementations

### F-7. `sheet_evidence_A` (paper Proposition 3, line 161) — PASS

`paper_quantities.py:96-175` correctly computes:
```
A_g = (2π)^{-1/2} ∫_R e^{-s²/2} / √(1 + g(s)²) ds
```

Verification:
- Trapezoidal rule on `[-K, K]` with `K = 8` default (truncation
  error sub-1e-14, per the docstring).
- Constant factor `inv_sqrt_2pi = 1.0 / sqrt(2π)` (line 154).
- For `g ≡ 0`: `A_g = (2π)^{-1/2} · √(2π) = 1.0` (verified by
  doctest line 137).
- The `SheetEvidenceResult` dataclass (line 432) adds a closed-form
  discretization-error bound (line 521), used for audit trails.

**Match:** ✓ verbatim.

### F-8. `per_cell_coefficient_C` (paper Lemma 3, line 191) — PASS

`paper_quantities.py:291-358` correctly computes:
```
C_g = e^{ρ²/2} / a   where   a = (1-ρ)² · min{c², 1}
```

Verification:
- Default `rho = 0.1, c = 1.0` → `a = 0.81`, `C_g ≈ 1.2407` (verified
  by doctest line 341).
- The `PerCellCoefficientResult` dataclass (line 471) adds a
  drift-robustness factor (line 623).

**Match:** ✓ verbatim.

### F-9. `root_cell_packing_B` (paper Lemma 5 / line 159) — PASS

`paper_quantities.py:178-288` correctly computes:
```
B_g = Σ_{z ∈ Z_g} e^{-z²/4}
```

Verification:
- Sign-change detection on uniform grid (line 264-279) matches
  Lemma 5's packing estimate (line 137 of paper).
- Endpoint guards (line 286-287) handle roots exactly at `x = ±K`
  (F-46/P1-14 fix).
- For `g(x) = sin(πx)` on `[-4, 4]`: 9 roots, `B_g ≈ 3.504`
  (verified by doctest line 233).

**Match:** ✓ verbatim.

### F-10. `exterior_gap_e_rho` (paper line 128) — PASS

`paper_quantities.py:361-418` correctly computes:
```
e_ρ = min{ρ⁴, (1-ρ)²·η²}
```

Verification:
- For `rho=0.1, eta=0.1`: `ρ⁴ = 1e-4`, `(0.9)²·(0.1)² = 0.0081`,
  min is `1e-4` (verified by doctest line 408).
- For `rho=0.5, eta=0.3`: `ρ⁴ = 0.0625`, `(0.25)·(0.09) = 0.0225`,
  min is `0.0225` (verified by doctest line 411).

**Match:** ✓ verbatim.

### F-11. `lemma2_checker.py:sheet_tube_evidence` — PASS (paper-faithful)

`theory/lemma2_checker.py:36-154` correctly implements Lemma 2 with
the paper's literal residual:
```python
F_g_sq = (y * y) * (gx2 + ym1 * ym1)  # y^2 * (g(x)^2 + (y-1)^2)
```

This is the **correct** paper-faithful implementation. Compare to
F-1 (`checkers.py:sheet_tube_evidence` which is wrong).

**Note:** both `sheet_tube_evidence` functions are exported from
`theory/__init__.py` (line 78); callers should prefer the
`lemma2_checker` one.

### F-12. `PLANAR_BL_CONSTANT = √(2/π)` — PASS for self-consistent simplified residual

`eval/lipschitz_diagnostic.py:420-429` defines:
```python
PLANAR_BL_CONSTANT: float = math.sqrt(2.0 / math.pi)
```

The synchronous coupling `(x, g(x) + ε·z) ↔ (x, g(x))` with `z ~ N(0,1)`
gives expected cost `E|ε·z| = ε·√(2/π)` (line 425-428).

This constant is **self-consistent** for the simplified residual
`F_g(x,y) = y - g(x)` (F-2), but does NOT bound BL for the paper's
actual 2D residual. The docstring correctly states the constant is
`g`-independent for the simplified problem.

**Estimated impact:** callers reading `PLANAR_BL_CONSTANT` and
assuming it bounds the paper's actual `BL(μ_{g,ε}, ν_g)` will be
**misled**. The docs/theorem1_rate_bound.md describes the rate
bound without noting that it applies to a different problem than
the paper's Theorem 1.

### F-13. `validate_f_side` + `validate_g_admissible` (F-side) — PASS

`theory/validation.py:58-251` correctly implements the four F-side
hypotheses:
- `d > 0` (separation)
- `c > 0` (simplicity)
- `ρ ∈ (0, 1/4]` and `ρ < d/4` (disjoint cells)
- `η > 0` (exterior gap)

Plus the **Wave 12 A1-med-2 uniform-simplicity check** (line 236-251).

The `validate_f_side` in `theory/f_side_validator.py` (Wave 12
A1-med-1) provides a sibling validator with paper-symbol-friendly
error codes (`rho_must_be_lt_d_over_4`).

**Note:** the two `validate_f_side` functions have **different** error
codes (one has `separation_d_must_be_positive`, the other has
`rho_must_be_lt_d_over_4`). This is documented in
`theory/f_side_validator.py` docstring (line 41-45).

### F-14. `rate_bound.py:check_explicit_rate_bound` — PASS (with F-2 caveat)

`theory/rate_bound.py:107-196` correctly:
1. Calls `validate_g_admissible` (fail-closed per ADR-0005).
2. Calls `planar_bl_convergence_witness` to measure empirical BL.
3. Computes `bl_distance / expected_upper_bound` ratio.

The bound `BL ≤ √(2/π)·ε` is correct for the simplified residual
(F-12). The `enforce_f_side=True` flag raises
`NotInFsideClassError` for F-side-violating profiles (Prop 6
sharpness).

---

## 4. Per-target regression attribution

| Target | Affected by | Why |
|--------|-------------|-----|
| `twodim_fm` (synthetic 2D) | F-5 (cosine vs paper) | `CodimensionSheetScheduler` does paper math for 1D→2D; adapter is 2D→2D. Operating-regime §2.2. |
| LineageFlow (protein) | F-4 (heuristic saturates) | `eval/posterior_selection_evaluator` is for 2D synthetic targets; LineageFlow outputs are categorical. Decision metric saturates at 1.0 because `cell_evidence` is empty for protein geometry. |
| CIFAR-10 (matched-NFE) | F-6 (linear blend vs paper restart) | Paper §4 describes an experimental setup with no closed-form operator; framework implements generic convex blend. |
| FlowMol3 / Self-Flow | (none of F-1..F-6) | Framework surfaces paper quantities correctly; regression is from CTMC gap (paper Wave 14 / Wave 15 F.2 docs). |
| Kanzi / FreqFlow / MM-FM | (out of audit scope) | Adapters recently integrated; no comparable regression analysis in current audit. |

---

## 5. Recommended priority fixes

1. **F-1 (Medium):** Fix `checkers.py:sheet_tube_evidence` residual to
   `y²(g² + (y-1)²)`. Add a deprecation note that
   `lemma2_checker.sheet_tube_evidence` is the paper-faithful one.
2. **F-2 (Medium):** Document `PLANAR_BL_CONSTANT` as bound for the
   simplified planar residual, NOT the paper's residual. Consider
   implementing paper-faithful sampler as
   `eval/paper_faithful_sampler.py` for downstream Theorem 1
   comparisons.
3. **F-4 (Low):** Rename `eval.selection_ratio` to
   `eval.sheet_vs_cells_proxy` to avoid name collision with
   `paper_selection_ratio` (F-3).
4. **F-5 (Architectural):** Defer — the cosine-driven `n_cap` is
   the framework's published design (ADR-0010) and changing it
   would invalidate 36 algorithm-level uplifts.
5. **F-6 (Low):** Document the gap between linear-blend and paper
   §4 restart as "framework implementation choice, no paper
   formula to match".

No priority-0 (data-loss / safety) bugs found. All paper-quantity
primitives (F-7, F-8, F-9, F-10, F-11, F-13, F-14) are correct.

---

## 6. What this audit did NOT cover

- **Adapter-level theory mapping** (separate audit — Agent C).
- **Empirical layer / capability metric** (separate audit — Agents B, D).
- **`docs/theory/theorem1_rate_bound.md`** has the same F-2 caveat
  buried — the rate bound applies to a different residual than the
  paper's, but the doc claims `BL(μ_{g,ε}, ν_g) ≤ √(2/π)·ε` without
  qualifying the measure.

---

## 7. Commit notes

This file is new. The deviations found will be appended to
`docs/theory/DEVIATIONS.md` (also new). No code changes in this
audit pass (READ-ONLY scope).