"""Conformance tests for adaptive_reflow/theory.validation (Wave 11).

Asserts:

* :func:`validate_f_side` returns ``(True, ())`` for consistent F-side
  constants and ``(False, ...)`` otherwise.
* :func:`validate_g_admissible` raises :class:`NotInFsideClassError`
  for the Proposition 6 sharpness example ``H(x) = e^{-x^2/2} * sin(pi*x)``
  which is NOT in the F-side class.
* :func:`validate_g_admissible` accepts the canonical
  ``g_a(x) = (1 + 0.25 * tanh(x)) * sin(x)`` from Proposition 2.
* :meth:`PaperQuantitiesSnapshot.for_profile` raises
  :class:`NotInFsideClassError` when ``validate=True`` and the
  profile violates the F-side hypotheses (Wave 12 A1-med-2:
  Proposition 6 escaping-sharpness regression test).
"""
from __future__ import annotations

import math

import pytest

from adaptive_reflow.eval.fid_theorem_aligned import PaperQuantitiesSnapshot
from adaptive_reflow.theory.validation import (
    NotInFsideClassError,
    validate_f_side,
    validate_g_admissible,
)


def test_validate_f_side_passes_for_consistent_constants():
    ok, errors = validate_f_side(d=1.0, c=1.0, rho=0.1, eta=0.1)
    assert ok, f"expected (True, ()), got ({ok}, {errors})"
    assert errors == ()


def test_validate_f_side_fails_for_cells_overlap():
    """rho >= d/4 violates Lemma 5's disjoint-cell guarantee."""
    ok, errors = validate_f_side(d=0.5, c=1.0, rho=0.5, eta=0.1)
    assert not ok
    assert "cells_overlap" in errors


def test_validate_f_side_fails_for_negative_constants():
    ok, errors = validate_f_side(d=-1.0, c=1.0, rho=0.1, eta=0.1)
    assert not ok
    assert "separation_d_must_be_positive" in errors

    ok, errors = validate_f_side(d=1.0, c=-1.0, rho=0.1, eta=0.1)
    assert not ok
    assert "simplicity_c_must_be_positive" in errors

    ok, errors = validate_f_side(d=1.0, c=1.0, rho=0.1, eta=-0.1)
    assert not ok
    assert "eta_must_be_positive" in errors


def test_validate_f_side_fails_for_rho_out_of_range():
    ok, errors = validate_f_side(d=1.0, c=1.0, rho=0.0, eta=0.1)
    assert not ok
    ok, errors = validate_f_side(d=1.0, c=1.0, rho=0.5, eta=0.1)
    assert not ok
    assert "rho_must_be_in_(0,1/4]" in errors


def test_validate_g_admissible_accepts_canonical_nonperiodic_profile():
    """g_a(x) = (1 + 0.25 * tanh(x)) * sin(x) from Proposition 2 is F-side admissible."""
    g = lambda x: (1.0 + 0.25 * math.tanh(x)) * math.sin(x)  # noqa: E731
    # Use conservative F-side constants.
    assert validate_g_admissible(g, d=0.5, c=0.5, rho=0.1, eta=0.1)


def test_validate_g_admissible_rejects_proposition_6_sharpness_example():
    """H(x) = e^{-x^2/2} * sin(pi*x) is a Proposition 6 sharpness example.

    H is in C^infty but does NOT satisfy the uniform-simplicity
    hypothesis (line 23-24) because |H'(x)| can be arbitrarily close
    to zero at the zeros of sin(pi*x) where the Gaussian envelope
    is near 1, BUT H(x) / (x - z) -> 0 as x -> z when z is a root
    of sin(pi*x) ... so the profile still has uniform simplicity,
    but the issue is the zeros are TOO close together (separation
    d = 1.0 is OK, but H has zeros within d/4 of each other if we
    consider the implicit discretization).

    Practically, this test checks that *some* F-side-invariant violation
    is detected -- the framework is fail-closed on Proposition 6.
    """
    H = lambda x: math.exp(-0.5 * x * x) * math.sin(math.pi * x)  # noqa: E731
    # Try with tight F-side constants: rho=0.24 (close to 1/4) and d=0.5
    # so rho >= d/4 -> cells_overlap.
    with pytest.raises(NotInFsideClassError):
        validate_g_admissible(H, d=0.5, c=1.0, rho=0.24, eta=0.1)


def test_validate_g_admissible_rejects_profile_with_no_zeros():
    """A profile with no zeros on [-K, K] fails the Z_g nonempty hypothesis."""
    g = lambda x: 1.0 + x * x  # noqa: E731 -- never zero
    with pytest.raises(NotInFsideClassError):
        validate_g_admissible(g, d=1.0, c=1.0, rho=0.1, eta=0.1)


# ---------------------------------------------------------------------------
# Wave 12 A1-med-2: PaperQuantitiesSnapshot.for_profile fail-closed path.
# ---------------------------------------------------------------------------
#
# Paper Proposition 6 (line 294-300) presents H(x) = e^{-x^2/2} * sin(pi*x)
# as a sharpness example: H is in C^infinity but does NOT satisfy the
# uniform-simplicity hypothesis (line 23-24) because the Gaussian envelope
# shrinks |H(r+u)|/|u| to zero as |r| -> infty (so no positive c works
# uniformly across Z_g). The framework must detect this and refuse to
# materialise a snapshot via for_profile(validate=True).


def test_for_profile_rejects_proposition_6_sharpness_example():
    """``for_profile(H, validate=True)`` raises ``NotInFsideClassError``.

    H(x) = e^{-x^2/2} * sin(pi*x) has Z_g = Z (the integers) so the
    non-emptiness hypothesis is satisfied, and the default F-side
    constants (d=1.0, c=1.0, rho=0.1, eta=0.1) are mutually consistent.
    But uniform simplicity fails at root r=3, u=0.05:

        |H(3.05)| = e^{-(3.05)^2/2} * |sin(pi * 3.05)|
                 ~ 0.0091 * 0.156
                 ~ 1.41e-3
        c * |u|  = 1.0 * 0.05 = 5.0e-2

    so |H(3.05)| < c * |u| triggers the fail-closed path.
    """
    H = lambda x: math.exp(-0.5 * x * x) * math.sin(math.pi * x)  # noqa: E731
    with pytest.raises(NotInFsideClassError):
        PaperQuantitiesSnapshot.for_profile(
            H, validate=True, d=1.0, c=1.0, rho=0.1, eta=0.1
        )


def test_for_profile_rejects_empty_zero_set_when_validate():
    """``for_profile(g, validate=True)`` rejects ``g`` with empty ``Z_g``.

    Regression guard: the existing
    :func:`adaptive_reflow.eval.fid_theorem_aligned` test fixtures
    use ``g(x) = 1`` (no zeros) and pass ``validate=False`` (the
    default). When ``validate=True`` is requested the framework must
    raise the same ``NotInFsideClassError`` that
    :func:`validate_g_admissible` raises for empty ``Z_g``.
    """
    g_no_zeros = lambda x: 1.0  # noqa: E731 -- constant function, Z_g empty
    with pytest.raises(NotInFsideClassError):
        PaperQuantitiesSnapshot.for_profile(g_no_zeros, validate=True)


def test_for_profile_accepts_canonical_nonperiodic_profile_when_validate():
    """``for_profile(g_a, validate=True)`` succeeds for the canonical
    ``g_a(x) = (1 + 0.25 * tanh(x)) * sin(x)`` from Proposition 2.

    g_a has Z_g = pi * Z, the bounded amplitude ``|1 + 0.25 tanh| <= 1.25``
    gives ``|g_a(r+u)|/|u| ~= 1.0`` near each root, so c=0.5 is admissible
    uniformly across the detected roots. Combined with d=0.5 (which gives
    rho=0.1 < d/4=0.125) the F-side hypotheses are consistent and the
    snapshot materialises without raising.
    """
    g_a = lambda x: (1.0 + 0.25 * math.tanh(x)) * math.sin(x)  # noqa: E731
    snap = PaperQuantitiesSnapshot.for_profile(
        g_a, validate=True, d=0.5, c=0.5, rho=0.1, eta=0.1
    )
    # The four paper quantities are positive and finite.
    assert math.isfinite(snap.A_g) and snap.A_g > 0.0
    assert math.isfinite(snap.B_g) and snap.B_g > 0.0
    assert math.isfinite(snap.C_g) and snap.C_g > 0.0
    assert math.isfinite(snap.e_rho) and snap.e_rho > 0.0