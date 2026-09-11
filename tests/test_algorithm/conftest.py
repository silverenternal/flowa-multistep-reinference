"""Test fixtures shared by ``tests/test_algorithm/``.

The :class:`TwoDimFMAdapter` runtime loads its velocity-field ``.npz``
from a canonical path under ``data/``. Tests in this directory that
exercise the adapter via :class:`ReInferenceRunner` rely on the file
existing at session start; the autouse materializer fixture is
centralized in the top-level ``tests/conftest.py`` (Wave 104 P0-B
dedup) so it fires once for the entire session regardless of which
subtree imports it.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Re-export the dedup'd fixtures from the top-level conftest so test
# files in this subtree continue to resolve them. Wave 104 P0-B
# unification.
from tests.conftest import (  # noqa: F401 — re-export
    _materialize_twodim_fm_weights,
    twodim_fm_weights_path,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


__all__ = (
    "_materialize_twodim_fm_weights",
    "twodim_fm_weights_path",
)
