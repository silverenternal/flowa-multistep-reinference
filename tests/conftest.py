"""Test-only path setup so the adaptive_reflow package resolves.

The package is at the repo root (``adaptive_reflow/``) and pytest must
be able to import it as ``adaptive_reflow``. We also walk up parent
directories looking for a ``pocket_modules`` package root so the legacy
torch-bound tests can resolve their ``pocket_modules`` ancestors when
they run; the legacy tests are gated on the ancestor walk succeeding
via the ``legacy`` marker.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_POCKET_MODULES_ROOT: Path | None = None
for parent in _REPO_ROOT.resolve().parents:
    if (parent / "pocket_modules").is_dir():
        _POCKET_MODULES_ROOT = parent
        break


def _ensure_repo_root_on_path() -> None:
    """Prepend the repo root to ``sys.path`` so ``import adaptive_reflow``
    resolves under any pytest invocation mode (rootdir-less, tests/ as
    rootdir, etc).
    """
    root_str = str(_REPO_ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def _ensure_pocket_modules_ancestor_on_path() -> None:
    """Prepend the ``pocket_modules`` ancestor to ``sys.path`` if it exists."""
    if _POCKET_MODULES_ROOT is None:
        return
    parent_str = str(_POCKET_MODULES_ROOT)
    if parent_str not in sys.path:
        sys.path.insert(0, parent_str)


_ensure_repo_root_on_path()
_ensure_pocket_modules_ancestor_on_path()
