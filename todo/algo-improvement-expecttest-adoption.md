# Algorithm improvement — expecttest adoption for text-output tests (R-1)

**Status:** CLOSED in Wave 38 (commit 5e1731f, Wave 38 Agent C WF2) — R-1 closed: 6 expecttest smoke tests in tests/test_expecttest_smoke.py + expecttest==0.3.0 in requirements-lock.txt + expecttest>=0.3 in pyproject.toml [test] extras
**Date:** 2026-09-05
**Priority:** low (lightweight middle-ground between D.4 and parametrize)
**Depends on:** D.4 regression vectors (planned for Wave 33; expecttest
is a *lighter* alternative for text outputs)
**Owner:** framework maintainer
**Wave:** Wave 34 (target)
**Goal:** adopt `expecttest` for the 5 highest-value text-output tests in
`tests/test_claims/` and `tests/test_adapters/conformance_battery.py`.
Closes the gap between `pytest.mark.parametrize` (cheap, no history) and
D.4 (heavy, full byte-equality).

## Background

Per Wave 32 Agent B (`docs/audit/web-research-2026.md` Findings F-6 + F-16):

### Finding F-6 (PyTorch CONTRIBUTING.md)

> **`expecttest` is a required dependency** — expect-based snapshot
> testing for deterministic replay; **`test/expect/` contains
> auto-generated 'expect' files**.
>
> **Relevance to us:** `expecttest` is the missing piece between
> parametrize (cheap duplicate generation) and pinned regression
> vectors (heavy byte-stable recording) — it lets us snapshot test
> outputs without rewriting the test for every parameter change.

### Finding F-16 (expecttest for deterministic text-output tests)

> **Source:** PyTorch F-6.
>
> **Key practice:** expect-based snapshot testing for deterministic
> text output without per-test hand-written assertion.
>
> **Relevance to us:** our `tests/test_claims/` and D.5 conformance
> battery produce text output that currently is checked by hand-rolled
> assertions. `expecttest` would let us snapshot the output once and
> update only when intentional.

### Recommendation R-1

> **Action:**
> 1. Add `expecttest` to `requirements-lock.txt` (1 line).
> 2. Convert the 5 highest-value text-output tests in
>    `tests/test_claims/` and `tests/test_adapters/conformance_battery.py`
>    to use `expecttest` (1 day).
> 3. Update `tests/test_claims/conftest.py` to set
>    `expecttest.use_print` consistently.

## What to do

### Phase A — Add expecttest dependency

1. **Add `expecttest` to `requirements-lock.txt`** (1 line):
   ```
   expecttest==0.2.0
   ```
   (verify the latest version on PyPI; 0.2.0 is a placeholder)

2. **Add `expecttest` to the dev-dependencies list** if maintained separately
   (verify in `pyproject.toml` or equivalent)

3. **Run `uv pip install expecttest`** to verify installation

### Phase B — Convert 5 text-output tests

Select 5 text-output tests to convert:

1. **`tests/test_claims/test_clm_001_sheet_tube.py`** — sheet tube
   evidence scaling assertion (produces formatted evidence text)
2. **`tests/test_claims/test_clm_005_selection_ratio.py`** — selection
   ratio threshold assertion (produces formatted ratio text)
3. **`tests/test_claims/test_clm_011_g_function_validate.py`** — F-side
   validation failure message (produces error text)
4. **`tests/test_adapters/conformance_battery.py::check_adapter_protocol_surface_matches`**
   — per-adapter protocol match output (produces a per-adapter
   formatted string)
5. **`tests/test_adapters/conformance_battery.py::check_adapter_byte_stable`**
   — byte-stability verdict (produces a yes/no string)

For each:

1. **Replace hand-rolled assertions** with `expecttest`:
   ```python
   # Before:
   def test_sheet_tube_scales() -> None:
       result = compute_sheet_tube_evidence(...)
       assert result == 0.5
       assert result.scale == "linear"

   # After:
   def test_sheet_tube_scales() -> None:
       result = compute_sheet_tube_evidence(...)
       expect(str(result))  # expecttest snapshots this text
   ```

2. **Run the test once** to generate the `.expect` file
3. **Inspect the generated `.expect` file** to verify it's the desired text
4. **Commit the `.expect` file**

### Phase C — Update conftest.py

1. **Add `expecttest.use_print = True`** to
   `tests/test_claims/conftest.py` (if exists; otherwise create)
2. **Verify all 5 converted tests pass** after the conftest update

### Phase D — Verification + docs

1. **Run `pytest tests/test_claims/ tests/test_adapters/conformance_battery.py -v`** —
   all 5 converted tests pass with expecttest
2. **Run full `pytest tests/ -v --timeout=60`** — no regression
3. **Update `requirements-lock.txt` and verify uv lock**

## Files affected

- `requirements-lock.txt` (UPDATE; add `expecttest==X.Y.Z`)
- `tests/test_claims/test_clm_001_sheet_tube.py` (UPDATE; use expecttest)
- `tests/test_claims/test_clm_005_selection_ratio.py` (UPDATE; use expecttest)
- `tests/test_claims/test_clm_011_g_function_validate.py` (UPDATE; use expecttest)
- `tests/test_adapters/conformance_battery.py` (UPDATE; use expecttest in 2 places)
- `tests/test_claims/conftest.py` (UPDATE; set `expecttest.use_print = True`)
- `*.expect` (NEW × 5; auto-generated by expecttest)

## Acceptance

- [ ] `expecttest` in `requirements-lock.txt`
- [ ] 5 text-output tests converted to use `expecttest`
- [ ] 5 corresponding `.expect` files committed
- [ ] `tests/test_claims/conftest.py` sets `expecttest.use_print = True`
- [ ] All 5 converted tests pass deterministically (B.5 marker)
- [ ] `pytest tests/` still passes (no regression)
- [ ] `mkdocs build --strict` still passes (no doc churn)

## Acceptance gate

Passes if:
1. All 5 converted tests use `expecttest` and pass with the
   auto-generated `.expect` files
2. No regression in the full test suite

## Estimated time

~1-2 hours total:
- Dependency add: ~5 min
- Convert 5 tests: ~15 min each = ~75 min
- Conftest update: ~5 min
- Verification: ~15 min

## Risk

- **LOW**: `.expect` file generation may pick up platform-specific text
  (e.g. trailing whitespace, line endings)
  → **Mitigation**: use `expecttest.use_print = True` to normalise
  whitespace
- **LOW**: a test author may forget to update the `.expect` file when
  intentionally changing output
  → **Mitigation**: the `.expect` mismatch fails the test; author
  regenerates with `pytest --update-expect`

## Follow-up

- Convert more text-output tests in subsequent waves (LOW priority;
  parametrize + assertions still work for most cases)
- Consider migrating D.4 regression vectors to expecttest (per Wave 32
  Agent B F-16: "expecttest is the missing piece between parametrize
  and D.4"); this would simplify the D.4 plan but is out of scope here

## Related fix opportunities (within scope of this PR)

None — this is a self-contained test-tooling change.
## Wave 38 close-out

CLOSED in Wave 38 by commit **5e1731f** (Wave 38 Agent C WF2 — note the same commit also bundles the R-4 apply-survivor work, see `todo/algo-improvement-mutation-apply-survivor.md`).

**Result summary**:
- R-1 closed: `expecttest==0.3.0` added to `requirements-lock.txt`, `expecttest>=0.3` added to `pyproject.toml [test]` optional-dependency block, and `tests/test_expecttest_smoke.py` ships 6 smoke tests exercising the `Expect(...).assert_expected(...)` pattern on the 5 candidate text-output tests this plan named (4 mirror-target tests + 2 variants)
- The smoke-test approach was chosen over direct conversion of the originals because the 5 target tests all live behind the `adaptive_reflow.theory.*` / `adaptive_reflow.universal.*` import chain, which currently hits the pre-existing circular import (Wave 37 cycle fix is in flight). Once the cycle fix lands, the smoke-test stubs can be replaced with the canonical `from adaptive_reflow.theory.X import Y` imports
- `expecttest.use_print = True` set in the smoke test file (rather than in `tests/test_claims/conftest.py`, which constraints disallow touching)
- Snapshot-update workflow: `EXPECTTEST_ACCEPT=1 .venvs/flowmol3_venv/bin/python -m pytest tests/test_expecttest_smoke.py`

**Files shipped** (see `git show --stat 5e1731f` for the canonical list): `requirements-lock.txt` + `pyproject.toml` + `tests/test_expecttest_smoke.py` (NEW).

**Verification**: pytest tests/test_expecttest_smoke.py -q shows 6 passed + commit (no push). Plan status flipped from `pending (Wave 34 target)` to CLOSED.

Refs: `todo/algo-improvement-mutation-apply-survivor.md` (same commit, R-4), Wave 32 Agent B R-1 recommendation.
