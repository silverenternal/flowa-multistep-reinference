# Wave 59 Agent 3 — BRAI (PerturbationPolicy) implementation

**Date:** 2026-09-07
**Wave:** 59 (MFPQA + BRAI, Paper A + Paper B)
**Agent:** 3 of 5 (PerturbationPolicy interface + BRAI algorithm)
**Status:** complete
**Constraint locked in:** interface-first (`todo/two-paper-algo-design.md` §1, §8)

## Scope

1. Designed abstract `PerturbationPolicy` Protocol (mirrors
   `MergeOperatorProtocol` and `IntegratorProtocol` patterns).
2. Implemented `UniformFreshPerturbation` — preserved default
   behavior; byte-stable for Wave 47 / 52 / 58 results.
3. Implemented `PaperQuantityAttractorInversion` (BRAI) — new
   opt-in algorithm that perturbs saturated state along
   `-grad(log P_qty)`.
4. Added 33 test cases (40 after parametrize expansion) in
   `tests/test_algorithm/test_perturbation.py`.
5. Verified no regression on Wave 59 Agent 1 integrator tests
   (40 perturbation + 29 integrator = 69 pass).

## Files

| Path | Action | Notes |
|---|---|---|
| `adaptive_reflow/algorithm/perturbation.py` | NEW | 700+ LOC module |
| `tests/test_algorithm/test_perturbation.py` | NEW | 33 tests |
| `docs/audit/wave59-brai-impl.md` | NEW | this file |

## Constraint compliance (§1 / §8 of design doc)

**Interface-first:** Protocol landed BEFORE the new algorithm
(§8 — "Interface design must be merged before any
implementation lands").

**Old preserved:** `UniformFreshPerturbation` reproduces the
deterministic ``standard_normal(x.shape)`` semantics the
adapter-level restart paths have used since Wave 0. Existing
adapters that do their own inlined
``np.random.default_rng(seed).standard_normal(...)`` keep
working unchanged; no data loss.

**New opt-in:** `PaperQuantityAttractorInversion` is opt-in via
explicit class selection (`perturbation=PaperQuantityAttractorInversion(...)`).
Default behavior is preserved.

## Design

### Protocol

```python
class PerturbationPolicy(Protocol):
    def propose(
        self,
        x_saturated: Any,
        paper_quantities: Optional[Mapping[str, Any]],
        t: float,
    ) -> Any: ...
    def config_hash(self) -> str: ...
    def to_config(self) -> dict[str, Any]: ...
    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "PerturbationPolicy": ...
```

Mirrors `IntegratorProtocol` (Wave 59 Agent 1) and
`MergeOperatorProtocol` (`adaptive_reflow/algorithm/merge_operator.py:248`).
`runtime_checkable` so callers can use `isinstance(policy, PerturbationPolicy)`.

### UniformFreshPerturbation (PRESERVED)

Returns ``standard_normal(x.shape)`` with seed
``hash((x.shape, t))``. The seed derivation is deterministic so
identical inputs always yield identical noise. The class is a
drop-in replacement for the inlined fresh-noise blocks in each
adapter's ``apply_restart_distribution``.

Constructor takes an optional ``seed_offset`` so adapters can
rotate the noise stream without subclassing; ``seed_offset=0``
reproduces the Wave 47 / 52 / 58 behavior bit-for-bit.

### PaperQuantityAttractorInversion (BRAI — NEW)

At saturation, perturb along ``-grad(log P_qty(x))`` so the
trajectory escapes the baseline's attractor:

```
x_perturbed = x_saturated + eps_scale * (-grad log P_qty)
```

Constructor knobs:
- ``eps_scale`` (default 0.1) — push magnitude.
- ``grad_eps`` (default 1e-3) — finite-difference step.
- ``log_p_qty`` (optional) — scalar callable ``(x, t) -> float``.
- ``grad_log_p_qty`` (optional) — analytic gradient callable
  ``(x, t, e_rho) -> ndarray``.
- ``default_sigma`` (default 1.0) — Gaussian prior scale when
  ``e_rho`` is missing from the snapshot.

**Priority for gradient computation** (graceful degradation):
1. User-supplied ``grad_log_p_qty`` (analytic).
2. Finite-difference on user-supplied ``log_p_qty``.
3. Analytic Gaussian gradient with snapshot's ``e_rho``
   (default fallback).

**Graceful fallback paths** (audit codes):
- `BRAI_NO_PAPER_QUANTITIES` — `paper_quantities is None`.
- `BRAI_FALLBACK_FIELDS_MISSING` — `e_rho` accessor absent.
- `BRAI_NONFINITE_QUANTITY_COERCED` — non-finite `e_rho`.
- `BRAI_GRAD_FALLBACK_TO_FD` — no analytic gradient supplied.

## Math derivation (Gaussian prior default)

With the default isotropic Gaussian prior

```
log P_qty(x) = -||x||^2 / (2 * sigma^2)
```

the gradient is

```
grad log P_qty(x) = -x / sigma^2
```

so the BRAI push direction is

```
-grad log P_qty(x) = x / sigma^2
```

and the perturbation is

```
x_perturbed = x + eps_scale * (x / sigma^2)
            = x * (1 + eps_scale / sigma^2)
```

— a radially-outward push from the origin (the canonical
"invert the attractor" behaviour). For any non-zero
``x_saturated``, the L2 norm strictly grows.

## Tests

40 test cases (33 functions × parametrize expansions) in
`tests/test_algorithm/test_perturbation.py`:

**Test 1 — UniformFreshPerturbation preserved** (7 tests):
- byte-stable legacy semantics (default ``seed_offset = 0``).
- different ``t`` produces different noise.
- ``isinstance(policy, PerturbationPolicy)``.
- ignores ``paper_quantities``.
- validates ``seed_offset``.
- ``from_config(to_config())`` round-trip.
- config-hash distinguishes offsets.

**Test 2 — BRAI inverts the prior** (6 tests):
- direction = ``-grad`` (radially outward for Gaussian prior).
- analytic ``grad_log_p_qty`` callable consumed (no FD fallback).
- finite-difference when only ``log_p_qty`` supplied.
- FD gradient accuracy (within ``O(grad_eps^2)`` of analytic).
- ``x_saturated`` is not mutated.
- default coefficients match design doc.

**Test 3 — Graceful fallback** (6 tests):
- ``paper_quantities is None`` → uniform-fresh + audit code.
- missing ``e_rho`` accessor → uniform-fresh + audit code.
- silent fallback when ``audit_codes=None``.
- non-finite ``e_rho`` → ``default_sigma`` + audit code.
- ``eps_scale`` validation (rejects 0/negative/non-finite).
- ``grad_eps`` validation.
- ``default_sigma`` validation.

**Test 4 — Config round-trip** (4 tests):
- BRAI ``from_config(to_config())`` round-trip (callables lost).
- config-hash distinguishes coefficients.
- ``build_perturbation_from_config`` dispatches both families.
- rejects unknown family / non-dict config.

**Test 5 — Math properties** (parametrized):
- radial push outward for Gaussian prior (5 radii).
- direction preserved for scalar saturation (4 sign cases).
- output shape preservation (3 shapes).
- ``eps_scale = 0`` rejected, ``1e-12`` accepted.
- callable-shaped snapshot consumed.

## Verification

```
$ pytest tests/test_algorithm/test_perturbation.py --noconftest
... 40 passed in 0.21s
```

(Note: `--noconftest` bypasses a pre-existing bug in
`tests/conftest.py:220-271` where the `serial_tool` autouse
fixture is a generator but doesn't yield when `PYTEST_SERIAL`
is unset — affects ALL tests in the repo, including the Wave 59
Agent 1 integrator tests. Outside Wave 59 Agent 3's disjoint
scope.)

```
$ pytest tests/test_algorithm/test_integrator.py
  tests/test_algorithm/test_perturbation.py --noconftest
... 69 passed in 0.21s
```

No regression on Wave 59 Agent 1's integrator suite.

## Design-doc compliance

- §3.2 / §4.2: Protocol + preserved + opt-in new. Done.
- §5 step 5: design Protocol first. Done.
- §5 step 6: implement preserved (UniformFresh). Done.
- §5 step 7: implement new (BRAI). Done.
- §5 step 8: wire into adapters — DEFERRED to separate wave
  (per §5 table, this is "Wire `PerturbationPolicy` into
  adapters" which is explicitly "separate from the interface +
  implementation steps"). Until that wire lands, every existing
  adapter keeps its inlined fresh-noise path unchanged.
- §8 interface-first: Protocol landed before new algorithm.
  Done.
- §8 old-path preservation: every existing adapter that does
  its own ``np.random.default_rng(seed).standard_normal(...)``
  block keeps working unchanged. Done.
- §8 A/B comparison: deferred to next wave (alongside MFPQA
  comparison from Wave 59 Agent 1).

## Notes

1. The Protocol deliberately accepts the ``t`` argument so the
   uniform-fresh seed can rotate per-round (different ``t``
   yields different noise) without forcing every concrete impl
   to consume ``t`` semantically.
2. The BRAI class is ``__init__``-configurable for both
   ``log_p_qty`` (scalar) and ``grad_log_p_qty`` (vector) so
   adapters with closed-form paper-quantity distributions can
   skip the FD overhead and adapters with only a Monte-Carlo
   estimator can still consume the protocol.
3. The default Gaussian prior ``log P_qty ∝ -||x||^2 / (2 * e_rho^2)``
   uses ``e_rho`` (paper Lemma 4 / 5's minimum-energy-gap scale)
   as the prior's standard deviation — dimensionally consistent
   with the paper's energy-gap units. Adapters that need a
   different scale pass ``default_sigma`` to the constructor.
4. BRAI's audit codes are gated on ``audit_codes is not None``
   so the legacy callers that opt out of audit emission get the
   silent fallback path that matches the legacy semantics for
   callers that have not opted into audit emission.

## Next wave

- Wire `PerturbationPolicy` into `apply_restart_distribution`
  in each adapter (Kanzi + LineageFlow first; same scope as
  Wave 59 Agent 1's integrator wire-in).
- A/B comparison: same seed + NFE, `UniformFreshPerturbation`
  vs `PaperQuantityAttractorInversion` — show
  `framework_continues_gain_at_high_nfe` per §4.3 of the
  design doc.
- Verify the closed-form ``grad_log_p_qty`` path with a
  Kanzi/LineageFlow-specific snapshot accessor (currently
  only the protocol shape is tested).
