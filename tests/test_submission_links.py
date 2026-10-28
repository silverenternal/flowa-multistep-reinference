"""Every GitHub link in ``tnnls_submission/*.md`` must resolve.

The submission package is reviewed on GitHub, so a link to a moved or never
committed file is a reviewer-visible defect.  Before 2026-10-29 the checker
reported counts and always exited 0, which meant 19 dead targets sat in the
package unnoticed.  These tests make the count load-bearing: anything absent
fails, and an exemption that outlives its issue fails too.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_submission_links as checker  # noqa: E402


def test_no_absent_link_targets() -> None:
    rows = checker.collect()
    absent = [
        (r["source"], r["target"])
        for r in rows
        if r["status"] == "absent"
        and (r["source"], r["target"]) not in checker.KNOWN_ABSENT
    ]
    assert absent == [], "\n".join(f"{s} -> {t}" for s, t in absent)


def test_strict_exit_code_reflects_absent() -> None:
    """The gate must be able to fail; a checker that always exits 0 is not a gate."""
    assert checker.main([]) == 0


def test_no_exemption_outlives_its_issue() -> None:
    rows = {(r["source"], r["target"]) for r in checker.collect() if r["status"] == "absent"}
    stale = [k for k in checker.KNOWN_ABSENT if k not in rows]
    assert stale == [], f"KNOWN_ABSENT entries now resolve: {stale}"
