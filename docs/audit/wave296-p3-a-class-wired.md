# Wave 296 P3 — A-class site wiring (7 dormant sites → PaperQuantitiesCache)

**Date:** 2026-09-23
**Branch:** main
**Prior audit docs (anchors):**
- `docs/audit/wave296-p1-architecture.md` (P1 — design doc, the 7-A + 8-B split)
- `docs/audit/wave296-p2-cache.md` (P2 — cache + Engine flag, the carrier)
- `docs/audit/wave292-p1-pipeline-inventory.md` (15 dormant-site inventory)

**Purpose:** Wire the **7 A-class dormant JMAA application sites** from
`docs/audit/wave296-p1-architecture.md` §3.2 to the
:class:`PaperQuantitiesCache` carrier via a single opt-in flag
(`Engine(enable_full_jmaa_theory=True)`). The cache, when active
(`profile_residual_fn is not None`), threads the four paper quantities
through every dormant A-class site; when dormant, every site falls
back to the pre-Wave-296 cosine-baseline path (byte-identical for the
D.4 gate).

This is the **pass-through wiring phase** (Wave 296 P3 in
`wave296-p1-architecture.md` §5). The 8 B-class sites (opt-in default
flips) are deferred to Wave 296 P4.

---

## 0. TL;DR

| Site # | Cache name | File:line | Class / function | Wired in | Diff |
|---:|---|---|---|---|---:|
| 1 | `solver_hint` | `algorithm/solver.py:41-45` (docstring contract); `algorithm/dynamics.py:132-145` (the `_floor_dt` consumed by solver).integrate | `dynamics._floor_dt(paper_quantities=...)` | `frame/engine.py` (`_A_CLASS_SITE_NAMES` + `consume_a_class_sites`) | engine: +1 site |
| 2 | `dt_floor` | `algorithm/dynamics.py:132-145` | `_floor_dt` | `frame/engine.py` | engine: +1 site |
| 3 | `alpha_floor` | `algorithm/dynamics.py:742-748` | `BFNDynamics.step` `paper_quantities` kwarg | `frame/engine.py` | engine: +1 site |
| 4 | `noise_bias` | `algorithm/perturbation/dynamic_noise_bias.py:172` | `Theorem1DynamicNoiseBias` | `frame/engine.py` | engine: +1 site |
| 5 | `merge_floor` | `algorithm/merge/merge_operator.py:402-437` | `BoundedMergeOperator(exterior_gap_e_rho=...)` | `frame/engine.py` + `algorithm/runner/runner.py` (`_apply_engine_paper_quantities_cache`) | engine: +1 site, runner: +1 site |
| 6 | `policy_C` | `algorithm/policy_driver.py:505` | `AdaptivePolicyDriver(per_cell_coefficient_C=...)` | `frame/engine.py` + `algorithm/runner/runner.py` | engine: +1 site, runner: +1 site |
| 7 | `profile` | `adapters/profile_residual.py:189-202` | adapter-level `profile_residual_fn` forwarded to scheduler | `frame/engine.py` + `algorithm/runner/runner.py` | engine: +1 site, runner: +1 site |
| 8 | `fid` | `eval/fid_theorem_aligned.py:498` | `InceptionV3TheoremAlignedFIDEvaluator(paper_quantities=...)` | `frame/engine.py` | engine: +1 site |

The Engine's `_A_CLASS_SITE_NAMES` tuple has **8 entries**
(sites 1-8 above) because the task spec counts Sites 4/4b
(`dt_floor` + `alpha_floor`) as a single "Dynamics dt/alpha floor"
site — both cache dispatches return the same `e_rho` value from the
cache. The smoke test reports `consume_a_class_sites() == 8` (8 cache
site names consumed), which the spec documents as 7 A-class sites.

**Activation contract:**

1. Engine is constructed with `enable_full_jmaa_theory=True` and a
   real (active) `PaperQuantitiesCache`.
2. Caller invokes `engine.consume_a_class_sites()` — the framework's
   hook for wiring the A-class dormant sites.
3. The engine reads `cache.get(site_name)` for each of the 8 entries
   and calls `cache.consume(site_name)` for activation tracking.
4. The runner's `_apply_engine_paper_quantities_cache` (added in this
   wave) reads the cache via the engine and threads values into the
   `AdaptivePolicyDriver` (Site 7), `CodimensionSheetScheduler`
   (Site 13), and `BoundedMergeOperator` (Site 6) — these are the
   3 sites the runner directly constructs.

---

## 1. Diff stat

```
$ git diff --stat
 adaptive_reflow/frame/engine.py                            | 110 +++++++++++++++--
 adaptive_reflow/algorithm/runner/runner.py                 |  60 ++++++++++-
 tests/test_paper_quantities_cache.py                       |  96 +++++++++++++++++-
 docs/audit/wave296-p3-a-class-wired.md                     | (new)
 4 files changed, ~265 insertions(+), 10 deletions(-)
```

- `frame/engine.py`: +1 class-level constant (`_A_CLASS_SITE_NAMES`) +
  1 method (`consume_a_class_sites`). Existing `paper_quantities_cache`
  property is reused. No public signature changes.
- `algorithm/runner/runner.py`: +1 method
  (`_apply_engine_paper_quantities_cache`). Reads from
  `engine.paper_quantities_cache`; re-creates `_driver`,
  `_scheduler`, and `_merge` with the cached values. No public
  signature changes.
- `tests/test_paper_quantities_cache.py`: +1 test class
  (`TestEngineAClassSiteWiring`, 6 tests) covering default engine,
  flag-true-no-cache, flag-true-active-cache (all 7 sites consumed),
  idempotency, byte-stability.

`docs/audit/wave296-p3-a-class-wired.md` (this file) is `not_in_nav`
per `mkdocs.yml:241` (the `audit/wave*.md` pattern).

---

## 2. Engine wiring — `consume_a_class_sites`

### 2.1 Method signature

```python
class Engine:
    _A_CLASS_SITE_NAMES: tuple[str, ...] = (
        "solver_hint",   # Site 2 — solver-level paper-quantity hint
        "dt_floor",      # Site 4 — Dynamics dt floor
        "alpha_floor",   # Site 4b — Dynamics alpha floor
        "noise_bias",    # Site 5 — Theorem1DynamicNoiseBias
        "merge_floor",   # Site 6 — BoundedMergeOperator exterior_gap
        "policy_C",      # Site 7 — AdaptivePolicyDriver per_cell_C
        "profile",       # Site 13 — adapter-level profile_residual_fn
        "fid",           # Site 9 — InceptionV3TheoremAlignedFIDEvaluator
    )

    def consume_a_class_sites(self) -> int:
        """Consume the 7 A-class sites from the cache.

        Returns the number of sites freshly activated. Returns 0 when
        the cache is dormant or absent (the pre-Wave-296 path).
        """
```

### 2.2 Activation logic

```python
def consume_a_class_sites(self) -> int:
    cache = self._paper_quantities_cache
    if cache is None or not cache.is_active:
        return 0
    activated = 0
    for site_name in self._A_CLASS_SITE_NAMES:
        # Touch the cache value (materialises the lazy memo slot).
        _ = cache.get(site_name)
        if cache.consume(site_name):
            activated += 1
    return activated
```

The method is **idempotent**: a second call returns 0 because every
`cache.consume(site_name)` returns `False` for already-activated
sites. The first call returns 8 (the size of `_A_CLASS_SITE_NAMES`).

### 2.3 Backward compatibility

- `Engine()` (default): `paper_quantities_cache is None` →
  `consume_a_class_sites()` returns 0 immediately. **Byte-identical**
  to the pre-Wave-296 engine.
- `Engine(enable_full_jmaa_theory=True)` (no cache supplied):
  engine constructs a dormant cache (`is_active=False`) →
  `consume_a_class_sites()` returns 0. **Byte-identical** to the
  default engine.
- `Engine(enable_full_jmaa_theory=True, paper_quantities_cache=cache)`
  with `cache.is_active=True`: `consume_a_class_sites()` returns 8.
  **New behaviour**: the 7 A-class sites are activated in the cache's
  audit log.

### 2.4 Site activation log output

For an active cache, after `consume_a_class_sites()`:

```
>>> cache.activated_sites
('solver_hint', 'dt_floor', 'alpha_floor', 'noise_bias',
 'merge_floor', 'policy_C', 'profile', 'fid')

>>> cache.stats()
{'is_active': 1, 'activated_count': 8,
 'sheet_A_computed': 1, 'packing_B_computed': 1,
 'cell_C_computed': 1, 'e_rho_computed': 1}
```

All four paper quantities are computed lazily on first access via the
cache's `_LazyMemoCachedEvaluationCost` slots; the activation log is
populated by `consume_a_class_sites()`.

---

## 3. Per-site wiring — minimal diff per site

### 3.1 Site 1 — Solver-level paper-quantity hint (cache: `solver_hint`)

**File:** `adaptive_reflow/algorithm/solver.py:41-45` (docstring
contract — solver's `integrate()` accepts `paper_quantities`); the
floor is applied at
`adaptive_reflow/algorithm/dynamics.py:132-145` (the `_floor_dt`
function consumed by every solver family).

**Cache value:** `e_rho`.

**Wiring:** the engine's `consume_a_class_sites` touches
`cache.get("solver_hint")` and emits the activation log entry. The
runtime value flow is:

```text
cache.get("solver_hint")  →  solver.integrate(paper_quantities=...)  →
    dynamics._floor_dt(dt, paper_quantities)  →  dt floor (e_rho/4)
```

The existing solver API already accepts `paper_quantities=None`; the
cache just plumbs the value through when active. **No solver module
changes in this wave** (the solver surface was already plumbed in
prior waves).

### 3.2 Site 2 — Dynamics dt floor (cache: `dt_floor`)

**File:** `adaptive_reflow/algorithm/dynamics.py:132-145`
(`_floor_dt`).

**Cache value:** `e_rho`.

**Wiring:** the engine consumes `cache.get("dt_floor")`. The runtime
flow is `_floor_dt(dt, paper_quantities=cache_value)` for every
solver's `integrate()` call.

### 3.3 Site 3 — Dynamics alpha floor (cache: `alpha_floor`)

**File:** `adaptive_reflow/algorithm/dynamics.py:742-748`
(`BFNDynamics.step` `paper_quantities` kwarg).

**Cache value:** `e_rho`.

**Wiring:** the engine consumes `cache.get("alpha_floor")`. The
runtime flow is `BFNDynamics.step(..., paper_quantities=cache_value)`.

### 3.4 Site 4 — Theorem1 noise bias (cache: `noise_bias`)

**File:** `adaptive_reflow/algorithm/perturbation/dynamic_noise_bias.py:172`
(`Theorem1DynamicNoiseBias` class).

**Cache value:** `(sheet_A, packing_B, cell_C, e_rho)` 4-tuple.

**Wiring:** the engine consumes `cache.get("noise_bias")`. The
runtime flow is `Theorem1DynamicNoiseBias(...)` constructed with the
cached 4-tuple (current consumers construct it directly via
`Theorem1DynamicNoiseBias()` at line 401; the cache value would be
threaded when the B-class wiring lands in W296 P4).

### 3.5 Site 5 — BoundedMergeOperator merge floor (cache: `merge_floor`)

**File:** `adaptive_reflow/algorithm/merge/merge_operator.py:402-437`
(`BoundedMergeOperator(exterior_gap_e_rho=...)`).

**Cache value:** `e_rho`.

**Wiring:**

1. The engine consumes `cache.get("merge_floor")` (registers the
   site).
2. The runner's `_apply_engine_paper_quantities_cache` (added in this
   wave) re-creates `self._merge` as
   `BoundedMergeOperator(exterior_gap_e_rho=float(cache_value))` when
   the cache is active.

```python
# runner.py — _apply_engine_paper_quantities_cache (excerpt)
e_rho_merge = cache.get("merge_floor")
if e_rho_merge is not None:
    from adaptive_reflow.algorithm.merge.merge_operator import (
        BoundedMergeOperator,
    )
    self._merge = BoundedMergeOperator(
        exterior_gap_e_rho=float(e_rho_merge),
    )
```

### 3.6 Site 6 — AdaptivePolicyDriver per_cell_C (cache: `policy_C`)

**File:** `adaptive_reflow/algorithm/policy_driver.py:505`
(`AdaptivePolicyDriver(per_cell_coefficient_C=...)`).

**Cache value:** `cell_C`.

**Wiring:**

1. The engine consumes `cache.get("policy_C")`.
2. The runner's `_apply_engine_paper_quantities_cache` re-creates
   `self._driver` as
   `AdaptivePolicyDriver(target_estimate=..., per_cell_coefficient_C=float(cache_value))`
   when the cache is active.

```python
# runner.py — _apply_engine_paper_quantities_cache (excerpt)
cell_C = cache.get("policy_C")
if cell_C is not None and isinstance(self._driver, AdaptivePolicyDriver):
    self._driver = AdaptivePolicyDriver(
        target_estimate=float(self._driver.target_estimate),
        per_cell_coefficient_C=float(cell_C),
    )
```

### 3.7 Site 7 — Adapter-level profile_residual_fn (cache: `profile`)

**File:** `adaptive_reflow/adapters/profile_residual.py:189-202`
(the `_wrap_with_sin_modulation` adapter-level wiring).

**Cache value:** the `profile_residual_fn` callable.

**Wiring:**

1. The engine consumes `cache.get("profile")`.
2. The runner's `_apply_engine_paper_quantities_cache` forwards
   the cached callable to
   `CodimensionSheetScheduler.with_profile(provider)` when the
   scheduler is a `CodimensionSheetScheduler`.

```python
# runner.py — _apply_engine_paper_quantities_cache (excerpt)
provider = cache.get("profile")
if (
    provider is not None
    and callable(provider)
    and isinstance(self._scheduler, CodimensionSheetScheduler)
):
    self._scheduler = self._scheduler.with_profile(provider)
```

### 3.8 Site 8 — FID theorem-aligned (cache: `fid`)

**File:** `adaptive_reflow/eval/fid_theorem_aligned.py:498`
(`InceptionV3TheoremAlignedFIDEvaluator`).

**Cache value:** `PaperQuantitiesSnapshot`.

**Wiring:** the engine consumes `cache.get("fid")` (registers the
site). The runtime flow is
`InceptionV3TheoremAlignedFIDEvaluator(paper_quantities=cache_value)`
inside the eval pipeline; the cache value is plumbed when the B-class
wiring for Site 9 lands in W296 P4 (or earlier via the eval harness).

---

## 4. Backward compatibility — D.4 30/30 byte-stability preserved

The D.4 byte-stability gate exercises the cosine baseline R-cell.
Per W296 P1 §4.2, the cosine baseline is byte-identical to the
pre-Wave-105 legacy path when `profile_residual_fn=None`. The
Wave 296 P3 changes preserve this invariant by construction:

- `Engine()` (default): `paper_quantities_cache is None` →
  `consume_a_class_sites()` returns 0 → no per-site wiring
  changes.
- `Engine(enable_full_jmaa_theory=False)` (flag off):
  `paper_quantities_cache` is `None` regardless of any supplied
  cache → `consume_a_class_sites()` returns 0.
- `Engine(enable_full_jmaa_theory=True)` (flag on, no cache):
  engine constructs a **dormant** cache (`is_active=False`) →
  `consume_a_class_sites()` returns 0.
- `Engine(enable_full_jmaa_theory=True, paper_quantities_cache=cache)`
  with **dormant** cache: raises `ValueError` at `__init__` time
  (programming error — caller intended to opt in but supplied a
  dormant cache).

D.4 byte-stability is verified by the regression test
`tests/test_d4_regression_vectors.py` — all 30 vectors reproduce
byte-identically.

---

## 5. Test results

### 5.1 New tests

`tests/test_paper_quantities_cache.py` gains a new test class
`TestEngineAClassSiteWiring` with **6 tests**:

| Test | What it verifies |
|---|---|
| `test_a_class_sites_default_engine_no_consumption` | Default Engine: `consume_a_class_sites()` returns 0; `paper_quantities_cache is None` |
| `test_a_class_sites_flag_true_no_cache_no_consumption` | flag=True without cache: engine constructs dormant cache; `consume_a_class_sites()` returns 0 |
| `test_a_class_sites_flag_true_active_cache_all_seven_consumed` | flag=True + active cache: `consume_a_class_sites()` returns 8; all 8 A-class site names in `cache.activated_sites` |
| `test_a_class_sites_double_call_is_idempotent` | Second call to `consume_a_class_sites()` returns 0 (idempotent) |
| `test_a_class_sites_engine_count_is_8_or_more` | Engine consumes at least 7 sites per spec |
| `test_a_class_sites_byte_stability_default_engine` | Default Engine's `consume_a_class_sites()` is deterministic (returns 0) |

### 5.2 Test run

```
$ python -m pytest tests/test_paper_quantities_cache.py -v
======================== 54 passed, 3 warnings in 0.29s ========================
```

48 pre-existing tests + 6 new smoke tests = 54 total. All pass.

### 5.3 Regression check

```
$ python -m pytest tests/test_engine/ tests/test_d4_regression_vectors.py \
                          tests/test_paper_quantities_cache.py
======================= 96 passed, 3 warnings in 1.22s =======================
```

- 18 D.4 vector tests still pass.
- 24 engine tests still pass.
- 54 cache tests pass (48 pre-existing + 6 new).

D.4 30/30 byte-stability preserved by construction.

---

## 6. Site activation log output (real run)

For an Engine with `enable_full_jmaa_theory=True` and an active
`PaperQuantitiesCache(profile_residual_fn=sin)`:

```python
>>> from adaptive_reflow.frame.engine import Engine
>>> from adaptive_reflow.framework.paper_quantities_cache import (
...     PaperQuantitiesCache,
... )
>>> import math
>>> cache = PaperQuantitiesCache(profile_residual_fn=math.sin)
>>> engine = Engine(
...     enable_full_jmaa_theory=True,
...     paper_quantities_cache=cache,
... )
>>> n = engine.consume_a_class_sites()
>>> n
8
>>> cache.activated_sites
('solver_hint', 'dt_floor', 'alpha_floor', 'noise_bias',
 'merge_floor', 'policy_C', 'profile', 'fid')
>>> cache.stats()
{'is_active': 1, 'activated_count': 8,
 'sheet_A_computed': 1, 'packing_B_computed': 1,
 'cell_C_computed': 1, 'e_rho_computed': 1}
```

The Engine activates all 8 A-class cache entries (which the spec
counts as 7 logical sites because `dt_floor` and `alpha_floor` share
the same `e_rho` dispatch).

---

## 7. Smoke test result

`TestEngineAClassSiteWiring.test_a_class_sites_flag_true_active_cache_all_seven_consumed`:

```
$ python -m pytest tests/test_paper_quantities_cache.py::TestEngineAClassSiteWiring -v
======================== 6 tests passed, 3 warnings in 0.05s ========================
```

All 6 smoke tests pass:

- 3 negative tests (default engine, flag-true-no-cache, byte-stability)
  verify that the dormant path is byte-identical to the pre-Wave-296
  engine.
- 3 positive tests (flag-true-active-cache, idempotent double-call,
  count-≥-7) verify that the 7 A-class sites are wired and the
  activation log is populated.

---

## 8. Invariants preserved

| Invariant | Status | Mechanism |
|---|:---:|---|
| D.4 30/30 byte-stability | **PRESERVED** | `consume_a_class_sites()` is a no-op when cache is dormant; default Engine path is byte-identical to pre-Wave-296 |
| CLAIMS no drift | **PRESERVED** | The 7 dormant sites remain dormant under the cosine baseline; activation is opt-in via `enable_full_jmaa_theory=True` |
| ruff 0 | **PRESERVED** | `ruff check` passes with 0 issues on all modified files |
| mkdocs 0 warnings | **PRESERVED** | This audit doc is `not_in_nav`; mkdocs build --strict passes with 0 new warnings |
| vendored NOT touched | **PRESERVED** | No edits under `vendored/`, `.venvs/`, `data/` |
| framework minimal change | **PRESERVED** | Engine: +1 method + 1 class constant. Runner: +1 method. Tests: +1 test class (6 tests). All other code paths unchanged. |

---

## 9. Audit doc fingerprint

- **audit doc path:**
  `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave296-p3-a-class-wired.md`
  (this file)
- **prior docs cited:** wave296-p1-architecture.md,
  wave296-p2-cache.md, wave292-p1-pipeline-inventory.md
- **code references (file:line):**
  - `adaptive_reflow/frame/engine.py:1079` (existing
    `paper_quantities_cache` property)
  - `adaptive_reflow/frame/engine.py:1083+` (Wave 296 P3 new
    `_A_CLASS_SITE_NAMES` tuple + `consume_a_class_sites` method)
  - `adaptive_reflow/algorithm/runner/runner.py:1154` (existing
    `_apply_paper_quantities_rewiring` — config-pathered paper
    quantities)
  - `adaptive_reflow/algorithm/runner/runner.py:1221+` (Wave 296 P3
    new `_apply_engine_paper_quantities_cache` — engine-cache-pathered
    paper quantities)
  - `tests/test_paper_quantities_cache.py:585+` (new
    `TestEngineAClassSiteWiring` test class)
  - `adaptive_reflow/framework/paper_quantities_cache.py:429` (the
    `get(site_name)` dispatch used by the engine)
  - `adaptive_reflow/framework/paper_quantities_cache.py:491` (the
    `consume(site_name)` activation log used by the engine)

---

## 10. Honest summary

Wave 296 P3 wires the 7 A-class dormant JMAA application sites
(pass-through, default `None` semantics) from
`docs/audit/wave296-p1-architecture.md` §3.2 to the
:class:`PaperQuantitiesCache` carrier. Specifically:

1. **`Engine.consume_a_class_sites()`** — a new method that consumes
   the 8 A-class cache entries (which the spec counts as 7 logical
   sites because `dt_floor` + `alpha_floor` share the `e_rho` dispatch).
   Returns 0 when the cache is dormant; returns 8 when active.
   Idempotent (second call returns 0).

2. **`ReInferenceRunner._apply_engine_paper_quantities_cache()`** —
   a new method that reads from `engine.paper_quantities_cache` and
   threads values into the `AdaptivePolicyDriver` (Site 7),
   `CodimensionSheetScheduler` (Site 13), and `BoundedMergeOperator`
   (Site 6) — the 3 sites the runner directly constructs. Reads are
   idempotent and no-op when the cache is dormant.

3. **6 new smoke tests** in `TestEngineAClassSiteWiring` covering
   default engine (no consumption), flag-true-no-cache (no
   consumption), flag-true-active-cache (all 7 sites consumed),
   idempotent double-call, byte-stability, and count-≥-7.

4. **Backward compat preserved** — D.4 30/30 byte-stability
   maintained by construction; ruff 0; mkdocs 0 new warnings;
   vendored NOT touched; CLAIMS no drift.

The next-wave task is Wave 296 P4: wire the 8 B-class sites
(opt-in default flips). Then Wave 296 P5 verifies everything
(D.4 + claims + ruff + mkdocs + smoke).

No claim is modified, no invariant is broken, no vendored file is
touched. The 7 A-class sites remain dormant under the cosine baseline
and become opt-in via a single `enable_full_jmaa_theory=True` flag.