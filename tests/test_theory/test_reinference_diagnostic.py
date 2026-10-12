"""CPU unit tests for :mod:`adaptive_reflow.theory.reinference_diagnostic`.

Covers the GAP-09 diagnostic surface: flow integration, the finite-difference
flow-map Lipschitz estimate, the Theorem-4 contraction variable/round-map rate,
and the Theorem-5 exact blend identity + Eq. 7 improvement condition.

NumPy-only — no torch, no GPU, no checkpoint.
"""
from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.theory.reinference_diagnostic import (
    blend_identity_terms,
    contraction_variable,
    estimate_flow_map_lipschitz,
    integrate_flow,
    round_map_contraction,
)


def _const_velocity(c: np.ndarray):
    def v(x: np.ndarray, t: float) -> np.ndarray:
        return np.broadcast_to(c, x.shape).astype(np.float64)

    return v


def _linear_contract(c: float):
    def v(x: np.ndarray, t: float) -> np.ndarray:
        return -c * x

    return v


def test_integrate_flow_constant_field_is_exact() -> None:
    c = np.array([1.0, -2.0, 0.5])
    x0 = np.zeros((3, 3), dtype=np.float64)
    out = integrate_flow(_const_velocity(c), x0, t_final=1.0, n_steps=10)
    # dx/dt = c  =>  x(1) = x0 + c.
    assert np.allclose(out, np.broadcast_to(c, out.shape))


def test_integrate_flow_rejects_bad_shapes() -> None:
    with pytest.raises(ValueError):
        integrate_flow(_const_velocity(np.zeros(3)), np.zeros(3))  # 1-D
    with pytest.raises(ValueError):
        integrate_flow(_const_velocity(np.zeros(3)), np.zeros((2, 3)), n_steps=0)


def test_integrate_flow_detects_shape_mismatch() -> None:
    def bad(x: np.ndarray, t: float) -> np.ndarray:
        return np.zeros((x.shape[0], x.shape[1] + 1))

    with pytest.raises(ValueError):
        integrate_flow(bad, np.zeros((2, 3)))


def test_estimate_lipschitz_on_linear_contraction() -> None:
    # v(x) = -c x  =>  Phi_T(x) = exp(-c) x, so Lip(Phi_T) = exp(-c).
    c = 0.7
    x = np.random.default_rng(0).standard_normal((32, 4))
    rep = estimate_flow_map_lipschitz(
        _linear_contract(c), x, t_final=1.0, n_steps=200, eps=1e-4
    )
    expected = float(np.exp(-c))
    assert rep.k_mean == pytest.approx(expected, rel=0.05)
    assert rep.k_max == pytest.approx(expected, rel=0.05)
    assert rep.n_estimates == x.shape[0] * rep.n_directions


def test_contraction_variable_validation_and_value() -> None:
    assert contraction_variable(0.5, 1.2) == pytest.approx(0.6)
    with pytest.raises(ValueError):
        contraction_variable(1.5, 1.0)
    with pytest.raises(ValueError):
        contraction_variable(-0.1, 1.0)
    with pytest.raises(ValueError):
        contraction_variable(0.5, -1.0)


def test_round_map_contraction_holds_on_contractive_field() -> None:
    x0 = np.random.default_rng(1).standard_normal((4, 3))
    fresh = np.random.default_rng(2).standard_normal((4, 3))
    rep = round_map_contraction(
        _linear_contract(0.5), x0, fresh, m=0.5, t_final=1.0, n_steps=50, n_iter=40
    )
    assert rep.contraction_holds  # q = m * K = 0.5 * exp(-0.5) < 1
    assert rep.contracts_empirically
    assert rep.empirical_rate_geomean < 1.0


def test_blend_identity_is_exact_and_predicts_sign() -> None:
    rng = np.random.default_rng(3)
    z = rng.standard_normal((128, 5))
    # Case A: Y much closer than X, X far from Y -> blend improves over X.
    X = z + 0.5 * rng.standard_normal((128, 5))
    Y = z + 0.05 * rng.standard_normal((128, 5))
    rep_a = blend_identity_terms(X, Y, z, m=0.5)
    assert abs(rep_a.identity_residual) < 1e-9
    assert rep_a.condition_holds
    assert rep_a.measured_blend_better
    assert rep_a.prediction_matches

    # Case B: Y far, X close -> condition fails and blend does not improve.
    X2 = z + 0.05 * rng.standard_normal((128, 5))
    Y2 = z + 0.5 * rng.standard_normal((128, 5))
    rep_b = blend_identity_terms(X2, Y2, z, m=0.5)
    assert abs(rep_b.identity_residual) < 1e-9
    assert rep_b.prediction_matches
    assert not rep_b.condition_holds


def test_blend_identity_rejects_shape_mismatch() -> None:
    with pytest.raises(ValueError):
        blend_identity_terms(np.zeros((2, 3)), np.zeros((2, 4)), np.zeros((2, 3)), m=0.5)
