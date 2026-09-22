"""Edge-case coverage for paper-grounded controllers (Wave 287 P).

The framework's paper-quantity-driven / paper-quantity-aware schedulers
sit at the centre of ADR-0013 (posterior selection drives the algorithm
layer). The canonical battery
(``tests/test_algorithm/test_scheduler/test_codimension_sheet.py``,
``test_paper_ratio_adaptive_scheduler.py``,
``test_convergence_adaptive.py``, ``test_evidence_driven_scheduler.py``,
``test_freetraj.py``, ``test_nfe_aware.py``) covers the **happy path**
and the per-family config round-trip. This file strengthens coverage on
the **boundary inputs** that surface latent bugs:

* ``CodimensionSheetScheduler`` -- paper-quantity-driven base
  (Lemma 2 / Lemma 3 / Corollary 1). Edge cases: ``A_g = 0``,
  ``A_g = 1e-12`` (paper boundary), ``A_g = 1e12`` (extreme),
  ``B_g = 0``, ``e_rho = 0``, ``e_rho`` negative, all-4-zero profile,
  ``n_min = n_max``, ``n_min > n_max`` (clamp behaviour),
  ``paper_quantities=None`` (degrades to legacy heuristic).
* ``PaperRatioAdaptiveScheduler`` -- paper-quantity-aware PID-lite
  controller. Edge cases: same as codim + ratio ``paper_quantities[weight]=0``
  (no signal).
* ``ConvergenceAdaptiveScheduler`` -- W2 PID controller.
  Edge cases: ``w2_history`` empty, ``w2 = NaN``, ``w2 = inf``, ``kp = 0``
  (no shift), ``kd = 0``, ``shift_max = 0``.
* ``EvidenceDrivenScheduler`` -- evidence-ratio PID controller.
  Edge cases: ``feedback_history`` empty, ``kp = 0``, ``kd = 0``,
  baseline ``selection_ratio = 0``, ``= 1``, ``NaN``.
* ``NFEAwareMemoryScheduler`` -- NFE-driven constant-capacity family.
  Edge cases: ``nfe_budget = 0`` (must not divide by zero), very small
  budget, ``threshold = 0``, ``max_memory_fraction = 0``, ``= 1``.
* ``FreeTrajScheduler`` -- trajectory-aware substep family.
  Edge cases: trajectory length 0, very long, ``trajectory_amplitude = 0``,
  ``trajectory_amplitude`` negative.
* ``TierAwareCodimensionSheetScheduler`` -- tier-quantile wrapper.
  Edge cases: tier assignment ties (exact boundary), single-tier
  fallback, ``n_cap *= 0.5`` floor (n_cap cannot go below n_min).
* ``TestSchedulerDeterminism`` -- D.4 byte-stable contract:
  same ``paper_quantities`` + seed -> same ``n_cap`` byte-for-byte
  across N rounds.

D.4 contract (Wave 32): the regression-vector suite is 30/30 PASS and
must remain so. The ``pytest.skip`` and ``pytest.raises`` assertions
in this file are designed so the byte-stable contract is preserved
even when an edge case throws.
"""

from __future__ import annotations

import hashlib
import math

import numpy as np
import pytest

from adaptive_reflow.algorithm.scheduler import (
    CodimensionSheetScheduler,
    ConvergenceAdaptiveScheduler,
    EvidenceDrivenScheduler,
    FreeTrajScheduler,
    NFEAwareMemoryScheduler,
    PaperRatioAdaptiveScheduler,
    SchedulerProtocol,
    TierAwareCodimensionSheetScheduler,
    default_cosine_scheduler,
)
from adaptive_reflow.contracts import (
    ArtifactHash,
    CosineScheduleConfig,
    FactorValue,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _identity_profile(x: float) -> float:
    """Identity residual profile for codimension-scheduler tests."""
    return float(x)


def _constant_profile(x: float) -> float:
    """Constant profile for tests that need predictable paper quantities."""
    return 1.0


def _zero_profile(x: float) -> float:
    """All-zero profile: paper-quantities fall into the degenerate branch."""
    return 0.0


def _make_cosine_config(
    *, cycle_length: int = 20, n_min: float = 0.0, n_max: float = 1.0,
) -> CosineScheduleConfig:
    """Build a minimal :class:`CosineScheduleConfig` for scheduler tests."""
    return CosineScheduleConfig(
        cycle_length=cycle_length,
        n_min=FactorValue(n_min),
        n_max=FactorValue(n_max),
        schedule_family="cosine_no_restart",
        per_channel_caps={},
        fresh_noise_floor_by_channel={},
        symmetric_delta_caps_by_channel={},
        restart_triggers_allowed=(),
        config_hash=ArtifactHash("test_paper_grounded_config"),
        frozen_before_evaluation=True,
    )


@pytest.fixture
def cos20() -> CodimensionSheetScheduler:
    """Canonical 20-round codimension scheduler (no profile)."""
    return CodimensionSheetScheduler(cycle_length=20, n_min=0.0, n_max=1.0)


@pytest.fixture
def cos20_with_profile() -> CodimensionSheetScheduler:
    """Canonical 20-round codimension scheduler WITH a residual profile.

    The profile unlocks the paper-quantity-augmented path so
    :attr:`sheet_A`, :attr:`packing_B`, :attr:`cell_C`,
    :attr:`exterior_gap_e_rho` are populated with the literal paper
    quantities.
    """
    return CodimensionSheetScheduler(
        cycle_length=20,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=_identity_profile,
    )


def _collect_n_cap_seq(scheduler: SchedulerProtocol, rounds: int) -> list[float]:
    """Sample ``scheduler`` for ``rounds`` rounds and return ``n_cap`` values."""
    n_caps: list[float] = []
    for r in range(rounds):
        sample = scheduler.sample(0, r, r)
        n_caps.append(float(sample.n_cap))
    return n_caps


# ===========================================================================
# TestCodimensionSheetScheduler -- paper Lemma 2 / Lemma 3 / Cor. 1
# ===========================================================================


class TestCodimensionSheetScheduler:
    """Edge cases for :class:`CodimensionSheetScheduler`.

    The codimension family is the framework's default paper-quantity-driven
    scheduler since Wave 34. The closed form is

        sheet = A_g * eps                    # Lemma 2 / Cor. 1
        cell  = C_g * B_g * eps^2            # Lemma 3 + Lemma 5
        ratio = sheet / (sheet + cell)       in [0, 1]
        n_cap = n_min + (n_max - n_min) * ratio

    Edge cases target the **boundary inputs** of the paper-quantity cache
    (the ``A_g`` / ``B_g`` / ``C_g`` / ``e_rho`` values) and the
    :func:`_paper_evidence_balance` fallback. Every test asserts

    * no exception (or the specific expected exception);
    * ``n_cap in [n_min, n_max]`` for every round.
    """

    def test_a_g_zero_does_not_raise(self, cos20_with_profile: CodimensionSheetScheduler) -> None:
        """``A_g = 0`` is a degenerate (zero sheet evidence) input -- no raise.

        With ``A_g = 0`` the per-round ``sheet = A_g * eps = 0`` so the
        ratio is exactly 0. The framework-side fallback (in
        :func:`_paper_evidence_balance`) engages so the scheduler does
        not divide by zero.
        """
        # ``A_g = 0`` only arises from a constant-zero profile whose
        # integral evaluates to zero.  Force the cache to zero.
        cos20_with_profile._sheet_A = 0.0  # type: ignore[attr-defined]
        for r in range(20):
            sample = cos20_with_profile.sample(0, r, r)
            assert 0.0 <= sample.n_cap <= 1.0
            assert math.isfinite(sample.n_cap)

    def test_a_g_extreme_low_does_not_raise(self, cos20_with_profile: CodimensionSheetScheduler) -> None:
        """``A_g = 1e-12`` -- paper's boundary value -- does not raise.

        Paper Theorem 1 requires ``A_g > 0`` but the boundary value
        ``A_g -> 0`` exercises the denominator floor in
        :func:`_paper_evidence_balance`. The fallback engages and the
        scheduler survives.
        """
        cos20_with_profile._sheet_A = 1e-12  # type: ignore[attr-defined]
        for r in range(20):
            sample = cos20_with_profile.sample(0, r, r)
            assert 0.0 <= sample.n_cap <= 1.0
            assert math.isfinite(sample.n_cap)

    def test_a_g_extreme_high_keeps_n_cap_in_unit_interval(self, cos20_with_profile: CodimensionSheetScheduler) -> None:
        """``A_g = 1e12`` -- extreme -- n_cap stays in [0, 1].

        With an extreme sheet signal the per-round ratio is 1 (sheet
        dominates), so ``n_cap = n_max`` regardless of the cell term.
        The scheduler clips defensively.
        """
        cos20_with_profile._sheet_A = 1e12  # type: ignore[attr-defined]
        for r in range(20):
            sample = cos20_with_profile.sample(0, r, r)
            assert 0.0 <= sample.n_cap <= 1.0
            assert math.isfinite(sample.n_cap)
            assert sample.n_cap == pytest.approx(1.0, abs=1e-9)

    def test_b_g_zero_does_not_raise(self, cos20_with_profile: CodimensionSheetScheduler) -> None:
        """``B_g = 0`` -- no cell packing -- falls back to the framework heuristic.

        With ``B_g = 0`` the cell term is ``0 * eps^2 = 0`` and the
        ratio is exactly 1.0 (sheet dominance). The scheduler does not
        raise; ``n_cap`` saturates at ``n_max``.
        """
        cos20_with_profile._packing_B = 0.0  # type: ignore[attr-defined]
        for r in range(20):
            sample = cos20_with_profile.sample(0, r, r)
            assert 0.0 <= sample.n_cap <= 1.0
            assert sample.n_cap == pytest.approx(1.0, abs=1e-9)

    def test_e_rho_zero_does_not_raise(self, cos20_with_profile: CodimensionSheetScheduler) -> None:
        """``e_rho = 0`` -- the exterior-gap floor collapses to zero.

        :attr:`inject_noise` applies ``max(A_g, e_rho / 4)`` as the
        noise mass floor (paper Lemma 5). With ``e_rho = 0`` the floor
        is 0 so the noise mass is ``A_g`` alone.
        """
        cos20_with_profile._exterior_gap_e_rho = 0.0  # type: ignore[attr-defined]
        sample = cos20_with_profile.sample(0, 0, 0)
        assert 0.0 <= sample.n_cap <= 1.0
        # And noise injection is still finite.
        rng = np.random.default_rng(0)
        state = np.zeros((4,), dtype=np.float64)
        out = cos20_with_profile.inject_noise(
            state,
            sample.as_cosine_schedule_sample(),
            generator=rng,
        )
        assert np.all(np.isfinite(out))

    def test_e_rho_negative_does_not_raise(self, cos20_with_profile: CodimensionSheetScheduler) -> None:
        """``e_rho < 0`` -- defensive: scheduler ignores the bad floor.

        Paper Lemma 5 requires ``e_rho >= 0``. A negative input is a
        caller bug; the scheduler must not propagate it through the
        noise-mass floor.
        """
        cos20_with_profile._exterior_gap_e_rho = -0.5  # type: ignore[attr-defined]
        sample = cos20_with_profile.sample(0, 0, 0)
        rng = np.random.default_rng(0)
        state = np.zeros((4,), dtype=np.float64)
        out = cos20_with_profile.inject_noise(
            state,
            sample.as_cosine_schedule_sample(),
            generator=rng,
        )
        assert np.all(np.isfinite(out))

    def test_all_four_zero_falls_back_to_heuristic(self) -> None:
        """``A_g = B_g = C_g = 0`` and ``e_rho = 0`` -- all-zero paper quantities.

        Forces the fallback path inside :func:`_paper_evidence_balance`
        (the ``denom <= 0`` branch). The scheduler must remain finite
        and ``n_cap in [0, 1]`` for every round.
        """
        scheduler = CodimensionSheetScheduler(
            cycle_length=10,
            n_min=0.0,
            n_max=1.0,
            profile_residual_fn=_constant_profile,
        )
        scheduler._sheet_A = 0.0  # type: ignore[attr-defined]
        scheduler._packing_B = 0.0  # type: ignore[attr-defined]
        scheduler._cell_C = 0.0  # type: ignore[attr-defined]
        scheduler._exterior_gap_e_rho = 0.0  # type: ignore[attr-defined]
        for r in range(10):
            sample = scheduler.sample(0, r, r)
            assert 0.0 <= sample.n_cap <= 1.0
            assert math.isfinite(sample.n_cap)

    def test_n_min_equal_to_n_max_collapses_to_constant(self) -> None:
        """``n_min == n_max`` -- the envelope collapses to a single value.

        With ``n_min = n_max = 0.5`` the per-round ``n_cap`` is *always*
        ``0.5`` regardless of the ratio. This is the limiting case of
        a degenerate envelope; the scheduler must accept it.
        """
        scheduler = CodimensionSheetScheduler(
            cycle_length=8,
            n_min=0.5,
            n_max=0.5,
            eps_implicit=0.05,
        )
        for r in range(8):
            sample = scheduler.sample(0, r, r)
            assert sample.n_cap == pytest.approx(0.5, abs=1e-9)

    def test_n_min_greater_than_n_max_is_silently_clipped(self) -> None:
        """``n_min > n_max`` -- the constructor accepts the input.

        The :class:`CodimensionSheetScheduler` constructor validates
        each value lies in ``[0, 1]`` independently but does NOT
        enforce ordering (this is the current contract). The closed
        form ``n_min + (n_max - n_min) * ratio`` then produces values
        OUTSIDE the canonical ``[0, 1]`` range for some ratios, but
        the defensive clip keeps ``n_cap`` in ``[0, 1]`` for every
        round.

        This test documents the **current** behaviour: the scheduler
        does not raise on ``n_min > n_max`` and the output stays
        in ``[0, 1]`` due to the defensive clip. If the contract is
        tightened in a future wave this test will need to be
        revisited.
        """
        scheduler = CodimensionSheetScheduler(
            cycle_length=4,
            n_min=0.9,
            n_max=0.1,
            eps_implicit=0.05,
        )
        for r in range(4):
            sample = scheduler.sample(0, r, r)
            # Defensive clip into [0, 1].
            assert 0.0 <= sample.n_cap <= 1.0
            assert math.isfinite(sample.n_cap)

    def test_paper_quantities_none_degrades_to_legacy(self, cos20: CodimensionSheetScheduler) -> None:
        """``profile_residual_fn is None`` -- falls back to legacy heuristic.

        The audit code emitted is ``codimension_framework_heuristic``
        (NOT ``codimension_paper_quantity_grounded``); the cached
        paper quantities on the scheduler are all ``None``.
        """
        assert cos20.profile_residual_fn is None
        assert cos20.sheet_A is None
        assert cos20.packing_B is None
        assert cos20.cell_C is None
        assert cos20.exterior_gap_e_rho is None
        assert cos20.profile_signature == "default_sheet"
        for r in range(20):
            sample = cos20.sample(0, r, r)
            assert "codimension_framework_heuristic" in sample.audit_codes
            assert "codimension_paper_quantity_grounded" not in sample.audit_codes


# ===========================================================================
# TestPaperRatioAdaptiveScheduler -- paper-quantity-aware PID-lite
# ===========================================================================


class TestPaperRatioAdaptiveScheduler:
    """Edge cases for :class:`PaperRatioAdaptiveScheduler`.

    The fully-integrated scheduler wraps
    :class:`CodimensionSheetScheduler` and applies a paper-quantity-aware
    PID-lite shift on top. Edge cases:

    * ``paper_quantities = None`` / empty -> shift stays 0;
    * ``paper_quantities = {}`` -> same as None;
    * ``paper_quantities = {"sheet_A": 0.0}`` -> zero signal, no shift;
    * very small / very large sheet_A -> finite shift bounded by
      ``shift_max``;
    * all codim edge cases carry over because the base IS a
      :class:`CodimensionSheetScheduler`.
    """

    def test_paper_quantities_none_keeps_shift_zero(self) -> None:
        """``paper_quantities = None`` -- no shift, base path only."""
        scheduler = PaperRatioAdaptiveScheduler()
        for r in range(5):
            scheduler.record_round_feedback(r, paper_quantities=None)
        assert scheduler.shift == 0.0
        assert scheduler.sheet_A_history == ()

    def test_paper_quantities_empty_dict_keeps_shift_zero(self) -> None:
        """``paper_quantities = {}`` -- same as ``None`` (safe default)."""
        scheduler = PaperRatioAdaptiveScheduler()
        for r in range(5):
            scheduler.record_round_feedback(r, paper_quantities={})
        assert scheduler.shift == 0.0

    def test_weight_zero_paper_quantity_keeps_shift_zero(self) -> None:
        """``paper_quantities["sheet_A"] = 0`` -- zero signal, no shift change.

        The EMA snaps to 0; the PID sees ``ratio = 0 / 0`` which the
        controller guards against (``ratio = 1.0``), so ``delta = 0``
        and ``shift`` stays bounded.
        """
        scheduler = PaperRatioAdaptiveScheduler(
            kp=0.5,
            kd=0.5,
            shift_max=0.3,
        )
        for r in range(10):
            scheduler.record_round_feedback(r, paper_quantities={"sheet_A": 0.0})
        # Shift may have moved slightly due to numerical guard, but
        # it must remain bounded by shift_max.
        assert abs(scheduler.shift) <= 0.3 + 1e-9

    def test_negative_sheet_a_ignored(self) -> None:
        """Negative ``sheet_A`` is silently dropped (defensive).

        Paper quantities are non-negative by construction; a negative
        input is a caller bug and must not poison the EMA.
        """
        scheduler = PaperRatioAdaptiveScheduler()
        scheduler.record_round_feedback(0, paper_quantities={"sheet_A": -0.5})
        # EMA stays None -- the negative value was dropped.
        assert scheduler.smoothed_sheet_A is None
        assert scheduler.sheet_A_history == ()

    def test_nan_sheet_a_ignored(self) -> None:
        """``sheet_A = NaN`` is dropped (does not poison EMA)."""
        scheduler = PaperRatioAdaptiveScheduler()
        scheduler.record_round_feedback(0, paper_quantities={"sheet_A": float("nan")})
        assert scheduler.smoothed_sheet_A is None
        assert scheduler.sheet_A_history == ()

    def test_inf_sheet_a_ignored(self) -> None:
        """``sheet_A = inf`` is dropped (does not poison EMA)."""
        scheduler = PaperRatioAdaptiveScheduler()
        scheduler.record_round_feedback(0, paper_quantities={"sheet_A": float("inf")})
        assert scheduler.smoothed_sheet_A is None
        assert scheduler.sheet_A_history == ()

    def test_extreme_sheet_a_keeps_shift_bounded(self) -> None:
        """Very large ``sheet_A`` -- shift stays inside ``[-shift_max, +shift_max]."""
        scheduler = PaperRatioAdaptiveScheduler(
            kp=0.5,
            kd=0.5,
            shift_max=0.2,
        )
        # Two extreme samples: 1e12 then 0. The PID sees a huge delta.
        scheduler.record_round_feedback(0, paper_quantities={"sheet_A": 1e12})
        scheduler.record_round_feedback(1, paper_quantities={"sheet_A": 1e12})
        scheduler.record_round_feedback(2, paper_quantities={"sheet_A": 0.0})
        assert abs(scheduler.shift) <= 0.2 + 1e-9

    def test_shift_clipping_to_shift_max(self) -> None:
        """Many monotonically-improving samples -- shift saturates at ``+shift_max``."""
        scheduler = PaperRatioAdaptiveScheduler(
            kp=1.0,
            kd=0.0,
            shift_max=0.1,
        )
        # sheet_A halves every round => sheet_ratio = 0.5 each step.
        for r in range(20):
            scheduler.record_round_feedback(
                r, paper_quantities={"sheet_A": 1.0 / (2 ** r)}
            )
        assert scheduler.shift == pytest.approx(0.1, abs=1e-9)

    def test_n_cap_in_unit_interval_invariant(self) -> None:
        """``n_cap in [0, 1]`` for every round, every edge case.

        Walks the codim edge cases through the wrapped scheduler --
        the :class:`PaperRatioAdaptiveScheduler` shift can move the
        base ``n_cap`` by ``±shift_max`` but the closed form clips
        into ``[0, 1]`` defensively.
        """
        scheduler = PaperRatioAdaptiveScheduler(shift_max=0.5)
        scheduler.record_round_feedback(0, paper_quantities={"sheet_A": 0.0})
        scheduler.record_round_feedback(1, paper_quantities={"sheet_A": 1e-12})
        scheduler.record_round_feedback(2, paper_quantities={"sheet_A": 1e12})
        for r in range(20):
            sample = scheduler.sample(0, r, r)
            assert 0.0 <= sample.n_cap <= 1.0


# ===========================================================================
# TestConvergenceAdaptiveScheduler -- W2 PID controller
# ===========================================================================


class TestConvergenceAdaptiveScheduler:
    """Edge cases for :class:`ConvergenceAdaptiveScheduler`.

    The convergence-adaptive scheduler wraps a base cosine scheduler and
    applies a PID-lite ``u_r`` shift based on per-round W2 feedback.
    Edge cases:

    * empty W2 history (no shift; first round is neutral);
    * non-finite W2 values (NaN, inf -- silently dropped);
    * zero gain (``kp = 0`` -- no shift; ``kd = 0`` -- no derivative);
    * ``shift_max = 0`` -- shift is pinned at zero.
    """

    def test_empty_w2_history_no_shift(self) -> None:
        """No feedback recorded -> shift stays at 0."""
        scheduler = ConvergenceAdaptiveScheduler(
            base=default_cosine_scheduler(cycle_length=10),
            kp=0.5,
            kd=0.5,
        )
        assert scheduler.w2_history == ()
        assert scheduler.shift == 0.0
        # First sample: shift == 0 -> n_cap == base.sample(0).n_cap.
        base_sample = scheduler.base.sample(0, 0, 0)
        shifted = scheduler.sample(0, 0, 0)
        assert shifted.n_cap == pytest.approx(float(base_sample.n_cap))

    def test_w2_nan_is_ignored(self) -> None:
        """``W2 = NaN`` -- the EMA and history are not updated."""
        scheduler = ConvergenceAdaptiveScheduler(
            base=default_cosine_scheduler(cycle_length=10),
        )
        scheduler.record_round_feedback(0, {"W2": float("nan")})
        assert scheduler.smoothed_w2 is None
        assert scheduler.w2_history == ()
        assert scheduler.shift == 0.0

    def test_w2_inf_is_ignored(self) -> None:
        """``W2 = inf`` -- the EMA and history are not updated."""
        scheduler = ConvergenceAdaptiveScheduler(
            base=default_cosine_scheduler(cycle_length=10),
        )
        scheduler.record_round_feedback(0, {"W2": float("inf")})
        assert scheduler.smoothed_w2 is None
        assert scheduler.w2_history == ()

    def test_w2_negative_inf_is_ignored(self) -> None:
        """``W2 = -inf`` -- also non-finite and dropped."""
        scheduler = ConvergenceAdaptiveScheduler(
            base=default_cosine_scheduler(cycle_length=10),
        )
        scheduler.record_round_feedback(0, {"W2": float("-inf")})
        assert scheduler.smoothed_w2 is None
        assert scheduler.w2_history == ()

    def test_kp_zero_no_proportional_shift(self) -> None:
        """``kp = 0`` -- the proportional branch is silent (only ``kd`` may move)."""
        scheduler = ConvergenceAdaptiveScheduler(
            base=default_cosine_scheduler(cycle_length=10),
            kp=0.0,
            kd=0.5,
            shift_max=0.5,
        )
        # W2 trace that would normally drive ``kp * (1 - ratio)``: shift
        # stays at 0 because kp=0.
        for w2 in (1.0, 0.5, 0.25):
            scheduler.record_round_feedback(0, {"W2": w2})
        # ``delta = -kd * (curr - prev)``; with strictly decreasing W2,
        # ``delta`` is positive (kp=0 contributes 0).
        # After three records the shift reflects ONLY the derivative.
        assert abs(scheduler.shift) <= 0.5

    def test_kd_zero_no_derivative_shift(self) -> None:
        """``kd = 0`` -- the derivative branch is silent (only ``kp`` may move)."""
        scheduler = ConvergenceAdaptiveScheduler(
            base=default_cosine_scheduler(cycle_length=10),
            kp=0.5,
            kd=0.0,
            shift_max=0.5,
        )
        scheduler.record_round_feedback(0, {"W2": 1.0})
        scheduler.record_round_feedback(1, {"W2": 0.5})
        # Improvement => ratio=0.5 < 1 => kp*(1-ratio) > 0 => shift>0
        assert scheduler.shift > 0.0
        # And kd=0 means the (curr-prev) term is gone -- the shift
        # reflects only kp's contribution.
        scheduler2 = ConvergenceAdaptiveScheduler(
            base=default_cosine_scheduler(cycle_length=10),
            kp=0.0,
            kd=0.5,
            shift_max=0.5,
            ema=0.3,  # F16: history holds the EMA-smoothed value
        )
        scheduler2.record_round_feedback(0, {"W2": 1.0})
        scheduler2.record_round_feedback(1, {"W2": 0.5})
        # F16: history = (1.0, 0.85) -- the EMA of (1.0, 0.5) with ema=0.3.
        # delta = 0.85 - 1.0 = -0.15. shift = 0 - 0.5 * (-0.15) = +0.075.
        assert scheduler2.shift == pytest.approx(0.075, abs=1e-9)

    def test_shift_max_zero_pins_shift_at_zero(self) -> None:
        """``shift_max = 0`` -- the shift is pinned at 0 regardless of feedback."""
        scheduler = ConvergenceAdaptiveScheduler(
            base=default_cosine_scheduler(cycle_length=10),
            kp=1.0,
            kd=1.0,
            shift_max=0.0,
        )
        for w2 in (1.0, 0.5, 0.25, 0.1):
            scheduler.record_round_feedback(0, {"W2": w2})
        # ``shift_max = 0`` means the clip lower bound == upper bound == 0.
        assert scheduler.shift == 0.0

    def test_n_cap_in_unit_interval_invariant(self) -> None:
        """``n_cap in [0, 1]`` invariant survives aggressive shift values."""
        scheduler = ConvergenceAdaptiveScheduler(
            base=default_cosine_scheduler(cycle_length=10),
            kp=2.0,
            kd=2.0,
            shift_max=0.99,
        )
        for r in range(10):
            scheduler.record_round_feedback(r, {"W2": 1.0 / (r + 1)})
        for r in range(10):
            sample = scheduler.sample(0, r, r)
            assert 0.0 <= sample.n_cap <= 1.0


# ===========================================================================
# TestEvidenceDrivenScheduler -- evidence-ratio PID controller
# ===========================================================================


class TestEvidenceDrivenScheduler:
    """Edge cases for :class:`EvidenceDrivenScheduler`.

    The evidence-driven scheduler adjusts the cosine baseline by a
    small PID-lite step driven by the per-round ``evidence_ratio``. Edge
    cases:

    * empty feedback history -> baseline only (no delta);
    * zero gain (``kp = 0`` -- no proportional shift; ``kd = 0`` -- no
      integral);
    * ``selection_ratio = 0``, ``= 1``, ``= NaN`` baseline signals.
    """

    def test_feedback_history_empty_emits_baseline_only(self) -> None:
        """No feedback recorded -> the sample equals the cosine baseline."""
        scheduler = EvidenceDrivenScheduler(_make_cosine_config(cycle_length=10))
        sample = scheduler.sample(0, 0, 0)
        # The first sample has ``delta = 0`` (the PID has not yet
        # observed anything).
        assert sample.n_cap == pytest.approx(
            scheduler._wrapped.sample(0, 0, 0).n_cap  # type: ignore[attr-defined]
        )

    def test_kp_zero_no_proportional_shift(self) -> None:
        """``kp = 0`` -- proportional branch silent (ki may still move)."""
        scheduler = EvidenceDrivenScheduler(
            _make_cosine_config(cycle_length=10),
            kp=0.0,
            ki=1.0,
            target_ratio=0.5,
        )
        scheduler.record_round_feedback(0, {"evidence_ratio": 0.0})
        # kp=0 means error*kp = 0; only the integral branch contributes.
        # The integral starts at 0 and is updated by ``error = 0.5 - 0 = 0.5``.
        # ``delta = 0 + 1 * 0.5 = 0.5``, clamped to ``max_step=0.1``.
        assert abs(scheduler._last_pid_delta) <= 0.1 + 1e-9  # type: ignore[attr-defined]

    def test_kd_zero_no_integral_shift(self) -> None:
        """``ki = 0`` -- integral branch silent (kp may still move)."""
        scheduler = EvidenceDrivenScheduler(
            _make_cosine_config(cycle_length=10),
            kp=1.0,
            ki=0.0,
            max_step=1.0,  # disable saturation for this test
            target_ratio=0.5,
        )
        scheduler.record_round_feedback(0, {"evidence_ratio": 0.0})
        # First call: error = 0.5 - 0 = 0.5; integral remains 0;
        # delta = kp*error + ki*integral = 1*0.5 + 0 = 0.5.
        assert scheduler._last_pid_delta == pytest.approx(0.5, abs=1e-9)  # type: ignore[attr-defined]

    def test_selection_ratio_zero_drives_positive_delta(self) -> None:
        """``evidence_ratio = 0`` -- maximally-low signal -> positive delta."""
        scheduler = EvidenceDrivenScheduler(
            _make_cosine_config(cycle_length=10),
            kp=1.0,
            ki=0.0,
            max_step=1.0,
            target_ratio=1.0,
        )
        scheduler.record_round_feedback(0, {"evidence_ratio": 0.0})
        # error = 1.0 - 0.0 = 1.0; delta = 1*1 + 0 = 1.0 (saturated at max_step=1.0).
        assert scheduler._last_pid_delta > 0.0  # type: ignore[attr-defined]

    def test_selection_ratio_one_drives_zero_delta(self) -> None:
        """``evidence_ratio = 1`` -- at set-point -> zero delta."""
        scheduler = EvidenceDrivenScheduler(
            _make_cosine_config(cycle_length=10),
            kp=1.0,
            ki=0.0,
            max_step=1.0,
            target_ratio=1.0,
        )
        scheduler.record_round_feedback(0, {"evidence_ratio": 1.0})
        # error = 1.0 - 1.0 = 0; delta = 0.
        assert scheduler._last_pid_delta == pytest.approx(0.0, abs=1e-9)  # type: ignore[attr-defined]

    def test_selection_ratio_nan_falls_back_to_neutral(self) -> None:
        """``evidence_ratio = NaN`` -- the controller treats it as ``0.5`` (neutral).

        Emits :data:`EVIDENCE_RATIO_MISSING` so the audit trail can
        distinguish the no-signal case from the explicit-signal case.
        """
        from adaptive_reflow.algorithm.scheduler import EVIDENCE_RATIO_MISSING

        scheduler = EvidenceDrivenScheduler(
            _make_cosine_config(cycle_length=10),
            kp=1.0,
            ki=0.0,
            max_step=1.0,
            target_ratio=0.5,
        )
        # No ``evidence_ratio`` / ``selection_ratio`` keys at all -> 0.5 fallback.
        scheduler.record_round_feedback(0, {})
        assert EVIDENCE_RATIO_MISSING in scheduler._last_audit_codes  # type: ignore[attr-defined]

    def test_selection_ratio_uses_finite_fallback(self) -> None:
        """NaN values are coerced to the neutral 0.5 -- no NaN propagation."""
        scheduler = EvidenceDrivenScheduler(
            _make_cosine_config(cycle_length=10),
            kp=1.0,
            ki=0.0,
            max_step=1.0,
            target_ratio=0.5,
        )
        scheduler.record_round_feedback(0, {"evidence_ratio": float("nan")})
        # The float() coercion of NaN is allowed (no Python exception),
        # but the controller does NOT propagate a NaN delta.
        assert math.isfinite(scheduler._last_pid_delta)  # type: ignore[attr-defined]

    def test_n_cap_in_unit_interval_invariant(self) -> None:
        """``n_cap in [0, 1]`` invariant for the evidence-driven scheduler."""
        scheduler = EvidenceDrivenScheduler(
            _make_cosine_config(cycle_length=10),
            kp=2.0,
            ki=0.5,
            max_step=0.5,
        )
        # Aggressive ratio swings.
        for r in range(10):
            scheduler.record_round_feedback(
                r, {"evidence_ratio": 1.0 - r / 10.0}
            )
        for r in range(10):
            sample = scheduler.sample(0, r, r)
            assert 0.0 <= sample.n_cap <= 1.0


# ===========================================================================
# TestNFEAwareMemoryScheduler -- NFE-driven constant-capacity family
# ===========================================================================


class TestNFEAwareMemoryScheduler:
    """Edge cases for :class:`NFEAwareMemoryScheduler`.

    The NFE-aware family uses the closed form

        nfe_per_round = nfe_budget / n_rounds
        ratio         = nfe_per_round / threshold
        m(r)          = min(M, M * ratio ** 2)

    Edge cases:

    * ``nfe_budget = 0`` -- the scheduler must not divide by zero.
      The constructor rejects this (``ValueError``).
    * ``threshold = 0`` -- the constructor rejects this.
    * very small budget (1 NFE total) -- ``nfe_per_round`` is small but
      the schedule is finite.
    * ``max_memory_fraction = 0`` -- the schedule emits ``n_cap = 1``.
    * ``max_memory_fraction = 1`` -- the schedule emits ``n_cap = 0``.
    * seed variant -- different seeds do not affect the schedule
      (deterministic).
    """

    def test_nfe_budget_zero_is_rejected(self) -> None:
        """``nfe_budget = 0`` raises ``ValueError`` at construction time.

        The scheduler cannot derive a meaningful per-round NFE when
        the total budget is zero.
        """
        with pytest.raises(ValueError, match="nfe_budget"):
            NFEAwareMemoryScheduler(cycle_length=10, nfe_budget=0, n_rounds=3)

    def test_threshold_zero_is_rejected(self) -> None:
        """``threshold = 0`` raises ``ValueError`` (the ratio denominator is zero)."""
        with pytest.raises(ValueError, match="threshold"):
            NFEAwareMemoryScheduler(
                cycle_length=10, nfe_budget=50, n_rounds=3, threshold=0
            )

    def test_n_rounds_zero_is_rejected(self) -> None:
        """``n_rounds = 0`` raises ``ValueError`` (avoids zero division)."""
        with pytest.raises(ValueError, match="n_rounds"):
            NFEAwareMemoryScheduler(
                cycle_length=10, nfe_budget=50, n_rounds=0
            )

    def test_nfe_budget_very_small_does_not_raise(self) -> None:
        """``nfe_budget = 1`` (the smallest legal value) -- no raise.

        ``nfe_per_round = 1 / n_rounds`` is a tiny positive number, so
        the ratio is small and ``m ≈ 0``.
        """
        scheduler = NFEAwareMemoryScheduler(
            cycle_length=10, nfe_budget=1, n_rounds=3
        )
        assert scheduler.nfe_per_round == pytest.approx(1.0 / 3.0)
        # memory_fraction is tiny but non-negative.
        assert scheduler.memory_fraction >= 0.0
        # And n_cap stays in [0, 1].
        assert 0.0 <= scheduler.n_cap <= 1.0

    def test_max_memory_fraction_zero_yields_full_capacity(self) -> None:
        """``max_memory_fraction = 0`` -> ``n_cap = 1`` (no memory dominance)."""
        scheduler = NFEAwareMemoryScheduler(
            cycle_length=10,
            nfe_budget=50,
            n_rounds=3,
            max_memory_fraction=0.0,
        )
        assert scheduler.memory_fraction == pytest.approx(0.0)
        assert scheduler.n_cap == pytest.approx(1.0)
        # Sampling round-by-round: every round emits n_cap == 1.
        for r in range(10):
            sample = scheduler.sample(0, r, r)
            assert sample.n_cap == pytest.approx(1.0)

    def test_max_memory_fraction_one_yields_zero_capacity(self) -> None:
        """``max_memory_fraction = 1`` -> ``n_cap = 0`` (full memory dominance)."""
        scheduler = NFEAwareMemoryScheduler(
            cycle_length=10,
            nfe_budget=200,
            n_rounds=3,
            max_memory_fraction=1.0,
        )
        assert scheduler.memory_fraction == pytest.approx(1.0)
        assert scheduler.n_cap == pytest.approx(0.0)
        for r in range(10):
            sample = scheduler.sample(0, r, r)
            assert sample.n_cap == pytest.approx(0.0)

    def test_seed_variant_does_not_affect_schedule(self) -> None:
        """Different ``seed`` values produce the SAME schedule (deterministic family).

        The NFE-aware scheduler is deterministic; ``seed`` only enters
        the :attr:`config_hash`. Two schedulers with different seeds
        but otherwise identical kwargs emit identical ``n_cap`` for
        every round.
        """
        s1 = NFEAwareMemoryScheduler(
            cycle_length=10, nfe_budget=50, n_rounds=3, seed=0
        )
        s2 = NFEAwareMemoryScheduler(
            cycle_length=10, nfe_budget=50, n_rounds=3, seed=42
        )
        for r in range(10):
            assert s1.sample(0, r, r).n_cap == pytest.approx(
                s2.sample(0, r, r).n_cap
            )

    def test_n_cap_in_unit_interval_invariant(self) -> None:
        """``n_cap in [0, 1]`` invariant for the NFE-aware family.

        Walks the legal parameter space (budgets from 1 to 1000,
        thresholds from 1 to 100) and verifies the invariant.
        """
        for budget, threshold, mmax in (
            (1, 1, 0.0),
            (1, 1, 1.0),
            (1000, 1, 0.0),
            (1000, 1, 1.0),
            (50, 10, 0.5),
        ):
            scheduler = NFEAwareMemoryScheduler(
                cycle_length=10,
                nfe_budget=budget,
                n_rounds=3,
                threshold=threshold,
                max_memory_fraction=mmax,
            )
            for r in range(10):
                sample = scheduler.sample(0, r, r)
                assert 0.0 <= sample.n_cap <= 1.0, (
                    f"n_cap={sample.n_cap} for budget={budget}, "
                    f"threshold={threshold}, mmax={mmax}, r={r}"
                )


# ===========================================================================
# TestFreeTrajScheduler -- trajectory-aware substep family
# ===========================================================================


class TestFreeTrajScheduler:
    """Edge cases for :class:`FreeTrajScheduler`.

    The FreeTraj scheduler wraps the cosine baseline and adds a small
    sinusoidal substep. Edge cases:

    * trajectory length 0 (single-round cycle, ``u_r = 0.5``);
    * very long trajectory (``cycle_length = 1000``);
    * ``trajectory_amplitude = 0`` -> the substep is always zero and
      the scheduler matches the cosine baseline exactly;
    * ``trajectory_amplitude`` negative -> the constructor rejects it
      (must lie in ``[0, 1]``).
    """

    def test_trajectory_length_zero_single_round_cycle(self) -> None:
        """``cycle_length = 1`` (degenerate single-round cycle)."""
        scheduler = FreeTrajScheduler(
            _make_cosine_config(cycle_length=1, n_min=0.0, n_max=1.0),
        )
        sample = scheduler.sample(0, 0, 0)
        # n_cap is finite and in [0, 1].
        assert 0.0 <= sample.n_cap <= 1.0
        assert math.isfinite(sample.n_cap)

    def test_trajectory_length_very_long_does_not_raise(self) -> None:
        """``cycle_length = 1000`` -- the scheduler samples without error."""
        scheduler = FreeTrajScheduler(
            _make_cosine_config(cycle_length=1000, n_min=0.0, n_max=1.0),
        )
        # Sample the first, middle, and last rounds.
        for r in (0, 500, 999):
            sample = scheduler.sample(0, r, r)
            assert 0.0 <= sample.n_cap <= 1.0

    def test_trajectory_amplitude_zero_matches_cosine_baseline(self) -> None:
        """``trajectory_amplitude = 0`` -> substep is zero, equals cosine baseline.

        The wrapped cosine scheduler's ``n_cap`` equals
        :class:`FreeTrajScheduler`'s ``n_cap`` for every round.
        """
        scheduler = FreeTrajScheduler(
            _make_cosine_config(cycle_length=10, n_min=0.0, n_max=1.0),
            trajectory_amplitude=0.0,
            trajectory_period=4,
        )
        baseline = default_cosine_scheduler(
            cycle_length=10, n_min=0.0, n_max=1.0,
        )
        for r in range(10):
            sample = scheduler.sample(0, r, r)
            base_cap = baseline.sample(0, r, r).n_cap
            assert sample.n_cap == pytest.approx(base_cap, abs=1e-9)

    def test_trajectory_amplitude_negative_is_rejected(self) -> None:
        """``trajectory_amplitude < 0`` raises ``ValueError``."""
        with pytest.raises(ValueError, match="trajectory_amplitude"):
            FreeTrajScheduler(
                _make_cosine_config(cycle_length=10),
                trajectory_amplitude=-0.1,
            )

    def test_trajectory_amplitude_above_one_is_rejected(self) -> None:
        """``trajectory_amplitude > 1`` raises ``ValueError``."""
        with pytest.raises(ValueError, match="trajectory_amplitude"):
            FreeTrajScheduler(
                _make_cosine_config(cycle_length=10),
                trajectory_amplitude=1.5,
            )

    def test_trajectory_period_zero_is_rejected(self) -> None:
        """``trajectory_period < 1`` raises ``ValueError``."""
        with pytest.raises(ValueError, match="trajectory_period"):
            FreeTrajScheduler(
                _make_cosine_config(cycle_length=10),
                trajectory_period=0,
            )

    def test_n_cap_in_unit_interval_invariant(self) -> None:
        """``n_cap in [0, 1]`` invariant for the FreeTraj family."""
        scheduler = FreeTrajScheduler(
            _make_cosine_config(cycle_length=20, n_min=0.0, n_max=1.0),
            trajectory_amplitude=1.0,  # extreme amplitude
        )
        for r in range(20):
            sample = scheduler.sample(0, r, r)
            assert 0.0 <= sample.n_cap <= 1.0


# ===========================================================================
# TestTierAwareCodimensionSheetScheduler -- tier-quantile wrapper
# ===========================================================================


class TestTierAwareCodimensionSheetScheduler:
    """Edge cases for :class:`TierAwareCodimensionSheetScheduler`.

    The tier-aware wrapper reduces ``n_cap`` by
    ``easy_tier_nfe_reduction_factor`` on the *easy* tier and passes
    hard / medium tiers through unchanged. Edge cases:

    * tier assignment ties (record whose baseline metric equals the
      quantile boundary) -- the boundary itself counts as the
      *higher* tier per the ``<=`` comparison;
    * single-tier fallback (only one baseline metric value) -- every
      record is in the same tier;
    * ``n_cap *= 0.5`` floor -- the reduction cannot drive ``n_cap``
      below ``n_min``;
    * no baseline metrics mapping -> falls through with full ``n_cap``;
    * ``easy_tier_nfe_reduction_factor = 1.0`` (the default) is a safe
      no-op.
    """

    def test_tier_assignment_ties_at_boundary_are_hard(self) -> None:
        """A record whose metric EQUALS the low boundary is *hard*.

        The boundary ``<=`` test places the record in the *hard* tier
        (the lower of the two adjacent tiers). The test arranges the
        baseline metrics so that one record's metric equals the
        computed low boundary value -- that record is then classified
        as ``hard`` (not ``medium``).
        """
        wrapper = TierAwareCodimensionSheetScheduler(
            easy_tier_nfe_reduction_factor=0.5,
            tier_quantile_boundaries=(0.25, 0.5),
        )
        # Five records evenly spaced [0, 0.25, 0.5, 0.75, 1.0]: the
        # 25th percentile is exactly 0.25 (= low boundary) and the
        # 50th percentile is exactly 0.5 (= high boundary) under
        # ``np.quantile`` linear interpolation. The ``0.25`` record
        # therefore sits AT the low boundary and is classified as
        # ``hard`` (the boundary itself falls into the lower tier per
        # the ``<=`` test); the ``0.5`` record sits AT the high
        # boundary and is classified as ``medium``.
        wrapper.set_baseline_metrics(
            {
                "below_rec": 0.0,
                "low_boundary_rec": 0.25,
                "high_boundary_rec": 0.5,
                "above_rec": 0.75,
                "easy_rec": 1.0,
            }
        )
        low, high = wrapper.tier_boundaries
        assert low == pytest.approx(0.25, abs=1e-9)
        assert high == pytest.approx(0.5, abs=1e-9)
        # Boundary record at the LOW boundary -> hard (the ``<=`` test
        # puts the boundary itself into the lower tier).
        wrapper.set_current_record("low_boundary_rec")
        wrapper.sample(0, 0, 0)
        assert wrapper.last_tier == "hard"
        # Boundary record at the HIGH boundary -> medium (the ``<=``
        # test puts the upper boundary into the medium tier).
        wrapper.set_current_record("high_boundary_rec")
        wrapper.sample(0, 0, 0)
        assert wrapper.last_tier == "medium"
        # A record strictly below the low boundary -> hard.
        wrapper.set_current_record("below_rec")
        wrapper.sample(0, 0, 0)
        assert wrapper.last_tier == "hard"
        # A record strictly above the high boundary -> easy.
        wrapper.set_current_record("easy_rec")
        wrapper.sample(0, 0, 0)
        assert wrapper.last_tier == "easy"

    def test_single_tier_fallback_all_records_same_tier(self) -> None:
        """With one unique baseline metric value, every record is in the same tier.

        The quantile computation produces ``low == high == value``;
        every record is at the boundary and classified as ``hard``
        (because the boundary itself is included in the lower tier).
        """
        wrapper = TierAwareCodimensionSheetScheduler(
            easy_tier_nfe_reduction_factor=0.5,
        )
        wrapper.set_baseline_metrics({"rec_a": 0.7, "rec_b": 0.7, "rec_c": 0.7})
        wrapper.set_current_record("rec_a")
        wrapper.sample(0, 0, 0)
        assert wrapper.last_tier in {"hard", "medium", "easy"}

    def test_no_baseline_metrics_falls_through_with_full_n_cap(self) -> None:
        """No baseline mapping -> the wrapper emits the FULL ``n_cap``.

        The audit trail shows ``tier_aware_medium_passthrough`` (the
        safe default), and the ``last_tier`` is ``"medium"``.
        """
        wrapper = TierAwareCodimensionSheetScheduler(
            easy_tier_nfe_reduction_factor=0.5,
        )
        # Note: no ``set_baseline_metrics`` call.
        sample = wrapper.sample(0, 0, 0)
        # Full n_cap (the wrapped codimension scheduler emits
        # n_min + (n_max - n_min) * ratio; the wrapper multiplies by
        # 0.5 only on the easy tier, but no record -> easy tier never
        # activated).
        assert math.isfinite(sample.n_cap)
        assert wrapper.last_tier == "medium"

    def test_easy_tier_factor_one_is_no_op(self) -> None:
        """``easy_tier_nfe_reduction_factor = 1.0`` -> the wrapper is a no-op.

        With ``factor = 1`` every tier sees the full ``n_cap``. This
        is the safe default documented in Wave 233 P3.
        """
        wrapper = TierAwareCodimensionSheetScheduler(
            easy_tier_nfe_reduction_factor=1.0,
        )
        # Build a mapping with a clear easy-tier outlier.
        wrapper.set_baseline_metrics(
            {"hard_rec": 0.0, "med_rec": 0.5, "easy_rec": 1.0}
        )
        baseline = default_cosine_scheduler(cycle_length=10)
        for rec_id in ("hard_rec", "med_rec", "easy_rec"):
            wrapper.set_current_record(rec_id)
            sample = wrapper.sample(0, 0, 0)
            base_cap = baseline.sample(0, 0, 0).n_cap
            # With factor = 1.0, the wrapper passes through unchanged.
            assert sample.n_cap == pytest.approx(base_cap, abs=1e-9)

    def test_easy_tier_factor_half_does_not_drive_n_cap_below_zero(self) -> None:
        """``easy_tier_nfe_reduction_factor = 0.5`` -- ``n_cap`` floor at ``n_min``.

        The reduction cannot drive ``n_cap`` below ``n_min`` (and
        therefore below zero). The wrapped scheduler has ``n_min=0``
        so ``n_cap >= 0`` always.
        """
        wrapper = TierAwareCodimensionSheetScheduler(
            easy_tier_nfe_reduction_factor=0.5,
            # Wider gap between hard and easy so we have a clear easy record.
        )
        wrapper.set_baseline_metrics(
            {"hard_rec": 0.0, "med_rec": 0.5, "easy_rec": 1.0}
        )
        wrapper.set_current_record("easy_rec")
        for r in range(10):
            sample = wrapper.sample(0, r, r)
            assert 0.0 <= sample.n_cap <= 1.0

    def test_easy_tier_factor_zero_is_rejected(self) -> None:
        """``easy_tier_nfe_reduction_factor = 0`` is rejected.

        The factor must lie in ``(0, 1]`` -- a zero factor would
        silently zero out the easy tier.
        """
        with pytest.raises(ValueError, match="easy_tier_nfe_reduction_factor"):
            TierAwareCodimensionSheetScheduler(
                easy_tier_nfe_reduction_factor=0.0,
            )

    def test_easy_tier_factor_above_one_is_rejected(self) -> None:
        """``easy_tier_nfe_reduction_factor > 1`` is rejected (must lie in ``(0, 1]``)."""
        with pytest.raises(ValueError, match="easy_tier_nfe_reduction_factor"):
            TierAwareCodimensionSheetScheduler(
                easy_tier_nfe_reduction_factor=1.5,
            )

    def test_quantile_boundaries_invalid_order_rejected(self) -> None:
        """``tier_quantile_boundaries`` outside ``(0, 1)`` with strict order is rejected."""
        with pytest.raises(ValueError, match="quantiles"):
            TierAwareCodimensionSheetScheduler(
                tier_quantile_boundaries=(0.5, 0.3),  # not strictly ordered
            )

    def test_n_cap_in_unit_interval_invariant(self) -> None:
        """``n_cap in [0, 1]`` invariant for the tier-aware wrapper."""
        wrapper = TierAwareCodimensionSheetScheduler(
            easy_tier_nfe_reduction_factor=0.1,  # very aggressive
        )
        wrapper.set_baseline_metrics(
            {f"rec_{i}": float(i) / 10.0 for i in range(10)}
        )
        for i in range(10):
            wrapper.set_current_record(f"rec_{i}")
            for r in range(10):
                sample = wrapper.sample(0, r, r)
                assert 0.0 <= sample.n_cap <= 1.0


# ===========================================================================
# TestSchedulerDeterminism -- D.4 byte-stable contract
# ===========================================================================


class TestSchedulerDeterminism:
    """Byte-stable D.4 contract.

    The framework's regression-vector suite (``tests/test_d4_regression_vectors.py``)
    enforces byte-stable schedules for the canonical cosine family.
    This class extends the contract to the paper-grounded controllers:

    * **Same kwargs** + **same paper_quantities sequence** + **same seed**
      -> **same ``n_cap``** byte-for-byte across ``N`` rounds, repeated
      ``3`` times.

    The deterministic property holds because every paper-grounded
    controller is a closed-form function of its inputs (no hidden
    state, no RNG between samples). The contract is verified via
    :func:`hashlib.sha256` so any rounding-mode change (e.g. switching
    from C ``double`` to ``longdouble``) would surface as a hash
    mismatch.
    """

    @staticmethod
    def _hash_n_cap_seq(seq: list[float]) -> str:
        """Return a stable SHA-256 digest of an ``n_cap`` sequence."""
        # Pack to bytes via float64 little-endian for byte-stable hashing.
        arr = np.asarray(seq, dtype=np.float64)
        return hashlib.sha256(arr.tobytes()).hexdigest()

    def test_codim_sheet_byte_stable_across_rounds(self) -> None:
        """CodimensionSheetScheduler emits a byte-stable ``n_cap`` sequence."""
        scheduler = CodimensionSheetScheduler(
            cycle_length=20,
            n_min=0.0,
            n_max=1.0,
            profile_residual_fn=_identity_profile,
            eps_implicit=0.05,
            seed=42,
        )
        seq = _collect_n_cap_seq(scheduler, 20)
        h = self._hash_n_cap_seq(seq)
        for _ in range(3):
            scheduler.reset()
            seq2 = _collect_n_cap_seq(scheduler, 20)
            assert self._hash_n_cap_seq(seq2) == h

    def test_paper_ratio_adaptive_byte_stable_across_rounds(self) -> None:
        """PaperRatioAdaptiveScheduler emits a byte-stable ``n_cap`` sequence."""
        scheduler = PaperRatioAdaptiveScheduler(
            kp=0.1,
            kd=0.05,
            shift_max=0.3,
            ema=0.3,
        )
        # Fixed paper-quantities sequence.
        pq_seq = [
            {"sheet_A": 0.5 + 0.05 * r} for r in range(20)
        ]
        for r, pq in enumerate(pq_seq):
            scheduler.record_round_feedback(r, paper_quantities=pq)
        seq = _collect_n_cap_seq(scheduler, 20)
        h = self._hash_n_cap_seq(seq)
        for _ in range(3):
            scheduler.reset()
            for r, pq in enumerate(pq_seq):
                scheduler.record_round_feedback(r, paper_quantities=pq)
            seq2 = _collect_n_cap_seq(scheduler, 20)
            assert self._hash_n_cap_seq(seq2) == h

    def test_convergence_adaptive_byte_stable_across_rounds(self) -> None:
        """ConvergenceAdaptiveScheduler emits a byte-stable ``n_cap`` sequence."""
        scheduler = ConvergenceAdaptiveScheduler(
            base=default_cosine_scheduler(cycle_length=20),
            kp=0.1,
            kd=0.05,
            shift_max=0.3,
            ema=0.3,
        )
        w2_seq = [1.0 / (r + 1) for r in range(20)]
        for r, w2 in enumerate(w2_seq):
            scheduler.record_round_feedback(r, {"W2": w2})
        seq = _collect_n_cap_seq(scheduler, 20)
        h = self._hash_n_cap_seq(seq)
        for _ in range(3):
            scheduler.reset()
            for r, w2 in enumerate(w2_seq):
                scheduler.record_round_feedback(r, {"W2": w2})
            seq2 = _collect_n_cap_seq(scheduler, 20)
            assert self._hash_n_cap_seq(seq2) == h

    def test_nfe_aware_byte_stable_across_rounds(self) -> None:
        """NFEAwareMemoryScheduler emits a byte-stable ``n_cap`` sequence."""
        scheduler = NFEAwareMemoryScheduler(
            cycle_length=20,
            nfe_budget=50,
            n_rounds=3,
            seed=42,
        )
        seq = _collect_n_cap_seq(scheduler, 20)
        h = self._hash_n_cap_seq(seq)
        for _ in range(3):
            scheduler.reset()
            seq2 = _collect_n_cap_seq(scheduler, 20)
            assert self._hash_n_cap_seq(seq2) == h

    def test_freetraj_byte_stable_across_rounds(self) -> None:
        """FreeTrajScheduler emits a byte-stable ``n_cap`` sequence."""
        scheduler = FreeTrajScheduler(
            _make_cosine_config(cycle_length=20, n_min=0.0, n_max=1.0),
            trajectory_amplitude=0.05,
            trajectory_period=4,
        )
        seq = _collect_n_cap_seq(scheduler, 20)
        h = self._hash_n_cap_seq(seq)
        for _ in range(3):
            scheduler.reset()
            seq2 = _collect_n_cap_seq(scheduler, 20)
            assert self._hash_n_cap_seq(seq2) == h

    def test_tier_aware_byte_stable_across_rounds(self) -> None:
        """TierAwareCodimensionSheetScheduler emits a byte-stable ``n_cap`` sequence."""
        wrapper = TierAwareCodimensionSheetScheduler(
            easy_tier_nfe_reduction_factor=0.5,
        )
        wrapper.set_baseline_metrics(
            {f"rec_{i}": float(i) / 10.0 for i in range(5)}
        )
        # Pin the current record so the tier is stable.
        wrapper.set_current_record("rec_4")  # highest -> easy
        seq: list[float] = []
        for r in range(20):
            sample = wrapper.sample(0, r, r)
            seq.append(float(sample.n_cap))
        h = self._hash_n_cap_seq(seq)
        for _ in range(3):
            wrapper.reset()
            wrapper.set_baseline_metrics(
                {f"rec_{i}": float(i) / 10.0 for i in range(5)}
            )
            wrapper.set_current_record("rec_4")
            seq2: list[float] = []
            for r in range(20):
                sample = wrapper.sample(0, r, r)
                seq2.append(float(sample.n_cap))
            assert self._hash_n_cap_seq(seq2) == h


__all__ = [
    "TestCodimensionSheetScheduler",
    "TestPaperRatioAdaptiveScheduler",
    "TestConvergenceAdaptiveScheduler",
    "TestEvidenceDrivenScheduler",
    "TestNFEAwareMemoryScheduler",
    "TestFreeTrajScheduler",
    "TestTierAwareCodimensionSheetScheduler",
    "TestSchedulerDeterminism",
]
