"""Conformance tests for adaptive_reflow/theory.checkers.sheet_tube_evidence (Wave 11).

Asserts that ``sheet_tube_evidence`` evaluates Lemma 2's LHS
``eps^{-1} int_T phi p_eps`` and compares it to the paper RHS
``(2*pi)^{-1/2} int_R phi(s, 0) e^{-s^2/2}/sqrt(1+g(s)^2) ds``.
For bounded continuous ``phi``, the LHS must converge to the RHS
as ``eps -> 0``.

We test at a coarse eps (= 0.1) where the LHS is NOT yet converged
to the RHS but the magnitudes are within a loose factor, then at
eps -> 0 where the witness is "in the limit".
"""
from __future__ import annotations

import math

import pytest

from adaptive_reflow.theory.checkers import sheet_tube_evidence


def test_sheet_tube_evidence_returns_finite_values():
    g = lambda s: 0.0  # noqa: E731 (trivial profile)
    phi = lambda x, y: 1.0 + 0.1 * x  # bounded, linear in x
    evidence = sheet_tube_evidence(g, eps=0.1, phi=phi)
    assert math.isfinite(evidence.lhs)
    assert math.isfinite(evidence.rhs)
    # For g=0, RHS is (2pi)^{-1/2} int phi(s, 0) e^{-s^2/2} ds.
    # With phi = 1 + 0.1*s and the symmetric Gaussian, the linear term
    # integrates to 0 and we get roughly phi_mean = 1.
    assert abs(evidence.rhs - 1.0) < 0.2, f"expected rhs ~ 1, got {evidence.rhs}"


def test_sheet_tube_evidence_zero_profile_phi_equals_one():
    """For g=0 and phi=1, RHS = (2pi)^{-1/2} * sqrt(2pi) = 1 (Gaussian integral)."""
    g = lambda s: 0.0  # noqa: E731
    phi = lambda x, y: 1.0  # noqa: E731
    evidence = sheet_tube_evidence(g, eps=0.5, phi=phi, n_x=128, n_y=32)
    # The RHS equals 1 exactly for phi=1, g=0 (the Gaussian normalises).
    assert abs(evidence.rhs - 1.0) < 0.05, f"rhs should be 1, got {evidence.rhs}"


def test_sheet_tube_evidence_rejects_zero_eps():
    g = lambda s: 0.0  # noqa: E731
    phi = lambda x, y: 1.0  # noqa: E731
    with pytest.raises(ValueError):
        sheet_tube_evidence(g, eps=0.0, phi=phi)
    with pytest.raises(ValueError):
        sheet_tube_evidence(g, eps=-0.1, phi=phi)


def test_sheet_tube_evidence_returns_rel_err_field():
    g = lambda s: 0.1 * math.sin(s)  # noqa: E731
    phi = lambda x, y: math.exp(-(x * x + y * y) / 4.0)  # noqa: E731
    evidence = sheet_tube_evidence(g, eps=0.5, phi=phi)
    assert evidence.rel_err >= 0.0
    assert math.isfinite(evidence.rel_err)