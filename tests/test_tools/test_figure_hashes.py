"""``check_figure_hashes`` must fail on the row, not on the table's absence.

``tnnls_submission/figures.md`` pins 37 figure digests and nothing checked
them.  The failure modes worth pinning are the ones that make a table look
clean: a format change that stops the regex matching (so zero rows are
verified), and a figure that exists in two tracked roots with different bytes
(so the table describes one of them and the other is a stale duplicate).
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[2] / "tools" / "check_figure_hashes.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_figure_hashes", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _row(idx: int, name: str, data: bytes, *, size: int | None = None) -> str:
    digest = hashlib.sha256(data).hexdigest()
    size = len(data) if size is None else size
    return f"| {idx} | `{name}` | `{digest}` | {size} | 10×10 | §1 | — |\n"


def _setup(tmp_path: Path, rows: str, files: dict[str, bytes]) -> Path:
    (tmp_path / "docs" / "figures").mkdir(parents=True)
    for name, data in files.items():
        (tmp_path / "docs" / "figures" / name).write_bytes(data)
    figures = tmp_path / "figures.md"
    figures.write_text(
        "| # | File | SHA-256 | Bytes | Dims | Section | Provenance |\n"
        "|---|---|---|---|---|---|---|\n" + rows,
        encoding="utf-8",
    )
    return figures


def test_a_matching_row_is_clean(tmp_path: Path) -> None:
    module = _load_module()
    figures = _setup(tmp_path, _row(1, "a.png", b"alpha"), {"a.png": b"alpha"})
    assert module.check(figures, root=tmp_path) == []


def test_a_wrong_digest_fails(tmp_path: Path) -> None:
    module = _load_module()
    figures = _setup(tmp_path, _row(1, "a.png", b"alpha"), {"a.png": b"beta"})
    problems = module.check(figures, root=tmp_path)
    assert [p.kind for p in problems] == ["hash"]


def test_a_missing_file_fails(tmp_path: Path) -> None:
    module = _load_module()
    figures = _setup(tmp_path, _row(1, "a.png", b"alpha"), {})
    problems = module.check(figures, root=tmp_path)
    assert [p.kind for p in problems] == ["missing"]


def test_a_wrong_size_fails(tmp_path: Path) -> None:
    module = _load_module()
    figures = _setup(
        tmp_path, _row(1, "a.png", b"alpha", size=99), {"a.png": b"alpha"}
    )
    problems = module.check(figures, root=tmp_path)
    assert [p.kind for p in problems] == ["size"]


def test_identical_copies_pass_and_divergent_copies_fail(tmp_path: Path) -> None:
    module = _load_module()
    figures = _setup(tmp_path, _row(1, "a.png", b"alpha"), {"a.png": b"alpha"})
    main = tmp_path / "paper-figures" / "main"
    main.mkdir(parents=True)
    (main / "a.png").write_bytes(b"alpha")
    assert module.check(figures, root=tmp_path) == []

    (main / "a.png").write_bytes(b"stale")
    problems = module.check(figures, root=tmp_path)
    assert [p.kind for p in problems] == ["divergent"]


def test_a_format_change_fails_closed(tmp_path: Path) -> None:
    """Zero parsed rows must not read as a clean table."""
    module = _load_module()
    figures = tmp_path / "figures.md"
    figures.write_text("| 1 | a.png | not-a-digest | 5 |\n", encoding="utf-8")
    problems = module.check(figures, root=tmp_path)
    assert [p.kind for p in problems] == ["unparsed"]


def test_main_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    module = _load_module()
    clean = _setup(tmp_path, _row(1, "a.png", b"alpha"), {"a.png": b"alpha"})
    assert module.main(["--figures", str(clean), "--root", str(tmp_path)]) == 0
    assert "OK: 1 figure rows match" in capsys.readouterr().out

    dirty = tmp_path / "dirty.md"
    dirty.write_text(_row(1, "a.png", b"nope"), encoding="utf-8")
    assert module.main(["--figures", str(dirty), "--root", str(tmp_path)]) == 1
    assert "FAIL" in capsys.readouterr().out
