"""Adaptive reflow utility helpers (Wave 38 R-2).

This package hosts small, stdlib-only helpers that are useful across
the framework but do not belong to any of the heavier sub-packages
(``contracts``, ``core``, ``framework``). New helpers should be
self-contained and depend only on the Python stdlib; framework-level
helpers belong in ``adaptive_reflow.framework`` instead.
"""
from __future__ import annotations

from adaptive_reflow.util.host_fingerprint import (
    capture_host_fingerprint,
    compute_host_fingerprint,
    with_host_fingerprint,
)

__all__ = [
    "compute_host_fingerprint",
    "capture_host_fingerprint",
    "with_host_fingerprint",
]
