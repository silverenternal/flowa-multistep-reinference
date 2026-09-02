"""Test-only path setup so the adaptive_reflow package resolves.

The package is at the repo root (``adaptive_reflow/``) and pytest must
be able to import it as ``adaptive_reflow``. We also walk up parent
directories looking for a ``pocket_modules`` package root so the legacy
torch-bound tests can resolve their ``pocket_modules`` ancestors when
they run; the legacy tests are gated on the ancestor walk succeeding
via the ``legacy`` marker.

Preflight skip fixtures
-----------------------

Three session-scoped fixtures gate tests that require resources the
sandbox may not have:

* :func:`requires_torch` — skip if the ``torch`` package is not
  importable. CPU-only sandboxes (the default for CI on this rig)
  typically lack torch, diffusers, transformers, and accelerate.
* :func:`requires_weights` — skip if no vendored SOTA weights are
  present under ``data/``. Weights are *not* vendored by default
  to keep the repo light; CI workflows that exercise real-weight
  smoke tests gate on this fixture.
* :func:`requires_network` — skip if the canonical MNIST mirror
  host ``ossci-datasets.s3.amazonaws.com`` cannot be reached on
  port 443 within a 2-second TCP timeout. Mirrors the P-09 probe
  pattern in :mod:`tests.test_adapters.conftest`.

These fixtures are *additive*: a test that does not opt in via
``@pytest.mark.usefixtures("requires_torch")`` (or the equivalent
``skipif`` marker that consults the fixture) keeps its original
behavior. Tests that *do* opt in turn from a hard error / setup
failure into a clean SKIPPED report so the rest of the suite can
run on offline, CPU-only, weight-free sandboxes.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _REPO_ROOT / "data"
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


# ---------------------------------------------------------------------------
# Preflight probes
# ---------------------------------------------------------------------------


def _probe_mnist_mirror(
    *,
    host: str = "ossci-datasets.s3.amazonaws.com",
    port: int = 443,
    timeout: float = 2.0,
) -> bool:
    """Quick socket-level probe of the MNIST mirror.

    Returns ``True`` when the host accepts a TCP connection within
    ``timeout`` seconds, ``False`` otherwise. Used by
    :func:`requires_network` to short-circuit test runs in offline
    sandboxes before attempting any download. Mirrors the P-09
    pattern in :mod:`tests.test_adapters.conftest`.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.close()
        return True
    except (OSError, socket.timeout):
        return False


def _has_torch() -> bool:
    """Return ``True`` iff ``torch`` is importable in this interpreter.

    The check is a one-shot ``importlib.util.find_spec`` — does not
    import torch, which keeps the suite fast on weight-free sandboxes
    where torch is not vendored.
    """
    try:
        import importlib.util

        return importlib.util.find_spec("torch") is not None
    except (ImportError, ValueError):
        return False


def _has_vendored_weights() -> bool:
    """Return ``True`` iff at least one SOTA weights tree is vendored.

    We check for the canonical ``weights_real/`` directories under
    each adapter's data dir. If *any* of them exists, we treat the
    rig as "weights available" and let ``requires_weights`` opt-in
    tests run. If *none* exist (the default state of a fresh clone),
    those tests skip with a clear reason string.
    """
    candidate_dirs = (
        _DATA_DIR / "lumina_image_2_0" / "weights_real",
        _DATA_DIR / "hidream_i1" / "weights_real",
        _DATA_DIR / "hidream_i1" / "weights_dev",
        _DATA_DIR / "flowmol3" / "weights_real",
        _DATA_DIR / "protbfn_abbfn" / "weights_real",
    )
    return any(p.is_dir() for p in candidate_dirs)


# ---------------------------------------------------------------------------
# Preflight skip fixtures (session-scoped, autouse=False — tests opt in)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def requires_torch() -> bool:
    """Skip the calling test unless ``torch`` is importable.

    Usage::

        @pytest.mark.usefixtures("requires_torch")
        def test_torch_dependent_thing():
            import torch
            ...

    The fixture returns ``True`` when torch is present (so tests
    that want to assert "skip means no-torch" can use it as a
    sentinel) and calls :func:`pytest.skip` with a clear reason
    string otherwise.
    """
    if not _has_torch():
        pytest.skip(
            "torch not in venv "
            "(install via `uv pip install torch torchvision "
            "diffusers transformers accelerate`)"
        )
    return True


@pytest.fixture(scope="session")
def requires_weights() -> bool:
    """Skip the calling test unless vendored SOTA weights are present.

    Usage::

        @pytest.mark.usefixtures("requires_weights")
        def test_real_weight_smoke():
            ...

    The probe checks for ``data/<adapter>/weights_real`` (and the
    ``weights_dev`` variant for HiDream) directories. When none
    exist the test skips with a reason that points at the
    canonical download scripts.
    """
    if not _has_vendored_weights():
        pytest.skip(
            "no vendored SOTA weights under data/ "
            "(install via tools/fetch_*_weights.py per ADR-0003)"
        )
    return True


@pytest.fixture(scope="session")
def requires_network() -> bool:
    """Skip the calling test unless ``ossci-datasets.s3.amazonaws.com`` is reachable.

    Usage::

        @pytest.mark.usefixtures("requires_network")
        def test_live_download_smoke():
            ...

    A 2-second TCP connect probe is enough to distinguish a working
    link from a fully offline sandbox without adding measurable
    overhead to the suite. Mirrors :func:`_probe_mnist_mirror` in
    :mod:`tests.test_adapters.conftest` so the gating semantics are
    identical.
    """
    if not _probe_mnist_mirror():
        pytest.skip(
            "no network: ossci-datasets.s3.amazonaws.com unreachable "
            "on port 443 within 2s"
        )
    return True


__all__ = (
    "requires_network",
    "requires_torch",
    "requires_weights",
)
