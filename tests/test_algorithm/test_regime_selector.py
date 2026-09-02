"""Tests for :mod:`adaptive_reflow.algorithm.scheduler.regime_selector`.

Phase-4 / Design #3 of the FID-JMAA theorem-alignment workflow.

The regime selector enforces the Lemma 4 bound ``eps^2 < e_rho / log 2``
(paper line 110-113) on the scheduler's per-round ``eps`` proposal.
These tests pin the regime predicate, the concrete selectors, the
audit codes, and the integration into
:class:`EvidenceDrivenScheduler` (opt-in regime branch).
"""

from __future__ import annotations

import math

import pytest

from adaptive_reflow.algorithm.scheduler import (
    EPS_REGIME_CLAMPED,
    EPS_REGIME_INFEASIBLE,
    EPS_REGIME_OK,
    REGIME_SELECTOR_REGISTRY,
    SchedulerProtocol,
    build_regime_selector,
)
from adaptive_reflow.algorithm.scheduler.evidence_driven import (
    EVIDENCE_REGIME_GATED,
    REGIME_VIOLATION_WARNING,
    EvidenceDrivenScheduler,
)
from adaptive_reflow.algorithm.scheduler.regime_selector import (
    DEFAULT_REGIME_SLACK,
    EPS_FLOOR,
    CosineAnnealRegimeSelector,
    ConvergenceAdaptiveRegimeSelector,
    RegimeAwareEpsSelector,
    RegimeSelection,
    default_e_rho_provider,
    regime_ceiling,
    regime_holds,
)
from adaptive_reflow.contracts import (
    ArtifactHash,
    CosineScheduleConfig,
    FactorValue,
    LEMMA4_REGIME_SLACK,
    RegimeAwareSchedulerProtocol,
    RegimeGate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    *, cycle_length: int = 20, n_min: float = 0.0, n_max: float = 1.0,
) -> CosineScheduleConfig:
    return CosineScheduleConfig(
        cycle_length=cycle_length,
        n_min=FactorValue(n_min),
        n_max=FactorValue(n_max),
        schedule_family="cosine_no_restart",
        per_channel_caps={},
        fresh_noise_floor_by_channel={},
        symmetric_delta_caps_by_channel={},
        restart_triggers_allowed=(),
        config_hash=ArtifactHash("test_config"),
        frozen_before_evaluation=True,
    )


# ---------------------------------------------------------------------------
# regime_ceiling + regime_holds
# ---------------------------------------------------------------------------


def test_regime_ceiling_strict_form_under_log2() -> None:
    """``ceiling = sqrt(e_rho / log 2) - slack`` so the strict inequality
    ``eps^2 < e_rho / log 2`` survives floating-point rounding."""
    e_rho = 1e-3
    ceil = regime_ceiling(e_rho, slack=DEFAULT_REGIME_SLACK)
    # Strict inequality: ceil**2 must be strictly less than e_rho/log 2.
    assert ceil ** 2 < e_rho / math.log(2.0)
    # Any eps at or below the ceiling satisfies regime_holds.
    assert regime_holds(ceil, e_rho)
    assert regime_holds(ceil * 0.5, e_rho)
    # Going slightly past the ceiling (by slack * 1.01, i.e. past the
    # strict tolerance) re-enters the violation regime.
    assert not regime_holds(ceil + DEFAULT_REGIME_SLACK * 1.01, e_rho)


def test_regime_ceiling_degenerate_inputs() -> None:
    """``e_rho <= 0`` and infeasible slack raise / return 0 deterministically."""
    assert regime_ceiling(0.0) == 0.0
    assert regime_ceiling(-1.0) == 0.0
    with pytest.raises(ValueError):
        regime_ceiling(1e-3, slack=-1.0)
    with pytest.raises(ValueError):
        regime_ceiling(1e-3, slack=float("nan"))


def test_regime_holds_handles_degenerates() -> None:
    """``regime_holds`` returns False for ``eps <= 0`` or ``e_rho <= 0``."""
    assert not regime_holds(0.0, 1e-3)
    assert not regime_holds(-1.0, 1e-3)
    assert not regime_holds(0.1, 0.0)
    assert not regime_holds(0.1, -1.0)


def test_regime_predicate_matches_fid_module() -> None:
    """``regime_holds`` must be bit-for-bit equal to the eval module's
    ``_regime_check`` so the scheduler and the downstream
    ``TheoremAlignedFID`` agree on what "inside the regime" means."""
    from adaptive_reflow.eval.fid_theorem_aligned import _regime_check

    grid = [
        (0.01, 1e-3),
        (0.05, 1e-3),
        (0.037, 1e-3),
        (0.038, 1e-3),
        (1e-6, 1e-3),
        (0.5, 1.0),
        (1.0, 1.0),
        (0.0, 1e-3),
        (0.1, 0.0),
    ]
    for eps, e_rho in grid:
        assert regime_holds(eps, e_rho) == bool(_regime_check(eps, e_rho)), (
            f"predicate divergence at eps={eps}, e_rho={e_rho}"
        )


# ---------------------------------------------------------------------------
# RegimeSelection dataclass
# ---------------------------------------------------------------------------


def test_regime_selection_as_metrics_uses_floats() -> None:
    """``as_metrics`` returns a flat float dict suitable for ledger emission."""
    sel = RegimeSelection(
        eps_next=0.03, eps_requested=0.04, eps_prev=0.05, e_rho=1e-3,
        ceiling=0.037, slack=1e-9, clamped=True, feasible=True,
        regime_check_ok=True,
        audit_codes=(EPS_REGIME_CLAMPED,),
        warning="hello",
    )
    metrics = sel.as_metrics()
    assert all(isinstance(v, float) for v in metrics.values())
    assert metrics["eps_next"] == 0.03
    assert metrics["eps_regime_clamped"] == 1.0
    assert metrics["eps_regime_feasible"] == 1.0
    assert metrics["eps_regime_check_ok"] == 1.0


# ---------------------------------------------------------------------------
# CosineAnnealRegimeSelector
# ---------------------------------------------------------------------------


def test_cosine_regime_respects_ceiling() -> None:
    """``CosineAnnealRegimeSelector`` never emits ``eps > ceiling``."""
    selector = CosineAnnealRegimeSelector(period_rounds=4)
    e_rho = 1e-3
    ceil = regime_ceiling(e_rho)
    for r in range(8):
        # The proposal is the cosine contraction of the previous eps.
        # We feed a constant large eps so the selector has to clamp.
        sel = selector.select_detailed(0.1, e_rho, round_index=r)
        assert sel.eps_next <= ceil + 1e-12
        assert sel.ceiling == pytest.approx(ceil, rel=1e-9)
        # If the proposal was clamped, the audit code must be present.
        if sel.clamped:
            assert EPS_REGIME_CLAMPED in sel.audit_codes[0]


def test_cosine_regime_is_monotone_when_unbounded() -> None:
    """With ``e_rho`` set huge the ceiling never bites and the cosine
    contraction is monotone decreasing in the round index."""
    selector = CosineAnnealRegimeSelector(period_rounds=4, eps_min=1e-6)
    e_rho = 1.0  # ceiling ≈ 1.20, never binds
    values: list[float] = []
    for r in range(6):
        sel = selector.select_detailed(0.1, e_rho, round_index=r)
        values.append(float(sel.eps_next))
    # Each value <= previous one (non-increasing).
    for prev, cur in zip(values[:-1], values[1:]):
        assert cur <= prev + 1e-12
    # The audit code is ``eps_regime_ok`` — no clamps.
    sel = selector.select_detailed(0.1, e_rho, round_index=0)
    assert EPS_REGIME_OK in sel.audit_codes[0]


def test_cosine_regime_to_from_config_round_trip() -> None:
    """``to_config`` / ``from_config`` round-trip the cosine selector."""
    original = CosineAnnealRegimeSelector(
        period_rounds=12, eps_min=1e-4, eps_floor=1e-6,
    )
    rebuilt = CosineAnnealRegimeSelector.from_config(original.to_config())
    assert rebuilt.period_rounds == original.period_rounds
    assert rebuilt.eps_min == original.eps_min
    assert rebuilt._eps_floor == original._eps_floor  # noqa: SLF001 - intentional


# ---------------------------------------------------------------------------
# ConvergenceAdaptiveRegimeSelector
# ---------------------------------------------------------------------------


def test_convergence_regime_clamps_to_ceiling() -> None:
    """``ConvergenceAdaptiveRegimeSelector`` clamps to the regime ceiling."""
    selector = ConvergenceAdaptiveRegimeSelector(
        kp=1.0, kd=0.0, gamma_min=0.5, ema=0.0,
    )
    e_rho = 1e-3
    ceil = regime_ceiling(e_rho)
    # Two metrics: first half-shrinks (improvement) so the
    # contraction factor dips toward ``gamma_min``; the proposal still
    # starts at 0.1, which the clamp must trim to the ceiling.
    selector.observe_round_feedback(0, {"W2": 1.0})
    selector.observe_round_feedback(1, {"W2": 0.5})
    sel = selector.select_detailed(0.1, e_rho, round_index=2)
    assert sel.eps_next <= ceil + 1e-12
    assert sel.regime_check_ok is True


def test_convergence_regime_ignores_missing_metric() -> None:
    """``observe_round_feedback`` without a tracked key is a no-op."""
    selector = ConvergenceAdaptiveRegimeSelector()
    selector.observe_round_feedback(0, {"coverage": 0.7})
    assert selector.last_metric_key is None
    assert selector.history == ()


def test_convergence_regime_factory_routes() -> None:
    """``build_regime_selector`` builds the right concrete type."""
    sel = build_regime_selector("convergence_adaptive", kp=0.2)
    assert isinstance(sel, ConvergenceAdaptiveRegimeSelector)
    assert sel._kp == 0.2  # noqa: SLF001 - intentional


def test_convergence_regime_unknown_family_raises() -> None:
    """Unknown selector families raise ``ValueError`` with a helpful message."""
    with pytest.raises(ValueError, match="unknown regime selector family"):
        build_regime_selector("phantom_family")


def test_convergence_regime_round_trip() -> None:
    """``to_config`` / ``from_config`` rebuilds a matching controller."""
    original = ConvergenceAdaptiveRegimeSelector(
        kp=0.3, kd=0.1, gamma_min=0.4, ema=0.2, eps_min=1e-5,
    )
    rebuilt = ConvergenceAdaptiveRegimeSelector.from_config(original.to_config())
    assert rebuilt._kp == original._kp  # noqa: SLF001
    assert rebuilt._kd == original._kd  # noqa: SLF001
    assert rebuilt._ema == original._ema  # noqa: SLF001
    assert rebuilt.metric_keys == original.metric_keys


# ---------------------------------------------------------------------------
# Regime-aware EvidenceDrivenScheduler
# ---------------------------------------------------------------------------


def test_regime_aware_back_compat_default() -> None:
    """Phase-3 callers (``regime_aware`` defaulted to ``False``) see no regime
    audit codes and identical ``eps_implicit`` propagation."""
    sched = EvidenceDrivenScheduler(_make_config(), eps_implicit_base=0.1)
    assert sched.regime_aware is False
    assert sched.e_rho_provider is None
    sample = sched.sample(0, 0, 0)
    assert sample.eps_implicit is not None
    # No regime code on the audit trail.
    assert not any(
        "regime" in str(code) or "eps_regime" in str(code)
        for code in sample.audit_codes
    )


def test_regime_aware_clamps_eps_to_ceiling() -> None:
    """With a small ``e_rho`` the scheduler clamps the PID's proposal to
    the ceiling and appends the regime audit codes."""
    sched = EvidenceDrivenScheduler(
        _make_config(),
        eps_implicit_base=0.5,
        regime_aware=True,
        e_rho_provider=lambda r: 1e-3,
    )
    sample = sched.sample(0, 0, 0)
    # PID's raw request from eps_implicit_base=0.5 is at least 0.5.
    # The selector must clamp it to the ceiling.
    ceil = regime_ceiling(1e-3)
    assert sample.eps_implicit is not None
    assert sample.eps_implicit <= ceil + 1e-12
    audit_text = " ".join(sample.audit_codes)
    assert EVIDENCE_REGIME_GATED in audit_text
    assert EPS_REGIME_CLAMPED in audit_text


def test_regime_aware_warnings_log_records_clamp() -> None:
    """``regime_violation_warnings`` captures the human-readable warning."""
    sched = EvidenceDrivenScheduler(
        _make_config(),
        eps_implicit_base=0.5,
        regime_aware=True,
        e_rho_provider=lambda r: 1e-3,
    )
    sched.sample(0, 0, 0)
    sched.sample(0, 1, 1)
    warnings = sched.regime_violation_warnings()
    assert len(warnings) == 2
    for w in warnings:
        assert REGIME_VIOLATION_WARNING in w
        assert "Lemma 4" in w


def test_regime_infeasible_when_ceiling_below_floor() -> None:
    """``e_rho`` so small the ceiling is below ``EPS_FLOOR`` infeasibly
    yields the floor and the infeasibility audit code."""
    # ``e_rho = 1e-15`` and ``slack = 1e-3`` push the ceiling into the
    # infeasible regime — the slack itself is larger than the raw bound
    # ``sqrt(e_rho/log 2) ≈ 1.2e-8`` so the selector's
    # ``regime_ceiling`` returns 0.0, tripping the infeasibility
    # branch.
    sched = EvidenceDrivenScheduler(
        _make_config(),
        eps_implicit_base=0.5,
        regime_aware=True,
        e_rho_provider=lambda r: 1e-15,
        regime_slack=1e-3,
    )
    sample = sched.sample(0, 0, 0)
    assert sample.eps_implicit == pytest.approx(EPS_FLOOR)
    audit_text = " ".join(sample.audit_codes)
    assert EPS_REGIME_INFEASIBLE in audit_text
    warnings = sched.regime_violation_warnings()
    assert any(
        "infeasib" in w.lower() or "below" in w.lower()
        for w in warnings
    )


def test_regime_aware_default_e_rho_when_provider_none() -> None:
    """When ``regime_aware=True`` and ``e_rho_provider`` is ``None`` the
    scheduler falls back to the paper default ``exterior_gap_e_rho``."""
    sched = EvidenceDrivenScheduler(
        _make_config(), eps_implicit_base=0.5, regime_aware=True,
    )
    assert callable(sched.e_rho_provider)
    # Sanity: the paper default returns a positive value.
    assert sched.e_rho_provider(0.0) > 0.0


def test_regime_aware_selector_without_aware_raises() -> None:
    """A caller must set ``regime_aware=True`` before passing a selector."""
    with pytest.raises(ValueError, match="regime_aware is False"):
        EvidenceDrivenScheduler(
            _make_config(),
            regime_selector=CosineAnnealRegimeSelector(),
        )


def test_regime_aware_conforms_to_protocol() -> None:
    """The constructed scheduler satisfies both ``SchedulerProtocol`` and the
    new ``RegimeAwareSchedulerProtocol``."""
    sched = EvidenceDrivenScheduler(
        _make_config(),
        eps_implicit_base=0.1,
        regime_aware=True,
        e_rho_provider=lambda r: 1e-3,
    )
    assert isinstance(sched, SchedulerProtocol)
    assert isinstance(sched, RegimeAwareSchedulerProtocol)
    assert hasattr(sched, "regime_violation_warnings")
    assert callable(sched.regime_violation_warnings)


def test_regime_aware_config_hash_distinguishes_selectors() -> None:
    """Two schedulers that differ ONLY in their selector family have
    distinct ``config_hash`` values."""
    sched_a = EvidenceDrivenScheduler(
        _make_config(), eps_implicit_base=0.1,
        regime_aware=True, e_rho_provider=lambda r: 1e-3,
        regime_selector_family="cosine_anneal",
    )
    sched_b = EvidenceDrivenScheduler(
        _make_config(), eps_implicit_base=0.1,
        regime_aware=True, e_rho_provider=lambda r: 1e-3,
        regime_selector_family="convergence_adaptive",
    )
    assert sched_a.config_hash() != sched_b.config_hash()


def test_regime_aware_config_hash_unchanged_when_inert() -> None:
    """Phase-3 callers (``regime_aware=False``) keep the existing hash."""
    sched_v3 = EvidenceDrivenScheduler(_make_config())
    sched_v4 = EvidenceDrivenScheduler(
        _make_config(), regime_aware=False,
    )
    assert sched_v3.config_hash() == sched_v4.config_hash()


def test_regime_aware_to_from_config_round_trip() -> None:
    """``to_config`` / ``from_config`` round-trips the regime branch."""
    original = EvidenceDrivenScheduler(
        _make_config(), eps_implicit_base=0.05,
        regime_aware=True, e_rho_provider=lambda r: 1e-3,
        regime_selector_family="cosine_anneal",
    )
    rebuilt = EvidenceDrivenScheduler.from_config(original.to_config())
    assert rebuilt.config_hash() == original.config_hash()
    assert rebuilt.regime_aware is True
    assert rebuilt.regime_selector is not None
    assert isinstance(rebuilt.regime_selector, CosineAnnealRegimeSelector)


def test_regime_aware_reset_clears_state() -> None:
    """``reset()`` clears the warning log + selector memory."""
    sched = EvidenceDrivenScheduler(
        _make_config(),
        eps_implicit_base=0.5,
        regime_aware=True,
        e_rho_provider=lambda r: 1e-3,
        regime_selector_family="convergence_adaptive",
    )
    sched.record_round_feedback(0, {"W2": 1.0})
    sched.record_round_feedback(1, {"W2": 0.5})
    sched.sample(0, 0, 0)
    sched.sample(0, 1, 1)
    assert len(sched.regime_violation_warnings()) >= 1
    sched.reset()
    assert sched.regime_violation_warnings() == ()
    assert sched.last_regime_selection is None


def test_regime_aware_selectors_fold_feedback() -> None:
    """The convergence selector's feedback fold runs from
    ``record_round_feedback`` so its contraction depends on real rounds."""
    sched = EvidenceDrivenScheduler(
        _make_config(),
        eps_implicit_base=0.5,
        regime_aware=True,
        e_rho_provider=lambda r: 1.0,  # ceiling huge; never clamps
        regime_selector_family="convergence_adaptive",
    )
    # Improving metric trajectory should drive a tighter contraction.
    sched.record_round_feedback(0, {"W2": 1.0})
    sched.record_round_feedback(1, {"W2": 0.4})
    selector = sched.regime_selector
    assert isinstance(selector, ConvergenceAdaptiveRegimeSelector)
    assert selector.last_metric_key == "W2"
    assert len(selector.history) == 2
    # Contraction factor < 1 because the metric improved.
    assert selector.contraction_factor() < 1.0


# ---------------------------------------------------------------------------
# RegimeGate contract
# ---------------------------------------------------------------------------


def test_regime_gate_default_is_inert() -> None:
    """Default ``RegimeGate`` is off and ``is_active()`` returns False."""
    gate = RegimeGate()
    assert gate.regime_aware is False
    assert gate.e_rho_provider is None
    assert gate.is_active() is False
    assert gate.e_rho_at(0.0) is None


def test_regime_gate_propagates_to_provider() -> None:
    """``e_rho_at`` delegates to the supplied provider when active."""
    provider_calls: list[float] = []
    gate = RegimeGate(
        regime_aware=True,
        e_rho_provider=lambda r: provider_calls.append(r) or 0.123,
    )
    assert gate.is_active()
    assert gate.e_rho_at(2.5) == 0.123
    assert provider_calls == [2.5]


def test_regime_gate_slack_aliases_constant() -> None:
    """The default ``RegimeGate.slack`` matches the contracts-layer constant."""
    assert RegimeGate().slack == LEMMA4_REGIME_SLACK


def test_evidence_driven_uses_gate_defaults_when_kwargs_omitted() -> None:
    """A ``RegimeGate`` supplies defaults the constructor would otherwise set."""
    sched = EvidenceDrivenScheduler(
        _make_config(),
        eps_implicit_base=0.05,
        regime_gate=RegimeGate(
            regime_aware=True,
            e_rho_provider=lambda r: 1e-3,
            slack=5e-9,
            selector_family="convergence_adaptive",
        ),
    )
    assert sched.regime_aware is True
    assert sched._regime_slack == 5e-9  # noqa: SLF001
    assert isinstance(sched.regime_selector, ConvergenceAdaptiveRegimeSelector)


def test_evidence_driven_explicit_kwarg_overrides_gate() -> None:
    """Explicit kwargs win over ``regime_gate`` defaults."""
    sched = EvidenceDrivenScheduler(
        _make_config(),
        eps_implicit_base=0.05,
        regime_aware=False,  # explicit kwarg
        regime_gate=RegimeGate(
            regime_aware=True,  # gate says on, kwarg says off
            e_rho_provider=lambda r: 1e-3,
        ),
    )
    assert sched.regime_aware is False


# ---------------------------------------------------------------------------
# default_e_rho_provider
# ---------------------------------------------------------------------------


def test_default_e_rho_provider_returns_positive_value() -> None:
    """The factory wires :func:`paper_quantities.exterior_gap_e_rho`."""
    provider = default_e_rho_provider()
    e_rho = provider(0.0)
    assert e_rho > 0.0
    assert math.isfinite(e_rho)


# ---------------------------------------------------------------------------
# Registry parity
# ---------------------------------------------------------------------------


def test_registry_covers_families() -> None:
    """The registry covers both concrete families."""
    assert "cosine_anneal" in REGIME_SELECTOR_REGISTRY
    assert "convergence_adaptive" in REGIME_SELECTOR_REGISTRY
    assert (
        REGIME_SELECTOR_REGISTRY["cosine_anneal"] is CosineAnnealRegimeSelector
    )
    assert (
        REGIME_SELECTOR_REGISTRY["convergence_adaptive"]
        is ConvergenceAdaptiveRegimeSelector
    )