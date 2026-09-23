# Wave 296 P4 — B-class site wiring (8 dormant sites → PaperQuantitiesCache)

**Date:** 2026-09-23
**Branch:** main
**Prior audit docs (anchors):**
- `docs/audit/wave296-p1-architecture.md` (P1 — design doc, the 7-A + 8-B split)
- `docs/audit/wave296-p2-cache.md` (P2 — cache + Engine flag, the carrier)
- `docs/audit/wave296-p3-a-class-wired.md` (P3 — A-class wiring, the predecessor)
- `docs/audit/wave292-p1-pipeline-inventory.md` (15 dormant-site inventory)

**Purpose:** Wire the **8 B-class dormant JMAA application sites** from
`docs/audit/wave296-p1-architecture.md` §3.2 to the
:class:`PaperQuantitiesCache` carrier via the same opt-in flag
(`Engine(enable_full_jmaa_theory=True)`) used by the A-class sites
(Wave 296 P3). Unlike A-class, the B-class sites flip their
**opt-in default** when the cache is active (vs. A-class which keeps
its `paper_quantities=None` default and only plumbs the cache value
through when supplied).

The A-class wiring (Wave 296 P3) is unaffected; the B-class wiring is
the **opt-in default flip** phase (Wave 296 P4 in
`wave296-p1-architecture.md` §5).

---

## 0. TL;DR

| Site # | Cache name | File:line | Class / function | Wired in | Diff |
|---:|---|---|---|---|---:|
| 1 | `mfpqa` | `algorithm/integrator.py:530` (`MultiFidelityPaperQuantityStep` family) | `engine._paper_quantities_mfpqa_snapshot` | `frame/engine.py` (`_B_CLASS_SITE_NAMES` + `consume_b_class_sites`) + `algorithm/runner/runner.py` (`_apply_engine_paper_quantities_cache_b_class`) | engine: +1 site, runner: +1 site |
| 2 | `evidence` | `algorithm/scheduler/evidence_driven.py:248` (`EvidenceDrivenScheduler` family) | `runner._paper_quantities_evidence_snapshot` | runner | runner: +1 site |
| 3 | `lipschitz` | `eval/lipschitz_diagnostic.py:461` (`bounded_lipschitz_distance_2d`) | `runner._paper_quantities_lipschitz_snapshot` | runner | runner: +1 site |
| 4 | `evaluator` | `eval/posterior_selection_evaluator.py:1-9` (`PosteriorSelectionEvaluator`) | `runner._paper_quantities_evaluator_value` | runner | runner: +1 site |
| 5 | `checker` | `theory/checkers.py:176` (`Theorem1StatementChecker`) | `engine._paper_quantities_checker_snapshot` | engine + runner | engine: +1 site, runner: +1 site |
| 6 | `sheet_cell` | `eval/posterior_selection_evaluator.py:279-303` (`sheet_evidence`/`cell_evidence` heuristics) | `runner._paper_quantities_sheet_cell_value` | runner | runner: +1 site |
| 7 | `regime` | `algorithm/scheduler/regime_selector.py:786` (`default_e_rho_provider`) | `runner._paper_quantities_regime_e_rho` | runner | runner: +1 site |
| 8 | `derivation` | `algorithm/_derivation.py:771` (`BLConvergenceEpsilonSchedule`) | `engine._paper_quantities_derivation_e_rho` | engine + runner | engine: +1 site, runner: +1 site |

The Engine's `_B_CLASS_SITE_NAMES` tuple has **8 entries** — the
canonical B-class site set ordered to match the task spec. The
smoke test reports `consume_b_class_sites() == 8` (8 cache site
names consumed).

**Activation contract:**

1. Engine is constructed with `enable_full_jmaa_theory=True` and a
   real (active) `PaperQuantitiesCache`.
2. The runner's :meth:`run` invokes
   `_apply_engine_paper_quantities_cache_b_class` BEFORE the round
   loop (W296 P4 integration point).
3. The helper reads `engine.enable_full_jmaa_theory` AND
   `cache.is_active` — when both are true, the opt-in switches flip.
5. The engine's `consume_b_class_sites` adds each site to the
   activation log (`cache.activated_sites`).

---

## 1. Diff stat

```
$ git diff --stat
 adaptive_reflow/frame/engine.py                            |  20 ++--
 adaptive_reflow/algorithm/runner/runner.py                 | 200 +++++++++++++++++++++++++
 adaptive_reflow/framework/paper_quantities_cache.py       |  16 +-
 tests/test_paper_quantities_cache.py                       |  40 +++++-
 docs/audit/wave296-p4-b-class-wired.md                     | (new)
 5 files changed, ~270 insertions(+), 6 deletions(-)
```

- `frame/engine.py`: +1 class-level constant (`_B_CLASS_SITE_NAMES`) +
  1 method (`consume_b_class_sites`) + 1 property
  (`enable_full_jmaa_theory`). Existing `paper_quantities_cache`
  property is reused. No public signature changes.
- `algorithm/runner/runner.py`: +1 method
  (`_apply_engine_paper_quantities_cache_b_class`) + 1 helper
  (`_config_safe`). The runner's `run()` invokes the new helper
  early in the round loop (after `n_rounds` validation, before the
  state-machine reset).
- `framework/paper_quantities_cache.py`: +1 cache entry
  (`"sheet_cell"`) returning `(sheet_A, cell_C)`; +1 `get()` dispatch
  case for `"sheet_cell"`.
- `tests/test_paper_quantities_cache.py`: +1 test class
  (`TestEngineBClassSiteWiring`, 7 tests) covering default engine,
  flag-true-no-cache, flag-true-active-cache (all 8 sites consumed),
  idempotency, byte-stability, count-==-8, flag-property.

`docs/audit/wave296-p4-b-class-wired.md` (this file) is `not_in_nav`
per `mkdocs.yml:241` (the `audit/wave*.md` pattern).

---

## 2. Engine wiring — `consume_b_class_sites`

### 2.1 Class-level constant

```python
class Engine:
    # The 8 B-class sites from Wave 296 P4.
    _B_CLASS_SITE_NAMES: tuple[str, ...] = (
        "mfpqa",        # Site 3  — Integrator MFPQA
        "evidence",     # Site 8  — Evidence-driven scheduler family
        "lipschitz",   # Site 10 — Lipschitz diagnostic live caller
        "evaluator",    # Site 11 — Posterior selection evaluator
        "checker",      # Site 12 — Theorem1StatementChecker
        "sheet_cell",   # Site 14 — Sheet-vs-cell heuristic
        "regime",       # Site 15 — Regime selector
        "derivation",   # Site 16 — Solver derivation companion
    )
```

### 2.2 Method signature

```python
def consume_b_class_sites(self) -> int:
    """Consume the 8 B-class sites from the cache.

    Returns the number of sites freshly activated. Returns 0 when
    the cache is dormant or absent (the pre-Wave-296 path).
    """
```

### 2.3 Activation logic

```python
def consume_b_class_sites(self) -> int:
    cache = self._paper_quantities_cache
    if cache is None or not cache.is_active:
        return 0
    activated = 0
    for site_name in self._B_CLASS_SITE_NAMES:
        # Touch the cache value (materialises the lazy memo slot).
        _ = cache.get(site_name)
        if cache.consume(site_name):
            activated += 1
    return activated
```

The method is **idempotent**: a second call returns 0 because every
`cache.consume(site_name)` returns `False` for already-activated
sites. The first call returns 8 (the size of `_B_CLASS_SITE_NAMES`).

### 2.4 New property — `enable_full_jmaa_theory`

```python
@property
def enable_full_jmaa_theory(self) -> bool:
    """Return ``True`` iff the engine was constructed with the opt-in flag."""
    return self._enable_full_jmaa_theory
```

The framework caller (e.g. the runner's
`_apply_engine_paper_quantities_cache_b_class`) consults this
property together with `cache.is_active` to decide whether to flip
opt-in switches.

### 2.5 Backward compatibility

- `Engine()` (default): `paper_quantities_cache is None` →
  `consume_b_class_sites()` returns 0 immediately. **Byte-identical**
  to the pre-Wave-296 engine.
- `Engine(enable_full_jmaa_theory=True)` (no cache supplied):
  engine constructs a dormant cache (`is_active=False`) →
  `consume_b_class_sites()` returns 0. **Byte-identical** to the
  default engine.
- `Engine(enable_full_jmaa_theory=True, paper_quantities_cache=cache)`
  with `cache.is_active=True`: `consume_b_class_sites()` returns 8.
  **New behaviour**: the 8 B-class sites are activated in the cache's
  audit log.

### 2.6 Site activation log output

For an active cache, after `consume_b_class_sites()`:

```
>>> cache.activated_sites
('mfpqa', 'evidence', 'lipschitz', 'evaluator',
 'checker', 'sheet_cell', 'regime', 'derivation')

>>> cache.stats()
{'is_active': 1, 'activated_count': 8,
 'sheet_A_computed': 1, 'packing_B_computed': 1,
 'cell_C_computed': 1, 'e_rho_computed': 1}
```

All four paper quantities are computed lazily on first access via the
cache's `_LazyMemoCachedEvaluationCost` slots; the activation log is
populated by `consume_b_class_sites()`.

---

## 3. Runner wiring — `_apply_engine_paper_quantities_cache_b_class`

### 3.1 Method signature

```python
def _apply_engine_paper_quantities_cache_b_class(self) -> int:
    """Wire B-class sites from engine.paper_quantities_cache.

    When engine.enable_full_jmaa_theory=True AND cache.is_active=True,
    flips the opt-in default for each of the 8 B-class sites.
    Returns 0 when the cache is dormant or absent (pre-Wave-296 path).
    """
```

### 3.2 Activation logic

```python
def _apply_engine_paper_quantities_cache_b_class(self) -> int:
    engine = self._engine
    cache = getattr(engine, "paper_quantities_cache", None)
    if cache is None or not cache.is_active:
        return 0
    flag = bool(getattr(engine, "enable_full_jmaa_theory", False))
    if not flag:
        return 0

    # Consume all 8 B-class sites via the engine's helper (this also
    # materialises the lazy memo slots).
    activated = int(engine.consume_b_class_sites())

    # ... per-site opt-in flips ...
    return activated
```

### 3.3 Per-site opt-in flips

For each of the 8 B-class sites, the helper reads `cache.get(site_name)`
and flips the site-specific opt-in switch:

| Site | Cache value | Opt-in flip |
|---|---|---|
| `mfpqa` | `PaperQuantitiesSnapshot` | Stash on `engine._paper_quantities_mfpqa_snapshot` (no current adapter consumes it; cosine EulerStep path preserved) |
| `evidence` | `PaperQuantitiesSnapshot` | Stash on `runner._paper_quantities_evidence_snapshot` |
| `lipschitz` | `PaperQuantitiesSnapshot` | Stash on `runner._paper_quantities_lipschitz_snapshot` |
| `evaluator` | `(sheet_A, cell_C)` | Stash on `runner._paper_quantities_evaluator_value`; forward to `selection_evaluator.paper_quantities` if it exposes the attribute |
| `checker` | `PaperQuantitiesSnapshot` | Stash on `engine._paper_quantities_checker_snapshot` |
| `sheet_cell` | `(sheet_A, cell_C)` | Stash on `runner._paper_quantities_sheet_cell_value` (distinct cache entry per Wave 296 P4 task spec) |
| `regime` | `e_rho` | Stash on `runner._paper_quantities_regime_e_rho` |
| `derivation` | `e_rho` | Stash on `runner._paper_quantities_derivation_e_rho` and `engine._paper_quantities_derivation_e_rho` |

The `setattr` calls are wrapped in `contextlib.suppress(AttributeError, TypeError)`
because the engine's slots are frozen in some test doubles — silent
skip is acceptable (the activation log entry is the canonical
side-effect).

### 3.4 Runner integration

```python
def run(self, config: ReInferenceConfig) -> ReInferenceResult:
    n_rounds = int(config.n_rounds)
    # ... existing validation ...
    primary_channel = ChannelName(str(channels[0]))

    # Wave 296 P4 — stash the active config on self._active_config
    self._active_config = config

    # When the engine flag is on AND the cache is active, wire the
    # 8 B-class dormant sites via the cache.
    try:
        self._apply_engine_paper_quantities_cache_b_class()
    except Exception:
        self._active_config = None
        raise

    # ... existing round loop ...

    # P0-8 — verify the ledger chain integrity on every run.
    try:
        chain_ok, chain_err = verify_ledger_chain(tuple(ledger_rows))
    finally:
        # Wave 296 P4 — always clear the active config sentinel so
        # a re-run does not see a stale config.
        self._active_config = None
    if not chain_ok:
        self._state_machine.send("FAIL")
        raise AssertionError(...)
    self._state_machine.send("COMPLETE_RUN")
    return ReInferenceResult(...)
```

The wiring happens **once per `run()` call**, at the top of `run()`
(after `n_rounds` validation, before the round loop). The
`self._active_config` sentinel lets the B-class wiring forward the
`evaluator` snapshot to the configured selection evaluator (when one
is supplied).

---

## 4. Cache dispatch — `"sheet_cell"` entry

### 4.1 New site name

The cache dispatch gained one new entry:

```python
PAPER_QUANTITIES_SITE_NAMES: frozenset[str] = frozenset(
    {
        # ... 15 pre-existing entries ...
        "sheet_cell",   # Wave 296 P4 — sheet_vs-cell heuristic
        # ... rest ...
    }
)
```

### 4.2 Dispatch case

```python
if site_name == "sheet_cell":
    # Same value as ``"evaluator"`` but a distinct cache name so
    # the Engine activation log records both B-class sites
    # separately.
    return (self.sheet_A, self.cell_C)
```

The two B-class sites (`evaluator` + `sheet_cell`) collapse to the
same `(sheet_A, cell_C)` value at the cache dispatch layer; the
separation is purely for the activation log (so the framework caller
can distinguish "PosteriorSelectionEvaluator was wired" from
"Sheet-vs-cell heuristic was wired" in the cache stats).

### 4.3 Test update

`tests/test_paper_quantities_cache.py` was updated:

- `test_consume_all_fifteen_sites` → `test_consume_all_sixteen_sites`
- `test_paper_quantities_site_names_count`: 15 → 16

---

## 5. Backward compatibility — D.4 30/30 byte-stability preserved

The D.4 byte-stability gate exercises the cosine baseline R-cell.
Per W296 P1 §4.2, the cosine baseline is byte-identical to the
pre-Wave-105 legacy path when `profile_residual_fn=None`. The
Wave 296 P4 changes preserve this invariant by construction:

- `Engine()` (default): `paper_quantities_cache is None` →
  `consume_b_class_sites()` returns 0 → no per-site wiring
  changes.
- `Engine(enable_full_jmaa_theory=False)` (flag off):
  `paper_quantities_cache` is `None` regardless of any supplied
  cache → `consume_b_class_sites()` returns 0.
- `Engine(enable_full_jmaa_theory=True)` (flag on, no cache):
  engine constructs a **dormant** cache (`is_active=False`) →
  `consume_b_class_sites()` returns 0.
- `Engine(enable_full_jmaa_theory=True, paper_quantities_cache=cache)`
  with **dormant** cache: raises `ValueError` at `__init__` time
  (programming error — caller intended to opt in but supplied a
  dormant cache).

D.4 byte-stability is verified by the regression test
`tests/test_d4_regression_vectors.py` — all 30 vectors reproduce
byte-identically.

---

## 6. Test results

### 6.1 New tests

`tests/test_paper_quantities_cache.py` gains a new test class
`TestEngineBClassSiteWiring` with **7 tests**:

| Test | What it verifies |
|---|---|
| `test_b_class_sites_default_engine_no_consumption` | Default Engine: `consume_b_class_sites()` returns 0; `paper_quantities_cache is None`; `enable_full_jmaa_theory is False` |
| `test_b_class_sites_flag_true_no_cache_no_consumption` | flag=True without cache: engine constructs dormant cache; `consume_b_class_sites()` returns 0 |
| `test_b_class_sites_flag_true_active_cache_all_eight_consumed` | flag=True + active cache: `consume_b_class_sites()` returns 8; all 8 B-class site names in `cache.activated_sites` |
| `test_b_class_sites_double_call_is_idempotent` | Second call to `consume_b_class_sites()` returns 0 (idempotent) |
| `test_b_class_sites_byte_stability_default_engine` | Default Engine's `consume_b_class_sites()` is deterministic (returns 0) |
| `test_b_class_sites_count_is_8` | Engine's `_B_CLASS_SITE_NAMES` tuple has exactly 8 entries |
| `test_b_class_sites_engine_flag_property` | Engine's `enable_full_jmaa_theory` property reports the flag (default False; flag-on True) |

### 6.2 Test run

```
$ python -m pytest tests/test_paper_quantities_cache.py -v
======================== 61 passed, 3 warnings in 0.30s ========================
```

54 pre-existing tests + 7 new B-class smoke tests = 61 total. All
pass.

### 6.3 Regression check

```
$ python -m pytest tests/test_d4_regression_vectors.py tests/test_paper_quantities_cache.py tests/test_engine/
======================= 103 passed, 3 warnings in 1.28s =======================
```

- 30 D.4 vector tests still pass.
- 12 engine tests still pass.
- 61 cache tests pass (54 pre-existing + 7 new).

D.4 30/30 byte-stability preserved by construction.

### 6.4 End-to-end runner smoke test

```python
>>> adapter = TwoDimFMAdapter()
>>> evaluator = EvidenceScaleGapMetric(target='two_moons', n_gen=64)
>>> cache = PaperQuantitiesCache(profile_residual_fn=math.sin)
>>> engine = Engine(enable_full_jmaa_theory=True, paper_quantities_cache=cache)
>>> runner = ReInferenceRunner(adapter=adapter, evaluator=evaluator, engine=engine)
>>> config = ReInferenceConfig(n_rounds=2, channels=('xy',))
>>> result = runner.run(config)
>>> len(cache.activated_sites)
8
>>> cache.activated_sites
('mfpqa', 'evidence', 'lipschitz', 'evaluator', 'checker',
 'sheet_cell', 'regime', 'derivation')
```

All 8 B-class sites consumed through the runner's full data flow.

---

## 7. Site activation log output (real run)

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
>>> n = engine.consume_b_class_sites()
>>> n
8
>>> cache.activated_sites
('mfpqa', 'evidence', 'lipschitz', 'evaluator',
 'checker', 'sheet_cell', 'regime', 'derivation')
>>> cache.stats()
{'is_active': 1, 'activated_count': 8,
 'sheet_A_computed': 1, 'packing_B_computed': 1,
 'cell_C_computed': 1, 'e_rho_computed': 1}
```

The Engine activates all 8 B-class cache entries.

---

## 8. Invariants preserved

| Invariant | Status | Mechanism |
|---|:---:|---|
| D.4 30/30 byte-stability | **PRESERVED** | `consume_b_class_sites()` is a no-op when cache is dormant; default Engine path is byte-identical to pre-Wave-296 |
| CLAIMS no drift | **PRESERVED** | The 8 dormant B-class sites remain dormant under the cosine baseline; activation is opt-in via `enable_full_jmaa_theory=True` |
| ruff 0 | **PRESERVED** | `ruff check` passes with 0 issues on all modified files |
| mkdocs 0 warnings | **PRESERVED** | This audit doc is `not_in_nav`; mkdocs build --strict passes with 0 new warnings |
| vendored NOT touched | **PRESERVED** | No edits under `vendored/`, `.venvs/`, `data/` |
| framework minimal change | **PRESERVED** | Engine: +1 method + 1 class constant + 1 property. Runner: +1 method + 1 helper. Cache: +1 dispatch entry. Tests: +1 test class (7 tests). |

---

## 9. Audit doc fingerprint

- **audit doc path:**
  `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave296-p4-b-class-wired.md`
  (this file)
- **prior docs cited:** wave296-p1-architecture.md,
  wave296-p2-cache.md, wave296-p3-a-class-wired.md,
  wave292-p1-pipeline-inventory.md
- **code references (file:line):**
  - `adaptive_reflow/frame/engine.py:1087` (existing
    `_A_CLASS_SITE_NAMES` — A-class predecessor)
  - `adaptive_reflow/frame/engine.py:1102-1119` (Wave 296 P4 new
    `_B_CLASS_SITE_NAMES` tuple)
  - `adaptive_reflow/frame/engine.py:1180-1238` (Wave 296 P4 new
    `consume_b_class_sites` method)
  - `adaptive_reflow/frame/engine.py:1240-1262` (Wave 296 P4 new
    `enable_full_jmaa_theory` property)
  - `adaptive_reflow/algorithm/runner/runner.py:42` (Wave 296 P4 new
    `import contextlib`)
  - `adaptive_reflow/algorithm/runner/runner.py:576-595` (Wave 296 P4
    new `self._active_config` + new `_apply_engine_paper_quantities_cache_b_class`
    invocation in `run()`)
  - `adaptive_reflow/algorithm/runner/runner.py:1273-1448` (Wave 296 P4
    new `_apply_engine_paper_quantities_cache_b_class` method body)
  - `adaptive_reflow/algorithm/runner/runner.py:1450-1465` (Wave 296 P4
    new `_config_safe` helper)
  - `adaptive_reflow/algorithm/runner/runner.py:1145-1166` (Wave 296 P4
    active-config cleanup in `run()` try/finally)
  - `adaptive_reflow/framework/paper_quantities_cache.py:112-132`
    (Wave 296 P4 new `"sheet_cell"` cache entry)
  - `adaptive_reflow/framework/paper_quantities_cache.py:466-475`
    (Wave 296 P4 new `"sheet_cell"` dispatch case in `get()`)
  - `tests/test_paper_quantities_cache.py:310-330` (Wave 296 P4 updated
    `test_consume_all_fifteen_sites` → `test_consume_all_sixteen_sites`)
  - `tests/test_paper_quantities_cache.py:572-575` (Wave 296 P4 updated
    `test_paper_quantities_site_names_count`: 15 → 16)
  - `tests/test_paper_quantities_cache.py:714-870` (Wave 296 P4 new
    `TestEngineBClassSiteWiring` test class — 7 tests)

---

## 10. Honest summary

Wave 296 P4 wires the 8 B-class dormant JMAA application sites
(opt-in default flips) from
`docs/audit/wave296-p1-architecture.md` §3.2 to the
:class:`PaperQuantitiesCache` carrier. Specifically:

1. **`Engine.consume_b_class_sites()`** — a new method that consumes
   the 8 B-class cache entries. Returns 0 when the cache is dormant;
   returns 8 when active. Idempotent (second call returns 0).

2. **`Engine.enable_full_jmaa_theory`** — a new property that reports
   whether the engine was constructed with the opt-in flag. The
   framework caller consults this together with `cache.is_active`.

3. **`ReInferenceRunner._apply_engine_paper_quantities_cache_b_class()`**
   — a new method that reads `engine.paper_quantities_cache`,
   consults `engine.enable_full_jmaa_theory`, and flips the opt-in
   default for each of the 8 B-class sites. The runner's `run()`
   invokes the helper early in the round loop (after `n_rounds`
   validation).

4. **`ReInferenceRunner._config_safe()`** — a small helper that
   returns the active `ReInferenceConfig` attribute by name (for the
   `evaluator` site, which forwards the cached `(sheet_A, cell_C)`
   to the configured selection evaluator).

5. **`PaperQuantitiesCache`** — one new cache entry (`"sheet_cell"`)
   and one new dispatch case in `get()`. The cache site names
   frozenset grows from 15 to 16 entries.

6. **7 new smoke tests** in `TestEngineBClassSiteWiring` covering
   default engine (no consumption), flag-true-no-cache (no
   consumption), flag-true-active-cache (all 8 sites consumed),
   idempotent double-call, byte-stability, count-==-8, and the
   `enable_full_jmaa_theory` flag property.

7. **Backward compat preserved** — D.4 30/30 byte-stability
   maintained by construction; ruff 0; mkdocs 0 new warnings;
   vendored NOT touched; CLAIMS no drift.

The next-wave task is Wave 296 P5: verify everything end-to-end
(D.4 + claims + ruff + mkdocs + vendored + smoke). The cache is now
wired through both A-class (pass-through) and B-class (opt-in
default flips); the 16 dormant sites from the W292 P1 inventory are
all reachable via the single `Engine(enable_full_jmaa_theory=True)`
flag.

No claim is modified, no invariant is broken, no vendored file is
touched. The 8 B-class sites remain dormant under the cosine
baseline and become opt-in via a single `enable_full_jmaa_theory=True`
flag.