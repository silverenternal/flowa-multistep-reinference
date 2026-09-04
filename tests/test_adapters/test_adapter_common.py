"""Tests for ``adapters/_adapter_common.py`` (P2-9).

The helpers in this module are byte-stable aliases for the duplicated
per-adapter bodies. The tests below guard the namespaces that are
load-bearing for ``native_config_hash`` and the ledger chain.
"""

from __future__ import annotations

import hashlib


def test_seed_from_ids_matches_frozen_vector() -> None:
    """Byte-stability guard: the seed is recorded in published digests."""
    from adaptive_reflow.adapters._adapter_common import seed_from_ids

    assert seed_from_ids("b0", "s0", 0) == int(
        __import__("hashlib")
        .sha256(repr(("b0", "s0", 0)).encode("utf-8"))
        .hexdigest()[:8],
        16,
    )


def test_make_ref_prefixes_are_unchanged() -> None:
    """Each adapter's historical TensorRef namespace must be preserved."""
    from adaptive_reflow.adapters._adapter_common import make_ref
    from adaptive_reflow.adapters.mnist_fm import _make_ref as mnist_ref
    from adaptive_reflow.adapters.rectified_flow_cifar import _make_ref as rf_ref
    from adaptive_reflow.adapters.twodim_fm import _make_ref as td_ref

    assert str(mnist_ref("initial", batch="b", sample="s")).startswith("mnist:x:")
    assert str(td_ref("initial", batch="b", sample="s")).startswith("twodim:xy:")
    assert str(rf_ref("initial", batch="b", sample="s")).startswith("rf_cifar:image:")
    # And the shared helper with the same prefix produces the same value.
    assert str(mnist_ref("initial", batch="b", sample="s")) == str(
        make_ref("mnist:x", "initial", batch="b", sample="s")
    )


def test_native_state_cache_is_lru_bounded() -> None:
    from adaptive_reflow.adapters._adapter_common import NativeStateCache

    c = NativeStateCache(maxsize=2)
    c.put("a", {"v": 1})
    c.put("b", {"v": 2})
    c.put("c", {"v": 3})
    assert "a" not in c and len(c) == 2


def test_native_state_cache_supports_inject_forward_noise_surface() -> None:
    """_inject_forward_noise.py reaches through .get / __setitem__."""
    from adaptive_reflow.adapters._adapter_common import NativeStateCache

    c = NativeStateCache(maxsize=4)
    c["d"] = {"x": 1}
    assert c.get("d") == {"x": 1} and c.get("missing") is None


def test_make_adapter_capabilities_defaults_match() -> None:
    """The factory's default kwargs produce the canonical capability surface."""
    from adaptive_reflow.adapters._adapter_common import make_adapter_capabilities

    kwargs = make_adapter_capabilities(
        state_shape=(2,),
        supported_channels=("x",),
        channel_domains={},
        native_config_hash="h",
        native_config_version="v",
    )
    assert kwargs["has_ode_integration_surface"] is True
    assert kwargs["has_prior_export"] is True
    assert kwargs["has_state_export"] is True
    assert kwargs["has_condition_injection"] is True
    assert kwargs["has_restart_boundary"] is True
    assert kwargs["has_continuous_channels"] is True
    assert kwargs["has_discrete_channels"] is False
    assert kwargs["has_trajectory_digest"] is True
    assert kwargs["has_deterministic_seed"] is True
    assert kwargs["has_materialization_route"] is True


def test_memory_fraction_for_returns_default_when_channel_missing() -> None:
    """When a channel is absent from the policy, default to beta=memory=0.5."""
    from adaptive_reflow.adapters._adapter_common import memory_fraction_for

    class _Policy:
        beta_by_channel = {}

    beta, mem = memory_fraction_for(_Policy(), "x")
    assert (beta, mem) == (0.5, 0.5)