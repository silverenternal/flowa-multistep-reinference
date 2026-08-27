"""Test fixtures shared by ``tests/test_algorithm/``.

The :class:`TwoDimFMAdapter` runtime loads its velocity-field ``.npz``
from a canonical path under ``data/``. Tests in this directory that
exercise the adapter via :class:`ReInferenceRunner` rely on the file
existing at session start; this conftest materializes it (with a
deliberately small step budget) on demand so the suite is hermetic
when the materialized data is missing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture(scope="session", autouse=True)
def _materialize_twodim_fm_weights() -> None:
    """Ensure ``data/twodim_fm_*.npz`` exist for the test session."""
    from tools.materialize_twodim_fm import ensure_canonical_files

    ensure_canonical_files(steps=300)


@pytest.fixture(scope="session")
def twodim_fm_weights_path() -> Path:
    """Return the canonical ``data/twodim_fm_two_moons.npz`` path."""
    return _REPO_ROOT / "data" / "twodim_fm_two_moons.npz"


__all__ = ()
