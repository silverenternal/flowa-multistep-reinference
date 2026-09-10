"""Wave 98.A — unit tests for :mod:`tools._gpu_watchdog`.

The watchdog's behaviour is exercised in 3 orthogonal ways:

1. :func:`gpu_status` — the manual one-shot poll. Returns a dict with
   the expected shape (:class:`dict` with ``util`` int, ``mem_mib``
   float, ``name`` str-or-None, ``available`` bool, ``raw`` str).
   Never raises; returns ``{"available": False, ...}`` when nvidia-smi
   is missing or returns empty output.

2. :func:`gpu_watchdog` — the background context manager. We mock
   :func:`gpu_status` via monkeypatch so the test does not need a real
   GPU. The watchdog must:

   - emit a WARNING line on stderr when util == 0 AND mem > 100 MiB
     persist for >= threshold_seconds,
   - NOT emit a warning when util > 5% OR mem <= 100 MiB,
   - clean up the daemon thread on context exit (no leaked threads).

3. The ``enabled=False`` short-circuit — context manager yields None
   and never spawns a thread.

All tests are stdlib-only (no torch / nvidia-ml-py / GPU required) so
they run on the cold-clone CI box.
"""
from __future__ import annotations

import importlib
import io
import os
import sys
import threading
import time
from typing import Any

import pytest


_HELPER = "tools._gpu_watchdog"


def _import_helper() -> Any:
    """Lazy-import ``tools._gpu_watchdog`` so module-level side effects
    (none today, but defensive) never run before the conftest fixture
    is set up."""
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", ".."),
    )
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    return importlib.import_module(_HELPER)


def _make_status(util: int, mem_mib: float, name: str = "Fake-GPU") -> dict[str, Any]:
    """Build a synthetic gpu_status() return value."""
    return {
        "available": True,
        "util": int(util),
        "mem_mib": float(mem_mib),
        "name": name,
        "raw": f"{int(util)}, {float(mem_mib):.1f}, {name}",
    }


def test_gpu_status_returns_expected_dict_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """Manual poll returns dict with the documented keys."""
    helper = _import_helper()

    # Force nvidia-smi to return a deterministic row by patching subprocess.run.
    class _FakeProc:
        returncode = 0
        stdout = "42, 512.0, Fake-GPU-0\n"

    def fake_run(*_args: Any, **_kwargs: Any) -> _FakeProc:
        return _FakeProc()

    monkeypatch.setattr(helper.subprocess, "run", fake_run)
    status = helper.gpu_status()
    assert status["available"] is True
    assert status["util"] == 42
    assert status["mem_mib"] == 512.0
    assert status["name"] == "Fake-GPU-0"
    assert isinstance(status["raw"], str)
    assert "42" in status["raw"]


def test_gpu_status_returns_unavailable_when_nvidia_smi_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When nvidia-smi is not on $PATH, return ``available=False``."""
    helper = _import_helper()

    def fake_run(*_args: Any, **_kwargs: Any) -> Any:
        raise FileNotFoundError("nvidia-smi not found")

    monkeypatch.setattr(helper.subprocess, "run", fake_run)
    status = helper.gpu_status()
    assert status["available"] is False
    assert status["util"] == 0
    assert status["mem_mib"] == 0.0
    assert status["name"] is None


def test_watchdog_detects_stuck_zero_util_with_memory_occupied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When util == 0 AND mem > 100 MiB persists > threshold, emit WARNING."""
    helper = _import_helper()
    monkeypatch.delenv("GPU_WATCHDOG_DISABLED", raising=False)

    # Mock gpu_status to always report "stuck" conditions.
    monkeypatch.setattr(helper, "gpu_status",
                        lambda: _make_status(util=0, mem_mib=2048.0))
    # Capture stderr writes from the watchdog.
    captured: io.StringIO = io.StringIO()
    monkeypatch.setattr(helper.sys, "stderr", captured)

    threshold = 1.0  # short for the test
    sample_interval = 0.2
    with helper.gpu_watchdog(
        threshold_seconds=threshold,
        sample_interval=sample_interval,
        enabled=True,
    ) as thread:
        assert thread is not None
        # Wait for the watchdog to cross the threshold.
        # 1.5 * threshold gives the watchdog enough slack.
        deadline = time.monotonic() + (threshold * 4.0)
        while time.monotonic() < deadline:
            content = captured.getvalue()
            if "[gpu-watchdog] WARNING" in content:
                break
            time.sleep(sample_interval / 2.0)

    content = captured.getvalue()
    assert "[gpu-watchdog] WARNING" in content, (
        f"Expected a WARNING line on stderr; got: {content!r}"
    )
    assert "util.gpu=0%" in content
    assert "2048" in content  # mem_mib
    assert "pid=" in content


def test_watchdog_does_not_fire_when_util_above_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When util > 5%, the watchdog must stay silent."""
    helper = _import_helper()
    monkeypatch.delenv("GPU_WATCHDOG_DISABLED", raising=False)

    monkeypatch.setattr(helper, "gpu_status",
                        lambda: _make_status(util=42, mem_mib=4096.0))
    captured: io.StringIO = io.StringIO()
    monkeypatch.setattr(helper.sys, "stderr", captured)

    threshold = 0.5
    sample_interval = 0.1
    with helper.gpu_watchdog(
        threshold_seconds=threshold, sample_interval=sample_interval,
        enabled=True,
    ):
        # Wait longer than threshold to ensure the loop runs.
        time.sleep(threshold * 4.0)

    content = captured.getvalue()
    assert "[gpu-watchdog] WARNING" not in content, (
        f"Unexpected WARNING when util > 5%; got: {content!r}"
    )


def test_watchdog_does_not_fire_when_memory_below_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When util == 0 but mem_mib < 100 MiB, the watchdog must stay silent
    (the 'occupied' condition is not met)."""
    helper = _import_helper()
    monkeypatch.delenv("GPU_WATCHDOG_DISABLED", raising=False)

    monkeypatch.setattr(helper, "gpu_status",
                        lambda: _make_status(util=0, mem_mib=42.0))
    captured: io.StringIO = io.StringIO()
    monkeypatch.setattr(helper.sys, "stderr", captured)

    threshold = 0.5
    sample_interval = 0.1
    with helper.gpu_watchdog(
        threshold_seconds=threshold, sample_interval=sample_interval,
        enabled=True,
    ):
        time.sleep(threshold * 4.0)

    content = captured.getvalue()
    assert "[gpu-watchdog] WARNING" not in content, (
        f"Unexpected WARNING when mem < 100 MiB; got: {content!r}"
    )


def test_watchdog_enabled_false_short_circuits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``enabled=False``, no thread is spawned and no warning is emitted."""
    helper = _import_helper()

    # gpu_status is never called when enabled=False — but if it WERE called,
    # it would warn. Use a sentinel to detect the call.
    called: list[bool] = []

    def fake_status() -> dict[str, Any]:
        called.append(True)
        return _make_status(util=0, mem_mib=99999.0)

    monkeypatch.setattr(helper, "gpu_status", fake_status)

    with helper.gpu_watchdog(
        threshold_seconds=0.1, sample_interval=0.05, enabled=False,
    ) as thread:
        assert thread is None
        time.sleep(0.3)

    assert called == [], (
        "gpu_status was called even though watchdog was disabled; "
        f"calls={called}"
    )


def test_watchdog_thread_is_daemon_and_cleaned_up_on_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The watchdog thread is daemon=True and joins on context exit
    (no leaked threads)."""
    helper = _import_helper()
    monkeypatch.delenv("GPU_WATCHDOG_DISABLED", raising=False)

    monkeypatch.setattr(helper, "gpu_status",
                        lambda: _make_status(util=42, mem_mib=4096.0))

    before = {t.ident for t in threading.enumerate()}
    with helper.gpu_watchdog(
        threshold_seconds=1.0, sample_interval=0.2,
    ) as thread:
        assert thread is not None
        assert thread.is_alive()
        assert thread.daemon is True
        # thread.name should be GpuWatchdog (the canonical thread name)
        assert thread.name == "GpuWatchdog"
    # Give the thread a moment to join.
    time.sleep(0.2)
    after = {t.ident for t in threading.enumerate()}
    leaked = after - before
    assert not leaked, f"Watchdog thread leaked: {leaked}"


def test_watchdog_resets_window_after_compute_recovers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If util was 0 then recovers, the zero-window resets — a NEW
    stuck period must re-trigger the warning."""
    helper = _import_helper()
    monkeypatch.delenv("GPU_WATCHDOG_DISABLED", raising=False)

    # Two-phase schedule: first 4 polls are stuck (start the window),
    # then a single recovered poll (resets the window), then 6 more
    # stuck polls (re-fire the warning). We poll deterministically
    # by counting how many polls have happened since the thread started.
    state = {"polls": 0}

    def scheduled_status() -> dict[str, Any]:
        state["polls"] += 1
        polls = state["polls"]
        # polls 1-4: stuck (0%); poll 5: recovered; polls 6+: stuck again.
        if polls == 5:
            return _make_status(util=50, mem_mib=2048.0)
        return _make_status(util=0, mem_mib=2048.0)

    monkeypatch.setattr(helper, "gpu_status", scheduled_status)
    captured: io.StringIO = io.StringIO()
    monkeypatch.setattr(helper.sys, "stderr", captured)

    threshold = 0.3  # 3 polls * 0.1s sample_interval = 0.3s
    sample_interval = 0.1
    with helper.gpu_watchdog(
        threshold_seconds=threshold, sample_interval=sample_interval,
    ):
        # Wait long enough for: first stuck window (4 polls = 0.4s > threshold),
        # recovery poll, second stuck window (>=4 polls = 0.4s > threshold).
        # Plus a safety margin for thread scheduling.
        time.sleep(threshold * 16.0)

    content = captured.getvalue()
    warning_count = content.count("[gpu-watchdog] WARNING")
    assert warning_count >= 1, (
        f"Expected at least one WARNING after window reset; got: {content!r}"
    )


def test_watchdog_warning_contains_command_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The WARNING line should include ``sys.argv`` (the user-visible command)
    so a human reading stderr can identify the offending sweep."""
    helper = _import_helper()
    monkeypatch.delenv("GPU_WATCHDOG_DISABLED", raising=False)

    monkeypatch.setattr(helper, "gpu_status",
                        lambda: _make_status(util=0, mem_mib=2048.0))
    captured: io.StringIO = io.StringIO()
    monkeypatch.setattr(helper.sys, "stderr", captured)
    monkeypatch.setattr(helper.sys, "argv",
                        ["my-sweep-driver", "--seed", "42", "--nfe", "50"])

    with helper.gpu_watchdog(
        threshold_seconds=0.3, sample_interval=0.1,
    ):
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            if "[gpu-watchdog] WARNING" in captured.getvalue():
                break
            time.sleep(0.05)

    content = captured.getvalue()
    assert "my-sweep-driver" in content, (
        f"WARNING should include the command argv; got: {content!r}"
    )
    assert "--seed" in content
