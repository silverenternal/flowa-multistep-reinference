"""Pytest suite for dynamic noise bias (D4 — iterative Theorem 1 application)."""

from __future__ import annotations

import pytest

from adaptive_reflow.algorithm.dynamic_noise_bias import (
    DEFAULT_MIN_GUMBEL_TEMP,
    NEW_DYNAMIC_NOISE_BIAS_COMPUTED,
    NEW_DYNAMIC_NOISE_BIAS_EPSILON_FLOORED_BY_PAPER_EXTERIOR_GAP,
    NEW_DYNAMIC_NOISE_BIAS_EPSILON_NONPOSITIVE,
    NEW_DYNAMIC_NOISE_BIAS_GUMBEL_HEURISTIC,
    NEW_DYNAMIC_NOISE_BIAS_GUMBEL_TEMP_COMPUTED,
    NEW_DYNAMIC_NOISE_BIAS_NO_MATERIALIZER,
    NEW_DYNAMIC_NOISE_BIAS_PREV_ANCHORED_TO_PREV_ENDPOINT,
    NEW_DYNAMIC_NOISE_BIAS_SHEET_NONPOSITIVE,
    CategoricalDynamicNoiseBias,
    IdentityDynamicNoiseBias,
    Theorem1DynamicNoiseBias,
    default_dynamic_noise_bias,
)
from adaptive_reflow.contracts.dynamic_noise_bias import (
    DynamicNoiseBiasResult,
    PaperQuantitiesSnapshot,
)


def _pq(
    sheet_A: float = 0.7,
    packing_B: float = 1.0,
    cell_C: float = 2.0,
    e_rho: float = 1e-4,
) -> PaperQuantitiesSnapshot:
    return PaperQuantitiesSnapshot(
        sheet_A=sheet_A,
        packing_B=packing_B,
        cell_C=cell_C,
        exterior_gap_e_rho=e_rho,
    )


# (1) Theorem1DynamicNoiseBias — eps decays monotonically.


def test_theorem1_eps_decays_monotonically() -> None:
    bias = Theorem1DynamicNoiseBias()
    pq = _pq(sheet_A=1.0, e_rho=1e-10)
    eps_values: list[float] = []
    for r in range(5):
        result = bias.compute_noise_bias(
            previous_endpoint={"x": r},
            paper_quantities=pq,
            round_index=r,
            total_rounds=5,
            channel_domain="continuous",
        )
        eps_values.append(result.epsilon_per_channel["default"])
    # Monotone non-increasing.
    for a, b in zip(eps_values, eps_values[1:]):
        assert a >= b, f"eps did not decay: {eps_values}"


def test_theorem1_eps_floored_by_exterior_gap() -> None:
    """When ``sheet_A * decay(r) < e_rho/4`` the floor lifts the epsilon."""
    bias = Theorem1DynamicNoiseBias()
    pq = _pq(sheet_A=1e-5, e_rho=1e-2)  # tiny sheet, big exterior gap
    codes: list[str] = []
    result = bias.compute_noise_bias(
        previous_endpoint={"x": 0},
        paper_quantities=pq,
        round_index=0,
        total_rounds=5,
        channel_domain="continuous",
        audit_codes=codes,
    )
    assert result.epsilon_per_channel["default"] == pytest.approx(1e-2 / 4.0)
    assert any(NEW_DYNAMIC_NOISE_BIAS_EPSILON_FLOORED_BY_PAPER_EXTERIOR_GAP in c for c in codes)


# (2) CategoricalDynamicNoiseBias — Gumbel temperature collapses.


def test_categorical_gumbel_temp_collapses() -> None:
    bias = CategoricalDynamicNoiseBias()
    pq = _pq(sheet_A=0.5, e_rho=1e-10)
    tau_first = None
    tau_last = None
    for r in [0, 4]:
        result = bias.compute_noise_bias(
            previous_endpoint={"x": r},
            paper_quantities=pq,
            round_index=r,
            total_rounds=5,
            channel_domain="discrete",
        )
        assert result.gumbel_temperature_per_channel is not None
        tau = result.gumbel_temperature_per_channel["default"]
        if r == 0:
            tau_first = tau
        else:
            tau_last = tau
    assert tau_first is not None and tau_last is not None
    assert tau_first >= tau_last


def test_categorical_rejects_continuous() -> None:
    bias = CategoricalDynamicNoiseBias()
    with pytest.raises(ValueError):
        bias.compute_noise_bias(
            previous_endpoint=None,
            paper_quantities=_pq(),
            round_index=0,
            total_rounds=1,
            channel_domain="continuous",
        )


def test_categorical_emits_heuristic_audit() -> None:
    bias = CategoricalDynamicNoiseBias()
    codes: list[str] = []
    bias.compute_noise_bias(
        previous_endpoint={"x": 0},
        paper_quantities=_pq(),
        round_index=0,
        total_rounds=2,
        channel_domain="discrete",
        audit_codes=codes,
    )
    assert any(NEW_DYNAMIC_NOISE_BIAS_GUMBEL_HEURISTIC in c for c in codes)


# (3) IdentityDynamicNoiseBias — back-compat.


def test_identity_back_compat() -> None:
    bias = IdentityDynamicNoiseBias()
    class _Sample:
        n_cap_base = 0.42
    result = bias.compute_noise_bias(
        previous_endpoint={"x": 1},
        paper_quantities=None,
        round_index=0,
        total_rounds=2,
        channel_domain="continuous",
        previous_round_sample=_Sample(),
    )
    assert result.epsilon_per_channel["default"] == 0.42
    assert result.bias_source == "schedule_fallback"


# (4) Posterior-mean-proxy threading.


def test_posterior_mean_proxy_threaded() -> None:
    """Without a materializer, the proxy IS the previous_endpoint."""
    bias = Theorem1DynamicNoiseBias()
    prev = {"x": 42}
    result = bias.compute_noise_bias(
        previous_endpoint=prev,
        paper_quantities=_pq(),
        round_index=0,
        total_rounds=2,
        channel_domain="continuous",
    )
    assert result.posterior_mean_proxy is prev
    assert any(NEW_DYNAMIC_NOISE_BIAS_PREV_ANCHORED_TO_PREV_ENDPOINT in c for c in result.audit_codes)


def test_materializer_callable_invoked() -> None:
    """With a materializer, the proxy is the materializer's return value."""
    calls: list[Any] = []
    def mat(value, key):
        calls.append((value, key))
        return {"materialized": True, "value": value}

    bias = Theorem1DynamicNoiseBias(materializer=mat)
    result = bias.compute_noise_bias(
        previous_endpoint={"x": 0},
        paper_quantities=_pq(),
        round_index=0,
        total_rounds=2,
        channel_domain="continuous",
    )
    assert result.posterior_mean_proxy["materialized"] is True
    assert calls == [({"x": 0}, "prev_endpoint")]


def test_materializer_exception_falls_back_to_prev() -> None:
    """If the materializer raises, fall back to previous_endpoint."""
    def mat(value, key):
        raise RuntimeError("materializer_broken")

    bias = Theorem1DynamicNoiseBias(materializer=mat)
    prev = {"x": 99}
    result = bias.compute_noise_bias(
        previous_endpoint=prev,
        paper_quantities=_pq(),
        round_index=0,
        total_rounds=2,
        channel_domain="continuous",
    )
    assert result.posterior_mean_proxy is prev


# (5) Fail-closed.


def test_fail_closed_on_nonpositive_epsilon() -> None:
    bias = Theorem1DynamicNoiseBias()
    pq = _pq(sheet_A=0.0, e_rho=1e-10)  # sheet_A = 0
    codes: list[str] = []
    result = bias.compute_noise_bias(
        previous_endpoint=None,
        paper_quantities=pq,
        round_index=0,
        total_rounds=2,
        channel_domain="continuous",
        audit_codes=codes,
    )
    assert any(NEW_DYNAMIC_NOISE_BIAS_SHEET_NONPOSITIVE in c for c in codes)
    assert result.bias_source == "schedule_fallback"


def test_fail_closed_on_invalid_pq() -> None:
    bias = Theorem1DynamicNoiseBias()
    bad = PaperQuantitiesSnapshot(sheet_A=-1, packing_B=1, cell_C=1, exterior_gap_e_rho=1)
    with pytest.raises(ValueError):
        bias.compute_noise_bias(
            previous_endpoint=None,
            paper_quantities=bad,
            round_index=0,
            total_rounds=1,
            channel_domain="continuous",
        )


# (6) Audit code emission.


def test_audit_code_emission_for_continuous() -> None:
    bias = Theorem1DynamicNoiseBias()
    codes: list[str] = []
    result = bias.compute_noise_bias(
        previous_endpoint={"x": 0},
        paper_quantities=_pq(),
        round_index=0,
        total_rounds=2,
        channel_domain="continuous",
        audit_codes=codes,
    )
    assert any(NEW_DYNAMIC_NOISE_BIAS_COMPUTED in c for c in codes)
    assert any(NEW_DYNAMIC_NOISE_BIAS_PREV_ANCHORED_TO_PREV_ENDPOINT in c for c in codes)


# (7) Selection ratio trace.


def test_selection_ratio_increases_as_eps_decreases() -> None:
    """``sheet / (sheet + cell)`` -> 1 as ``eps -> 0``."""
    bias = Theorem1DynamicNoiseBias()
    pq = _pq(sheet_A=0.7, packing_B=1.0, cell_C=2.0, e_rho=1e-10)
    ratios: list[float] = []
    for r in range(5):
        result = bias.compute_noise_bias(
            previous_endpoint={"x": r},
            paper_quantities=pq,
            round_index=r,
            total_rounds=5,
            channel_domain="continuous",
        )
        ratios.append(result.selection_ratio)
    # Each subsequent ratio >= previous (eps decays -> sheet dominates).
    for a, b in zip(ratios, ratios[1:]):
        assert a <= b, f"selection_ratio did not increase: {ratios}"


# (8) PaperQuantitiesSnapshot validator.


def test_paper_quantities_snapshot_validates() -> None:
    pq = _pq()
    ok, errs = pq.validate()
    assert ok, errs


@pytest.mark.parametrize("field,value", [
    ("sheet_A", 0.0),
    ("packing_B", -1.0),
    ("cell_C", float("nan")),
    ("exterior_gap_e_rho", float("inf")),
])
def test_paper_quantities_rejects_bad_values(field, value) -> None:
    kw = dict(sheet_A=0.5, packing_B=1.0, cell_C=1.0, exterior_gap_e_rho=1e-4)
    kw[field] = value
    pq = PaperQuantitiesSnapshot(**kw)
    ok, errs = pq.validate()
    assert not ok
    assert any(field in e for e in errs)


# (9) Constructor validation.


def test_invalid_constructor_args() -> None:
    with pytest.raises(ValueError):
        Theorem1DynamicNoiseBias(min_gumbel_temp=0.0)
    with pytest.raises(ValueError):
        Theorem1DynamicNoiseBias(min_gumbel_temp=-0.1)
    with pytest.raises(ValueError):
        Theorem1DynamicNoiseBias(decay_kind="")


# (10) Default factory + bias family tags.


def test_default_factory_returns_theorem1() -> None:
    """Per 2026-09-05 user directive: default noise bias is paper-grounded Theorem1,
    not the legacy cosine back-compat IdentityDynamicNoiseBias.

    The IdentityDynamicNoiseBias class remains exported for back-compat callers
    (it is still used as the no-paper-quantities / zero-sheet fallback inside
    Theorem1DynamicNoiseBias.compute_noise_bias itself), but is no longer the
    factory default.
    """
    bias = default_dynamic_noise_bias()
    assert isinstance(bias, Theorem1DynamicNoiseBias)
    assert bias.bias_family() == "theorem1"
    assert not isinstance(bias, IdentityDynamicNoiseBias)


def test_bias_family_tags() -> None:
    assert IdentityDynamicNoiseBias().bias_family() == "identity"
    assert Theorem1DynamicNoiseBias().bias_family() == "theorem1"
    assert CategoricalDynamicNoiseBias().bias_family() == "categorical"
