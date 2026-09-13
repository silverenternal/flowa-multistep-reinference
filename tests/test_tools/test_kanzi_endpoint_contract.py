"""A real sweep must return measured endpoints and honor execution controls."""
from types import SimpleNamespace

import numpy as np
import pytest

from tools import _kanzi_sweep_runner as runner


class Adapter:
    def __init__(self, entry):
        self._native_states = {"initial": {"x0": np.ones((2, 512))}}
        if entry is not None:
            self._native_states["trace"] = entry

    def build_initial_state(self, **kwargs):
        return SimpleNamespace(native_state_digest="initial")

    def set_traj_shape(self, shape):
        self.shape = shape

    def solve_ode(self, bundle, cond, *, seed):
        self.condition = cond
        return SimpleNamespace(native_state_digest="trace")


@pytest.mark.parametrize("entry", [None, {"x0": np.ones((2, 3))}, {"trajectory": []}])
def test_missing_trajectory_is_an_error(entry):
    with pytest.raises(RuntimeError, match="did not produce a trajectory"):
        runner._synthesize_x_final_real(Adapter(entry), 0, seed=42)


@pytest.mark.parametrize("endpoint", [np.empty((0, 3)), np.full((2, 3), np.nan), np.full((2, 3), np.inf)])
def test_empty_or_nonfinite_endpoint_is_an_error(endpoint):
    with pytest.raises(RuntimeError, match="empty or non-finite"):
        runner._synthesize_x_final_real(Adapter({"trajectory": [endpoint]}), 0, seed=42)


def test_rollout_and_decoder_controls_reach_execution(monkeypatch):
    from tools import kanzi_latent_to_coord as bridge

    seen = {}
    def decode(latent, **kwargs):
        seen.update(kwargs)
        return np.ones((1, 2, 3)) * 10

    monkeypatch.setattr(bridge, "kanzi_latent_to_coords", decode)
    monkeypatch.setattr(runner, "torch", SimpleNamespace(manual_seed=lambda seed: None))
    endpoint = np.arange(6).reshape(2, 3)
    adapter = Adapter({"trajectory": [np.zeros((2, 3)), endpoint]})
    result = runner._synthesize_x_final_real(
        adapter, 0, seed=42, decoder=SimpleNamespace(quantize=None),
        mode="framework_inv_proj", num_steps=7, solver="heun", decoder_steps=9,
    )
    assert seen["n_steps"] == 9
    assert adapter.condition.delta_spec.get("num_steps") == 7
    assert adapter.condition.delta_spec.get("sampler_id") == "heun"
    np.testing.assert_array_equal(adapter._native_states["initial"]["x0"], np.ones((2, 3)))
    np.testing.assert_array_equal(result, endpoint)
