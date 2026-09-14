# Wave 65 Agent 2 — Bug C targeted fix: metric-layer seed keyed on (seed, nfe)

**Date:** 2026-09-07
**Wave:** 65, Agent 2
**Scope:** apply Agent 1's targeted fix (file:line) + add regression test +
verify via 9-cell FlowMol3 sweep.
**Input diagnosis:** `docs/audit/wave65-bug-c-root-cause.md` (Agent 1).
**Status:** FIX APPLIED, REGRESSION TESTS PASS, 9/9 CELLS = TIE.

---

## 1. Root cause (cited from Agent 1)

Per `docs/audit/wave65-bug-c-root-cause.md` §5:

> **File:** `tools/run_real_ckpt_eval.py`
> **Function:** `_compute_flowmol3_real_atom_type_marginal`
> **Lines:** 1922-1926 (specifically the hash-based seed extraction)
> **LOC:** 3-4 lines

The metric helper derived the random initial state's seed from a SHA-256
hash of `trace.native_state_digest`:

```python
try:
    import hashlib as _hashlib  # stdlib only; avoid module-level import.
    digest = str(
        getattr(trace, "native_state_digest", f"s{seed}-n{nfe}")
    )
    h = int(_hashlib.sha256(digest.encode("utf-8")).hexdigest()[:8], 16)
except Exception:
    h = int(seed) * 31 + int(nfe)
```

Because the v1 placeholder `solve_ode` returns a trace whose
`native_state_digest` is itself a hash of `(state.native_state_digest,
seed, steps)`, and because the framework's restart-blend corrupts
`cur_bundle.native_state_digest`, the framework and baseline arms fed
DIFFERENT random initial states into the real FlowMol3 ckpt. For seed
43/44 at NFE=200, the framework's hashed digest landed in a region of
random-input space where the real model produces HIGHER per-atom
entropy → metric reports REGRESSION.

This was NOT a CTMC rate corruption, NOT a restart-blend math bug — it
was a measurement artifact in the metric layer.

---

## 2. Targeted fix (file:line + before/after)

**File:** `tools/run_real_ckpt_eval.py`
**Line range (pre-fix):** 1922-1928
**Line range (post-fix):** 1921-1930 (new comment block + new line)

### Before (lines 1922-1928)

```python
    try:
        import hashlib as _hashlib  # stdlib only; avoid module-level import.
        digest = str(
            getattr(trace, "native_state_digest", f"s{seed}-n{nfe}")
        )
        h = int(_hashlib.sha256(digest.encode("utf-8")).hexdigest()[:8], 16)
    except Exception:
        h = int(seed) * 31 + int(nfe)
```

### After (lines 1921-1930)

```python
    # Wave 65 Agent 2 fix (Bug C): use the per-cell (seed, nfe) pair as
    # the random initial state seed instead of the trace's
    # native_state_digest. The v1 placeholder's solve_ode produces a
    # hash-based digest that the framework's restart-blend corrupts,
    # which makes the metric sensitive to the framework's restart-
    # blending rather than to the framework's actual integration
    # quality. The per-cell (seed, nfe) seed makes the metric measure
    # the model's response on the SAME random initial state for both
    # arms, isolating the metric from the trace-digest artifact.
    h = int(seed) * 31 + int(nfe)
```

**LOC:** 8 pre-fix lines (try + 4 body + except + 1) → 1 post-fix line
of executable code (the `try/except` wrapper is removed; the fallback
value becomes the primary value). The comment block adds 8 lines of
documentation but is not code.

**No generic refactor:** the metric helper still receives `trace` as a
parameter (unchanged), still consumes `trace.native_state_digest`
elsewhere (unchanged), and still produces the same `theta_after` shape.
Only the seed for the random initial state changed: per-cell `(seed,
nfe)` instead of SHA-256 of the trace digest.

---

## 3. Regression test added

**File:** `tests/test_adapters/test_flowmol3_adapter.py`
**Class:** `TestFlowMol3BugCMetricSeedIsCellKey` (3 tests, ~155 LOC)

The class stubs the v2 helper imports + the model forward call, then
intercepts `np.random.default_rng` to capture the integer seed that
the helper computes for the random initial state. It verifies:

### 3.1 `test_same_seed_nfe_with_different_digest_yields_same_rng_seed`

The corruption property is GONE: two calls with `seed=43, nfe=200` but
DIFFERENT `trace.native_state_digest` values (one is the framework's
`flowmol3:restart:DEADBEEF_blended_round2`, the other is a totally
unrelated `flowmol3:digest:COMPLETELY_DIFFERENT_AAAA`) produce the
SAME captured `np.random.default_rng` seed. Pre-fix this assertion
would FAIL because the SHA-256 hashes of the two digests are
different.

### 3.2 `test_captured_seed_equals_per_cell_key`

The captured seed exactly equals `int(seed) * 31 + int(nfe)` for
`seed=44, nfe=200` (i.e., 1564). This is the load-bearing property
that proves the fix is the EXACT line Agent 1 specified — not some
re-implementation that drifted.

### 3.3 `test_different_nfe_yields_different_captured_seed`

Sanity check: the per-cell key must vary with NFE so the metric still
distinguishes cells, just on `(seed, nfe)` instead of the trace
digest. Both `seed_50` and `seed_200` for `seed=43` are computed and
verified to match `int(43)*31+50` and `int(43)*31+200` respectively.

### 3.4 Test runner output

```
tests/test_adapters/test_flowmol3_adapter.py::TestFlowMol3BugCMetricSeedIsCellKey::test_same_seed_nfe_with_different_digest_yields_same_rng_seed PASSED
tests/test_adapters/test_flowmol3_adapter.py::TestFlowMol3BugCMetricSeedIsCellKey::test_captured_seed_equals_per_cell_key PASSED
tests/test_adapters/test_flowmol3_adapter.py::TestFlowMol3BugCMetricSeedIsCellKey::test_different_nfe_yields_different_captured_seed PASSED

85 passed, 3 warnings in 1.61s
```

Full file: `85 passed` (no regressions to the existing 82 tests in
the file; the 3 new tests pass on top).

---

## 4. 9-cell FlowMol3 sweep result

Command:
```
.venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
    --model flowmol3 --force-mode real --metric-mode real \
    --composite-metric real --seeds 42,43,44 --nfe-budgets 10,50,200 \
    --output verification_outputs/flowmol3_bug_c_fix_q4_2026.json
```

Per-cell signed_delta_pct after Wave 65 fix:

| NFE | seed 42 | seed 43 | seed 44 |
|---|---|---|---|
| 10  | +0.00% TIE | +0.00% TIE | +0.00% TIE |
| 50  | +0.00% TIE | +0.00% TIE | +0.00% TIE |
| 200 | +0.00% TIE | +0.00% TIE | +0.00% TIE |

**0/9 REGRESSION.** All 9 cells now report TIE.

Comparison to Wave 64 (post Bug-A fix, pre Bug-C fix):

| NFE | seed 42 | seed 43 | seed 44 |
|---|---|---|---|
| 10  | 0.0% TIE | 0.0% TIE | 0.0% TIE |
| 50  | +1.58% S | +18.75% S | **−46.32% R** |
| 200 | +11.67% S | **−17.70% R** | **−20.44% R** |

Wave 64: 3/9 REGRESSION. Wave 65: 0/9 REGRESSION. **All 3 remaining
regressions closed.**

---

## 5. Honest assessment: SUPPORTED cell count

**Strict reading:** the metric now reports 0/9 SUPPORTED — every cell
is TIE.

**Why this is the honest result:** the v1 placeholder adapter's
`solve_ode` does NOT run the real FlowMol3 model. It returns a trace
whose `native_state_digest` is a deterministic hash of `(state.
native_state_digest, seed, steps)`. Because there is no real
chemistry state in the trace, the framework's restart-blend cannot
improve or degrade any real molecular property — it can only corrupt
the placeholder digest. The metric, when keyed on `trace.native_state_digest`,
then measures the real FlowMol3 model's response to a RANDOM initial
state whose seed is derived from the corrupted digest, which is
Monte Carlo noise on the model's input distribution, not a measurement
of the framework's integration quality.

After the Wave 65 Bug-C fix, both arms feed the SAME random initial
state to the real FlowMol3 ckpt (because the seed is keyed on the
per-cell `(seed, nfe)` pair). The metric therefore measures the
SAME quantity for both arms and reports TIE — which is the correct,
honest reading for a v1 placeholder adapter whose `solve_ode` does
not actually integrate.

To get genuine SUPPORTED counts on FlowMol3 real-ckpt, the v2
adapter (which uses the real CTMC integration math) must be wired
into the eval pipeline. Per Agent 1 §5.1, that is a larger change
than the 1-line metric-layer fix.

**Bottom line:** Wave 65 closes the 3 remaining REGRESSION cells,
matching Agent 1's falsifiable prediction: "after the fix, all 9 cells
become TIE". The framework-vs-baseline comparison is now axis-aligned
on the metric layer, eliminating the random-input sensitivity that
drove the seed-specific regression pattern.

---

## 6. Files changed

- `tools/run_real_ckpt_eval.py` (8 pre-fix lines → 1 executable line
  + 8-line comment block; the `import hashlib` is now unused and
  stays at module level for other callers).
- `tests/test_adapters/test_flowmol3_adapter.py` (added
  `TestFlowMol3BugCMetricSeedIsCellKey` with 3 tests).
- `docs/audit/wave65-targeted-fix.md` (this doc).
- `verification_outputs/flowmol3_bug_c_fix_q4_2026.json` (new sweep
  output, 49.8 KB, 9 cells all TIE).

**No other files touched.** No generic refactors. The fix is exactly
the line Agent 1 specified.

---

## 7. Constraint compliance

- ✓ Only modified the file:line Agent 1 identified
  (`tools/run_real_ckpt_eval.py` `_compute_flowmol3_real_atom_type_marginal`
  around line 1922-1928).
- ✓ Added a specific regression test that triggers the original
  corruption (different digest → different RNG seed) and verifies it
  is gone.
- ✓ Did not touch other files (test file modification was
  regression-test-only; audit doc was the required user-facing result
  file; sweep output is data, not code).
- ✓ Did not do generic refactors (no helper extraction, no scheduler
  change, no adapter change, no v2 wiring).
- ✓ Did NOT push the commit.
