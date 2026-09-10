"""Wave 98.A — GPU utilization watchdog (0% compute + memory occupied).

OWNER: Wave 98 Agent A — diagnostic that should have caught the Wave 96.E
stuck-process scenario. When a sweep driver is running on GPU but compute
stays at 0% for >30s while VRAM is occupied, write a WARNING line to
stderr so the user can intervene.

Public surface
--------------

* :func:`gpu_status` — manual poll. Returns ``dict[str, Any]`` with
  ``util`` (0-100), ``mem_mib`` (float, MiB), ``name`` (str | None),
  ``available`` (bool — False if nvidia-smi is missing / empty).
* :func:`gpu_watchdog` — context manager. Spawns a daemon thread that
  polls every ``sample_interval`` seconds (default 5s). If
  ``util == 0`` is observed continuously for >= ``threshold_seconds``
  (default 30s) AND ``mem_mib > 100``, write a WARNING to stderr with
  timestamp, process pid, GPU util, memory used, and the command line.

Implementation notes
--------------------

* ``nvidia-smi`` is invoked via :mod:`subprocess` with a short timeout
  (~2s). If nvidia-smi is missing or returns non-JSON / no rows, the
  watchdog silently no-ops (no spam).
* The watchdog thread is ``daemon=True`` so it dies with the parent
  process — no orphaned GPU pollers.
* The thread uses an :class:`threading.Event` for cooperative
  shutdown so the test suite can deterministically exercise it.
* Stdlib-only (no torch / numpy / nvidia-ml-py) so the helper is
  cold-clone safe + CI-friendly.
"""
from __future__ import annotations

import contextlib
import json
import os
import shlex
import subprocess
import sys
import threading
import time
from typing import Any, Iterator


_NVSMI_QUERY = (
    "--query-gpu=utilization.gpu,memory.used,name"
    " --format=csv,noheader,nounits"
)

# Default memory-occupied threshold (MiB). Below this, no warning —
# the process is either not on the GPU or has already released VRAM.
DEFAULT_MEM_THRESHOLD_MIB = 100.0

# Environment variable that disables the watchdog entirely. Useful
# for tests (so the watchdog doesn't interfere with subprocess mocks)
# and for users who prefer a quieter stderr.
_DISABLE_ENV_VAR = "GPU_WATCHDOG_DISABLED"


def gpu_status() -> dict[str, Any]:
    """Manual one-shot GPU poll. Returns::

        {
            "util": int,           # 0-100 (gpu util percentage)
            "mem_mib": float,      # memory.used in MiB
            "name": str | None,    # gpu name (or None if unavailable)
            "available": bool,     # False if nvidia-smi missing / no rows
            "raw": str,            # raw stdout (last line)
        }

    Never raises. If ``nvidia-smi`` is missing or returns empty / non-JSON,
    returns ``{"available": False, ...}``.
    """
    try:
        proc = subprocess.run(
            ["nvidia-smi", *_NVSMI_QUERY.split()],
            capture_output=True, text=True, timeout=2.0,
        )
    except BaseException:  # noqa: BLE001 — must NEVER raise from the watchdog
        # Catch everything (BaseException) so the watchdog's background
        # thread is immune to test mocks + pathological nvidia-smi crashes.
        return {"available": False, "util": 0, "mem_mib": 0.0,
                "name": None, "raw": ""}
    out = (proc.stdout or "").strip()
    if proc.returncode != 0 or not out:
        return {"available": False, "util": 0, "mem_mib": 0.0,
                "name": None, "raw": out}
    # Take the first GPU's row (multi-GPU boxes are rare for sweep drivers).
    first = out.splitlines()[0]
    parts = [p.strip() for p in first.split(",")]
    try:
        util = int(parts[0]) if len(parts) >= 1 else 0
        mem_mib = float(parts[1]) if len(parts) >= 2 else 0.0
        name = parts[2] if len(parts) >= 3 else None
    except (ValueError, IndexError):
        return {"available": False, "util": 0, "mem_mib": 0.0,
                "name": None, "raw": first}
    return {"available": True, "util": util, "mem_mib": mem_mib,
            "name": name, "raw": first}


class _WatchdogThread(threading.Thread):
    """Background poll thread. Daemon — dies with parent."""

    def __init__(
        self,
        threshold_seconds: float,
        sample_interval: float,
        mem_threshold_mib: float,
        stop_event: threading.Event,
        warn_sink: Any | None = None,
    ) -> None:
        super().__init__(name="GpuWatchdog", daemon=True)
        self.threshold_seconds = float(threshold_seconds)
        self.sample_interval = float(sample_interval)
        self.mem_threshold_mib = float(mem_threshold_mib)
        self.stop_event = stop_event
        # ``warn_sink=None`` means "look up ``sys.stderr`` at print time"
        # (lazy binding — so the test suite can monkeypatch stderr AFTER
        # the thread is constructed).
        self.warn_sink = warn_sink
        self._zero_started_at: float | None = None
        self._warned: bool = False  # one warning per stuck window
        # Once we determine the host has no nvidia-smi (or the call is
        # unavailable), short-circuit subsequent polls to avoid spamming
        # subprocess invocations on non-GPU hosts.
        self._disabled_due_to_unavailable: bool = False

    def _warn(self, status: dict[str, Any]) -> None:
        ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        cmd = " ".join(shlex.quote(c) for c in sys.argv) or "<no argv>"
        sink = self.warn_sink if self.warn_sink is not None else sys.stderr
        print(
            f"[gpu-watchdog] WARNING @ {ts}Z pid={os.getpid()} "
            f"util.gpu={status['util']}% mem.used={status['mem_mib']:.0f} MiB "
            f"threshold_s={self.threshold_seconds:.0f} "
            f"name={status.get('name')!r} cmd={cmd}",
            file=sink, flush=True,
        )

    def run(self) -> None:
        # Initial sample so we don't warn on a transient startup pause.
        last_status = gpu_status()
        if not last_status["available"]:
            self._disabled_due_to_unavailable = True
            return  # no GPU on this host — no further polls
        while not self.stop_event.is_set():
            if self.stop_event.wait(self.sample_interval):
                break
            if self._disabled_due_to_unavailable:
                return
            status = gpu_status()
            if not status["available"]:
                self._disabled_due_to_unavailable = True
                return
            stuck = (
                status["available"]
                and status["util"] == 0
                and status["mem_mib"] > self.mem_threshold_mib
            )
            if stuck:
                if self._zero_started_at is None:
                    self._zero_started_at = time.monotonic()
                elif (
                    not self._warned
                    and (time.monotonic() - self._zero_started_at)
                    >= self.threshold_seconds
                ):
                    self._warn(status)
                    self._warned = True
            else:
                # Compute recovered or VRAM released — reset the window.
                self._zero_started_at = None
                self._warned = False
            last_status = status


@contextlib.contextmanager
def gpu_watchdog(
    threshold_seconds: float = 30.0,
    sample_interval: float = 5.0,
    mem_threshold_mib: float = DEFAULT_MEM_THRESHOLD_MIB,
    enabled: bool = True,
) -> Iterator[_WatchdogThread | None]:
    """Context manager — spawns a background GPU util watchdog.

    Usage::

        from tools._gpu_watchdog import gpu_watchdog

        with gpu_watchdog(threshold_seconds=30, sample_interval=5):
            # ... do GPU work ...
            ...

    Args:
        threshold_seconds: How long ``util.gpu == 0`` must persist
            (while ``mem > mem_threshold_mib``) before warning.
        sample_interval: Seconds between polls.
        mem_threshold_mib: Memory floor for "occupied" (default 100 MiB).
            Below this, no warning is emitted even if util == 0.
        enabled: Set False to short-circuit (e.g., for unit tests or
            non-GPU hosts). The context manager yields ``None``.

    Yields:
        The watchdog thread (or ``None`` when ``enabled=False``) so the
        caller can introspect it (e.g., for tests). The thread is
        always stopped + joined on context exit.

    Notes
    -----
    Setting the ``GPU_WATCHDOG_DISABLED=1`` env var also short-circuits
    the watchdog (useful for tests that mock ``subprocess.run`` — the
    watchdog would otherwise consume mock calls and confuse assertions).
    """
    if not enabled or os.environ.get(_DISABLE_ENV_VAR) == "1":
        yield None
        return
    stop_event = threading.Event()
    thread = _WatchdogThread(
        threshold_seconds=threshold_seconds,
        sample_interval=sample_interval,
        mem_threshold_mib=mem_threshold_mib,
        stop_event=stop_event,
    )
    thread.start()
    try:
        yield thread
    finally:
        stop_event.set()
        # Give the thread up to 2 sample-intervals to exit cleanly.
        thread.join(timeout=max(2.0 * sample_interval, 1.0))


__all__ = [
    "DEFAULT_MEM_THRESHOLD_MIB",
    "gpu_status",
    "gpu_watchdog",
]
