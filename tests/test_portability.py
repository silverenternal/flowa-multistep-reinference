"""The code must not assume it lives in the author's home directory.

Before 2026-10-29, 93 lines across ``tools/``, ``scripts/`` and
``adaptive_reflow/`` pinned the repository root to the literal
``/home/hugo/codes/flowa-multistep-reinference``.  On this box that is
harmless; on a reviewer's clone every one of them points at a directory that
does not exist, and the failure is silent — a path constant simply resolves to
nothing and the adapter falls back.

The fix was mechanical: ``Path(__file__).resolve().parents[N]``, which yields
the identical absolute path here and the clone's path anywhere else.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCANNED = ("adaptive_reflow", "tools", "scripts", "reproduce", "tests")
LITERAL = '"/home/hugo/codes/flowa-multistep-reinference"'


def test_no_hardcoded_repo_root() -> None:
    hits = [
        f"{path.relative_to(ROOT)}:{lineno}"
        for top in SCANNED
        for path in (ROOT / top).rglob("*.py")
        if path.is_file() and path.resolve() != Path(__file__).resolve()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if LITERAL in line
    ]
    assert hits == [], hits


def test_library_path_defaults_resolve_inside_the_repo() -> None:
    """A clone-relative default must still land in this checkout."""
    from adaptive_reflow.adapters.flowmol3_upstream_shim import (
        FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR,
        FLOWMOL3_UPSTREAM_REPO,
    )

    for value in (FLOWMOL3_UPSTREAM_REPO, FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR):
        assert Path(value).is_absolute()
        assert Path(value).is_relative_to(ROOT), value
