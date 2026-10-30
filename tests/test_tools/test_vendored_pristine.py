"""Pins ``tools/check_vendored_pristine.py`` — guardrail 1, made mechanical.

AGENTS.md guardrail 1 forbids modifying the vendored upstream trees, and
``tnnls_submission/data_availability.md`` discloses nine files that were patched
during development and reverted.  ``data/`` is gitignored, so no CI job can see
those trees; the gate is the only thing that checks them, which makes the gate
itself worth testing.
"""

from __future__ import annotations

import importlib.util
import pathlib
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "check_vendored_pristine.py"


@pytest.fixture()
def tool():
    spec = importlib.util.spec_from_file_location("check_vendored_pristine", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _repo(root: pathlib.Path, rel: str) -> pathlib.Path:
    path = root / rel
    path.mkdir(parents=True)
    for cmd in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "t@example.com"],
        ["git", "config", "user.name", "t"],
    ):
        subprocess.run(cmd, cwd=path, check=True, capture_output=True)
    (path / "mod.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=path, check=True, capture_output=True)
    return path


def _point_at(tool, root: pathlib.Path) -> None:
    """Redirect the gate at a scratch tree and drop the real pin lists."""
    tool.REPO_ROOT = root
    tool.DATA = root / "data"
    tool.PINNED = ()
    tool.REVERTED_FILES = ()


def test_skips_when_no_data_tree(tool, tmp_path, monkeypatch) -> None:
    """A clone has no data/, and that is not a failure."""
    _point_at(tool, tmp_path)
    checks, problems = tool.check()
    assert checks == 0
    assert problems == []


def test_clean_tree_passes(tool, tmp_path) -> None:
    _point_at(tool, tmp_path)
    _repo(tmp_path, "data/kanzi_upstream")
    checks, problems = tool.check()
    assert checks >= 1
    assert problems == []


def test_modified_tracked_file_is_reported(tool, tmp_path) -> None:
    _point_at(tool, tmp_path)
    path = _repo(tmp_path, "data/kanzi_upstream")
    (path / "mod.py").write_text("x = 2\n")
    _checks, problems = tool.check()
    assert len(problems) == 1
    assert "modified tracked files" in problems[0]
    assert "mod.py" in problems[0]


def test_untracked_addition_is_allowed(tool, tmp_path) -> None:
    """Weights, caches and generated configs land untracked in these trees."""
    _point_at(tool, tmp_path)
    path = _repo(tmp_path, "data/kanzi_upstream")
    (path / "weights.pt").write_bytes(b"\0")
    _checks, problems = tool.check()
    assert problems == []


def test_head_mismatch_is_reported(tool, tmp_path) -> None:
    _point_at(tool, tmp_path)
    _repo(tmp_path, "data/kanzi_upstream")
    tool.PINNED = (("data/kanzi_upstream", "0000000"),)
    _checks, problems = tool.check()
    assert any("pinned to 0000000" in p for p in problems)


def test_reverted_file_must_match_its_pin(tool, tmp_path) -> None:
    _point_at(tool, tmp_path)
    path = _repo(tmp_path, "data/kanzi_upstream")
    tool.PINNED = ()
    tool.REVERTED_FILES = (("data/kanzi_upstream", "HEAD", "mod.py"),)
    assert tool.check()[1] == []
    (path / "mod.py").write_text("x = 3\n")
    problems = tool.check()[1]
    assert any("differs from HEAD" in p for p in problems)
