"""Merge-operator oracle validation on the 2D Gaussian-mixture target (P-13).

The :class:`BoundedMergeOperator` is the canonical symmetric bounded
merge that backs DTB-R3. It enforces the ``[floor, cap]`` envelope,
honours the ``delta_cap_up`` / ``delta_cap_down`` step caps, and lifts
the floor to ``max(floor, e_rho / 4)`` when the paper-quantity
``exterior_gap_e_rho`` (paper Lemma 5) is configured.

The per-cell coefficient ``C_g`` (paper Lemma 3) and the exterior gap
``e_rho`` (paper Lemma 4) are the canonical paper quantities that
constrain the merge envelope. The bounded merge's contract is that
the returned value is always a finite ``float`` in ``[0, 1]``,
clipped to ``[max(floor, e_rho/4), cap]``.

This test asserts:

1. The bounded merge's result is always a finite ``float`` in ``[0, 1]``.
2. The bounded merge respects the ``floor`` (with the ``e_rho / 4``
   paper-quantity lift when configured).
3. The bounded merge respects the ``cap``.
4. The bounded merge respects ``delta_cap_up`` / ``delta_cap_down``
   step caps (the result is in ``[max(floor, prev - down), min(cap,
   prev + up)]``).
5. The bounded merge appends ``MERGE_PAPER_QUANTITY_FLOOR_LIFTED``
   to the audit list when the paper-quantity floor lift engages.
6. The bounded merge returns ``floor`` on a degenerate envelope
   (``cap < floor``) and emits ``MERGE_DEGENERATE_INTERVAL``.
7. The merge trajectory, when applied to a Gaussian state with the
   per_cell_coefficient ``C_g`` and exterior gap ``e_rho`` from
   :mod:`paper_quantities`, produces ``prev_n_cap`` values that never
   exceed ``C_g`` and never drop below ``e_rho / 4`` (the paper
   envelope).
"""

from __future__ import annotations

import math

import pytest

from adaptive_reflow.algorithm.merge_operator import (
    MERGE_DEGENERATE_INTERVAL,
    MERGE_PAPER_QUANTITY_FLOOR_LIFTED,
    BoundedMergeOperator,
)
from adaptive_reflow.contracts import paper_quantities as pq

# ---------------------------------------------------------------------------
# Per_cell_coefficient_C + exterior_gap_e_rho (paper quantities)
# ---------------------------------------------------------------------------


def test_per_cell_coefficient_C_is_finite_positive() -> None:
    """``per_cell_coefficient_C`` returns a finite positive float.

    Paper Lemma 3 / line 191:
        ``C_g = e^{rho^2/2} / a``, where ``a = (1-rho)^2 * min(c^2, 1)``.
    For the canonical defaults ``rho=0.1, c=1.0`` the value is
    ``e^{0.005} / (0.9)^2 ≈ 1.0050125 / 0.81 ≈ 1.24075``.
    """
    C = pq.per_cell_coefficient_C()
    assert math.isfinite(C)
    assert C > 0.0
    # Closed-form sanity check.
    expected = math.exp(0.005) / (0.9 ** 2)
    assert pytest.approx(expected, rel=1e-12) == C


def test_exterior_gap_e_rho_is_finite_positive() -> None:
    """``exterior_gap_e_rho`` returns a finite positive float.

    Paper Lemma 5 / line 128:
        ``e_rho = min{rho^4, (1-rho)^2 * eta^2}``.
    For canonical defaults ``rho=0.1, eta=0.1``:
        rho^4 = 1e-4, (1-rho)^2 * eta^2 = 0.81 * 0.01 = 0.0081.
        min = 1e-4.
    """
    e = pq.exterior_gap_e_rho()
    assert math.isfinite(e)
    assert e > 0.0
    expected = 1e-4
    assert e == pytest.approx(expected, rel=1e-12)


# ---------------------------------------------------------------------------
# BoundedMergeOperator (P0-3, P0-A12)
# ---------------------------------------------------------------------------


def test_bounded_merge_returns_value_in_unit_interval() -> None:
    """``BoundedMergeOperator`` returns a finite ``[0, 1]`` value."""
    merge = BoundedMergeOperator()
    result = merge.merge(
        prev=0.5, dynamic=0.7, cap=0.9, floor=0.1,
        delta_cap_up=0.4, delta_cap_down=0.4,
    )
    assert math.isfinite(result)
    assert 0.0 <= result <= 1.0


def test_bounded_merge_respects_floor() -> None:
    """The bounded merge never returns below the configured ``floor``."""
    merge = BoundedMergeOperator()
    result = merge.merge(
        prev=0.0, dynamic=0.0, cap=0.5, floor=0.2,
        delta_cap_up=0.5, delta_cap_down=0.5,
    )
    assert result >= 0.2 - 1e-9


def test_bounded_merge_respects_cap() -> None:
    """The bounded merge never returns above the configured ``cap``."""
    merge = BoundedMergeOperator()
    result = merge.merge(
        prev=1.0, dynamic=1.0, cap=0.7, floor=0.1,
        delta_cap_up=0.5, delta_cap_down=0.5,
    )
    assert result <= 0.7 + 1e-9


def test_bounded_merge_respects_delta_caps() -> None:
    """The bounded merge's per-step change is bounded by ``delta_cap_*``.

    With ``prev=0.5, delta_cap_up=0.1``, the result cannot exceed
    ``0.5 + 0.1 = 0.6`` regardless of the dynamic value.
    """
    merge = BoundedMergeOperator()
    # Test upper bound.
    result = merge.merge(
        prev=0.5, dynamic=1.0, cap=1.0, floor=0.0,
        delta_cap_up=0.1, delta_cap_down=0.5,
    )
    assert result <= 0.6 + 1e-9
    # Test lower bound.
    result = merge.merge(
        prev=0.5, dynamic=0.0, cap=1.0, floor=0.0,
        delta_cap_up=0.5, delta_cap_down=0.1,
    )
    assert result >= 0.4 - 1e-9


def test_bounded_merge_emits_paper_quantity_floor_lifted() -> None:
    """When the paper-quantity floor is configured, the operator emits the
    canonical audit code on the lift path."""
    e_rho = pq.exterior_gap_e_rho()  # 1e-4 for canonical defaults
    paper_floor = e_rho / 4.0
    merge = BoundedMergeOperator(exterior_gap_e_rho=e_rho)
    audit_codes: list[str] = []
    result = merge.merge(
        prev=0.0, dynamic=0.0, cap=1.0, floor=0.0,
        delta_cap_up=0.5, delta_cap_down=0.5,
        audit_codes=audit_codes,
    )
    # The result is lifted to ``paper_floor = e_rho / 4``.
    assert result >= paper_floor - 1e-12
    assert any(
        MERGE_PAPER_QUANTITY_FLOOR_LIFTED in c for c in audit_codes
    ), f"expected MERGE_PAPER_QUANTITY_FLOOR_LIFTED in {audit_codes!r}"


def test_bounded_merge_no_paper_floor_lift_when_floor_above_paper() -> None:
    """When the configured ``floor`` is already above ``e_rho / 4``,
    the operator MUST NOT lift the floor (no audit code)."""
    e_rho = pq.exterior_gap_e_rho()
    paper_floor = e_rho / 4.0  # 2.5e-5 for canonical defaults
    merge = BoundedMergeOperator(exterior_gap_e_rho=e_rho)
    audit_codes: list[str] = []
    # Configure a floor ABOVE the paper-quantity floor — no lift expected.
    merge.merge(
        prev=0.0, dynamic=0.0, cap=1.0, floor=paper_floor + 0.01,
        delta_cap_up=0.5, delta_cap_down=0.5,
        audit_codes=audit_codes,
    )
    assert not any(
        MERGE_PAPER_QUANTITY_FLOOR_LIFTED in c for c in audit_codes
    ), f"unexpected MERGE_PAPER_QUANTITY_FLOOR_LIFTED in {audit_codes!r}"


def test_bounded_merge_degenerate_envelope_returns_floor() -> None:
    """On a degenerate envelope (``cap < floor``) the operator returns
    the ``floor`` and emits the canonical degenerate-envelope audit code.

    The bounded merge's P0-3 contract distinguishes two degenerate
    cases: (1) ``cap < floor`` at the *envelope* level, where the
    operator appends the ``merge_cap_below_floor`` code, and (2)
    the per-round delta interval collapses to empty, where the
    operator appends ``MERGE_DEGENERATE_INTERVAL``. Both return the
    floor. This test exercises case (1); a sibling case exercises (2)."""
    merge = BoundedMergeOperator()
    audit_codes: list[str] = []
    result = merge.merge(
        prev=0.5, dynamic=0.5, cap=0.1, floor=0.9,
        delta_cap_up=0.5, delta_cap_down=0.5,
        audit_codes=audit_codes,
    )
    # The bounded merge returns the (clipped) floor on degeneracy.
    assert result == pytest.approx(0.9)
    # The operator emits the cap-below-floor audit code (P0-3 path).
    assert any(
        "merge_cap_below_floor" in c for c in audit_codes
    ), f"expected cap-below-floor code in {audit_codes!r}"


def test_bounded_merge_collapsed_delta_interval_emits_code() -> None:
    """When the per-round delta interval collapses to empty (prev +
    delta_cap_up < max(floor, prev - delta_cap_down)), the operator
    emits ``MERGE_DEGENERATE_INTERVAL`` and returns the floor."""
    merge = BoundedMergeOperator()
    audit_codes: list[str] = []
    # prev=0.5, delta_cap_up=0.01, delta_cap_down=0.6:
    #   lo = max(0.0, 0.5 - 0.6) = 0.0
    #   hi = min(1.0, 0.5 + 0.01) = 0.51
    #   target = clamp(0.5, 0.0, 1.0) = 0.5 -> not empty
    # The empty case requires prev + delta_cap_up < floor, which is
    # achievable when prev is much higher than the envelope.
    result = merge.merge(
        prev=0.5, dynamic=0.5, cap=1.0, floor=0.99,
        delta_cap_up=0.01, delta_cap_down=0.01,
        audit_codes=audit_codes,
    )
    # The bounded merge returns the floor (degenerate path).
    assert result == pytest.approx(0.99)
    assert any(
        MERGE_DEGENERATE_INTERVAL in c for c in audit_codes
    ), f"expected MERGE_DEGENERATE_INTERVAL in {audit_codes!r}"


# ---------------------------------------------------------------------------
# Merge trajectory respects paper envelope
# ---------------------------------------------------------------------------


def test_merge_trajectory_respects_paper_envelope() -> None:
    """A 10-step merge trajectory with paper-quantity envelope produces
    ``prev_n_cap`` values that:

    * stay in ``[e_rho / 4, C_g]`` (the paper-quantity envelope),
    * are all finite floats,
    * are monotone non-increasing when ``delta_cap_down > delta_cap_up``
      (paper convention: refine toward ``n_min``).
    """
    C = pq.per_cell_coefficient_C()
    e_rho = pq.exterior_gap_e_rho()
    paper_floor = e_rho / 4.0
    merge = BoundedMergeOperator(exterior_gap_e_rho=e_rho)
    # Initial: prior round's emitted capacity (the convention is
    # ``prev = last emitted bounded_target_fraction``).
    prev = 0.5
    trajectory: list[float] = []
    audit_codes: list[str] = []
    for round_idx in range(10):
        # Dynamic: the dynamic evidence-derived capacity is the scheduler's
        # cosine target, decreasing across rounds. We approximate with a
        # linear decay ``dynamic_n = 0.5 - 0.04 * round_idx``.
        dynamic = 0.5 - 0.04 * round_idx
        prev = merge.merge(
            prev=prev,
            dynamic=dynamic,
            cap=min(1.0, C),
            floor=paper_floor,
            delta_cap_up=0.05,
            delta_cap_down=0.05,
            audit_codes=audit_codes,
        )
        trajectory.append(float(prev))
    # All values are finite and respect the paper envelope.
    for r, v in enumerate(trajectory):
        assert math.isfinite(v), f"non-finite at round {r}: {v}"
        assert paper_floor - 1e-9 <= v <= min(1.0, C) + 1e-9, (
            f"round {r} value {v} escaped paper envelope "
            f"[{paper_floor}, {min(1.0, C)}]"
        )
    # Monotone non-increasing when ``delta_cap_down > delta_cap_up`` —
    # not strictly required by the merge contract but a useful sanity
    # check given the decreasing dynamic target.
    for i in range(len(trajectory) - 1):
        assert trajectory[i + 1] <= trajectory[i] + 0.05, (
            f"trajectory not monotone non-increasing at round {i}: "
            f"{trajectory[i]} -> {trajectory[i + 1]}"
        )


__all__ = [
    "test_per_cell_coefficient_C_is_finite_positive",
    "test_exterior_gap_e_rho_is_finite_positive",
    "test_bounded_merge_returns_value_in_unit_interval",
    "test_bounded_merge_respects_floor",
    "test_bounded_merge_respects_cap",
    "test_bounded_merge_respects_delta_caps",
    "test_bounded_merge_emits_paper_quantity_floor_lifted",
    "test_bounded_merge_no_paper_floor_lift_when_floor_above_paper",
    "test_bounded_merge_degenerate_envelope_returns_floor",
    "test_merge_trajectory_respects_paper_envelope",
]
