# Algorithm improvement — property-based testing (B.7)

**Status:** done (Wave 17 P1 = B.7 — tests/test_property_based/ with 9+ property tests; hypothesis dev dep verified) (+ Wave 24 Agent C extended with test_theory_checkers_properties.py; Wave 38 hypothesis derandomize (CI profile); property tests pass deterministically in Wave 41-54)
**Date:** 2026-09-05
**Priority:** high (framework-internal-metrics rev 2 §1 B.7 = 0%; deep
verification gap; Wave 14 audit did not flag B.7 explicitly but it is a
critical missing piece for NeurIPS-tier algorithm depth)
**Depends on:** Wave 15 Agent T completing A.7 must-fail fixtures (to
avoid property tests duplicating must-fail tests)
**Owner:** framework maintainer
**Goal:** Add Hypothesis-style property tests to public deterministic
algorithm modules. Target ≥40% coverage by Wave 16.

## Background

Framework-internal-metrics rev 2 §1 B.7:
> Property-based test coverage: fraction of public deterministic
> algorithm modules with ≥ 1 Hypothesis-style @given test with
> explicit seed pin.
> Current: 0%; Target: ≥ 0.4 by Wave 16.

We have 36 hand-written isolation tests (Wave 14 W3 rescue) but ZERO
property-based tests. Property tests find edge cases hand-written tests
miss:

- Schedule monotonicity / periodicity invariants
- Policy driver idempotency
- Merge operator associativity / commutativity
- Blender convex combinations
- Sequential protocol composability
- Theory checker input symmetry

This is a critical verification-rigor gap. Without property tests, we
can't catch bugs that pass smoke tests but violate mathematical
invariants.

## Scope

### Public deterministic algorithm modules (target list)

| Module | Properties to test |
|---|---|
| `adaptive_reflow/algorithm/scheduler/_core.py` | Periodicity, monotonicity, config_hash distinctness |
| `adaptive_reflow/algorithm/policy_driver.py` | Idempotency on identical inputs |
| `adaptive_reflow/algorithm/merge_operator.py` | Associativity, commutativity (within tolerance) |
| `adaptive_reflow/algorithm/blender.py` | Convex combination invariants |
| `adaptive_reflow/algorithm/sequential.py` | Composability |
| `adaptive_reflow/algorithm/evidence_driver.py` | Decision boundary correctness |
| `adaptive_reflow/algorithm/batched_runner.py` | Batch consistency |
| `adaptive_reflow/theory/paper_quantities.py` | Symmetry (sheet = sheet), monotonicity |
| `adaptive_reflow/theory/checkers.py` | Monotonicity in eps; Theorem1Statement components well-ordered |
| `adaptive_reflow/theory/lemma2_checker.py` | Ratio ≤ 1.0 for all profiles (Lemma 2 limit) |
| `adaptive_reflow/theory/validation.py` | F-side hypothesis check completeness |
| `adaptive_reflow/eval/lipschitz_diagnostic.py` | BL metric triangle inequality (sampled) |
| `adaptive_reflow/eval/w2.py` | W2 metric axioms (sampled) |

## Tasks

1. **Install `hypothesis`** if not already in dev deps (check
   `pyproject.toml` `[project.optional-dependencies.dev]`); add if missing
2. **Create `tests/test_property_based/`** directory with one file per
   algorithm module
3. **For each module**: write 2-5 Hypothesis `@given` tests for the most
   important invariants. Pin seeds explicitly per Research 4 pitfall
   (un-seeded property tests on stochastic code are flaky).
4. **Verify**: `pytest tests/test_property_based/ -v` passes; compute
   coverage ratio
5. **Wire into CI** (auto-picked-up by pytest; no extra config needed
   beyond the marker registry)

## Files affected

- `tests/test_property_based/__init__.py` (NEW)
- `tests/test_property_based/test_scheduler_properties.py` (NEW)
- `tests/test_property_based/test_policy_driver_properties.py` (NEW)
- `tests/test_property_based/test_merge_operator_properties.py` (NEW)
- `tests/test_property_based/test_blender_properties.py` (NEW)
- `tests/test_property_based/test_sequential_properties.py` (NEW)
- `tests/test_property_based/test_evidence_driver_properties.py` (NEW)
- `tests/test_property_based/test_batched_runner_properties.py` (NEW)
- `tests/test_property_based/test_theory_properties.py` (NEW)
- `tests/test_property_based/test_eval_properties.py` (NEW)
- `pyproject.toml` (UPDATE; ensure `hypothesis` is in dev deps)
- `framework-internal-metrics.md` §1 B.7 (UPDATE; metric table reflects
  new state)

## Acceptance

- [ ] All 9+ new test files exist
- [ ] Each file has 2-5 `@given` tests with explicit seeds
- [ ] All property tests pass
- [ ] B.7 metric ≥ 0.40 in framework-internal-metrics rev 2
- [ ] `docs/baseline-audit-report.md` §B.7 updated to "MET"
- [ ] Commit + push

## Estimated time

2-4 hours CPU (no GPU; pure test writing + verification).

## Acceptance gate

**Gate name:** `G-B7-PROPERTY-BASED-TESTING` (new)

**Pre-condition:** Wave 15 Agent T completed A.7 must-fail fixtures
**Pass conditions:**
- [ ] All acceptance checklist items
- [ ] `docs/baseline-audit-report.md` §B.7 marked MET

## Pitfall (per Research 4)

Property-based tests are flaky on stochastic numerical code. Hypothesis
can shrink to a seed that triggers a legitimate random walk.
**Mitigation**: pin RNG (numpy.random.Generator + explicit seed) inside
the property test, or restrict property tests to deterministic
algorithms (e.g., deterministic ODE integrators) and use SBC for
stochastic ones.

## Out of scope

- Property tests for STOCHASTIC algorithms (covered separately by SBC task)
- Property tests for ADAPTER-specific code (D.3 task)
- Property tests for paper_quantities LAYER specifics (A.4 task already
  exists)

## Related

- `framework-internal-metrics.md` §1 B.7 (defines the metric)
- `framework-internal-metrics.md` §6 (initial current-value audit; B.7 = 0%)
- `todo/algo-improvement-traceability-hardening.md` (Wave 15 Agent T — sister task)
- `todo/algo-improvement-convergence-order.md` (C.6 — deterministic integrator verification)
- `todo/algo-improvement-sbc.md` (C.7 — stochastic verification)

## Wave 56 close-out

Status refreshed: B.7 property-based tests now cover 11+ modules (Wave 17 + Wave 24), with deterministic derandomize profile (Wave 38) ensuring CI reproducibility. Property tests remain a foundational layer that protects algorithm invariants in Wave 41-52 composite eval pipelines. Last touched commit: `811ca75` (Wave 55 Agent C: Author todo/INDEX.md master entry point).