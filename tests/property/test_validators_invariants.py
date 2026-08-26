"""Property-based invariants for the contract validators (DTB-validators).

Five hypothesis-driven templates covering the four universal numeric
validators in :mod:`adaptive_reflow.contracts.validators`:

9. ``validate_unit_float`` is total — it never raises on any input.
10. Boundary inclusivity — ``0.0`` and ``1.0`` are both valid.
11. Type rejection — ``str`` and ``None`` return ``False``.
12. ``validate_positive_int`` rejects ``bool``.
13. ``validate_nonneg_int`` accepts ``0`` and rejects negatives.

Stdlib-only.
"""
from __future__ import annotations

import pytest
from hypothesis import HealthCheck, assume, given, settings

from adaptive_reflow.contracts.validators import (
    validate_nonneg_int,
    validate_positive_int,
    validate_unit_float,
)

from . import (
    booleans,
    negative_ints,
    non_numeric_types,
    nonneg_small_ints,
    positive_small_ints,
    unit_floats,
)

# ---------------------------------------------------------------------------
# 9. validate_unit_float is total — it never raises on any input.
# ---------------------------------------------------------------------------


@given(x=unit_floats)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_validate_unit_float_total(x: float) -> None:
    """``validate_unit_float`` is total on any in-envelope float input."""
    ok, errors = validate_unit_float(x)
    assert isinstance(ok, bool)
    assert isinstance(errors, tuple)
    if ok:
        assert errors == ()
    else:
        assert all(isinstance(e, str) for e in errors)


# ---------------------------------------------------------------------------
# 10. Boundary inclusivity — 0.0 and 1.0 both valid
# ---------------------------------------------------------------------------


def test_validate_unit_float_accepts_zero() -> None:
    """``0.0`` is in the closed unit interval and must validate."""
    ok, errors = validate_unit_float(0.0)
    assert ok is True
    assert errors == ()


def test_validate_unit_float_accepts_one() -> None:
    """``1.0`` is in the closed unit interval and must validate."""
    ok, errors = validate_unit_float(1.0)
    assert ok is True
    assert errors == ()


@given(x=unit_floats)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_validate_unit_float_inclusive_on_sampled_envelope(x: float) -> None:
    """Sampled envelope points all validate (boundary + interior)."""
    ok, errors = validate_unit_float(x)
    assert ok is True, f"validator rejected envelope value {x!r}: {errors!r}"
    assert errors == ()


# ---------------------------------------------------------------------------
# 11. Type rejection — str and None return False
# ---------------------------------------------------------------------------


@given(bad=non_numeric_types)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_validate_unit_float_rejects_non_numeric(bad: object) -> None:
    """``validate_unit_float`` returns ``False`` for non-numeric input."""
    ok, errors = validate_unit_float(bad)  # type: ignore[arg-type]
    assert ok is False
    assert isinstance(errors, tuple)
    assert len(errors) >= 1
    assert all(isinstance(e, str) for e in errors)


def test_validate_unit_float_rejects_str() -> None:
    """A ``str`` value must be rejected with a non-empty error tuple."""
    ok, errors = validate_unit_float("0.5")  # type: ignore[arg-type]
    assert ok is False
    assert errors
    assert all(isinstance(e, str) for e in errors)


def test_validate_unit_float_rejects_none() -> None:
    """``None`` must be rejected with a non-empty error tuple."""
    ok, errors = validate_unit_float(None)  # type: ignore[arg-type]
    assert ok is False
    assert errors
    assert all(isinstance(e, str) for e in errors)


# ---------------------------------------------------------------------------
# 12. validate_positive_int rejects bool
# ---------------------------------------------------------------------------


def test_validate_positive_int_rejects_bool_true() -> None:
    """``True`` (a ``bool``) must be rejected by the positive-int validator."""
    ok, errors = validate_positive_int(True, "n")  # type: ignore[arg-type]
    assert ok is False
    assert errors
    assert all(isinstance(e, str) for e in errors)


def test_validate_positive_int_rejects_bool_false() -> None:
    """``False`` (a ``bool``) must be rejected by the positive-int validator."""
    ok, errors = validate_positive_int(False, "n")  # type: ignore[arg-type]
    assert ok is False
    assert errors
    assert all(isinstance(e, str) for e in errors)


@given(b=booleans)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_validate_positive_int_rejects_all_bools(b: bool) -> None:
    """Every ``bool`` value must be rejected, regardless of its int value."""
    ok, errors = validate_positive_int(b, "n")  # type: ignore[arg-type]
    assert ok is False
    assert errors


@given(n=positive_small_ints)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_validate_positive_int_accepts_positive_ints(n: int) -> None:
    """Genuine ``int`` values ``>= 1`` are accepted."""
    ok, errors = validate_positive_int(n, "n")
    assert ok is True
    assert errors == ()


# ---------------------------------------------------------------------------
# 13. validate_nonneg_int accepts 0 and rejects negatives
# ---------------------------------------------------------------------------


def test_validate_nonneg_int_accepts_zero() -> None:
    """``0`` is a valid non-negative integer."""
    ok, errors = validate_nonneg_int(0, "n")
    assert ok is True
    assert errors == ()


@given(n=nonneg_small_ints)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_validate_nonneg_int_accepts_nonneg_ints(n: int) -> None:
    """Every non-negative ``int`` is accepted."""
    ok, errors = validate_nonneg_int(n, "n")
    assert ok is True
    assert errors == ()


@given(n=negative_ints)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_validate_nonneg_int_rejects_negatives(n: int) -> None:
    """Every negative ``int`` is rejected with a non-empty error tuple."""
    ok, errors = validate_nonneg_int(n, "n")
    assert ok is False
    assert errors
    assert all(isinstance(e, str) for e in errors)


@given(b=booleans)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_validate_nonneg_int_rejects_bools(b: bool) -> None:
    """``bool`` is rejected even though its int value is ``0`` or ``1``."""
    ok, errors = validate_nonneg_int(b, "n")  # type: ignore[arg-type]
    assert ok is False
    assert errors
