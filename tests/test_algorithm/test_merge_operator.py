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
    """P0-3 (F-18) + F5: ``cap < floor`` post-clip returns the
    ``floor`` value and emits the canonical ``merge_cap_below_floor``
    audit code so the runner's loop survives a degenerate envelope.

    Earlier (post-F5) the operator raised
    :exc:`MergeAuthorityError` on ``cap < floor``, which contradicted
    the :data:`MergeOperatorProtocol` docstring ("implementations
    MUST NOT raise on legitimate caller input such as ``cap <
    floor``"). The runner crashed on legitimate envelopes where a
    misconfigured codim scheduler supplied ``n_max < n_min``; the
    fail-closed path now returns the ``floor`` and the audit code
    captures the degenerate envelope so the loop survives.
    """
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
    # Fail-closed: return the floor value rather than raising.
    assert result == pytest.approx(0.7, abs=1e-12)
    # Audit code emitted so downstream audit readers see the
    # degenerate envelope.
    assert any("merge_cap_below_floor" in code for code in audit)


def test_p0_3_bounded_merge_operator_never_raises_on_finite_inputs() -> None:
    """P0-3: no legitimate (numeric, finite) input raises; the
    operator only raises on ``None`` / non-numeric types at the
    coercion boundary. The cap < floor case no longer raises — the
    operator returns ``floor`` and emits the canonical audit code
    (P0-3 fix). See ``test_p0_3_bounded_merge_operator_clips_cap_below_floor``.
    """
    op = BoundedMergeOperator()
    for prev, dynamic, cap, floor, up, down in [
        # envelope edge cases — all cap >= floor post-clip
        (0.5, 0.5, 1.5, 0.0, 1.0, 1.0),
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
# 8. Protocol docstring — non-clamping operators MAY accept audit_codes (P2-4)
# ---------------------------------------------------------------------------


def test_merge_operator_protocol_docstring_documents_non_clamping_audit_codes() -> None:
    """The :class:`MergeOperatorProtocol` docstring explicitly states
    that :class:`IdentityOperator` and :class:`EMAOperator` are
    non-clamping operators that MAY accept ``audit_codes`` but ignore
    it (audit P2-4: contract documentation).
    """
    docstring = MergeOperatorProtocol.__doc__ or ""
    assert "audit_codes" in docstring
    # The new P2-4 contract text must be present.
    assert "non-clamping" in docstring


def test_identity_operator_does_not_emit_envelope_audit_codes() -> None:
    """:class:`IdentityOperator` does not emit
    :data:`MERGE_DEGENERATE_INTERVAL` even on degenerate envelopes
    (audit P2-4: non-clamping operators ignore the envelope
    semantics, so the bounded-merge audit codes MUST NOT appear).
    """
    audit: list[str] = []
    IdentityOperator().merge(
        prev=0.5,
        dynamic=0.5,
        cap=0.0,  # degenerate: cap < floor
        floor=1.0,
        delta_cap_up=0.0,
        delta_cap_down=0.0,
        audit_codes=audit,
    )
    degenerate_lines = [
        code for code in audit if "merge_degenerate_interval" in code
    ]
    assert degenerate_lines == [], (
        f"IdentityOperator emitted MERGE_DEGENERATE_INTERVAL codes: "
        f"{degenerate_lines!r}; non-clamping operators MUST NOT emit "
        f"bounded-merge audit codes (P2-4)."
    )


def test_ema_operator_does_not_emit_envelope_audit_codes() -> None:
    """:class:`EMAOperator` does not emit
    :data:`MERGE_DEGENERATE_INTERVAL` even on degenerate envelopes
    (audit P2-4).
    """
    audit: list[str] = []
    EMAOperator().merge(
        prev=0.5,
        dynamic=0.5,
        cap=0.0,
        floor=1.0,
        delta_cap_up=0.0,
        delta_cap_down=0.0,
        audit_codes=audit,
    )
    degenerate_lines = [
        code for code in audit if "merge_degenerate_interval" in code
    ]
    assert degenerate_lines == [], (
        f"EMAOperator emitted MERGE_DEGENERATE_INTERVAL codes: "
        f"{degenerate_lines!r}; non-clamping operators MUST NOT emit "
        f"bounded-merge audit codes (P2-4)."
    )


# ---------------------------------------------------------------------------
# from_config / to_config round-trip (P1-1) — merge operators
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "operator",
    [
        BoundedMergeOperator(tolerance=1e-9),
        BoundedMergeOperator(tolerance=1e-6),
        BoundedMergeOperator(tolerance=1e-9, exterior_gap_e_rho=0.05),
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


# ---------------------------------------------------------------------------
# 9. P0-A12 — BoundedMergeOperator folds ``exterior_gap_e_rho`` into floor
# ---------------------------------------------------------------------------


def test_bounded_paper_quantity_floor() -> None:
    """P0-A12: when constructed with ``exterior_gap_e_rho``, the
    operator lifts the envelope ``floor`` to ``max(floor, e_rho / 4)``
    (paper Lemma 5 physical-complement floor) and emits
    :data:`MERGE_PAPER_QUANTITY_FLOOR_LIFTED` on the lift path.

    Quantitative target: with ``e_rho = 0.05`` the lifted floor is
    ``>= 0.0125`` (``= 0.05 / 4``) and the merge result respects the
    lifted envelope (the result is never below the lifted floor).
    """
    from adaptive_reflow.algorithm.merge_operator import (
        MERGE_PAPER_QUANTITY_FLOOR_LIFTED,
    )

    op = BoundedMergeOperator(exterior_gap_e_rho=0.05)
    assert op.exterior_gap_e_rho == pytest.approx(0.05)

    # Schedule-supplied floor 0.0 < 0.0125 -> the operator lifts the
    # floor to 0.0125 and emits the audit code. With prev=0.0 and
    # dynamic=0.0, the merge result equals the lifted floor.
    audit: list[str] = []
    result = op.merge(
        prev=0.0,
        dynamic=0.0,
        cap=1.0,
        floor=0.0,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit,
    )
    assert result == pytest.approx(0.0125)
    assert any(MERGE_PAPER_QUANTITY_FLOOR_LIFTED in code for code in audit)
    # Audit line carries the lifted floor + e_rho.
    lifted_lines = [
        c for c in audit if MERGE_PAPER_QUANTITY_FLOOR_LIFTED in c
    ]
    assert any("floor=0.012500" in c for c in lifted_lines)

    # Result respects the lifted envelope: even with a very small
    # ``prev`` (below the lifted floor) the result is floored at
    # ``e_rho / 4`` when ``dynamic`` and the delta caps are zero.
    audit2: list[str] = []
    result2 = op.merge(
        prev=0.0,
        dynamic=0.0,
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.0,
        delta_cap_down=0.0,
        audit_codes=audit2,
    )
    assert result2 >= 0.0125, (
        f"result {result2} fell below the lifted floor 0.0125"
    )


def test_bounded_paper_quantity_floor_no_lift_when_already_higher() -> None:
    """P0-A12: when the schedule-supplied ``floor`` is already at or
    above ``e_rho / 4`` the operator MUST NOT lift and MUST NOT emit
    the audit code.
    """
    from adaptive_reflow.algorithm.merge_operator import (
        MERGE_PAPER_QUANTITY_FLOOR_LIFTED,
    )

    op = BoundedMergeOperator(exterior_gap_e_rho=0.05)
    audit: list[str] = []
    result = op.merge(
        prev=0.5,
        dynamic=0.5,
        cap=1.0,
        floor=0.2,  # already above 0.05 / 4 = 0.0125
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit,
    )
    assert result == pytest.approx(0.5)
    assert not any(MERGE_PAPER_QUANTITY_FLOOR_LIFTED in c for c in audit)


def test_bounded_paper_quantity_floor_legacy_default_unchanged() -> None:
    """P0-A12: when ``exterior_gap_e_rho`` is ``None`` (the default),
    the operator preserves the legacy behaviour byte-for-byte — no
    audit code is emitted, and the result is the same as the
    no-paper-quantity path.
    """
    op = BoundedMergeOperator()  # exterior_gap_e_rho defaults to None
    assert op.exterior_gap_e_rho is None
    audit: list[str] = []
    result = op.merge(
        prev=0.5,
        dynamic=0.5,
        cap=1.0,
        floor=0.0,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit,
    )
    assert result == pytest.approx(0.5)
    # No paper-quantity audit code emitted.
    assert not any(
        "merge_paper_quantity_floor_lifted" in c for c in audit
    )


def test_bounded_merge_operator_rejects_invalid_e_rho() -> None:
    """P0-A12: ``exterior_gap_e_rho`` must be finite and non-negative."""
    with pytest.raises(ValueError, match="real number"):
        BoundedMergeOperator(exterior_gap_e_rho="not a number")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite"):
        BoundedMergeOperator(exterior_gap_e_rho=float("inf"))
    with pytest.raises(ValueError, match="non-negative"):
        BoundedMergeOperator(exterior_gap_e_rho=-0.1)


def test_bounded_paper_quantity_floor_result_respects_envelope() -> None:
    """P0-A12: even with the paper-quantity floor lift, the result
    MUST be a finite ``float`` in ``[0, 1]`` and the cap envelope
    must be respected. The lift only changes the floor; cap and the
    delta-cap-driven interval are still honored.
    """
    op = BoundedMergeOperator(exterior_gap_e_rho=0.05)
    audit: list[str] = []
    # cap = 0.5 so the result is bounded by the cap.
    result = op.merge(
        prev=0.4,
        dynamic=0.4,
        cap=0.5,
        floor=0.0,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit,
    )
    # Floor lifts to 0.0125; cap=0.5 stays. The result sits inside
    # the lifted envelope.
    assert 0.0125 <= result <= 0.5


# ---------------------------------------------------------------------------
# 10. P1-A13 — IdentityOperator emits MERGE_NONFINITE_DYNAMIC_CLIPPED
# (additional coverage for non-finite prev + audit_codes=None path).
# ---------------------------------------------------------------------------


def test_identity_emits_finiteness_code() -> None:
    """P1-A13: ``IdentityOperator`` forwards
    :data:`MERGE_NONFINITE_DYNAMIC_CLIPPED` to ``audit_codes`` on
    every call where ``dynamic`` was clipped into ``[0, 1]``. The
    operator is byte-identical when ``dynamic`` is already in
    ``[0, 1]``.
    """
    from adaptive_reflow.algorithm.merge_operator import (
        MERGE_NONFINITE_DYNAMIC_CLIPPED,
    )

    op = IdentityOperator()
    # Out-of-range ``dynamic`` triggers the audit code.
    audit: list[str] = []
    out_clip = op.merge(
        prev=0.5,
        dynamic=1.7,
        cap=1.0,
        floor=0.0,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit,
    )
    assert out_clip == pytest.approx(1.0)
    assert any(MERGE_NONFINITE_DYNAMIC_CLIPPED in c for c in audit)

    # In-range ``dynamic`` -> no audit code, byte-identical output.
    audit.clear()
    out_in = op.merge(
        prev=0.5,
        dynamic=0.5,
        cap=1.0,
        floor=0.0,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit,
    )
    assert out_in == pytest.approx(0.5)
    assert audit == []

    # ``NaN`` -> ``0.0`` with the audit code emitted.
    audit.clear()
    import math

    out_nan = op.merge(
        prev=0.5,
        dynamic=float("nan"),
        cap=1.0,
        floor=0.0,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit,
    )
    assert math.isfinite(out_nan)
    assert out_nan == pytest.approx(0.0)
    assert any(MERGE_NONFINITE_DYNAMIC_CLIPPED in c for c in audit)


# ---------------------------------------------------------------------------
# 6. F5 — cap/floor fail-closed (P0)
# ---------------------------------------------------------------------------


def test_bounded_merge_rejects_cap_below_floor_post_clip() -> None:
    """P0-3 (F-18): BoundedMergeOperator returns the ``floor`` value
    when ``cap < floor`` after clipping (fail-closed), and emits the
    canonical ``merge_cap_below_floor`` audit code.

    Earlier the operator raised ``MergeAuthorityError`` (F5 fix),
    which contradicted the :data:`MergeOperatorProtocol` docstring
    ("implementations MUST NOT raise on legitimate caller input
    such as ``cap < floor``") and crashed the runner on legitimate
    envelopes. The fail-closed path now returns ``floor`` and the
    audit code captures the degenerate envelope so the runner's
    loop survives.
    """
    op = BoundedMergeOperator()
    audit: list[str] = []
    result = op.merge(
        prev=0.5,
        dynamic=0.3,
        cap=0.2,
        floor=0.8,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit,
    )
    # Fail-closed: returns the floor value.
    assert result == pytest.approx(0.8, abs=1e-12)
    # Audit code captures the degenerate envelope.
    assert any("merge_cap_below_floor" in c for c in audit)


# ---------------------------------------------------------------------------
# 7. F1 — MERGE_PREV_ANCHORED_TO_LAST_EMITTED emission (P1)
# ---------------------------------------------------------------------------


def test_bounded_merge_emits_prev_anchored() -> None:
    """F1: BoundedMergeOperator emits
    ``MERGE_PREV_ANCHORED_TO_LAST_EMITTED`` when ``prev_source ==
    "last_emitted"`` and does NOT emit it under the default
    ``prev_source="default"``.
    """
    from adaptive_reflow.algorithm.merge_operator import (
        MERGE_PREV_ANCHORED_TO_LAST_EMITTED,
    )

    op = BoundedMergeOperator()

    # Default ``prev_source`` -> no anchored-to-last-emitted audit code.
    audit_default: list[str] = []
    op.merge(
        prev=0.5,
        dynamic=0.4,
        cap=1.0,
        floor=0.0,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit_default,
    )
    assert not any(MERGE_PREV_ANCHORED_TO_LAST_EMITTED in c for c in audit_default)

    # ``prev_source="last_emitted"`` -> emits the anchored code.
    audit_anchored: list[str] = []
    op.merge(
        prev=0.5,
        dynamic=0.4,
        cap=1.0,
        floor=0.0,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        audit_codes=audit_anchored,
        prev_source="last_emitted",
    )
    assert any(MERGE_PREV_ANCHORED_TO_LAST_EMITTED in c for c in audit_anchored)


# ---------------------------------------------------------------------------
# 8. F7 — BoundedMergeOperator.merge accepts schedule_sample kwarg (P1)
# ---------------------------------------------------------------------------


def test_bounded_merge_accepts_schedule_sample() -> None:
    """F7: BoundedMergeOperator.merge accepts ``schedule_sample`` as a
    kwarg (no-op; the bounded merge does not modulate its envelope by
    ``n_cap``). The kwarg is part of the protocol surface so callers
    can forward a single call shape to any ``MergeOperatorProtocol``
    implementation.
    """
    op = BoundedMergeOperator()
    sample = type("S", (), {"n_cap": 0.7})()
    # Without schedule_sample:
    out_no_sample = op.merge(
        prev=0.5,
        dynamic=0.4,
        cap=1.0,
        floor=0.0,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
    )
    # With schedule_sample — must produce the same result (no-op).
    out_with_sample = op.merge(
        prev=0.5,
        dynamic=0.4,
        cap=1.0,
        floor=0.0,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
        schedule_sample=sample,
    )
    assert out_with_sample == pytest.approx(out_no_sample)
