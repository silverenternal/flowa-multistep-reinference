"""Every relative markdown link in the docs tree must resolve.

GitHub resolves a relative link against the containing file's directory, so a
moved document or a repo-root-relative target silently 404s.  Before
2026-10-29 nothing checked this: 146 unique targets were broken across 50
files (99 had an unambiguous fix, 47 did not).

``tools/check_doc_links.py`` is the reproducible form.  These tests fail on
any new breakage and on an exemption that outlives its issue.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_doc_links as checker  # noqa: E402


def test_no_broken_relative_links() -> None:
    broken = [
        (r["source"], r["target"], r["status"])
        for r in checker.collect()
        if r["source"] not in checker.FROZEN
    ]
    assert broken == [], "\n".join(f"{s} -> {t} ({k})" for s, t, k in broken)


def test_scanner_actually_walks_the_tree() -> None:
    """A gate that scans nothing always passes."""
    assert checker.count_links() >= 1000


def test_code_fences_are_not_treated_as_links() -> None:
    """Example snippets such as ``[alt](figures/foo.png)`` are prose."""
    targets = {r["target"] for r in checker.collect()}
    assert "figures/foo.png" not in targets


def test_frozen_entries_point_at_real_files() -> None:
    """An exemption for a path that no longer exists silently widens the gate."""
    missing = [s for s in checker.FROZEN if not (ROOT / s).is_file()]
    assert missing == [], missing
