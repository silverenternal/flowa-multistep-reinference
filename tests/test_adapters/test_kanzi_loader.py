"""Real Kanzi load failures must not become synthetic velocity fields."""
from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from adaptive_reflow.adapters import kanzi
from adaptive_reflow.universal.adapter import CapabilityMissingError


@pytest.mark.parametrize("via_adapter", [False, True])
def test_upstream_builder_failure_is_typed(tmp_path, monkeypatch, via_adapter):
    torch = pytest.importorskip("torch")
    checkpoint = tmp_path / "kanzi.pt"
    torch.save({"model_cfg": {}, "model": {}}, checkpoint)
    failure = RuntimeError("upstream state_dict mismatch")

    class BrokenDAE:
        def __init__(self, config):
            raise failure

    module = ModuleType("kanzi.models")
    module.DAE = BrokenDAE
    module.DAEConfig = SimpleNamespace
    monkeypatch.setitem(sys.modules, "kanzi.models", module)
    with pytest.raises(CapabilityMissingError, match="kanzi_dae_load_failed") as caught:
        if via_adapter:
            kanzi.default_kanzi_adapter(weights_path=checkpoint, force_mode="torch")
        else:
            kanzi._load_torch_model(checkpoint)
    assert caught.value.__cause__ is failure


def test_corrupt_checkpoint_is_typed(tmp_path):
    pytest.importorskip("torch")
    checkpoint = tmp_path / "invalid.pt"
    checkpoint.write_bytes(b"not a torch checkpoint")
    with pytest.raises(CapabilityMissingError, match="kanzi_dae_load_failed") as caught:
        kanzi._load_torch_model(checkpoint)
    assert caught.value.__cause__ is not None


def test_real_checkpoint_loads_on_cpu_with_strict_state(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")
    checkpoint = tmp_path / "weights.pt"
    torch.save({"model_cfg": {}, "model": {"weight": torch.tensor([2.0])}}, checkpoint)

    class DAE(torch.nn.Module):
        def __init__(self, config):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.zeros(1))

    module = ModuleType("kanzi.models")
    module.DAE = DAE
    module.DAEConfig = SimpleNamespace
    monkeypatch.setitem(sys.modules, "kanzi.models", module)
    original_load = torch.load

    def cuda_checkpoint_load(*args, **kwargs):
        # Emulate a CUDA-saved checkpoint on a CPU-only host: every read
        # must explicitly map its storage to CPU.
        assert kwargs.get("map_location") == "cpu"
        return original_load(*args, **kwargs)

    monkeypatch.setattr(torch, "load", cuda_checkpoint_load)
    shim = kanzi._load_torch_model(checkpoint)
    assert isinstance(shim._dae, DAE)
    assert shim._dae.weight.device.type == "cpu"
    assert shim._dae.weight.item() == 2.0
    assert not shim._dae.training

    torch.save({"model_cfg": {}, "model": {}}, checkpoint)
    with pytest.raises(CapabilityMissingError, match="Missing key"):
        kanzi._load_torch_model(checkpoint)


def test_explicit_synthetic_does_not_load_checkpoint(tmp_path, monkeypatch):
    checkpoint = tmp_path / "invalid.pt"
    checkpoint.write_bytes(b"not a torch checkpoint")

    def unexpected_loader(path):
        pytest.fail("explicit synthetic mode must not load real weights")

    monkeypatch.setattr(kanzi, "_load_torch_model", unexpected_loader)
    adapter = kanzi.default_kanzi_adapter(
        weights_path=checkpoint, force_mode="synthetic",
    )
    assert adapter._mode == "synthetic"
    state = adapter.build_initial_state(batch_id="loader-test", sample_id="sample")
    assert state.native_state_digest in adapter._native_states
