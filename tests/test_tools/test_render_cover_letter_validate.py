"""``render_cover_letter.py --validate`` must not read "no marker" as "filled".

The shipped cover letter substitutes ``INTERACTIVE_DEFAULTS`` exemplar values
instead of leaving ``[USER TO FILL: ...]`` markers, so a rendered letter looks
identical whether its identities are real or still ``hugo@example.com``.  The
validator used to label every absent marker ``[FILLED]``, which turned the one
question the author needed answered — are the exemplars gone? — into a green
report that could never go red.  These tests pin the two signals apart.
"""

from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path

TOOL = (
    Path(__file__).resolve().parents[2] / "tools" / "render_cover_letter.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("render_cover_letter", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run(tmp_path: Path, text: str) -> str:
    module = _load_module()
    target = tmp_path / "cover_letter.md"
    target.write_text(text, encoding="utf-8")
    stream = io.StringIO()
    rc = module.run_validate(target, output_stream=stream)
    assert rc == 0
    return stream.getvalue()


def test_an_unfilled_marker_is_reported_as_unfilled(tmp_path: Path) -> None:
    out = _run(
        tmp_path,
        "**Authors:** `[USER TO FILL: Reviewer 1 affiliation]`\n",
    )
    assert "[UNFILLED]" in out
    assert "1 still unfilled" in out


def test_an_exemplar_without_a_marker_is_not_reported_as_filled(
    tmp_path: Path,
) -> None:
    out = _run(
        tmp_path,
        "Sincerely,\n\nHugo Huang\nMIT CSAIL, 32 Vassar St\nhugo@example.com\n",
    )
    assert "[FILLED]" not in out
    assert "[MARKER GONE]" in out
    assert "exemplar hits" in out
    assert "appear to carry real values" not in out
    # The hit is reported with a line number the author can navigate to.
    assert "line 4" in out


def test_a_letter_with_no_marker_and_no_exemplar_is_reported_clean(
    tmp_path: Path,
) -> None:
    out = _run(
        tmp_path,
        "Sincerely,\n\nA. Real Author\nDepartment of Statistics, Real University\n"
        "author@real-university.edu\n",
    )
    assert "0 exemplar hits" in out
    assert "appear to carry real values" in out


def test_the_shipped_letter_still_reports_its_exemplars() -> None:
    """The repository's own letter must not validate as filled."""
    module = _load_module()
    letter = TOOL.parents[1] / "tnnls_submission" / "cover_letter.md"
    stream = io.StringIO()
    module.run_validate(letter, output_stream=stream)
    out = stream.getvalue()
    summary = next(line for line in out.splitlines() if line.startswith("Summary:"))
    hits = int(summary.split()[-3])
    assert hits > 0, summary
    assert "example.com" in out
