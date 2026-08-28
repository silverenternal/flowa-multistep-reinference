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

import math

import pytest

from adaptive_reflow.algorithm import (
    BoundedMergeOperator,
    EMAOperator,
    IdentityOperator,
    MergeAuthorityError,
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


# ---------------------------------------------------------------------------
# 6. P0-3 — operators MUST return a finite float in [0, 1]; no raising on
# legitimate caller inputs.
# ---------------------------------------------------------------------------


def test_p0_3_bounded_merge_operator_clips_cap_above_one() -> None:
    """P0-3: ``cap > 1`` clips to ``1.0`` and emits
    :data:`MERGE_DEGENERATE_INTERVAL` (or the canonical cap audit
    code) rather than raising :exc:`MergeAuthorityError`."""
    op = BoundedMergeOperator()
    audit: list[str] = []
    result = op.merge(
        prev=0.5,
        dynamic=0.5,
        cap=1.5,  # out of [0, 1] -> clipped to 1.0
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
        audit_codes=audit,
    )
    # Result is in [0, 1].
    assert 0.0 <= result <= 1.0
    # Audit trail carries the canonical cap-out-of-range code (the
    # cap is clipped so we observe its clipped value).
    assert any("merge_cap_out_of_range" in code for code in audit)
    # The degenerate interval path should NOT fire because
    # cap=1.0 > prev=0.5 with delta_cap_down=0.5 keeps the interval
    # non-empty.
    assert not any("merge_degenerate_interval" in code for code in audit)


def test_p0_3_bounded_merge_operator_clips_cap_below_floor() -> None:
    """P0-3: ``cap < floor`` swaps the envelope and emits the
    canonical ``merge_cap_below_floor`` audit code rather than
    raising."""
    op = BoundedMergeOperator()
    audit: list[str] = []
    result = op.merge(
        prev=0.3,
        dynamic=0.5,
        cap=0.2,
        floor=0.7,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
        audit_codes=audit,
    )
    assert 0.0 <= result <= 1.0
    # ``cap < floor`` is the configuration error path; after clipping
    # the swap the merge is total and the audit line is recorded.
    assert any("merge_cap_below_floor" in code for code in audit)


def test_p0_3_bounded_merge_operator_never_raises_on_finite_inputs() -> None:
    """P0-3: no legitimate (numeric, finite) input raises; the
    operator only raises on ``None`` / non-numeric types at the
    coercion boundary.
    """
    op = BoundedMergeOperator()
    for prev, dynamic, cap, floor, up, down in [
        # envelope edge cases
        (0.5, 0.5, 1.5, 0.0, 1.0, 1.0),
        (0.5, 0.5, 0.5, 1.5, 1.0, 1.0),
        (0.5, 0.5, 0.2, 0.7, 1.0, 1.0),
        (0.5, 0.5, 1.0, -0.1, 1.0, 1.0),
        (0.5, 0.5, 1.0, 0.0, 1.5, 1.0),
        (0.5, 0.5, 1.0, 0.0, 1.0, -0.1),
    ]:
        result = op.merge(
            prev=prev,
            dynamic=dynamic,
            cap=cap,
            floor=floor,
            delta_cap_up=up,
            delta_cap_down=down,
        )
        assert 0.0 <= result <= 1.0
        assert math.isfinite(result)


def test_p0_3_bounded_merge_operator_raises_only_on_non_numeric() -> None:
    """P0-3: the coercion boundary (non-numeric ``None`` / string)
    is the only point that may raise :exc:`MergeAuthorityError`.
    """
    op = BoundedMergeOperator()
    with pytest.raises(MergeAuthorityError):
        op.merge(
            prev=None,
            dynamic=0.5,
            cap=1.0,
            floor=0.0,
            delta_cap_up=0.5,
            delta_cap_down=0.5,
        )
    with pytest.raises(MergeAuthorityError):
        op.merge(
            prev=0.5,
            dynamic=0.5,
            cap="not-a-number",
            floor=0.0,
            delta_cap_up=0.5,
            delta_cap_down=0.5,
        )


def test_p0_3_bounded_merge_operator_non_finite_prev_clipped() -> None:
    """P0-3: non-finite ``prev`` is clipped into ``[0, 1]`` and the
    canonical :data:`MERGE_NONFINITE_PREV_CLIPPED` audit code is
    appended.
    """
    import math

    op = BoundedMergeOperator()
    audit: list[str] = []
    # ``prev = nan`` triggers the non-finite prev clip path.
    result = op.merge(
        prev=float("nan"),
        dynamic=0.5,
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
        audit_codes=audit,
    )
    assert 0.0 <= result <= 1.0
    assert math.isfinite(result)
    assert any("merge_nonfinite_prev_clipped" in code for code in audit)


def test_p0_3_identity_operator_clips_non_finite_dynamic() -> None:
    """P0-3: ``IdentityOperator.merge`` clips non-finite / out-of-range
    ``dynamic`` into ``[0, 1]`` rather than raising. ``NaN``
    becomes ``0.0`` and ``inf`` becomes ``1.0``.
    """
    import math

    op = IdentityOperator()
    audit: list[str] = []
    # ``NaN`` -> ``0.0``.
    result_nan = op.merge(
        prev=0.5,
        dynamic=float("nan"),
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
        audit_codes=audit,
    )
    assert result_nan == pytest.approx(0.0)
    assert any("merge_nonfinite_dynamic_clipped" in code for code in audit)
    # ``inf`` -> ``1.0``.
    audit.clear()
    result_inf = op.merge(
        prev=0.5,
        dynamic=float("inf"),
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
        audit_codes=audit,
    )
    assert result_inf == pytest.approx(1.0)
    assert any("merge_nonfinite_dynamic_clipped" in code for code in audit)
    # Out-of-range ``1.5`` -> ``1.0``.
    audit.clear()
    result_high = op.merge(
        prev=0.5,
        dynamic=1.5,
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
        audit_codes=audit,
    )
    assert result_high == pytest.approx(1.0)
    # ``-0.1`` -> ``0.0``.
    audit.clear()
    result_low = op.merge(
        prev=0.5,
        dynamic=-0.1,
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
        audit_codes=audit,
    )
    assert result_low == pytest.approx(0.0)


def test_p0_3_ema_operator_clips_non_finite_inputs() -> None:
    """P0-3: ``EMAOperator.merge`` clips non-finite / out-of-range
    ``prev`` and ``dynamic`` into ``[0, 1]`` rather than producing
    a NaN EMA value.
    """
    import math

    op = EMAOperator()
    audit: list[str] = []
    # ``prev = NaN, dynamic = 0.5``: ``prev`` clips to ``0.0``; EMA
    # step ``0.0 + 0.1 * (0.5 - 0.0) = 0.05``.
    result = op.merge(
        prev=float("nan"),
        dynamic=0.5,
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
        audit_codes=audit,
    )
    assert 0.0 <= result <= 1.0
    assert math.isfinite(result)
    assert pytest.approx(0.05) == result
    assert any("merge_nonfinite_prev_clipped" in code for code in audit)
    # ``dynamic = NaN`` also clips to ``0.0``; EMA step
    # ``prev + 0.1 * (0.0 - prev) = 0.9 * prev``. With ``prev = 0.5``
    # the result is ``0.45``.
    audit.clear()
    result2 = op.merge(
        prev=0.5,
        dynamic=float("nan"),
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
        audit_codes=audit,
    )
    assert 0.0 <= result2 <= 1.0
    assert any("merge_nonfinite_dynamic_clipped" in code for code in audit)


# ---------------------------------------------------------------------------
# 7. P0-3 — protocol contract declaration (the contract is documented on
# the Protocol class; the unit tests below verify the contract is honoured
# by all three operators.
# ---------------------------------------------------------------------------


def test_p0_3_all_operators_return_finite_float_in_unit_interval() -> None:
    """P0-3 contract: every ``MergeOperatorProtocol`` implementation
    MUST return a finite ``float`` in ``[0, 1]`` for any combination
    of legitimate (numeric) caller inputs.
    """
    import math

    cases = [
        # (prev, dynamic, cap, floor, up, down)
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        (1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
        (0.5, 0.5, 1.0, 0.0, 0.5, 0.5),
        (0.7, 0.2, 0.5, 0.1, 0.5, 0.5),
        # extreme envelopes (clipped, not raised)
        (0.5, 0.5, 2.0, -1.0, 2.0, -1.0),
    ]
    for op in (
        BoundedMergeOperator(),
        IdentityOperator(),
        EMAOperator(),
    ):
        for prev, dynamic, cap, floor, up, down in cases:
            result = op.merge(
                prev=prev,
                dynamic=dynamic,
                cap=cap,
                floor=floor,
                delta_cap_up=up,
                delta_cap_down=down,
            )
            assert isinstance(result, float)
            assert math.isfinite(result)
            assert 0.0 <= result <= 1.0


# ---------------------------------------------------------------------------
# from_config / to_config round-trip (P1-1) — merge operators
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "operator",
    [
        BoundedMergeOperator(tolerance=1e-9),
        BoundedMergeOperator(tolerance=1e-6),
        IdentityOperator(),
        EMAOperator(alpha=0.2),
        EMAOperator(),  # default
    ],
)
def test_merge_operator_config_round_trip(operator) -> None:
    """``operator == cls.from_config(operator.to_config())`` byte-for-byte."""
    config = operator.to_config()
    if isinstance(operator, BoundedMergeOperator):
        rebuilt = BoundedMergeOperator.from_config(config)
    elif isinstance(operator, IdentityOperator):
        rebuilt = IdentityOperator.from_config(config)
    elif isinstance(operator, EMAOperator):
        rebuilt = EMAOperator.from_config(config)
    else:  # pragma: no cover
        raise AssertionError("unhandled operator")
    assert type(rebuilt) is type(operator)
    assert rebuilt.to_config() == config
    # ``merge`` outputs agree on a canonical input.
    result_orig = operator.merge(
        prev=0.3,
        dynamic=0.7,
        cap=0.5,
        floor=0.1,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
    )
    result_rebuilt = rebuilt.merge(
        prev=0.3,
        dynamic=0.7,
        cap=0.5,
        floor=0.1,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
    )
    assert result_orig == pytest.approx(result_rebuilt)
