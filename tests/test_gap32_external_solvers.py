"""CPU tests for the generic GAP-32 external solvers (tools/gap32_external_solvers.py).

Pure-NumPy module — no torch, no GPU. Validates the four arms' shape /
determinism / key algorithmic invariants so the MNIST + FlowMol3 head-to-head
rests on a checked batched port rather than an untested one.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_TOOLS = _REPO_ROOT / "tools"
for _p in (str(_REPO_ROOT), str(_TOOLS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import gap32_external_solvers as ext  # noqa: E402

_ARM_ORDER = ("vanilla", "fastdllm", "abcache", "lediflow")


def _const_field(value: float = 1.0) -> ext.VelocityField:
    def _vf(x: np.ndarray, t: float) -> np.ndarray:
        return np.full_like(np.asarray(x, dtype=np.float64), value)

    return _vf


def _identity_project() -> ext.Project:
    def _p(x: np.ndarray) -> np.ndarray:
        return np.asarray(x, dtype=np.float64)

    return _p


def test_external_arm_roster() -> None:
    # The module's roster is vanilla + the three published accelerators.
    assert set(ext.EXTERNAL_ARMS) == {"vanilla", "fastdllm", "abcache", "lediflow"}


@pytest.mark.parametrize("arm", _ARM_ORDER)
def test_all_arms_preserve_shape(arm: str) -> None:
    x0 = np.zeros((5, 4), dtype=np.float64)
    out, stats = ext.run_external_arm(
        arm=arm,
        velocity_field=_const_field(),
        x0=x0,
        nfe=8,
        t_end=1.0,
        project=_identity_project(),
    )
    assert out.shape == x0.shape
    assert np.all(np.isfinite(out))
    assert stats["n_macro_steps"] == 8


@pytest.mark.parametrize("arm", _ARM_ORDER)
def test_all_arms_are_deterministic(arm: str) -> None:
    x0 = np.linspace(-1.0, 1.0, 24, dtype=np.float64).reshape(6, 4)
    a, _ = ext.run_external_arm(
        arm=arm, velocity_field=_const_field(0.3), x0=x0, nfe=6, t_end=1.0,
        project=_identity_project(),
    )
    b, _ = ext.run_external_arm(
        arm=arm, velocity_field=_const_field(0.3), x0=x0, nfe=6, t_end=1.0,
        project=_identity_project(),
    )
    assert np.array_equal(a, b)


def test_vanilla_euler_matches_constant_field_integral() -> None:
    # dx/dt = 1 over [0, 1] => x_end = x0 + 1 exactly for any nfe.
    x0 = np.zeros((3, 2), dtype=np.float64)
    out, stats = ext.vanilla_euler(
        velocity_field=_const_field(1.0), x0=x0, nfe=10, t_end=1.0,
        project=_identity_project(),
    )
    assert np.allclose(out, 1.0, atol=1e-12)
    assert stats["effective_nfe"] == 10


def test_abcache_reuses_velocity_cache() -> None:
    x0 = np.zeros((4, 3), dtype=np.float64)
    _, stats = ext.solve_ode_abcache(
        velocity_field=_const_field(), x0=x0, nfe=24, t_end=1.0,
        project=_identity_project(),
    )
    # warmup (2) + periodic recomputes must be strictly below the full budget.
    assert stats["effective_nfe"] < 24
    assert stats["n_cache_reuse_steps"] > 0


def test_fastdllm_rejects_bad_threshold() -> None:
    with pytest.raises(ValueError):
        ext.solve_ode_fastdllm(
            velocity_field=_const_field(), x0=np.zeros((1, 2)), nfe=4, t_end=1.0,
            confidence_threshold=1.5, project=_identity_project(),
        )


def test_unknown_arm_raises() -> None:
    with pytest.raises(ValueError):
        ext.run_external_arm(
            arm="nope", velocity_field=_const_field(), x0=np.zeros((1, 2)),
            nfe=4, t_end=1.0, project=_identity_project(),
        )
