"""Pins ``docs/audit/INDEX.md`` against the audit tree it claims to map.

The index was regenerated on 2026-10-30 from a committed generator
(``tools/regen_audit_index.py``) after nineteen days of drift: it listed 484 of
613 records, its TOTAL row disagreed with the sum of its own columns, and the
script that produced it lived in ``/tmp``.  These tests are the gate that keeps
the map honest, so the drift cannot silently recur.
"""

from __future__ import annotations

import importlib.util
import pathlib
import re
from collections import Counter

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
INDEX = REPO_ROOT / "docs" / "audit" / "INDEX.md"
TOOL = REPO_ROOT / "tools" / "regen_audit_index.py"

_ROW = re.compile(r"^- `([^`]+)`$", re.M)
_TABLE_ROW = re.compile(r"^\| `([a-z0-9_]+)` \| .+? \| (\d+) \| (\d+) \| (\d+) \|$", re.M)
_TOTAL_ROW = re.compile(r"^\| \*\*TOTAL\*\* \| — \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \|$", re.M)


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("regen_audit_index", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_index_is_current(tool) -> None:
    """A fresh build must be byte-identical to the committed file."""
    assert tool.build() == INDEX.read_text(encoding="utf-8"), (
        "docs/audit/INDEX.md is stale; run python3 tools/regen_audit_index.py"
    )


def test_every_record_is_listed_once(tool) -> None:
    """The index lists every audit record, and invents none."""
    on_disk = Counter(path.name for _rel, path in tool._records())
    listed = Counter(m.group(1) for m in _ROW.finditer(INDEX.read_text(encoding="utf-8")))
    assert listed == on_disk
    assert sum(listed.values()) == sum(on_disk.values()) > 500


def test_total_row_matches_the_columns() -> None:
    """TOTAL equals the column sums -- the defect that survived 19 days."""
    text = INDEX.read_text(encoding="utf-8")
    rows = _TABLE_ROW.findall(text)
    total = _TOTAL_ROW.search(text)
    assert total, "cluster map has no TOTAL row"
    assert tuple(int(x) for x in total.groups()) == (
        sum(int(r[1]) for r in rows),
        sum(int(r[2]) for r in rows),
        sum(int(r[3]) for r in rows),
    )


def test_each_row_counts_match_its_cluster(tool) -> None:
    """The per-cluster table row agrees with the detail block below it."""
    text = INDEX.read_text(encoding="utf-8")
    blocks = dict(
        (m.group(1), m.group(0))
        for m in re.finditer(r"### Cluster: `([a-z0-9_]+)`.*?(?=\n### Cluster: |\Z)", text, re.S)
    )
    for slug, files, active, historical in _TABLE_ROW.findall(text):
        if int(files) == 0:
            assert slug not in blocks, f"{slug} has no records but has a detail block"
            continue
        block = blocks[slug]
        assert len(_ROW.findall(block)) == int(files), slug
        assert f"**Files: {files}** (active: {active}, historical: {historical})" in block, slug


def test_cluster_order_is_frozen(tool) -> None:
    """Boundaries and order are frozen for the v3.0-tnnls-ready submission."""
    text = INDEX.read_text(encoding="utf-8")
    assert [r[0] for r in _TABLE_ROW.findall(text)] == [c[0] for c in tool.CLUSTERS]
    # 14 per-model + 11 activity clusters; the frozen count is 25.
    assert len(tool.CLUSTERS) == 25


def test_generator_is_deterministic(tool) -> None:
    """Two builds in the same tree are identical (no timestamps, no mtimes)."""
    assert tool.build() == tool.build()


def test_model_records_are_not_dragged_by_body_text(tool) -> None:
    """A body mention of a model name must not move a record into that cluster."""
    known: dict[str, str] = {}
    kanzi = REPO_ROOT / "docs" / "audit" / "kanzi"
    path = next(iter(sorted(kanzi.glob("*.md"))))
    rel = path.relative_to(REPO_ROOT / "docs" / "audit").as_posix()
    assert tool._classify(rel, path, known) == "kanzi"
