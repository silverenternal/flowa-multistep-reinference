"""Process bridge from the framework to the Python 3.11 FlowMol3 sidecar.

Architecture
------------

The framework at the project's pinned Python 3.12 venv cannot import
``flowmol`` directly because:

* ``dgl`` has no Python 3.12 wheel.
* the upstream ``flowmol`` ``pyproject.toml`` pins
  ``requires-python = ">=3.10,<3.11"``.

The bridge launches a long-running subprocess inside the sidecar venv at
``/home/hugo/.venv-flowmol311`` that exposes the published
``CTMCVectorField.integrate`` result over a tiny JSON-line protocol on
stdin/stdout. The framework stays on its native Python 3.12; the
sidecar owns the real FlowMol3 forward pass.

Wire protocol (one JSON object per line, LF-terminated, UTF-8)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Client -> server (``{"cmd": "init", ...}``)``::

    {"cmd": "init",
     "weights_path": "<absolute path to last.ckpt>",
     "device": "cpu",
     "config_yaml": "<optional absolute path> or null",
     "n_timesteps": 1}

Server -> client::

    {"status": "ready",
     "epoch": <int>, "global_step": <int>,
     "atom_map": [...], "dataset_name": "...",
     "ctmc": true,
     "parameterization": "ctmc"}

Client -> server (``{"cmd": "denoise", ...}``)``::

    {"cmd": "denoise",
     "x": [[...]],            # (n_atoms, 3) float64, in Angstrom
     "a": [...],              # (n_atoms,) int64 in [0, FLOWMOL3ADAPTER_N_ATOM_TYPES)
     "c": [...],              # (n_atoms,) float64 formal charges
     "e": [[...]],            # (n_atoms, n_atoms) int64 bond labels
     "t": 0.5,                # normalized time in [0, 1)
     "n_timesteps": 1}        # optional override; defaults to init value

Server -> client::

    {"status": "ok",
     "x_out": [[...]], "a_out": [...], "c_out": [...], "e_out": [[...]]}

Errors are returned as ``{"status": "error", "code": "...", "message": "..."}``
with the process kept alive. A non-recoverable fatal error (model load
failure) terminates the process with a non-zero exit code; the client
sees an ``EOFError`` on ``readline`` and surfaces it.

The protocol is intentionally minimal so the sidecar can be driven from
a shell or a notebook without dragging in the framework.
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

#: Absolute path to the Python 3.11 sidecar venv. Override at runtime
#: via the ``FLOWMOL3_SIDECAR_VENV`` environment variable (the harness
#: sets it for CI). The path is intentionally not hard-coded into the
#: test suite so the unit tests stay hermetic.
DEFAULT_SIDECAR_VENV: str = "/home/hugo/.venv-flowmol311"

#: Default Python binary inside the sidecar venv.
DEFAULT_SIDECAR_PYTHON: str = os.path.join(DEFAULT_SIDECAR_VENV, "bin", "python")

#: Default sidecar server script (relative to the project root).
DEFAULT_SIDECAR_SCRIPT: str = "tools/flowmol3_sidecar_server.py"

#: How long to wait (seconds) for the sidecar to emit ``{"status": "ready"}``.
DEFAULT_STARTUP_TIMEOUT_S: float = 600.0

#: How long to wait (seconds) for a single ``denoise`` response.
DEFAULT_DENOISE_TIMEOUT_S: float = 60.0


@dataclass
class _SidecarConfig:
    """Resolved sidecar launch configuration."""

    python: str
    server_script: str
    project_root: str


def _resolve_config(
    *,
    venv: str | None,
    python: str | None,
    server_script: str | None,
    project_root: str | None,
) -> _SidecarConfig:
    """Resolve the launch configuration, honoring env-var overrides."""
    if python is None:
        env_venv = os.environ.get("FLOWMOL3_SIDECAR_PYTHON")
        if env_venv:
            python = env_venv
        else:
            venv_path = venv if venv is not None else os.environ.get(
                "FLOWMOL3_SIDECAR_VENV", DEFAULT_SIDECAR_VENV
            )
            python = os.path.join(venv_path, "bin", "python")
    if server_script is None:
        server_script = os.environ.get(
            "FLOWMOL3_SIDECAR_SCRIPT", DEFAULT_SIDECAR_SCRIPT
        )
    if project_root is None:
        project_root = os.environ.get(
            "FLOWMOL3_PROJECT_ROOT",
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
        )
    return _SidecarConfig(
        python=str(python),
        server_script=str(server_script),
        project_root=str(project_root),
    )


class FlowMol3SidecarError(RuntimeError):
    """Raised when the sidecar returns an error frame or fails to launch."""


class FlowMol3SidecarProcess:
    """Long-running Python 3.11 subprocess hosting the FlowMol3 forward.

    The bridge is intentionally synchronous and blocking — one
    ``denoise`` request at a time. The :class:`FlowMol3V2Adapter` calls
    :meth:`denoise` from its main thread inside the ODE loop, so any
    concurrency here would only complicate the reader thread without
    buying throughput.

    Parameters
    ----------
    weights_path : str
        Absolute path to the FlowMol3 Lightning ``last.ckpt``.
    device : str
        ``"cpu"`` (CPU GVP forward is ~1 s / sample at 6 GVP layers /
        3 + 3 message + update; well below the 8.6 s smoke wall clock)
        or ``"cuda:0"`` etc.
    config_yaml : str | None
        Optional absolute path to the ``config.yaml`` next to the
        checkpoint. If ``None``, the sidecar uses the upstream
        FlowMol3 default config (overridable by env var
        ``FLOWMOL3_CONFIG_YAML``).
    n_timesteps : int
        Number of integration steps per ``denoise`` call (default 1;
        the framework integrates externally over ``[0, 1]`` with
        ``num_steps=100`` and only needs the endpoint prediction).
    venv, python, server_script, project_root
        Optional overrides; see :func:`_resolve_config` for env-var
        precedence.
    startup_timeout_s, denoise_timeout_s
        Wall-clock budgets before the bridge gives up and raises
        :class:`FlowMol3SidecarError`.

    Notes
    -----
    The sidecar is a single-process, single-threaded server. A single
    ``denoise`` request fully occupies the GVP forward; concurrent
    requests would only serialize on the underlying GIL.
    """

    def __init__(
        self,
        weights_path: str,
        *,
        device: str = "cpu",
        config_yaml: str | None = None,
        n_timesteps: int = 1,
        venv: str | None = None,
        python: str | None = None,
        server_script: str | None = None,
        project_root: str | None = None,
        startup_timeout_s: float = DEFAULT_STARTUP_TIMEOUT_S,
        denoise_timeout_s: float = DEFAULT_DENOISE_TIMEOUT_S,
    ) -> None:
        if not weights_path:
            raise ValueError("weights_path_required")
        if int(n_timesteps) <= 0:
            raise ValueError("n_timesteps_must_be_positive")
        self._weights_path = str(weights_path)
        self._device = str(device)
        self._config_yaml = (
            str(config_yaml) if config_yaml is not None else os.environ.get(
                "FLOWMOL3_CONFIG_YAML", ""
            ) or None
        )
        self._n_timesteps = int(n_timesteps)
        self._startup_timeout_s = float(startup_timeout_s)
        self._denoise_timeout_s = float(denoise_timeout_s)
        cfg = _resolve_config(
            venv=venv,
            python=python,
            server_script=server_script,
            project_root=project_root,
        )
        self._cfg = cfg
        self._proc: subprocess.Popen[Any] | None = None
        self._reader_lock = threading.Lock()
        # Background stderr drain (prevents the child from blocking on
        # stderr-full). Populated on start; joined on close().
        self._stderr_thread: threading.Thread | None = None
        self._stderr_chunks: list[str] = []
        # Echoed back by the server on the ready frame; cached for tests
        # and diagnostics.
        self._server_info: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> dict[str, Any]:
        """Launch the sidecar and wait for ``{"status": "ready"}``."""
        if self._proc is not None:
            raise FlowMol3SidecarError("sidecar_already_started")
        if not os.path.exists(self._cfg.python):
            raise FlowMol3SidecarError(
                f"sidecar_python_not_found:{self._cfg.python}"
            )
        if not os.path.exists(self._cfg.server_script):
            raise FlowMol3SidecarError(
                f"sidecar_script_not_found:{self._cfg.server_script}"
            )
        # ``-u`` = unbuffered stdio. ``PYTHONUNBUFFERED=1`` is belt-and-
        # suspenders; the sidecar relies on line-buffered stdout for the
        # JSON-line protocol.
        env = dict(os.environ)
        env.setdefault("PYTHONUNBUFFERED", "1")
        env.setdefault("FLOWMOL3_PROJECT_ROOT", self._cfg.project_root)
        cmd = [
            self._cfg.python,
            "-u",
            self._cfg.server_script,
            "--weights",
            self._weights_path,
            "--device",
            self._device,
            "--n-timesteps",
            str(self._n_timesteps),
        ]
        if self._config_yaml is not None:
            cmd.extend(["--config-yaml", self._config_yaml])
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self._cfg.project_root,
                env=env,
                text=True,
                bufsize=1,  # line-buffered
            )
        except OSError as exc:
            raise FlowMol3SidecarError(
                f"sidecar_spawn_failed:{exc.__class__.__name__}:{exc}"
            ) from exc
        # Background stderr drain (prevents the child from blocking on
        # a full pipe). The thread appends lines to ``_stderr_chunks``
        # and silently terminates when EOF is reached.
        assert self._proc.stderr is not None
        self._stderr_thread = threading.Thread(
            target=_drain_stderr,
            args=(self._proc.stderr, self._stderr_chunks),
            daemon=True,
            name="flowmol3-sidecar-stderr",
        )
        self._stderr_thread.start()
        # The server emits its ``ready`` frame automatically right after
        # the model finishes loading, *before* it reads the first
        # command. So the bridge just waits for that first line; it
        # does NOT send an ``init`` of its own (the server treats
        # ``init`` as a no-op and emits a second ``ready`` in response,
        # which would then race with the first ``denoise`` reply).
        try:
            ready = self._recv(timeout_s=self._startup_timeout_s)
        except Exception:
            self.close()
            raise
        if ready.get("status") != "ready":
            self.close()
            raise FlowMol3SidecarError(
                f"sidecar_init_failed:{json.dumps(ready)[:512]}"
            )
        self._server_info = dict(ready)
        return dict(ready)

    def close(self) -> None:
        """Terminate the sidecar (idempotent). Drains stderr first."""
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        # Politely ask the server to shut down. We don't block on the
        # ``shutdown`` reply because the server may already be in an
        # error state.
        try:
            if proc.stdin is not None and proc.poll() is None:
                try:
                    proc.stdin.write(
                        json.dumps({"cmd": "shutdown"}) + "\n"
                    )
                    proc.stdin.flush()
                except (BrokenPipeError, OSError):
                    pass
        finally:
            if proc.poll() is None:
                with contextlib.suppress(OSError):
                    proc.terminate()
                try:
                    proc.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    with contextlib.suppress(subprocess.TimeoutExpired):
                        proc.wait(timeout=2.0)
            if proc.stdout is not None:
                with contextlib.suppress(OSError):
                    proc.stdout.close()
            if proc.stderr is not None:
                with contextlib.suppress(OSError):
                    proc.stderr.close()
            if proc.stdin is not None:
                with contextlib.suppress(OSError):
                    proc.stdin.close()

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __enter__(self) -> FlowMol3SidecarProcess:
        self.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def __del__(self) -> None:
        # Best-effort cleanup if the user forgot to ``close()``.
        with contextlib.suppress(Exception):
            self.close()

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def server_info(self) -> dict[str, Any]:
        """Snapshot of the ``{"status": "ready"}`` frame."""
        return dict(self._server_info)

    @property
    def stderr_tail(self) -> str:
        """Tail of the sidecar's stderr (debug aid; empty if no output)."""
        return "".join(self._stderr_chunks)[-4096:]

    # ------------------------------------------------------------------
    # Core IPC
    # ------------------------------------------------------------------

    def denoise(
        self,
        x: np.ndarray,
        a: np.ndarray,
        c: np.ndarray,
        e: np.ndarray,
        t: float,
        *,
        n_timesteps: int | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Run a single ``denoise`` round trip; return ``(x_out, a_out, c_out, e_out)``.

        Parameters
        ----------
        x : ``(n_atoms, 3)`` float64
            Current per-atom positions in Angstrom.
        a : ``(n_atoms,)`` int64
            Current per-atom type labels (in
            ``[0, FLOWMOL3ADAPTER_N_ATOM_TYPES)``).
        c : ``(n_atoms,)`` float64
            Current per-atom formal charges.
        e : ``(n_atoms, n_atoms)`` int64
            Current pairwise bond labels (in
            ``[0, FLOWMOL3ADAPTER_N_BOND_TYPES)``).
        t : float
            Normalized time in ``[0, 1)`` (informational; the sidecar
            treats the call as an unconditional denoise, the framework
            applies the flow-matching velocity transform externally).
        n_timesteps : int | None
            Optional override for the number of integration steps; if
            ``None`` the sidecar uses its init value.

        Returns
        -------
        x_out, a_out, c_out, e_out : np.ndarray
            Endpoint predictions with the same shapes as the inputs.
        """
        if self._proc is None:
            raise FlowMol3SidecarError("sidecar_not_started")
        if self._proc.poll() is not None:
            raise FlowMol3SidecarError(
                f"sidecar_exited:rc={self._proc.returncode}"
            )
        x_arr = np.asarray(x, dtype=np.float64)
        a_arr = np.asarray(a, dtype=np.int64)
        c_arr = np.asarray(c, dtype=np.float64)
        e_arr = np.asarray(e, dtype=np.int64)
        if x_arr.ndim != 2 or x_arr.shape[-1] != 3:
            raise ValueError(f"x_shape_invalid:{x_arr.shape}")
        n_atoms = int(x_arr.shape[0])
        if a_arr.shape != (n_atoms,):
            raise ValueError(f"a_shape_invalid:{a_arr.shape}")
        if c_arr.shape != (n_atoms,):
            raise ValueError(f"c_shape_invalid:{c_arr.shape}")
        if e_arr.shape != (n_atoms, n_atoms):
            raise ValueError(f"e_shape_invalid:{e_arr.shape}")
        payload: dict[str, Any] = {
            "cmd": "denoise",
            "x": x_arr.tolist(),
            "a": a_arr.tolist(),
            "c": c_arr.tolist(),
            "e": e_arr.tolist(),
            "t": float(t),
        }
        if n_timesteps is not None:
            payload["n_timesteps"] = int(n_timesteps)
        reply = self._send_recv(payload)
        if reply.get("status") != "ok":
            code = reply.get("code", "sidecar_error")
            message = reply.get("message", "unknown error")
            raise FlowMol3SidecarError(f"{code}:{message}")
        try:
            x_out = np.asarray(reply["x_out"], dtype=np.float64).reshape(n_atoms, 3)
            a_out = np.asarray(reply["a_out"], dtype=np.int64).reshape(n_atoms)
            c_out = np.asarray(reply["c_out"], dtype=np.float64).reshape(n_atoms)
            e_out = np.asarray(reply["e_out"], dtype=np.int64).reshape(
                n_atoms, n_atoms
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise FlowMol3SidecarError(
                f"sidecar_reply_malformed:{exc.__class__.__name__}:{exc}"
            ) from exc
        return x_out, a_out, c_out, e_out

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send(self, payload: dict[str, Any]) -> None:
        assert self._proc is not None
        assert self._proc.stdin is not None
        line = json.dumps(payload) + "\n"
        try:
            self._proc.stdin.write(line)
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise FlowMol3SidecarError(
                f"sidecar_stdin_broken:{exc.__class__.__name__}"
            ) from exc

    def _recv(self, timeout_s: float) -> dict[str, Any]:
        assert self._proc is not None
        assert self._proc.stdout is not None
        line = _readline_with_timeout(self._proc.stdout, timeout_s)
        if line is None:
            stderr_tail = self.stderr_tail
            rc = self._proc.poll()
            raise FlowMol3SidecarError(
                f"sidecar_eof_or_timeout:rc={rc}:stderr_tail={stderr_tail[:200]!r}"
            )
        try:
            return json.loads(line)
        except json.JSONDecodeError as exc:
            raise FlowMol3SidecarError(
                f"sidecar_reply_invalid_json:{exc}:line={line[:200]!r}"
            ) from exc

    def _send_recv(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._reader_lock:
            self._send(payload)
            return self._recv(timeout_s=self._denoise_timeout_s)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _readline_with_timeout(stream: Any, timeout_s: float) -> str | None:
    """``stream.readline()`` with a wall-clock timeout.

    Implemented as a polling loop because the framework process is on
    Python 3.12 and we cannot depend on :mod:`select` semantics across
    all platforms. Polling at 5 ms keeps the worst-case latency
    invisible (1 s integration * 5 ms == 0.5% overhead).
    """
    deadline = time.monotonic() + float(timeout_s)
    while True:
        line = stream.readline()
        if line:
            return line
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.005)


def _drain_stderr(stream: Any, sink: list[str]) -> None:
    """Drain ``stream`` to ``sink`` line-by-line until EOF."""
    try:
        for line in iter(stream.readline, ""):
            sink.append(line)
    except (OSError, ValueError):
        # Stream closed during shutdown; nothing to do.
        return


__all__ = [
    "DEFAULT_SIDECAR_VENV",
    "DEFAULT_SIDECAR_PYTHON",
    "DEFAULT_SIDECAR_SCRIPT",
    "DEFAULT_STARTUP_TIMEOUT_S",
    "DEFAULT_DENOISE_TIMEOUT_S",
    "FlowMol3SidecarError",
    "FlowMol3SidecarProcess",
]
