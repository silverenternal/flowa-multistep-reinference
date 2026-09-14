"""HIGH-2 fix: ``bounded_lipschitz_distance_2d`` must fail-loud under no-scipy.

Paper Theorem 1 contract requires the *exact* bounded-Lipschitz distance
on the ambient plane. Historically the function silently fell back to a
greedy upper-bound assignment when :func:`scipy.optimize.linear_sum_assignment`
was unavailable — a different value that violates the Theorem 1 contract
under scipy-missing deployments (CI minimal, Windows, etc.).

This module pins two contracts:

1. **Negative path**: with ``scipy.optimize`` stubbed out,
   :func:`bounded_lipschitz_distance_2d` must raise
   :class:`ImportError` whose message names ``scipy>=1.7`` as the
   requirement (no silent greedy fallback).
2. **Happy path**: with scipy available, the function still returns a
   non-negative finite scalar (Hungarian-optimal BL distance).
"""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from adaptive_reflow.eval.lipschitz_diagnostic import (
    bounded_lipschitz_distance_2d,
)


def test_bounded_lipschitz_distance_2d_raises_without_scipy() -> None:
    """Negative path: scipy missing -> ImportError (not silent greedy fallback)."""
    # Simulate scipy.optimize.linear_sum_assignment being unavailable.
    # The ``linear_sum_assignment`` symbol is imported lazily inside the
    # function under test, so stubbing the parent ``scipy.optimize``
    # module is sufficient to trigger the ImportError branch.
    with patch.dict(sys.modules, {"scipy.optimize": None}), pytest.raises(
        ImportError, match=r"scipy>=1\.7"
    ):
        bounded_lipschitz_distance_2d(
            left=[[0.0, 0.0], [1.0, 1.0]],
            right=[[0.5, 0.5], [1.5, 1.5]],
        )


def test_bounded_lipschitz_distance_2d_importerror_message_names_pip_install() -> None:
    """The error message must include an actionable install hint."""
    with patch.dict(sys.modules, {"scipy.optimize": None}), pytest.raises(
        ImportError
    ) as exc_info:
        bounded_lipschitz_distance_2d(
            left=[[0.0, 0.0], [1.0, 1.0]],
            right=[[0.5, 0.5], [1.5, 1.5]],
        )
    message = str(exc_info.value)
    # The Hungarian-algorithm symbol name is what makes the requirement
    # unambiguous — a bare "install scipy" would not satisfy the
    # Theorem-1 contract, which needs the assignment solver specifically.
    assert "linear_sum_assignment" in message
    assert "pip install" in message


def test_bounded_lipschitz_distance_2d_with_scipy() -> None:
    """Happy path: scipy present -> exact BL distance."""
    left = [[0.0, 0.0], [1.0, 1.0]]
    right = [[0.5, 0.5], [1.5, 1.5]]
    distance = bounded_lipschitz_distance_2d(left, right)
    assert isinstance(distance, float)
    assert distance >= 0.0
    # Hungarian-optimal coupling matches each point to its diagonal twin;
    # both legs have Euclidean distance sqrt(0.5**2 + 0.5**2) = sqrt(1/2).
    assert distance == pytest.approx(2 ** -0.5, rel=1e-9)


def test_bounded_lipschitz_distance_2d_input_validation_runs_before_scipy_check() -> None:
    """Input validation must happen before the scipy import attempt.

    Even with scipy missing, malformed inputs should raise
    :class:`ValueError` — not be masked by the ImportError. This keeps
    the diagnostic surface stable regardless of environment.
    """
    with patch.dict(sys.modules, {"scipy.optimize": None}), pytest.raises(ValueError):
        bounded_lipschitz_distance_2d(
            left=[[0.0, 0.0]],
            right=[[0.0, 0.0]],
            bound=0.0,
        )
