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


def test_a_dead_audit_citation_is_reported(tool, sandbox) -> None:
    """A citation into the audit tree promises a record the reader can open.

    Ten such citations had gone stale in ``tnnls_submission/`` because the
    audit tree was reorganised into topic clusters and the link *label* kept
    the old path.  The prefix is no longer exempt (2026-10-30).
    """
    (sandbox / "README.md").write_text(
        "Per `docs/audit/wave233-p3-tier-aware.md` and `docs/drafts/gone.md`.\n",
        encoding="utf-8",
    )
    dead = tool.collect()
    assert [row["target"] for row in dead] == [
        "docs/audit/wave233-p3-tier-aware.md",
        "docs/drafts/gone.md",
    ]
    assert tool.count_pointers() == 2


def test_a_live_audit_citation_is_accepted(tool, sandbox) -> None:
    record = sandbox / "docs" / "audit" / "engineering" / "p3-tier-aware.md"
    record.parent.mkdir(parents=True)
    record.write_text("# record\n", encoding="utf-8")
    (sandbox / "README.md").write_text(
        "Per `docs/audit/engineering/p3-tier-aware.md`.\n", encoding="utf-8"
    )
    assert tool.collect() == []
    assert tool.count_pointers() == 1


def test_changelog_is_not_a_surface(tool) -> None:
    """Append-only history may name files that were later deleted."""
    assert "CHANGELOG.md" not in tool.SURFACES


def test_declared_absent_weight_is_exempt_only_while_absent(tool, sandbox) -> None:
    """A 10.5 GB checkpoint is exempt when absent, checked when present."""
    token = "data/lineageflow/lineageflow-rp55.ckpt"
    (sandbox / "README.md").write_text(f"Weights at `{token}`.\n", encoding="utf-8")

    assert token in tool.known_absent()
    assert tool.count_pointers() == 0

    weights = sandbox / "data" / "lineageflow"
    weights.mkdir(parents=True)
    (weights / "lineageflow-rp55.ckpt").write_text("", encoding="utf-8")

    assert token not in tool.known_absent()
    assert tool.count_pointers() == 1
    assert tool.collect() == []


def test_symbols_and_globs_are_not_paths(tool, sandbox) -> None:
    """Only tokens with a known extension are treated as paths."""
    (sandbox / "README.md").write_text(
        "Call `tools.paper_metrics.compute_validity_pct` and "
        "`tools/sweep_*.py`.\n",
        encoding="utf-8",
    )
    assert tool.collect() == []


def test_the_retired_todo_directory_is_still_checked(tool, sandbox) -> None:
    """A prefix that no longer exists is the one that most needs checking.

    ``todo/`` was retired on 2026-10-13 and six citations into it survived in
    ``tnnls_submission/`` -- the prefix was simply not in ``PATH_PREFIXES``, so
    nothing looked.  It is in the tuple now.
    """
    assert "todo" in tool.PATH_PREFIXES
    (sandbox / "README.md").write_text(
        "Policy per `todo/PUSH-READY.md` and `todo/RISK-REGISTER.md`.\n",
        encoding="utf-8",
    )
    assert [row["target"] for row in tool.collect()] == [
        "todo/PUSH-READY.md",
        "todo/RISK-REGISTER.md",
    ]


def test_a_model_card_is_a_surface(tool, sandbox) -> None:
    """The seven model cards are in the mkdocs nav; they were not checked.

    Ten of their pointers named ``docs/paper-draft.md``, archived on 2026-08-28,
    and five named SOTA harnesses that were never committed.  ``READER_GLOBS``
    is what makes the next one fail instead of shipping.
    """
    cards = sandbox / "docs" / "models"
    cards.mkdir(parents=True)
    (cards / "demo.model_card.md").write_text(
        "See `docs/paper-draft.md`.\n", encoding="utf-8"
    )
    assert [row["target"] for row in tool.collect()] == ["docs/paper-draft.md"]


def test_prose_absent_is_exempt_only_for_its_own_document(tool, sandbox, monkeypatch) -> None:
    """``(doc, token)`` is the key, so an exemption cannot leak across pages."""
    monkeypatch.setattr(
        tool, "PROSE_ABSENT", {("README.md", "todo/GATES.md"): ("used to live",)}
    )
    (sandbox / "README.md").write_text(
        "The table that used to live in `todo/GATES.md`.\n", encoding="utf-8"
    )
    assert tool.collect() == []

    (sandbox / "docs" / "GATES.md").write_text(
        "The table lives in `todo/GATES.md`.\n", encoding="utf-8"
    )
    monkeypatch.setattr(tool, "SURFACES", ("README.md", "docs/GATES.md"))
    assert [row["target"] for row in tool.collect()] == ["todo/GATES.md"]


def test_a_prose_absent_exemption_lapses_with_the_phrase(tool, sandbox, monkeypatch) -> None:
    """The exemption is conditional on the prose, not on the token alone.

    A path kept alive by "the record was retired" has to lose its exemption the
    moment the sentence stops saying that -- otherwise the entry becomes a
    permanent blind spot, which is the defect the gate exists to catch.
    """
    monkeypatch.setattr(
        tool, "PROSE_ABSENT", {("README.md", "todo/GATES.md"): ("was never committed",)}
    )
    (sandbox / "README.md").write_text(
        "The table in `todo/GATES.md` was never committed.\n", encoding="utf-8"
    )
    assert tool.collect() == []

    (sandbox / "README.md").write_text(
        "The table in `todo/GATES.md` is authoritative.\n", encoding="utf-8"
    )
    assert [row["target"] for row in tool.collect()] == ["todo/GATES.md"]


def test_an_undelivered_checkpoint_is_exempt_only_while_absent(tool, sandbox) -> None:
    """The model cards tell the reader where to drop a checkpoint they must fetch."""
    token = "data/freqflow_ckpt/nnet_ema.pth"
    (sandbox / "README.md").write_text(f"Place it at `{token}`.\n", encoding="utf-8")
    assert tool.count_pointers() == 0

    target = sandbox / token
    target.parent.mkdir(parents=True)
    target.write_text("", encoding="utf-8")
    assert tool.count_pointers() == 1
