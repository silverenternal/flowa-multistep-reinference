"""Shim — backward-compat module docstring for the pre-Wave-104 monolithic file.

Wave 104 P2-B: split from a single 2549-LOC file into 7 per-family
sub-files under ``tests/test_algorithm/test_scheduler/`` (one per
scheduler family + 3 cross-cutting concerns). All 117 test functions
were MOVED verbatim — no test is deleted, no test is renamed, no
fixture name changed.

Pytest auto-discovers the 117 tests via the 7 sub-files:

* ``tests/test_algorithm/test_scheduler/test_cosine_default.py``     (17 tests)
* ``tests/test_algorithm/test_scheduler/test_simple_schedulers.py`` (17 tests)
* ``tests/test_algorithm/test_scheduler/test_convergence_adaptive.py`` (30 tests)
* ``tests/test_algorithm/test_scheduler/test_codimension_sheet.py`` (25 tests)
* ``tests/test_algorithm/test_scheduler/test_inject_noise.py``      (5 tests)
* ``tests/test_algorithm/test_scheduler/test_nfe_aware.py``         (11 tests)
* ``tests/test_algorithm/test_scheduler/test_config_round_trip.py`` (12 tests)

This file is the post-Wave-104 shim that REPLACES the original 2549-LOC
monolithic test file. It contains NO ``def test_*`` functions (by design
— pytest counts each test exactly once via the sub-file location). The
original 2549-LOC file is preserved in git history at the pre-Wave-104
commit (see ``docs/audit/wave101-review-layer3-tests.md`` Section 1 Rank
1 for the audit context and ``todo/planned/w101-fix-layer3-tests.md``
Section 3 P2-B for the fix plan).

D.4 byte-stable: PASS — no test logic was modified.
"""
from __future__ import annotations
