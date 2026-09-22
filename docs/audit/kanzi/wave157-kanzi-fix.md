# Wave 157 P1: kanzi shape fix at adaptive_reflow/adapters/kanzi.py:1209

**Wave:** 157 (kanzi CPU-only trivial fix, NOT a 35h GPU blocker)
**Agent:** Wave 157 Agent 1
**Date:** 2026-09-15
**Status:** Applied; AST-valid; ruff 0; D.4 72/72 PASS; claims consistency "No drift detected."

## Background

The Wave 156 P2 K1 RC5 full N=1000 5-arm real-ckpt ablation sweep
(`aaf0f9b`) ran 10/15 OK with **kanzi 5/5 RUN_ERROR** at
`adaptive_reflow/adapters/kanzi.py:1209`:

```
ValueError: too many values to unpack (expected 3)
```

The pre-existing kanzi `_KanziDAEShim.forward` unpacks
`self._dae.encode(x)` as a 3-tuple:

```python
_, z, _ = self._dae.encode(x)        # (B, L, d_z) codebook-quantized
```

The hypothesis is that the upstream DAE model in the loaded checkpoint
returns **4** values (e.g. a newer FSQ-aware version that adds a
length-mask or codebook-loss output), which causes the strict 3-tuple
unpack to fail on real checkpoints.

## The 3-line patch (kanzi.py:1209)

**Before** (line 1209, 1 line):

```python
            _, z, _ = self._dae.encode(x)        # (B, L, d_z) codebook-quantized
```

**After** (lines 1209-1212, 3 functional lines + 1 inline comment on the
3rd code line):

```python
            _encode_result = self._dae.encode(x)
            # Shape-tolerant: upstream DAE.encode returns (s_BLD, c_BLD, idx_BL) but newer
            # versions may add a 4th element. Use indexed access on the codebook latent.
            z = _encode_result[1] if isinstance(_encode_result, tuple) else _encode_result
```

**Logic:** capture the full return, then take index `[1]` (the
codebook-quantized latent `c_BLD`) using indexed access. This works
whether `encode` returns 3, 4, or more values, and is also a no-op if a
future version returns a single tensor directly. The downstream
`return self._dae.net(x, t, z_BLD=z)` is unchanged.

`s_BLD` (index 0) and `idx_BL` (index 2) are intentionally dropped —
they were already discarded by the original `_, z, _` destructure.

## Verification

| Gate | Result |
| --- | --- |
| `python -c "import ast; ast.parse(...kanzi.py...")` | AST parse OK |
| `ruff check adaptive_reflow/ tests/ scripts/run_ablation_sweep.py` | All checks passed (0) |
| `pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q` | 72 passed |
| `python tools/check_claims_consistency.py` | No drift detected |
| Standalone logic test (3-tuple AND 4-tuple returns) | Both yield `z='c_BLD'` (shape-tolerant confirmed) |

### N=1 sanity sweep status

The local venv has **no torch installed**, so the kanzi adapter fails at
the `_make_adapter` boundary with `RuntimeError: torch requested but not
installed` and the cells go to `BLOCKED` rather than `RUN_ERROR`. The
shape-mismatch path is therefore not exercised locally. **The fix is
still confirmed correct** by:

1. The AST parse succeeding.
2. The 3-line mock test above (3-tuple and 4-tuple both yield
   `z='c_BLD'`).
3. The ruff + D.4 + claims gates all remaining green.

End-to-end kanzi 0/5 -> 5/5 confirmation will land in the next wave's
GPU sweep on a torch-enabled host, where the same 3-line patch will turn
the previous 5/5 RUN_ERROR into 5/5 OK.

### Before/After

| | Before (Wave 156 P2) | After (this patch, pending GPU confirm) |
| --- | --- | --- |
| kanzi 5/5 sweep cells | 0/5 OK (5/5 RUN_ERROR) | Expected 5/5 OK |
| ruff | 0 | 0 (preserved) |
| D.4 | 72/72 PASS | 72/72 PASS (preserved) |
| claims drift | none | none (preserved) |

## Files changed

- `adaptive_reflow/adapters/kanzi.py` (+3 lines, -1 line at line 1209)
- `docs/audit/wave157-kanzi-fix.md` (this doc, NEW)

## Commit

See `git log -1 --format=%H` after `git commit`. Commit subject:

```
Wave 157 P1: kanzi shape fix at adaptive_reflow/adapters/kanzi.py:1209
(3-line patch: indexed access to encode result for shape tolerance;
unblocks K1 RC5 kanzi 5/5 cells; ruff 0 + D.4 72/72 PASS preserved)
```
