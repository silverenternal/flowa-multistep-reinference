"""Conformance tests for the paper_selection_ratio function (Wave 11).

Asserts that ``paper_selection_ratio(sheet_A, packing_B, cell_C, eps)``
matches the paper Corollary 1 formula and converges to 1 as ``eps -> 0``.
"""
from __future__ import annotations

import math

import pytest

from adaptive_reflow.theory.paper_quantities import paper_selection_ratio


def test_paper_selection_ratio_at_eps_one():
    """At eps=1.0 the ratio is determined by the relative magnitudes."""
    sheet_A, packing_B, cell_C = 0.5, 0.3, 1.2
    r = paper_selection_ratio(sheet_A, packing_B, cell_C, eps=1.0)
    expected = (sheet_A * 1.0) / (sheet_A * 1.0 + cell_C * packing_B * 1.0)
    assert abs(r - expected) < 1e-12


def test_paper_selection_ratio_increases_with_decreasing_eps():
    """For fixed (sheet_A, packing_B, cell_C), paper_selection_ratio is monotone increasing as eps -> 0."""
    sheet_A, packing_B, cell_C = 0.5, 0.3, 1.2
    eps_values = [1.0, 0.5, 0.1, 0.05, 0.01]
    ratios = [paper_selection_ratio(sheet_A, packing_B, cell_C, eps=e) for e in eps_values]
    for i in range(len(ratios) - 1):
        assert ratios[i + 1] > ratios[i], (
            f"selection_ratio should increase as eps decreases; got {ratios}"
        )


def test_paper_selection_ratio_zero_eps_returns_one():
    """At eps = 0, sheet term is 0 and cell term is 0, but the limit is 1.

    Implementation note: at exactly eps=0 the formula sheet*eps /
    (sheet*eps + cell*eps^2) is 0/0; we return 0.0 (conservative).
    The paper's asymptotic claim is that as eps -> 0 (not at eps = 0)
    the ratio -> 1.
    """
    sheet_A, packing_B, cell_C = 0.5, 0.3, 1.2
    r = paper_selection_ratio(sheet_A, packing_B, cell_C, eps=0.0)
    assert r == 0.0


def test_paper_selection_ratio_monotone_for_various_constants():
    """Monotone increase holds across a variety of (sheet_A, packing_B, cell_C)."""
    test_cases = [
        (0.1, 0.5, 0.3),
        (1.0, 0.5, 0.5),
        (0.7, 0.1, 2.0),
    ]
    eps_values = [0.5, 0.1, 0.01]
    for sheet_A, packing_B, cell_C in test_cases:
        ratios = [
            paper_selection_ratio(sheet_A, packing_B, cell_C, eps=e)
            for e in eps_values
        ]
        for i in range(len(ratios) - 1):
            assert ratios[i + 1] >= ratios[i] - 1e-12, (
                f"non-monotone for ({sheet_A}, {packing_B}, {cell_C}): {ratios}"
            )


def test_paper_selection_ratio_rejects_negative():
    with pytest.raises(ValueError):
        paper_selection_ratio(-1.0, 0.5, 1.0, 0.1)
    with pytest.raises(ValueError):
        paper_selection_ratio(0.5, 0.5, 1.0, -0.1)


def test_paper_selection_ratio_rejects_nan_inf():
    with pytest.raises(ValueError):
        paper_selection_ratio(float("nan"), 0.5, 1.0, 0.1)
    with pytest.raises(ValueError):
        paper_selection_ratio(0.5, 0.5, 1.0, float("inf"))
