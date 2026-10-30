"""Pins ``tools/paper_evidence.py`` -- the register and the surface it renders.

``docs/PAPER-EVIDENCE.md`` is generated from ``docs/paper-evidence.json`` and is
the single cell-level register every paper task reads first.  ``--check``
validated the register's paths and quotes but never compared the markdown a
reviewer reads against a fresh render, so the two could drift silently.  These
tests pin both halves.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "paper_evidence.py"
REGISTER = REPO_ROOT / "docs" / "paper-evidence.json"
SURFACE = REPO_ROOT / "docs" / "PAPER-EVIDENCE.md"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("paper_evidence", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def register(tool):
    return tool.load(REGISTER)


def test_check_passes_on_the_real_register(tool) -> None:
    assert tool.main(["--check"]) == 0


def test_surface_matches_a_fresh_render(tool, register) -> None:
    assert tool.check_markdown(register, SURFACE) == []


def test_stale_surface_is_reported(tool, register, tmp_path) -> None:
    path = tmp_path / "PAPER-EVIDENCE.md"
    path.write_text("stale\n", encoding="utf-8")
    problems = tool.check_markdown(register, path)
    assert len(problems) == 1
    assert "is stale against the register" in problems[0]


def test_missing_surface_is_reported(tool, register, tmp_path) -> None:
    problems = tool.check_markdown(register, tmp_path / "absent.md")
    assert len(problems) == 1
    assert "does not exist" in problems[0]


def test_render_then_check_round_trips(tool, register, tmp_path) -> None:
    path = tmp_path / "rendered.md"
    path.write_text(tool.render(register), encoding="utf-8")
    assert tool.check_markdown(register, path) == []


def test_render_is_deterministic(tool, register) -> None:
    assert tool.render(register) == tool.render(register)
