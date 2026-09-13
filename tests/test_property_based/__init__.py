"""Property-based test suite (B.7 — ``framework-internal-metrics.md`` rev 2 §1).

The framework's hand-written isolation tests (36 of them, Wave 14 W3 rescue)
verify a finite set of pinned inputs against expected outputs. Property-based
tests, by contrast, drive each algorithm module with randomly-generated inputs
and assert mathematical invariants (monotonicity, associativity, commutativity,
idempotency, convex-combination structure, …). Hypothesis shrinks counter-
examples to the minimal reproducer, surfacing edge cases the hand-written tests
miss.

Per Research 4 (pitfall): property-based tests on stochastic numerical code are
flaky — Hypothesis can shrink to a seed that triggers a legitimate random
walk. **Mitigation**: every property in this directory either pins an explicit
``numpy.random.Generator(seed=...)`` or restricts its scope to deterministic
algorithms (per-round capacity schedulers, closed-form paper quantities,
bounded-merge arithmetic, blender convex combinations). Stochastic-only
algorithms are covered by the C.7 SBC task, not here.

Seed policy (B.7 acceptance):
    Every ``@given`` test below uses one of two seed-pin strategies:
      (a) ``PhaseManager().given(seed=...)`` + ``@settings(...)``  — pin
          *both* the outer RNG and Hypothesis's internal deriver.
      (b) ``example(...)`` + ``seed=``-pinned strategies at the module
          level for deterministic-algorithm tests where Hypothesis's
          internal shrinker has no stochastic surface to vary.

The seeds are reused across property tests within a single module so a
regression surfaces byte-identical inputs across runs.
"""
