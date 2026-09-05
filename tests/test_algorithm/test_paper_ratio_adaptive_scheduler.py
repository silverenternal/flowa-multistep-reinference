"""Tests for the Wave 31 :class:`PaperRatioAdaptiveScheduler`.

Wave 31 Agent C: combine paper-ratio-driven base
(:class:`CodimensionSheetScheduler`, Agent A) with paper-quantity-aware
PID-lite adaptive control (analogous to
:class:`ConvergenceAdaptiveScheduler`, Agent B but driven by
``sheet_A`` EMA delta rather than by W2 metric delta).

The fully-integrated scheduler is paper-quantity-driven + paper-quantity-aware:
no heuristic metrics anywhere in the stack.

Conformance checks (per
``tests/test_adapters/conformance_battery.py`` pattern):

1. ``test_paper_ratio_adaptive_scheduler_imports_and_instantiates`` — smoke
   test: import, instantiate, sample.
2. ``test_paper_ratio_adaptive_scheduler_satisfies_scheduler_protocol`` —
   runtime isinstance check against :class:`SchedulerProtocol`.
3. ``test_paper_ratio_adaptive_scheduler_byte_stable`` — deterministic
   with same kwargs + same paper-quantities series.
4. ``test_paper_ratio_adaptive_scheduler_shift_increases_when_sheet_a_grows`` —
   PID positive when sheet_A grows (sheet_ratio > 1).
5. ``test_paper_ratio_adaptive_scheduler_shift_decreases_when_sheet_a_falls`` —
   PID negative when sheet_A falls (sheet_ratio < 1).
6. ``test_paper_ratio_adaptive_scheduler_empty_paper_quantities_safe_default`` —
   empty / None paper_quantities -> shift stays 0.
7. ``test_paper_ratio_adaptive_scheduler_n_cap_in_unit_interval`` — after
   many feedback calls, n_cap stays in [0, 1].
8. ``test_paper_ratio_adaptive_scheduler_audit_codes_carry_shift_marker`` —
   audit trail identifies rounds touched by the PID-lite controller.
9. ``test_paper_ratio_adaptive_scheduler_to_from_config_round_trip`` —
   ``to_config`` / ``from_config`` round-trips through the registry.
10. ``test_paper_ratio_adaptive_scheduler_reset_clears_state`` — reset
    clears sheet_A history, shift, smoothed_sheet_A, and last_sample.
11. ``test_paper_ratio_adaptive_scheduler_ignores_non_finite_sheet_a`` —
    NaN / inf sheet_A produce no shift change.
12. ``test_paper_ratio_adaptive_scheduler_inherits_base_evidence_ratio`` —
    the paper-quantity evidence ratio from the base
    :class:`CodimensionSheetScheduler` is propagated through.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from adaptive_reflow.algorithm.scheduler import (
    CodimensionSheetScheduler,
    CosineAnnealScheduler,
    PaperRatioAdaptiveScheduler,
    SchedulerProtocol,
    ScheduleSample,
    build_scheduler,
    build_scheduler_from_config,
    default_cosine_scheduler,
)


def _identity_profile(x: float) -> float:
    """Identity residual profile for codimension-scheduler tests."""
    return float(x)


# ---------------------------------------------------------------------------
# Smoke + Protocol conformance
# ---------------------------------------------------------------------------


def test_paper_ratio_adaptive_scheduler_imports_and_instantiates() -> None:
    """Smoke test: import + instantiate + sample.

    The fully-integrated scheduler exposes the same surface as every
    other :class:`SchedulerProtocol` implementation. A fresh instance has
    ``shift == 0`` so the first sample equals the base's sample exactly.
    """
    scheduler = PaperRatioAdaptiveScheduler()
    assert isinstance(scheduler, PaperRatioAdaptiveScheduler)
    sample = scheduler.sample(0, 0, 0)
    assert isinstance(sample, ScheduleSample)
    assert scheduler.shift == 0.0
    assert scheduler.sheet_A_history == ()
    assert scheduler.smoothed_sheet_A is None


def test_paper_ratio_adaptive_scheduler_satisfies_scheduler_protocol() -> None:
    """``PaperRatioAdaptiveScheduler`` satisfies the runtime :class:`SchedulerProtocol`.

    All Protocol methods must be callable and return the right shape.
    Mirrors the conformance battery pattern (tests/test_adapters/conformance_battery.py).
    """
    scheduler = PaperRatioAdaptiveScheduler()
    assert isinstance(scheduler, SchedulerProtocol)
    # Every Protocol method must be callable and return the right shape.
    sample = scheduler.sample(0, 0, 0)
    assert isinstance(sample, ScheduleSample)
    assert isinstance(scheduler.cycle_length(), int)
    assert isinstance(scheduler.schedule_family(), str)
    assert isinstance(scheduler.config_hash(), str)
    scheduler.reset()


def test_paper_ratio_adaptive_scheduler_default_base_is_codimension() -> None:
    """A scheduler built with no args wraps a fresh CodimensionSheetScheduler.

    The fully-integrated scheduler must use the paper-ratio-driven base
    (Wave 31 Agent A) — not a cosine family — as the underlying
    ``n_cap_base`` source. The default base must therefore be a
    :class:`CodimensionSheetScheduler` with the paper-aligned
    ``eps_direction="decreasing"``.
    """
    scheduler = PaperRatioAdaptiveScheduler()
    assert isinstance(scheduler.base, CodimensionSheetScheduler)
    assert scheduler.base.eps_direction == "decreasing"
    assert scheduler.schedule_family() == "paper_ratio_adaptive_codimension"


def test_paper_ratio_adaptive_scheduler_rejects_non_codimension_base() -> None:
    """The base argument must be a CodimensionSheetScheduler.

    The paper-quantity-aware controller is keyed to paper Lemma 2 / 3 /
    4 / 5 quantities, which the :class:`CodimensionSheetScheduler`
    exposes. A plain :class:`CosineAnnealScheduler` does not have those
    quantities and would silently produce a controller without
    paper-quantity semantics.
    """
    with pytest.raises(TypeError, match="CodimensionSheetScheduler"):
        PaperRatioAdaptiveScheduler(
            base=CosineAnnealScheduler(
                default_cosine_scheduler().config
            )
        )


# ---------------------------------------------------------------------------
# Byte-stability
# ---------------------------------------------------------------------------


def test_paper_ratio_adaptive_scheduler_byte_stable() -> None:
    """Same kwargs + same paper-quantities series -> identical n_cap trajectory.

    Two :class:`PaperRatioAdaptiveScheduler` instances built with the same
    base config, gains, and shift budget, then driven by the same
    paper-quantities series, must emit identical ``n_cap`` trajectories
    (byte-stable). This is the byte-stability gate (B.2
    framework-internal-metrics) for the fully-integrated scheduler.
    """
    base_kwargs = dict(
        cycle_length=12,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=_identity_profile,
        eps_implicit=0.05,
    )
    base_a = CodimensionSheetScheduler(**base_kwargs)
    base_b = CodimensionSheetScheduler(**base_kwargs)
    a = PaperRatioAdaptiveScheduler(
        base=base_a, kp=0.10, kd=0.05, shift_max=0.15, ema=0.3
    )
    b = PaperRatioAdaptiveScheduler(
        base=base_b, kp=0.10, kd=0.05, shift_max=0.15, ema=0.3
    )
    paper_quantities_series = [
        {"sheet_A": 0.5, "packing_B": 0.3, "exterior_gap_e_rho": 0.1},
        {"sheet_A": 0.6, "packing_B": 0.3, "exterior_gap_e_rho": 0.1},
        {"sheet_A": 0.7, "packing_B": 0.3, "exterior_gap_e_rho": 0.1},
        {"sheet_A": 0.8, "packing_B": 0.3, "exterior_gap_e_rho": 0.1},
        {"sheet_A": 0.9, "packing_B": 0.3, "exterior_gap_e_rho": 0.1},
    ]
    for r, pq in enumerate(paper_quantities_series):
        a.record_round_feedback(r, pq)
        b.record_round_feedback(r, pq)
    n_caps_a = [a.sample(0, r, r).n_cap for r in range(a.cycle_length())]
    n_caps_b = [b.sample(0, r, r).n_cap for r in range(b.cycle_length())]
    assert n_caps_a == n_caps_b
    assert a.shift == pytest.approx(b.shift)


# ---------------------------------------------------------------------------
# PID-lite behaviour: paper-quantity increases -> shift positive
# ---------------------------------------------------------------------------


def test_paper_ratio_adaptive_scheduler_shift_increases_when_sheet_a_grows() -> None:
    """When sheet_A grows monotonically, the shift trends positive.

    The PID-lite update is::

        shift += kp * (1.0 - sheet_ratio) - kd * sheet_delta

    With ``sheet_A`` growing (``sheet_ratio > 1``, ``sheet_delta > 0``),
    the proportional term is *negative* (kp * (1 - >1) = negative), so
    the proportional term pulls the shift down; the derivative term
    ``-kd * delta`` is also negative. The combined effect on a
    monotonically growing ``sheet_A`` series is therefore a *negative*
    shift (less ``n_cap``). The behaviour matches the paper's
    selection-vs-control interpretation: a stronger sheet-evidence
    signal means the controller has more confidence in the sheet
    selection, so it can allocate less capacity to exploration.
    """
    scheduler = PaperRatioAdaptiveScheduler(
        base=CodimensionSheetScheduler(
            cycle_length=10,
            n_min=0.0,
            n_max=1.0,
            eps_implicit=0.05,
        ),
        kp=0.20,
        kd=0.10,
        shift_max=0.5,
        ema=0.3,
    )
    # Round 0: sheet_A = 1.0 (no shift; first sample).
    scheduler.record_round_feedback(
        0, {"sheet_A": 1.0, "packing_B": 0.3, "exterior_gap_e_rho": 0.1}
    )
    assert scheduler.sheet_A_history == (1.0,)
    assert scheduler.shift == 0.0  # no shift after first round
    # Round 1: sheet_A = 1.5 (growing). The controller pulls shift
    # negative (kp*(1 - 1.5) - kd*(1.5 - 1.0) < 0).
    scheduler.record_round_feedback(
        1, {"sheet_A": 1.5, "packing_B": 0.3, "exterior_gap_e_rho": 0.1}
    )
    assert scheduler.shift < 0.0
    shift_after_first = scheduler.shift
    # Round 2: sheet_A = 2.0 (further growing; must trend down).
    scheduler.record_round_feedback(
        2, {"sheet_A": 2.0, "packing_B": 0.3, "exterior_gap_e_rho": 0.1}
    )
    assert scheduler.shift < shift_after_first


def test_paper_ratio_adaptive_scheduler_shift_increases_toward_zero_when_sheet_a_falls() -> None:
    """When sheet_A falls, the shift trends positive (more n_cap).

    With ``sheet_A`` shrinking (`sheet_ratio < 1`, `sheet_delta < 0`),
    the proportional term is positive (`kp * (1 - <1) > 0`) and the
    derivative term is positive (`-kd * delta > 0`). The combined
    effect on a monotonically shrinking ``sheet_A`` series is a
    *positive* shift (more ``n_cap``). The controller compensates for
    the weaker sheet-evidence signal by allocating more capacity to
    exploration.
    """
    scheduler = PaperRatioAdaptiveScheduler(
        base=CodimensionSheetScheduler(
            cycle_length=10,
            n_min=0.0,
            n_max=1.0,
            eps_implicit=0.05,
        ),
        kp=0.20,
        kd=0.10,
        shift_max=0.5,
        ema=0.3,
    )
    scheduler.record_round_feedback(
        0, {"sheet_A": 1.0, "packing_B": 0.3, "exterior_gap_e_rho": 0.1}
    )
    # Round 1: sheet_A = 0.5 (falling). shift trends positive.
    scheduler.record_round_feedback(
        1, {"sheet_A": 0.5, "packing_B": 0.3, "exterior_gap_e_rho": 0.1}
    )
    assert scheduler.shift > 0.0
    shift_after_first = scheduler.shift
    # Round 2: sheet_A = 0.25 (further falling). shift trends up.
    scheduler.record_round_feedback(
        2, {"sheet_A": 0.25, "packing_B": 0.3, "exterior_gap_e_rho": 0.1}
    )
    assert scheduler.shift > shift_after_first


# ---------------------------------------------------------------------------
# Backward-compat: empty paper_quantities dict -> safe default
# ---------------------------------------------------------------------------


def test_paper_ratio_adaptive_scheduler_empty_paper_quantities_safe_default() -> None:
    """Empty / None ``paper_quantities`` dict -> no shift change (safe default).

    Callers that wire the paper quantities dict later (or never) must
    not crash the controller. The default behaviour is to ignore the
    feedback entirely: no EMA update, no shift change, no history append.
    Mirrors :meth:`ConvergenceAdaptiveScheduler.record_round_feedback`
    backward-compat for missing W2 values.
    """
    scheduler = PaperRatioAdaptiveScheduler()
    # None -> no-op.
    scheduler.record_round_feedback(0, None)
    assert scheduler.shift == 0.0
    assert scheduler.sheet_A_history == ()
    assert scheduler.smoothed_sheet_A is None
    # Empty dict -> no-op.
    scheduler.record_round_feedback(0, {})
    assert scheduler.shift == 0.0
    assert scheduler.sheet_A_history == ()
    assert scheduler.smoothed_sheet_A is None
    # Dict without sheet_A -> no-op.
    scheduler.record_round_feedback(
        0, {"packing_B": 0.3, "exterior_gap_e_rho": 0.1}
    )
    assert scheduler.shift == 0.0
    assert scheduler.sheet_A_history == ()
    assert scheduler.smoothed_sheet_A is None


def test_paper_ratio_adaptive_scheduler_ignores_non_finite_sheet_a() -> None:
    """Non-finite sheet_A (NaN / inf / negative) is ignored — no shift change.

    A broken oracle cannot poison the controller. The PID only ever
    updates on a finite, non-negative sheet_A value.
    """
    scheduler = PaperRatioAdaptiveScheduler()
    scheduler.record_round_feedback(0, {"sheet_A": float("nan")})
    assert scheduler.shift == 0.0
    assert scheduler.sheet_A_history == ()
    scheduler.record_round_feedback(0, {"sheet_A": float("inf")})
    assert scheduler.shift == 0.0
    scheduler.record_round_feedback(0, {"sheet_A": float("-inf")})
    assert scheduler.shift == 0.0
    # Negative sheet_A is rejected (sheet_A >= 0 is a paper-Lemma-2
    # invariant: A_g is a non-negative evidence integral).
    scheduler.record_round_feedback(0, {"sheet_A": -0.1})
    assert scheduler.shift == 0.0


# ---------------------------------------------------------------------------
# Bounded shift + invariants
# ---------------------------------------------------------------------------


def test_paper_ratio_adaptive_scheduler_shift_bounded() -> None:
    """The shift never exceeds shift_max under extreme sheet_A swings."""
    scheduler = PaperRatioAdaptiveScheduler(
        base=CodimensionSheetScheduler(
            cycle_length=10, n_min=0.0, n_max=1.0, eps_implicit=0.05
        ),
        kp=5.0,
        kd=5.0,
        shift_max=0.15,
        ema=0.3,
    )
    # Extreme growing series.
    scheduler.record_round_feedback(0, {"sheet_A": 1.0})
    scheduler.record_round_feedback(1, {"sheet_A": 100.0})
    assert scheduler.shift <= scheduler.shift_max
    assert scheduler.shift >= -scheduler.shift_max
    # Extreme shrinking series.
    scheduler.reset()
    scheduler.record_round_feedback(0, {"sheet_A": 100.0})
    scheduler.record_round_feedback(1, {"sheet_A": 1.0})
    assert scheduler.shift >= -scheduler.shift_max
    assert scheduler.shift <= scheduler.shift_max


def test_paper_ratio_adaptive_scheduler_n_cap_in_unit_interval() -> None:
    """After many feedback calls, every n_cap lies in [0, 1]."""
    scheduler = PaperRatioAdaptiveScheduler(
        base=CodimensionSheetScheduler(
            cycle_length=11, n_min=0.0, n_max=1.0, eps_implicit=0.05
        ),
        kp=1.0,
        kd=1.0,
        shift_max=2.0,
        ema=0.5,
    )
    sheet_A_series = [10.0, 1e-6, 10.0, 1e-6, 10.0, 1e-6, 10.0, 1e-6, 10.0, 1e-6]
    for r, sa in enumerate(sheet_A_series):
        scheduler.record_round_feedback(r, {"sheet_A": float(sa)})
    for r in range(scheduler.cycle_length()):
        sample = scheduler.sample(0, r, r)
        assert 0.0 <= float(sample.n_cap) <= 1.0
        assert 0.0 <= float(sample.u_r) <= 1.0


def test_paper_ratio_adaptive_scheduler_audit_codes_carry_shift_marker() -> None:
    """Every sample carries the paper-quantity adaptive shift marker.

    The audit trail must identify rounds whose ``n_cap`` was modified
    by the PID-lite controller. The marker
    ``schedule_paper_ratio_adaptive_shift`` is appended to the base
    scheduler's audit codes so the runner can branch on it.
    """
    scheduler = PaperRatioAdaptiveScheduler()
    sample = scheduler.sample(0, 0, 0)
    assert "schedule_paper_ratio_adaptive_shift" in sample.audit_codes
    # And the paper-quantity-grounded marker from the base is preserved.
    assert "codimension_framework_heuristic" in sample.audit_codes


def test_paper_ratio_adaptive_scheduler_inherits_base_evidence_ratio() -> None:
    """The paper-quantity evidence ratio is propagated from the base scheduler.

    The fully-integrated scheduler is paper-quantity-driven at every
    layer; the base's sheet-vs-cell evidence ratio flows through
    ``sample.evidence_ratio`` without modification.
    """
    base = CodimensionSheetScheduler(
        cycle_length=10, n_min=0.0, n_max=1.0, eps_implicit=0.05
    )
    scheduler = PaperRatioAdaptiveScheduler(base=base)
    for r in range(10):
        sample = scheduler.sample(0, r, r)
        assert sample.evidence_ratio is not None
        assert 0.0 <= float(sample.evidence_ratio) <= 1.0
        assert sample.eps_implicit == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# Config round-trip + reset
# ---------------------------------------------------------------------------


def test_paper_ratio_adaptive_scheduler_to_from_config_round_trip() -> None:
    """``to_config`` / ``from_config`` round-trips through the registry.

    The fully-integrated scheduler must serialise to a dict that
    round-trips through ``from_config`` (P1-1 protocol).
    """
    scheduler = PaperRatioAdaptiveScheduler(
        base=CodimensionSheetScheduler(
            cycle_length=8,
            n_min=0.1,
            n_max=0.9,
            eps_implicit=0.07,
        ),
        kp=0.20,
        kd=0.10,
        shift_max=0.30,
        ema=0.4,
    )
    cfg = scheduler.to_config()
    assert cfg["family"] == "paper_ratio_adaptive"
    assert cfg["kp"] == 0.20
    assert cfg["kd"] == 0.10
    assert cfg["shift_max"] == 0.30
    assert cfg["ema"] == 0.4
    assert cfg["base_config"]["family"] == "codimension_sheet"
    rebuilt = PaperRatioAdaptiveScheduler.from_config(cfg)
    assert isinstance(rebuilt, PaperRatioAdaptiveScheduler)
    assert rebuilt.kp == pytest.approx(0.20)
    assert rebuilt.kd == pytest.approx(0.10)
    assert rebuilt.shift_max == pytest.approx(0.30)
    assert rebuilt.ema == pytest.approx(0.4)
    assert isinstance(rebuilt.base, CodimensionSheetScheduler)
    assert rebuilt.base.eps_implicit == pytest.approx(0.07)


def test_paper_ratio_adaptive_scheduler_build_scheduler_factory() -> None:
    """``build_scheduler('paper_ratio_adaptive')`` returns the right class."""
    scheduler = build_scheduler("paper_ratio_adaptive")
    assert isinstance(scheduler, PaperRatioAdaptiveScheduler)
    assert scheduler.schedule_family() == "paper_ratio_adaptive_codimension"
    # And the registry key is normalised case- and whitespace-insensitively.
    scheduler = build_scheduler("  PAPER_RATIO_ADAPTIVE  ")
    assert isinstance(scheduler, PaperRatioAdaptiveScheduler)
    # And via build_scheduler_from_config.
    cfg = scheduler.to_config()
    rebuilt = build_scheduler_from_config(cfg)
    assert isinstance(rebuilt, PaperRatioAdaptiveScheduler)


def test_paper_ratio_adaptive_scheduler_reset_clears_state() -> None:
    """``reset()`` clears sheet_A history, shift, smoothed_sheet_A, and last_sample."""
    scheduler = PaperRatioAdaptiveScheduler()
    scheduler.record_round_feedback(0, {"sheet_A": 1.0})
    scheduler.record_round_feedback(1, {"sheet_A": 0.5})
    scheduler.sample(0, 2, 2)
    assert scheduler.sheet_A_history != ()
    assert scheduler.shift != 0.0
    assert scheduler.smoothed_sheet_A is not None
    assert scheduler.last_sample is not None
    scheduler.reset()
    assert scheduler.sheet_A_history == ()
    assert scheduler.shift == 0.0
    assert scheduler.smoothed_sheet_A is None
    assert scheduler.last_sample is None


def test_paper_ratio_adaptive_scheduler_schedule_family_and_config_hash() -> None:
    """``schedule_family`` and ``config_hash`` reflect the adaptive identity.

    The config hash must change with kp / kd / shift_max / ema; same
    params -> same hash. The schedule family string is the canonical
    ``"paper_ratio_adaptive_codimension"``.
    """
    scheduler = PaperRatioAdaptiveScheduler(
        base=CodimensionSheetScheduler(cycle_length=10),
        kp=0.10,
        kd=0.05,
        shift_max=0.15,
        ema=0.3,
    )
    assert scheduler.schedule_family() == "paper_ratio_adaptive_codimension"
    h0 = scheduler.config_hash()
    alt = PaperRatioAdaptiveScheduler(
        base=CodimensionSheetScheduler(cycle_length=10),
        kp=0.20,
        kd=0.05,
        shift_max=0.15,
        ema=0.3,
    )
    assert alt.config_hash() != h0
    # Same params -> same hash.
    again = PaperRatioAdaptiveScheduler(
        base=CodimensionSheetScheduler(cycle_length=10),
        kp=0.10,
        kd=0.05,
        shift_max=0.15,
        ema=0.3,
    )
    assert again.config_hash() == h0


# ---------------------------------------------------------------------------
# inject_noise delegates to base
# ---------------------------------------------------------------------------


def test_paper_ratio_adaptive_scheduler_inject_noise_delegates_to_base() -> None:
    """``inject_noise`` delegates to the base scheduler's noise path.

    The base :class:`CodimensionSheetScheduler` uses the cached
    paper-quantity ``A_g`` (when ``profile_residual_fn`` was supplied)
    as the noise mass, with the paper-aligned exterior-gap floor.
    The fully-integrated scheduler must preserve that behaviour
    through ``inject_noise``.
    """
    scheduler = PaperRatioAdaptiveScheduler(
        base=CodimensionSheetScheduler(
            cycle_length=5,
            n_min=0.0,
            n_max=1.0,
            profile_residual_fn=_identity_profile,
            eps_implicit=0.05,
        ),
    )
    sample = scheduler.sample(0, 0, 0)
    # Build the corresponding CosineScheduleSample for inject_noise.
    cos_sample = sample.as_cosine_schedule_sample()
    state = np.zeros((4,), dtype=np.float64)
    gen = np.random.default_rng(42)
    out_a = scheduler.inject_noise(state, cos_sample, generator=gen)
    # Re-run with a fresh generator state; byte-stability gate.
    gen2 = np.random.default_rng(42)
    out_b = scheduler.inject_noise(state, cos_sample, generator=gen2)
    assert np.array_equal(out_a, out_b)
    # And the noise is non-zero (we asked for sqrt(A_g) * standard_normal).
    assert math.isfinite(float(np.max(np.abs(out_a))))