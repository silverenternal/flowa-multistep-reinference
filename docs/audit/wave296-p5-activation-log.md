# Wave 296 P5 — End-to-end integration test (16/16 sites activation log)

**Date:** 2026-09-23
**Branch:** main
**Prior audit docs (anchors):**
- `docs/audit/wave296-p1-architecture.md` (P1 — design doc, the 7-A + 8-B split)
- `docs/audit/wave296-p2-cache.md` (P2 — cache + Engine flag)
- `docs/audit/wave296-p3-a-class-wired.md` (P3 — A-class wiring)
- `docs/audit/wave296-p4-b-class-wired.md` (P4 — B-class wiring)

**Purpose:** Lock down the Wave 296 P5 invariant — when
`Engine(enable_full_jmaa_theory=True)` is constructed with an ACTIVE
`PaperQuantitiesCache` (i.e. `profile_residual_fn is not None`) AND
the framework caller invokes BOTH the A-class framework hook
(`Engine.consume_a_class_sites`) AND the B-class framework hook
(`Engine.consume_b_class_sites`), the cache's activation log records
**all 16 JMAA application sites** from the Wave 292 P1 inventory.

When the flag is OFF (the default — byte-identical to the pre-Wave-296
cosine baseline), the cache is `None` and **zero sites** are
activated.

---

## 0. TL;DR

| Metric | Result |
|---|---|
| Test file | `tests/test_full_jmaa_integration.py` |
| Total tests | **38** |
| Tests passing | **38 / 38** |
| A-class sites consumed (with flag) | **8 / 8** |
| B-class sites consumed (with flag) | **8 / 8** |
| Total sites active (with flag) | **16 / 16** |
| Sites active without flag | **0** |
| D.4 30/30 byte-stability | **PRESERVED** (30/30 PASS) |
| ruff diagnostics | **0** on the new test file |
| Vendored touched | **NO** |

The new integration test file (`tests/test_full_jmaa_integration.py`)
covers six test classes that collectively verify:

1. End-to-end runner + engine + cache → 16 sites active
2. Default flag=False → 0 sites active (byte-stability)
3. Site count consistency (A-class + B-class = 16)
4. Per-site enumeration (every site individually reachable)
5. Activation-log idempotency
6. Cache stats observability contract

---

## 1. Site enumeration (16 entries)

The 16 JMAA application sites from the Wave 292 P1 inventory are
split into two classes (Wave 296 P3 + P4 wiring):

### 1.1 A-class sites (8 cache entries — Wave 296 P3)

| # | Cache name | File:line | Class / function | Activation log |
|---:|---|---|---|:---:|
| 1 | `solver_hint` | `algorithm/dynamics.py:132-145` (`_floor_dt`) | solver-level paper-quantity hint | ✓ |
| 2 | `dt_floor` | `algorithm/dynamics.py:132-145` (`_floor_dt`) | Dynamics dt floor | ✓ |
| 3 | `alpha_floor` | `algorithm/dynamics.py:742-748` (`BFNDynamics.step`) | Dynamics alpha floor | ✓ |
| 4 | `noise_bias` | `algorithm/perturbation/dynamic_noise_bias.py:172` (`Theorem1DynamicNoiseBias`) | Theorem1 noise bias | ✓ |
| 5 | `merge_floor` | `algorithm/merge/merge_operator.py:402-437` (`BoundedMergeOperator`) | Merge operator exterior_gap | ✓ |
| 6 | `policy_C` | `algorithm/policy_driver.py:505` (`AdaptivePolicyDriver`) | Policy driver per_cell_C | ✓ |
| 7 | `profile` | `adapters/profile_residual.py:189-202` (`profile_residual_fn`) | Adapter-level profile | ✓ |
| 8 | `fid` | `eval/fid_theorem_aligned.py:498` (`InceptionV3TheoremAlignedFIDEvaluator`) | FID theorem-aligned | ✓ |

### 1.2 B-class sites (8 cache entries — Wave 296 P4)

| # | Cache name | File:line | Class / function | Activation log |
|---:|---|---|---|:---:|
| 1 | `mfpqa` | `algorithm/integrator.py:530` (`MultiFidelityPaperQuantityStep`) | Integrator MFPQA | ✓ |
| 2 | `evidence` | `algorithm/scheduler/evidence_driven.py:248` (`EvidenceDrivenScheduler`) | Evidence-driven scheduler | ✓ |
| 3 | `lipschitz` | `eval/lipschitz_diagnostic.py:461` (`bounded_lipschitz_distance_2d`) | Lipschitz diagnostic | ✓ |
| 4 | `evaluator` | `eval/posterior_selection_evaluator.py:1-9` (`PosteriorSelectionEvaluator`) | Posterior selection evaluator | ✓ |
| 5 | `checker` | `theory/checkers.py:176` (`Theorem1StatementChecker`) | Theorem1StatementChecker | ✓ |
| 6 | `sheet_cell` | `eval/posterior_selection_evaluator.py:279-303` (sheet/cell heuristic) | Sheet-vs-cell heuristic | ✓ |
| 7 | `regime` | `algorithm/scheduler/regime_selector.py:786` (`default_e_rho_provider`) | Regime selector wrap | ✓ |
| 8 | `derivation` | `algorithm/_derivation.py:771` (`BLConvergenceEpsilonSchedule`) | Solver derivation companion | ✓ |

**Total: 16 distinct cache entries → 16 distinct activation-log entries.**

---

## 2. Activation log output (real run)

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
>>> engine.consume_a_class_sites()  # A-class hook
8
>>> engine.consume_b_class_sites()  # B-class hook
8
>>> cache.activated_sites
('solver_hint', 'dt_floor', 'alpha_floor', 'noise_bias',
 'merge_floor', 'policy_C', 'profile', 'fid',
 'mfpqa', 'evidence', 'lipschitz', 'evaluator',
 'checker', 'sheet_cell', 'regime', 'derivation')
>>> cache.stats()
{'is_active': 1, 'activated_count': 16,
 'sheet_A_computed': 1, 'packing_B_computed': 1,
 'cell_C_computed': 1, 'e_rho_computed': 1}
```

All 16 sites are reachable; all 4 paper quantities are computed
lazily on first access.

---

## 3. End-to-end runner integration

The runner's `run()` auto-invokes the B-class framework hook when the
flag is on AND the cache is active. The A-class framework hook is a
separate caller-side operation (per Wave 296 P3 §2.2).

```python
>>> from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
>>> from adaptive_reflow.algorithm.runner import (
...     ReInferenceConfig,
...     ReInferenceRunner,
... )
>>> adapter = TwoDimFMAdapter(weights_path=weights, target="two_moons")
>>> runner = ReInferenceRunner(adapter=adapter, engine=engine)
>>> config = ReInferenceConfig(
...     n_rounds=1, seed=42, channels=("xy",),
... )
>>> result = runner.run(config)
>>> # runner.run() auto-consumed the 8 B-class sites:
>>> len(cache.activated_sites)
8
>>> # Now invoke the A-class hook explicitly:
>>> engine.consume_a_class_sites()
8
>>> len(cache.activated_sites)
16
>>> set(cache.activated_sites) == set(ALL_16_SITES)
True
```

The activation log records **exactly 16** distinct sites after both
hooks are invoked.

---

## 4. Test file breakdown

### 4.1 File location

```
tests/test_full_jmaa_integration.py   # 678 lines, 38 tests
```

### 4.2 Test classes

| # | Class | Tests | What it verifies |
|---:|---|---:|---|
| 1 | `TestAllSitesActiveWithFlag` | 3 | End-to-end runner + engine + cache → 16 sites active |
| 2 | `TestOnlyZeroSitesActiveWithoutFlag` | 4 | Flag=False (default) → 0 sites active (byte-stability) |
| 3 | `TestSitesCountConsistent` | 10 | Site-count consistency (A-class + B-class = 16) |
| 4 | `TestPerSiteEnumeration` | 16 | Per-site enumeration (parametrized over all 16 sites) |
| 5 | `TestActivationIdempotency` | 2 | Repeated runs don't double-activate |
| 6 | `TestCacheStatsObservability` | 3 | Cache `stats()` snapshot contract |

Total: **38 tests** (3 + 4 + 10 + 16 + 2 + 3).

### 4.3 Test pass / fail breakdown

```
$ python -m pytest tests/test_full_jmaa_integration.py -v
======================== 38 passed, 8 warnings in 0.33s ========================
```

All 38 tests pass. The 8 warnings are pre-existing
`DeprecationWarning` outputs from the framework (Wave 34 default
scheduler deprecation + molecular contracts re-exports), unrelated
to the new test.

---

## 5. D.4 byte-stability preservation

The new test file does NOT modify the framework runtime path; it only
exercises the cache + activation log API. D.4 30/30 byte-stability
is preserved by construction:

```
$ python -m pytest tests/test_d4_regression_vectors.py --no-header -q
30 passed, 3 warnings in 1.21s
```

All 30 D.4 vectors still reproduce byte-identically on the current
host. The cosine-baseline path (the D.4 gate) is untouched.

---

## 6. ruff + mkdocs + vendored

| Check | Status |
|---|:---:|
| `ruff check tests/test_full_jmaa_integration.py` | **PASS** (0 diagnostics) |
| `ruff check adaptive_reflow/ tests/` | **PASS** (0 diagnostics) |
| `mkdocs build --strict` | **PASS** (this audit doc is `not_in_nav` per `mkdocs.yml:241`) |
| Vendored touched | **NO** (no edits under `vendored/`, `.venvs/`, `data/`) |

The audit doc is `not_in_nav` per the existing `audit/wave*.md`
pattern in `mkdocs.yml:241`, so mkdocs emits no new warnings.

---

## 7. CI integration

The new test file is wired into the canonical CPU watchdog
(`.github/workflows/cpu-tests.yml`) via a new step:

```yaml
- name: Run full JMAA theory integration test (Wave 296 P5)
  # Wave 296 P5 — end-to-end integration test that verifies ALL
  # 16 JMAA application sites are active when
  # ``Engine(enable_full_jmaa_theory=True`` plus an active
  # ``PaperQuantitiesCache``. Verifies the activation log
  # contract from ``docs/audit/wave296-p5-activation-log.md``:
  # 8 A-class + 8 B-class = 16 sites total. CPU only; no torch.
  run: PYTHONPATH=. python -m pytest tests/test_full_jmaa_integration.py --no-header -q
```

The step is added after the existing paper-grounded scheduler test
step and runs on every push to `main` and on every pull request.

---

## 8. Backward compatibility preserved

| Invariant | Status | Mechanism |
|---|:---:|---|
| D.4 30/30 byte-stability | **PRESERVED** | The new test does not modify the framework runtime; the cache's dormant path is byte-identical to pre-Wave-296 |
| CLAIMS no drift | **PRESERVED** | Cosine baseline R-cell FID achievement unchanged; the 15 dormant sites' activation is opt-in via `enable_full_jmaa_theory=True` |
| ruff 0 | **PRESERVED** | New test file is ruff-clean (0 diagnostics) |
| mkdocs 0 warnings | **PRESERVED** | Audit doc is `not_in_nav` per `mkdocs.yml:241` |
| Vendored NOT touched | **PRESERVED** | No edits under `vendored/`, `.venvs/`, `data/` |

---

## 9. Test pass-rate analysis

| Test class | Pass | Fail | Skip |
|---|---:|---:|---:|
| `TestAllSitesActiveWithFlag` | 3 | 0 | 0 |
| `TestOnlyZeroSitesActiveWithoutFlag` | 4 | 0 | 0 |
| `TestSitesCountConsistent` | 10 | 0 | 0 |
| `TestPerSiteEnumeration` | 16 | 0 | 0 |
| `TestActivationIdempotency` | 2 | 0 | 0 |
| `TestCacheStatsObservability` | 3 | 0 | 0 |
| **Total** | **38** | **0** | **0** |

Pass-rate: **100%**.

---

## 10. Audit doc fingerprint

- **audit doc path:**
  `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave296-p5-activation-log.md`
  (this file)
- **prior docs cited:** wave296-p1-architecture.md,
  wave296-p2-cache.md, wave296-p3-a-class-wired.md,
  wave296-p4-b-class-wired.md
- **code references (file:line):**
  - `tests/test_full_jmaa_integration.py:1-678` (new — 38 tests)
  - `adaptive_reflow/frame/engine.py:1087` (`_A_CLASS_SITE_NAMES` — 8 entries)
  - `adaptive_reflow/frame/engine.py:1113` (`_B_CLASS_SITE_NAMES` — 8 entries)
  - `adaptive_reflow/frame/engine.py:1124` (`consume_a_class_sites`)
  - `adaptive_reflow/frame/engine.py:1176` (`consume_b_class_sites`)
  - `adaptive_reflow/framework/paper_quantities_cache.py:494` (`activated_sites`)
  - `adaptive_reflow/framework/paper_quantities_cache.py:530` (`stats()`)
  - `.github/workflows/cpu-tests.yml:75-83` (new CI step)

---

## 11. Honest summary

Wave 296 P5 closes the full JMAA theory activation pipeline:

1. **`tests/test_full_jmaa_integration.py`** — 38 new tests covering
   the end-to-end integration path. Verifies that with
   `Engine(enable_full_jmaa_theory=True)` + active cache, all 16
   JMAA application sites are reachable through the framework hooks
   and recorded in the cache's activation log.

2. **`.github/workflows/cpu-tests.yml`** — new CI step that runs the
   integration test on every push to `main` and on every pull request.

3. **`docs/audit/wave296-p5-activation-log.md`** (this file) — the
   audit doc that records the site enumeration, test pass/fail
   breakdown, and backward-compat invariants.

The Wave 296 pipeline (P1 design + P2 cache + P3 A-class wiring + P4
B-class wiring + P5 integration test) now provides a complete,
auditable contract for the full JMAA theory activation:

- **Default path** (`Engine()`): zero sites activated; cosine baseline
  byte-identical to pre-Wave-296; D.4 30/30 PASS.
- **Opt-in path** (`Engine(enable_full_jmaa_theory=True)` + active
  cache + both framework hooks): all 16 sites activated; all 4 paper
  quantities computed lazily; activation log records the union of
  A-class and B-class sites.

No claim is modified, no invariant is broken, no vendored file is
touched, ruff 0, mkdocs 0 new warnings, D.4 30/30 PASS.

The Wave 296 task is closed.
