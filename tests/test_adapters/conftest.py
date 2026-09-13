"""Test fixtures shared by ``tests/test_adapters/``.

The :class:`TwoDimFMAdapter` runtime loads its velocity-field ``.npz``
from a canonical path under ``data/``. Tests rely on the file existing
at session start; the autouse materializer fixture is centralized in
the top-level ``tests/conftest.py`` (Wave 104 P0-B dedup) so it fires
once for the entire session regardless of which subtree imports it.
The :func:`_probe_mnist_mirror` helper is also centralized there.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# Re-export the dedup'd fixtures from the top-level conftest so test
# files that import them via ``tests.test_adapters.conftest`` continue
# to resolve. Wave 104 P0-B unification.
from tests.conftest import (  # noqa: F401 — re-export
    _materialize_twodim_fm_weights,
    _probe_mnist_mirror,
    twodim_fm_eight_gaussians_weights_path,
    twodim_fm_weights_path,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Canonical vendored MNIST cache (P-09). When present, the offline
# loader resolves MNIST without hitting the live mirror.
_MNIST_OFFLINE_CACHE_DIR = _REPO_ROOT / "data" / "mnist_fm_train_cache"
_MNIST_TRAIN_IMAGES_GZ = (
    _MNIST_OFFLINE_CACHE_DIR / "MNIST" / "raw" / "train-images-idx3-ubyte.gz"
)


@pytest.fixture(scope="session")
def mnist_train_smoke_skip_guard() -> bool:
    """Skip-guard flag for :func:`test_train_smoke_decreases_loss`.

    Returns ``True`` when the smoke test should be skipped: namely
    when *neither* the vendored offline cache nor the live mirror is
    reachable. Returns ``False`` when at least one path can serve
    the data, in which case the test proceeds (it falls back to a
    live download when the cache is missing).

    The probe is intentionally cheap (single TCP connect with a
    2-second timeout) so it adds negligible overhead to the suite.
    """
    if _MNIST_TRAIN_IMAGES_GZ.exists():
        return False
    if _probe_mnist_mirror():
        return False
    return True


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


__all__ = (
    "_probe_mnist_mirror",
    "_materialize_twodim_fm_weights",
    "twodim_fm_weights_path",
    "twodim_fm_eight_gaussians_weights_path",
    "mnist_train_smoke_skip_guard",
    "mnist_fm_weights_path",
)
