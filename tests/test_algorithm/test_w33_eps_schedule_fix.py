"""Wave 33 Phase 2 Agent E: regression tests for the HIGH-confidence fixes.

Gap A: ``CodimensionSheetScheduler.sample`` used to plug a constant
``eps_implicit`` into the per-round closed form. Paper Theorem 1's
``eps -> 0`` is realised as a *schedule* (``eps(r) = eps_0 * (1 - u_r)``)
across the cycle, not as a constant scale. The fix is bit-safe at
``r=0`` (matches the legacy constant) and changes the cycle's terminal
round to actually exercise the paper's sheet-dominance limit.

The tests below verify the new per-round ``eps`` schedule:

* ``test_eps_per_round_diminishes_in_decreasing_direction``: at every
  round ``r`` the sample's ``eps_implicit`` equals
  ``eps_0 * (1 - u_r)`` (floored at ``1e-9``).
* ``test_eps_per_round_diminishes_in_increasing_direction``: legacy
  ``"increasing"`` reverses the ramp (``eps(r) = eps_0 * u_r``) for
  back-compat with the prior cosine-based interpretation.
* ``test_eps_per_round_floor_at_terminal_round``: at ``r=L-1`` the
  per-round ``eps`` is clamped at the canonical floor ``1e-9``
  (avoiding the ``eps=0`` degenerate cell-collapse).
* ``test_r0_matches_legacy_constant``: at ``r=0`` the per-round ``eps``
  equals the constructor constant; the fix is bit-safe for legacy
  callers.
* ``test_paper_quantity_path_uses_per_round_eps``: the
  paper-quantity-augmented path (with ``profile_residual_fn``
  configured) also receives the per-round ``eps`` so the cycle's
  terminal round actually exercises ``eps -> 0``.
"""

from __future__ import annotations

import math

import pytest

from adaptive_reflow.algorithm.scheduler._core import (
    CodimensionSheetScheduler,
    _paper_evidence_balance,
)


def test_eps_per_round_diminishes_in_decreasing_direction() -> None:
    """Per-round ``eps`` decreases monotonically under ``decreasing``."""
    eps_0 = 0.05
    cycle_length = 10
    codim = CodimensionSheetScheduler(
        cycle_length=cycle_length,
        n_min=0.0,
        n_max=1.0,
        eps_implicit=eps_0,
        eps_direction="decreasing",
    )
    prev = float("inf")
    for r in range(cycle_length):
        sample = codim.sample(0, r, r)
        u_r = float(r) / (cycle_length - 1)
        expected = max(eps_0 * (1.0 - u_r), 1e-9)
        assert sample.eps_implicit == pytest.approx(expected, abs=1e-12)
        # Monotone non-increasing under decreasing direction.
        assert sample.eps_implicit <= prev + 1e-15
        prev = float(sample.eps_implicit)


def test_eps_per_round_diminishes_in_increasing_direction() -> None:
    """Per-round ``eps`` increases monotonically under legacy ``increasing``."""
    eps_0 = 0.05
    cycle_length = 10
    codim = CodimensionSheetScheduler(
        cycle_length=cycle_length,
        n_min=0.0,
        n_max=1.0,
        eps_implicit=eps_0,
        eps_direction="increasing",
    )
    with pytest.warns(DeprecationWarning):
        prev = 0.0
        for r in range(cycle_length):
            sample = codim.sample(0, r, r)
            u_r = float(r) / (cycle_length - 1)
            expected = max(eps_0 * u_r, 1e-9)
            assert sample.eps_implicit == pytest.approx(expected, abs=1e-12)
            # Monotone non-decreasing under legacy increasing.
            assert sample.eps_implicit >= prev - 1e-15
            prev = float(sample.eps_implicit)


def test_eps_per_round_floor_at_terminal_round() -> None:
    """At ``r=L-1`` the per-round ``eps`` is clamped at the floor ``1e-9``.

    Without the floor, ``eps_per_round = eps_0 * (1 - 1) = 0`` would
    collapse the cell side of the closed form to zero (``ratio -> 0``)
    even when the sheet side is also zero (``sheet = max(n_base, 0) = 0``).
    The floor preserves the paper-aligned "sheet dominates" limit.
    """
    eps_0 = 0.05
    cycle_length = 5
    codim = CodimensionSheetScheduler(
        cycle_length=cycle_length,
        n_min=0.0,
        n_max=1.0,
        eps_implicit=eps_0,
    )
    sample = codim.sample(0, cycle_length - 1, cycle_length - 1)
    assert sample.eps_implicit == pytest.approx(1e-9, abs=1e-15)


def test_r0_matches_legacy_constant() -> None:
    """At ``r=0`` the per-round ``eps`` equals the constructor constant.

    The fix is bit-safe for legacy callers that previously expected
    ``sample.eps_implicit == eps_implicit`` at the first round.
    """
    eps_0 = 0.05
    codim = CodimensionSheetScheduler(
        cycle_length=10,
        n_min=0.0,
        n_max=1.0,
        eps_implicit=eps_0,
    )
    sample = codim.sample(0, 0, 0)
    assert sample.eps_implicit == pytest.approx(eps_0, abs=1e-15)


def test_paper_quantity_path_uses_per_round_eps() -> None:
    """The paper-quantity-augmented path also receives per-round ``eps``."""
    profile = lambda x: math.sin(x)  # noqa: E731

    eps_0 = 0.05
    cycle_length = 4
    codim = CodimensionSheetScheduler(
        cycle_length=cycle_length,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=profile,
        eps_implicit=eps_0,
    )
    # Cache paper quantities are round-independent; verify the per-round
    # ratio matches the paper-quantity closed form using per-round eps.
    sheet_A = float(codim.sheet_A)
    packing_B = float(codim.packing_B)
    cell_C = float(codim.cell_C)
    for r in range(cycle_length):
        sample = codim.sample(0, r, r)
        u_r = float(r) / (cycle_length - 1)
        eps_per_round = max(eps_0 * (1.0 - u_r), 1e-9)
        expected_ratio = _paper_evidence_balance(
            0.0,
            eps_per_round,
            sheet_A=sheet_A,
            packing_B=packing_B,
            cell_C=cell_C,
        )
        assert sample.evidence_ratio == pytest.approx(expected_ratio, abs=1e-12)


def test_constructor_eps_implicit_unchanged_for_backcompat() -> None:
    """``CodimensionSheetScheduler.eps_implicit`` returns the constructor value.

    P2-W33-A: the constructor constant ``eps_implicit`` remains
    introspectable via the ``eps_implicit`` property for back-compat
    with code that reads the configured scale. The per-round value
    lives on the ``ScheduleSample``.
    """
    codim = CodimensionSheetScheduler(
        cycle_length=10, n_min=0.0, n_max=1.0, eps_implicit=0.123
    )
    assert codim.eps_implicit == pytest.approx(0.123, abs=1e-15)
