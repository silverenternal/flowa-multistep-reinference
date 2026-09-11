"""Shim — backward-compat module docstring for the pre-Wave-104 monolithic file.

Wave 104 P2-B: split from a single 2586-LOC file into per-section
sub-files under ``tests/test_algorithm/test_runner/``. All 41 test
functions were MOVED verbatim — no test is deleted, no test is renamed,
no fixture name changed.

Pytest auto-discovers the 41 tests via the sub-file location:

* ``tests/test_algorithm/test_runner/test_runner_all.py`` (initial
  consolidated landing pad — further splits tracked as Wave 104+
  follow-up. The 7 logical groupings called out in the audit
  document ``docs/audit/wave101-review-layer3-tests.md`` Section 1
  Rank 2 are: (1) default runner vs engine path, (2) mixed scheduler +
  driver, (3) per_round_metrics, (4) algorithm_signatures, (5) default
  factories, (6) record_round_feedback wiring, (7) F34 / F3 / C4
  contract round-trips).

This file is the post-Wave-104 shim that REPLACES the original 2586-LOC
monolithic test file. It contains NO ``def test_*`` functions (by design
— pytest counts each test exactly once via the sub-file location). The
original 2586-LOC file is preserved in git history at the pre-Wave-104
commit (see ``docs/audit/wave101-review-layer3-tests.md`` Section 1 Rank
2 for the audit context and ``todo/planned/w101-fix-layer3-tests.md``
Section 3 P2-B for the fix plan).

D.4 byte-stable: PASS — no test logic was modified.
"""
from __future__ import annotations
