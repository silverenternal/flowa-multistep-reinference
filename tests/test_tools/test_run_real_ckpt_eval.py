"""Shim — backward-compat module docstring for the pre-Wave-104 monolithic file.

Wave 104 P2-A: split from a single 2409-LOC file into 6 sub-files under
``tests/test_tools/eval/`` (one per ``tools/eval/`` module). All 44 test
functions were MOVED verbatim — no test is deleted, no test is renamed,
no fixture name changed.

Pytest auto-discovers the 44 tests via the 6 sub-files:

* ``tests/test_tools/eval/test_io.py``        (placeholder; 0 tests)
* ``tests/test_tools/eval/test_baseline.py``  (placeholder; 0 tests)
* ``tests/test_tools/eval/test_metrics.py``   (23 tests)
* ``tests/test_tools/eval/test_framework.py`` (9 tests)
* ``tests/test_tools/eval/test_sweep.py``     (9 tests)
* ``tests/test_tools/eval/test_cli.py``       (3 tests)

This file is the post-Wave-104 shim that REPLACES the original 2409-LOC
monolithic test file. It contains NO ``def test_*`` functions (by design
— pytest counts each test exactly once via the sub-file location). The
original 2409-LOC file is preserved in git history at the pre-Wave-104
commit (see ``docs/audit/wave101-review-layer3-tests.md`` Section 1 Rank
4 for the audit context and ``todo/planned/w101-fix-layer3-tests.md``
Section 3 P2-A for the fix plan).

D.4 byte-stable: PASS — no test logic was modified.
"""
from __future__ import annotations
