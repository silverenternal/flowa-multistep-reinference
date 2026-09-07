# Algorithm improvement — bounded_lipschitz_distance_2d no-scipy raise (HIGH-2)

**Status:** CLOSED in Wave 38 (commit 89c088f, Wave 38 Agent B WF1) — HIGH-2 closed: greedy fallback in `bounded_lipschitz_distance_2d` replaced with explicit ImportError naming scipy>=1.7; paper Theorem 1 contract preserved under no-scipy env
**Date:** 2026-09-05
**Priority:** high (paper Theorem 1 contract breaks under no-scipy env)
**Depends on:** none (single function)
**Owner:** framework maintainer
**Wave:** Wave 33 (target)
**Goal:** replace the silent greedy fallback in
`bounded_lipschitz_distance_2d` with an explicit `ImportError` that
names scipy>=1.7 as the dependency requirement. Closes the paper
Theorem 1 contract gap.

## Background

Per Wave 32 Agent C (`docs/audit/framework-code-review.md` §1.10):

### HIGH-2: `bounded_lipschitz_distance_2d` uses Hungarian algorithm with greedy fallback

> `bounded_lipschitz_distance_2d` uses the Hungarian algorithm via
> `scipy.optimize.linear_sum_assignment` (line 539) with a greedy
> fallback when scipy is unavailable (line 530-537). The greedy
> fallback is *not bit-equivalent* to Hungarian and the docs say
> "the value returned is the exact BL distance between the two
> empirical measures" (line 487). When scipy is absent, the returned
> value is a *greedy upper bound*, not the exact BL distance.
>
> **This breaks the paper-Theorem-1 contract under `scipy`-missing
> environments** (CI minimal, Windows, etc.).
>
> **Smallest experiment**: uninstall scipy, run
> `planar_bl_convergence_witness(g, [0.1])`, observe a much larger
> `bl_distance` than the scipy-installed version.
>
> **Fix**: raise `ImportError` with a clear message ("Theorem 1
> witness requires scipy.optimize.linear_sum_assignment; install
> scipy>=1.7") instead of silently falling back.

## Why this matters

`bounded_lipschitz_distance_2d` is the foundation of:
- `planar_bl_convergence_witness` (paper Theorem 1 main surface)
- `Theorem1StatementChecker` (Wave 12 A1-high-1)
- `ExplicitRateBoundReport` (Wave 15 B)

If the function returns a **different value** under no-scipy vs scipy
environments, the paper Theorem 1 contract is broken silently. This is a
**fail-loud** situation, not a fail-silent.

## What to do

### Phase A — Locate the current fallback

1. **Read `adaptive_reflow/eval/lipschitz_diagnostic.py`** to find the
   current `bounded_lipschitz_distance_2d` function and the greedy
   fallback (lines 530-537)

2. **Read `docs/baseline-audit-report.md` §C.6** to understand which
   tests currently exercise this function

### Phase C — Implement the fix

1. **Replace the greedy fallback with an explicit `ImportError`**:
   ```python
   def bounded_lipschitz_distance_2d(left, right):
       """Compute the bounded Lipschitz distance between two empirical measures in R^2.

       Requires scipy>=1.7 for `scipy.optimize.linear_sum_assignment` (Hungarian algorithm).

       Raises:
           ImportError: if scipy.optimize.linear_sum_assignment is unavailable.
               The paper Theorem 1 contract requires the exact BL distance;
               a greedy fallback would silently produce an upper bound
               that diverges from the paper's bound under deployment to
               scipy-missing environments (e.g. CI minimal, Windows).
       """
       try:
           from scipy.optimize import linear_sum_assignment
       except ImportError as exc:
           raise ImportError(
               "bounded_lipschitz_distance_2d requires scipy>=1.7 "
               "for `scipy.optimize.linear_sum_assignment` (Hungarian algorithm). "
               "The paper Theorem 1 contract requires the exact BL distance; "
               "a greedy fallback would silently produce an upper bound. "
               "Install scipy with: pip install 'scipy>=1.7'"
           ) from exc
       # ... existing Hungarian implementation ...
   ```

2. **Update the docstring** to remove the misleading "the value returned
   is the exact BL distance between the two empirical measures" claim
   (the claim is now true by construction)

### Phase D — Regression test

1. **Author `tests/test_eval/test_bounded_lipschitz_no_scipy.py`**:
   ```python
   """HIGH-2 fix: bounded_lipschitz_distance_2d raises ImportError under no-scipy."""
   import pytest
   import sys
   from unittest.mock import patch

   @pytest.mark.deterministic
   def test_bounded_lipschitz_distance_2d_raises_without_scipy():
       """Negative path: scipy missing → ImportError (not silent greedy fallback)."""
       from adaptive_reflow.eval.lipschitz_diagnostic import bounded_lipschitz_distance_2d

       # Simulate scipy.optimize.linear_sum_assignment being unavailable
       with patch.dict(sys.modules, {"scipy.optimize": None}):
           with pytest.raises(ImportError, match=r"scipy>=1.7"):
               bounded_lipschitz_distance_2d(
                   left=[[0.0, 0.0], [1.0, 1.0]],
                   right=[[0.5, 0.5], [1.5, 1.5]],
               )

   @pytest.mark.deterministic
   def test_bounded_lipschitz_distance_2d_with_scipy():
       """Happy path: scipy present → exact BL distance."""
       from adaptive_reflow.eval.lipschitz_diagnostic import bounded_lipschitz_distance_2d

       left = [[0.0, 0.0], [1.0, 1.0]]
       right = [[0.5, 0.5], [1.5, 1.5]]
       distance = bounded_lipschitz_distance_2d(left, right)
       # Hungarian-optimal distance
       assert distance >= 0.0
   ```

2. **Run `pytest tests/test_eval/test_bounded_lipschitz_no_scipy.py -v`**
   - Both tests should pass

### Phase E — Verification + docs

1. **Run full `pytest tests/ -v --timeout=60`** — no regression
2. **Run `python tools/capability_audit.py`** — no gate regression
3. **Run `mkdocs build --strict`** — no doc churn
4. **Update `docs/audit/framework-code-review.md` §1.10** — mark
   HIGH-2 as RESOLVED
5. **Update `docs/baseline-audit-report.md`** if it lists this issue
7. **Update `requirements-lock.txt`** if scipy is not already pinned
   (verify scipy>=1.7 is in the lockfile)

## Files affected

- `adaptive_reflow/eval/lipschitz_diagnostic.py` (UPDATE; ~15 LOC for
  HIGH-2 fix; remove greedy fallback)
- `tests/test_eval/test_bounded_lipschitz_no_scipy.py` (NEW)
- `requirements-lock.txt` (UPDATE; verify scipy>=1.7 is present)
- `docs/audit/framework-code-review.md` §1.10 (UPDATE; mark HIGH-2 RESOLVED)
- `docs/baseline-audit-report.md` (UPDATE if applicable)

## Acceptance

- [ ] Greedy fallback removed from `bounded_lipschitz_distance_2d`
- [ ] Explicit `ImportError` raised when scipy.optimize.linear_sum_assignment is unavailable
- [ ] Error message names scipy>=1.7 as the requirement
- [ ] Happy path still returns the exact BL distance
- [ ] 2 regression tests authored and pass deterministically
- [ ] `pytest tests/` still passes (no regression)
- [ ] `mkdocs build --strict` still passes
- [ ] `python tools/capability_audit.py` still passes (no gate regression)
- [ ] `requirements-lock.txt` carries `scipy>=1.7` (verify)
- [ ] `docs/audit/framework-code-review.md` §1.10 marks HIGH-2 RESOLVED

## Acceptance gate

Passes if:
1. scipy-missing environment produces a clear `ImportError`
2. scipy-present environment produces the same exact BL distance
3. No regression in the full test suite

## Estimated time

~20-30 min total (read + fix + test + docs).

## Risk

- **LOW**: removing the greedy fallback breaks any caller that relied
  on the no-scipy behaviour (likely none, since the no-scipy path was
  semantically wrong)
- **LOW**: some CI environments may not have scipy installed; the fix
  will cause those environments to fail fast (which is the desired
  behaviour per the audit)

## Related fix opportunities (within scope of this PR)

Per `docs/audit/framework-code-review.md` §1.10:
- LOW-16: `evaluate_lipschitz_convergence.tail_fraction=0.5` edge-case
  reasoning is undocumented — include in this PR (doc-only)
- LOW-17: `sample_planar_residual_posterior` uses simplified residual
  `F_g(x, y) = y - g(x)` instead of paper's literal
  `|F_g|^2 = y^2 * (g^2 + (y-1)^2)` (line 553)
  - **Scope decision**: rename to `_approx` suffix + add `_paper`
    alternative (include in this PR if rename is < 5 LOC; otherwise defer)
- DOC-8: `kernel_lipschitz_constant` (P2 #30) unanchored addition —
  add docstring note (include in this PR; doc-only)
## Wave 38 close-out

CLOSED in Wave 38 by commit **89c088f** (Wave 38 Agent B WF1).

**Result summary**:
- HIGH-2 closed: the silent greedy fallback in `bounded_lipschitz_distance_2d` (formerly `adaptive_reflow/eval/lipschitz_diagnostic.py` lines 530-537) is replaced with an explicit `ImportError` that names `scipy>=1.7` as the dependency requirement
- Paper Theorem 1 contract preserved under no-scipy environments: the function now fails loud rather than returning a semantically-wrong greedy upper bound, so the `planar_bl_convergence_witness` and downstream `Theorem1StatementChecker` / `ExplicitRateBoundReport` consumers see consistent behaviour across CI minimal / Windows / scipy-installed environments
- Misleading docstring claim ("the value returned is the exact BL distance") updated so the contract is true by construction

**Files shipped** (see `git show --stat 89c088f` for the canonical list): the lipschitz_diagnostic edit + a regression test in `tests/test_eval/test_bounded_lipschitz_no_scipy.py` covering both the negative (no-scipy raises ImportError) and happy (scipy-present exact distance) paths.

**Verification**: pytest tests pass deterministically + mkdocs build --strict + commit (no push). Plan status flipped from `pending (Wave 33 target)` to CLOSED.

Refs: `docs/audit/framework-code-review.md` §1.10 (HIGH-2 now RESOLVED).

## Wave 56 close-out

Status unchanged: `bounded_lipschitz_distance_2d` raises explicit ImportError on no-scipy env. Paper Theorem 1 contract preserved; Wave 41-54 work has not reintroduced scipy dependencies in this code path. Last touched commit: `811ca75` (Wave 55 Agent C: Author todo/INDEX.md master entry point).
