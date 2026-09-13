import pytest

torch = pytest.importorskip("torch")
from adaptive_reflow.adapters.rectified_flow_cifar import _extract_checkpoint_state_dict


def test_raw_and_model_bundle():
    raw = {"w": torch.zeros(2)}
    assert _extract_checkpoint_state_dict(raw) is raw
    assert _extract_checkpoint_state_dict({"model": raw}) is raw


def test_direct_ema_preferred():
    ema = {"w": torch.ones(2)}
    assert _extract_checkpoint_state_dict({"ema": ema, "model": {"w": torch.zeros(2)}}) is ema


def test_shadow_ema_pairing_and_sigmas():
    model = {"module.w": torch.zeros(2), "module.sigmas": torch.zeros(1)}
    out = _extract_checkpoint_state_dict({"model": model, "ema": {"shadow_params": [torch.ones(2)]}})
    assert torch.equal(out["module.w"], torch.ones(2))
    assert "module.sigmas" in out


@pytest.mark.parametrize("payload", [{"ema": {"shadow_params": []}}, {"model": {}}, {}, []])
def test_invalid_or_malformed_rejected(payload):
    with pytest.raises(RuntimeError):
        _extract_checkpoint_state_dict(payload)


def test_shadow_shape_mismatch_rejected_without_model_fallback():
    model = {"module.w": torch.zeros(2)}
    with pytest.raises(RuntimeError):
        _extract_checkpoint_state_dict({"model": model, "ema": {"shadow_params": [torch.ones(3)]}})


@pytest.mark.parametrize("shadows", [[], [torch.ones(2), torch.ones(2)], [None]])
def test_shadow_count_and_type_mismatch(shadows):
    with pytest.raises(RuntimeError):
        _extract_checkpoint_state_dict({"model": {"w": torch.zeros(2)},
                                        "ema": {"shadow_params": shadows}})


@pytest.mark.parametrize("ema", [{}, {"decay": 0.99}, None])
def test_invalid_ema_never_falls_back_to_non_ema_weights(ema):
    with pytest.raises(RuntimeError):
        _extract_checkpoint_state_dict({"model": {"w": torch.zeros(2)}, "ema": ema})


@pytest.mark.parametrize("model", [{"w": None}, {1: torch.zeros(2)}, {}])
def test_invalid_model_in_shadow_bundle(model):
    with pytest.raises(RuntimeError):
        _extract_checkpoint_state_dict({"model": model, "ema": {"shadow_params": [torch.ones(2)]}})
