"""GAP-52 — channel-faithful charge blending for the FlowMol3 restart blend.

The upstream FlowMol3 checkpoint consumes ``c`` as a 6-class categorical
(``clip(round(c) + 2, 0, 5)``). The historical blend treated it as a
continuous channel, which shrinks the blended variance by
``m**2 + (1-m)**2`` (std 1.0 -> 0.707 at ``m=0.5``) and raises the
neutral-class probability from 38.3 % to 52.0 %.

These CPU tests pin (a) the byte-stable continuous default, (b) the
categorical mode's marginal preservation, and (c) the per-channel policy
wiring in the canonical R3 driver.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_driver():
    for p in (str(REPO_ROOT), str(REPO_ROOT / "scripts")):
        if p not in sys.path:
            sys.path.insert(0, p)
    return importlib.import_module("wave338_p5_r3_n1000_paired")


def _blend_module():
    from adaptive_reflow.adapters import flowmol3_v2_adapter as mod

    return mod


def _state(seed: int, n: int = 64, discrete_n: int = 8) -> dict:
    rng = np.random.default_rng(seed)
    return {
        "x": rng.standard_normal((n, 3)),
        "c": rng.standard_normal(n),
        "a": rng.integers(0, 10, size=discrete_n),
        "e": rng.integers(0, 5, size=(discrete_n, discrete_n)),
        "n_atoms": n,
    }


def _memory(m: float) -> dict:
    from adaptive_reflow.universal.state import ChannelName

    return {
        ChannelName("coordinate"): m,
        ChannelName("charge"): m,
        ChannelName("raw_pair"): m,
    }


def test_continuous_default_is_the_linear_blend() -> None:
    mod = _blend_module()
    prior, fresh = _state(1), _state(2)
    out = mod._channel_aware_blend(prior, fresh, _memory(0.5))
    np.testing.assert_allclose(out["c"], 0.5 * prior["c"] + 0.5 * fresh["c"])
    np.testing.assert_allclose(out["x"], 0.5 * prior["x"] + 0.5 * fresh["x"])


def test_continuous_default_variance_collapses() -> None:
    """Documents the defect the categorical mode exists to remove."""
    mod = _blend_module()
    n = 200_000
    prior, fresh = _state(3, n), _state(4, n)
    out = mod._channel_aware_blend(prior, fresh, _memory(0.5))
    # var = m^2 + (1-m)^2 = 0.5 at m = 0.5.
    assert out["c"].std() == pytest.approx(np.sqrt(0.5), abs=0.01)


def test_categorical_preserves_the_charge_class_marginal() -> None:
    mod = _blend_module()
    n = 200_000
    prior, fresh = _state(5, n), _state(6, n)
    out = mod._channel_aware_blend(
        prior, fresh, _memory(0.5), charge_mode="categorical"
    )
    # Output labels are integers in [-2, 3] (the 6 upstream classes).
    labels = np.rint(out["c"]).astype(int)
    assert set(np.unique(labels)) <= set(range(-2, 4))
    # P(neutral class) = P(-0.5 < N(0,1) < 0.5) = 0.3829, not the
    # variance-collapsed 0.520.
    p_neutral = float(np.mean(labels == 0))
    assert p_neutral == pytest.approx(0.3829, abs=0.01)


def test_categorical_memory_one_keeps_the_prior_class() -> None:
    mod = _blend_module()
    prior, fresh = _state(7), _state(8)
    out = mod._channel_aware_blend(
        prior, fresh, _memory(1.0), charge_mode="categorical"
    )
    np.testing.assert_array_equal(
        np.rint(out["c"]).astype(int),
        np.clip(np.rint(prior["c"]).astype(int), -2, 3),
    )


def test_categorical_memory_zero_takes_the_fresh_class() -> None:
    mod = _blend_module()
    prior, fresh = _state(9), _state(10)
    out = mod._channel_aware_blend(
        prior, fresh, _memory(0.0), charge_mode="categorical"
    )
    np.testing.assert_array_equal(
        np.rint(out["c"]).astype(int),
        np.clip(np.rint(fresh["c"]).astype(int), -2, 3),
    )


def test_per_channel_policy_betas() -> None:
    mod = _load_driver()
    from adaptive_reflow.universal.state import ChannelName

    policy = mod._make_real_restart_policy(
        seed=1,
        memory_fraction=0.5,
        per_channel={"coordinate": 0.25, "charge": 0.75, "raw_pair": 0.75},
    )
    assert float(policy.beta_by_channel[ChannelName("coordinate")]) == 0.75
    assert float(policy.beta_by_channel[ChannelName("charge")]) == 0.25
    assert float(policy.beta_by_channel[ChannelName("raw_pair")]) == 0.25


def test_per_channel_defaults_to_the_scalar() -> None:
    mod = _load_driver()
    from adaptive_reflow.universal.state import ChannelName

    policy = mod._make_real_restart_policy(
        seed=1, memory_fraction=0.6, per_channel={"charge": 0.9}
    )
    assert float(policy.beta_by_channel[ChannelName("coordinate")]) == pytest.approx(0.4)
    assert float(policy.beta_by_channel[ChannelName("charge")]) == pytest.approx(0.1)
    assert float(policy.beta_by_channel[ChannelName("raw_pair")]) == pytest.approx(0.4)


def test_invalid_charge_mode_is_rejected() -> None:
    from adaptive_reflow.adapters.flowmol3_v2_adapter import FlowMol3V2Adapter

    with pytest.raises(ValueError, match="unknown_charge_blend_mode"):
        FlowMol3V2Adapter(backend="numpy", charge_blend_mode="onehot")
