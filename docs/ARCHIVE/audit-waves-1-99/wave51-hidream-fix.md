# Wave 51 Agent A — HiDream harness test fix

## Summary

Fixed 2 failing tests in `tests/test_tools/test_run_sota_hidream_i1_experiment.py`
(`test_per_round_dumps_subdirs` and `test_per_round_dumps_n_rounds_one`) by
making the HiDream harness work in the test environment without third-party
packages.

## Root cause

The test runs the harness via a subprocess using
`REPO_ROOT / ".venv" / "bin" / "python"`. This venv only has `numpy` (the
fixture's probe in `tests/test_tools/test_run_sota_hidream_i1_experiment.py`
probes `import numpy`). The harness was unconditionally importing two
third-party packages at module-load time, so the test subprocess
crashed before any PNG emission could happen:

1. **`import torch`** inside `_build_pipeline_and_adapter`
   (`tools/run_sota_hidream_i1_experiment.py` line 204, pre-fix).
   The synthetic smoke path does not need torch at all — the
   HiDream-I1-Dev weights are not present, so the function returns
   early after the synthetic-branch returns `None, adapter`.

2. **`from PIL import Image`** inside `_emit_synthetic_pngs`
   (`tools/run_sota_hidream_i1_experiment.py` line 859, pre-fix).
   The synthetic path emits PIL-noise PNGs; on the test venv
   Pillow is unavailable, so the smoke test crashed inside the
   per-round emission loop.

Both bugs only surface on the test subprocess (which has neither
`torch` nor `Pillow`), not on the pytest interpreter itself (which
has both, and so triggers `requires_torch` skip on cold-import
failure).

## Fix

Two minimal, additive changes to `tools/run_sota_hidream_i1_experiment.py`:

### 1. Defer `import torch` past the synthetic branch

Moved `import torch` from the top of `_build_pipeline_and_adapter` to
just below the `if weights is None or not weights.exists():` early
return. The synthetic path never touches torch.

### 2. Stdlib-only PNG fallback in `_emit_synthetic_pngs`

Replaced the unconditional `from PIL import Image` with a try/except
that prefers PIL when available and falls back to a stdlib-only PNG
writer (using `struct` + `zlib` + CRC-32) when Pillow is unavailable.
Both code paths produce valid RGB PNGs that PIL can re-read; the test
harness only checks `path.exists()` so byte-level identity isn't
required.

The fallback uses the canonical PNG signature `\x89PNG\r\n\x1a\n`,
8-bit RGB color type 2, filter byte 0 per row, and zlib-compressed
IDAT — no deflate parameters, just the default. CRCs use
`zlib.crc32()` with the PNG polynomial (default).

## Files changed

- `tools/run_sota_hidream_i1_experiment.py` — 2 spots, ~40 LOC added
  (mostly the stdlib PNG writer helper + its docstring).

No tests were modified; the test fixture already had a numpy probe and
`requires_torch` gating, so no skip marker was needed.

## Verification

```
.venvs/flowmol3_venv/bin/python -m pytest tests/test_tools/test_run_sota_hidream_i1_experiment.py -q --tb=line
......                                                                   [100%]
6 passed in 4.77s
```

All 6 tests pass. The previously-failing 2 tests (`test_per_round_dumps_subdirs`
and `test_per_round_dumps_n_rounds_one`) now pass; the 4 that already
passed (`test_module_imports`, `test_help_flag_exits_cleanly`,
`test_emit_synthetic_pngs_emits_per_round`, `test_make_per_round_callback_signature`)
are unaffected — they exercise either direct module imports or the PIL
path through the pytest interpreter (which has Pillow).

## Notes

- The `requires_torch` fixture (`tests/conftest.py`) checks
  `importlib.util.find_spec("torch")` on the pytest interpreter, not
  the subprocess. So `pytestmark = pytest.mark.usefixtures("requires_torch")`
  on this test module does not protect against the `.venv/bin/python`
  subprocess failing on the same package. Wave 51 fix removes the
  subprocess's torch dependency on the synthetic path; if a future
  test were to add a real-weights run, the subprocess would still
  need torch and the existing fixture would not catch that — a
  separate concern, not addressed here.
- The stdlib PNG writer is intentionally minimal (uncompressed
  filtered rows, zlib-default compression). It is *not* a general-
  purpose PIL replacement; only the synthetic-noise smoke path uses it.
- No real-weights path is affected: `_build_pipeline_and_adapter`'s
  torch branch is reached only when `--weights` points at a directory
  that exists, in which case torch is required by construction.