"""Test fixtures shared by ``tests/test_adapters/``.

The :class:`TwoDimFMAdapter` runtime loads its velocity-field ``.npz``
from a canonical path under ``data/``. Tests rely on the file existing
at session start; this conftest materializes it (with a deliberately
small step budget) on demand so the suite is hermetic when the
materialized data is missing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture(scope="session", autouse=True)
def _materialize_twodim_fm_weights() -> None:
    """Ensure ``data/twodim_fm_two_moons.npz`` exists for the test session.

    The fixture is session-scoped and autouse so every test in
    ``tests/test_adapters/`` that touches the 2D FM adapter sees a
    populated weights file. The materializer is idempotent: when the
    canonical file is already on disk the fixture is a no-op.
    """
    from tools.materialize_twodim_fm import ensure_canonical_files

    ensure_canonical_files(steps=300)


@pytest.fixture(scope="session")
def twodim_fm_weights_path() -> Path:
    """Return the canonical ``data/twodim_fm_two_moons.npz`` path."""
    return _REPO_ROOT / "data" / "twodim_fm_two_moons.npz"


@pytest.fixture(scope="session")
def twodim_fm_eight_gaussians_weights_path() -> Path:
    """Return the canonical ``data/twodim_fm_eight_gaussians.npz`` path."""
    return _REPO_ROOT / "data" / "twodim_fm_eight_gaussians.npz"


@pytest.fixture(scope="session")
def mnist_fm_weights_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create deterministic MNIST adapter weights without training a model."""
    from adaptive_reflow.adapters.mnist_fm_train import (
        save_weights,
        velocity_field_unet_init,
    )

    path = tmp_path_factory.mktemp("mnist_fm") / "mnist_fm_test.npz"
    weights = velocity_field_unet_init(
        np.random.default_rng(0), base_channels=8
    )
    return save_weights(list(weights), path)


__all__ = ()
