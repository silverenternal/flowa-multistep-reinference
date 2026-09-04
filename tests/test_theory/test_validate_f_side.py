"""Conformance tests for adaptive_reflow/theory.validation.validate_f_side (Wave 11)."""
from __future__ import annotations

import pytest

from adaptive_reflow.theory.validation import validate_f_side


def test_validate_f_side_returns_tuple():
    result = validate_f_side(d=1.0, c=1.0, rho=0.1, eta=0.1)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], bool)
    assert isinstance(result[1], tuple)


def test_validate_f_side_default_like_parameters_pass():
    """The framework's default F-side constants (rho=eta=0.1) should pass."""
    ok, errors = validate_f_side(d=1.0, c=1.0, rho=0.1, eta=0.1)
    assert ok
    assert errors == ()


def test_validate_f_side_parametrized_lattice():
    """Lattice: for rho < d/4 returns (True, ()); for rho >= d/4 returns (False, ('cells_overlap',))."""
    cases = [
        # (d, c, rho, eta, expect_ok, expect_codes)
        (1.0, 1.0, 0.1, 0.1, True, ()),
        (0.5, 1.0, 0.1, 0.1, True, ()),  # 0.1 < 0.5/4 = 0.125 -> pass
        (0.4, 1.0, 0.1, 0.1, False, ("cells_overlap",)),  # 0.1 >= 0.4/4 = 0.1 -> cells_overlap
        (1.0, 1.0, 0.24, 0.1, True, ()),  # 0.24 < 1.0/4 = 0.25 -> pass
        (1.0, 1.0, 0.25, 0.1, False, ("cells_overlap",)),  # 0.25 >= 1.0/4 -> cells_overlap
    ]
    for d, c, rho, eta, expect_ok, expect_codes in cases:
        ok, errors = validate_f_side(d=d, c=c, rho=rho, eta=eta)
        assert ok == expect_ok, f"({d}, {c}, {rho}, {eta}): got ok={ok}, expected {expect_ok}"
        for code in expect_codes:
            assert code in errors, (
                f"({d}, {c}, {rho}, {eta}): expected code {code!r} in {errors}"
            )


def test_validate_f_side_rho_upper_bound():
    """rho > 1/4 should fail (Lemma 5 setup requires rho in (0, 1/4])."""
    ok, errors = validate_f_side(d=10.0, c=1.0, rho=0.3, eta=0.1)
    assert not ok
    assert "rho_must_be_in_(0,1/4]" in errors


def test_validate_f_side_zero_rho_fails():
    ok, errors = validate_f_side(d=1.0, c=1.0, rho=0.0, eta=0.1)
    assert not ok
    assert "rho_must_be_in_(0,1/4]" in errors


def test_validate_f_side_aggregates_errors():
    """Multiple errors are reported additively."""
    ok, errors = validate_f_side(d=-1.0, c=-1.0, rho=0.5, eta=-0.1)
    assert not ok
    # Expect multiple codes.
    assert len(errors) >= 3


def test_validate_f_side_strict_d_lt_four_rho():
    """The boundary case d = 4*rho is on the edge; the implementation requires rho < d/4 strict."""
    ok, errors = validate_f_side(d=0.4, c=1.0, rho=0.1, eta=0.1)
    # d/4 = 0.1, rho = 0.1 -> NOT strict -> should fail with cells_overlap.
    assert not ok
    assert "cells_overlap" in errors