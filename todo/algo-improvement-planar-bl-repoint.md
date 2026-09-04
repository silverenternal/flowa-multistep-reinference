# Algorithm improvement A — re-point Theorem 1 to true R^2 BL

**Status:** done (Wave 14 A — commit 6d12744; Theorem1StatementChecker consumes true R² BL throughout via planar_bl_convergence_witness)
**Priority:** high (Wave 12 high-3 agent's own follow-up)
**Depends on:** Wave 12 done (e0238ab); `planar_bl_convergence_witness()`
in `adaptive_reflow/eval/lipschitz_diagnostic.py` available
**Owner:** framework maintainer
**Goal:** the unified `Theorem1StatementChecker` consumes the true R^2
BL distance throughout (no 1-D y=0 projection; no rejection sampler).
Side effect: paper Theorem 1 is now realised on the correct metric space.

## Background

Wave 12 A1-high-3 added `bounded_lipschitz_distance_2d()`,
`sample_planar_residual_posterior()`, `sample_planar_limit()`, and
`planar_bl_convergence_witness()` in
`adaptive_reflow/eval/lipschitz_diagnostic.py`. These compute the
**paper's metric** (BL on R^2) directly.

The agent deliberately did NOT re-point
`adaptive_reflow/theory/checkers.py::theorem1_bl_convergence_witness`
because A1-high-1 was editing `theory/` in parallel. That follow-up is
now unblocked.

## Current state

```
adaptive_reflow/theory/checkers.py::theorem1_bl_convergence_witness
  uses 1-D y=0 projection with a rejection sampler.

adaptive_reflow/theory/checkers.py::Theorem1StatementChecker.check
  consumes theorem1_bl_convergence_witness for its bl_distance field.

adaptive_reflow/eval/fid_theorem_aligned.py::assert_convergence_rate
  docstring already declares "regression gate rather than a proof of
  Theorem 1" — i.e. it knows it's the wrong metric.
```

## Target state

```
adaptive_reflow/theory/checkers.py::theorem1_bl_convergence_witness
  -> keep as a thin wrapper that calls planar_bl_convergence_witness()
     and forwards PlanarBLConvergenceReport (rename or deprecate?)

adaptive_reflow/theory/checkers.py::Theorem1StatementChecker.check
  -> calls planar_bl_convergence_witness() directly, takes
     bl_distances[0] (or min) as bl_distance field.

adaptive_reflow/eval/fid_theorem_aligned.py::assert_convergence_rate
  -> no change; remains the regression gate for the Gaussian-Frechet
     proxy.
```

## Files affected (estimated)

- `adaptive_reflow/theory/checkers.py` — refactor `theorem1_bl_convergence_witness` to wrap `planar_bl_convergence_witness`; update `Theorem1StatementChecker.check` to call the planar witness.
- `adaptive_reflow/theory/__init__.py` — possibly re-export `PlanarBLConvergenceReport`.
- `tests/test_theory/test_theorem1_unified.py` — update 1-2 tests to assert new shape.
- `adaptive_reflow/eval/lipschitz_diagnostic.py` — read-only (already shipped).

## Acceptance

- [ ] `Theorem1StatementChecker.check` returns a `Theorem1Statement` whose `bl_distance` is the value reported by `planar_bl_convergence_witness` (not the 1-D projection).
- [ ] `tests/test_theory/test_theorem1_unified.py` updates verify the new shape (e.g. assert `bl_distance` is `min(eps_schedule)`-driven).
- [ ] pytest passes: `tests/test_theory` (247) + `tests/test_contracts` (27) + `tests/test_eval/test_lipschitz_diagnostic.py` (32).
- [ ] mkdocs --strict still exit 0.
- [ ] No changes to `fid_theorem_aligned.py` numerical behavior.
- [ ] Commit + push (one PR).

## Estimated time

30-60 min (no GPU; pure refactor + tests).

## Acceptance gate

**Gate name:** `G-ALGO-PLANAR-BL` (new; defined here)

**Pre-condition:** Wave 12 done + `planar_bl_convergence_witness` shipped
**Pass conditions:**
- [ ] Acceptance checklist above all met
- [ ] `todo/STATUS.md` updated
- [ ] `todo/PHASE-1-framework-and-theory.md` §1.1 cross-references this file

## Out of scope

- Removing `fid_theorem_aligned.py` (it remains as a Gaussian-Frechet
  proxy for downstream evaluation; the paper's BL is now the audit
  metric, not the evaluation metric).
- Re-running any SOTA model comparison (this is framework-internal).