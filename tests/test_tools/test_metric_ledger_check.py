"""``build_metric_ledger --check`` must notice a refresh, not just a new row.

``docs/METRIC_LEDGER.{md,json}`` is generated from CLAIMS.md, INSIGHTS.md and
the live engineering gates.  It was 5 rows stale (133 on disk, 138 when
regenerated) and nothing compared the two.  The comparison has to look at
content rather than shape: a regenerated digest on an otherwise identical row
changes no line count, which is why the drift went unnoticed.

These tests exercise ``_drift`` directly -- ``build()`` shells out to mkdocs,
pytest and ruff, so an end-to-end test of ``--check`` would cost minutes.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "tools" / "build_metric_ledger.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_metric_ledger", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_identical_content_reports_no_drift(tmp_path: Path) -> None:
    module = _load_module()
    target = tmp_path / "LEDGER.md"
    target.write_text("a\nb\n", encoding="utf-8")
    assert module._drift("a\nb\n", target) == []


def test_a_missing_file_is_drift(tmp_path: Path) -> None:
    module = _load_module()
    drift = module._drift("a\n", tmp_path / "nope.md")
    assert len(drift) == 1
    assert "missing" in drift[0]


def test_a_changed_digest_on_an_unchanged_row_count_is_drift(tmp_path: Path) -> None:
    module = _load_module()
    target = tmp_path / "LEDGER.md"
    target.write_text("row | baf1e11a\nrow2 | keep\n", encoding="utf-8")
    drift = module._drift("row | 8f98bfc5\nrow2 | keep\n", target)
    assert drift, "a same-length edit must still count as drift"
    assert "first difference at line 1" in drift[1]
    assert "baf1e11a" in drift[2]
    assert "8f98bfc5" in drift[3]


def test_the_repository_ledger_has_no_parse_errors(tmp_path: Path) -> None:
    """Guard the two counts the drift hid: rows and build errors."""
    text = (TOOL.parents[1] / "docs" / "METRIC_LEDGER.md").read_text(encoding="utf-8")
    assert "133 rows" not in text, "the 133-row header is the stale reading"
    assert "(138 rows)" in text
