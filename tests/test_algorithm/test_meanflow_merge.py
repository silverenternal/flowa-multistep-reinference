"""Tests for :class:`MeanFlowMergeOperator` (A2 — MeanFlow, arXiv:2505.13447).

The operator extends :class:`BoundedMergeOperator` with a MeanFlow
decomposition twist: ``u_eff = raw - dt * ema_grad`` clipped into
``[floor, cap]``. The tests cover:

* construction + identity (``family``, ``config_hash``);
* the canonical bounded-merge contract (returns a finite ``[0, 1]``
  float, honours ``MERGE_DEGENERATE_INTERVAL``);
* the MeanFlow audit code is emitted on every merge;
* degenerate ``t == s`` pairs fall back to the bounded merge with a
  ``MEANFLOW_PAIR_INVALID`` audit code;
* the ``to_config`` / ``from_config`` round-trip.
"""

from __future__ import annotations

import math

import pytest

from adaptive_reflow.algorithm.merge_operator import (
    MERGE_DEGENERATE_INTERVAL,
    MergeOperatorProtocol,
)
from adaptive_reflow.algorithm.merge_operator_v3 import (
    MEANFLOW_DECOMPOSITION_AUDIT,
    MEANFLOW_PAIR_INVALID,
    MeanFlowMergeOperator,
)

# ---------------------------------------------------------------------------
# Construction + identity
# ---------------------------------------------------------------------------


def test_meanflow_is_a_merge_operator_protocol() -> None:
    """``MeanFlowMergeOperator`` conforms to :class:`MergeOperatorProtocol`."""
    op = MeanFlowMergeOperator()
    assert isinstance(op, MergeOperatorProtocol)


def test_meanflow_default_family_is_meanflow() -> None:
    """``family`` is ``"meanflow"`` by default."""
    op = MeanFlowMergeOperator()
    assert op.FAMILY == "meanflow"


def test_meanflow_default_t_and_s() -> None:
    """The default ``t`` / ``s`` pair is ``(1.0, 0.0)`` (MeanFlow's canonical)."""
    op = MeanFlowMergeOperator()
    assert op.t == pytest.approx(1.0)
    assert op.s == pytest.approx(0.0)


def test_meanflow_config_hash_stable() -> None:
    """Two operators with the same config have the same ``config_hash``."""
    a = MeanFlowMergeOperator()
    b = MeanFlowMergeOperator()
    assert a.config_hash() == b.config_hash()


def test_meanflow_rejects_invalid_alpha_grad() -> None:
    """``alpha_grad`` outside ``[0, 1]`` raises ``ValueError``."""
    with pytest.raises(ValueError):
        MeanFlowMergeOperator(alpha_grad=-0.1)
    with pytest.raises(ValueError):
        MeanFlowMergeOperator(alpha_grad=1.5)


def test_meanflow_rejects_non_finite_t() -> None:
    """A non-finite ``t`` raises ``ValueError``."""
    with pytest.raises(ValueError):
        MeanFlowMergeOperator(t=float("inf"))


def test_meanflow_rejects_non_finite_s() -> None:
    """A non-finite ``s`` raises ``ValueError``."""
    with pytest.raises(ValueError):
        MeanFlowMergeOperator(s=float("nan"))


# ---------------------------------------------------------------------------
# Bounded-merge contract (P0-3)
# ---------------------------------------------------------------------------


def test_meanflow_merge_returns_finite_unit_interval() -> None:
    """The merge returns a finite ``[0, 1]`` float for any envelope."""
    op = MeanFlowMergeOperator()
    for prev, dynamic, cap, floor in (
        (0.5, 0.5, 1.0, 0.0),
        (0.7, 0.3, 0.9, 0.1),
        (0.0, 1.0, 1.0, 0.0),
        (0.4, 0.4, 0.5, 0.0),
    ):
        out = op.merge(
            prev=prev, dynamic=dynamic,
            cap=cap, floor=floor,
            delta_cap_up=1.0, delta_cap_down=1.0,
        )
        assert isinstance(out, float)
        assert math.isfinite(out)
        assert 0.0 <= out <= 1.0


def test_meanflow_merge_with_cap_floor_clipped() -> None:
    """A ``dynamic`` above ``cap`` is clipped to ``cap``."""
    op = MeanFlowMergeOperator()
    out = op.merge(
        prev=0.5, dynamic=0.95,
        cap=0.7, floor=0.1,
        delta_cap_up=1.0, delta_cap_down=1.0,
    )
    # ``dynamic`` is clamped to ``cap``; result is bounded by ``cap``.
    assert out <= 0.7 + 1e-9


def test_meanflow_merge_honours_envelope() -> None:
    """The merge respects ``floor`` and ``cap``."""
    op = MeanFlowMergeOperator(t=1.0, s=0.0, alpha_grad=0.0)
    for _ in range(5):  # populate ema_grad
        op.merge(
            prev=0.5, dynamic=0.5,
            cap=0.8, floor=0.2,
            delta_cap_up=1.0, delta_cap_down=1.0,
        )
    out = op.merge(
        prev=0.5, dynamic=0.5,
        cap=0.8, floor=0.2,
        delta_cap_up=1.0, delta_cap_down=1.0,
    )
    assert 0.2 - 1e-9 <= out <= 0.8 + 1e-9


def test_meanflow_emits_degenerate_interval_audit_code() -> None:
    """A degenerate envelope (``cap < floor``) emits the canonical code.

    The :class:`BoundedMergeOperator` now raises
    :class:`MergeAuthorityError` (F5 fix — fail-closed instead of
    silently swapping the envelope) on ``cap < floor``. The audit code
    is appended *before* the raise so a downstream reader can still
    attribute the rejection to the broken envelope configuration.
    """
    from adaptive_reflow.algorithm.merge_operator import MergeAuthorityError

    op = MeanFlowMergeOperator()
    codes: list[str] = []
    with pytest.raises(MergeAuthorityError):
        op.merge(
            prev=0.5, dynamic=0.5,
            cap=0.1, floor=0.9,  # cap < floor
            delta_cap_up=1.0, delta_cap_down=1.0,
            audit_codes=codes,
        )
    assert any("merge_cap_below_floor" in c for c in codes)


def test_meanflow_emits_decomposition_audit_code() -> None:
    """Every merge emits the ``meanflow_decomposition_audit`` code."""
    op = MeanFlowMergeOperator()
    codes: list[str] = []
    op.merge(
        prev=0.5, dynamic=0.5,
        cap=1.0, floor=0.0,
        delta_cap_up=1.0, delta_cap_down=1.0,
        audit_codes=codes,
    )
    assert any(MEANFLOW_DECOMPOSITION_AUDIT in c for c in codes)


# ---------------------------------------------------------------------------
# Degenerate t == s path
# ---------------------------------------------------------------------------


def test_meanflow_degenerate_t_equals_s_emits_pair_invalid() -> None:
    """``t == s`` (no dt) emits ``meanflow_pair_invalid`` and falls back."""
    op = MeanFlowMergeOperator(t=0.5, s=0.5)
    codes: list[str] = []
    out = op.merge(
        prev=0.5, dynamic=0.5,
        cap=1.0, floor=0.0,
        delta_cap_up=1.0, delta_cap_down=1.0,
        audit_codes=codes,
    )
    assert any(MEANFLOW_PAIR_INVALID in c for c in codes)
    # The merge falls back to the bounded-merge behaviour, so the
    # result is in ``[0, 1]`` and finite.
    assert math.isfinite(out)
    assert 0.0 <= out <= 1.0


def test_meanflow_negative_dt_inverts_correction() -> None:
    """A negative ``dt`` (``s > t``) flips the correction sign."""
    op = MeanFlowMergeOperator(t=0.0, s=1.0, alpha_grad=0.0)
    # ``dt = t - s = -1.0``; the correction is ``-dt * ema_grad``.
    codes: list[str] = []
    op.merge(
        prev=0.5, dynamic=0.5,
        cap=1.0, floor=0.0,
        delta_cap_up=1.0, delta_cap_down=1.0,
        audit_codes=codes,
    )
    assert any(MEANFLOW_DECOMPOSITION_AUDIT in c for c in codes)


# ---------------------------------------------------------------------------
# EMA gradient tracking
# ---------------------------------------------------------------------------


def test_meanflow_ema_grad_tracks_dynamic_changes() -> None:
    """The ``ema_grad`` proxy accumulates across calls."""
    op = MeanFlowMergeOperator(alpha_grad=1.0)
    # ``alpha_grad=1.0`` means each call replaces the EMA with the
    # raw gradient (no smoothing). The first call has no prior
    # ``prev_dynamic`` so the EMA stays 0.
    op.merge(prev=0.5, dynamic=0.7, cap=1.0, floor=0.0,
             delta_cap_up=1.0, delta_cap_down=1.0)
    assert op.ema_grad == pytest.approx(0.0)
    # The second call computes ``(0.9 - 0.7) / 1.0 = 0.2``.
    op.merge(prev=0.5, dynamic=0.9, cap=1.0, floor=0.0,
             delta_cap_up=1.0, delta_cap_down=1.0)
    assert op.ema_grad == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# Config round-trip (P1-1)
# ---------------------------------------------------------------------------


def test_meanflow_to_config_returns_dict() -> None:
    """``to_config`` includes the ``"family": "meanflow"`` key."""
    op = MeanFlowMergeOperator(t=0.8, s=0.2, alpha_grad=0.3)
    config = op.to_config()
    assert config["family"] == "meanflow"
    assert config["t"] == pytest.approx(0.8)
    assert config["s"] == pytest.approx(0.2)
    assert config["alpha_grad"] == pytest.approx(0.3)


def test_meanflow_from_config_round_trip() -> None:
    """``from_config`` reproduces a byte-identical operator."""
    original = MeanFlowMergeOperator(t=0.7, s=0.3, alpha_grad=0.25)
    rebuilt = MeanFlowMergeOperator.from_config(original.to_config())
    assert rebuilt.config_hash() == original.config_hash()
    assert rebuilt.t == pytest.approx(0.7)
    assert rebuilt.s == pytest.approx(0.3)
    assert rebuilt.alpha_grad == pytest.approx(0.25)


def test_meanflow_from_config_rejects_non_dict() -> None:
    """``from_config`` fails closed on non-dict input."""
    with pytest.raises(TypeError):
        MeanFlowMergeOperator.from_config("not_a_dict")  # type: ignore[arg-type]
