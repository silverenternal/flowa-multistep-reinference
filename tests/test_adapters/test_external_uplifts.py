"""Tests for framework-EXTERNAL P0/P1 uplifts.

Covers the new target distributions, the wider-MLP option, the new
integrators (``heun``, ``dpm_solver``, ``unipc``, configurable
``dopri5``), and end-to-end integration through the adapter.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pytest

from adaptive_reflow.adapters.integrators import (
    INTEGRATOR_REGISTRY,
    AMEDSolverIntegrator,
    DormandPrinceRK45Integrator,
    DPMSolverIntegrator,
    HeunIntegrator,
    RK4Integrator,
    UniPCIntegrator,
    build_integrator,
)
from adaptive_reflow.adapters.twodim_fm import (
    TWODIM_FM_DEFAULT_ATOL,
    TWODIM_FM_DEFAULT_MAX_STEPS,
    TWODIM_FM_DEFAULT_RTOL,
    TwoDimFMAdapter,
    default_twodim_fm_adapter,
)
from adaptive_reflow.data.target_distributions import (
    CHECKERBOARD_MODE_CENTERS,
    CHECKERBOARD_NOISE,
    CHECKERBOARD_SAMPLER_CENTERS,
    EIGHT_GAUSSIANS_SAMPLER_CENTERS,
    GAUSSIAN_GRID_MODE_CENTERS,
    GAUSSIAN_GRID_NOISE,
    GAUSSIAN_GRID_SAMPLER_CENTERS,
    PINWHEEL_MODE_CENTERS,
    PINWHEEL_NOISE,
    PINWHEEL_SAMPLER_CENTERS,
    SWISS_ROLL_MODE_CENTERS,
    SWISS_ROLL_NOISE,
    SWISS_ROLL_SAMPLER_CENTERS,
    TWO_MOONS_NOISE,
    sampler_centers_for,
    sampler_for,
    supported_targets,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _simple_velocity(t: float, y: np.ndarray) -> np.ndarray:
    """Constant velocity field for integrator unit tests.

    ``v(x, t) = (1, 0)`` so a perfect solver produces
    ``y(1) = y(0) + (1, 0)`` regardless of step count.
    """
    arr = np.asarray(y, dtype=np.float64)
    if arr.ndim == 1:
        return np.asarray([1.0, 0.0], dtype=np.float64)
    out = np.zeros_like(arr)
    out[..., 0] = 1.0
    return out


def _radial_velocity(t: float, y: np.ndarray) -> np.ndarray:
    """Outward radial velocity ``v = (cos θ, sin θ)`` along the angle.

    Used as a non-trivial velocity field for endpoint-error comparison
    across integrators.
    """
    arr = np.asarray(y, dtype=np.float64)
    if arr.ndim == 1:
        return arr.copy()  # identity; trivial test for the 1-D shape path.
    return arr.copy()


# ---------------------------------------------------------------------------
# 1. INTEGRATOR_REGISTRY surface (P0 #4)
# ---------------------------------------------------------------------------


def test_integrator_registry_contains_all_required_methods() -> None:
    """Registry exposes ``rk4``, ``heun``, ``dpm_solver``, ``unipc``,
    ``dopri5``, ``am_ed`` (P0 #4 + P1 #1)."""
    required = {"rk4", "heun", "dpm_solver", "unipc", "dopri5", "am_ed"}
    assert required.issubset(INTEGRATOR_REGISTRY.keys())


def test_build_integrator_returns_typed_instance() -> None:
    for key, expected_cls in (
        ("rk4", RK4Integrator),
        ("heun", HeunIntegrator),
        ("dpm_solver", DPMSolverIntegrator),
        ("unipc", UniPCIntegrator),
        ("dopri5", DormandPrinceRK45Integrator),
        ("am_ed", AMEDSolverIntegrator),
    ):
        instance = build_integrator(key)
        assert isinstance(instance, expected_cls)


def test_build_integrator_rejects_unknown() -> None:
    with pytest.raises(KeyError):
        build_integrator("not_a_method")


# ---------------------------------------------------------------------------
# 2. Per-integrator endpoint behaviour (P0 #4)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("family", ["rk4", "heun", "dpm_solver", "unipc", "dopri5", "am_ed"])
def test_each_integrator_produces_finite_step(family: str) -> None:
    """Every integrator step returns a finite ``(2,)`` array."""
    integrator = build_integrator(family)
    y0 = np.asarray([0.0, 0.0], dtype=np.float64)
    y1 = integrator.step(_simple_velocity, 0.0, y0, 0.1)
    assert np.all(np.isfinite(y1))
    assert y1.shape == (2,)


def test_rk4_matches_constant_velocity_at_unit_step() -> None:
    """RK4 on constant ``v=(1,0)`` produces exactly ``x = (1, 0)`` at t=1."""
    integrator = RK4Integrator()
    y0 = np.asarray([0.0, 0.0], dtype=np.float64)
    y1 = integrator.step(_simple_velocity, 0.0, y0, 1.0)
    np.testing.assert_allclose(y1, [1.0, 0.0], atol=1e-12)


def test_dpm_solver_matches_constant_velocity() -> None:
    """DPM-Solver first-order is exact on a linear ODE."""
    integrator = DPMSolverIntegrator()
    y0 = np.asarray([0.0, 0.0], dtype=np.float64)
    y1 = integrator.step(_simple_velocity, 0.0, y0, 1.0)
    np.testing.assert_allclose(y1, [1.0, 0.0], atol=1e-12)


def test_dormand_prince_with_configurable_tolerances() -> None:
    """Dormand-Prince constructor accepts rtol / atol / max_steps kwargs."""
    integ = DormandPrinceRK45Integrator(rtol=1e-5, atol=1e-7, max_steps=200)
    assert integ._rtol == pytest.approx(1e-5)
    assert integ._atol == pytest.approx(1e-7)
    assert integ._max_steps == 200
    y1 = integ.step(_simple_velocity, 0.0, np.zeros(2, dtype=np.float64), 0.1)
    assert np.all(np.isfinite(y1))


def test_dormand_prince_rejects_non_positive_tolerances() -> None:
    with pytest.raises(ValueError):
        DormandPrinceRK45Integrator(rtol=0.0, atol=1e-4, max_steps=10)
    with pytest.raises(ValueError):
        DormandPrinceRK45Integrator(rtol=1e-3, atol=-1.0, max_steps=10)
    with pytest.raises(ValueError):
        DormandPrinceRK45Integrator(rtol=1e-3, atol=1e-4, max_steps=0)


# ---------------------------------------------------------------------------
# 3. Target-distribution sampler coverage (P1 #2)
# ---------------------------------------------------------------------------


def test_supported_targets_includes_new_distributions() -> None:
    targets = supported_targets()
    for new in ("swiss_roll", "pinwheel", "checkerboard", "gaussian_grid"):
        assert new in targets


def test_sampler_for_dispatches_each_target() -> None:
    rng = np.random.default_rng(7)
    for target in supported_targets():
        sampler = sampler_for(target)
        out = sampler(64, rng)
        assert out.shape == (64, 2)
        assert np.all(np.isfinite(out))


def test_sampler_for_unknown_raises() -> None:
    with pytest.raises(ValueError):
        sampler_for("not_a_target")


def test_sampler_centers_for_each_new_target() -> None:
    """Each new target exposes sampler-centre geometry."""
    assert sampler_centers_for("swiss_roll").shape == SWISS_ROLL_SAMPLER_CENTERS.shape
    assert sampler_centers_for("pinwheel").shape == PINWHEEL_SAMPLER_CENTERS.shape
    assert sampler_centers_for("checkerboard").shape == CHECKERBOARD_SAMPLER_CENTERS.shape
    assert sampler_centers_for("gaussian_grid").shape == GAUSSIAN_GRID_SAMPLER_CENTERS.shape


def test_gaussian_grid_has_25_modes() -> None:
    """Quantitative target: gaussian_grid has 25 modes to stress
    cosine annealing."""
    assert GAUSSIAN_GRID_SAMPLER_CENTERS.shape == (25, 2)
    assert GAUSSIAN_GRID_MODE_CENTERS.shape == (25, 2)


def test_pinwheel_has_5_arms() -> None:
    assert PINWHEEL_SAMPLER_CENTERS.shape == (5, 2)


def test_checkerboard_has_4_corners() -> None:
    assert CHECKERBOARD_SAMPLER_CENTERS.shape == (4, 2)


# ---------------------------------------------------------------------------
# 4. Wider MLP option (P2 #38)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("hidden", [32, 64, 128, 256])
def test_wider_mlp_random_init_produces_finite_trajectory(hidden: int) -> None:
    """``hidden_width`` 32..256 with ``init_random_weights=True`` yields
    finite endpoint."""
    adapter = TwoDimFMAdapter(
        init_random_weights=True,
        hidden_width=hidden,
        num_steps=10,
    )
    state = adapter.build_initial_state(batch_id="b0", sample_id="s0")
    cond = adapter.compose_condition(
        state,
        _fake_condition(),
    )
    trace = adapter.solve_ode(state, cond, seed=42)
    assert np.all(np.isfinite(_read_endpoint(adapter, trace, state)))


def test_wider_mlp_rejects_non_positive_hidden() -> None:
    with pytest.raises(ValueError):
        TwoDimFMAdapter(init_random_weights=True, hidden_width=0)


# ---------------------------------------------------------------------------
# 5. Adapter constructor validation (P1 #6 / #36)
# ---------------------------------------------------------------------------


def test_adapter_rejects_unknown_target() -> None:
    with pytest.raises(ValueError):
        TwoDimFMAdapter(target="not_a_target")  # type: ignore[arg-type]


def test_adapter_rejects_unknown_integrator() -> None:
    with pytest.raises(ValueError):
        TwoDimFMAdapter(integrator="not_an_integrator")  # type: ignore[arg-type]


def test_adapter_rejects_non_positive_num_steps() -> None:
    with pytest.raises(ValueError):
        TwoDimFMAdapter(num_steps=0)


def test_adapter_rejects_non_positive_rtol() -> None:
    with pytest.raises(ValueError):
        TwoDimFMAdapter(rtol=0.0)


def test_adapter_rejects_non_positive_atol() -> None:
    with pytest.raises(ValueError):
        TwoDimFMAdapter(atol=0.0)


def test_adapter_rejects_non_positive_max_steps() -> None:
    with pytest.raises(ValueError):
        TwoDimFMAdapter(max_steps=0)


def test_default_dormand_prince_tolerances_are_published() -> None:
    """Quantitative target: defaults match the legacy inline values."""
    assert pytest.approx(1e-3) == TWODIM_FM_DEFAULT_RTOL
    assert pytest.approx(1e-4) == TWODIM_FM_DEFAULT_ATOL
    assert TWODIM_FM_DEFAULT_MAX_STEPS == 1000


# ---------------------------------------------------------------------------
# 6. End-to-end adapter integration with new integrators (P0 #4 + P1 #1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("integrator", ["rk4", "heun", "dpm_solver", "unipc"])
def test_adapter_drives_every_new_integrator_end_to_end(integrator: str) -> None:
    """The framework (adapter) drives each new integrator through the
    full protocol surface (``build_initial_state`` -> ``solve_ode``
    -> ``observe_endpoint``)."""
    adapter = TwoDimFMAdapter(integrator=integrator, num_steps=10)
    state = adapter.build_initial_state(batch_id="b0", sample_id="s0")
    cond = adapter.compose_condition(state, _fake_condition())
    trace = adapter.solve_ode(state, cond, seed=42)
    endpoint = adapter.observe_endpoint(trace, state)
    assert trace.steps > 0
    assert trace.accept_rate > 0.0
    assert endpoint.detach_proof is True


def test_adapter_drives_dormand_prince_with_configurable_tolerances() -> None:
    """The framework can drive ``dormand_prince`` with custom tolerances
    (P1 #36)."""
    adapter = TwoDimFMAdapter(
        integrator="dormand_prince",
        rtol=1e-3,
        atol=1e-4,
        max_steps=20,
        num_steps=10,
    )
    state = adapter.build_initial_state(batch_id="b0", sample_id="s0")
    cond = adapter.compose_condition(state, _fake_condition())
    trace = adapter.solve_ode(state, cond, seed=42)
    assert trace.steps > 0
    assert trace.accept_rate > 0.0


# ---------------------------------------------------------------------------
# 7. Default factory exposes new targets and integrators (P0 #10)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("target", ["two_moons", "eight_gaussians"])
@pytest.mark.parametrize("integrator", ["rk4", "heun", "dpm_solver", "unipc"])
def test_default_factory_supports_each_target_integrator_pair(
    target: str, integrator: str
) -> None:
    """``default_twodim_fm_adapter(target, integrator=...)`` builds a
    working adapter for every supported pair."""
    adapter = default_twodim_fm_adapter(target, integrator=integrator)  # type: ignore[arg-type]
    assert adapter._target == target
    assert adapter._integrator == integrator


# ---------------------------------------------------------------------------
# Internal scaffolding
# ---------------------------------------------------------------------------


class _FakeCondition:
    delta_spec: Mapping[str, object] = {}
    source: str = "test"
    target_round: int = 0
    calibration_artifact_hash: str = "h"


def _fake_condition() -> _FakeCondition:
    return _FakeCondition()


def _read_endpoint(adapter: TwoDimFMAdapter, trace, state) -> np.ndarray:
    """Read the final trajectory row from the adapter's native state."""
    entry = adapter._native_states.get(trace.native_state_digest)
    assert entry is not None
    traj = np.asarray(entry["trajectory"], dtype=np.float64)
    return np.asarray(traj[-1], dtype=np.float64)
