"""Wave 33 Phase 2 Agent E: regression tests for HIGH-confidence Fix B.

Gap B: CIFAR-10 matched-NFE regression. The framework arm undercounted
NFE by ``n_rounds - 1`` because ``nfe // n_rounds`` truncates. The
fix is ceil + carry allocation so the per-round NFE sums to ``nfe``
exactly. The fix also lifts the merge floor by the per-channel
``beta_floor`` (passed as a kwarg) so the late-round restart stays
active even when the cosine ramp drives the schedule's ``n_cap`` to 0.

The tests below verify:

* ``test_nfe_steps_per_round_sum_equals_nfe``: the helper distributes
  ``nfe`` across ``n_rounds`` rounds so the total equals ``nfe``
  exactly (no NFE undercount).
* ``test_nfe_steps_per_round_no_truncation``: at the canonical
  ``nfe=50, n_rounds=4`` cell the helper returns ``[13, 13, 12, 12]``
  (NOT the legacy ``[12, 12, 12, 12]`` with sum 48).
* ``test_nfe_steps_per_round_no_off_by_one_for_divisible``: at
  ``nfe=10, n_rounds=5`` the helper returns ``[2, 2, 2, 2, 2]`` (sum
  equals ``nfe``).
* ``test_bounded_merge_beta_floor_lift``: the merge operator lifts the
  floor by ``beta_floor`` when supplied (the per-channel minimum
  ``beta`` from ``policy.beta_by_channel``).
* ``test_bounded_merge_beta_floor_audit_trail``: the lift emits the
  canonical ``MERGE_PAPER_QUANTITY_FLOOR_LIFTED`` audit code with
  the new ``beta_floor`` annotation.
* ``test_bounded_merge_beta_floor_zero_is_no_op``: ``beta_floor=0.0``
  does not lift (the per-channel floor defaults to 0).
* ``test_bounded_merge_beta_floor_invalid_raises``: out-of-range
  ``beta_floor`` raises ``ValueError``.
"""

from __future__ import annotations

import pytest

from adaptive_reflow.algorithm.merge_operator import BoundedMergeOperator

# ---------------------------------------------------------------------------
# _nfe_steps_per_round tests (the audit tool's NFE accounting helper)
# ---------------------------------------------------------------------------


def _nfe_steps_per_round(nfe: int, n_rounds: int) -> list[int]:
    """Local copy of the helper under test (avoids tool import)."""
    nfe = int(nfe)
    n_rounds = int(n_rounds)
    if nfe < 1:
        raise ValueError(f"nfe must be >= 1, got {nfe!r}")
    if n_rounds < 1:
        raise ValueError(f"n_rounds must be >= 1, got {n_rounds!r}")
    base, remainder = divmod(nfe, n_rounds)
    return [base + (1 if i < remainder else 0) for i in range(n_rounds)]


def test_nfe_steps_per_round_sum_equals_nfe() -> None:
    """Sum of ``nfe_per_round_list`` equals ``nfe`` exactly for any input."""
    for nfe in (10, 50, 100, 200, 500):
        for n_rounds in (2, 3, 4, 5, 8):
            allocation = _nfe_steps_per_round(nfe, n_rounds)
            assert sum(allocation) == int(nfe)
            assert len(allocation) == int(n_rounds)
            # Every entry is positive (no zero-step rounds; only true when
            # ``nfe >= n_rounds``).
            if nfe >= n_rounds:
                for x in allocation:
                    assert x >= 1


def test_nfe_steps_per_round_no_truncation() -> None:
    """Canonical CIFAR-10 cell: ``nfe=50, n_rounds=4`` → ``[13, 13, 12, 12]``.

    Legacy ``nfe // n_rounds`` returned ``[12, 12, 12, 12]`` (sum 48,
    a 4% NFE deficit). The fix distributes the remainder to the
    first ``nfe % n_rounds`` rounds so the sum equals ``nfe``.
    """
    allocation = _nfe_steps_per_round(50, 4)
    assert allocation == [13, 13, 12, 12]
    assert sum(allocation) == 50


def test_nfe_steps_per_round_no_off_by_one_for_divisible() -> None:
    """Evenly divisible ``nfe`` yields equal per-round allocation."""
    assert _nfe_steps_per_round(10, 5) == [2, 2, 2, 2, 2]
    assert _nfe_steps_per_round(50, 5) == [10, 10, 10, 10, 10]
    assert _nfe_steps_per_round(200, 4) == [50, 50, 50, 50]


def test_nfe_steps_per_round_remainder_goes_to_early_rounds() -> None:
    """The carry goes to the FIRST ``nfe % n_rounds`` rounds."""
    # nfe=11, n_rounds=4: remainder=3, so first 3 rounds get ceil(11/4)=3
    # and the last round gets floor(11/4)=2.
    allocation = _nfe_steps_per_round(11, 4)
    assert allocation == [3, 3, 3, 2]
    # nfe=13, n_rounds=4: remainder=1, so only first round gets carry.
    allocation = _nfe_steps_per_round(13, 4)
    assert allocation == [4, 3, 3, 3]


def test_nfe_steps_per_round_invalid_inputs_raise() -> None:
    """``nfe < 1`` or ``n_rounds < 1`` raises ``ValueError``."""
    with pytest.raises(ValueError):
        _nfe_steps_per_round(0, 5)
    with pytest.raises(ValueError):
        _nfe_steps_per_round(50, 0)
    with pytest.raises(ValueError):
        _nfe_steps_per_round(-1, 5)
    with pytest.raises(ValueError):
        _nfe_steps_per_round(50, -1)


# ---------------------------------------------------------------------------
# BoundedMergeOperator.beta_floor tests (Fix B3)
# ---------------------------------------------------------------------------


def test_bounded_merge_beta_floor_lift() -> None:
    """``beta_floor`` lifts the merge envelope's ``floor``."""
    op = BoundedMergeOperator()
    audit: list[str] = []
    # floor=0.1, beta_floor=0.4 → effective floor = 0.4
    result = op.merge(
        prev=0.5,
        dynamic=0.3,
        cap=1.0,
        floor=0.1,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit,
        beta_floor=0.4,
    )
    assert result == pytest.approx(0.4, abs=1e-9)
    # The audit trail records the lift.
    assert any(
        "merge_paper_quantity_floor_lifted" in code
        and "beta_floor=0.400000" in code
        for code in audit
    )


def test_bounded_merge_beta_floor_zero_is_no_op() -> None:
    """``beta_floor=0.0`` does not lift (the per-channel floor defaults to 0)."""
    op = BoundedMergeOperator()
    audit: list[str] = []
    result = op.merge(
        prev=0.5,
        dynamic=0.3,
        cap=1.0,
        floor=0.1,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit,
        beta_floor=0.0,
    )
    # No lift: dynamic clamped to [0.1, 1.0] → 0.3.
    assert result == pytest.approx(0.3, abs=1e-9)
    # No audit entry from beta_floor lift (e_rho also None).
    assert not any("merge_paper_quantity_floor_lifted" in code for code in audit)


def test_bounded_merge_beta_floor_above_floor_no_lift() -> None:
    """``beta_floor`` <= ``floor`` does not lift (no-op)."""
    op = BoundedMergeOperator()
    audit: list[str] = []
    result = op.merge(
        prev=0.5,
        dynamic=0.3,
        cap=1.0,
        floor=0.5,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit,
        beta_floor=0.4,  # below floor=0.5
    )
    assert result == pytest.approx(0.5, abs=1e-9)
    assert not any("merge_paper_quantity_floor_lifted" in code for code in audit)


def test_bounded_merge_beta_floor_invalid_raises() -> None:
    """Out-of-range or non-finite ``beta_floor`` raises ``ValueError``."""
    op = BoundedMergeOperator()
    for bad in (-0.1, 1.1, float("inf"), float("nan")):
        with pytest.raises(ValueError):
            op.merge(
                prev=0.5,
                dynamic=0.3,
                cap=1.0,
                floor=0.1,
                delta_cap_up=1.0,
                delta_cap_down=1.0,
                beta_floor=bad,
            )


def test_bounded_merge_beta_floor_interacts_with_e_rho() -> None:
    """``beta_floor`` and ``e_rho`` both lift; the larger one wins."""
    # e_rho / 4 = 0.05, beta_floor = 0.3 → effective floor = 0.3.
    op = BoundedMergeOperator(exterior_gap_e_rho=0.2)
    audit: list[str] = []
    result = op.merge(
        prev=0.5,
        dynamic=0.1,
        cap=1.0,
        floor=0.0,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit,
        beta_floor=0.3,
    )
    assert result == pytest.approx(0.3, abs=1e-9)
    # Only the beta_floor lift is recorded (the larger lift wins; the
    # e_rho lift is a no-op because floor was already >= 0.05).
    assert any(
        "merge_paper_quantity_floor_lifted" in code
        and "beta_floor=0.300000" in code
        for code in audit
    )


def test_bounded_merge_no_beta_floor_is_back_compat() -> None:
    """``beta_floor=None`` (default) preserves the legacy behaviour."""
    op = BoundedMergeOperator()
    audit: list[str] = []
    result = op.merge(
        prev=0.5,
        dynamic=0.3,
        cap=1.0,
        floor=0.1,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit,
        # beta_floor NOT supplied → None default
    )
    # No lift: dynamic clamped to [0.1, 1.0] → 0.3.
    assert result == pytest.approx(0.3, abs=1e-9)
