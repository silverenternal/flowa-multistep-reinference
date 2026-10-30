"""Pins ``tools/check_reviewer_pointers.py`` — the code-span half of a pointer.

``check_doc_links.py`` resolves markdown links and ignores inline code spans.
The docs point at their evidence with code spans, so a renamed tool or a moved
evidence directory left the pointer dead while the prose still read as if it
resolved.  Two such pointers sat in both READMEs: ``tools/verify_reproducibility.py``
(the file is ``..._smoke.py``) and ``verification_outputs/composite_axis_byte_stable/SOURCE.md``
(the directory is ``docs/headline-evidence/composite_axis_byte_stable/``).
This test pins the gate that now checks them.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "check_reviewer_pointers.py"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("check_reviewer_pointers", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sandbox(tool, tmp_path, monkeypatch):
    """Point the gate at an empty tree with a single README surface."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "tnnls_submission").mkdir()
    monkeypatch.setattr(tool, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(tool, "SURFACES", ("README.md",))
    return tmp_path


def test_every_reviewer_pointer_resolves(tool) -> None:
    assert tool.collect() == []
    assert tool.count_pointers() > 300


def test_dead_pointer_is_reported(tool, sandbox) -> None:
    (sandbox / "README.md").write_text(
        "See `tools/does_not_exist.py`.\n", encoding="utf-8"
    )
    rows = tool.collect()
    assert [r["target"] for r in rows] == ["tools/does_not_exist.py"]
    assert tool.main(["--quiet"]) == 1


def test_live_pointer_is_accepted(tool, sandbox) -> None:
    (sandbox / "tools").mkdir()
    (sandbox / "tools" / "real.py").write_text("", encoding="utf-8")
    (sandbox / "README.md").write_text("See `tools/real.py`.\n", encoding="utf-8")
    assert tool.collect() == []
    assert tool.main(["--quiet"]) == 0


def test_audit_and_draft_citations_are_exempt(tool, sandbox) -> None:
    """A citation into the audit tree is provenance, not a live pointer."""
    (sandbox / "README.md").write_text(
        "Per `docs/audit/wave233-p3-tier-aware.md` and `docs/drafts/gone.md`.\n",
        encoding="utf-8",
    )
    assert tool.collect() == []
    assert tool.count_pointers() == 0


def test_changelog_is_not_a_surface(tool) -> None:
    """Append-only history may name files that were later deleted."""
    assert "CHANGELOG.md" not in tool.SURFACES


def test_symbols_and_globs_are_not_paths(tool, sandbox) -> None:
    """Only tokens with a known extension are treated as paths."""
    (sandbox / "README.md").write_text(
        "Call `tools.paper_metrics.compute_validity_pct` and "
        "`tools/sweep_*.py`.\n",
        encoding="utf-8",
    )
    assert tool.collect() == []
