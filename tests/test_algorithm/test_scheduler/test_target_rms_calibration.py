"""Wave 125 Phase 4 — paper-quantity-driven β target-RMS calibration tests.

Tests the additive :func:`adjust_n_cap_for_target_rms` and
:func:`paper_quantity_driven_beta` helpers shipped by Wave 125 Phase 4
(see ``todo/algo-improvement-paper-quantity-beta-calibration.md``).
The two helpers together expose the calibration knob that adapts the
paper-quantity-driven schedule's ``n_cap`` to a target RMSD threshold
— the protein-reconstruction RMSD may sit too high or too low for
the scheduler's literal paper-quantity-driven ``n_cap``, and the
calibration knob lets the caller request a specific RMSD target.

The tests pin two invariants:

* **Test 1 — calibration honoured**: ``paper_quantity_driven_beta(
  target_rms_threshold=...)`` delegates to ``adjust_n_cap_for_target_rms``
  and returns the calibrated ``n_cap`` (no silent override). The
  helper must remain a *pure* function of the threshold.
* **Test 2 — default behaviour unchanged**: ``paper_quantity_driven_beta()``
  with no ``target_rms_threshold`` returns the same ``n_cap`` the
  pre-Wave-125 :class:`CodimensionSheetScheduler` would emit for the
  same round / cycle — i.e. the additive kwarg must NOT silently change
  the existing paper-quantity-driven default.

A handful of secondary tests cover edge cases (clamping, monotonicity,
validation) so a future regression in the calibration math gets
caught immediately.
"""

from __future__ import annotations

import math

import pytest

from adaptive_reflow.algorithm.scheduler.adaptive import (
    _REF_N_CAP,
    _REF_RMSD,
    CodimensionSheetScheduler,
    adjust_n_cap_for_target_rms,
    paper_quantity_driven_beta,
)

# ---------------------------------------------------------------------------
# Test 1 — paper_quantity_driven_beta respects target_rms_threshold kwarg
# ---------------------------------------------------------------------------


def test_beta_scheduler_respects_target_rms_threshold() -> None:
    """Beta scheduler must respect ``target_rms_threshold`` kwarg.

    Wave 125 Phase 4 acceptance test: when ``target_rms_threshold`` is
    supplied, ``paper_quantity_driven_beta`` must delegate to
    :func:`adjust_n_cap_for_target_rms` and return the calibrated
    ``n_cap`` (no silent override from the other scheduler-shape
    kwargs). This pins the additive contract that the calibration
    knob does what its name promises — callers can request a target
    RMSD and receive the matching ``n_cap`` without having to reason
    about the scheduler's internal paper-quantity constants.
    """
    # Anchor: at the reference RMSD the calibration must equal the
    # reference ``n_cap`` (the linear scale's fixed point).
    assert adjust_n_cap_for_target_rms(_REF_RMSD) == pytest.approx(
        _REF_N_CAP, rel=1e-12
    )

    # The default behaviour: a tight (1.0 Å) target lowers ``n_cap``
    # below the reference (less fresh noise, more memory dominance).
    calibrated = paper_quantity_driven_beta(target_rms_threshold=1.0)
    expected = adjust_n_cap_for_target_rms(1.0)
    assert calibrated == pytest.approx(expected, rel=1e-12), (
        f"paper_quantity_driven_beta(target_rms_threshold=1.0) must "
        f"equal adjust_n_cap_for_target_rms(1.0); got {calibrated!r} "
        f"vs {expected!r}"
    )
    assert calibrated < _REF_N_CAP, (
        f"A 1.0 Å target must lower n_cap below the {_REF_N_CAP} "
        f"reference; got {calibrated!r}"
    )

    # And: a loose (5.0 Å) target raises ``n_cap`` above the reference
    # (more fresh noise, less memory dominance).
    calibrated_loose = paper_quantity_driven_beta(target_rms_threshold=5.0)
    expected_loose = adjust_n_cap_for_target_rms(5.0)
    assert calibrated_loose == pytest.approx(expected_loose, rel=1e-12)
    assert calibrated_loose > _REF_N_CAP


# ---------------------------------------------------------------------------
# Test 2 — paper_quantity_driven_beta default behaviour unchanged
# ---------------------------------------------------------------------------


def test_beta_scheduler_default_behavior_unchanged() -> None:
    """Beta scheduler must remain backward-compatible (no silent breaking change).

    Wave 125 Phase 4 acceptance test: when ``target_rms_threshold`` is
    ``None`` (the default), :func:`paper_quantity_driven_beta` must
    return the same ``n_cap`` value that the pre-Wave-125
    :class:`CodimensionSheetScheduler` would emit for the same round /
    cycle. The additive kwarg MUST NOT silently change the existing
    paper-quantity-driven default — callers that never pass
    ``target_rms_threshold`` must see byte-identical output.

    We verify this at several rounds to make sure the default path
    remains a faithful delegation across the whole cycle, not just
    at the round-0 marker.
    """
    cycle_length = 20
    eps_implicit = 0.05
    pre_wave_125 = CodimensionSheetScheduler(
        cycle_length=cycle_length,
        n_min=0.0,
        n_max=1.0,
        eps_implicit=eps_implicit,
    )
    for round_in_cycle in range(cycle_length):
        expected = float(
            pre_wave_125.sample(0, round_in_cycle, round_in_cycle).n_cap
        )
        # Default kwargs: cycle_length=20, eps_implicit=0.05,
        # n_min=0.0, n_max=1.0, round_in_cycle=0. We override
        # round_in_cycle explicitly here to sweep the cycle.
        got = paper_quantity_driven_beta(
            cycle_length=cycle_length,
            eps_implicit=eps_implicit,
            round_in_cycle=round_in_cycle,
        )
        assert got == pytest.approx(expected, abs=1e-12), (
            f"Default paper_quantity_driven_beta(round_in_cycle="
            f"{round_in_cycle}) must equal the pre-Wave-125 "
            f"CodimensionSheetScheduler's n_cap; got {got!r} vs "
            f"{expected!r}. The additive kwarg must NOT silently "
            f"change the default behaviour."
        )


# ---------------------------------------------------------------------------
# Test 3 — adjust_n_cap_for_target_rms validation
# ---------------------------------------------------------------------------


def test_adjust_n_cap_for_target_rms_rejects_zero_target() -> None:
    """A zero target RMSD must be rejected (silent full-memory collapse)."""
    with pytest.raises(ValueError, match="target_rms_threshold"):
        adjust_n_cap_for_target_rms(0.0)


def test_adjust_n_cap_for_target_rms_rejects_negative_target() -> None:
    """A negative target RMSD must be rejected."""
    with pytest.raises(ValueError, match="target_rms_threshold"):
        adjust_n_cap_for_target_rms(-1.0)


def test_adjust_n_cap_for_target_rms_rejects_non_finite_target() -> None:
    """A non-finite target RMSD must be rejected."""
    with pytest.raises(ValueError, match="finite"):
        adjust_n_cap_for_target_rms(float("nan"))
    with pytest.raises(ValueError, match="finite"):
        adjust_n_cap_for_target_rms(float("inf"))


def test_adjust_n_cap_for_target_rms_rejects_non_real_target() -> None:
    """A non-real target RMSD (e.g. string) must be rejected with TypeError."""
    with pytest.raises(TypeError):
        adjust_n_cap_for_target_rms("1.0")  # type: ignore[arg-type]
    # Booleans are technically ``int`` but must be rejected to avoid
    # silent ``True -> 1`` / ``False -> 0`` surprises.
    with pytest.raises(TypeError):
        adjust_n_cap_for_target_rms(True)  # type: ignore[arg-type]


def test_adjust_n_cap_for_target_rms_rejects_invalid_ref_rmsd() -> None:
    """``ref_rmsd`` must be finite and > 0."""
    with pytest.raises(ValueError, match="ref_rmsd"):
        adjust_n_cap_for_target_rms(1.0, ref_rmsd=0.0)
    with pytest.raises(ValueError, match="ref_rmsd"):
        adjust_n_cap_for_target_rms(1.0, ref_rmsd=-1.0)
    with pytest.raises(ValueError, match="ref_rmsd"):
        adjust_n_cap_for_target_rms(1.0, ref_rmsd=float("nan"))


def test_adjust_n_cap_for_target_rms_rejects_invalid_ref_n_cap() -> None:
    """``ref_n_cap`` must lie in [0, 1]."""
    with pytest.raises(ValueError, match="ref_n_cap"):
        adjust_n_cap_for_target_rms(1.0, ref_n_cap=-0.1)
    with pytest.raises(ValueError, match="ref_n_cap"):
        adjust_n_cap_for_target_rms(1.0, ref_n_cap=1.5)
    with pytest.raises(ValueError, match="ref_n_cap"):
        adjust_n_cap_for_target_rms(1.0, ref_n_cap=float("nan"))


# ---------------------------------------------------------------------------
# Test 4 — adjust_n_cap_for_target_rms monotone + clipped
# ---------------------------------------------------------------------------


def test_adjust_n_cap_for_target_rms_monotonic_in_target() -> None:
    """The calibration must be monotonically increasing in target_rms.

    A larger target RMSD (looser quality) must produce a larger
    ``n_cap`` (more fresh noise); a smaller target RMSD (tighter
    quality) must produce a smaller ``n_cap``. This is the
    mathematical contract callers rely on when wiring the calibration
    into the restart policy.
    """
    prev = -1.0
    for target in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 5.0, 10.0):
        n_cap = adjust_n_cap_for_target_rms(target)
        assert n_cap >= prev - 1e-12, (
            f"Calibration must be non-decreasing in target_rms; at "
            f"target={target} got n_cap={n_cap} but prev={prev}"
        )
        prev = n_cap


def test_adjust_n_cap_for_target_rms_clips_to_unit_interval() -> None:
    """Output must lie in [0, 1] for any positive target_rms.

    The linear mapping ``ref_n_cap * (target / ref_rmsd)`` can exceed
    ``1`` for very large targets (or fall below ``0`` for very small
    ones if the calibration were not monotone-positive); the helper
    must always clip into the canonical ``[0, 1]`` ``n_cap`` envelope
    so the result is safe to feed directly into the restart policy.
    """
    for target in (1e-9, 1e-6, 0.01, 1.0, 100.0, 1e9):
        n_cap = adjust_n_cap_for_target_rms(target)
        assert 0.0 <= n_cap <= 1.0
        assert math.isfinite(n_cap)
    # And the anchor: at the reference RMSD the output equals the
    # reference ``n_cap`` (the linear scale's fixed point).
    assert adjust_n_cap_for_target_rms(_REF_RMSD) == pytest.approx(
        _REF_N_CAP, rel=1e-12
    )
    # And: a target much larger than ``ref_rmsd`` saturates at 1.
    assert adjust_n_cap_for_target_rms(1e6) == pytest.approx(1.0)
    # And: a target much smaller than ``ref_rmsd`` saturates near 0.
    assert adjust_n_cap_for_target_rms(1e-6) == pytest.approx(
        _REF_N_CAP * (1e-6 / _REF_RMSD), rel=1e-12
    )
    assert adjust_n_cap_for_target_rms(1e-6) >= 0.0


def test_adjust_n_cap_for_target_rms_respects_overrides() -> None:
    """The ``ref_rmsd`` / ``ref_n_cap`` overrides must take effect."""
    # A different reference anchor should rescale the output
    # proportionally.
    custom_n_cap = adjust_n_cap_for_target_rms(
        5.0, ref_rmsd=5.0, ref_n_cap=0.4
    )
    assert custom_n_cap == pytest.approx(0.4, rel=1e-12)
    halved = adjust_n_cap_for_target_rms(
        5.0, ref_rmsd=5.0, ref_n_cap=0.2
    )
    assert halved == pytest.approx(0.2, rel=1e-12)
    assert halved == pytest.approx(custom_n_cap / 2.0, rel=1e-12)


# ---------------------------------------------------------------------------
# Test 5 — paper_quantity_driven_beta threshold wins over scheduler shape
# ---------------------------------------------------------------------------


def test_beta_scheduler_threshold_overrides_scheduler_shape() -> None:
    """The ``target_rms_threshold`` must take precedence over scheduler shape.

    When ``target_rms_threshold`` is supplied, the remaining scheduler
    kwargs (``eps_implicit``, ``cycle_length``, ...) are *ignored* —
    the calibration is pure. This pins the additive Wave 125 contract
    that the threshold "always wins" so callers cannot be surprised
    by a stale scheduler-shape setting silently vetoing the
    calibration.
    """
    threshold = 1.0
    expected = adjust_n_cap_for_target_rms(threshold)
    for kwargs in (
        {},
        {"eps_implicit": 0.5},
        {"cycle_length": 4, "round_in_cycle": 2},
        {"n_min": 0.5, "n_max": 0.6},
    ):
        kwargs_with_threshold = {"target_rms_threshold": threshold, **kwargs}
        got = paper_quantity_driven_beta(**kwargs_with_threshold)
        assert got == pytest.approx(expected, rel=1e-12), (
            f"paper_quantity_driven_beta({kwargs_with_threshold}) "
            f"must ignore the scheduler-shape kwargs when "
            f"target_rms_threshold is set; got {got!r} vs "
            f"{expected!r}"
        )


def test_beta_scheduler_pure_threshold_helper_no_side_effects() -> None:
    """Calling the helper twice with the same threshold must yield the same value.

    The calibration is a pure function of its inputs, so repeated
    invocations must be deterministic. This guards against a future
    change that accidentally introduces hidden state (e.g. an EMA)
    into the calibration path.
    """
    first = paper_quantity_driven_beta(target_rms_threshold=1.5)
    second = paper_quantity_driven_beta(target_rms_threshold=1.5)
    assert first == pytest.approx(second, rel=1e-12)
    # And: a different threshold yields a different ``n_cap``.
    other = paper_quantity_driven_beta(target_rms_threshold=3.0)
    assert other != pytest.approx(first, rel=1e-6)
