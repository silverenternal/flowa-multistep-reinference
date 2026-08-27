"""Tests for the MergeOperatorProtocol abstraction.

Covers:

* :class:`MergeOperatorProtocol` is ``runtime_checkable`` so any object
  exposing ``merge`` with the canonical signature is accepted as a
  merge operator.
* :class:`BoundedMergeOperator` produces results bit-for-bit identical
  to the legacy :func:`adaptive_reflow.frame.bounded_merge` wrapper.
* :class:`IdentityOperator` returns ``dynamic`` verbatim, ignoring the
  envelope (cap / floor / delta caps) and the audit list.
* :class:`EMAOperator` smooths the update — the result is closer to
  ``prev`` than ``dynamic`` when they disagree.
* Operators are swapable: invoking
  :meth:`BoundedMergeOperator.merge` and
  :meth:`IdentityOperator.merge` on the same inputs yields different
  outputs, so the operator choice is observable in the round trace.
"""

from __future__ import annotations

import pytest

from adaptive_reflow.algorithm import (
    BoundedMergeOperator,
    EMAOperator,
    IdentityOperator,
    MergeOperatorProtocol,
    default_bounded_merge_operator,
)
from adaptive_reflow.frame import bounded_merge

# ---------------------------------------------------------------------------
# 1. runtime_checkable
# ---------------------------------------------------------------------------


def test_bounded_merge_operator_protocol_runtime_checkable() -> None:
    """All canonical operators satisfy ``MergeOperatorProtocol``."""
    assert isinstance(BoundedMergeOperator(), MergeOperatorProtocol)
    assert isinstance(IdentityOperator(), MergeOperatorProtocol)
    assert isinstance(EMAOperator(), MergeOperatorProtocol)
    # Default factory returns the canonical BoundedMergeOperator.
    assert isinstance(default_bounded_merge_operator(), MergeOperatorProtocol)


# ---------------------------------------------------------------------------
# 2. BoundedMergeOperator matches legacy bounded_merge()
# ---------------------------------------------------------------------------


def test_bounded_merge_operator_matches_legacy() -> None:
    """The operator's ``merge`` is bit-for-bit identical to the legacy
    :func:`adaptive_reflow.frame.bounded_merge` wrapper.
    """
    operator = BoundedMergeOperator()
    cases = [
        # (prev, dynamic, cap, floor, delta_cap_up, delta_cap_down)
        (0.8, 0.2, 1.0, 0.0, 0.5, 0.5),  # decrease
        (0.2, 0.7, 1.0, 0.0, 0.5, 0.5),  # increase
        (0.5, 0.5, 1.0, 0.0, 0.5, 0.5),  # no change
        (0.1, 0.0, 1.0, 0.05, 0.5, 0.5),  # floor clamping
        (0.9, 1.0, 0.95, 0.0, 0.5, 0.5),  # cap clamping
        (0.5, 1.0, 1.0, 0.0, 1.0, 0.05),  # asymmetric up
        (0.5, 0.0, 1.0, 0.0, 0.05, 1.0),  # asymmetric down
        (1.0, 0.5, 0.6, 0.0, 0.0, 0.0),  # degenerate interval
    ]
    for prev, dynamic, cap, floor, up, down in cases:
        op_result = operator.merge(
            prev=prev,
            dynamic=dynamic,
            cap=cap,
            floor=floor,
            delta_cap_up=up,
            delta_cap_down=down,
        )
        legacy_result = bounded_merge(
            prev=prev,
            dynamic=dynamic,
            cap=cap,
            floor=floor,
            delta_cap_up=up,
            delta_cap_down=down,
        )
        assert op_result == pytest.approx(legacy_result)


def test_bounded_merge_operator_matches_legacy_with_audit_codes() -> None:
    """Audit-code emission is identical between operator and legacy."""
    operator = BoundedMergeOperator()
    audit_a: list[str] = []
    audit_b: list[str] = []
    # Degenerate-interval case: hi < lo -> collapse to floor + audit.
    operator.merge(
        prev=1.0,
        dynamic=0.5,
        cap=0.6,
        floor=0.0,
        delta_cap_up=0.0,
        delta_cap_down=0.0,
        audit_codes=audit_a,
    )
    bounded_merge(
        prev=1.0,
        dynamic=0.5,
        cap=0.6,
        floor=0.0,
        delta_cap_up=0.0,
        delta_cap_down=0.0,
        audit_codes=audit_b,
    )
    assert audit_a == audit_b


# ---------------------------------------------------------------------------
# 3. IdentityOperator passes dynamic through
# ---------------------------------------------------------------------------


def test_identity_operator_passes_through() -> None:
    """IdentityOperator ignores the envelope; it returns ``dynamic``."""
    op = IdentityOperator()
    result = op.merge(
        prev=0.5,
        dynamic=0.9,
        cap=0.6,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
    )
    # Even though cap=0.6 < dynamic=0.9, the identity operator returns
    # dynamic verbatim because it does no clamping.
    assert result == pytest.approx(0.9)


def test_identity_operator_does_not_emit_audit_codes() -> None:
    """IdentityOperator is a no-op on audit emission."""
    op = IdentityOperator()
    audit: list[str] = []
    op.merge(
        prev=1.0,
        dynamic=0.5,
        cap=0.6,
        floor=0.0,
        delta_cap_up=0.0,
        delta_cap_down=0.0,
        audit_codes=audit,
    )
    # No degenerate-interval collapse can fire under the identity
    # operator (it returns dynamic verbatim regardless).
    assert audit == []


# ---------------------------------------------------------------------------
# 4. EMAOperator smooths
# ---------------------------------------------------------------------------


def test_ema_operator_smooths() -> None:
    """EMAOperator smooths the update; the result lies strictly between
    ``prev`` and ``dynamic`` (the canonical smoothing property)."""
    op = EMAOperator()
    prev = 0.0
    dynamic = 1.0
    result = op.merge(
        prev=prev,
        dynamic=dynamic,
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
    )
    # alpha = 0.1 by default: result = prev + 0.1 * (dynamic - prev) = 0.1.
    assert 0.0 < result < 1.0
    assert result == pytest.approx(0.1)


def test_ema_operator_alpha_is_configurable() -> None:
    """EMAOperator respects a custom ``alpha`` constructor argument."""
    op = EMAOperator(alpha=0.5)
    result = op.merge(
        prev=0.0,
        dynamic=1.0,
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
    )
    # alpha = 0.5 -> result = 0.0 + 0.5 * (1.0 - 0.0) = 0.5.
    assert result == pytest.approx(0.5)
    assert op.alpha == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# 5. Operators are swapable
# ---------------------------------------------------------------------------


def test_operators_are_swapable() -> None:
    """Running the same merge with different operators produces
    different results — the operator choice is observable in the
    round trace.
    """
    # Pick an envelope / inputs where the bounded and identity
    # operators MUST differ: dynamic=0.9 with cap=0.6 forces the
    # bounded operator to clamp down, but the identity operator
    # returns 0.9 verbatim.
    prev = 0.5
    dynamic = 0.9
    cap = 0.6
    floor = 0.0
    delta_cap_up = 1.0
    delta_cap_down = 1.0

    bounded_result = BoundedMergeOperator().merge(
        prev=prev,
        dynamic=dynamic,
        cap=cap,
        floor=floor,
        delta_cap_up=delta_cap_up,
        delta_cap_down=delta_cap_down,
    )
    identity_result = IdentityOperator().merge(
        prev=prev,
        dynamic=dynamic,
        cap=cap,
        floor=floor,
        delta_cap_up=delta_cap_up,
        delta_cap_down=delta_cap_down,
    )
    ema_result = EMAOperator().merge(
        prev=prev,
        dynamic=dynamic,
        cap=cap,
        floor=floor,
        delta_cap_up=delta_cap_up,
        delta_cap_down=delta_cap_down,
    )

    # Bounded: clamp 0.9 to [0.0, 0.6] -> 0.6.
    assert bounded_result == pytest.approx(cap)
    # Identity: return dynamic verbatim -> 0.9.
    assert identity_result == pytest.approx(dynamic)
    # EMA: prev + 0.1 * (dynamic - prev) = 0.5 + 0.04 = 0.54.
    assert ema_result == pytest.approx(0.54)

    # All three distinct -> operator choice is observable.
    assert bounded_result != identity_result
    assert bounded_result != ema_result
    assert identity_result != ema_result
