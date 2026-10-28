"""Guard the SHA-256 rows in ``tnnls_submission/MANIFEST.md``.

The manifest is the reviewer's integrity anchor.  ``tools/check_submission_manifest.py``
resolves every row; this test fails if a *new* row goes stale, and fails if a
documented exemption is left behind after the row is refreshed.
"""
from __future__ import annotations

import pytest

from tools.check_submission_manifest import (
    CURRENT_ARTIFACTS,
    KNOWN_STALE,
    MANIFEST,
    REPO_ROOT,
    check_artifacts,
    check_ledger,
    check_rows,
)

pytestmark = pytest.mark.skipif(
    not MANIFEST.is_file(), reason="submission package is not present"
)


def test_no_undocumented_stale_row() -> None:
    for name, status in check_rows():
        if status.startswith("STALE"):
            assert name in KNOWN_STALE, f"manifest row went stale: {name} {status}"
        elif status == "MISSING":
            pytest.fail(f"manifest row points at a missing file: {name}")


def test_known_stale_list_stays_honest() -> None:
    still_stale = {n for n, s in check_rows() if s.startswith("STALE")}
    assert still_stale == KNOWN_STALE, (
        f"entries that no longer drift: {KNOWN_STALE - still_stale}"
    )


def test_packaging_addendum_artifacts_match_disk() -> None:
    assert check_artifacts() == [(rel, "ok") for rel, _, _ in CURRENT_ARTIFACTS]
    for rel, _sha, _size in CURRENT_ARTIFACTS:
        assert (REPO_ROOT / rel).is_file(), rel


def test_sha256sums_ledger_matches_tree() -> None:
    """`SHA256SUMS` is the only place MANIFEST.md's own digest can live."""
    bad = [(name, status) for name, status in check_ledger() if status != "ok"]
    assert bad == [], bad


def test_manifest_carries_no_self_hash() -> None:
    """A self-referential row is stale by construction; it must stay hash-free."""
    self_rows = [s for n, s in check_rows() if n == "MANIFEST.md"]
    assert self_rows == [], self_rows
