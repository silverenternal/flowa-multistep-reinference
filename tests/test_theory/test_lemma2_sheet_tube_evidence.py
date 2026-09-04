"""Conformance tests for adaptive_reflow/theory.checkers.sheet_tube_evidence (Wave 11).

Asserts that ``sheet_tube_evidence`` evaluates Lemma 2's LHS
``eps^{-1} int_T phi p_eps`` and compares it to the paper RHS
``(2*pi)^{-1/2} int_R phi(s, 0) e^{-s^2/2}/sqrt(1+g(s)^2) ds``.
For bounded continuous ``phi``, the LHS must converge to the RHS
as ``eps -> 0``.

We test at a coarse eps (= 0.1) where the LHS is NOT yet converged
to the RHS but the magnitudes are within a loose factor, then at
eps -> 0 where the witness is "in the limit".

The Wave 12 A1-high-2 fix adds a *finite-eps* LHS/RHS ratio witness
exposed by :mod:`adaptive_reflow.theory.lemma2_checker` that
demonstrates ``LHS / RHS -> 1`` as ``eps -> 0`` for the Proposition 2
nonperiodic family ``g_a(x) = (1 + 0.25*tanh(x)) * sin(x)``.
"""
from __future__ import annotations

import math

import pytest

from adaptive_reflow.theory import sheet_tube_evidence as ratio_witness
from adaptive_reflow.theory.checkers import sheet_tube_evidence


# ---------------------------------------------------------------------------
# Wave 11 -- checkers.sheet_tube_evidence (dataclass witness)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Wave 12 A1-high-2 -- lemma2_checker.sheet_tube_evidence (float ratio)
# ---------------------------------------------------------------------------


def _g_a(x: float) -> float:
    """Proposition 2 nonperiodic family (paper line 62-64).

    ``g_a(x) = (1 + 0.25*tanh(x)) * sin(x)`` with ``a(x) = 1 + 0.25*tanh(x)``.
    Admissible (no periodicity) and bounded above/below by positive
    constants, hence a valid witness for Lemma 2 (which does NOT
    require periodicity, see Remark 1 line 54-56).
    """
    return (1.0 + 0.25 * math.tanh(x)) * math.sin(x)


def test_ratio_witness_returns_float_finite():
    """``lemma2_checker.sheet_tube_evidence`` returns a finite ``float``."""
    ratio = ratio_witness(_g_a, eps=0.1, phi=lambda x, y: 1.0)
    assert isinstance(ratio, float)
    assert math.isfinite(ratio)


def test_ratio_witness_rejects_non_positive_eps():
    """Negative / zero ``eps`` is rejected."""
    phi = lambda x, y: 1.0  # noqa: E731
    with pytest.raises(ValueError):
        ratio_witness(_g_a, eps=0.0, phi=phi)
    with pytest.raises(ValueError):
        ratio_witness(_g_a, eps=-0.1, phi=phi)


def test_ratio_witness_converges_to_one_for_proposition_two_profile():
    """Paper Lemma 2 limit: ``LHS / RHS -> 1`` as ``eps -> 0``.

    For the Proposition 2 family ``g_a(x) = (1 + 0.25*tanh(x)) sin(x)``
    and the constant test function ``phi(x, y) = 1``, the LHS at
    finite ``eps`` is computed by 2D-grid Monte-Carlo on
    ``T = {(x, y) : |y| <= 1/2}`` with the paper's literal residual
    ``|F_g|^2 = y^2 * (g(x)^2 + (y-1)^2)``. The RHS is the
    coarea-weighted line integral from Lemma 2's display. Per
    Lemma 2 the ratio converges to 1.0 as ``eps -> 0``.

    Convergence rate is ``O(eps^2)``: at ``eps = 0.01`` the ratio is
    within ~0.03% of 1; at ``eps = 0.05`` within ~0.7%; at
    ``eps = 0.1`` within ~3.5%; at ``eps = 0.5`` within ~28% (slow
    because the convergence regime has not been entered).

    The acceptance criterion is:

    1. The smallest ``eps`` (``0.01``) yields ``|ratio - 1| <= 0.01``
       (1% tolerance).
    2. The sequence of ratios approaches 1 monotonically (in absolute
       distance) as ``eps`` decreases along ``[0.5, 0.1, 0.05, 0.01]``.
    """
    phi = lambda x, y: 1.0  # noqa: E731
    eps_seq = (0.5, 0.1, 0.05, 0.01)
    ratios = [ratio_witness(_g_a, eps=e, phi=phi) for e in eps_seq]

    # (1) 1% tolerance at the smallest eps -- the headline convergence
    # assertion for the A1-high-2 acceptance criterion.
    assert abs(ratios[-1] - 1.0) < 0.01, (
        f"ratio at eps={eps_seq[-1]} should be within 1% of 1, "
        f"got {ratios[-1]}"
    )

    # (2) Trend: distance to 1 is non-increasing as eps decreases
    # (the O(eps^2) convergence gives monotonic distance reduction
    # from eps = 0.5 onward for this specific g_a).
    distances = [abs(r - 1.0) for r in ratios]
    for prev, curr in zip(distances, distances[1:]):
        assert curr <= prev + 1e-12, (
            f"distance to 1 should decrease as eps -> 0; got "
            f"{distances}"
        )


def test_ratio_witness_zero_profile_phi_one_converges_to_one():
    """For ``g = 0`` and ``phi = 1`` the ratio converges to 1 as ``eps -> 0``.

    With ``g = 0`` the residual ``|F_g|^2 = y^2 (y-1)^2`` and the RHS is
    ``(2*pi)^{-1/2} * sqrt(2*pi) = 1``. The LHS converges to 1 in the
    limit. Convergence is ``O(eps^2)``: at ``eps = 0.01`` the ratio is
    within ~0.06% of 1; at ``eps = 0.5`` it is ~35% off (the convergence
    regime has not been entered).

    The acceptance criterion is:

    1. The smallest ``eps`` (``0.01``) yields ``|ratio - 1| <= 0.01``
       (1% tolerance).
    2. The sequence of ratios approaches 1 monotonically (in absolute
       distance) as ``eps`` decreases.
    """
    g_zero = lambda x: 0.0  # noqa: E731
    phi = lambda x, y: 1.0  # noqa: E731
    eps_seq = (0.5, 0.1, 0.05, 0.01)
    ratios = [ratio_witness(g_zero, eps=e, phi=phi) for e in eps_seq]

    # (1) 1% tolerance at the smallest eps.
    assert abs(ratios[-1] - 1.0) < 0.01, (
        f"ratio at eps={eps_seq[-1]} should be within 1% of 1, "
        f"got {ratios[-1]}; full sequence = {ratios}"
    )

    # (2) Trend: distance to 1 is non-increasing as eps decreases.
    distances = [abs(r - 1.0) for r in ratios]
    for prev, curr in zip(distances, distances[1:]):
        assert curr <= prev + 1e-12, (
            f"distance to 1 should decrease as eps -> 0; got "
            f"{distances}"
        )


def test_ratio_witness_smooth_phi_converges_to_one():
    """For a non-trivial smooth ``phi``, the ratio still converges to 1.

    Uses ``phi(x, y) = exp(-x^2/4 - y^2/4)`` -- a smooth bounded
    continuous test function that exercises the full Lemma 2 limit
    (not just the ``phi = 1`` closed-form edge case).
    """
    phi = lambda x, y: math.exp(-(x * x + y * y) / 4.0)  # noqa: E731
    eps_seq = (0.5, 0.1, 0.05, 0.01)
    ratios = [ratio_witness(_g_a, eps=e, phi=phi) for e in eps_seq]
    # Headline: 1% tolerance at the smallest eps.
    assert abs(ratios[-1] - 1.0) < 0.01, (
        f"ratio at eps={eps_seq[-1]} should be within 1% of 1, "
        f"got {ratios[-1]}; full sequence = {ratios}"
    )
    # Trend: distances decrease.
    distances = [abs(r - 1.0) for r in ratios]
    for prev, curr in zip(distances, distances[1:]):
        assert curr <= prev + 1e-12, (
            f"distance to 1 should decrease as eps -> 0; got "
            f"{distances}"
        )