"""The per-cell reproduction recipes must not pin stale hashes.

`paper-data/**/*REPRODUCIBILITY_RECIPE.md` is reviewer-facing: a pinned hash
that no longer matches sends a reviewer down a false trail. The one known-stale
row is exempted in `tools/check_recipe_hashes.py` with its reason, and the
second test here makes sure that exemption cannot outlive the row.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_recipe_hashes as checker  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (ROOT / "paper-data").is_dir(),
    reason="paper-data/ not present",
)


def test_all_recipe_pins_match_except_the_documented_one() -> None:
    errors, n_rows, n_stale = checker.check()
    assert errors == [], "\n".join(errors)
    assert n_rows >= 60, f"only {n_rows} pinned rows parsed; the table format changed?"
    assert n_stale == len(checker.KNOWN_STALE)


def test_no_stale_exemption_outlives_its_row() -> None:
    rows, _ = checker.collect()
    seen = {(doc, path, sha) for doc, path, sha, _ in rows}
    for doc, path, sha in checker.KNOWN_STALE:
        assert (doc, path, sha) in seen, (
            f"exemption for {path} in {doc} no longer matches a row; "
            "remove it from KNOWN_STALE"
        )


def test_every_pinned_path_resolves() -> None:
    rows, _ = checker.collect()
    unresolved = [path for _, path, _, resolved in rows if resolved is None]
    assert unresolved == [], unresolved
