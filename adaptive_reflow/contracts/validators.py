"""Adaptive reflow typed contracts — numeric + scalar validators.

Stdlib-only: no torch, no other adaptive_reflow imports, no IO.
"""
from __future__ import annotations

import math

from .types import FactorValue

# ---------------------------------------------------------------------------
# Validation result alias
# ---------------------------------------------------------------------------

ValidationResult = tuple[bool, tuple[str, ...]]


def _ok() -> ValidationResult:
    return (True, ())


def _err(*messages: str) -> ValidationResult:
    return (False, tuple(messages))


# ---------------------------------------------------------------------------
# Numeric / scalar validators
# ---------------------------------------------------------------------------


def validate_unit_float(x: float) -> ValidationResult:
    """Return ``(True, ())`` iff ``x`` is finite and in ``[0, 1]``."""
    if not isinstance(x, (int, float)):
        return _err(f"expected a real number, got {type(x).__name__}")
    fx = float(x)
    if not math.isfinite(fx):
        return _err(f"value must be finite, got {fx!r}")
    if fx < 0.0 or fx > 1.0:
        return _err(f"value must be in [0, 1], got {fx!r}")
    return _ok()


def validate_unit_factor(x: FactorValue, name: str) -> ValidationResult:
    """Return ``(True, ())`` iff ``x`` is finite and in ``[0, 1]``.

    The error message includes ``name`` so per-factor validation surfaces which
    factor caused the rejection.
    """
    if name is None or str(name).strip() == "":
        return _err("validate_unit_factor requires a non-empty name")
    if not isinstance(x, (int, float)):
        return _err(f"{name}: expected a real number, got {type(x).__name__}")
    fx = float(x)
    if not math.isfinite(fx):
        return _err(f"{name}: value must be finite, got {fx!r}")
    if fx < 0.0 or fx > 1.0:
        return _err(f"{name}: value must be in [0, 1], got {fx!r}")
    return _ok()


def validate_positive_int(x: int, name: str) -> ValidationResult:
    """Return ``(True, ())`` iff ``x`` is a positive integer (``>= 1``)."""
    if name is None or str(name).strip() == "":
        return _err("validate_positive_int requires a non-empty name")
    if isinstance(x, bool) or not isinstance(x, int):
        return _err(f"{name}: expected int, got {type(x).__name__}")
    if x < 1:
        return _err(f"{name}: must be >= 1, got {x}")
    return _ok()


def validate_nonneg_int(x: int, name: str) -> ValidationResult:
    """Return ``(True, ())`` iff ``x`` is a non-negative integer (``>= 0``)."""
    if name is None or str(name).strip() == "":
        return _err("validate_nonneg_int requires a non-empty name")
    if isinstance(x, bool) or not isinstance(x, int):
        return _err(f"{name}: expected int, got {type(x).__name__}")
    if x < 0:
        return _err(f"{name}: must be >= 0, got {x}")
    return _ok()
