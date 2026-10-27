"""Parity gate for the torch MNIST inference backend.

The torch backend (:mod:`adaptive_reflow.adapters.mnist_fm_torch`) exists only to
run the *same* arithmetic faster. This file is the contract that makes that
claim checkable: if the two paths ever diverge, the backend is wrong.

Three levels, cheapest first:

1. ``test_forward_matches_numpy`` — one velocity evaluation, float64, at three
   times. Tolerance ``1e-12`` absolute; observed ~4e-15.
2. ``test_rk4_trajectory_matches_numpy`` — ten RK4 steps from a shared ``x0``.
   Tolerance ``1e-12``; observed ~9e-16.
3. ``test_restart_value_matches_distribution`` — the additive
   ``apply_restart_value`` entry point must produce exactly the same blended
   ``x0`` and digest as ``apply_restart_distribution``, which is what lets the
   batched path hold priors in a NumPy array instead of the 128-entry LRU.

The file skips (rather than fails) when torch is not importable, so the default
CPU-only test environment stays green.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from adaptive_reflow.adapters.mnist_fm import (
    MNIST_FLAT_DIM,
    MnistFmAdapter,
    _integrate_rk4,
    _unet_evaluate,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CKPT = REPO_ROOT / "data" / "mnist_fm" / "production.ckpt.npz"

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("torch") is None,
    reason="torch not importable in this interpreter",
)

if not CKPT.exists():  # pragma: no cover — artifact-dependent
    pytestmark = pytest.mark.skip(reason=f"missing checkpoint {CKPT}")


@pytest.fixture(scope="module")
def adapter() -> MnistFmAdapter:
    return MnistFmAdapter(weights_path=CKPT)


@pytest.fixture(scope="module")
def backend():
    from adaptive_reflow.adapters.mnist_fm_torch import TorchMnistVelocity

    return TorchMnistVelocity(CKPT, device="cpu", dtype="float64")


def test_forward_matches_numpy(adapter: MnistFmAdapter, backend) -> None:
    x = np.random.default_rng(0).standard_normal((16, MNIST_FLAT_DIM))
    for t in (0.0, 0.37, 1.0):
        ref = _unet_evaluate(adapter._weights, x, t)
        got = backend.numpy(backend.forward(x, t))
        assert got.shape == ref.shape
        assert np.abs(ref - got).max() < 1e-12, f"forward diverged at t={t}"


def test_rk4_trajectory_matches_numpy(adapter: MnistFmAdapter, backend) -> None:
    x0 = np.random.default_rng(1).standard_normal(MNIST_FLAT_DIM)
    np.clip(x0, -1.0, 1.0, out=x0)
    grid = np.linspace(0.3, 1.0, 11)
    ref = _integrate_rk4(adapter._weights, x0, grid)
    got = backend.numpy(
        backend.integrate_rk4(x0.reshape(1, -1), t0=0.3, t1=1.0, num_steps=10)
    )
    assert np.abs(ref[-1] - got[0]).max() < 1e-12


def test_restart_value_matches_distribution() -> None:
    """``apply_restart_value`` must be a pure refactor of the cache lookup."""
    from scripts.wave191_p3_mnist_sweep import make_policy

    adapter = MnistFmAdapter(weights_path=CKPT)
    policy = make_policy(arm="evidence_driven", beta=0.3, round_idx=1)
    bundle = adapter.build_initial_state(batch_id="parity", sample_id="s00000")
    prior = np.asarray(
        adapter._native_states.get(bundle.native_state_digest, {})["x0"],
        dtype=np.float64,
    )

    via_cache = adapter.apply_restart_distribution(bundle, policy)
    via_value = adapter.apply_restart_value(prior, bundle, policy)

    a = np.asarray(adapter._native_states.get(via_cache.native_state_digest, {})["x0"])
    b = np.asarray(adapter._native_states.get(via_value.native_state_digest, {})["x0"])
    assert np.array_equal(a, b)
    assert via_cache.native_state_digest == via_value.native_state_digest
    assert via_cache.source_round == via_value.source_round
