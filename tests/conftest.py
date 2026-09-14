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

import contextlib
import os
import socket
import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _REPO_ROOT / "data"

# Wave 98.A — disable the GPU utilization watchdog during the test
# suite. The watchdog's background thread invokes nvidia-smi every
# 5 seconds, which collides with tests that mock subprocess.run
# (e.g. test_upstream_eval.py's smoke tests assert ``call_count == 1``
# on the mocked subprocess.run). Tests that exercise the watchdog
# itself (tests/test_tools/test_gpu_watchdog.py) override this via
# monkeypatch and do not rely on real nvidia-smi availability.
os.environ.setdefault("GPU_WATCHDOG_DISABLED", "1")

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
    except (TimeoutError, OSError):
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


# ---------------------------------------------------------------------------
# serial_tool fixture — enforce serial pytest execution
# ---------------------------------------------------------------------------
#
# Background: tests/test_tools/ has 215 tests that each pull in heavy
# framework imports (multiple registry modules, numpy, subprocess CLI
# probes, hypothesis). Running four concurrent pytest processes on
# this rig has been observed to spike each CPU to 9-10 cores — total
# ~40 cores — and trigger thrash that drops pass-rate.
#
# The ``serial_tool`` fixture below enforces a single-writer lockfile
# semantics: the first pytest process to start acquires the lockfile,
# any subsequent pytest process waits on the lockfile until the
# original holder releases it. Only the holder enters the test body;
# waiters block at session start.
#
# Scope: ``session``, autouse=True only when env var ``PYTEST_SERIAL`` is
# set. Default off (opt-in) to keep unrelated test runs unaffected.
# Set ``PYTEST_SERIAL=1`` (or any non-empty value) to enable.
#
# Lockfile path: ``/tmp/pytest_serial.lock`` by default, overridable
# via ``PYTEST_SERIAL_LOCKFILE`` env var.

_PYTEST_SERIAL_LOCKFILE = os.environ.get(
    "PYTEST_SERIAL_LOCKFILE", "/tmp/pytest_serial.lock"
)


@pytest.fixture(scope="session", autouse=True)
def serial_tool() -> None:
    """Hold a process-level lockfile for the entire pytest session.

    Skipped entirely when ``PYTEST_SERIAL`` is unset. When enabled,
    this fixture blocks at session start until the lockfile is free,
    then writes its PID and holds the lockfile until session teardown.
    Concurrent pytest processes serialize on this fixture, capping
    CPU pressure to a single session's worth at a time.
    """
    if not os.environ.get("PYTEST_SERIAL"):
        yield
        return

    lock_path = Path(_PYTEST_SERIAL_LOCKFILE)
    poll_interval = float(os.environ.get("PYTEST_SERIAL_POLL", "1.0"))
    timeout = float(os.environ.get("PYTEST_SERIAL_TIMEOUT", "3600"))

    deadline = time.time() + timeout
    while True:
        try:
            # ``x`` (exclusive create) succeeds iff the file does not exist.
            # Atomic on POSIX; on Windows this would need adjustment but
            # the test rig is Linux-only.
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            os.write(fd, f"{os.getpid()}\n".encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                stale_pid = int(lock_path.read_text().strip() or "0")
            except (OSError, ValueError):
                stale_pid = 0
            if stale_pid and not _pid_alive(stale_pid):
                with contextlib.suppress(OSError):
                    lock_path.unlink()
                continue
            if time.time() > deadline:
                raise RuntimeError(
                    f"serial_tool: lockfile {lock_path} held by PID "
                    f"{stale_pid} after {timeout}s — aborting."
                ) from None
            time.sleep(poll_interval)

    try:
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            lock_path.unlink()


def _pid_alive(pid: int) -> bool:
    """Return True iff ``pid`` corresponds to a live process."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
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


# ---------------------------------------------------------------------------
# Shared fixtures used by tests/test_adapters/ and tests/test_algorithm/
# (Wave 104 P0-B dedup). Centralized here so the autouse weight-materi­alizer
# fires for every test that depends on the canonical 2D FM weights file,
# and so that ``twodim_fm_weights_path`` / ``twodim_fm_eight_gaussians_weights_path``
# have a single definition across both subtrees.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _materialize_twodim_fm_weights() -> None:
    """Ensure ``data/twodim_fm_*.npz`` exist for the test session.

    Session-scoped and autouse so every test in
    ``tests/test_adapters/`` and ``tests/test_algorithm/`` that touches
    the 2D FM adapter sees a populated weights file. The materializer
    is idempotent: when the canonical files are already on disk the
    fixture is a no-op. Previously duplicated in both sub-conftest
    files; unified here in Wave 104 P0-B.
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


__all__ = (
    "requires_network",
    "requires_torch",
    "requires_weights",
    "serial_tool",
)
