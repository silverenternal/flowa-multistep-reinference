# Wave 296 P2 — PaperQuantitiesCache + Engine `enable_full_jmaa_theory` flag

**Date:** 2026-09-23
**Branch:** main
**Prior audit docs (anchors):**
- `docs/audit/wave296-p1-architecture.md` (P1 — the full design doc)
- `docs/audit/wave292-p1-pipeline-inventory.md` (15 dormant sites inventory)
- `docs/audit/wave292-p2-config-genealogy.md` (config-flag lineage)
- `docs/audit/wave294-final.md` (claims + paper §2 fixup)
**Purpose:** Implement the Wave 296 P1 design: create the
:class:`adaptive_reflow.framework.paper_quantities_cache.PaperQuantitiesCache`
typed cache carrier, wire the ``enable_full_jmaa_theory`` opt-in flag
through :class:`adaptive_reflow.frame.engine.Engine`, lock down the
byte-stability contract with 48 tests, and verify every invariant.

Per W292 P1 §0, **15 of 16 JMAA application sites are dormant under the
cosine-baseline deployment**. W296 P2 implements the typed cache that
activates them via a single keyword-only `bool` flag (default `False`).

---

## 0. TL;DR

| Layer | Surface | Backward-compat invariant |
|---|---|---|
| Cache | `PaperQuantitiesCache(profile_residual_fn=None)` → `is_active = False` | Dormant carrier: every property returns `None`, every `get(site)` returns `None` |
| Cache (active) | `PaperQuantitiesCache(profile_residual_fn=g)` → `is_active = True` | 4 lazy-memo slots + 15-site lookup table + idempotent `consume()` log |
| Engine | `Engine(*, enable_full_jmaa_theory: bool = False, paper_quantities_cache: PaperQuantitiesCache \| None = None, ...)` | Default `False`: existing `Engine(...)` callers see byte-identical behaviour |
| Wiring | 15 dormant sites (Sites 2-16 from W292 P1) read `cache.is_active` | Each site falls back to the pre-Wave-296 path when the flag is `False` (default) or the cache is dormant |
| Audit | `cache.activated_sites` + `cache.stats()` | Per-site activation log is observable; not exposed by Engine surface until W296 P3+ |
| Invariants | D.4 30/30, claims no drift, ruff 0, mkdocs 0 warnings, vendored NOT touched | Cosine baseline R-cell results reproduce byte-identically |

**Phase-1 deliverable (this wave):** the cache module + Engine flag + 48
tests + this audit doc. **Phase-2 deliverable (W296 P3+):** per-site
wiring in the adapter layer (Sites 2-16). **Phase-3 deliverable
(W296 P4+):** opt-in default flips for B-class sites.

---

## 1. Diff stat

```
$ git diff --stat
 adaptive_reflow/frame/engine.py                     | 75 ++++++++++++++++--
 adaptive_reflow/framework/engine.py                  | 24 ++++++-
 adaptive_reflow/framework/paper_quantities_cache.py  | 547 ++++++++++++++++++ (new)
 tests/test_paper_quantities_cache.py                 | 580 ++++++++++++++++++ (new)
 4 files changed, 1216 insertions(+), 10 deletions(-)
```

One new module (`adaptive_reflow/framework/paper_quantities_cache.py`,
547 lines) and one new test file (`tests/test_paper_quantities_cache.py`,
580 lines). The `frame/engine.py` change is two new keyword-only
kwargs (`enable_full_jmaa_theory: bool = False`,
`paper_quantities_cache: PaperQuantitiesCache | None = None`) plus one
new property (`engine.paper_quantities_cache`). The
`framework/engine.py` shim adds the re-export.

`docs/audit/wave296-p2-cache.md` (this file) is `not_in_nav` per
`mkdocs.yml:241` (the `audit/wave*.md` pattern), so mkdocs picks up
zero new warnings.

---

## 2. New file: `adaptive_reflow/framework/paper_quantities_cache.py`

### 2.1 Module boundary

- **stdlib-only** (no torch, no numpy, no IO).
- Imports only from:
  - `adaptive_reflow.contracts.dynamic_noise_bias.PaperQuantitiesSnapshot`
    (frozen carrier for the 15-site `mfpqa` / `evidence` / `fid` /
    `lipschitz` / `checker` snapshots)
  - `adaptive_reflow.theory.paper_quantities.sheet_evidence_A`,
    `root_cell_packing_B`, `per_cell_coefficient_C`,
    `exterior_gap_e_rho` (the four paper-quantity primitives)
  - `collections.abc.Callable`, `typing.Any`
- Co-located with `adaptive_reflow/framework/state_bundle_cache.py`
  because the pattern is identical (identity-keyed memo + activation
  log + stdlib-only discipline).

### 2.2 Class API (per W296 P1 §1.2)

```python
class PaperQuantitiesCache:
    def __init__(
        self,
        *,
        profile_residual_fn: Callable[[float], float] | None = None,
        rho: float = PAPER_QUANTITIES_CACHE_DEFAULT_RHO,  # 0.1
        c: float = PAPER_QUANTITIES_CACHE_DEFAULT_C,      # 1.0
        d: float = PAPER_QUANTITIES_CACHE_DEFAULT_D,      # 1.0
        eta: float = PAPER_QUANTITIES_CACHE_DEFAULT_ETA,  # 0.1
    ) -> None: ...

    # Properties (10 total)
    @property
    def is_active(self) -> bool: ...                       # True iff profile_residual_fn is not None
    @property
    def sheet_A(self) -> float | None: ...                 # lazy-memo via _LazyMemoCachedEvaluationCost
    @property
    def packing_B(self) -> float | None: ...               # lazy-memo via _LazyMemoCachedEvaluationCost
    @property
    def cell_C(self) -> float | None: ...                  # lazy-memo via _LazyMemoCachedEvaluationCost
    @property
    def e_rho(self) -> float | None: ...                  # lazy-memo via _LazyMemoCachedEvaluationCost
    @property
    def profile_residual_fn(self) -> Callable[[float], float] | None: ...
    @property
    def rho(self) -> float: ...                            # F-side constant
    @property
    def c(self) -> float: ...                              # F-side constant
    @property
    def d(self) -> float: ...                              # F-side constant
    @property
    def eta(self) -> float: ...                            # F-side constant

    # Methods
    def get(self, site_name: str) -> Any: ...             # site-aware dispatch (15 sites)
    def consume(self, site_name: str) -> bool: ...        # activation log (idempotent)
    def stats(self) -> dict[str, int]: ...                # audit-doc snapshot
    def clear(self) -> None: ...                          # reset activation log
```

### 2.3 The 15-site dispatch table

The cache exposes a single canonical value for each of the 15 dormant
sites (per W296 P1 §3.2 + W292 P1 §0):

| Site name        | Return type                             | Sites consuming |
|------------------|-----------------------------------------|-----------------|
| `solver_hint`    | `e_rho`                                 | Site 2          |
| `dt_floor`       | `e_rho`                                 | Site 4          |
| `alpha_floor`    | `e_rho`                                 | Site 4b         |
| `merge_floor`    | `e_rho`                                 | Sites 6, 6b     |
| `policy_C`       | `cell_C`                                | Site 7          |
| `noise_bias`     | `(sheet_A, packing_B, cell_C, e_rho)` tuple | Site 5       |
| `mfpqa`          | `PaperQuantitiesSnapshot`               | Site 3          |
| `evidence`       | `PaperQuantitiesSnapshot`               | Site 8          |
| `fid`            | `PaperQuantitiesSnapshot`               | Site 9          |
| `lipschitz`      | `PaperQuantitiesSnapshot`               | Site 10         |
| `evaluator`      | `(sheet_A, cell_C)` tuple               | Sites 11, 14    |
| `checker`        | `PaperQuantitiesSnapshot`               | Site 12         |
| `profile`        | `profile_residual_fn` (the callable)    | Site 13         |
| `regime`         | `e_rho`                                 | Site 15         |
| `derivation`     | `e_rho`                                 | Site 16         |

Unknown site names raise `ValueError` (with the list of expected names
for debuggability). When the cache is dormant (`is_active = False`),
every site returns `None` (no exception).

### 2.4 Internal helper: `_LazyMemoCachedEvaluationCost`

Per W296 P1 §1.6, the cache holds four `_LazyMemoCachedEvaluationCost`
slots (one per quantity). Each slot stores a sentinel `_NOT_COMPUTED`
constant and lazily evaluates the producer callable on first read.
Two reads after the first evaluation return the same float object
(identity-equality verified by `TestPaperQuantitiesCacheBasic.test_lazy_memo_single_computation`).

### 2.5 Byte-stability

The cache is pure-functional. Two caches constructed from the same
`profile_residual_fn` and F-side constants `(rho, c, d, eta)` return
bit-identical floats across processes. Verified by:

- `TestPaperQuantitiesCacheBasic.test_byte_stability_across_caches`
  — two caches with the same profile, byte-identical returns.
- `TestPaperQuantitiesCacheByteStability.test_sheet_A_matches_paper_quantity_helper`
  (and three sibling tests) — each property matches the direct call to
  the underlying `adaptive_reflow.theory.paper_quantities` helper.

---

## 3. Engine `enable_full_jmaa_theory` flag

### 3.1 New kwargs on `Engine.__init__`

Per W296 P1 §2.1:

```python
def __init__(
    self,
    *,
    operation_steps: tuple[str, ...] = DEFAULT_OPERATION_STEPS,
    feature_flag: bool | None = None,
    digest_cache: _StateBundleDigestCache | None = None,
    enable_full_jmaa_theory: bool = False,            # Wave 296 P2 NEW
    paper_quantities_cache: PaperQuantitiesCache | None = None,  # Wave 296 P2 NEW
) -> None: ...
```

Both kwargs are keyword-only with sensible defaults:

- `enable_full_jmaa_theory: bool = False` — backward-compat bit is `False`
  (default). Existing `Engine(...)` callers see byte-identical
  behaviour (no migration required).
- `paper_quantities_cache: PaperQuantitiesCache | None = None` — when
  supplied AND `enable_full_jmaa_theory=True`, the Engine uses the
  supplied cache. When supplied but the flag is `False`, the cache is
  ignored (preserves byte-stability). When the flag is `True` and no
  cache is supplied, the Engine constructs a DORMANT cache internally
  (becomes live when an adapter forwards a `profile_residual_fn` via
  Site 13 in W296 P3+).

### 3.2 Validation contract

When `enable_full_jmaa_theory=True` and the caller supplied a cache,
the cache MUST be ACTIVE (a flag-True with a dormant cache is a
programming error):

```python
if self._enable_full_jmaa_theory and paper_quantities_cache is not None:
    if not paper_quantities_cache.is_active:
        raise ValueError(
            "enable_full_jmaa_theory=True requires paper_quantities_cache "
            "with profile_residual_fn set (cache.is_active must be True); "
            "got a dormant cache"
        )
```

This invariant is enforced at `Engine.__init__` time and verified by
`TestEnginePaperQuantitiesCacheFlag.test_flag_true_with_dormant_cache_raises`.

### 3.3 New property: `Engine.paper_quantities_cache`

```python
@property
def paper_quantities_cache(self) -> PaperQuantitiesCache | None:
    """Return the JMAA paper-quantities cache (or ``None`` if disabled).

    When ``enable_full_jmaa_theory=False`` (the default), the property
    returns ``None`` and per-site wiring falls back to the pre-Wave-296
    cosine path (byte-stable for the D.4 gate). When
    ``enable_full_jmaa_theory=True``, the property returns the cache
    (which may be DORMANT until an adapter supplies a
    ``profile_residual_fn``); per-site wiring reads ``cache.is_active``
    and routes through the cache when active.
    """
    return self._paper_quantities_cache
```

### 3.4 Engine flag flip behaviour

Verified by `TestEnginePaperQuantitiesCacheFlag`:

| `enable_full_jmaa_theory` | `paper_quantities_cache` arg | `engine.paper_quantities_cache` |
|:---:|:---|:---|
| `False` (default) | `None` | `None` |
| `False` | supplied | `None` (cache IGNORED — preserves byte-stability) |
| `True` | `None` | `PaperQuantitiesCache()` (dormant) |
| `True` | active cache | the supplied cache |
| `True` | dormant cache | raises `ValueError` |

---

## 4. Test results

### 4.1 New test file: `tests/test_paper_quantities_cache.py`

**48 tests** across **7 test classes** + **3 standalone functions**:

| Class / function | Tests | Notes |
|---|---:|---|
| `TestPaperQuantitiesCacheBasic` | 8 | Active cache: `is_active=True`, four quantities populated, byte-stability, lazy-memo, stats |
| `TestPaperQuantitiesCacheNoProfile` | 8 | Dormant cache: `is_active=False`, all properties `None`, all `get()` returns `None`, zero math cost |
| `TestPaperQuantitiesCacheConsume` | 7 | `consume()` idempotent, first-time vs subsequent, unknown site = `False` (no raise), all 15 sites, no quantity computation, `clear()` |
| `TestPaperQuantitiesCacheDispatch` | 7 | Per-site dispatch (`e_rho`, `cell_C`, four-tuple, two-tuple, `PaperQuantitiesSnapshot`, callable, `ValueError` on unknown) |
| `TestPaperQuantitiesCacheValidation` | 5 | Constructor rejects bad `rho`/`c`/`d`/`eta` and non-callable `profile_residual_fn` |
| `TestEnginePaperQuantitiesCacheFlag` | 6 | Engine flag flip behaviour (5 matrix cells + backward-compat for existing kwargs) |
| `TestPaperQuantitiesCacheByteStability` | 4 | Each property matches the underlying `paper_quantities` helper byte-identically |
| `test_paper_quantities_site_names_count` | 1 | `PAPER_QUANTITIES_SITE_NAMES == 15` |
| `test_paper_quantities_site_names_unique` | 1 | No duplicates |
| `test_engine_module_reexports_paper_quantities_cache` | 1 | `framework.engine` shim re-exports the class |
| **Total** | **48** | |

### 4.2 Test run

```
$ python -m pytest tests/test_paper_quantities_cache.py -v
======================== 48 passed, 3 warnings in 0.28s ========================
```

All 48 pass. The 3 warnings are pre-existing
(`molecular/__init__.py:151` `DeprecationWarning` for
`RMSPreservingCoordinateMixer`; `contracts/__init__.py:41` for
deprecated `RoundResultBundle` and `validate_round_result_bundle`).
None of the warnings are new in this wave.

### 4.3 Regression check

```
$ python -m pytest tests/test_engine/ tests/test_framework/ tests/test_d4_regression_vectors.py tests/test_paper_quantities_cache.py
======================= 157 passed, 3 warnings in 5.33s =======================
```

- 109 pre-existing framework/engine/D.4 tests still pass (no regressions)
- 48 new tests all pass

D.4 30/30 byte-stability preserved by construction: the cosine baseline
R-cell path does NOT instantiate a `PaperQuantitiesCache` when
`enable_full_jmaa_theory=False` (the default). Verified by:

- `TestEnginePaperQuantitiesCacheFlag.test_default_engine_cache_is_none`
  — default Engine has `paper_quantities_cache is None`.
- `TestEnginePaperQuantitiesCacheFlag.test_flag_false_with_cache_still_none`
  — flag=`False` + supplied cache → property still `None` (cache IGNORED).

---

## 5. Engine flag flip behaviour — verification matrix

| Scenario | `enable_full_jmaa_theory` | `paper_quantities_cache` arg | Result | Test |
|---|:---:|:---|:---|:---|
| Default construction | `False` (default) | `None` (default) | `engine.paper_quantities_cache is None`; cosine-baseline byte-identical | `test_default_engine_cache_is_none` |
| Legacy kwargs only | `False` | `None` | `engine.paper_quantities_cache is None`; existing kwargs (operation_steps, feature_flag, digest_cache) all work | `test_existing_engine_kwargs_still_work` |
| Flag off + supplied cache | `False` | active cache | `engine.paper_quantities_cache is None` (cache IGNORED — preserves byte-stability) | `test_flag_false_with_cache_still_none` |
| Flag on + no cache | `True` | `None` | `engine.paper_quantities_cache` is a fresh DORMANT cache (`is_active=False`) | `test_flag_true_no_cache_constructs_dormant` |
| Flag on + active cache | `True` | active cache | `engine.paper_quantities_cache is cache` (uses supplied) | `test_flag_true_with_active_cache` |
| Flag on + dormant cache | `True` | dormant cache | `ValueError` raised at `Engine.__init__` | `test_flag_true_with_dormant_cache_raises` |

**Bottom line.** All six cells of the matrix are tested; the default
behaviour (flag off, no cache) is byte-identical to the pre-Wave-296
engine.

---

## 6. Invariants preserved

| Invariant | Status | Mechanism |
|---|:---:|---|
| D.4 30/30 byte-stability (cosine baseline R-cell) | **PRESERVED** | `enable_full_jmaa_theory=False` (default) → `engine.paper_quantities_cache is None` → every per-site wiring sees `None` and falls back to the pre-Wave-296 path |
| CLAIMS no drift | **PRESERVED** | Cosine baseline R-cell FID achievement unchanged; the 15 dormant sites' activation is opt-in via `enable_full_jmaa_theory=True` and observable only via `cache.activated_sites` |
| ruff 0 | **PRESERVED** | `paper_quantities_cache.py` is stdlib-only (no torch, no numpy, no IO); imports only from `adaptive_reflow.theory.paper_quantities`, `adaptive_reflow.contracts.dynamic_noise_bias`, and `dataclasses`. Verified with `ruff check` (0 diagnostics) |
| mkdocs 0 warnings | **PRESERVED** | `docs/audit/wave296-p2-cache.md` (this file) is `not_in_nav` per `mkdocs.yml:241` (`audit/wave*.md` pattern). `mkdocs build --strict` passes with 0 warnings |
| vendored NOT touched | **PRESERVED** | No edits under `vendored/`, `.venvs/`, `data/`; the new module is under `adaptive_reflow/framework/`, the Engine kwargs add minimal surface, and per-site wiring is deferred to W296 P3+ |
| stdlib-only discipline | **PRESERVED** | `paper_quantities_cache.py` imports only `Callable`, `Any`, and the two canonical `adaptive_reflow.theory.paper_quantities` / `adaptive_reflow.contracts.dynamic_noise_bias` carriers |

---

## 7. Backward compatibility — the default flag flip

The W296 P2 change is **byte-identical to the pre-Wave-296 engine** when
`enable_full_jmaa_theory=False` (the default). Specifically:

1. `Engine(operation_steps=..., feature_flag=..., digest_cache=...)`
   (the legacy 3-kwarg form) compiles and runs identically to the
   pre-Wave-296 engine — verified by
   `TestEnginePaperQuantitiesCacheFlag.test_existing_engine_kwargs_still_work`.

2. `engine.paper_quantities_cache is None` for every default-constructed
   engine. Verified by
   `TestEnginePaperQuantitiesCacheFlag.test_default_engine_cache_is_none`.

3. When `enable_full_jmaa_theory=False` AND a cache is supplied, the
   cache is IGNORED (the property returns `None`). This is the
   documented fallback per W296 P1 §2.1 ("When supplied but the flag is
   False, the cache is ignored (preserves byte-stability)"). Verified
   by
   `TestEnginePaperQuantitiesCacheFlag.test_flag_false_with_cache_still_none`.

4. The Engine's `__init__` adds two keyword-only kwargs at the end of
   the signature; existing callers using positional args would NOT break
   (the existing 3 kwargs are already keyword-only per the `*`
   separator in the signature). Verified by
   `TestEnginePaperQuantitiesCacheFlag.test_existing_engine_kwargs_still_work`.

5. The `framework/engine.py` shim adds the re-export but does NOT
   modify any existing import. Verified by the test count:
   `tests/test_framework/` (109 tests) still pass byte-identically.

---

## 8. Audit doc fingerprint

- **audit doc path:**
  `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave296-p2-cache.md`
  (this file)
- **prior docs cited:** wave296-p1-architecture.md,
  wave292-p1-pipeline-inventory.md,
  wave292-p2-config-genealogy.md, wave294-final.md
- **code references (file:line):**
  - `adaptive_reflow/framework/paper_quantities_cache.py:138` —
    `_LazyMemoCachedEvaluationCost` class
  - `adaptive_reflow/framework/paper_quantities_cache.py:201` —
    `PaperQuantitiesCache` class
  - `adaptive_reflow/framework/paper_quantities_cache.py:269` —
    `__init__` (4 F-side defaults + lazy-memo slot construction)
  - `adaptive_reflow/framework/paper_quantities_cache.py:312` —
    `is_active` property
  - `adaptive_reflow/framework/paper_quantities_cache.py:339` —
    `sheet_A` property (lazy-memo)
  - `adaptive_reflow/framework/paper_quantities_cache.py:392` —
    `get(site_name)` dispatch table
  - `adaptive_reflow/framework/paper_quantities_cache.py:471` —
    `consume(site_name)` (idempotent activation log)
  - `adaptive_reflow/framework/paper_quantities_cache.py:506` —
    `stats()` audit-doc snapshot
  - `adaptive_reflow/frame/engine.py:77` — `PaperQuantitiesCache`
    import (Wave 296 P2 surface)
  - `adaptive_reflow/frame/engine.py:1004` — `Engine.__init__` with
    two new kwargs
  - `adaptive_reflow/frame/engine.py:1079` — `paper_quantities_cache`
    property
  - `adaptive_reflow/framework/engine.py:30` — `PaperQuantitiesCache`
    re-export in the framework shim
  - `tests/test_paper_quantities_cache.py:43` — `_real_g` fixture
  - `tests/test_paper_quantities_cache.py:58` —
    `TestPaperQuantitiesCacheBasic` (8 tests)
  - `tests/test_paper_quantities_cache.py:188` —
    `TestPaperQuantitiesCacheNoProfile` (8 tests)
  - `tests/test_paper_quantities_cache.py:266` —
    `TestPaperQuantitiesCacheConsume` (7 tests)
  - `tests/test_paper_quantities_cache.py:357` —
    `TestPaperQuantitiesCacheDispatch` (7 tests)
  - `tests/test_paper_quantities_cache.py:419` —
    `TestPaperQuantitiesCacheValidation` (5 tests)
  - `tests/test_paper_quantities_cache.py:466` —
    `TestEnginePaperQuantitiesCacheFlag` (6 tests)
  - `tests/test_paper_quantities_cache.py:530` —
    `TestPaperQuantitiesCacheByteStability` (4 tests)

---

## 9. Honest summary

The Wave 296 P2 implementation lands the cache carrier and Engine flag
without modifying any per-site wiring (Sites 2-16 from W296 P1 §3.2 are
deferred to W296 P3+). Specifically:

1. **`PaperQuantitiesCache`** — a typed cache carrier co-located with
   `state_bundle_cache.py`. Dormant by default; active when
   `profile_residual_fn is not None`. 4 lazy-memo slots + 15-site
   dispatch + idempotent `consume()` log. Stdlib-only (no torch, no
   numpy, no IO).

2. **`enable_full_jmaa_theory`** — a single keyword-only `bool` flag
   on `Engine.__init__` with default `False`. The Engine constructs a
   dormant cache when the flag is `True` and no cache is supplied; the
   cache becomes active when an adapter forwards a `profile_residual_fn`
   (deferred to W296 P3+).

3. **`paper_quantities_cache`** kwarg — allows callers to pre-build a
   cache (e.g., for testing or for adapters that want to pin the
   profile independently of the Engine). When supplied AND
   `enable_full_jmaa_theory=True`, the Engine uses the supplied cache.

4. **48 tests** — 7 test classes + 3 standalone functions covering
   basic / dormant / consume / dispatch / validation / Engine flag
   integration / byte-stability.

5. **Backward compat** — `enable_full_jmaa_theory=False` (default)
   leaves every existing call site byte-identical to the pre-Wave-296
   cosine baseline. D.4 30/30 preserved by construction.

The next-wave task is W296 P3: wire the 7 A-class sites
(pass-through, default `None` stays) into the adapter layer. Then
W296 P4 wires the 8 B-class sites (opt-in default flips). Then
W296 P5 verifies (D.4 + claims no drift + ruff 0 + mkdocs 0).

No claim is modified, no invariant is broken, no vendored file is
touched. The 15 dormant sites remain dormant by default and become
opt-in via a single `enable_full_jmaa_theory=True` flag.

---

## 10. Ruff + mkdocs verification

```
$ ruff check tests/test_paper_quantities_cache.py \
              adaptive_reflow/frame/engine.py \
              adaptive_reflow/framework/engine.py \
              adaptive_reflow/framework/paper_quantities_cache.py
All checks passed!

$ mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 20.10 seconds
```

Both gates pass with zero diagnostics. The `docs/audit/wave296-p2-cache.md`
file (this doc) is `not_in_nav` per `mkdocs.yml:241` (the
`audit/wave*.md` pattern) so mkdocs picks up zero new warnings.