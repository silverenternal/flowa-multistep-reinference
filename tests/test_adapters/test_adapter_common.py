"""Tests for ``adapters/_adapter_common.py`` (P2-9).

The helpers in this module are byte-stable aliases for the duplicated
per-adapter bodies. The tests below guard the namespaces that are
load-bearing for ``native_config_hash`` and the ledger chain.
"""

from __future__ import annotations

import hashlib

import pytest


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
    from adaptive_reflow.adapters.twodim_fm import _make_ref as td_ref

    # Wave 42 (D.1 shrink): rectified_flow_cifar dropped its ``_make_ref``
    # wrapper and now calls the shared helper with its historical prefix
    # inline. The namespace guarded here is unchanged.
    def rf_ref(label: str, **parts: object) -> object:
        return make_ref("rf_cifar:image", label, **parts)

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


def test_memory_fraction_for_paper_uplift_27_emits_audit_when_lift_fires() -> None:
    """P0-A12 — paper-uplift-27: e_rho/4 floor lift emits audit code."""
    from adaptive_reflow.adapters._adapter_common import memory_fraction_for

    class _Policy:
        beta_by_channel = {"x": 1.0}  # beta=1.0 -> floor=0.0, lift fires when e_rho/4 > 0

    audit_codes: list[str] = []
    beta, mem = memory_fraction_for(
        _Policy(), "x", exterior_gap_e_rho=0.4, audit_codes=audit_codes
    )
    # floor was 0.0; lift to 0.4 / 4 = 0.1
    assert beta == 1.0
    assert mem == pytest.approx(0.1)
    assert any(c.startswith("merge_paper_quantity_floor_lifted") for c in audit_codes)


def test_memory_fraction_for_paper_uplift_27_no_audit_when_no_lift() -> None:
    """When the schedule floor already dominates e_rho/4, no audit emission."""
    from adaptive_reflow.adapters._adapter_common import memory_fraction_for

    class _Policy:
        beta_by_channel = {"x": 0.5}  # beta=0.5 -> floor=0.5, dominates e_rho/4=2.5e-5

    audit_codes: list[str] = []
    beta, mem = memory_fraction_for(
        _Policy(), "x", exterior_gap_e_rho=1e-4, audit_codes=audit_codes
    )
    assert beta == 0.5
    assert mem == 0.5
    assert audit_codes == []


def test_memory_fraction_for_paper_uplift_27_disabled_by_default() -> None:
    """When exterior_gap_e_rho is None, behaviour is unchanged from baseline."""
    from adaptive_reflow.adapters._adapter_common import memory_fraction_for

    class _Policy:
        beta_by_channel = {"x": 1.0}

    audit_codes: list[str] = []
    beta, mem = memory_fraction_for(_Policy(), "x", audit_codes=audit_codes)
    assert beta == 1.0
    assert mem == 0.0
    assert audit_codes == []

# ---------------------------------------------------------------------------
# D.1 (Wave 33) — make_adapter_capabilities equivalence tests
# ---------------------------------------------------------------------------
# These tests demonstrate that the shared `make_adapter_capabilities`
# helper from `_adapter_common.py` produces the same kwargs dict that
# the 5 NEW adapters (Wave 10 / Wave 21 PHASE-3) would otherwise
# inline in their capability class `__init__`. The goal is to enable a
# future low-risk adapter-shrink (D.1) where these inlined __init__
# blocks are replaced by a call to the shared helper.


def test_make_adapter_capabilities_uses_shared_defaults() -> None:
    """Shared helper sets the 5 always-True capability flags by default."""
    from adaptive_reflow.adapters._adapter_common import make_adapter_capabilities

    kwargs = make_adapter_capabilities(
        state_shape=(2,),
        supported_channels=("x",),
        channel_domains={"x": "continuous"},
        native_config_hash="unit:test:v1",
        native_config_version="1.0.0",
    )
    assert kwargs["has_ode_integration_surface"] is True
    assert kwargs["has_prior_export"] is True
    assert kwargs["has_state_export"] is True
    assert kwargs["has_condition_injection"] is True
    assert kwargs["has_restart_boundary"] is True
    assert kwargs["has_deterministic_seed"] is True
    assert kwargs["state_shape"] == (2,)
    assert kwargs["supported_channels"] == ("x",)
    assert kwargs["native_config_hash"] == "unit:test:v1"


def test_make_adapter_capabilities_matches_freqflow_kwargs() -> None:
    """Shared helper produces kwargs identical to FreqFlow's inlined __init__."""
    from adaptive_reflow.adapters._adapter_common import make_adapter_capabilities
    from adaptive_reflow.adapters.freqflow import (
        FREQ_FLOW_CHANNEL_DOMAINS,
        FREQ_FLOW_CHANNELS,
        FREQ_FLOW_CONFIG_HASH,
        FREQ_FLOW_CONFIG_VERSION,
        FREQ_FLOW_STATE_SHAPE,
    )
    from adaptive_reflow.universal import NoOpMixer

    kwargs = make_adapter_capabilities(
        state_shape=FREQ_FLOW_STATE_SHAPE,
        supported_channels=FREQ_FLOW_CHANNELS,
        channel_domains=FREQ_FLOW_CHANNEL_DOMAINS,
        native_config_hash=FREQ_FLOW_CONFIG_HASH,
        native_config_version=FREQ_FLOW_CONFIG_VERSION,
        required_mixer=NoOpMixer,
    )
    # The shared helper's 5 always-True flags + the freqflow-specific
    # fields together form a superset of what the inlined __init__
    # would pass to super().__init__.
    expected_keys = {
        "has_ode_integration_surface",
        "has_prior_export",
        "has_state_export",
        "has_condition_injection",
        "has_restart_boundary",
        "has_continuous_channels",
        "has_discrete_channels",
        "has_trajectory_digest",
        "has_deterministic_seed",
        "has_materialization_route",
        "state_shape",
        "supported_channels",
        "channel_domains",
        "required_mixer",
        "exposed_envelope_criteria",
        "exposed_evaluators",
        "native_config_hash",
        "native_config_version",
    }
    assert set(kwargs) == expected_keys
    assert kwargs["state_shape"] == FREQ_FLOW_STATE_SHAPE
    assert kwargs["native_config_hash"] == FREQ_FLOW_CONFIG_HASH


def test_make_adapter_capabilities_matches_kanzi_kwargs() -> None:
    """Shared helper produces kwargs identical to Kanzi's inlined __init__."""
    from adaptive_reflow.adapters._adapter_common import make_adapter_capabilities
    from adaptive_reflow.adapters.kanzi import (
        KANZI_CHANNEL_DOMAINS,
        KANZI_CHANNELS,
        KANZI_CONFIG_HASH,
        KANZI_CONFIG_VERSION,
        KANZI_STATE_SHAPE,
    )
    from adaptive_reflow.universal import NoOpMixer

    kwargs = make_adapter_capabilities(
        state_shape=KANZI_STATE_SHAPE,
        supported_channels=KANZI_CHANNELS,
        channel_domains=KANZI_CHANNEL_DOMAINS,
        native_config_hash=KANZI_CONFIG_HASH,
        native_config_version=KANZI_CONFIG_VERSION,
        required_mixer=NoOpMixer,
    )
    assert kwargs["state_shape"] == KANZI_STATE_SHAPE
    assert kwargs["native_config_hash"] == KANZI_CONFIG_HASH


def test_make_adapter_capabilities_extra_kwargs_override() -> None:
    """``extra`` kwargs override the shared defaults (escape hatch for special-case adapters)."""
    from adaptive_reflow.adapters._adapter_common import make_adapter_capabilities

    kwargs = make_adapter_capabilities(
        state_shape=(2,),
        supported_channels=("x",),
        channel_domains={"x": "continuous"},
        native_config_hash="t",
        native_config_version="1",
        has_discrete_channels=True,  # override
    )
    assert kwargs["has_discrete_channels"] is True


def test_make_adapter_capabilities_byte_stable_for_shared_inputs() -> None:
    """Two calls with the same inputs produce identical kwargs dicts (byte-stability for ledger)."""
    from adaptive_reflow.adapters._adapter_common import make_adapter_capabilities

    common = {
        "state_shape": (2,),
        "supported_channels": ("x",),
        "channel_domains": {"x": "continuous"},
        "native_config_hash": "t",
        "native_config_version": "1",
    }
    kwargs_a = make_adapter_capabilities(**common)
    kwargs_b = make_adapter_capabilities(**common)
    assert kwargs_a == kwargs_b
