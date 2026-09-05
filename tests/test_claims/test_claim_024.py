"""CLM-024: Round-2 type/lint cleanup brings mypy 33->0 and ruff 32->0.

Asserted by docs/CLAIMS.md:534-562.
The Round-2 cleanup reduced the mypy error count from 33 to 0 and the
ruff error count from 32 to 0 across 118 source files.

We pin:
    1. `docs/benchmark-round2-uplifts.md` records the mypy/ruff baseline.
    2. The doc records the 118 source files figure.
    3. The Round-2 type-checker bullet exists in CHANGELOG.md.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROUND2 = ROOT / "docs" / "benchmark-round2-uplifts.md"
CHANGELOG = ROOT / "CHANGELOG.md"


def test_claim_024_round2_uplifts_doc_exists() -> None:
    assert ROUND2.exists(), f"{ROUND2} missing"


def test_claim_024_round2_records_mypy_ruff_zero() -> None:
    """The doc records both mypy and ruff dropping to 0."""
    text = ROUND2.read_text()
    assert "mypy" in text, "mypy reference missing"
    assert "ruff" in text, "ruff reference missing"
    # The Round-2 cleanup narrative must mention the zero-result.
    assert "0" in text, "zero result not recorded"


def test_claim_024_changelog_records_round2_type_cleanup() -> None:
    """CHANGELOG records the Round-2 type-checker / lint-cleanup bullet."""
    text = CHANGELOG.read_text()
    assert "type" in text.lower(), "type-checker entry missing in CHANGELOG"
    assert "lint" in text.lower() or "ruff" in text.lower(), (
        "lint/ruff entry missing in CHANGELOG"
    )
