"""Capture host characteristics for audit-output provenance (R-2).

Mirrors the SciMLBenchmarks.jl auto-append pattern (Finding F-5 of
``docs/audit/web-research-2026.md``): every
``verification_outputs/*.json`` produced by a ``tools/run_*`` script
should carry a ``_host_fingerprint`` field so a future agent reading
the output can tell which machine produced it.

The host fingerprint is **richer** than the per-output regression
vector's ``host_fingerprint`` field (which is a SHA-256 of
``env_hash.txt`` used for byte-stability checking; see
``tools/run_regression_vector_audit.py``). The two fingerprints
complement each other:

* ``tools/run_regression_vector_audit`` ``host_fingerprint`` is a single
  hex digest of the locked environment; used for **byte-stability**
  verification of pinned regression vectors.
* ``adaptive_reflow.util.host_fingerprint.compute_host_fingerprint``
  is a structured dict (python / torch / cuda / hostname_hash /
  platform / captured_at); used for **per-output audit provenance**.

Both fields are emitted independently.

The module has zero hard dependencies beyond the Python stdlib. The
optional ``torch`` probe is wrapped in ``try / except ImportError`` so
the module is importable on CPU-only sandboxes that lack torch.

Public API
----------
* :func:`compute_host_fingerprint` — return the fingerprint dict.
* :func:`capture_host_fingerprint` — alias kept for symmetry with the
  SciMLBenchmarks.jl "capture host characteristics" framing and to
  match the todo's planned API.
* :func:`with_host_fingerprint` — append the fingerprint to a payload
  dict (or wrap a list payload in an envelope). Used by
  ``tools/run_*`` scripts at JSON-dump time.

Why a leading underscore on the JSON key?
-----------------------------------------
``_host_fingerprint`` (underscore-prefixed) signals "metadata, not
data" to downstream consumers. JSON schema validators can ignore it;
diff tools will surface it as a one-line change rather than a data
regression.
"""
from __future__ import annotations

import hashlib
import platform
import socket
import sys
from datetime import UTC, datetime, timezone

# ---------------------------------------------------------------------------
# Core fingerprint computation.
# ---------------------------------------------------------------------------


def compute_host_fingerprint() -> dict[str, str]:
    """Return a stable, JSON-serialisable fingerprint of the current host.

    Returns
    -------
    dict[str, str]
        Keys: ``python``, ``platform``, ``hostname_hash``, ``captured_at``,
        and (when torch is importable) ``torch``, ``cuda``. All values are
        strings.

    Notes
    -----
    * ``hostname_hash`` is a ``sha256:`` prefixed 16-hex-char digest of
      ``socket.gethostname()``; the leading hex segment is enough to
      disambiguate machines for audit-provenance purposes (full PII
      redaction) while remaining deterministic.
    * ``captured_at`` is an ISO-8601 UTC timestamp (timezone-aware).
    * ``torch.__version__`` is captured opportunistically; on CPU-only
      sandboxes ``torch`` may be absent, in which case the field is
      ``"not_installed"`` (and ``cuda`` becomes ``"n/a"``).
    """
    hostname = socket.gethostname()
    hostname_hash = (
        "sha256:" + hashlib.sha256(hostname.encode("utf-8")).hexdigest()[:16]
    )
    fp: dict[str, str] = {
        "python": sys.version.split()[0],  # e.g. "3.11.5"
        "platform": platform.platform(),
        "hostname_hash": hostname_hash,
        "captured_at": datetime.now(UTC).isoformat(),
    }
    try:
        import torch

        fp["torch"] = torch.__version__
        fp["cuda"] = torch.version.cuda or "none"
    except ImportError:
        fp["torch"] = "not_installed"
        fp["cuda"] = "n/a"
    return fp


# ---------------------------------------------------------------------------
# Back-compat alias (the todo specifies capture_host_fingerprint).
# ---------------------------------------------------------------------------


def capture_host_fingerprint() -> dict[str, str]:
    """Alias for :func:`compute_host_fingerprint`.

    Kept for symmetry with the SciMLBenchmarks.jl "capture host
    characteristics" framing and the API sketched in
    ``todo/algo-improvement-host-fingerprint.md``. New code should
    prefer :func:`compute_host_fingerprint` (the canonical name).
    """
    return compute_host_fingerprint()


# ---------------------------------------------------------------------------
# Payload decorator — used by tools/run_*.py scripts at JSON-dump time.
# ---------------------------------------------------------------------------


def with_host_fingerprint(payload: dict | list) -> dict:  # type: ignore[type-arg]
    """Return a copy of ``payload`` with ``_host_fingerprint`` appended.

    Parameters
    ----------
    payload : dict | list
        The audit-output dict (preferred). A bare ``list`` payload is
        accepted for ergonomics and is wrapped in an envelope::

            {"_host_fingerprint": {...}, "items": [...]}

    Returns
    -------
    dict
        A new dict; the input ``payload`` dict is shallow-copied, never
        mutated in place. The fingerprint key is the underscore-prefixed
        ``_host_fingerprint`` (metadata, not data).

    Raises
    ------
    TypeError
        If ``payload`` is neither a ``dict`` nor a ``list``.
    """
    fp = compute_host_fingerprint()
    if isinstance(payload, dict):
        result = dict(payload)
        result["_host_fingerprint"] = fp
        return result
    if isinstance(payload, list):
        return {"_host_fingerprint": fp, "items": payload}
    raise TypeError(
        f"with_host_fingerprint: unsupported payload type {type(payload).__name__}"
    )


__all__ = [
    "compute_host_fingerprint",
    "capture_host_fingerprint",
    "with_host_fingerprint",
]
