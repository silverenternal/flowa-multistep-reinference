"""AST-level guard: the ``universal/`` and ``frame/`` subpackages must not
import from ``molecular/``.

This is the load-bearing test for the universal / molecular split.
If a future change drags a ``molecular`` import into ``universal/`` or
``frame/``, this test fails closed.

We do this by walking the AST of every ``adaptive_reflow/universal/*.py``
and ``adaptive_reflow/frame/*.py`` file and asserting no ``import`` or
``import from`` statement targets the ``adaptive_reflow.molecular``
namespace. The guard covers both:

* ``adaptive_reflow/universal/`` — the universal protocol + carrier
  surface (must be model-family-agnostic).
* ``adaptive_reflow/frame/`` — the universal round frame, including
  the public engine + adapter protocol shim. Per ADR-0003, the frame
  layer carries no molecule-specific knowledge (no molecule-only
  fallback tables such as the legacy ``DOMAIN_BY_CHANNEL``).

The test is stdlib-only (uses :mod:`ast` and :mod:`pathlib`).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_UNIVERSAL_DIR = _REPO_ROOT / "adaptive_reflow" / "universal"
_FRAME_DIR = _REPO_ROOT / "adaptive_reflow" / "frame"
_GUARDED_DIRS: tuple[Path, ...] = (_UNIVERSAL_DIR, _FRAME_DIR)


def _iter_python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if p.is_file())


def _imports_molecular(tree: ast.AST) -> list[tuple[str, int]]:
    """Return ``(qualified_name, lineno)`` for every import that touches
    ``adaptive_reflow.molecular`` (or any of its submodules).

    Walks ``ast.Import`` and ``ast.ImportFrom`` nodes. Names compared
    are package-level only — a relative import (``from . import x``)
    cannot reach ``molecular`` because ``molecular`` is a sibling
    package, not a subpackage of ``universal`` or ``frame``.
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


def _guarded_dir_params() -> list[tuple[str, Path]]:
    """Return ``(label, directory)`` pairs for every guarded subpackage.

    Each guarded directory contributes its own parametrised test so a
    failure pinpoints the offending subpackage.
    """
    return [(p.name, p) for p in _GUARDED_DIRS]


class TestNoMolecularImport:
    """The :mod:`adaptive_reflow.universal` and :mod:`adaptive_reflow.frame`
    subpackages must be molecule-free.
    """

    @pytest.mark.parametrize(
        "guarded_label,py_file",
        [
            (label, str(p.relative_to(_REPO_ROOT)))
            for label, root in _guarded_dir_params()
            for p in _iter_python_files(root)
        ],
        ids=lambda s: s.replace("\\", "/"),
    )
    def test_guarded_file_does_not_import_molecular(
        self, guarded_label: str, py_file: str
    ) -> None:
        """Each ``adaptive_reflow/{universal,frame}/*.py`` file must not
        import anything from ``adaptive_reflow.molecular``."""
        del guarded_label  # surfaced via the parametrise label
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

    def test_frame_directory_exists(self) -> None:
        """Sanity: the :mod:`adaptive_reflow.frame` directory must exist."""
        assert _FRAME_DIR.is_dir(), (
            f"expected frame directory at {_FRAME_DIR}, not found"
        )

    @pytest.mark.parametrize(
        "guarded_label,guarded_dir",
        _guarded_dir_params(),
        ids=lambda s: s if isinstance(s, str) else s.name,
    )
    def test_guarded_directory_has_at_least_one_module(
        self, guarded_label: str, guarded_dir: Path
    ) -> None:
        """Sanity: every guarded directory must contain at least one
        Python module so the AST guard actually exercises something."""
        del guarded_label  # surfaced via the parametrise label
        py_files = _iter_python_files(guarded_dir)
        assert py_files, f"{guarded_dir} has no .py files"

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

    def test_frame_init_exports_no_molecule_named_symbols(self) -> None:
        """The :mod:`adaptive_reflow.frame` package's ``__init__`` must
        not expose any symbol whose name contains the substring
        ``molecule`` (case-insensitive)."""
        from adaptive_reflow import frame

        for name in dir(frame):
            if name.startswith("_"):
                continue
            assert "molecule" not in name.lower(), (
                f"frame/__init__ exposes molecule-named symbol: {name!r}"
            )

    def test_frame_adapter_module_does_not_re_export_domain_by_channel(self) -> None:
        """The legacy ``DOMAIN_BY_CHANNEL`` molecule-only fallback table
        that used to be re-exported from :mod:`adaptive_reflow.frame.adapter`
        has been removed. Per-channel domain resolution is the adapter's
        own responsibility via ``AdapterCapabilities.channel_domains``."""
        from adaptive_reflow.frame import adapter as frame_adapter

        assert not hasattr(frame_adapter, "DOMAIN_BY_CHANNEL"), (
            "frame.adapter.DOMAIN_BY_CHANNEL has been removed; the universal "
            "engine resolves channel domains via each adapter's own "
            "AdapterCapabilities.channel_domains declaration."
        )
