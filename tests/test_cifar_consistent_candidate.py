"""Verify the candidate's physical restart time, noise and exact call allocation on a zero flow."""

import numpy as np
import pytest

from tools.cifar_consistent_candidate_20261103 import candidate


@pytest.mark.parametrize("cost,first_steps", [(99, 76), (199, 153)])
def test_candidate_matches_physical_state_time_and_has_no_centroid_projection(
    monkeypatch, cost, first_steps
):
    torch = pytest.importorskip("torch")
    monkeypatch.setattr(torch.cuda, "synchronize", lambda *_: None)
    initial = np.arange(5 * 3 * 2 * 2, dtype=np.float32).reshape(5, 3, 2, 2) / 100
    calls = []

    def model(x, t):
        calls.append(float(t[0]))
        return torch.zeros_like(x)

    result, info = candidate(model, initial, seed=101, cost=cost, device="cpu")
    noise = (
        np.random.default_rng(np.random.SeedSequence([101, 1, 0]))
        .standard_normal(initial.shape)
        .astype(np.float32)
    )
    np.testing.assert_allclose(result, 0.7 * initial + 0.3 * noise, rtol=1e-6, atol=1e-7)
    assert len(calls) == cost and info["velocity_calls_per_sample"] == cost
    assert info["parts"] == [first_steps, cost - first_steps]
    assert calls[0] == pytest.approx(0.001)
    assert calls[first_steps] == pytest.approx(0.7)
    assert not np.allclose(result.mean(0), initial.mean(0))
