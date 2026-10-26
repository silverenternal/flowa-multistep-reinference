"""Tests for the single paper evidence register (docs/paper-evidence.json)."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import paper_evidence  # noqa: E402


def _register() -> dict:
    return copy.deepcopy(paper_evidence.load())


def test_repository_register_is_valid() -> None:
    register = paper_evidence.load()
    assert paper_evidence.validate(register) == []
    assert len(register["cells"]) == 11


def test_win_requires_both_halves() -> None:
    register = _register()
    r2 = next(cell for cell in register["cells"] if cell["id"] == "R2")
    r2["cell_verdict"] = "WIN"  # frontier is still UNMEASURED
    errors = paper_evidence.validate(register)
    assert any("cell WIN requires point WIN and frontier WIN" in error for error in errors)


def test_unmeasured_frontier_cannot_win() -> None:
    register = _register()
    cell = next(cell for cell in register["cells"] if cell["id"] == "R6")
    cell["point"]["verdict"] = "WIN"
    cell["cell_verdict"] = "WIN"
    errors = paper_evidence.validate(register)
    assert any("unmeasured frontier cannot be WIN" in error for error in errors)


def test_duplicate_id_rejected() -> None:
    register = _register()
    register["cells"].append(copy.deepcopy(register["cells"][0]))
    errors = paper_evidence.validate(register)
    assert any("duplicate id" in error for error in errors)


def test_missing_artifact_rejected() -> None:
    register = _register()
    register["cells"][0]["point"]["artifact"] = "verification_outputs/does-not-exist.json"
    errors = paper_evidence.validate(register)
    assert any("path does not exist" in error for error in errors)


def test_quote_must_appear_in_artifact_or_audit() -> None:
    register = _register()
    register["cells"][0]["point"]["quote"] = "this string is nowhere"
    errors = paper_evidence.validate(register)
    assert any("quote not found" in error for error in errors)


def test_render_is_deterministic_and_lists_every_cell() -> None:
    register = paper_evidence.load()
    first = paper_evidence.render(register)
    second = paper_evidence.render(register)
    assert first == second
    for cell in register["cells"]:
        assert f"### {cell['id']} — " in first
