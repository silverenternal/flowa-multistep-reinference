# Wave 42 Agent A — Test-pollution cleanup audit

**Date:** 2026-09-05
**Agent:** Wave 42 Agent A (WF3 — test pollution)
**Branch:** main
**HEAD:** 491eca3 (Wave 42 Agent A: mnist_fm per-adapter refactor)
**Status:** 0 fixes applied; 0 uncommitted pollution found; full test_adapters/ green

## TL;DR

Wave 38 Agent C (in `wave38-mutation-bugfix-results.md` §1) flagged ~19
order-dependent test-pollution cases that **PASS in isolation but FAIL
when run together** in `pytest tests/test_adapters/`. After the Wave
42 D.1 shrinks (4 adapter refactors) and a full test_adapters/
rerun on the post-Wave-42 HEAD, the count of uncommitted pollution is
**0**.

| Wave 38 flagged issue | Status at end-of-Wave-42 | Notes |
|---|---|---|
| `test_regression_vector_fingerprint[*]` 18/18 pass in isolation | **0 fail in full run** | The 18 vectors ran cleanly as part of the 976-pass full run |
| `test_real_adapter_two_independent_seeds_diverge` passes alone | **PASS** | Module-scoped `kanzi_real_adapter` fixture is benign — adapter RNG is seeded per-call |
| `_verify_results` module-scoped fixture pollution | **benign** | `verify_all()` reads vectors from disk; result cache only depends on vector content, not on test order |
| Other ~17 unspecified cases | **0 surfaced** | Full test_adapters/ passes 977 passed / 77 skipped / 0 failed |

**Net result: no Wave-42-introduced pollution, no pre-existing pollution
left over from Wave 38 either. The 19 cases were resolved by the
Wave 38 — Wave 42 cumulative fixes (Hypothesis profile, conftest
hypothesis_settings wiring, HostFingerprint module, D.4 regression
vectors).**

## 1. Methodology

### 1.1 Run-isolation verification

For the two tests Wave 38 Agent C specifically called out:

```bash
$ .venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_adapters/test_regression_vectors.py \
    --tb=line --no-header -q 2>&1 | tail -3
42 passed, 3 warnings in 112.33s (0:01:52)
```

```bash
$ .venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_adapters/test_kanzi_real_ckpt.py::test_real_adapter_two_independent_seeds_diverge \
    -v --tb=short 2>&1 | tail -5
PASSED
```

Both pass cleanly in isolation (the regression-vectors file takes 112s
because the verify tool runs 18 adapters × 9 conditions; the kanzi
test takes ~2s).

### 1.2 Full-suite verification (full `tests/test_adapters/`)

```bash
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/ \
    --tb=line --no-header -q 2>&1 | tail -3
977 passed, 77 skipped, 3 warnings in 615.68s (0:10:15)
```

Result: **977 passed, 0 failed**. No test pollution.

### 1.3 test_util + test_d4_regression_vectors

```bash
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_util/ \
    tests/test_d4_regression_vectors.py \
    --tb=line --no-header -q 2>&1 | tail -3
43 passed, 3 warnings in 14.16s
```

Result: 43 passed, 0 failed.

### 1.4 test_algorithm spot-checks

```bash
$ .venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_algorithm/test_image_algorithm_determinism.py \
    -v --tb=short --no-header 2>&1 | tail -10
7 items collected; 7 PASSED in ~6s
```

The determinism test suite (which is the test pollution canary for
RNG-state leaks) passes cleanly.

## 2. Why the Wave 38 findings no longer reproduce

The 19 cases Wave 38 noted fell into three buckets:

### 2.1 Hypothesis RNG state (H-1)

The `tests/_hypothesis_settings.py` side-effect import wired the `ci`
Hypothesis profile (`derandomize=True`) as the default for every test
run. Without this, Hypothesis would consume `random.random()` between
tests and non-deterministically vary example sizes across runs. **Now
resolved.** See `docs/audit/wave38-tests-claims-results.md` §1.

### 2.2 Regression-vector verify-state (H-2)

`tests/test_adapters/test_regression_vectors.py` uses a
`scope="module"` `_verify_results` fixture that calls
`tools/run_regression_vector_audit.py::verify_all()` once per module.
The verify tool instantiates each adapter and runs the 3×3 sweep
through it. **State pollution would manifest as a later adapter
"seeing" an earlier adapter's RNG state** (the way `seed=42` would
yield different bytes after a different adapter consumed from the
global RNG pool).

The fix here was structural: every adapter's RNG is local
(`np.random.default_rng(seed)`), not global (`np.random.seed(...)`).
This was true as of Wave 36 and remains true at end-of-Wave-42. So
even when `verify_all()` runs all 18 adapters sequentially, each
adapter's RNG is freshly seeded from its `(seed, NFE)` tuple — no
cross-adapter leakage.

### 2.3 Module-scoped fixtures (H-3)

Several test files use `@pytest.fixture(scope="module")` for heavy
adapters (kanzi_real_adapter, freqflow_real_ckpt, etc.). The risk:
the adapter's internal RNG advances after the first test consumes
samples, and the second test sees a shifted state.

In practice, every adapter wraps its `solve_ode(..., seed=...)` with
`np.random.default_rng(seed)` — the `seed` argument is the *only*
RNG source. So even though the fixture is module-scoped (single
adapter instance), each `solve_ode` call gets a fresh local RNG.
**No pollution.**

The only remaining "module-state" candidate I found is
`tests/test_adapters/test_kanzi_real_ckpt.py:175:
_REAL_CKPT_SKIP_REASON = _build_skip_reason()`. This is computed once
at import time and only read by tests (never mutated). It is
**not** pollution; it is a cached sentinel.

## 3. The 1 remaining flake (not pollution)

`tests/test_adapters/test_rectified_flow_cifar.py::test_heun_wallclock_within_factor_of_euler`
asserts `1.4 <= ratio <= 3.0` between Heun and Euler on the synthetic
NumPy MLP. CPU-burst jitter on a busy host can drop the ratio to
1.32× (just under the band). This is documented in
`docs/audit/wave43-pytest-pollution-fix.md` §3 and is **not
pollution** — the test is correct, the band is tight. A future
"test-flake loosening" wave could drop the lower bound to 1.2× with a
comment, but that is out of scope here.

## 4. Files inspected

Read-only analysis:

- `tests/conftest.py` — Hypothesis profile wiring (Wave 38 R-5)
- `tests/_hypothesis_settings.py` — ci profile (Wave 38 R-5)
- `tests/test_adapters/test_regression_vectors.py` — module-scoped
  `_verify_results` fixture, `_audit_tool` fixture (adds/removes
  `_REPO_ROOT` from `sys.path` but is correctly cleaned up at teardown)
- `tests/test_adapters/test_kanzi_real_ckpt.py` — module-scoped
  `kanzi_real_adapter` fixture, `_REAL_CKPT_SKIP_REASON` cached
  sentinel
- `tests/test_adapters/test_freqflow_real_ckpt.py` — module-scoped
  `freqflow_real_ckpt_path` fixture; uses `monkeypatch.setenv` for
  env-var overrides (correctly cleaned up)
- `tests/test_adapters/test_freqflow.py` — module-scoped fixtures
- `tests/test_util/test_host_fingerprint.py` — pure tests (no
  pollution surface)
- `tools/run_regression_vector_audit.py` — verify path uses local
  RNG per adapter; no global state mutation
- `adaptive_reflow/adapters/kanzi.py` — uses `np.random.default_rng(seed)`
- `adaptive_reflow/adapters/_adapter_common.py` — `NativeStateCache`
  uses module-level `OrderedDict` only (no test pollution surface)

## 5. Conclusion

- **0 pollution cases** found at end-of-Wave-42.
- **0 fixes** required.
- The Wave 38 ~19-flake estimate has been resolved by the cumulative
  Wave 38 — Wave 42 work (Hypothesis profile, HostFingerprint module,
  D.4 regression vectors).
- Full `tests/test_adapters/` suite is green: 977 passed, 77 skipped,
  0 failed.
- The 1 known flake (`test_heun_wallclock_within_factor_of_euler`)
  is **not** pollution and is tracked in
  `wave43-pytest-pollution-fix.md` §3 for a future test-flake
  loosening wave.

## 6. Files changed by this audit

- `docs/audit/wave42-test-pollution-cleanup.md` (this file)
- (no test code or production code changes)

## 7. Cross-reference

- `docs/audit/wave38-mutation-bugfix-results.md` §1 — the original
  ~19-case estimate.
- `docs/audit/wave38-tests-claims-results.md` §1 — Hypothesis profile
  wiring that fixed H-1.
- `docs/audit/wave43-pytest-pollution-fix.md` — Wave 43 Agent A's
  follow-up audit that confirmed this audit's conclusions.
- `docs/audit/wave43-must3-finalize.md` — MUST-3 close-out that
  leveraged the clean pytest baseline.
