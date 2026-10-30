"""Pins ``tools/check_doc_anchors.py`` — the fragment half of every link.

``check_doc_links.py`` resolves the file half of a relative link and drops the
fragment, and ``mkdocs build --strict`` does not compare fragments with heading
ids either.  So 101 ``page.md#anchor`` links were unchecked, and 37 of them
pointed at nothing.  This test pins the gate that now checks them.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "check_doc_anchors.py"

pytest.importorskip("markdown")


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("check_doc_anchors", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_fragment_link_resolves(tool) -> None:
    checked, problems = tool.check()
    assert checked > 50
    assert problems == []


def test_ascii_heading_id_drops_the_cjk_tail(tool, tmp_path) -> None:
    """``## Headline results / 头条结果`` must get the id ``headline-results``."""
    import markdown

    page = tmp_path / "p.md"
    page.write_text("## Headline results / 头条结果\n", encoding="utf-8")
    assert "headline-results" in tool._anchors(page, markdown)


def test_explicit_and_html_anchors_are_collected(tool, tmp_path) -> None:
    """Chinese headings need a hand-written anchor; both spellings count."""
    import markdown

    page = tmp_path / "p.md"
    page.write_text(
        '<a id="背景"></a>\n## 1. 背景：问题\n\n## Claim {#CLM-059}\n',
        encoding="utf-8",
    )
    anchors = tool._anchors(page, markdown)
    assert "背景" in anchors
    assert "CLM-059" in anchors


def test_broken_fragment_is_reported(tool, tmp_path, monkeypatch) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("[x](b.md#nope)\n", encoding="utf-8")
    (tmp_path / "docs" / "b.md").write_text("## Real heading\n", encoding="utf-8")
    monkeypatch.setattr(tool, "REPO_ROOT", tmp_path)
    checked, problems = tool.check()
    assert checked == 1
    assert problems and problems[0][1] == "b.md#nope"


def test_resolving_fragment_is_accepted(tool, tmp_path, monkeypatch) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("[x](b.md#real-heading)\n", encoding="utf-8")
    (tmp_path / "docs" / "b.md").write_text("## Real heading\n", encoding="utf-8")
    monkeypatch.setattr(tool, "REPO_ROOT", tmp_path)
    assert tool.check() == (1, [])
