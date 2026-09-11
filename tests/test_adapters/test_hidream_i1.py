"""HiDream-I1 adapter test split — thin re-export shim (Wave 104 P1-B).

The original 771-LOC ``test_hidream_i1.py`` was split into three
test-discovery-eligible sub-files (per pytest's ``python_files =
['test_*.py', '*_test.py']`` default pattern) plus this shim:

* :mod:`test_hidream_i1_smoke`     — 18 tests (capability handshake,
  build/solve/observe, validation paths, per-variant defaults,
  inject_forward_noise, weights-path resolver)
* :mod:`test_hidream_i1_conformance` — 3 tests (conditioning cache reuse,
  batched_inference determinism, 20-round ``Engine.run_round`` stress)
* :mod:`test_hidream_i1_metrics`   — empty (HiDream-I1 has no
  Tier-3 paper-metric tests at this time)

The shared helpers live in :mod:`_hidream_helpers` (leading underscore
prevents pytest discovery — it is import-only).

This shim file contains NO ``def test_*`` functions on purpose: a
re-export shim would double-count the test_* items (pytest walks every
imported module's namespace for ``test_*`` attributes). Keeping the
shim empty guarantees ``pytest --collect-only`` shows exactly the same
test count as before the split.

The original module docstring is preserved in
:mod:`test_hidream_i1_smoke`.

Wave 104 P1-B: pure file-system refactor. NO test_* function is
deleted, renamed, or modified.
"""
from __future__ import annotations

# No ``def test_*`` here on purpose. See module docstring.
__all__: list[str] = []
