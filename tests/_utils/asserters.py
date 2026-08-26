"""Reusable property-test asserters for the adaptive_reflow test suite.

This module collects small, hypothesis-friendly assertion helpers that
encapsulate the *invariant style* of the adaptive_reflow contracts:

* unit-interval membership (``[0, 1]``),
* non-negativity / strict positivity,
* float finiteness,
* deterministic-idempotence,
* anti-monotone / monotone comparisons with a small tolerance.

The helpers deliberately return ``None`` on success (so they can be
called directly inside :func:`hypothesis.given` test bodies) and raise
:exc:`AssertionError` on failure. They are *not* a replacement for
:mod:`pytest`; pytest is still the test runner and shows the failure
traceback.
"""
from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

#: Tolerance used for float comparisons. Sufficient to absorb IEEE-754
#: roundoff in products of factors in ``[0, 1]`` without masking real
#: regressions.
_FLOAT_TOL: float = 1e-9


def assert_unit_interval(x: float, *, name: str = "value") -> None:
    """Assert ``x`` is a finite ``float`` in ``[0, 1]``."""
    assert isinstance(x, (int, float)) and not isinstance(x, bool), (
        f"{name}: expected real number, got {type(x).__name__}"
    )
    fx = float(x)
    assert math.isfinite(fx), f"{name}: must be finite, got {fx!r}"
    assert 0.0 - _FLOAT_TOL <= fx <= 1.0 + _FLOAT_TOL, (
        f"{name}: must be in [0, 1], got {fx!r}"
    )


def assert_non_negative(x: float, *, name: str = "value") -> None:
    """Assert ``x`` is a finite ``float`` with ``x >= 0``."""
    assert isinstance(x, (int, float)) and not isinstance(x, bool), (
        f"{name}: expected real number, got {type(x).__name__}"
    )
    fx = float(x)
    assert math.isfinite(fx), f"{name}: must be finite, got {fx!r}"
    assert fx >= -_FLOAT_TOL, f"{name}: must be >= 0, got {fx!r}"


def assert_positive(x: float, *, name: str = "value") -> None:
    """Assert ``x`` is a finite ``float`` with ``x > 0``."""
    assert isinstance(x, (int, float)) and not isinstance(x, bool), (
        f"{name}: expected real number, got {type(x).__name__}"
    )
    fx = float(x)
    assert math.isfinite(fx), f"{name}: must be finite, got {fx!r}"
    assert fx > _FLOAT_TOL, f"{name}: must be > 0, got {fx!r}"


def assert_finite(x: Any, *, name: str = "value") -> None:
    """Assert ``x`` is a finite real number (booleans coerced)."""
    assert isinstance(x, (int, float)) and not isinstance(x, bool), (
        f"{name}: expected real number, got {type(x).__name__}"
    )
    fx = float(x)
    assert math.isfinite(fx), f"{name}: must be finite, got {fx!r}"


def assert_in_closed(a: float, lo: float, hi: float, *, name: str = "value") -> None:
    """Assert ``a`` lies in the closed interval ``[lo, hi]``."""
    assert lo <= hi + _FLOAT_TOL, (
        f"{name}: interval must satisfy lo <= hi, got lo={lo}, hi={hi}"
    )
    assert_finite(a, name=name)
    assert_finite(lo, name=f"{name}.lo")
    assert_finite(hi, name=f"{name}.hi")
    fa, flo, fhi = float(a), float(lo), float(hi)
    assert flo - _FLOAT_TOL <= fa <= fhi + _FLOAT_TOL, (
        f"{name}: must be in [{flo}, {fhi}], got {fa!r}"
    )


def assert_delta_capped(prev: float, result: float,
                        delta_cap_up: float,
                        delta_cap_down: float) -> None:
    """Assert ``|result - prev| <= max(delta_cap_up, delta_cap_down) + tol``.

    Used by the bounded-merge invariants: any per-round change cannot
    exceed the larger of the up/down delta caps.
    """
    assert_finite(prev, name="prev")
    assert_finite(result, name="result")
    assert_finite(delta_cap_up, name="delta_cap_up")
    assert_finite(delta_cap_down, name="delta_cap_down")
    bound = max(float(delta_cap_up), float(delta_cap_down)) + _FLOAT_TOL
    diff = abs(float(result) - float(prev))
    assert diff <= bound, (
        f"|result - prev|={diff} exceeds max delta cap={bound} "
        f"(delta_cap_up={delta_cap_up}, delta_cap_down={delta_cap_down})"
    )


def assert_monotone_increasing(xs: Iterable[float], *, name: str = "sequence") -> None:
    """Assert ``xs`` is non-decreasing (each element <= the next)."""
    seq = list(xs)
    assert len(seq) >= 2, f"{name}: need at least two elements"
    for i in range(1, len(seq)):
        prev, cur = float(seq[i - 1]), float(seq[i])
        assert prev - _FLOAT_TOL <= cur, (
            f"{name}: not non-decreasing at index {i}: "
            f"{prev} > {cur}"
        )


def assert_monotone_decreasing(xs: Iterable[float], *, name: str = "sequence") -> None:
    """Assert ``xs`` is non-increasing (each element >= the next)."""
    seq = list(xs)
    assert len(seq) >= 2, f"{name}: need at least two elements"
    for i in range(1, len(seq)):
        prev, cur = float(seq[i - 1]), float(seq[i])
        assert cur - _FLOAT_TOL <= prev, (
            f"{name}: not non-increasing at index {i}: "
            f"{prev} < {cur}"
        )


def assert_idempotent(call: Any, *args: Any, **kwargs: Any) -> None:
    """Assert that calling ``call`` twice yields the same result.

    Equality is structural (``==``); for dataclasses / frozen tuples this
    is the canonical determinism invariant.
    """
    a = call(*args, **kwargs)
    b = call(*args, **kwargs)
    assert a == b, (
        f"idempotence violated: first call returned {a!r}, second {b!r}"
    )


# ---------------------------------------------------------------------------
# Validation / blocker / determinism helpers (DTB-style contracts)
# ---------------------------------------------------------------------------


def flowa_close(
    actual: float,
    expected: float,
    *,
    rtol: float = 1e-12,
    atol: float = 1e-12,
    equal_nan: bool = False,
) -> bool:
    """Return whether two floats are within the requested tolerance.

    Thin wrapper around :func:`math.isclose` that uses the adaptive_reflow
    defaults ``rtol=1e-12`` and ``atol=1e-12``. The signature mirrors
    :func:`math.isclose` so callers familiar with the stdlib get the same
    shape; the defaults are tightened to absorb IEEE-754 roundoff in
    products of factors in ``[0, 1]`` without masking real regressions.

    ``equal_nan`` is supported (Python's stdlib ``math.isclose`` does
    not accept it). When ``equal_nan=True`` both ``NaN`` operands
    compare equal; otherwise ``NaN`` operands always compare unequal
    (matching IEEE-754 semantics for ``==``).

    Parameters
    ----------
    actual:
        The measured value.
    expected:
        The reference value.
    rtol:
        Relative tolerance.
    atol:
        Absolute tolerance.
    equal_nan:
        When ``True``, two ``NaN`` values compare equal (mathematically
        incorrect but convenient for property-based tests that want to
        tolerate ``NaN`` outputs on adversarial input).

    Returns
    -------
    bool
        ``True`` iff ``actual`` and ``expected`` compare equal under the
        requested tolerances (and NaN handling policy).
    """
    a = float(actual)
    b = float(expected)
    if math.isnan(a) and math.isnan(b):
        return bool(equal_nan)
    return math.isclose(a, b, rel_tol=float(rtol), abs_tol=float(atol))


def assert_validation_ok(result_tuple: tuple[bool, tuple[str, ...]]) -> None:
    """Assert that a validator's ``(ok, errors)`` tuple reports success.

    The contract validators in :mod:`adaptive_reflow.contracts.validators`
    (and elsewhere) all return a ``ValidationResult`` shaped as
    ``(bool, tuple[str, ...])``. This helper unwraps the tuple and asserts
    both the leading boolean and the empty error tuple so callers get a
    precise failure message.

    Parameters
    ----------
    result_tuple:
        The ``(ok, errors)`` tuple returned by a validator. The first
        element must be exactly ``True``; the second element must be an
        empty tuple.
    """
    assert isinstance(result_tuple, tuple) and len(result_tuple) == 2, (
        f"validation result must be a 2-tuple (ok, errors), got {type(result_tuple).__name__}"
    )
    ok, errors = result_tuple
    assert ok is True, (
        f"validation expected to pass but returned ok=False; errors={errors!r}"
    )
    assert errors == (), (
        f"validation expected to pass but returned non-empty errors={errors!r}"
    )


def assert_validation_failed(
    result_tuple: tuple[bool, tuple[str, ...]],
    expected_code_substring: str,
) -> None:
    """Assert that a validator reports a specific (substring) error code.

    The substring match is deliberate: validators emit composite error
    codes (``"name: reason"``) and tests usually want to assert the
    ``reason`` half. Substring matching keeps the helper robust to the
    evolving prefixes without forcing tests to recompute the exact name.

    Parameters
    ----------
    result_tuple:
        The ``(ok, errors)`` tuple returned by a validator.
    expected_code_substring:
        Substring that must appear in at least one element of the
        ``errors`` tuple.
    """
    assert isinstance(result_tuple, tuple) and len(result_tuple) == 2, (
        f"validation result must be a 2-tuple (ok, errors), got {type(result_tuple).__name__}"
    )
    ok, errors = result_tuple
    assert ok is False, (
        f"validation expected to fail but returned ok=True; errors={errors!r}"
    )
    assert isinstance(errors, tuple), (
        f"validation errors must be a tuple, got {type(errors).__name__}"
    )
    assert errors, (
        f"validation expected to fail with code substring "
        f"{expected_code_substring!r} but errors tuple is empty"
    )
    substring = str(expected_code_substring)
    matches = tuple(e for e in errors if substring in e)
    assert matches, (
        f"validation errors {errors!r} contain no substring "
        f"{substring!r}"
    )


def assert_blocker_tuple(blocker_codes_tuple: tuple[str, ...]) -> None:
    """Assert that a blocker-codes tuple is sorted and unique.

    The adaptive_reflow contracts (notably
    :func:`adaptive_reflow.frame.channel_rule.compute_channel_decision`)
    produce deterministic, sorted blocker tuples so equality is stable
    across runs. This helper enforces that invariant for tests that
    inspect the raw tuple structure.

    Parameters
    ----------
    blocker_codes_tuple:
        The ``blocker_codes`` tuple to inspect. Must be a ``tuple`` of
        strings whose elements are sorted ascending and appear at most
        once.
    """
    assert isinstance(blocker_codes_tuple, tuple), (
        f"blocker_codes must be a tuple, got {type(blocker_codes_tuple).__name__}"
    )
    for i, code in enumerate(blocker_codes_tuple):
        assert isinstance(code, str), (
            f"blocker_codes[{i}] must be str, got {type(code).__name__}"
        )
    # Uniqueness: comparing ``len(set(t))`` to ``len(t)`` is the canonical
    # O(n) deduplication probe.
    assert len(set(blocker_codes_tuple)) == len(blocker_codes_tuple), (
        f"blocker_codes must be unique, got duplicates in {blocker_codes_tuple!r}"
    )
    # Sortedness: walk the tuple and check each element <= the next.
    for i in range(1, len(blocker_codes_tuple)):
        prev_code = blocker_codes_tuple[i - 1]
        cur_code = blocker_codes_tuple[i]
        assert prev_code <= cur_code, (
            f"blocker_codes not sorted at index {i}: {prev_code!r} > {cur_code!r}"
        )


def assert_decision_byte_stable(callable_fn: Any, *args: Any, **kwargs: Any) -> None:
    """Assert that ``callable_fn(*args, **kwargs)`` is byte-stable across calls.

    "Byte-stable" means the *rendered* form of the result is identical
    across two independent invocations of the callable. The helper uses
    :func:`repr` (which is what the audit / ledger row uses to write the
    decision to a stable string), so structural equality of frozen
    dataclasses propagates through unchanged.

    Parameters
    ----------
    callable_fn:
        A zero-or-more-argument callable returning a value whose
        :func:`repr` is expected to be identical across calls.
    *args, **kwargs:
        Forwarded verbatim to ``callable_fn``.
    """
    first = callable_fn(*args, **kwargs)
    second = callable_fn(*args, **kwargs)
    first_repr = repr(first)
    second_repr = repr(second)
    assert first_repr == second_repr, (
        f"decision not byte-stable across calls: first={first_repr!r}, "
        f"second={second_repr!r}"
    )


__all__ = [
    "assert_blocker_tuple",
    "assert_decision_byte_stable",
    "assert_delta_capped",
    "assert_finite",
    "assert_idempotent",
    "assert_in_closed",
    "assert_monotone_decreasing",
    "assert_monotone_increasing",
    "assert_non_negative",
    "assert_positive",
    "assert_unit_interval",
    "assert_validation_failed",
    "assert_validation_ok",
    "flowa_close",
]
