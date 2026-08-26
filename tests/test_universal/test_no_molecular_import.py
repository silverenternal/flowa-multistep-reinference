"""AST-level guard: the ``universal/`` subpackage must not import from ``molecular/``.

This is the load-bearing test for the universal / molecular split.
If a future change drags a ``molecular`` import into ``universal/``,
this test fails closed.

We do this by walking the AST of every ``adaptive_reflow/universal/*.py``
file and asserting no ``import`` or ``import from`` statement targets
the ``adaptive_reflow.molecular`` namespace.

The test is stdlib-only (uses :mod:`ast` and :mod:`pathlib`).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_UNIVERSAL_DIR = _REPO_ROOT / "adaptive_reflow" / "universal"


def _iter_python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if p.is_file())


def _imports_molecular(tree: ast.AST) -> list[tuple[str, int]]:
    """Return ``(qualified_name, lineno)`` for every import that touches
    ``adaptive_reflow.molecular`` (or any of its submodules).

    Walks ``ast.Import`` and ``ast.ImportFrom`` nodes. Names compared
    are package-level only — a relative import (``from . import x``)
    cannot reach ``molecular`` because ``molecular`` is a sibling
    package, not a subpackage of ``universal``.
    """
    findings: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "adaptive_reflow.molecular" or alias.name.startswith(
                    "adaptive_reflow.molecular."
                ):
                    findings.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "adaptive_reflow.molecular" or module.startswith(
                "adaptive_reflow.molecular."
            ):
                findings.append((module, node.lineno))
    return findings


class TestNoMolecularImport:
    """The :mod:`adaptive_reflow.universal` subpackage must be molecule-free."""

    @pytest.mark.parametrize(
        "py_file",
        [str(p.relative_to(_REPO_ROOT)) for p in _iter_python_files(_UNIVERSAL_DIR)],
        ids=lambda s: s.replace("\\", "/"),
    )
    def test_universal_file_does_not_import_molecular(self, py_file: str) -> None:
        """Each ``adaptive_reflow/universal/*.py`` file must not import
        anything from ``adaptive_reflow.molecular``."""
        path = _REPO_ROOT / py_file
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        findings = _imports_molecular(tree)
        assert findings == [], (
            f"{py_file} must not import from adaptive_reflow.molecular; "
            f"found: {findings}"
        )

    def test_universal_directory_exists(self) -> None:
        """Sanity: the :mod:`adaptive_reflow.universal` directory must exist."""
        assert _UNIVERSAL_DIR.is_dir(), (
            f"expected universal directory at {_UNIVERSAL_DIR}, not found"
        )

    def test_universal_directory_has_at_least_one_module(self) -> None:
        """Sanity: the directory must contain at least one Python module."""
        py_files = _iter_python_files(_UNIVERSAL_DIR)
        assert py_files, "universal/ has no .py files"

    def test_universal_init_exports_no_molecule_named_symbols(self) -> None:
        """The :mod:`adaptive_reflow.universal` package's ``__init__`` must
        not expose any symbol whose name contains the substring
        ``molecule`` (case-insensitive)."""
        from adaptive_reflow import universal

        for name in dir(universal):
            if name.startswith("_"):
                continue
            assert "molecule" not in name.lower(), (
                f"universal/__init__ exposes molecule-named symbol: {name!r}"
            )
