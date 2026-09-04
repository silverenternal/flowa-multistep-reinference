"""Conformance tests for adaptive_reflow/theory.f_side_validator.validate_f_side (Wave 12 A1-med-1).

Asserts that :func:`validate_f_side` is fail-closed on the four F-side
constraints (``rho < d/4``, ``rho <= 1/4``, ``c > 0``, ``eta > 0``) and
returns additive, paper-symbol-friendly error codes:

    * ``"rho_must_be_lt_d_over_4"``
    * ``"rho_must_be_le_1_over_4"``
    * ``"c_must_be_positive"``
    * ``"eta_must_be_positive"``
"""
from __future__ import annotations

from adaptive_reflow.theory.f_side_validator import validate_f_side


def test_validate_f_side_pass():
    """Default-like F-side constants pass: ``(True, ())``."""
    ok, errors = validate_f_side(d=1.0, c=1.0, rho=0.1, eta=0.1)
    assert ok is True
    assert errors == ()


def test_validate_f_side_fail_rho_ge_d_over_4():
    """``d=0.4, rho=0.1``: ``rho == d/4`` violates Lemma 5 strict ``rho < d/4``."""
    ok, errors = validate_f_side(d=0.4, c=1.0, rho=0.1, eta=0.1)
    assert ok is False
    assert errors == ("rho_must_be_lt_d_over_4",)


def test_validate_f_side_fail_rho_gt_1_over_4():
    """``rho=0.3 > 1/4`` violates the cell-radius upper bound."""
    ok, errors = validate_f_side(d=10.0, c=1.0, rho=0.3, eta=0.1)
    assert ok is False
    assert errors == ("rho_must_be_le_1_over_4",)


def test_validate_f_side_fail_c_le_0():
    """``c=0.0`` violates the uniform-simplicity constraint."""
    ok, errors = validate_f_side(d=1.0, c=0.0, rho=0.1, eta=0.1)
    assert ok is False
    assert errors == ("c_must_be_positive",)


def test_validate_f_side_fail_eta_le_0():
    """``eta=0.0`` violates the exterior-gap constraint."""
    ok, errors = validate_f_side(d=1.0, c=1.0, rho=0.1, eta=0.0)
    assert ok is False
    assert errors == ("eta_must_be_positive",)


def test_validate_f_side_fail_all():
    """All four constraints fail simultaneously; errors aggregate additively."""
    # d=0.0 forces rho_must_be_lt_d_over_4 (since d/4 == 0 and rho > 0).
    # c=-1.0 forces c_must_be_positive.
    # rho=0.5 forces rho_must_be_le_1_over_4.
    # eta=-1.0 forces eta_must_be_positive.
    ok, errors = validate_f_side(d=0.0, c=-1.0, rho=0.5, eta=-1.0)
    assert ok is False
    assert "rho_must_be_lt_d_over_4" in errors
    assert "rho_must_be_le_1_over_4" in errors
    assert "c_must_be_positive" in errors
    assert "eta_must_be_positive" in errors
    assert len(errors) == 4
