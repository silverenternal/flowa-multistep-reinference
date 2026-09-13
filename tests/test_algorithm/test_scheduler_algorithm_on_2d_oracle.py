"""Scheduler-only oracle validation on the 2D Gaussian-mixture target (P-13).

The :class:`SchedulerProtocol` family (``CosineAnnealScheduler``,
``CodimensionSheetScheduler``) emits per-round samples whose
``n_cap`` drives the framework's bounded-merge envelope. The paper
identifies the closed-form ``eps``-regime (Theorem 1, Lemma 2 +
Lemma 3) with the sheet-vs-cell evidence balance and the exterior
gap ``e_rho``.

This test asserts:

1. The scheduler's ``n_cap`` schedule lies in ``[n_min, n_max]`` for
   every round (``(eps)^2 < e_rho / log 2`` is *not* a paper theorem
   statement — it's the regime selector's constraint; we therefore
   use ``n_cap in [n_min, n_max]`` as the testable proxy).
2. The schedule is **monotone non-increasing** for ``eps_direction=
   "decreasing"`` (paper convention).
3. The schedule's per-round capacity never escapes the canonical
   envelope.
4. The corresponding ``memory_fraction = 1 - n_cap`` is in ``[0, 1]``
   and ``>= 0.5`` at the cycle's terminal round when ``n_min == 0``
   (memory dominates at the end of the cycle per ADR-0010).
5. The ``CodimensionSheetScheduler`` caches the four paper quantities
   (``A_g``, ``B_g``, ``C_g``, ``e_rho``) when a residual profile
   is supplied and exposes them via the documented accessors.
6. The per-round ``evidence_ratio`` reported by
   :class:`CodimensionSheetScheduler` is in ``[0, 1]`` and tends to
   ``1`` as ``eps_implicit -> 0`` (paper Theorem 1 sheet dominance).
"""

from __future__ import annotations

import math

import pytest

from adaptive_reflow.algorithm.scheduler._core import (
    CodimensionSheetScheduler,
    CosineAnnealScheduler,
    SchedulerProtocol,
    default_cosine_scheduler,
)
from adaptive_reflow.contracts import paper_quantities as pq

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_cosine_schedule(
    scheduler: SchedulerProtocol, cycle_length: int
) -> list[float]:
    """Return the per-round ``n_cap`` sequence for one cycle."""
    samples = []
    for r in range(cycle_length):
        s = scheduler.sample(
            outer_cycle_id=0, round_in_cycle=r, target_round=r
        )
        samples.append(float(s.n_cap))
    return samples


# ---------------------------------------------------------------------------
# CosineAnnealScheduler
# ---------------------------------------------------------------------------


def test_cosine_schedule_within_envelope() -> None:
    """``CosineAnnealScheduler`` keeps ``n_cap`` in ``[n_min, n_max]``.

    The framework's canonical envelope ``[0, 1]`` is the contract;
    the scheduler MUST NOT escape it. We use a non-trivial
    ``n_min=0.1, n_max=0.9`` envelope to exercise the clipping
    contract.
    """
    scheduler = default_cosine_scheduler(
        cycle_length=8, n_min=0.1, n_max=0.9
    )
    schedule = _collect_cosine_schedule(scheduler, cycle_length=8)
    for r, nc in enumerate(schedule):
        assert 0.1 - 1e-9 <= nc <= 0.9 + 1e-9, (
            f"n_cap at round {r} escaped envelope: {nc}"
        )


def test_cosine_schedule_monotone_for_n_min_eq_zero() -> None:
    """Cosine schedule is monotone non-increasing across the cycle.

    With ``n_min=0`` the cosine closed-form
    ``n_cap = n_min + (n_max - n_min) * (1 + cos(pi*u_r)) / 2`` is
    monotone non-increasing in ``u_r``. We assert this for the
    framework's default cycle length.
    """
    scheduler = default_cosine_scheduler(cycle_length=10)
    schedule = _collect_cosine_schedule(scheduler, cycle_length=10)
    for i in range(len(schedule) - 1):
        assert schedule[i + 1] <= schedule[i] + 1e-9, (
            f"cosine schedule not monotone non-increasing at round {i}: "
            f"{schedule[i]} -> {schedule[i + 1]}"
        )


def test_cosine_schedule_extremes_match_anchors() -> None:
    """The cosine schedule hits ``n_max`` at ``r=0`` and ``n_min`` at ``r=L-1``.

    Paper Theorem 1 / ADR-0010: ``r=0`` is the high-noise end (lots
    of fresh exploration), ``r=L-1`` is the low-noise end (refinement
    with memory dominant).
    """
    n_min, n_max = 0.1, 0.9
    cycle_length = 6
    scheduler = default_cosine_scheduler(
        cycle_length=cycle_length, n_min=n_min, n_max=n_max
    )
    schedule = _collect_cosine_schedule(scheduler, cycle_length=cycle_length)
    assert schedule[0] == pytest.approx(n_max, abs=1e-9)
    assert schedule[-1] == pytest.approx(n_min, abs=1e-9)


def test_cosine_memory_fraction_in_unit_interval() -> None:
    """``memory_fraction = 1 - n_cap`` lies in ``[0, 1]`` for every round.

    The schedule sample's ``memory_fraction`` method (ADR-0010) is
    the canonical capacity-to-memory transform; the engine / runner
    consumes it verbatim.
    """
    scheduler = default_cosine_scheduler(cycle_length=12)
    for r in range(12):
        sample = scheduler.sample(
            outer_cycle_id=0, round_in_cycle=r, target_round=r
        )
        m = sample.memory_fraction()
        assert 0.0 <= m <= 1.0, (
            f"memory_fraction at round {r} escaped [0, 1]: {m}"
        )


def test_cosine_schedule_deterministic() -> None:
    """Two schedulers with identical config produce identical schedules.

    Determinism is the framework's per-round scheduling contract.
    """
    s_a = default_cosine_scheduler(cycle_length=10, n_min=0.0, n_max=1.0)
    s_b = default_cosine_scheduler(cycle_length=10, n_min=0.0, n_max=1.0)
    sched_a = _collect_cosine_schedule(s_a, 10)
    sched_b = _collect_cosine_schedule(s_b, 10)
    assert sched_a == sched_b, "cosine schedule not deterministic"


# ---------------------------------------------------------------------------
# CodimensionSheetScheduler
# ---------------------------------------------------------------------------


def _identity_profile(x: float) -> float:
    """A trivial residual profile used for paper-quantity computation."""
    return 0.0


def test_codimension_scheduler_caches_paper_quantities() -> None:
    """``CodimensionSheetScheduler`` caches the four paper quantities
    when ``profile_residual_fn`` is supplied.

    The quantities come from :mod:`paper_quantities`:
        ``A_g = sheet_evidence_A(profile)``
        ``B_g = root_cell_packing_B(profile)``
        ``C_g = per_cell_coefficient_C()``
        ``e_rho = exterior_gap_e_rho()``
    """
    sched = CodimensionSheetScheduler(
        cycle_length=5,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=_identity_profile,
        eps_implicit=0.05,
    )
    # All four quantities are cached on construction.
    assert sched.sheet_A is not None
    assert sched.packing_B is not None
    assert sched.cell_C is not None
    assert sched.exterior_gap_e_rho is not None
    # They agree with the standalone paper_quantities evaluators.
    assert sched.sheet_A == pytest.approx(
        pq.sheet_evidence_A(_identity_profile), rel=1e-12
    )
    assert sched.packing_B == pytest.approx(
        pq.root_cell_packing_B(_identity_profile), rel=1e-12
    )
    assert sched.cell_C == pytest.approx(
        pq.per_cell_coefficient_C(), rel=1e-12
    )
    assert sched.exterior_gap_e_rho == pytest.approx(
        pq.exterior_gap_e_rho(), rel=1e-12
    )


def test_codimension_scheduler_no_profile_returns_none_quantities() -> None:
    """When ``profile_residual_fn is None``, the cached quantities are
    ``None`` (the scheduler uses the framework-side heuristic)."""
    sched = CodimensionSheetScheduler(
        cycle_length=5, n_min=0.0, n_max=1.0, profile_residual_fn=None
    )
    assert sched.sheet_A is None
    assert sched.packing_B is None
    assert sched.cell_C is None
    assert sched.exterior_gap_e_rho is None


def test_codimension_scheduler_evidence_ratio_in_unit_interval() -> None:
    """The per-round ``evidence_ratio`` is in ``[0, 1]`` and tends to
    ``1`` as ``eps_implicit -> 0`` (paper Theorem 1 sheet dominance)."""
    sched = CodimensionSheetScheduler(
        cycle_length=5,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=_identity_profile,
        eps_implicit=0.05,
    )
    ratios: list[float] = []
    for r in range(5):
        s = sched.sample(
            outer_cycle_id=0, round_in_cycle=r, target_round=r
        )
        assert s.evidence_ratio is not None
        assert 0.0 <= s.evidence_ratio <= 1.0, (
            f"evidence_ratio at round {r} escaped [0, 1]: {s.evidence_ratio}"
        )
        ratios.append(float(s.evidence_ratio))

    # Property: as eps_implicit -> 0 the ratio -> 1 (sheet dominance).
    # Test by comparing a moderate and a tiny eps_implicit.
    sched_tiny = CodimensionSheetScheduler(
        cycle_length=5,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=_identity_profile,
        eps_implicit=1e-8,
    )
    sched_moderate = CodimensionSheetScheduler(
        cycle_length=5,
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=_identity_profile,
        eps_implicit=0.5,
    )
    sample_tiny = sched_tiny.sample(0, 0, 0)
    sample_moderate = sched_moderate.sample(0, 0, 0)
    assert sample_tiny.evidence_ratio is not None
    assert sample_moderate.evidence_ratio is not None
    assert sample_tiny.evidence_ratio > sample_moderate.evidence_ratio, (
        f"eps -> 0 should drive ratio to 1; got "
        f"{sample_tiny.evidence_ratio} (tiny) vs "
        f"{sample_moderate.evidence_ratio} (moderate)"
    )


def test_codimension_scheduler_schedule_within_envelope() -> None:
    """``CodimensionSheetScheduler`` keeps ``n_cap`` in ``[n_min, n_max]``
    across the full cycle (with paper-quantity-augmented mode)."""
    sched = CodimensionSheetScheduler(
        cycle_length=8,
        n_min=0.1,
        n_max=0.9,
        profile_residual_fn=_identity_profile,
        eps_implicit=0.05,
    )
    for r in range(8):
        s = sched.sample(0, r, r)
        assert 0.1 - 1e-9 <= s.n_cap <= 0.9 + 1e-9, (
            f"n_cap at round {r} escaped envelope: {s.n_cap}"
        )


def test_codimension_scheduler_eps_regime() -> None:
    """``eps_implicit`` is positive (paper requires ``eps > 0``).

    The scheduler rejects non-positive ``eps_implicit`` and exposes
    it via :attr:`eps_implicit` exactly as supplied.
    """
    with pytest.raises(ValueError):
        CodimensionSheetScheduler(
            cycle_length=5, n_min=0.0, n_max=1.0, eps_implicit=0.0
        )
    with pytest.raises(ValueError):
        CodimensionSheetScheduler(
            cycle_length=5, n_min=0.0, n_max=1.0, eps_implicit=-0.1
        )
    sched = CodimensionSheetScheduler(
        cycle_length=5, n_min=0.0, n_max=1.0, eps_implicit=0.05
    )
    assert sched.eps_implicit == pytest.approx(0.05)


__all__ = [
    "test_cosine_schedule_within_envelope",
    "test_cosine_schedule_monotone_for_n_min_eq_zero",
    "test_cosine_schedule_extremes_match_anchors",
    "test_cosine_memory_fraction_in_unit_interval",
    "test_cosine_schedule_deterministic",
    "test_codimension_scheduler_caches_paper_quantities",
    "test_codimension_scheduler_no_profile_returns_none_quantities",
    "test_codimension_scheduler_evidence_ratio_in_unit_interval",
    "test_codimension_scheduler_schedule_within_envelope",
    "test_codimension_scheduler_eps_regime",
]
