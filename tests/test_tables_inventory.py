"""Guard ``tnnls_submission/tables.md`` against its cited artifacts.

The table file promises byte-addressable provenance.  ``tools/check_tables_inventory.py``
tests that promise for the machine-checkable rows; this test runs it and fails
if any drift appears.  ``KNOWN_DRIFT`` is now empty: the 14 rows documented in
``docs/audit/tables-inventory-provenance.md`` were corrected on 2026-10-29, and
the second test below keeps the exemption set from being re-populated silently.

Skipped when ``verification_outputs/`` is absent (source-only checkout).
"""
from __future__ import annotations

import pytest

from tools.check_tables_inventory import (
    KNOWN_DRIFT,
    OUT,
    TABLES,
    Report,
    check_table1,
    check_table2,
    check_table3,
)

pytestmark = pytest.mark.skipif(
    not TABLES.is_file() or not OUT.is_dir(),
    reason="submission tables or verification_outputs are not present",
)


def _run() -> Report:
    rep = Report()
    check_table2(rep)
    check_table3(rep)
    check_table1(rep)
    return rep


def test_no_undocumented_drift() -> None:
    rep = _run()
    assert rep.unknown == [], f"tables.md drifted from its artifacts: {rep.unknown}"


def test_known_drift_list_stays_honest() -> None:
    """Every documented drift must still be real.

    Once the frozen table is corrected, the stale entry has to go; otherwise
    the exemption quietly covers a row that no longer needs it.
    """
    rep = _run()
    still_drifting = {r[0] for r in rep.known}
    assert still_drifting == KNOWN_DRIFT, (
        f"entries that no longer drift: {KNOWN_DRIFT - still_drifting}"
    )


def test_jt_artifact_carries_the_quoted_statistics() -> None:
    """Table 3 quotes a z and an asymptotic p; the CSV must store both."""
    import csv

    path = OUT / "wave234-p3-jonckheere.csv"
    if not path.is_file():
        pytest.skip("JT CSV not present")
    rows = list(csv.DictReader(path.open()))
    assert rows, "JT CSV is empty"
    for row in rows:
        assert float(row["jt_z"]) > 0
        assert 0.0 < float(row["jt_p_asymptotic"]) < 1.0
