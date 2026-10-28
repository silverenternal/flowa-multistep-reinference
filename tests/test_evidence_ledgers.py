"""Every SHA256SUMS ledger in the evidence bundle must be honest.

`data_availability.md` sends reviewers to `sha256sum --check`, so a stale line
or a file that is named SHA256SUMS but holds prose is a reproducibility defect,
not a cosmetic one. The three live issues are exempted with reasons in
`tools/check_evidence_ledgers.py`; these tests fail on anything new and on an
exemption that outlives its issue.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_evidence_ledgers as checker  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (ROOT / "verification_outputs").is_dir(),
    reason="evidence bundle not present",
)


def test_no_unknown_ledger_problems() -> None:
    errors, counts, n_known = checker.check()
    assert errors == [], "\n".join(errors)
    assert counts.get("ok", 0) + counts.get("self", 0) >= 15, counts
    assert n_known == len(checker.KNOWN_ISSUES)


def test_self_line_failures_are_expected_not_real() -> None:
    """A ledger's own line can never match; it must not be reported as drift."""
    _, counts, _ = checker.check()
    assert counts.get("self", 0) > 0
    assert counts.get("real", 0) == 0
    assert counts.get("not_a_ledger", 0) == 1


def test_no_exemption_outlives_its_issue() -> None:
    errors, _, _ = checker.check()
    stale = [e for e in errors if "exemption no longer matches" in e]
    assert stale == [], stale
